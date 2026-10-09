# Consolidation scope and consumer inventory

Regrouping baseline: `3311a4fa` (shared swarm/platform identity). Status: **A0 partial source inventory; deployment discovery and independent sign-off pending.**

This register distinguishes inspected code and development consumers from actual deployed services. No running application containers or dashboard were observed at regrouping. That observation does not prove that external consumers do not exist. Owner roles refer to engineering responsibilities, not assigned people.

## Entry points and authority

| Surface / source | Inspected consumers | Authority, effects and state | Disposition / owner |
| --- | --- | --- | --- |
| `mas.cli`, `mas.__main__`, `pyproject.toml` (`mas`, `mas-doctor`) | README quickstart; `scripts/run_quality_gate.sh`; CLI/evaluation tests | Local health and capability inspection; no production admission | Retain read-only / platform |
| `mas.swarm.cli` (`mas-swarm`, module invocation) | `scripts/evaluate_secure_swarm.py`, `scripts/verify_secure_swarm.py`, `tests/test_secure_swarm.py`, `tests/test_shared_swarm_identity.py` | Init/enroll/revoke/submit/run/status/cancel/recover/approve/export/backup/audit/provider-check; local signed authority or explicit platform IAM; provider billing, Docker workers and operator-selected export | Retain coding behavior, adapt contracts; historical cutover pending / platform + security |
| `main.py` | README demos; legacy dashboard launch | Local trusted demo bootstrap, template organization, configured host tools and provider; dispatch defaults staged | Retain labelled demonstrations outside consolidated admission / runtime |
| `mas.dashboard.server.DashboardRequestHandler` | `main.py`, `scripts/launch_portal.py`; portal/static UI | Shared dashboard token and trusted principal; broad legacy PM/dispatch/portal routes and configured host services | Keep single-tenant legacy surface separate; adapt or retire at P5 / platform |
| `mas.dashboard.server.TenantDashboardRequestHandler`, `mas.tenancy` | `tests/test_tenant_boundary.py`, `tests/test_durable_identity.py` | Server-resolved IAM tenant and private PM/workspace; current session checks; tenant PM effects | Retain tenant PM restrictions; common task admission pending / platform + data |
| `mas.mcp.protocol.MCPRegistry`, `mas.mcp.transport` | `scripts/mas_mcp_stdio.py`; tests and trusted Python clients | Legacy trusted-principal mode or explicit tenant IAM binding; registered tools/resources/prompts | Preserve explicit mode; no automatic broker admission / platform |
| `mas.audit_witness` | Anchor HTTP worker; `tests/test_external_audit_anchor.py` | Separate trusted operator enrollment and HTTPS checkpoint service; private witness database/key/token | Retain protocol; independent deployed service unconfigured / independent witness operator |
| Direct Python APIs, scripts and evaluation harness | Local tests, seeded work queue and scripted demos | Trusted host access, arbitrary configured tools, fixture or explicit live-model effects | Administrative/development scope only; never expose raw APIs as an admitted broker / capability owners |

The CLI subcommand list comes from `mas/swarm/cli.py:parser`; handler distinctions come from `mas/dashboard/server.py`. The migration map owns component disposition beyond these entry points.

## Capability and store domains

