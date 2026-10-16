"""Mediated provider inference broker implementing mas-provider-broker-v1 (CC-05 P1).

Preserves the no-host-mount, no-egress container boundary. Guests submit untrusted
mas-provider-broker-v1 requests over a host-supervised channel; the broker validates
IAM session, coordinator generation, policy version, model allowlist, and held budget
before performing provider inference and durable accounting.
"""
from __future__ import annotations

import hashlib
import math
import re
import secrets
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable

from mas.pm.adapters.antigravity import sanitize_payload
from mas.swarm.contracts import canonical, digest, strict_json

BROKER_SCHEMA = "mas-provider-broker-v1"
MAX_REQUEST_BYTES = 32768  # 32 KiB
MAX_RESPONSE_BYTES = 16384  # 16 KiB
MAX_MESSAGES = 32
DEFAULT_PROVIDER_DEADLINE_S = 45.0
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")

BROKER_ERROR_CATEGORIES = frozenset({
    "INVALID_REQUEST",
    "AUTHORITY_DENIED",
    "STALE_GENERATION",
    "POLICY_CHANGED",
    "BUDGET_EXHAUSTED",
    "UNSUPPORTED_RUNTIME",
    "UNSUPPORTED_MODEL",
    "PROVIDER_UNAVAILABLE",
    "UNKNOWN_PROVIDER_EXECUTION",
    "OUTPUT_LIMIT",
})

LIVE_LOOP_DDL = """
CREATE TABLE IF NOT EXISTS pm_coordinator_broker_requests (
    request_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('builder','reviewer')),
    issuer_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    price_revision INTEGER NOT NULL,
    request_digest TEXT NOT NULL,
    max_output_tokens INTEGER NOT NULL,
    reserved_tokens INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('RESERVED','SENDING','SUCCEEDED','FAILED_CONFIRMED','UNKNOWN_PROVIDER_EXECUTION','CANCELED_BEFORE_SEND')),
    provider_call_id TEXT,
    response_text TEXT,
    response_digest TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_micros INTEGER,
    receipt_id TEXT UNIQUE,
    error_category TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_broker_req_run ON pm_coordinator_broker_requests(run_id, status);
CREATE INDEX IF NOT EXISTS idx_broker_req_attempt ON pm_coordinator_broker_requests(attempt_id);

CREATE TABLE IF NOT EXISTS pm_coordinator_broker_audits (
    audit_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    request_digest TEXT NOT NULL,
    response_digest TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_micros INTEGER,
    reservation_id TEXT,
    settlement_id TEXT,
    error_category TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_broker_audit_req ON pm_coordinator_broker_audits(request_id);

CREATE TABLE IF NOT EXISTS pm_coordinator_candidate_exports (
    proposal_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    policy_version INTEGER NOT NULL,
    builder_id TEXT NOT NULL,
    exporter_id TEXT NOT NULL,
    repo_identity TEXT NOT NULL,
    base_commit_sha TEXT NOT NULL,
    candidate_commit_sha TEXT NOT NULL,
    tree_sha TEXT NOT NULL,
    proposal_digest TEXT NOT NULL,
    diff_digest TEXT NOT NULL,
    artifact_digest TEXT NOT NULL,
    files_count INTEGER NOT NULL,
    total_bytes INTEGER NOT NULL,
    receipt_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cand_export_attempt ON pm_coordinator_candidate_exports(attempt_id, candidate_commit_sha);

CREATE TABLE IF NOT EXISTS pm_coordinator_integrations (
    integration_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    policy_version INTEGER NOT NULL,
    merger_id TEXT NOT NULL,
    authorization_ref TEXT NOT NULL,
    repo_identity TEXT NOT NULL,
    target_ref TEXT NOT NULL,
    expected_target_sha TEXT NOT NULL,
    candidate_commit_sha TEXT NOT NULL,
    tree_sha TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('INTENDED','CONFIRMED','UNKNOWN_INTEGRATION','CONFLICT','REJECTED')),
    confirmed_target_sha TEXT,
    error_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cand_integrations_issue ON pm_coordinator_integrations(issue_id, status);

CREATE TABLE IF NOT EXISTS pm_runtime_activity_events (
    cursor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    run_id TEXT,
    fencing_token INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    kind TEXT NOT NULL,
    authority_class TEXT NOT NULL CHECK(authority_class IN ('GUEST','SERVICE')),
    actor TEXT NOT NULL,
    summary TEXT NOT NULL,
    payload_digest TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    evidence_status TEXT CHECK(evidence_status IN ('claimed','validated','rejected')),
    candidate_commit_sha TEXT,
    occurred_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    UNIQUE(tenant_id, project_id, event_id),
    UNIQUE(tenant_id, project_id, attempt_id, authority_class, sequence)
);
CREATE INDEX IF NOT EXISTS idx_runtime_activity_issue ON pm_runtime_activity_events(tenant_id, project_id, issue_id, cursor_id);

CREATE TABLE IF NOT EXISTS pm_project_board_changes (
    change_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    change_kind TEXT NOT NULL,
    task_version INTEGER NOT NULL,
    summary_json TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_board_changes_proj ON pm_project_board_changes(tenant_id, project_id, change_seq);

CREATE TABLE IF NOT EXISTS pm_coordinator_loop_jobs (
    job_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL UNIQUE,
    task_id TEXT NOT NULL,
    profile TEXT NOT NULL CHECK(profile IN ('coding.solve.v1','repo.verify.v1')),
    stage TEXT NOT NULL CHECK(stage IN ('ADMITTED','DEVELOPING','EXPORTING','VERIFYING','REVIEWING','REWORK_PENDING','AWAITING_REQUIRED_APPROVAL','INTEGRATING','COMPLETION_PENDING','COMPLETE','ESCALATED')),
    current_attempt_id TEXT,
    current_run_id TEXT,
    current_candidate_sha TEXT,
    base_commit_sha TEXT NOT NULL,
    policy_version INTEGER NOT NULL,
    fencing_token INTEGER NOT NULL,
    attempts_used INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    provider_calls_used INTEGER NOT NULL DEFAULT 0,
    max_provider_calls INTEGER NOT NULL DEFAULT 12,
    deadline_epoch REAL NOT NULL,
    is_paused INTEGER NOT NULL DEFAULT 0,
    escalation_category TEXT,
    escalation_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pm_coordinator_loop_handoffs (
    handoff_id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    run_id TEXT,
    policy_version INTEGER NOT NULL,
    fencing_token INTEGER NOT NULL,
    originating_receipt_id TEXT NOT NULL,
    from_stage TEXT NOT NULL,
    to_stage TEXT NOT NULL,
    destination_role TEXT NOT NULL,
    canonical_digest TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PENDING','DISPATCHED','ACKNOWLEDGED','CANCELED')),
    created_at TEXT NOT NULL,
    acknowledged_at TEXT,
    UNIQUE(job_id, originating_receipt_id, to_stage)
);
CREATE INDEX IF NOT EXISTS idx_loop_handoffs_job ON pm_coordinator_loop_handoffs(job_id, status);

CREATE TABLE IF NOT EXISTS pm_coordinator_escalations (
    escalation_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT,
    run_id TEXT,
    candidate_commit_sha TEXT,
    category TEXT NOT NULL,
    decision_needed TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    held_liabilities INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK(status IN ('OPEN','RESOLVED')),
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_coord_escalations_issue ON pm_coordinator_escalations(issue_id, status);
"""


