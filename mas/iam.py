"""
mas.iam: Enterprise Multi-Tenant Identity & Access Management (IAM)
Implements Policy-Based Access Control (PBAC), Role-Based Access Control (RBAC),
cryptographic token authentication, and strict multi-tenant boundary isolation.

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
from weakref import WeakValueDictionary
from dataclasses import dataclass, field
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
    Enterprise-grade multi-tenant IAM engine enforcing:
    1. Tenant lifecycle and isolation boundaries.
    2. Signed HMAC token issuance and verification (OAuth/PAB pattern).
    3. Fine-grained RBAC/PBAC action and resource authorization.
    4. Filesystem workspace jailing per tenant.
    """

    def __init__(self, signing_secret: Optional[str] = None) -> None:
        import secrets
        # Unconfigured local instances are intentionally process-local. Durable
        # deployments must supply MAS_IAM_SECRET or an explicit private key.
        key = signing_secret if signing_secret is not None else os.getenv("MAS_IAM_SECRET")
        if key is None:
            key = secrets.token_hex(32)
        if len(key.encode("utf-8")) < 32:
            raise ValueError("IAM signing key must contain at least 32 bytes")
        self.signing_secret = key.encode("utf-8")
        self._contexts = WeakValueDictionary()
        self._tenants: Dict[str, Tenant] = {}
        self._principals: Dict[str, Principal] = {}  # key: f"{tenant_id}:{user_id}"
        self._custom_policies: Dict[str, List[PolicyRule]] = {}  # key: tenant_id

        # Standard default role permissions mapping
        self._role_permissions: Dict[str, Set[str]] = {
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
        if tenant_id in self._tenants:
            raise ValueError(f"Tenant '{tenant_id}' already exists.")

        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            status=TenantStatus.ACTIVE,
            allowed_scopes=allowed_scopes or {"default"},
            metadata=metadata or {},
        )
        self._tenants[tenant_id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def suspend_tenant(self, tenant_id: str) -> None:
        if tenant_id in self._tenants:
            self._tenants[tenant_id].status = TenantStatus.SUSPENDED

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
            roles=roles or {StandardRole.READ_ONLY.value},
            scopes=scopes or set(),
            email=email,
        )
        self._principals[key] = principal
        return principal

    def get_principal(self, tenant_id: str, user_id: str) -> Optional[Principal]:
        return self._principals.get(f"{tenant_id}:{user_id}")

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
            "nonce": base64.b64encode(os.urandom(8)).decode("ascii"),
        }

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii").rstrip("=")
        signature = hmac.new(self.signing_secret, payload_b64.encode("ascii"), hashlib.sha256).hexdigest()

        return f"{payload_b64}.{signature}"

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
        tenant = self.get_tenant(context.tenant_id)
        principal = self.get_principal(context.tenant_id, context.principal_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE or not principal:
            return False
        if not resource_urn.startswith(f"urn:mas:tenant:{resource_tenant_id}:"):
            return False
        # Hard Rule 1: Multi-tenant boundary isolation
        if context.tenant_id != resource_tenant_id:
            return False

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
