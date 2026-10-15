"""
mas.pm.receipts: Durable quarantined receipt slice for GHA-04A.

Provides authenticated observation admission, immutable receipt storage,
strict identity and contract hashing, quota enforcement, and crash recovery.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError
from typing import Any, Optional

from mas.authority import get_authority_guard
from mas.iam import MultiTenantIAM, TenantContext, TenantStatus
from mas.pm.delivery import DeliveryGateError
from mas.pm.receipt_access import ReceiptAccess
from mas.pm.receipt_contracts import ReceiptContract, ReceiptPayload
from mas.tenancy import TenantBinding, current_binding

RECEIPTS_DDL = """
CREATE UNIQUE INDEX uq_pm_delivery_tasks_tenant_project_issue ON pm_delivery_tasks(tenant_id, project_id, issue_id);
CREATE TABLE pm_delivery_actions (
 tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL,
 action_id TEXT NOT NULL, contract_digest TEXT NOT NULL CHECK(length(contract_digest)=64),
 contract_json TEXT NOT NULL,
 PRIMARY KEY(tenant_id,project_id,issue_id,action_id),
 FOREIGN KEY(tenant_id,project_id,issue_id) REFERENCES pm_delivery_tasks(tenant_id,project_id,issue_id)
);
CREATE TABLE pm_delivery_receipts (
 receipt_id TEXT NOT NULL PRIMARY KEY CHECK(length(receipt_id)=69 AND substr(receipt_id,1,5)='rcpt_' AND substr(receipt_id,6) NOT GLOB '*[^0-9a-f]*'),
 tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL,
 action_id TEXT NOT NULL, observation_id TEXT NOT NULL,
 payload_digest TEXT NOT NULL CHECK(length(payload_digest)=64),
 payload_json TEXT NOT NULL, admitted_at TEXT NOT NULL,
 authority_verified INTEGER NOT NULL DEFAULT 0 CHECK(authority_verified=0),
 UNIQUE(tenant_id,project_id,issue_id,action_id,observation_id),
 UNIQUE(receipt_id,tenant_id,project_id,issue_id),
 FOREIGN KEY(tenant_id,project_id,issue_id,action_id)
 REFERENCES pm_delivery_actions(tenant_id,project_id,issue_id,action_id)
);
CREATE TABLE pm_delivery_items (
 receipt_id TEXT NOT NULL, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL,
 check_id TEXT NOT NULL, claimed_outcome TEXT NOT NULL CHECK(claimed_outcome IN ('PASSED','FAILED','SKIPPED','UNAVAILABLE')),
 PRIMARY KEY(receipt_id,check_id),
 FOREIGN KEY(receipt_id,tenant_id,project_id,issue_id)
 REFERENCES pm_delivery_receipts(receipt_id,tenant_id,project_id,issue_id)
);
CREATE TRIGGER pm_delivery_actions_no_update BEFORE UPDATE ON pm_delivery_actions BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER pm_delivery_actions_no_delete BEFORE DELETE ON pm_delivery_actions BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER pm_delivery_receipts_no_update BEFORE UPDATE ON pm_delivery_receipts BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER pm_delivery_receipts_no_delete BEFORE DELETE ON pm_delivery_receipts BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER pm_delivery_items_no_update BEFORE UPDATE ON pm_delivery_items BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER pm_delivery_items_no_delete BEFORE DELETE ON pm_delivery_items BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER pm_delivery_actions_no_replace BEFORE INSERT ON pm_delivery_actions
WHEN EXISTS(SELECT 1 FROM pm_delivery_actions WHERE tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND issue_id=NEW.issue_id AND action_id=NEW.action_id)
BEGIN SELECT RAISE(ABORT,'immutable: existing action'); END;
CREATE TRIGGER pm_delivery_receipts_no_replace BEFORE INSERT ON pm_delivery_receipts
WHEN EXISTS(SELECT 1 FROM pm_delivery_receipts WHERE receipt_id=NEW.receipt_id OR (tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND issue_id=NEW.issue_id AND action_id=NEW.action_id AND observation_id=NEW.observation_id))
BEGIN SELECT RAISE(ABORT,'immutable: existing receipt'); END;
CREATE TRIGGER pm_delivery_items_no_replace BEFORE INSERT ON pm_delivery_items
WHEN EXISTS(SELECT 1 FROM pm_delivery_items WHERE receipt_id=NEW.receipt_id AND check_id=NEW.check_id)
BEGIN SELECT RAISE(ABORT,'immutable: existing item'); END;
"""

MAX_CANONICAL_BYTES = 1024 * 1024  # 1 MiB combined
MAX_ITEMS = 128
MAX_ARTIFACTS = 64
MAX_RECEIPTS_PER_PROJECT = 10000
ALLOWED_OUTCOMES = frozenset({"PASSED", "FAILED", "SKIPPED", "UNAVAILABLE"})
IDENTIFIER_REGEX = re.compile(r"^[A-Za-z0-9_\-\.]{1,128}$")


def _extract_entity_name(stmt: str) -> str:
    tokens = stmt.split()
    for i, tok in enumerate(tokens):
        if tok.upper() in ("TABLE", "INDEX", "TRIGGER"):
            return tokens[i + 1].strip("();,")
    return tokens[2].strip("();,")


def migrate_receipts(db: Any) -> None:
    """Additive, checksummed and drift-verified receipt schema migration (version 2026101401)."""
    checksum = hashlib.sha256(RECEIPTS_DDL.strip().encode()).hexdigest()
    statements: list[str] = []
    statement = ""
    for line in RECEIPTS_DDL.strip().splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            stmt_clean = statement.strip()
            if stmt_clean:
                statements.append(stmt_clean)
            statement = ""

    def normalize(sql: str) -> str:
        return re.sub(r"\s+", "", sql).rstrip(";").lower()

    with db.atomic_transaction() as conn:
        row = conn.execute(
            "SELECT checksum FROM pm_schema_migrations WHERE version=2026101401"
        ).fetchone()
        if row:
            if row["checksum"] != checksum:
                raise DeliveryGateError("Receipt migration checksum mismatch")
            for stmt in statements:
                name = _extract_entity_name(stmt)
                observed = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE name=?", (name,)
                ).fetchone()
                if not observed or normalize(observed["sql"]) != normalize(stmt):
                    raise DeliveryGateError("Receipt migration schema mismatch: " + name)
            return

        for stmt in statements:
            conn.execute(stmt)
        conn.execute(
            "INSERT INTO pm_schema_migrations(version,name,checksum) VALUES(2026101401,'receipt_slice_v1',?)",
            (checksum,),
        )


def canonical_json(value: Any) -> str:
    """Produces deterministic canonical JSON serialization without whitespace, sorted keys, NaN/Infinity forbidden."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_digest(value: Any) -> str:
    """Computes SHA-256 hexadecimal digest of canonical JSON serialization."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_identifier(name: str, value: Any) -> None:
    if not isinstance(value, str) or not IDENTIFIER_REGEX.fullmatch(value):
        raise ValueError(f"Invalid {name}: must be 1-128 ASCII alphanumeric, '.', '-', '_'")


def validate_contract(contract: Any) -> None:
    try:
        ReceiptContract.model_validate(contract)
    except ValidationError as exc:
        errors = exc.errors(include_input=False, include_context=False)
        if any(e["loc"] == ("check_ids",) and e["type"] == "value_error" for e in errors):
            raise ValueError("INVALID_CONTRACT: check_ids must be strictly sorted and unique") from exc
        raise ValueError("INVALID_CONTRACT: strict version-one contract required") from exc


def validate_payload(payload: Any, contract: dict[str, Any]) -> None:
    if isinstance(payload, dict):
        for field, limit in (("items", MAX_ITEMS), ("artifact_claims", MAX_ARTIFACTS)):
            if isinstance(payload.get(field), list) and len(payload[field]) > limit:
                raise ValueError(f"INVALID_PAYLOAD: {field} count {len(payload[field])} exceeds limit {limit}")
    try:
        validated = ReceiptPayload.model_validate(payload)
    except ValidationError as exc:
        errors = exc.errors(include_input=False, include_context=False)
        if any(e["loc"] and e["loc"][-1] == "claimed_outcome" for e in errors):
            raise ValueError("INVALID_PAYLOAD: invalid claimed_outcome") from exc
        if any(e["loc"] == () and e["type"] == "value_error" for e in errors):
            raise ValueError("INVALID_PAYLOAD: item check_ids must be strictly sorted and unique") from exc
        raise ValueError("INVALID_PAYLOAD: strict version-one payload required") from exc
    if not {item.check_id for item in validated.items}.issubset(contract["check_ids"]):
        raise ValueError("INVALID_PAYLOAD: item check_ids must be subset of contract check_ids")


def _bound_database(binding: TenantBinding, db: Any) -> Any:
    if db is None:
        from mas.pm.db import PMDatabase
        return PMDatabase(binding.database)
    if Path(db.db_path).resolve() != Path(binding.database).resolve():
        raise PermissionError("Receipt database differs from authenticated storage binding")
    return db


def _require_access(access: Any) -> ReceiptAccess:
    if not isinstance(access, ReceiptAccess):
        raise PermissionError("Explicit trusted receipt access profile required")
    return access


def validate_caller_binding(binding: Any, action: str = "write") -> TenantBinding:
    """Validates the authenticated caller binding afresh against IAM authority."""
    if isinstance(binding, TenantContext):
        raise PermissionError("Naked TenantContext cannot be accepted as proof of IAM authentication")

    resolved_binding = binding
    if resolved_binding is None:
        resolved_binding = current_binding()

    if resolved_binding is None or not isinstance(resolved_binding, TenantBinding):
        raise PermissionError("Authenticated tenant binding required")

    iam = resolved_binding.iam
    if not isinstance(iam, MultiTenantIAM):
        raise PermissionError("Binding requires supported MultiTenantIAM instance")

    identity = resolved_binding.identity
    if not isinstance(identity, TenantContext):
        raise PermissionError("Malformed tenant identity in binding")

    tenant = iam.get_tenant(identity.tenant_id)
    if tenant is None or tenant.status != TenantStatus.ACTIVE:
        raise PermissionError("Tenant is suspended, inactive or does not exist")

    principal = iam.get_principal(identity.tenant_id, identity.principal_id)
    if principal is None:
        raise PermissionError("Principal does not exist")
    p_status = getattr(principal, "status", "ACTIVE")
    if p_status == "SUSPENDED":
        raise PermissionError("Principal is suspended")

    now = time.time()
    if identity.expires_at <= now:
        raise PermissionError("Session token expired")

    if identity.token_id:
        if iam._store:
            sess_doc = iam._store.get("session", identity.token_id)
            if sess_doc is None or sess_doc.get("revoked", False):
                raise PermissionError("Session is revoked or unavailable")
            if sess_doc.get("expires", 0) <= now:
                raise PermissionError("Session is expired")
        else:
            session = iam._sessions.get(identity.token_id)
            if session is None or session.get("revoked", False):
                raise PermissionError("Session is revoked or unavailable")
            if session.get("expires", 0) <= now:
                raise PermissionError("Session is expired")

    tenant_id = identity.tenant_id
    if action == "write":
        has_perm = (
            iam.authorize(identity, "receipt:write", tenant_id, f"urn:mas:tenant:{tenant_id}:receipt")
            or iam.authorize(identity, "storage:write", tenant_id, f"urn:mas:tenant:{tenant_id}:request")
        )
        if not has_perm:
            raise PermissionError("Insufficient authority: receipt:write or storage:write required")
    elif action == "read":
        has_perm = (
            iam.authorize(identity, "receipt:read", tenant_id, f"urn:mas:tenant:{tenant_id}:receipt")
            or iam.authorize(identity, "storage:read", tenant_id, f"urn:mas:tenant:{tenant_id}:request")
        )
        if not has_perm:
            raise PermissionError("Insufficient authority: receipt:read or storage:read required")

    return resolved_binding


def record_observation(
    authenticated_binding: Any,
    action_id: str,
    observation_id: str,
    contract: dict[str, Any],
    payload: dict[str, Any],
    *,
    issue_id: Optional[str] = None,
    project_id: Optional[str] = None,
    db: Optional[Any] = None,
    access: ReceiptAccess | None = None,
) -> dict[str, Any]:
    """Records an untrusted witness observation into the durable quarantined receipt store."""
    access = _require_access(access)
    validate_identifier("action_id", action_id)
    validate_identifier("observation_id", observation_id)
    canonical_contract = canonical_json(contract)
    canonical_payload = canonical_json(payload)
    if len(canonical_contract.encode("utf-8")) + len(canonical_payload.encode("utf-8")) > MAX_CANONICAL_BYTES:
        raise ValueError(f"Request bounds exceeded: combined canonical JSON exceeds {MAX_CANONICAL_BYTES} bytes")

    validate_contract(contract)
    validate_payload(payload, contract)
    contract = json.loads(canonical_contract)
    payload = json.loads(canonical_payload)
    validate_contract(contract)
    validate_payload(payload, contract)

    valid_binding = validate_caller_binding(authenticated_binding, action="write")
    tenant_id = valid_binding.identity.tenant_id

    target_issue_id = issue_id
    if not target_issue_id:
        raise ValueError("issue_id must be explicitly provided")
    validate_identifier("issue_id", target_issue_id)

    if project_id is not None:
        validate_identifier("project_id", project_id)

    with get_authority_guard():
        valid_binding = validate_caller_binding(authenticated_binding, action="write")
        effective_db = _bound_database(valid_binding, db)
        access.require(tenant_id, project_id=project_id, payload=payload)

        with effective_db.atomic_transaction() as conn:
            task_row = conn.execute(
                "SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (target_issue_id,)
            ).fetchone()
            if not task_row:
                raise KeyError(f"Enrolled delivery task not found for issue {target_issue_id}")
            if task_row["tenant_id"] != tenant_id:
                raise PermissionError("Cross-tenant delivery task access forbidden")
            if project_id is not None and task_row["project_id"] != project_id:
                raise ValueError(f"Project mismatch: expected {task_row['project_id']}, got {project_id}")

            effective_project_id = task_row["project_id"]
            access.require(tenant_id, project_id=effective_project_id, payload=payload)
            owner = [tenant_id, effective_project_id, target_issue_id]

            action_hash = sha256_digest({"owner": owner, "contract": contract})
            payload_hash = sha256_digest(payload)

            prior = conn.execute(
                "SELECT contract_digest FROM pm_delivery_actions WHERE tenant_id=? AND project_id=? AND issue_id=? AND action_id=?",
                (*owner, action_id),
            ).fetchone()
            if prior and prior[0] != action_hash:
                raise ValueError("ACTION_CONTRACT_CONFLICT")

            existing = conn.execute(
                "SELECT receipt_id, payload_digest FROM pm_delivery_receipts WHERE tenant_id=? AND project_id=? AND issue_id=? AND action_id=? AND observation_id=?",
                (*owner, action_id, observation_id),
            ).fetchone()
            if existing:
                if existing[1] != payload_hash:
                    raise ValueError("OBSERVATION_CONFLICT")
                return {
                    "status": "EXISTING",
                    "receipt_id": existing[0],
                    "authority_verified": False,
                    "source_authority_verified": False,
                }

            count = conn.execute(
                "SELECT count(*) FROM pm_delivery_receipts WHERE tenant_id=? AND project_id=?",
                (tenant_id, effective_project_id),
            ).fetchone()[0]
            if count >= MAX_RECEIPTS_PER_PROJECT:
                raise ValueError(f"PROJECT_RECEIPT_QUOTA_EXCEEDED: maximum {MAX_RECEIPTS_PER_PROJECT} receipts reached")

            if not prior:
                conn.execute(
                    "INSERT INTO pm_delivery_actions VALUES(?,?,?,?,?,?)",
                    (*owner, action_id, action_hash, canonical_contract),
                )

            receipt_id = "rcpt_" + sha256_digest(
                {
                    "owner": owner,
                    "action_id": action_id,
                    "observation_id": observation_id,
                    "payload_digest": payload_hash,
                }
            )
            admitted_at = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO pm_delivery_receipts VALUES(?,?,?,?,?,?,?,?,?,0)",
                (
                    receipt_id,
                    *owner,
                    action_id,
                    observation_id,
                    payload_hash,
                    canonical_payload,
                    admitted_at,
                ),
            )

            for item in payload["items"]:
                conn.execute(
                    "INSERT INTO pm_delivery_items VALUES(?,?,?,?,?,?)",
                    (receipt_id, *owner, item["check_id"], item["claimed_outcome"]),
                )

            return {
                "status": "CREATED",
                "receipt_id": receipt_id,
                "authority_verified": False,
                "source_authority_verified": False,
            }


def get_receipt(
    authenticated_binding: Any,
    receipt_id: str,
    *,
    db: Optional[Any] = None,
    access: ReceiptAccess | None = None,
) -> Optional[dict[str, Any]]:
    """Read immutable quarantined claims with fresh guarded authority."""
    access = _require_access(access)
    valid_binding = validate_caller_binding(authenticated_binding, action="read")
    tenant_id = valid_binding.identity.tenant_id
    with get_authority_guard():
        valid_binding = validate_caller_binding(authenticated_binding, action="read")
        effective_db = _bound_database(valid_binding, db)
        access.require(tenant_id)

        conn = effective_db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM pm_delivery_receipts WHERE receipt_id=? AND tenant_id=? "
                "AND (? IS NULL OR project_id=?)",
                (receipt_id, tenant_id, access.project_id, access.project_id),
            ).fetchone()
            if not row:
                return None
            if row["tenant_id"] != tenant_id:
                return None
            access.require(tenant_id, project_id=row["project_id"])

            action_row = conn.execute(
                "SELECT contract_json FROM pm_delivery_actions WHERE tenant_id=? AND project_id=? AND issue_id=? AND action_id=?",
                (row["tenant_id"], row["project_id"], row["issue_id"], row["action_id"]),
            ).fetchone()
            if not action_row:
                return None

            items = conn.execute(
                "SELECT check_id, claimed_outcome FROM pm_delivery_items WHERE receipt_id=? ORDER BY check_id",
                (receipt_id,),
            ).fetchall()

            return {
                "receipt_id": row["receipt_id"],
                "tenant_id": row["tenant_id"],
                "project_id": row["project_id"],
                "issue_id": row["issue_id"],
                "action_id": row["action_id"],
                "observation_id": row["observation_id"],
                "payload_digest": row["payload_digest"],
                "payload": json.loads(row["payload_json"]),
                "contract": json.loads(action_row["contract_json"]),
                "admitted_at": row["admitted_at"],
                "authority_verified": False,
                "source_authority_verified": False,
                "items": [
                    {"check_id": it["check_id"], "claimed_outcome": it["claimed_outcome"]}
                    for it in items
                ],
            }
        finally:
            conn.close()


class DeliveryReceiptService:
    """Supported service interface for durable delivery receipts."""

    def __init__(
        self, db: Any, connector_registry=None, *, connector_key=None,
        tenant_id=None, project_id=None, trusted_local=False,
    ) -> None:
        self.db = db
        self.access = ReceiptAccess(connector_registry, connector_key, tenant_id, project_id, trusted_local)

    def record_observation(
        self,
        authenticated_binding: Any,
        action_id: str,
        observation_id: str,
        contract: dict[str, Any],
        payload: dict[str, Any],
        *,
        issue_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> dict[str, Any]:
        return record_observation(
            authenticated_binding,
            action_id,
            observation_id,
            contract,
            payload,
            issue_id=issue_id,
            project_id=project_id,
            db=self.db,
            access=self.access,
        )

    def get_receipt(
        self,
        authenticated_binding: Any,
        receipt_id: str,
    ) -> Optional[dict[str, Any]]:
        return get_receipt(
            authenticated_binding,
            receipt_id,
            db=self.db,
            access=self.access,
        )