def migrate_live_loop(db: Any) -> None:
    """Additive, checksummed schema migration for P1–P6 live coordinator contracts (version 2026101601)."""
    checksum = hashlib.sha256(LIVE_LOOP_DDL.strip().encode("utf-8")).hexdigest()
    with db.atomic_transaction() as conn:
        row = conn.execute(
            "SELECT checksum FROM pm_schema_migrations WHERE version=2026101601"
        ).fetchone()
        if row:
            if row["checksum"] != checksum:
                raise sqlite3.DatabaseError("Live loop migration checksum mismatch")
            return
        for stmt in LIVE_LOOP_DDL.strip().split(";"):
            clean = stmt.strip()
            if clean:
                conn.execute(clean + ";")
        conn.execute(
            "INSERT INTO pm_schema_migrations(version,name,checksum) VALUES(2026101601,'live_loop_v1',?)",
            (checksum,),
        )


class BrokerError(RuntimeError):
    """Bounded, credential-safe provider broker error."""

    def __init__(self, category: str, message: str) -> None:
        if category not in BROKER_ERROR_CATEGORIES:
            category = "UNKNOWN_PROVIDER_EXECUTION"
        self.category = category
        # Never expose internal paths or credential-bearing URLs
        safe_msg = sanitize_payload(re.sub(r"https?://\S+", "[REDACTED_URL]", str(message)))
        super().__init__(f"{category}: {safe_msg}")


@dataclass(frozen=True)
class PriceSchedule:
    """Versioned operator-approved price schedule in integer micro-units per 1,000 tokens."""
    revision: int
    provider_id: str
    model_id: str
    input_micros_per_1k: int
    output_micros_per_1k: int

    def __post_init__(self) -> None:
        if (
            type(self.revision) is not int or self.revision <= 0
            or type(self.input_micros_per_1k) is not int or self.input_micros_per_1k < 0
            or type(self.output_micros_per_1k) is not int or self.output_micros_per_1k < 0
            or not self.provider_id or not self.model_id
        ):
            raise ValueError("Invalid operator price schedule")

    def compute_cost_micros(self, input_tokens: int, output_tokens: int) -> int:
        return math.ceil(
            (input_tokens * self.input_micros_per_1k + output_tokens * self.output_micros_per_1k) / 1000
        )


