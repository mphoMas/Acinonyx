# Tenant boundary: authenticated PM and MCP pilot

This is an explicitly configured tenant boundary, not production approval for all MAS entry points. The default legacy dashboard and MCP registry remain single-tenant trusted-host interfaces. Do not expose those legacy interfaces to unrelated tenants.

## Supported boundary

A trusted host constructs `MCPRegistry` or `DashboardServer` with all three arguments: `iam`, `tenant_id`, and `tenant_root`. The tenant ID is server configuration; a request cannot select it. Use an absolute storage root owned by the coordinator. Configure a private persistent `MAS_IAM_SECRET` before starting services, and independently configure the private governance signing keys described in the revision review.

```python
from pathlib import Path
from mas.iam import MultiTenantIAM, StandardRole
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.pm.tools import register_pm_tools
from mas.tools.filesystem import register_filesystem_tools

# Trusted provisioning code only. Never give provisioning or IAM objects to agents.
iam = MultiTenantIAM(db_path=Path("/srv/mas-identity/iam.sqlite"))  # Requires MAS_IAM_SECRET.
# Enrollment is a one-time trusted operation. Do not overwrite roles on restart.
if iam.get_tenant("acme") is None:
    iam.create_tenant("acme", "Acme")
if iam.get_principal("acme", "operator") is None:
    iam.register_principal("acme", "operator", roles={StandardRole.TENANT_ADMIN.value})
credential = iam.issue_token("acme", "operator", ttl_seconds=3600)
registry = MCPRegistry(iam=iam, tenant_id="acme", tenant_root=Path("/srv/mas-tenants"))
register_filesystem_tools(registry)
register_pm_tools(registry)
client = MCPClient(registry, bearer_token=credential)
# await client.call_tool("pm_create_project", {"key": "CORE", "name": "Acme work"})
```

Deliver credentials through a secure channel; never log them. HTTP tenant mode uses the same bearer token format:

```python
from mas.dashboard.server import DashboardServer
from mas.organization.company import ConsultingEnterprise

server = DashboardServer(
    ConsultingEnterprise(), host="127.0.0.1", port=8080,
    iam=iam, tenant_id="acme", tenant_root=Path("/srv/mas-tenants"),
)
server.start_background()
```

HTTP tenant mode serves authenticated `/api/pm/` routes and the two identity revocation endpoints described below. It denies the shared portal, events, model gateway, enterprise dispatch and dashboard UI routes. Place a supported authenticated TLS gateway in front of a deployed API; this built-in server does not implement TLS. Supplying a legacy dashboard token does not authorize tenant requests. Provisioning remains a trusted host operation, not an HTTP enrollment endpoint.

## Enforcement

- Credentials establish tenant and principal. Claimed principals cannot replace authenticated identity. Principal names used by PM are qualified as `tenant:user`.
- Authorization uses contexts issued by this IAM verifier and rechecks current tenant status, principal existence, expiration and permission reductions. Copied or constructed context objects confer no authority. Repeated verification of one token does not invalidate concurrent requests.
- Request-local context variables carry identity without changing process-global filesystem roots or the global PM database singleton.
- Tenant workspaces live under `<root>/workspaces/tenants/<tenant>`; separate PM databases live under `<root>/state/tenants/<tenant>/pm.db`. Equal project/issue keys can coexist independently. Foreign cached database objects are rejected inside tenant requests.
- Filesystem read/write/list tools use the current workspace. File operations walk directory descriptors with `O_NOFOLLOW`, preventing symlink replacement between validation and open. Directory listings do not follow symlinks.
- Python execution mounts only the current workspace, excludes PM state, strips the child environment and requires both execution and storage-write authority. Bubblewrap remains mandatory even if legacy sandbox configuration is disabled; missing or unsupported isolation refuses execution.
- Tenant dispatch supports `fs_read`, `fs_write`, `fs_list`, the registered PM tools, and `run_python` when explicitly registered. Other tool names, recursive glob, resources and prompts are denied. Model, Git, browser, cloud-data and delegation tools require separate tenant implementations before admission.
- Synchronous tenant-registry `call_tool` is denied. Use authenticated request dispatch or `MCPClient(..., bearer_token=...)`.

## Deployment limits

Durable IAM is available with `MultiTenantIAM(..., db_path=...)` or `MAS_IAM_DB_PATH` plus `MAS_IAM_SECRET`. It restores tenants, principals, issued sessions and revocations from a private SQLite authority. Omitting the database path preserves the process-local development mode. See [identity storage and recovery](DURABLE_IDENTITY.md) for enrollment, revocation, concurrency and backup rules. The supported durable store is a single-host POSIX filesystem implementation, not a distributed identity provider.

The coordinator, its Python code, configuration and storage parent directories are trusted. This is not a boundary against malicious host code, privileged host users or a compromised kernel. SQLite access outside tenant request scope is a trusted internal API. Do not run unrelated tenant workloads through legacy orchestration, shared memory or the general model gateway. The supervised swarm has its own separately verified store boundary.

Do not enable shared enterprise routes by extending a string allowlist. Each admitted handler must demonstrate its storage, credentials, state, cancellation, audit and resource ownership under tenant context. The PM pilot does not settle verifier-issued release evidence, external audit anchoring, multi-host recovery or production load assurance.
