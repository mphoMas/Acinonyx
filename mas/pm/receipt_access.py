"""Trusted startup policy for the single-process quarantined receipt service."""
from dataclasses import dataclass

from mas.pm.gateway.models import ConnectorRegistry


@dataclass(frozen=True)
class ReceiptAccess:
    connector_registry: ConnectorRegistry | None = None
    connector_key: tuple[str, str] | None = None
    tenant_id: str | None = None
    project_id: str | None = None
    trusted_local: bool = False

    def __post_init__(self):
        if type(self.trusted_local) is not bool:
            raise ValueError("Explicit receipt access profile required")
        if self.trusted_local:
            if any(value is not None for value in (self.connector_registry, self.connector_key, self.tenant_id, self.project_id)):
                raise ValueError("Trusted-local and connector profiles cannot be combined")
        elif (not isinstance(self.connector_registry, ConnectorRegistry)
              or not isinstance(self.connector_key, tuple) or len(self.connector_key) != 2
              or any(not isinstance(v, str) or not v.isascii() or not v.isdigit() or len(v) > 64 for v in self.connector_key)
              or not isinstance(self.tenant_id, str) or not self.tenant_id
              or not isinstance(self.project_id, str) or not self.project_id):
            raise ValueError("Connector receipts require a supported registry and server-owned repository/tenant/project binding")

    def require(self, tenant_id, *, project_id=None, payload=None):
        """Call inside the shared authority guard, on every read and write."""
        if self.trusted_local:
            return
        snapshot = self.connector_registry.get_snapshot(self.connector_key)
        if (snapshot is None or snapshot.status != "ACTIVE"
                or (snapshot.repository_id, snapshot.repository_owner_id) != self.connector_key):
            raise PermissionError("Connector policy is not registered or not active")
        if (tenant_id != self.tenant_id or snapshot.tenant_id != self.tenant_id
                or snapshot.project_id != self.project_id
                or (project_id is not None and project_id != self.project_id)):
            raise PermissionError("Connector ownership does not match configured tenant/project")
        if payload is not None:
            claims = payload["transport_claims"]
            if (claims["repository_id"], claims["repository_owner_id"]) != self.connector_key:
                raise PermissionError("Transport claims do not match configured connector")
