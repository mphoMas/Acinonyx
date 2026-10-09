# MAS consolidation acceptance checklist

Status: **IN PROGRESS — no full consolidation gate is signed off.** Regrouping baseline: `3311a4fa4a99957d9f4c13dde89fc97f0e8817f3`.
Related: [ADR](MAS_CONSOLIDATION_ADR.md), [migration map](MAS_CONSOLIDATION_MIGRATION.md), [scope inventory](MAS_CONSOLIDATION_INVENTORY.md).

The shared-identity baseline passed 478 repository tests, all five gates and clean-wheel checks; see [shared identity evidence](../reviews/SHARED_SWARM_IDENTITY_EVIDENCE.json). These results qualify their documented scope. They do not pass future consolidation gates, certify a deployed witness or establish enterprise readiness. Earlier anchor/contract milestones remain historical evidence.

## Current partial evidence

| Gate | Current contribution | Still required |
| --- | --- | --- |
| A0 | Source-referenced control-plane and development consumer inventory; explicit scope exclusions | Confirm deployment consumers, ownership and external-service inventory before cutover; reviewer sign-off |
| A1 | Shared identity/evidence contracts plus bounded coding task admission | Message/capability/result/approval/audit schemas and shared lifecycle; conformance review |
| A2 | Existing coding schema 2, idempotency and approval behavior retained | Full extraction comparison including cancelled and failed tasks; reviewed upgrade mapping |
| A3 | Fresh platform-bound swarm and tenant PM MCP share durable IAM sessions; revocation cases pass at baseline | All admitted HTTP/CLI/MCP workflow surfaces and broader cutover |
| A4–A16 | Scoped earlier fixtures/reviews supply inputs where applicable | Candidate-specific full acceptance and operational evidence; no automatic gate pass |

## Gate register

Each checkbox requires recorded candidate-specific evidence and reviewer sign-off. A test that was not run remains pending. Unsupported adapters remain unavailable rather than receiving a blanket exception.

