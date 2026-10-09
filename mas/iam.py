"""
mas.iam: Local tenant identity and role/scope authorization.
HMAC bearer sessions with optional durable SQLite identity and revocation state.
This is not an OAuth server or a general policy-engine implementation.

Architect: Acinonyx / Enterprise Security Directorate
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
import math
import sqlite3
from weakref import WeakValueDictionary
from dataclasses import dataclass, field, asdict
from pathlib import Path
from mas.identity_store import IdentityStore
from mas.audit_anchor import HTTPAuditAnchor
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TenantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class PolicyEffect(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class StandardRole(str, Enum):
    TENANT_ADMIN = "tenant_admin"
    SECURITY_AUDITOR = "security_auditor"
    DATA_ARCHITECT = "data_architect"
    ML_ENGINEER = "ml_engineer"
    ANALYTICS_ENGINEER = "analytics_engineer"
    OPERATOR = "operator"
    READ_ONLY = "read_only"
    SWARM_OWNER = "swarm_owner"
    SWARM_REQUESTER = "swarm_requester"
    SWARM_APPROVER = "swarm_approver"


@dataclass
class Tenant:
    tenant_id: str
    name: str
    status: TenantStatus = TenantStatus.ACTIVE
    allowed_scopes: Set[str] = field(default_factory=set)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Principal:
    user_id: str
    tenant_id: str
    roles: Set[str] = field(default_factory=set)
    scopes: Set[str] = field(default_factory=set)
    email: Optional[str] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class PolicyRule:
    effect: PolicyEffect
    actions: List[str]  # e.g., ["tools:*", "storage:read", "models:invoke"]
    resources: List[str]  # e.g., ["urn:mas:tenant:*:workspace", "urn:mas:tenant:acme:data:*"]


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    principal_id: str
    roles: Set[str]
    scopes: Set[str]
    token_id: str
    expires_at: float


class MultiTenantIAM:
    """
    Local tenant IAM engine enforcing:
    1. Tenant lifecycle and isolation boundaries.
    2. Issued HMAC bearer sessions and current revocation checks.
    3. Role/scope actions and tenant resource ownership.
    4. Filesystem workspace jailing per tenant.
    """

    def __init__(self, signing_secret: Optional[str] = None, *, db_path: Optional[str | Path] = None, anchor: Optional[HTTPAuditAnchor] = None) -> None:
        import secrets
        # Unconfigured local instances are intentionally process-local. Durable
        # deployments must supply MAS_IAM_SECRET or an explicit private key.
        key = signing_secret if signing_secret is not None else os.getenv("MAS_IAM_SECRET")
        path = db_path if db_path is not None else os.getenv("MAS_IAM_DB_PATH")
        if path is not None and key is None:
            raise ValueError("Durable IAM requires a configured private signing key")
        if key is None:
            key = secrets.token_hex(32)
        if len(key.encode("utf-8")) < 32:
            raise ValueError("IAM signing key must contain at least 32 bytes")
        self.signing_secret = key.encode("utf-8")
        configured = [os.getenv(name) for name in ("MAS_IAM_ANCHOR_URL", "MAS_IAM_ANCHOR_NAMESPACE", "MAS_IAM_ANCHOR_TOKEN")]
        if anchor is None and any(value is not None for value in configured):
            if not all(configured):
                raise ValueError("External audit anchor requires URL, namespace and bearer credential")
            anchor = HTTPAuditAnchor(*configured)
        if anchor is not None and path is None:
            raise ValueError("External audit anchoring requires durable identity storage")
        self._store = IdentityStore(path, self.signing_secret, anchor=anchor) if path is not None else None
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._contexts = WeakValueDictionary()
        self._tenants: Dict[str, Tenant] = {}
        self._principals: Dict[str, Principal] = {}  # key: f"{tenant_id}:{user_id}"
        self._custom_policies: Dict[str, List[PolicyRule]] = {}  # key: tenant_id

        # Standard default role permissions mapping
        self._role_permissions: Dict[str, Set[str]] = {
            StandardRole.SWARM_OWNER.value: {"swarm:owner", "swarm:request", "swarm:approve"},
            StandardRole.SWARM_REQUESTER.value: {"swarm:request"},
            StandardRole.SWARM_APPROVER.value: {"swarm:approve"},
            StandardRole.TENANT_ADMIN.value: {
                "tools:*",
                "storage:*",
                "models:*",
                "agents:*",
                "audit:*",
                "admin:*",
            },
            StandardRole.DATA_ARCHITECT.value: {
                "tools:read",
                "tools:execute",
                "storage:read",
                "storage:write",
                "models:invoke",
                "agents:dispatch",
            },
            StandardRole.ML_ENGINEER.value: {
                "tools:read",
                "tools:execute",
                "storage:read",
                "storage:write",
                "models:invoke",
                "models:train",
            },
            StandardRole.SECURITY_AUDITOR.value: {
                "tools:read",
                "storage:read",
                "audit:read",
                "audit:export",
            },
            StandardRole.READ_ONLY.value: {
                "tools:read",
                "storage:read",
                "audit:read",
            },
            StandardRole.OPERATOR.value: {
                "tools:read",
                "tools:execute",
                "storage:read",
                "agents:dispatch",
            },
        }

    def audit_checkpoint(self) -> Dict[str, Any]:
        """Trusted non-secret checkpoint export for reviewed witness enrollment."""
        if not self._store:
            raise ValueError("Checkpoint export requires durable identity storage")
        return self._store.export_checkpoint()

    @property
    def database_path(self) -> Optional[Path]:
        """Non-secret host storage location, never mounted into a tenant worker."""
        return self._store.path if self._store else None

    # -------------------------------------------------------------------------
    # Tenant Management
    # -------------------------------------------------------------------------

    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        allowed_scopes: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tenant:
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", tenant_id):
            raise ValueError(f"Invalid tenant_id '{tenant_id}'. Must be alphanumeric with '-' or '_'.")
        if self.get_tenant(tenant_id):
            raise ValueError(f"Tenant '{tenant_id}' already exists.")

        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            status=TenantStatus.ACTIVE,
            allowed_scopes=set(allowed_scopes) if allowed_scopes is not None else {"default"},
            metadata=metadata or {},
        )
        if self._store:
            document = asdict(tenant)
            document["status"] = tenant.status.value
            document["allowed_scopes"] = sorted(tenant.allowed_scopes)
            self._store.create_tenant(document)
        else:
            self._tenants[tenant_id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        if self._store:
            document = self._store.get("tenant", tenant_id)
            if document:
                document["status"] = TenantStatus(document["status"])
                document["allowed_scopes"] = set(document["allowed_scopes"])
                return Tenant(**document)
            return None
        return self._tenants.get(tenant_id)

    def suspend_tenant(self, tenant_id: str) -> None:
        if self._store:
            self._store.suspend_tenant(tenant_id)
        elif tenant_id in self._tenants:
            self._tenants[tenant_id].status = TenantStatus.SUSPENDED
            for session in self._sessions.values():
                if session["tenant_id"] == tenant_id:
                    session["revoked"] = True

    # -------------------------------------------------------------------------
    # Principal Management
    # -------------------------------------------------------------------------

    def register_principal(
        self,
        tenant_id: str,
        user_id: str,
        roles: Optional[Set[str]] = None,
        scopes: Optional[Set[str]] = None,
        email: Optional[str] = None,
    ) -> Principal:
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Cannot register principal. Tenant '{tenant_id}' not found.")
        if tenant.status != TenantStatus.ACTIVE:
            raise PermissionError(f"Tenant '{tenant_id}' is not ACTIVE ({tenant.status.value}).")

        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", user_id):
            raise ValueError("Invalid user_id")
        key = f"{tenant_id}:{user_id}"
        principal = Principal(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=set(roles) if roles is not None else {StandardRole.READ_ONLY.value},
            scopes=set(scopes) if scopes is not None else set(),
            email=email,
        )
        if self._store:
            document = asdict(principal)
            document["roles"] = sorted(principal.roles)
            document["scopes"] = sorted(principal.scopes)
            self._store.register_principal(document)
        else:
            for session in self._sessions.values():
                if session["tenant_id"] == tenant_id and session["user_id"] == user_id:
                    session["revoked"] = True
            self._principals[key] = principal
        return principal

    def get_principal(self, tenant_id: str, user_id: str) -> Optional[Principal]:
        if self._store:
            document = self._store.get("principal", f"{tenant_id}:{user_id}")
            return self._principal_from_document(document) if document else None
        return self._principals.get(f"{tenant_id}:{user_id}")

    @staticmethod
    def _principal_from_document(document):
        return Principal(**{**document, "roles": set(document["roles"]), "scopes": set(document["scopes"])})

    # -------------------------------------------------------------------------
    # Cryptographic Token Issuance & Verification (OAuth / Bearer)
    # -------------------------------------------------------------------------

    def issue_token(
        self,
        tenant_id: str,
        user_id: str,
        ttl_seconds: int = 3600,
    ) -> str:
        principal = self.get_principal(tenant_id, user_id)
        if not principal:
            raise ValueError(f"Principal '{user_id}' in tenant '{tenant_id}' does not exist.")

        tenant = self.get_tenant(tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            raise PermissionError("Tenant is inactive")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, (int, float)) or not math.isfinite(ttl_seconds):
            raise ValueError("Token lifetime must be finite")
        now = time.time()
        payload = {
            "tid": tenant_id,
            "uid": user_id,
            "roles": list(principal.roles),
            "scopes": list(principal.scopes),
            "iat": now,
            "exp": now + ttl_seconds,
            "nonce": os.urandom(32).hex(),
        }

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        signature = hmac.new(self.signing_secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()

        token = f"{payload_b64}.{signature}"
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if self._store:
            self._store.issue_session(payload, token_hash)
        else:
            self._sessions[payload["nonce"]] = {"tenant_id": tenant_id, "user_id": user_id, "expires": payload["exp"], "token_hash": token_hash, "revoked": False}
        return token

    def verify_token(self, token: str) -> TenantContext:
        if not isinstance(token, str) or len(token) > 16384 or not token.isascii():
            raise PermissionError("Malformed IAM token format.")
        parts = token.split(".")
        if len(parts) != 2:
            raise PermissionError("Malformed IAM token format.")

        payload_b64, signature = parts
        expected_sig = hmac.new(self.signing_secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            raise PermissionError("Invalid cryptographic token signature.")

        # Add base64 padding back if stripped
        padded_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
        try:
            payload = json.loads(base64.urlsafe_b64decode(padded_b64).decode("utf-8"))
        except Exception as e:
            raise PermissionError(f"Corrupted token payload: {e}")

        now = time.time()
        if not isinstance(payload, dict):
            raise PermissionError("Malformed token claims")
        expiry = payload.get("exp")
        if isinstance(expiry, bool) or not isinstance(expiry, (int, float)) or not math.isfinite(expiry):
            raise PermissionError("Malformed token expiration")
        if now >= expiry:
            raise PermissionError("Token has expired.")

        tenant_id = payload.get("tid", "")
        if not isinstance(tenant_id, str) or not isinstance(payload.get("uid"), str):
            raise PermissionError("Malformed tenant identity")
        tenant = self.get_tenant(tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            raise PermissionError(f"Tenant '{tenant_id}' is inactive or does not exist.")

        if not isinstance(payload.get("nonce"), str) or not payload["nonce"]:
            raise PermissionError("Malformed token nonce")
        principal = self.get_principal(tenant_id, payload["uid"])
        if principal is None:
            raise PermissionError("Principal no longer exists")
        if any(not isinstance(payload.get(key), list) or any(not isinstance(value, str) for value in payload[key]) for key in ("roles", "scopes")):
            raise PermissionError("Malformed token permissions")
        if self._store:
            document = self._store.authority(tenant_id, payload["uid"], payload["nonce"], token_hash=hashlib.sha256(token.encode()).hexdigest(), expires=expiry)
            principal = self._principal_from_document(document)
        else:
            self._check_session(tenant_id, payload["uid"], payload["nonce"], expiry, hashlib.sha256(token.encode()).hexdigest())
        context = TenantContext(
            tenant_id=tenant_id,
            principal_id=payload.get("uid", ""),
            roles=frozenset(payload["roles"]) & frozenset(principal.roles),
            scopes=frozenset(payload["scopes"]) & frozenset(principal.scopes),
            token_id=payload.get("nonce", ""),
            expires_at=expiry,
        )
        self._contexts[id(context)] = context
        return context

    def _check_session(self, tenant, user, sid, expiry, token_hash=None):
        session = self._sessions.get(sid)
        if not session or session["tenant_id"] != tenant or session["user_id"] != user or session["revoked"] or session["expires"] <= time.time() or session["expires"] != expiry:
            raise PermissionError("Session expired, revoked or unavailable")
        if token_hash is not None and not hmac.compare_digest(session["token_hash"], token_hash):
            raise PermissionError("Token does not match issued session")

    def revoke_session(self, actor_token: str, session_id: str) -> bool:
        """Revoke your own session, or a session in your tenant with admin authority."""
        if not isinstance(session_id, str) or not re.fullmatch(r"[a-f0-9]{64}", session_id):
            raise ValueError("Invalid session identifier")
        actor = self.verify_token(actor_token)
        if session_id != actor.token_id and not self.authorize(actor, "admin:revoke", actor.tenant_id, f"urn:mas:tenant:{actor.tenant_id}:session"):
            raise PermissionError("Session revocation requires tenant admin authority")
        if self._store:
            return self._store.revoke_session(actor, session_id, lambda doc: self._has_permission(actor, self._principal_from_document(doc), "admin:revoke"))
        session = self._sessions.get(session_id)
        if not session or session["tenant_id"] != actor.tenant_id:
            raise PermissionError("Session unavailable in this tenant")
        session["revoked"] = True
        return True

    def revoke_principal_sessions(self, actor_token: str, user_id: str) -> int:
        """Tenant administrator revokes every current session for one principal."""
        if not isinstance(user_id, str) or not re.fullmatch(r"[a-zA-Z0-9_\-]+", user_id):
            raise ValueError("Invalid user_id")
        actor = self.verify_token(actor_token)
        if not self.authorize(actor, "admin:revoke", actor.tenant_id, f"urn:mas:tenant:{actor.tenant_id}:session"):
            raise PermissionError("Session revocation requires tenant admin authority")
        if self._store:
            return self._store.revoke_principal_sessions(actor, user_id, lambda doc: self._has_permission(actor, self._principal_from_document(doc), "admin:revoke"))
        if not self.get_principal(actor.tenant_id, user_id):
            raise PermissionError("Principal unavailable in this tenant")
        count = 0
        for session in self._sessions.values():
            if session["tenant_id"] == actor.tenant_id and session["user_id"] == user_id and not session["revoked"]:
                session["revoked"] = True
                count += 1
        return count

    def invalidate_all_sessions(self) -> int:
        """Trusted host restore operation, while request servers are offline.

        This is deliberately unavailable through HTTP and agent tool registries.
        """
        if self._store:
            return self._store.invalidate_all_sessions()
        count = 0
        for session in self._sessions.values():
            if not session["revoked"]:
                session["revoked"] = True
                count += 1
        return count

    def backup(self, destination: str | Path) -> None:
        """Trusted host administrator only; never expose this as an agent tool."""
        if not self._store:
            raise ValueError("Backup requires durable identity storage")
        self._store.backup(destination)

    # -------------------------------------------------------------------------
    # Policy-Based Authorization Engine (PAB)
    # -------------------------------------------------------------------------

    def authorize(
        self,
        context: TenantContext,
        action: str,
        resource_tenant_id: str,
        resource_urn: str,
    ) -> bool:
        """
        Enforces tenant isolation and action authorization:
        1. Context tenant must match target resource tenant (No cross-tenant bleed).
        2. Context must possess matching scope or role permission.
        """
        # Only this verifier may establish authority; recheck current lifecycle
        # and permissions on every action, including already-running requests.
        if self._contexts.get(id(context)) is not context or time.time() >= context.expires_at:
            return False
        try:
            if self._store:
                document = self._store.authority(context.tenant_id, context.principal_id, context.token_id, expires=context.expires_at)
                principal = self._principal_from_document(document)
                tenant = None  # The store checks tenant status in the same snapshot.
            else:
                self._check_session(context.tenant_id, context.principal_id, context.token_id, context.expires_at)
                tenant = self.get_tenant(context.tenant_id)
                principal = self.get_principal(context.tenant_id, context.principal_id)
        except (PermissionError, OSError, sqlite3.Error):
            return False
        if (not self._store and (not tenant or tenant.status != TenantStatus.ACTIVE)) or not principal:
            return False
        if not resource_urn.startswith(f"urn:mas:tenant:{resource_tenant_id}:"):
            return False
        # Hard Rule 1: Multi-tenant boundary isolation
        if context.tenant_id != resource_tenant_id:
            return False

        return self._has_permission(context, principal, action)

    def _has_permission(self, context: TenantContext, principal: Principal, action: str) -> bool:
        # Gather all permissions from assigned roles
        all_perms: Set[str] = set(context.scopes) & principal.scopes
        for role in context.roles & principal.roles:
            role_perms = self._role_permissions.get(role, set())
            all_perms.update(role_perms)

        # Check action match
        for perm in all_perms:
            if perm == "*":
                return True
            if perm.endswith(":*"):
                prefix = perm[:-2]
                if action.startswith(prefix + ":") or action == prefix:
                    return True
            if perm == action:
                return True

        return False

    # -------------------------------------------------------------------------
    # Workspace & Filesystem Jail Isolation
    # -------------------------------------------------------------------------

    def get_isolated_sandbox_path(self, tenant_id: str, base_workspace: str) -> str:
        """
        Returns a canonical isolated directory for the tenant.
        Prevents directory traversal (e.g. '../') and ensures the folder exists.
        """
        if not re.fullmatch(r"[a-zA-Z0-9_\-]+", tenant_id):
            raise ValueError(f"Dangerous tenant_id containing invalid characters: '{tenant_id}'")

        from pathlib import Path
        clean_base = Path(base_workspace).resolve()
        container = clean_base / "tenants"
        tenant_path = container / tenant_id
        # Never follow a pre-existing symlink into another tenant or host path.
        if container.is_symlink() or tenant_path.is_symlink():
            raise PermissionError("Tenant workspace cannot be a symlink")
        tenant_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if tenant_path.resolve() != tenant_path:
            raise PermissionError("Tenant workspace escaped its configured root")
        return str(tenant_path)



# Global default instance for runtime access
default_iam = MultiTenantIAM()
