# Regrouping and coding task-admission verification

Regrouping baseline: `3311a4fa` (shared durable platform IAM and supervised swarm). Candidate: that baseline plus the working-tree changes identified by the [source/evidence manifest](REGROUPING_TASK_ADMISSION_EVIDENCE.json).

Status: **Engineering verification of an incremental slice; independent consolidation sign-off remains pending.** This report does not issue a production verdict or mark a full consolidation gate complete.

## Readiness reconciliation

The release checklist now supersedes the old Sprint 2 production certification with the narrower supported single-host shared-identity pilot verdict and deployment blockers. README, documentation index, capability matrix, implementation status, migration map and acceptance register use the shared-identity regrouping baseline. The machine-readable registry now labels enterprise engagement and echo agents as demos. Durable tenant IAM and simulated vector adapters are no longer incorrectly described as unshipped capabilities.

The [scope inventory](../architecture/MAS_CONSOLIDATION_INVENTORY.md) identifies inspected entry points, development consumers, stores, credential owners and effects. Deployed consumers, accountable owners, external-service configurations and operational targets remain unverified. A0 is partial, not signed off.

## Task-admission boundary

`CodingTaskAdmission` is a strict, frozen version-one host-owned submission view. It binds the authenticated tenant and subject, generated task ID, tenant-scoped request key, supported coding workflow, immutable request/suite hashes, creation time and nested coding resource policy. Unknown fields, unsupported versions, malformed IDs/hashes, non-finite or coerced policy values and expanded operational ceilings are rejected. JSON admission also rejects duplicate keys and numeric overflow such as `1e999`.

The nested policy reuses the existing `mas.swarm.contracts.Limits` ceiling validator instead of establishing a divergent set of limits. The Store validates fresh admission after authentication and before inserting state/audit. The existing idempotent retry path remains first: acknowledged terminal requests return their original task, and changed-input conflicts still fail.

Persisted signed swarm schema 2, document shape, existing signatures, transitions, approval and separate authority binding remain unchanged. The adapter returns the host dictionary unchanged. It is not an external enrollment endpoint or authorization token. General message/capability/result/approval/audit contracts and shared coordinator/lifecycle are still required for A1; broader extraction and migration comparison remain required for A2.

## Validation and discovered fixture issue

The focused contract/store/shared-identity suite passed 100 cases. A clean wheel installed outside the checkout passed the 35 new admission cases and the existing shared CLI/PM MCP/revocation smoke; all 100 packaged MAS Python files match candidate source. The evidence manifest records the final full gate, JUnit counts, command/environment details, source hashes and raw artifact hashes.

The first full gate recorded 512 passes and one legacy gateway failure. A prefix diagnostic reproduced HTTP 429: the earlier enterprise demo consumed 24,997 of the gateway fixture's 25,000-token minute budget, leaving insufficient budget for the following transport test. Each test now owns a fresh normal budget and ephemeral local listener, with operator upstream configuration disabled for fixture calls. An explicit exhaustion case requires HTTP 429/error and absent usage. No production quota was increased or disabled. A subsequent check caught a port-zero address mistake in the new exhaustion test; it now uses the assigned listener port. The 18 gateway/governance checks pass. Failed full runs and diagnostic logs are retained in the evidence; the final full gate follows these corrections.

Local scripted gateway artifacts and TLS model fixtures are transport/integration evidence, not live model quality. No new production container qualification, live-model evaluation, historical migration or witness deployment was performed.

## Next acceptance work

Complete the shared lifecycle/message/capability/result/approval/audit definitions and their compatibility fixtures before coordinator extraction. Confirm deployed consumers and reviewed identity/history ownership before migration. Independently deploy and drill the witness before its production gate can pass. Then qualify lifecycle/routing/execution boundaries and the PM-to-coding vertical slice through admitted interfaces. No historical swarm credentials or state were automatically migrated during regrouping.