@dataclass
class BrokerChannelBinding:
    """Host-supervised channel bound to exactly one physical run and generation."""
    channel_id: str
    tenant_id: str
    project_id: str
    issue_id: str
    task_id: str
    attempt_id: str
    run_id: str
    fencing_token: int
    policy_version: int
    role: str  # 'builder' or 'reviewer'
    issuer_id: str
    iam_token: str
    approved_provider: str
    approved_model: str
    role_system_prompt: str
    max_output_tokens_limit: int
    max_calls_per_run: int = 12
    deadline_epoch: float = 0.0
    revoked: bool = False
    halted_by_overspend: bool = False

    def __post_init__(self) -> None:
        if self.role not in {"builder", "reviewer"}:
            raise ValueError("Channel role must be 'builder' or 'reviewer'")
        if type(self.fencing_token) is not int or self.fencing_token <= 0:
            raise ValueError("Positive integer fencing_token required")
        if type(self.policy_version) is not int or self.policy_version <= 0:
            raise ValueError("Positive integer policy_version required")
        if type(self.max_output_tokens_limit) is not int or self.max_output_tokens_limit <= 0:
            raise ValueError("Positive integer max_output_tokens_limit required")
        if type(self.max_calls_per_run) is not int or not 1 <= self.max_calls_per_run <= 64:
            raise ValueError("Invalid max_calls_per_run")


@dataclass(frozen=True)
class ProviderTransportOutcome:
    """Measured outcome from a trusted host provider transport."""
    provider_call_id: str
    chunks: tuple[str, ...]
    input_tokens: Any
    output_tokens: Any
    status: str = "SUCCEEDED"  # 'SUCCEEDED', 'FAILED_CONFIRMED', 'UNKNOWN'


class ProviderTransport:
    """Interface for host-owned HTTPS provider inference calls."""

    def send(
        self,
        *,
        request_id: str,
        provider_id: str,
        model_id: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_output_tokens: int,
        timeout_s: float,
    ) -> ProviderTransportOutcome:
        raise NotImplementedError

    def reconcile(self, *, request_id: str, provider_id: str, model_id: str) -> ProviderTransportOutcome | None:
        """Optional provider-side status check for in-flight SENDING requests after restart."""
        return None


def validate_guest_broker_request(raw_request: str | bytes | dict[str, Any], max_output_allowance: int) -> dict[str, Any]:
    """Strictly validates a mas-provider-broker-v1 guest request before reserving funding."""
    if isinstance(raw_request, (str, bytes)):
        encoded = raw_request.encode("utf-8") if isinstance(raw_request, str) else raw_request
        if len(encoded) > MAX_REQUEST_BYTES:
            raise BrokerError("INVALID_REQUEST", "Request exceeds 32 KiB limit")
        try:
            payload = strict_json(encoded)
        except Exception as exc:
            raise BrokerError("INVALID_REQUEST", f"Malformed JSON request: {exc}") from exc
    elif isinstance(raw_request, dict):
        try:
            serialized = canonical(raw_request).encode("utf-8")
        except Exception as exc:
            raise BrokerError("INVALID_REQUEST", f"Non-canonicalizable request: {exc}") from exc
        if len(serialized) > MAX_REQUEST_BYTES:
            raise BrokerError("INVALID_REQUEST", "Request exceeds 32 KiB limit")
        payload = strict_json(serialized)
    else:
        raise BrokerError("INVALID_REQUEST", "Request must be JSON object")

    if not isinstance(payload, dict) or set(payload.keys()) != {
        "schema",
        "request_id",
        "messages",
        "max_output_tokens",
    }:
        raise BrokerError("INVALID_REQUEST", "Request must contain exact mas-provider-broker-v1 fields")

    if payload["schema"] != BROKER_SCHEMA:
        raise BrokerError("INVALID_REQUEST", "Unsupported broker schema")

    req_id = payload["request_id"]
    if not isinstance(req_id, str) or not UUID_RE.fullmatch(req_id):
        raise BrokerError("INVALID_REQUEST", "request_id must be a valid lowercase UUID")

    max_out = payload["max_output_tokens"]
    if type(max_out) is not int or max_out <= 0:
        raise BrokerError("INVALID_REQUEST", "max_output_tokens must be a positive integer")
    if max_out > max_output_allowance:
        raise BrokerError("INVALID_REQUEST", "max_output_tokens exceeds approved job allowance")

    messages = payload["messages"]
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise BrokerError("INVALID_REQUEST", "messages must be a non-empty list of at most 32 items")

    for msg in messages:
        if not isinstance(msg, dict) or set(msg.keys()) != {"role", "content"}:
            raise BrokerError("INVALID_REQUEST", "Each message must have exact keys {'role', 'content'}")
        if msg["role"] not in {"user", "assistant"}:
            raise BrokerError("INVALID_REQUEST", "Guest messages may only use 'user' or 'assistant' roles")
        content = msg["content"]
        if not isinstance(content, str) or not content.strip():
            raise BrokerError("INVALID_REQUEST", "Message content must be non-empty plain text")
        if "\x00" in content:
            raise BrokerError("INVALID_REQUEST", "Null bytes forbidden in message content")

    return payload


