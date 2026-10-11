# CC-01 and SBA-03 resubmission review

Reviewed 11 October 2026. Candidates: SBA-03 `148ad034`; CC-01 `582631e1`.

## 1. Verdict & Executive Summary

**SBA-03: REJECTED (REQUIRES RE-WORK).** Several previous findings are addressed, including zero execution appetite for new tasks, effective dependency validation, and transaction-time mapping checks. Active reviewer preservation and planning authority remain incomplete.

**CC-01: APPROVED WITH CONDITIONS for capability discovery and CC-02 contract drafting only.** The submitted excerpts identify batch CLI interfaces; they do not qualify duplicate-safe recovery, cancellation containment, or real candidate review. Automatic dispatch is not approved. The coordinator is not implemented by these commits.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Active reviewer removal changes live policy.** In `mas/pm/plans.py`, a change from a nonempty reviewer requirement to `None` sets `staged_rev=None`, but `effective_rev` uses `staged_rev is not None` as its staging discriminator. Independent reproduction: create a task requiring `independent`, mark it IN_PROGRESS, then publish a revision with no reviewer requirement. Stored live reviewer becomes null, pending reconciliation true, staged reviewer null. The pending transition guard helps, but the live policy is already erased. **Fix:** represent staged removal explicitly; preserve live policy for every active change, including null/empty values; test authorized application and rejection of the proposal.

2. **Planning authority remains broader than the claimed contract.** `mas/pm/tools.py:pm_publish_plan` only requires a nonempty execution principal in unbound mode, with no planning permission check. HTTP planning also admits `storage:*` and shared-mode name-based special cases including `test-live-auth-token`. Storage permission is not evidence of planning authorization. Direct `PlanPublisherService` accepts arbitrary actor strings; the reported local registration through that service is not proof of authenticated publication. **Fix:** enforce explicit planning authority at exposed entry points; define and constrain trusted administrative service use; remove test identities from production authorization. Verify non-planner, revoked and cross-tenant rejection through HTTP and MCP.

3. **Conversation continuation is not interrupted-run recovery.** CC-01 tests ask a completed conversation to recall a token. They do not interrupt an active side effect, restart the coordinator, reconcile its existing run and prove exactly one effect. `resume` with a new prompt can start another turn. Antigravity's demonstrated run ID arrives in final JSON; persisting it before completion is not demonstrated. **Fix:** classify continuation separately; prove streaming early references and supported status/retrieval, or specify UNKNOWN_EXECUTION with automatic retry prohibited. Test crash before/after launch and before result persistence with an externally counted side effect.

4. **Candidate review and cancellation claims exceed evidence.** Prompting a model to print `APPROVED` and an invented candidate tag only proves output transport. A parent process exit does not prove descendants or remote work stopped. **Fix:** provide real immutable Git candidate and independently measured checks, plus a deliberately failing candidate which the reviewer rejects. Test child-process cleanup, late writes/results and uncertain remote cancellation. Avoid guarantees based solely on process groups.

### Medium Severity

- Local board keys differ from the cloud mapping because a local verification ticket occupies SBA-10. This is acceptable if UUID/planning-reference identity remains stable. The uploaded listing is not independent verification of the deployment. Supply API receipts and before/after identity, state, evidence and dependency comparisons; never synchronize by issue number alone.
- The runtime matrix is prose with excerpts rather than a committed reproducible probe and full bounded evidence. Record exact versions, invocation limits, failures and unavailable operations. OS working-directory selection is not filesystem containment.

### Low Severity

- Replace unconditional “guarantees” and “without re-executing” language with measured capabilities and explicit uncertainty.

## 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** Batch invocation is a plausible adapter foundation; process lifecycle and recovery are not qualified. No runtime adapter or outbox implementation is certified here.
- **Data & Schema Contracts:** Budget separation and transactional graph validation improve planning integrity. Null staging semantics still corrupt live reviewer policy. Local keys are deployment-specific.
- **AI & Model Runtimes:** Printed verdicts and recalled tokens are smoke checks, not semantic review or exactly-once execution evidence.
- **Resilience & Governance:** Explicit planner authority, revocation checks, uncertain execution handling and descendant cancellation evidence remain required.

## 4. Architect’s Action Directive

1. Antigravity fixes null reviewer staging and explicit planning authorization; adds negative HTTP/MCP and active-policy tests.
2. Antigravity corrects CC-01 capability classifications and submits bounded reproducible probes for active-run interruption, duplicate prevention, real candidate review and cancellation effects. If unsupported, document safe stop/reconciliation rather than automatic resume.
3. CC-02 contract drafting may begin now, incorporating these constraints. No dependency-ready dispatch or automatic DONE claim follows from this conditional discovery acceptance.
4. Preserve the existing SBA board/branch and stable task UUIDs; provide deployment API reconciliation receipts. Do not mark the rejected SBA-03 implementation accepted.
5. Resubmit candidate-specific evidence for independent review before scheduling implementation relies on SBA-03.

## Verification performed

Independent command: `python -m pytest tests/test_sba_03_plan_publication.py tests/test_sba_02_discovery.py tests/test_sba_05_session_integration.py -q` using the existing project environment: **62 passed in 20.99 seconds**.

Independent disposable database reproduction confirmed active reviewer removal described above. The initial reproduction fixture lacked a required project ID; after correcting the fixture, it completed successfully and returned `live_reviewer_after_removal: null`, `pending: true`, `staged: null`.

No full repository gate or live provider runs were performed for this review. `agy` is unavailable in this cloud environment; submitted local CLI excerpts were assessed as reported evidence. No backend application code was changed.