| Domain / sources | Store / credential owner | Effects and admission boundary |
| --- | --- | --- |
| Durable identity: `mas/iam.py`, `identity_store.py`, `platform/identity.py` | Private IAM SQLite and signing secret; issued session hashes/revocations | Shared authority only for explicitly bound consumers; protect private paths and reauthorize at effects. No OAuth or implicit historical migration. |
| Witness: `audit_anchor.py`, `audit_witness.py`, `anchor_http_worker.py` | Independent witness SQLite/key, namespace writer token and TLS trust | External HTTPS checkpoints qualify identity freshness only; swarm history is not externally anchored. Deployment/admin/restore independence remains unverified. |
| Coding: `swarm/store.py`, `runtime.py`, `contracts.py` | Signed schema-2 run/audit SQLite, private key, local credentials or platform binding; request-key table column | Three role proposals, bounded calls, measured worker verification and separate human approval. Preserve historical signature/state semantics. No automatic deployment. |
| Execution/provider: `swarm/worker.py`, `process.py`, `provider.py`, `provider_worker.py` | Trusted Docker socket; operator-owned image policy/provider settings/API credential | Worker processes and upstream billed calls; reservations can remain uncertain. Candidate code has no authority. Cleanup/reconciliation remains host-owned. |
| PM: `pm/db.py`, `fsm.py`, `guards.py`, `tools.py`, `git_queue.py` | Legacy PM SQLite or private tenant PM database; verdict/evidence keys | Board mutations, evidence/approval and queue/repository effects. PM-to-coding task adapter remains unimplemented. |
| Messages/orchestration: `core/*`, `orchestration/*`, `squad/*`, `organization/*` | Process-local context, events, caches and configured JSONL audit/checkpoints | Legacy routing/delegation is not the admitted tenant message broker. New shared message/operation contracts and routing limits remain required. |
| Memory/research: `memory/*`, `tools/knowledge_vault_tool.py`, `grounding.py` | Working context, episodic/comms SQLite, local research files and simulated vector service | Read/write/search/replay/retention require per-tenant qualification before admission; retrieved content cannot become authority. |
| Host/external tools: `tools/*`, `providers/*` | Trusted filesystem/Git/cloud/browser configuration and credentials | Git/GitOps, cloud data/storage, browsing and desktop effects require separate capability policy and live service evidence. Existing implementation is not blanket admission. |
| Packaging/observability: `config.py`, `audit.py`, `observability.py`, `capabilities.py`, CI, Dockerfile | Local logs/artifacts and configured runtime environment | Report scope truthfully; required audit/state effects remain transactional within each owner. Old image evidence does not qualify new candidates. |

## Development environment observations

Observed 9 October 2026: clean Acinonyx baseline and clean separate MAS research/reference repository; saved review evidence and multiple virtual environments; Docker daemon available but no application containers. `mas doctor` reports staged dispatch, sandbox and ACL enabled, legacy provider absent. Swarm provider/image variables and API-key binding are present; readiness observations are unknown and no new remote model call was made. No dashboard token, durable IAM path/key or anchor URL was configured in the inspected shell. VPN is not configured; startup HTTP policy specifies unrestricted proxy access and no TCP grants. No secret values are recorded here.

Existing `swarm-live` databases/reports are retained as private historical evidence. They are not migrated, enrolled or reopened as current platform authority. Keys and token files are never included in source/evidence bundles.

## Pilot envelope and unresolved discovery

The target remains an allowlisted supervised single-host coding/tenant-PM pilot with an independently administered HTTPS IAM witness. The present source milestone qualifies narrower fresh-store shared identity. Public hostile-code hosting, distributed execution, autonomous deployment, browser/desktop actions, general cloud data access and tenant-unaware memory/research remain excluded from consolidation admission.

Before A0 can be signed off, the deployment owner must enumerate actual HTTP/MCP/CLI consumers, tenant/subject mappings, running services, externally configured endpoints and credentials by alias, active tasks/leases, data volumes, retention and restore ownership. Source inspection and an idle development session cannot supply this evidence. Capture sanitized manifests; do not enumerate credential values. Before cutover assign accountable owners, specify resource/operational targets and review the disposition of each consumer.

Next source sequence: complete versioned task/lifecycle/message/capability/result/approval/audit definitions and compatibility fixtures (A1–A2), then qualify unified authority/migration/witness (A3–A5) before broader coordinator/broker and PM-to-coding admission. See [current status](MAS_CONSOLIDATION_STATUS.md) and [gate register](MAS_CONSOLIDATION_ACCEPTANCE.md).