class ProviderBroker:
    """Host-owned mediated inference broker with durable accounting and IAM verification."""

    def __init__(
        self,
        db: Any,
        *,
        iam: Any,
        transport: ProviderTransport,
        allowed_models: dict[tuple[str, str], PriceSchedule],
        supported_runtimes: set[str] | None = None,
        audit_hook: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        migrate_live_loop(db)
        self.db = db
        self.iam = iam
        self.transport = transport
        self.allowed_models = dict(allowed_models)
        self.supported_runtimes = frozenset(supported_runtimes or {"antigravity", "codex", "synthetic"})
        self.audit_hook = audit_hook
        self._channels: dict[str, BrokerChannelBinding] = {}

    def open_channel(self, binding: BrokerChannelBinding) -> BrokerChannelBinding:
        """Registers a host-supervised channel bound to one physical run and generation."""
        for existing in self._channels.values():
            if existing.run_id == binding.run_id and existing.role == binding.role and not existing.revoked:
                if existing.channel_id != binding.channel_id:
                    raise BrokerError("AUTHORITY_DENIED", "Run/role already bound to an active channel")
        self._channels[binding.channel_id] = binding
        return binding

    def revoke_channel(self, channel_id: str) -> None:
        """Revokes a channel prior to container cleanup or cancellation."""
        ch = self._channels.get(channel_id)
        if ch is not None:
            ch.revoked = True

    def _record_audit(self, conn: sqlite3.Connection, entry: dict[str, Any]) -> None:
        if self.audit_hook is not None:
            self.audit_hook(entry)
        conn.execute(
            """
            INSERT INTO pm_coordinator_broker_audits (
                audit_id, request_id, tenant_id, project_id, issue_id, task_id,
                attempt_id, run_id, actor_id, provider_id, model_id,
                request_digest, response_digest, input_tokens, output_tokens,
                cost_micros, reservation_id, settlement_id, error_category, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry["audit_id"],
                entry["request_id"],
                entry["tenant_id"],
                entry["project_id"],
                entry["issue_id"],
                entry["task_id"],
                entry["attempt_id"],
                entry["run_id"],
                entry["actor_id"],
                entry["provider_id"],
                entry["model_id"],
                entry["request_digest"],
                entry.get("response_digest"),
                entry.get("input_tokens"),
                entry.get("output_tokens"),
                entry.get("cost_micros"),
                entry.get("reservation_id"),
                entry.get("settlement_id"),
                entry.get("error_category"),
                entry["created_at"],
            ),
        )

    def _verify_channel_and_job_state(
        self,
        conn: sqlite3.Connection,
        channel: BrokerChannelBinding,
    ) -> tuple[PriceSchedule, str, int]:
        """Rechecks IAM session, coordinator generation, policy, cancellation, model allowlist, and budget."""
        if channel.revoked:
            raise BrokerError("AUTHORITY_DENIED", "Broker channel has been revoked")
        if channel.halted_by_overspend:
            raise BrokerError("BUDGET_EXHAUSTED", "Channel halted due to uncovered usage liability")

        # 1. Verify IAM session & scope
        try:
            ctx = self.iam.verify_token(channel.iam_token)
            if (
                ctx.principal_id != channel.issuer_id
                or ctx.tenant_id != channel.tenant_id
                or not self.iam.authorize(
                    ctx,
                    "coordinator:broker:invoke",
                    channel.tenant_id,
                    f"urn:mas:tenant:{channel.tenant_id}:coordinator:broker",
                )
            ):
                raise BrokerError("AUTHORITY_DENIED", "IAM principal or broker scope unauthorized")
        except BrokerError:
            raise
        except Exception as exc:
            raise BrokerError("AUTHORITY_DENIED", f"IAM session invalid or revoked: {exc}") from exc

        # 2. Verify model/provider allowlist and price revision
        schedule = self.allowed_models.get((channel.approved_provider, channel.approved_model))
        if schedule is None:
            raise BrokerError("UNSUPPORTED_MODEL", "Requested provider/model is not in operator allowlist")

        # 3. Verify coordinator run/attempt/intent/issue state
        row = conn.execute(
            """
            SELECT a.tenant_id, a.project_id, a.issue_id, a.task_id,
                   a.status AS attempt_status, a.budget_tokens_allocated, a.budget_tokens_spent,
                   r.status AS run_status, r.fencing_token AS run_fence,
                   i.intent_id, i.adapter_type, i.status AS intent_status, i.fencing_token AS intent_fence,
                   q.policy_version, q.has_pending_reconciliation
            FROM pm_coordinator_runs r
            JOIN pm_coordinator_attempts a ON a.attempt_id = r.attempt_id
            JOIN pm_coordinator_intents i ON i.intent_id = r.intent_id AND i.attempt_id = a.attempt_id
            JOIN pm_issues q ON q.id = a.issue_id AND q.project_id = a.project_id
            WHERE r.run_id = ? AND a.attempt_id = ?
            """,
            (channel.run_id, channel.attempt_id),
        ).fetchone()
        if not row:
            raise BrokerError("AUTHORITY_DENIED", "Coordinator run or attempt record not found")

        if (
            row["tenant_id"] != channel.tenant_id
            or row["project_id"] != channel.project_id
            or row["issue_id"] != channel.issue_id
            or row["task_id"] != channel.task_id
        ):
            raise BrokerError("AUTHORITY_DENIED", "Channel identity mismatch against coordinator store")

        if row["adapter_type"] not in self.supported_runtimes:
            raise BrokerError("UNSUPPORTED_RUNTIME", "Adapter runtime does not support mediated broker")

        if row["run_fence"] != channel.fencing_token or row["intent_fence"] != channel.fencing_token:
            raise BrokerError("STALE_GENERATION", "Channel fencing token is stale")

        if row["policy_version"] != channel.policy_version or row["has_pending_reconciliation"]:
            raise BrokerError("POLICY_CHANGED", "Issue policy changed or has pending reconciliation")

        if row["intent_status"] in {"CANCELED", "CANCEL_REQUESTED"} or row["attempt_status"] == "CANCELED":
            raise BrokerError("AUTHORITY_DENIED", "Execution intent or attempt is canceled")

        # Check loop pause if enrolled in automatic loop
        loop_row = conn.execute(
            "SELECT is_paused FROM pm_coordinator_loop_jobs WHERE issue_id = ?",
            (channel.issue_id,),
        ).fetchone()
        if loop_row and loop_row["is_paused"]:
            raise BrokerError("AUTHORITY_DENIED", "Coordinator job is paused")

        # Check active reservation (builder requires HELD; reviewer may execute after builder SETTLED within attempt allocation)
        allowed_res_states = ("HELD", "SETTLED") if channel.role == "reviewer" else ("HELD",)
        placeholders = ",".join("?" for _ in allowed_res_states)
        res_row = conn.execute(
            f"""
            SELECT reservation_id, amount, settled_amount, status
            FROM pm_coordinator_reservations
            WHERE attempt_id = ? AND status IN ({placeholders})
            ORDER BY created_at DESC LIMIT 1
            """,
            (channel.attempt_id, *allowed_res_states),
        ).fetchone()
        if not res_row or res_row["amount"] <= 0:
            raise BrokerError("BUDGET_EXHAUSTED", "No active HELD budget reservation for attempt")

        return schedule, res_row["reservation_id"], int(res_row["amount"])

    def handle_request(self, channel_id: str, raw_request: str | bytes | dict[str, Any]) -> dict[str, Any]:
        """Processes a mas-provider-broker-v1 request with durable idempotency and accounting."""
        channel = self._channels.get(channel_id)
        if channel is None:
            raise BrokerError("AUTHORITY_DENIED", "Unknown broker channel")

        # Validate request schema & bounds BEFORE reserving funding
        parsed = validate_guest_broker_request(raw_request, channel.max_output_tokens_limit)
        request_id = parsed["request_id"]
        max_output_tokens = parsed["max_output_tokens"]
        messages = parsed["messages"]
        req_digest = digest({
            "schema": BROKER_SCHEMA,
            "request_id": request_id,
            "messages": messages,
            "max_output_tokens": max_output_tokens,
            "run_id": channel.run_id,
            "role": channel.role,
            "provider_id": channel.approved_provider,
            "model_id": channel.approved_model,
        })

        # Estimate input tokens conservatively (1 token per 4 bytes + 16 overhead) for sub-reservation check
        prompt_bytes = len(canonical(messages).encode("utf-8")) + len(channel.role_system_prompt.encode("utf-8"))
        estimated_input_tokens = max(1, (prompt_bytes + 3) // 4)
        sub_reservation_tokens = estimated_input_tokens + max_output_tokens

        now_iso = datetime.now(timezone.utc).isoformat()
        need_reconcile = False

        # Step 1 & 2: Atomic check/create in DB before network send
        with self.db.atomic_transaction() as conn:
            existing = conn.execute(
                "SELECT * FROM pm_coordinator_broker_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            if existing is not None:
                if existing["request_digest"] != req_digest or existing["run_id"] != channel.run_id:
                    raise BrokerError("INVALID_REQUEST", "Conflicting request payload or run for existing request_id")
                status = existing["status"]
                if status == "SUCCEEDED":
                    # Re-verify caller authority before replaying
                    self._verify_channel_and_job_state(conn, channel)
                    return {
                        "schema": BROKER_SCHEMA,
                        "request_id": request_id,
                        "status": "SUCCEEDED",
                        "provider_call_id": existing["provider_call_id"],
                        "provider_id": existing["provider_id"],
                        "model_id": existing["model_id"],
                        "response_text": existing["response_text"],
                        "input_tokens": existing["input_tokens"],
                        "output_tokens": existing["output_tokens"],
                        "receipt_id": existing["receipt_id"],
                    }
                if status == "SENDING":
                    need_reconcile = True
                else:
                    raise BrokerError(
                        existing["error_category"] or "UNKNOWN_PROVIDER_EXECUTION",
                        f"Request previously terminated in state {status}",
                    )

            schedule, reservation_id, held_amount = self._verify_channel_and_job_state(conn, channel)

            if not need_reconcile:
                # Check call count bound and remaining token budget
                call_stats = conn.execute(
                    """
                    SELECT COUNT(*) AS call_count,
                           COALESCE(SUM(CASE
                               WHEN status = 'SUCCEEDED' THEN COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)
                               WHEN status IN ('RESERVED', 'SENDING', 'UNKNOWN_PROVIDER_EXECUTION') THEN reserved_tokens
                               ELSE 0
                           END), 0) AS committed_or_held_tokens
                    FROM pm_coordinator_broker_requests
                    WHERE attempt_id = ?
                    """,
                    (channel.attempt_id,),
                ).fetchone()
                if call_stats["call_count"] >= channel.max_calls_per_run:
                    raise BrokerError("BUDGET_EXHAUSTED", "Maximum provider calls per run exceeded")
                if call_stats["committed_or_held_tokens"] + sub_reservation_tokens > held_amount:
                    raise BrokerError("BUDGET_EXHAUSTED", "Available held token budget insufficient for request ceiling")

                conn.execute(
                    """
                    INSERT INTO pm_coordinator_broker_requests (
                        request_id, tenant_id, project_id, issue_id, task_id,
                        attempt_id, run_id, fencing_token, role, issuer_id,
                        provider_id, model_id, price_revision, request_digest,
                        max_output_tokens, reserved_tokens, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'SENDING', ?, ?)
                    """,
                    (
                        request_id,
                        channel.tenant_id,
                        channel.project_id,
                        channel.issue_id,
                        channel.task_id,
                        channel.attempt_id,
                        channel.run_id,
                        channel.fencing_token,
                        channel.role,
                        channel.issuer_id,
                        channel.approved_provider,
                        channel.approved_model,
                        schedule.revision,
                        req_digest,
                        max_output_tokens,
                        sub_reservation_tokens,
                        now_iso,
                        now_iso,
                    ),
                )

        # Calculate bounded deadline outside DB transaction
        remaining_s = DEFAULT_PROVIDER_DEADLINE_S
        if channel.deadline_epoch > 0:
            rem = channel.deadline_epoch - time.time()
            if rem <= 0:
                self._mark_failed_or_uncertain(
                    channel, request_id, req_digest, reservation_id,
                    status="CANCELED_BEFORE_SEND" if not need_reconcile else "UNKNOWN_PROVIDER_EXECUTION",
                    error_category="BUDGET_EXHAUSTED",
                )
                raise BrokerError("BUDGET_EXHAUSTED", "Task deadline expired")
            remaining_s = min(DEFAULT_PROVIDER_DEADLINE_S, rem)

        # Step 3: Perform network/IPC call or reconcile duplicate SENDING
        try:
            if need_reconcile:
                outcome = self.transport.reconcile(
                    request_id=request_id,
                    provider_id=channel.approved_provider,
                    model_id=channel.approved_model,
                )
                if outcome is None:
                    self._mark_failed_or_uncertain(
                        channel, request_id, req_digest, reservation_id,
                        status="UNKNOWN_PROVIDER_EXECUTION",
                        error_category="UNKNOWN_PROVIDER_EXECUTION",
                    )
                    raise BrokerError(
                        "UNKNOWN_PROVIDER_EXECUTION",
                        "Duplicate SENDING request could not be reconciled; holding budget",
                    )
            else:
                outcome = self.transport.send(
                    request_id=request_id,
                    provider_id=channel.approved_provider,
                    model_id=channel.approved_model,
                    system_prompt=channel.role_system_prompt,
                    messages=messages,
                    max_output_tokens=max_output_tokens,
                    timeout_s=remaining_s,
                )
        except BrokerError:
            raise
        except TimeoutError as exc:
            self._mark_failed_or_uncertain(
                channel, request_id, req_digest, reservation_id,
                status="UNKNOWN_PROVIDER_EXECUTION",
                error_category="UNKNOWN_PROVIDER_EXECUTION",
            )
            raise BrokerError("UNKNOWN_PROVIDER_EXECUTION", "Provider call timed out after send") from exc
        except Exception as exc:
            self._mark_failed_or_uncertain(
                channel, request_id, req_digest, reservation_id,
                status="UNKNOWN_PROVIDER_EXECUTION",
                error_category="PROVIDER_UNAVAILABLE",
            )
            raise BrokerError("PROVIDER_UNAVAILABLE", f"Provider transport error: {exc}") from exc

        # Step 4: Bound stream chunks while reading and validate usage
        if outcome.status == "FAILED_CONFIRMED":
            self._mark_failed_or_uncertain(
                channel, request_id, req_digest, reservation_id,
                status="FAILED_CONFIRMED",
                error_category="PROVIDER_UNAVAILABLE",
            )
            raise BrokerError("PROVIDER_UNAVAILABLE", "Provider confirmed request failure without usage")

        if outcome.status != "SUCCEEDED":
            self._mark_failed_or_uncertain(
                channel, request_id, req_digest, reservation_id,
                status="UNKNOWN_PROVIDER_EXECUTION",
                error_category="UNKNOWN_PROVIDER_EXECUTION",
            )
            raise BrokerError("UNKNOWN_PROVIDER_EXECUTION", "Provider execution outcome uncertain")

        buf: list[str] = []
        total_bytes = 0
        for chunk in outcome.chunks:
            if not isinstance(chunk, str):
                self._mark_failed_or_uncertain(
                    channel, request_id, req_digest, reservation_id,
                    status="UNKNOWN_PROVIDER_EXECUTION",
                    error_category="UNKNOWN_PROVIDER_EXECUTION",
                )
                raise BrokerError("UNKNOWN_PROVIDER_EXECUTION", "Invalid non-text provider chunk")
            total_bytes += len(chunk.encode("utf-8"))
            if total_bytes > MAX_RESPONSE_BYTES:
                self._mark_failed_or_uncertain(
                    channel, request_id, req_digest, reservation_id,
                    status="UNKNOWN_PROVIDER_EXECUTION",
                    error_category="OUTPUT_LIMIT",
                )
                raise BrokerError("OUTPUT_LIMIT", "Provider response stream exceeded 16 KiB limit")
            buf.append(chunk)
        response_text = "".join(buf)

        in_tok = outcome.input_tokens
        out_tok = outcome.output_tokens
        if (
            type(in_tok) is not int or in_tok < 0
            or type(out_tok) is not int or out_tok < 0
            or (in_tok == 0 and out_tok == 0)
            or not isinstance(outcome.provider_call_id, str)
            or not outcome.provider_call_id.strip()
        ):
            self._mark_failed_or_uncertain(
                channel, request_id, req_digest, reservation_id,
                status="UNKNOWN_PROVIDER_EXECUTION",
                error_category="UNKNOWN_PROVIDER_EXECUTION",
            )
            raise BrokerError("UNKNOWN_PROVIDER_EXECUTION", "Missing or invalid integer usage from provider")

        # Step 5 & 6: Settle usage or escalate overspend without clamping
        total_actual_tokens = in_tok + out_tok
        cost_micros = schedule.compute_cost_micros(in_tok, out_tok)
        resp_digest = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
        receipt_id = f"brk_{secrets.token_hex(16)}"
        finished_iso = datetime.now(timezone.utc).isoformat()

        overspent = False
        with self.db.atomic_transaction() as conn:
            spent_row = conn.execute(
                """
                SELECT COALESCE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), 0) AS prior_spent
                FROM pm_coordinator_broker_requests
                WHERE attempt_id = ? AND status = 'SUCCEEDED' AND request_id != ?
                """,
                (channel.attempt_id, request_id),
            ).fetchone()
            cumulative_tokens = int(spent_row["prior_spent"]) + total_actual_tokens

            if total_actual_tokens > sub_reservation_tokens or cumulative_tokens > held_amount:
                # Never clamp real usage to a fabricated affordable amount!
                overspent = True
                channel.halted_by_overspend = True
                conn.execute(
                    """
                    UPDATE pm_coordinator_broker_requests
                    SET status = 'UNKNOWN_PROVIDER_EXECUTION',
                        provider_call_id = ?,
                        response_text = ?,
                        response_digest = ?,
                        input_tokens = ?,
                        output_tokens = ?,
                        cost_micros = ?,
                        receipt_id = ?,
                        error_category = 'BUDGET_EXHAUSTED',
                        updated_at = ?
                    WHERE request_id = ?
                    """,
                    (
                        outcome.provider_call_id,
                        response_text,
                        resp_digest,
                        in_tok,
                        out_tok,
                        cost_micros,
                        receipt_id,
                        finished_iso,
                        request_id,
                    ),
                )
                conn.execute(
                    """
                    UPDATE pm_coordinator_attempts
                    SET budget_tokens_spent = budget_tokens_spent + ?
                    WHERE attempt_id = ?
                    """,
                    (total_actual_tokens, channel.attempt_id),
                )
                esc_id = f"esc_{secrets.token_hex(12)}"
                conn.execute(
                    """
                    INSERT INTO pm_coordinator_escalations (
                        escalation_id, tenant_id, project_id, issue_id, task_id,
                        attempt_id, run_id, candidate_commit_sha, category,
                        decision_needed, evidence_json, held_liabilities, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'exhausted_attempts_time_budget', ?, ?, ?, 'OPEN', ?)
                    """,
                    (
                        esc_id,
                        channel.tenant_id,
                        channel.project_id,
                        channel.issue_id,
                        channel.task_id,
                        channel.attempt_id,
                        channel.run_id,
                        "Reconcile uncovered provider usage exceeding reserved ceiling",
                        canonical({
                            "request_id": request_id,
                            "actual_tokens": total_actual_tokens,
                            "reserved_ceiling": sub_reservation_tokens,
                            "cumulative_tokens": cumulative_tokens,
                            "attempt_held_amount": held_amount,
                        }),
                        total_actual_tokens,
                        finished_iso,
                    ),
                )
                self._record_audit(
                    conn,
                    {
                        "audit_id": f"aud_{secrets.token_hex(12)}",
                        "request_id": request_id,
                        "tenant_id": channel.tenant_id,
                        "project_id": channel.project_id,
                        "issue_id": channel.issue_id,
                        "task_id": channel.task_id,
                        "attempt_id": channel.attempt_id,
                        "run_id": channel.run_id,
                        "actor_id": channel.issuer_id,
                        "provider_id": channel.approved_provider,
                        "model_id": channel.approved_model,
                        "request_digest": req_digest,
                        "response_digest": resp_digest,
                        "input_tokens": in_tok,
                        "output_tokens": out_tok,
                        "cost_micros": cost_micros,
                        "reservation_id": reservation_id,
                        "settlement_id": None,
                        "error_category": "BUDGET_EXHAUSTED",
                        "created_at": finished_iso,
                    },
                )
            else:
                # Normal confirmed settlement within ceiling
                conn.execute(
                    """
                    UPDATE pm_coordinator_broker_requests
                    SET status = 'SUCCEEDED',
                        provider_call_id = ?,
                        response_text = ?,
                        response_digest = ?,
                        input_tokens = ?,
                        output_tokens = ?,
                        cost_micros = ?,
                        receipt_id = ?,
                        error_category = NULL,
                        updated_at = ?
                    WHERE request_id = ?
                    """,
                    (
                        outcome.provider_call_id,
                        response_text,
                        resp_digest,
                        in_tok,
                        out_tok,
                        cost_micros,
                        receipt_id,
                        finished_iso,
                        request_id,
                    ),
                )
                conn.execute(
                    """
                    UPDATE pm_coordinator_attempts
                    SET budget_tokens_spent = budget_tokens_spent + ?
                    WHERE attempt_id = ?
                    """,
                    (total_actual_tokens, channel.attempt_id),
                )
                conn.execute(
                    """
                    UPDATE pm_coordinator_loop_jobs
                    SET provider_calls_used = provider_calls_used + 1,
                        updated_at = ?
                    WHERE issue_id = ?
                    """,
                    (finished_iso, channel.issue_id),
                )
                self._record_audit(
                    conn,
                    {
                        "audit_id": f"aud_{secrets.token_hex(12)}",
                        "request_id": request_id,
                        "tenant_id": channel.tenant_id,
                        "project_id": channel.project_id,
                        "issue_id": channel.issue_id,
                        "task_id": channel.task_id,
                        "attempt_id": channel.attempt_id,
                        "run_id": channel.run_id,
                        "actor_id": channel.issuer_id,
                        "provider_id": channel.approved_provider,
                        "model_id": channel.approved_model,
                        "request_digest": req_digest,
                        "response_digest": resp_digest,
                        "input_tokens": in_tok,
                        "output_tokens": out_tok,
                        "cost_micros": cost_micros,
                        "reservation_id": reservation_id,
                        "settlement_id": receipt_id,
                        "error_category": None,
                        "created_at": finished_iso,
                    },
                )

        if overspent:
            raise BrokerError("BUDGET_EXHAUSTED", "Actual provider usage exceeded reserved ceiling; liability held")

        return {
            "schema": BROKER_SCHEMA,
            "request_id": request_id,
            "status": "SUCCEEDED",
            "provider_call_id": outcome.provider_call_id,
            "provider_id": channel.approved_provider,
            "model_id": channel.approved_model,
            "response_text": response_text,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "receipt_id": receipt_id,
        }

    def _mark_failed_or_uncertain(
        self,
        channel: BrokerChannelBinding,
        request_id: str,
        req_digest: str,
        reservation_id: str,
        *,
        status: str,
        error_category: str,
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self.db.atomic_transaction() as conn:
            conn.execute(
                """
                UPDATE pm_coordinator_broker_requests
                SET status = ?, error_category = ?, updated_at = ?
                WHERE request_id = ?
                """,
                (status, error_category, now_iso, request_id),
            )
            self._record_audit(
                conn,
                {
                    "audit_id": f"aud_{secrets.token_hex(12)}",
                    "request_id": request_id,
                    "tenant_id": channel.tenant_id,
                    "project_id": channel.project_id,
                    "issue_id": channel.issue_id,
                    "task_id": channel.task_id,
                    "attempt_id": channel.attempt_id,
                    "run_id": channel.run_id,
                    "actor_id": channel.issuer_id,
                    "provider_id": channel.approved_provider,
                    "model_id": channel.approved_model,
                    "request_digest": req_digest,
                    "response_digest": None,
                    "input_tokens": None,
                    "output_tokens": None,
                    "cost_micros": None,
                    "reservation_id": reservation_id,
                    "settlement_id": None,
                    "error_category": error_category,
                    "created_at": now_iso,
                },
            )


class MediatedIPCChannel:
    """Bounded line-delimited JSON IPC bridge between a guest process and the host ProviderBroker."""

    def __init__(self, broker: ProviderBroker, channel_id: str) -> None:
        self.broker = broker
        self.channel_id = channel_id

    def process_line(self, raw_line: bytes | str) -> bytes:
        """Processes a single JSON line from a guest and returns a canonical JSON line response."""
        try:
            resp = self.broker.handle_request(self.channel_id, raw_line)
            return (canonical(resp) + "\n").encode("utf-8")
        except BrokerError as exc:
            err_payload = {
                "schema": BROKER_SCHEMA,
                "status": "ERROR",
                "error_category": exc.category,
                "message": str(exc),
            }
            return (canonical(err_payload) + "\n").encode("utf-8")


__all__ = [
    "BROKER_SCHEMA",
    "BROKER_ERROR_CATEGORIES",
    "BrokerChannelBinding",
    "BrokerError",
    "MediatedIPCChannel",
    "PriceSchedule",
    "ProviderBroker",
    "ProviderTransport",
    "ProviderTransportOutcome",
    "migrate_live_loop",
    "validate_guest_broker_request",
]
