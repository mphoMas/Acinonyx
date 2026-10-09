# MAS consolidation implementation status

Baseline: `645067c673f4221cfcaf8959a49be266ea38911d`. Scope: first contract/compatibility slice; P0 and P2 are **in progress**, not complete. Design: [ADR](MAS_CONSOLIDATION_ADR.md), [migration map](MAS_CONSOLIDATION_MIGRATION.md), [acceptance gates](MAS_CONSOLIDATION_ACCEPTANCE.md).

## Shared identity slice

Explicitly platform-bound stores now use durable platform IAM sessions with dedicated owner/requester/approver permissions, a persisted signed authority binding and IAM-before-swarm transaction guard. The same session is exercised through tenant-bound PM MCP and the coding swarm; revocation blocks both. See [shared identity design and recovery](SHARED_SWARM_IDENTITY.md). Existing local stores are not automatically migrated; witness activation and a reviewed historical import remain pending. P1 is in progress, not complete.

## Implemented first slice

`mas/platform/contracts.py` defines strict, immutable version-one `TaskIdentity`, `CaseOutcome` and `VerificationEvidence` models. They reject unknown fields, unsupported versions, malformed identifiers/hashes, inconsistent pass/status claims, duplicate/empty/excessive case sets and non-finite timestamps. The JSON boundary rejects duplicate keys, non-finite constants and documents over 64 KiB. The workflow identifier is deliberately restricted to `coding.solve.v1`; no arbitrary adapter admission exists.

`mas/platform/coding.py` bridges existing trusted coding run data into those contracts. `CodingSwarm._pipeline` validates observed results before recording rejection/review evidence. Exact run/provider, source hash, suite hash, executor image and ordered case IDs must match the host-owned run. Task tenant and attempt come from the authenticated store document, not agent messages. Validation checks consistency; it does not authenticate arbitrary JSON or confer authority.

The bridge returns existing evidence unchanged. Swarm storage remains schema 2; signatures, state machine, role checks, private test expectations and separate human approval remain enforced by their existing owners. No new network endpoint, unrestricted worker, credential migration or automatic deployment is introduced. Shared contract validation supplements existing Store provenance/approval checks; it does not replace them.

Concrete task, message, capability, approval, audit and general execution schemas remain to be specified/implemented beyond this deliberately small evidence slice. The current task identity is not a complete Task contract. Do not interpret this module as a completed common coordinator or broker.

## Inspected control-plane inventory

This inventory covers identified executable surfaces and state owners. It is not a completed consumer/data migration inventory; deployment consumers and actual configured external services require discovery before cutover.

| Surface | Current authority / side effects | Consolidation boundary |
| --- | --- | --- |
| `mas`, `mas-doctor`, `python -m mas` | Health/capabilities CLI; configuration and local health inspection | Keep read-only scope; report admitted adapters truthfully. |
| `mas-swarm`, `python -m mas.swarm.cli` | Separate local hashed credentials and signed SQLite schema-2 store; model requests, Docker workers, backups, approved file export | First shared evidence bridge only; shared IAM pending. Local enrollment/init are trusted operator actions. |
| `main.py` demos | Configured legacy providers/tools/organization and template modes | Demo paths cannot supply production verification evidence; no consolidation admission. |
| `DashboardServer` legacy handler | Broad dashboard/portal/dispatch/PM routes and configured host services | Do not route it into shared platform implicitly. Enumerate callers and retire/adapt bypass routes in P5. |
| Tenant-bound dashboard handler | Durable platform IAM, server-resolved tenant workspace and private tenant PM SQLite; PM mutations and session revocation | Retain tested tenant PM restrictions; common task/broker adapter pending. |
| `MCPRegistry.handle_request` and in-memory MCP client | Legacy trusted-principal mode or explicit tenant IAM binding; tool/resource/prompt access | Admission must preserve actual server-resolved identity; no caller-selected downgrade. Shared broker pending. |
| `python -m mas.audit_witness` | Independent private SQLite and key; OS-admin namespace enrollment or TLS checkpoint service | Identity authority only; independent production host is still unconfigured. No agent provisioning endpoint. |
| Direct Python APIs / evaluation and acceptance scripts | Trusted local administrator code; evaluations can start workers or invoke configured live models | Not remote capability endpoints; preserve explicit fixture/live distinction and side-effect scope. |

| Store / credential owner | Current semantics | Migration requirement |
| --- | --- | --- |
| Platform IAM (`MAS_IAM_DB_PATH`, private `MAS_IAM_SECRET`) | Signed SQLite identity history, session hashes/revocation; optional fixed HTTPS namespace binding | Preserve private authority outside workspaces; no stale restore or secret transfer through artifacts. |
| Witness (`--database`, private key/token files) | Separate signing key, hashed namespace writer; forward-only head | Independent administrators and restore boundary required; cannot rewind to fit restored coordinator. |
| Swarm CLI private state/key/token files | Signed run/audit history, hashed role credentials, provider usage reservations and exact approval | Explicit tenant/subject/role mapping, reissued sessions and provenance manifests; do not copy tokens into IAM. |
| PM SQLite (`mas/pm/db.py`) | Legacy configurable DB or tenant-bound private per-tenant state | One writer and explicit versioned task/operation mapping on cutover. |
| Working/episodic/comms/vector memory | In-memory context, SQLite reflection/trajectory/comms stores or configured adapter namespaces; not universally tenant-admitted | Ownership/query/replay/retention contracts before migration; no blanket cloud-service evidence. |
| Audit/events/artifacts and caches | Separate legacy JSONL/event state and workflow-specific signed history | Define stream ownership, redaction, retention and replay policy; witness does not automatically anchor these. |
| Provider configuration (`MAS_SWARM_API_KEY`, provider-specific environment settings) | Trusted provider adapters; upstream billed effects; model outputs untrusted | Secrets stay in operator settings; usage uncertainty and cancellation need common accounting contracts. |
| Docker socket / host tools / Git and external services | Trusted host authority and potentially irreversible effects | Inventory actual configured credentials and destinations; broker approval/effect reconciliation before admission. |

## Next implementation sequence

1. Complete P0 caller/effect inventory and versioned task/message/capability/approval/audit contracts, including migration fixtures and resource ceilings. This slice supplies evidence contract requirements, not all of A0–A2.
2. The explicit swarm-to-platform identity adapter is implemented for new platform-bound state. Complete reviewed identity/history mapping and credential reissue for existing deployments; keep their legacy credentials confined to the isolated old path until cutover.
3. Extract shared lifecycle/budget/capability controls, preserving coding adapter behavior and signed storage compatibility. Qualify cancellation/revocation at active effect boundaries.
4. Admit the first PM-to-coding vertical slice. Gate memory/research and every additional interface independently.

Verification and the architect verdict are in the [first-slice review](../reviews/CONSOLIDATION_CONTRACT_REVIEW.md). No consolidation gate is marked complete merely because these contracts exist.