- [ ] **A0 — Inventory and scope.** List every executable entry point, capability, store, credential, effect and current consumer. Resolve retain/adapt/replace/retire ownership; explicitly identify trusted host APIs and demo paths. Publish the supported pilot envelope and denied scopes. Evidence: reviewed inventory with source references.
- [ ] **A1 — Versioned contracts.** Define strict task/message/capability/result/evidence/approval/audit schemas and legal transitions. Reject unknown fields, invalid versions, duplicate JSON keys, non-finite values, oversized payloads and mismatched references. Evidence: schema review and meaningful conformance/negative cases.
- [ ] **A2 — Compatibility baseline.** Run the current coding adapter unchanged against representative successful, failed and cancelled tasks. Compare observable behavior and persisted contracts before/after extraction. Evidence: candidate revision, commands, actual results and supported upgrade/version mapping.
- [ ] **A3 — Unified authority.** Show real CLI/HTTP/MCP and workflow entry points using shared authoritative identity. Deny invalid/expired/revoked credentials, tenant switching and forged approver roles. Revocation persists across processes/restarts and prevents subsequent sensitive actions in an active run. Record cancellation policy and already-completed-effect limits. Evidence: integration cases through real handlers.
- [ ] **A4 — Identity migration.** Reconcile tenant/subject/role mappings, deny ambiguous ownership, reissue credentials and preserve distinct submitter/approver requirements. No old cached context bypasses the cutover. Evidence: migration manifest, reconciled counts and negative credential tests.
- [ ] **A5 — Independent witness operations.** Record actual HTTPS deployment, administrative/key/storage/restore separation and scoped writer provisioning without secret values. Exercise outage, TLS trust, restart, stale authentic backup and lost-ack/commit divergence in that deployment. Confirm no rewind/reset or local fallback. Evidence: operational drill and matching-state or fresh-generation recovery procedure. Additional anchored streams require separate qualification.
- [ ] **A6 — Coordinator lifecycle.** Test concurrent claims, stale leases, duplicate submission keys, changed-input conflicts, legal transitions and optimistic state conflicts. Bound retries and delegation; terminal tasks cannot silently resume. Evidence: real concurrency and process-death/recovery cases, with side-effect reconciliation.
- [ ] **A7 — Message and context isolation.** Deny cross-tenant publish/subscribe/replay/artifact access and forged sender authority. Bound queues, context, payloads, hops/depth and cyclic delegation; cancellation terminates pending work safely. Evidence: adversarial routing, overflow and cancellation tests, not only schema validation.
- [ ] **A8 — Execution and capability boundaries.** Test actual mounted paths, environment, network policy and limits at admitted entry points. Candidate code cannot access host/tenant-neighbor stores, Docker socket, verifier expectations or credentials. Cleanup covers timeout, cancellation, process death, output/memory exhaustion and daemon uncertainty. No unrestricted fallback. Evidence: real worker/OS integration and container reconciliation logs.
- [ ] **A9 — Honest verification and approval.** Reject canned success, self-issued certificates, zero executed mandatory cases, missing/stale/tampered results, candidate/suite/image mismatch and changed artifacts after approval. Independent verifier results bind exact task/attempt/artifact; model agreement alone cannot approve. Missing/uncertain provider usage consumes the reservation and blocks unjustified approval. Evidence: targeted negative release cases and provenance checks.
- [ ] **A10 — First vertical slice and persistence.** Complete tenant PM task → coding → worker verification → separate human approval → source export through accepted interfaces. Reconcile state and artifacts after crash/restart; repeat requests cannot duplicate acknowledged effects. Demonstrate isolated tenants and audit-failure rollback. Evidence: end-to-end run plus reviewed import/backup manifests. Automatic deploy remains excluded.
- [ ] **A11 — Memory and research admission.** Exercise cross-tenant search/read/write/delete/replay, retention and bounded context. Imported notes or retrieved documents cannot change policy or become trusted instructions. Separate real fetched/cited sources from model inference and local/cloud simulations. Evidence: real adapter tests, injection cases and recovery/deletion behavior.
- [ ] **A12 — Model and orchestration admission.** Explicitly identify model/provider and verify actual availability; no silent substitution or synthetic fallback. Test budgets, failure/timeout/cancellation, loop/delegation bounds and representative quality with held-out tasks. Evidence: actual usage/latency/outcomes and prompt-injection evaluation; test fixtures remain labelled fixtures.
- [ ] **A13 — Interface cutover.** Prove equivalent identity, tenant, capability and approval rules through all supported CLI/HTTP/MCP surfaces. Unsupported routes and legacy/demo bypasses are denied or removed from production startup. Shadow execution does not duplicate effects. Evidence: interface admission matrix and route/startup tests.
- [ ] **A14 — Operational envelope.** Before the drill, set workload, concurrency, latency/error thresholds, resource ceilings, backup RPO/RTO, retention and alert response targets. Measure agreed load and soak behavior, outage/restart and backup restoration. No orphaned workers, hidden failed tasks, credential leakage or unexplained state divergence is acceptable. Evidence: reproducible workload/configuration and measured outcomes against agreed targets. No invented SLO pass from unit counts.
- [ ] **A15 — Reproducible candidate.** Run appropriate full gates with zero failures/errors/skips for required acceptance suites. Install a clean wheel outside the checkout and test the supported vertical slice; verify packaged source hashes. Build/run the target deployment if container deployment is admitted. Evidence: revision, dirty-state check, dependency/image versions, commands, JUnit/logs and artifact hashes. Baseline image results cannot qualify a changed candidate.
- [ ] **A16 — Independent final verdict.** Review platform feasibility, data contracts, AI correctness and resilience/governance against this declared scope. Record unresolved findings, owners and verifiable conditions. Production activation requires all deployment blockers closed; pilot acceptance must state its narrower limits. Evidence: explicit APPROVED, APPROVED WITH CONDITIONS or REJECTED verdict; no automatic 10/10 label.

## Evidence record and review rules

For each gate retain: gate/adapter ID, candidate commit and source/artifact hashes, test/environment versions, sanitized configuration, commands and timestamps, expected/observed outcomes, passed/failed/skipped counts, raw logs/JUnit references, remaining risks, owner and reviewer decision. Keep secrets out of evidence and access controls on tenant-bearing logs. Attach a reviewed manifest to each migration run.

A reproducible infrastructure failure is a failure or blocked gate, not a successful case. Missing prerequisites, unconfigured production endpoints and model unavailability must be reported explicitly. Do not waive scope-critical checks to make a count pass. Architectural safety and model quality require separate evidence.

## Admission and rollback policy

- **Draft/design acceptance:** review A0–A2 definitions and agreed requirements; this does not authorize production rollout.
- **Supported pilot:** satisfy applicable A0–A10 and A13–A16 for the first slice. A11/A12 apply before their additional capabilities are admitted; live model use always requires the relevant provider/usage checks in A12.
- **Extended platform:** repeat adapter gates for every capability, plus the full shared regression gate. Browser, desktop and distributed execution need new threat models and acceptance criteria before use.
- **Enterprise admission:** requires separately specified deployment, tenant, recovery, governance and sustained-load criteria. This draft does not define or grant a blanket enterprise certification.

On a failed migration/authority/verification gate: stop admissions, preserve evidence, reconcile live effects and apply the rehearsed compatible recovery. Never make service available by bypassing policy, undoing revocation, stripping witness binding or reopening an unaccepted legacy interface.
