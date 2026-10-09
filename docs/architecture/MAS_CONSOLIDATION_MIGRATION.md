# MAS consolidation component migration map

Status: **DRAFT; no migration completed by this document.** Baseline: `119ca57ac000058f485dc1a33f62aafd722a3931`.
Design authority: [ADR](MAS_CONSOLIDATION_ADR.md). Admission evidence: [checklist](MAS_CONSOLIDATION_ACCEPTANCE.md).
Owner roles below are proposed responsibilities, not claims that people have been assigned.

## Component disposition

Retain means preserve tested behavior, not unconditional admission. Adapt means put the component behind the shared contracts and remove bypass routes. Replace means change the mechanism. Retire means remove it from supported production routes after compatibility/cutover checks; useful demos can remain explicitly labelled.

| Current component | Disposition and target | Phase | Admission requirement |
| --- | --- | --- | --- |
| `mas/swarm/runtime.py`, `contracts.py`, `cli.py` | Retain coding behavior; adapt behind shared workflow/coordinator contracts. Do not broaden arbitrary code access. | P2–P3 | Existing three-role, verification and human-approval semantics remain; compatibility and negative tests pass. |
| `mas/swarm/store.py` identity and run history | Replace duplicate online authority through IAM adapter; retain signed run history until reviewed versioned migration. | P1–P3 | Ownership/role mapping, reissued credentials, separation of approver, provenance reconciliation and revocation across active runs. |
| `mas/iam.py`, `identity_store.py`, `tenancy.py` | Retain and adapt as authoritative identity/tenant foundation. | P1 | All admitted surfaces consult current authority; private state is outside tenant mounts; no downgrade. |
| `mas/audit_anchor.py`, `audit_witness.py`, `anchor_http_worker.py` | Retain independent identity checkpoint protocol; separately deploy. Qualify new stream anchoring independently. | P1, P5 | Independent operations boundary, TLS, outage/recovery exercises and exact checkpoint enforcement. |
| `mas/core/message.py`, `event_bus.py`, `validation.py` | Adapt to versioned tenant/task messages and enforced routing. | P2 | Forged sender, cross-tenant subscription/replay and oversized/backpressure cases deny safely. |
| `mas/core/agent.py`, `state.py`, `cache.py` | Adapt behind bounded role/context/state contracts. | P2–P4 | No cached authorization bypass, cross-tenant context reuse or unbounded state growth. |
| `mas/core/swarm.py` | Defer distributed transport; keep outside initial supported pilot. | P6 | Explicit authenticated delivery/replay guarantees and multi-host partition/recovery evidence. |
| `mas/orchestration/*`, `mas/squad/*`, `mas/organization/*` | Adapt useful supervisor/pipeline/debate/delegation patterns; keep organization demonstrations outside authority. | P4 | Bounded depth/calls, cycle rejection, cancellation propagation; roles cannot manufacture approval or credentials. |
| `mas/pm/*` | Retain tenant-isolated PM persistence; adapt operations to common task/effect contracts. | P3 | Ownership at real HTTP/MCP boundaries, idempotency conflicts, concurrent updates and recovery reconciliation. |
| `mas/memory/working.py`, `episodic.py`, `comms_vault.py` | Adapt namespaces, query/replay ownership, retention and bounded context. | P4 | Cross-tenant read/write/search/replay denied; backup/delete behavior and injection handling demonstrated. |
| `mas/memory/vector_saas.py` | Adapt local behavior; keep real external service admission conditional. | P4 | Real service provenance and enforced tenant filters; local/demo results never labelled cloud integration. |
| `mas/swarm/provider*.py` | Retain strict live provider/usage handling; use as reference adapter. | P2 | Outage, cancellation, usage uncertainty, model discovery and no synthetic fallback. |
| `mas/providers/*` | Adapt admitted providers to shared contracts; separate mock/demo providers. | P4 | Strict outputs, explicit supported model IDs, budgets, credential isolation and representative live evidence. |
| `mas/swarm/worker.py`, `process.py` | Retain restricted coding workers and cleanup; adapt execution result contract. | P2–P3 | Host boundary, resource limits, cancellation/crash cleanup and no host-execution fallback. |
| `mas/tools/executor.py`, filesystem/storage tools | Replace unrestricted exposure with broker-authorized tenant adapters; retain existing restrictive mechanisms where suitable. | P3 | Secure path resolution, no host/private-store mounts, executor-policy tests at entry points. |
| Git/patch/package/GitOps tools | Adapt to reviewed repository and effect policies. | P4 | Validated repository ownership, exact candidate binding, external-effect authorization and uncertain-effect reconciliation. |
| Research/grounding/knowledge/data-contract tools | Adapt provenance, read scopes and bounded imported content. | P4 | Untrusted content cannot change policy; citations distinguish fetched source from model inference. |
| `bigquery_tool.py` and external data services | Conditional adaptation after real contract and credential qualification. | P4–P6 | Tenant/service scope, timeout/idempotency semantics and real integration evidence. |
| Browser/computer-use/display/visual-diff tools | Defer migration until scoped action and host isolation contracts exist. | P6 | Credential/session isolation, destination/action policies, destructive-action approval and recovery evidence. |
| `mas/mcp/*`, dashboard/server, CLI | Adapt thin interfaces to shared identity and broker; retire bypass routes. | P5 | Equivalent denial and approval policy across interfaces; legacy endpoints cannot opt out. |
| `mas/release_policy.py`, `eval/*`, HITL tooling | Adapt to typed measured evidence and exact artifact approval. | P2–P5 | Tampering, stale/missing evidence and simulated-success rejection; quality evidence separate from structural checks. |
| `mas/audit.py`, observability/config/capabilities | Adapt stream ownership, redaction and evidence-backed status. | P2–P5 | Required audit failure blocks mutation; tenant-scoped logs, secret redaction and truthful capabilities. |
| `main.py` demos and template QA claims | Retain clearly labelled educational demos; retire from release/admission evidence. | P0, P5 | Demo output never satisfies real verifier or production approval gates. |
| CI, packaging, Docker deployment and documentation | Retain reproducible gate; adapt compatibility/admission stages and supported entry points. | All | Candidate-specific logs/JUnit, clean install, deployment configuration and accurate supported scope. |

