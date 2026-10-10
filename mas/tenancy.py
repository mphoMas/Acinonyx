"""Trusted request-local tenant bindings; never derive these from tool arguments."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path

from mas.iam import MultiTenantIAM, TenantContext
from mas.security import ExecutionContext


@dataclass(frozen=True)
class TenantBinding:
    iam: MultiTenantIAM
    identity: TenantContext
    workspace: Path
    database: Path

    def require(self, action: str) -> None:
        tenant = self.identity.tenant_id
        if not self.iam.authorize(self.identity, action, tenant, f"urn:mas:tenant:{tenant}:request"):
            raise PermissionError("Tenant authority unavailable or action denied")


_binding: ContextVar[TenantBinding | None] = ContextVar("mas_tenant_binding", default=None)


def current_binding() -> TenantBinding | None:
    return _binding.get()


def resolve_tenant_database_path(iam: MultiTenantIAM, tenant: str, root: Path | str) -> Path:
    """Resolves the trusted isolated database path for a tenant within root."""
    root_path = Path(root).resolve()
    state = Path(iam.get_isolated_sandbox_path(tenant, str(root_path / "state")))
    return state / "pm.db"


@contextmanager
def tenant_scope(iam: MultiTenantIAM, token: str | TenantContext, tenant: str, root: Path):
    if iam.database_path is not None and iam.database_path.is_relative_to((root / "workspaces").resolve()):
        raise PermissionError("Identity authority must be outside tenant workspaces")
    if isinstance(token, TenantContext):
        identity = token
    else:
        identity = iam.verify_token(token)
    if identity.tenant_id != tenant:
        raise PermissionError("Credential belongs to another tenant")
    workspace = Path(iam.get_isolated_sandbox_path(tenant, str(root / "workspaces")))
    db_path = resolve_tenant_database_path(iam, tenant, root)
    binding = TenantBinding(iam, identity, workspace, db_path)
    marker = _binding.set(binding)
    try:
        with ExecutionContext.scope(f"{tenant}:{identity.principal_id}"):
            yield binding
    finally:
        _binding.reset(marker)