## Sequenced implementation work

| Phase | Owner role | Deliverable and dependencies | Exit gate |
| --- | --- | --- | --- |
| P0: inventory and contracts | Architect + platform engineer | Inventory entry points, state schemas, callers, secrets and effects. Define versioned contracts and compatibility policy from ADR. No runtime rerouting. | A0–A2: reviewed component inventory, schemas, supported pilot envelope and migration fixtures. |
| P1: authority and witness | Security/platform engineer + independent witness operator | Deploy witness independently; implement shared IAM adapter. Review swarm tenant/subject/role mapping and session cutover. Depends on P0. | A3–A5: no bypass, revoked authority denied, independent recovery evidence. |
| P2: coordinator and broker | Platform engineer | Extract common transition, budget, capability and evidence interfaces without changing accepted coding behavior. Depends on P0; production admission requires P1. | A6–A9: compatibility, bounded messages/execution, cancellation and verifier integrity. |
| P3: first vertical slice | Platform/data engineer | Authenticated operator → tenant PM task → coding workflow → measured results → separate approval → export. No automatic deployment. Depends on P1/P2. | A10: full entry-point flow, cross-tenant and crash/recovery cases; reviewed data manifest. |
| P4: memory/research/orchestration | Data + AI/runtime engineer | Migrate one capability at a time with ownership, provenance and bounded delegation. Depends on accepted P3. | A11–A12 per adapter; unsupported capabilities remain denied. |
| P5: interfaces and cutover | Platform engineer + operator + reviewer | Route CLI/HTTP/MCP through accepted controls; retire bypasses; execute rehearsed migration and operational qualification. Depends on accepted adapters. | A13–A16: equivalent interface policy, load/restore, clean packaging and independent verdict. |
| P6: optional expansion | Architect + capability owner | Browser/desktop, external data and distributed execution require separate scoped design/acceptance. | New scope-specific gates; no automatic admission from P5. |

Do not assign dates until P0 estimates real adapter and data-migration effort. Phase completion is evidence-based, not a percentage of files renamed.

## Data cutover procedure

1. Inventory each tenant, principal, active credential, task, artifact and audit stream. Produce an explicit mapping; reject unresolved identity conflicts. Back up private stores and keys under their distinct trust boundaries.
2. Create isolated migration fixtures from approved non-secret samples. Verify export manifests, record counts, tenant ownership, artifact hashes, historical signature validity and terminal state mapping.
3. Rehearse import and compatible rollback; define which mutations prevent reverse migration. Never import active old credentials as implicitly trusted sessions.
4. Stop new admissions, drain or cancel tasks, reconcile uncertain containers/provider/effects, and capture final signed manifests. Only one authoritative writer may exist after cutover.
5. Activate reviewed authority mappings, reissue credentials and retain separate submitter/approver identity. Enable only accepted interfaces for an allowlisted tenant.
6. Compare imported state/evidence against manifests and exercise denial cases. If checks fail, stop traffic. Revert routing only when the prior adapter is still accepted and compatible with current authority; otherwise recover forward offline.
7. Retain previous stores as restricted historical evidence under an explicit retention policy; remove obsolete routes and credentials after the stability window. Do not erase history as part of cleanup.

## Stop conditions

Stop migration on ambiguous tenant ownership, invalid provenance, mismatched witness head, authorization bypass, missing usage/evidence, orphaned execution, unreconciled external effects or failed restore rehearsal. Do not compensate by disabling isolation, re-enabling stale credentials, rewinding checkpoints or treating simulated output as test evidence.
