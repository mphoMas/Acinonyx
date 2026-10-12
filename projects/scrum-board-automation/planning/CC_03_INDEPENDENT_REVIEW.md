# Independent CC-03 acceptance review

Reviewed 12 October 2026. Candidate implementation `14befa0b`, submitted head `284cb877`. Owner: Antigravity. Reviewer: Codex.

## 1. Verdict & Executive Summary

**Status: REJECTED (REQUIRES RE-WORK) for CC-03 acceptance and downstream CC-04 dispatch.** Basic SQLite persistence and guarded intent transitions work, and the frontend/Codex fix commits are preserved. Required ownership, truthful cancellation, funded reservations and migration guarantees are not yet established by this implementation. Passing tests do not cover the reproduced defects below.

The independent Antigravity acceptance report for Codex `03da60da` is recorded at `18cc0a98`; this review concerns Antigravity's new CC-03 implementation, not withdrawal of that prior review.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **A physical run can belong to the wrong attempt.** `CoordinatorStore.pre_spawn_intent` accepts an optional caller-supplied attempt_id, updates that attempt and inserts a run without checking it equals the intent's attempt. `pm_coordinator_runs` has independent intent/attempt foreign keys rather than a composite ownership constraint. Disposable reproduction: intent i1 belongs to a1; pre_spawn(i1, attempt_id=a2) returns true and stores run1 under a2. **Impact:** task ownership, usage, evidence and recovery can be attributed to different attempts. **Fix:** derive attempt solely from the guarded intent; reject any contradictory supplied value; enforce composite (intent_id, attempt_id) relational ownership, including receipt/run/attempt consistency. Regression must attempt wrong-attempt and cross-project relationships and confirm full rollback.

2. **Cancellation fabricates observed runtime termination.** `cancel_intent` changes attempts to CANCELED and SPAWNING/STREAMING runs to KILLED even though this storage-only milestone performs no cancellation or process observation. Reproduction: create a SPAWNING record and call cancel; get_run reports KILLED. **Impact:** recovery or UI can treat potentially running work as stopped. **Fix:** distinguish cancellation intent from observed process outcome. Retire generation and keep cancellation requested/unknown states plus budget holds until an authoritative adapter or reconciliation receipt proves termination. Repeated cancellation must be idempotent. Test cancellation without observation and late events, not just rejected completion.

3. **Budget reservation is an unchecked numeric label.** `create_attempt_with_intent` stores budget_reservation but never reserves an authorized project/issue pool, validates appetite or excludes concurrent commitments. Reproduction: a project budget of 10, task appetite zero, and two attempts each reserving 100,000 are accepted. **Impact:** the claimed held budget does not prevent double allocation. **Fix:** persist funded authorization/reservation and settlement states in an atomic ledger; reject negative/non-finite/unauthorized amounts and concurrent over-allocation; retain uncertainty holds without inventing measured spend. If admission belongs to CC-04, narrow CC-03 claims and still supply the durable reservation primitives needed by that scheduler. Do not represent an integer column as enforced reservation.

4. **Tenant labels and mutation authority are not validated by CoordinatorStore.** Initial attempts accept supplied tenant_id; foreign keys only keep later intents consistent with that label. `_get_connection` checks storage:read when bound, not coordinator mutation authority; database path isolation alone does not verify supplied tenant ownership. **Fix:** bind store access to verified tenant/service authority or an explicit trusted local administrative mode; reject mismatched tenant labels and require appropriate mutation authority. Run actual tenant-scoped negative tests. The unbound disposable reproduction is not a demonstrated remote exploit, and there is no exposed dispatch endpoint in this milestone.

5. **Required versioned migration is absent.** New DDL runs inside general init_schema with no coordinator migration version/checksum ledger or failure-injection rollback evidence. Connection isolation_level=None means a Python `with conn` alone does not open one atomic transaction for the migration. Broad OperationalError handling can hide causes beyond an existing column. **Fix:** implement explicit versioned transactional migration, distinguish already-existing schema via PRAGMA, fail loudly on other errors, verify backup/integrity/reopen and inject a failure midway to prove all-or-nothing evolution. Preserve historical evidence and identity bytes.

### Medium Severity

- `complete_intent` accepts a nullable candidate and arbitrary tokens_spent, then marks attempt SUCCEEDED and run EXITED without a persisted adapter exit receipt or exit_code. Storage transition intent must not manufacture measured execution. Require authoritative outcome fields or keep proposed versus observed outcomes separate before runtime wiring.
- Attempt generation is not advanced with the claimed intent; multiple adapter intents can share one attempt. Define aggregation and per-intent/run fencing so one adapter completion/cancellation cannot overwrite another's attempt outcome.
- `record_evidence_receipt` stores arbitrary signatures and independent issue/attempt/run references while describing them as admitted. Either enforce full ownership and cryptographic admission upstream with a constrained trusted interface, or explicitly quarantine raw submitted receipts; raw persistence is not verification.

### Low Severity

- Correct the delivery label “full implementation” to the exact qualified scope until these guarantees are verified. Ruff check is lint, not a formatter check.

## 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** Intent CAS and pre-spawn transaction are useful; recovery needs truthful outcomes and coherent run/attempt identity before a daemon dispatches work.
- **Data & Schema Contracts:** Existing mappings survive tested reopen. Composite ownership and atomic versioned migration remain incomplete.
- **AI & Model Runtimes:** No live runtime execution is claimed or qualified. Persisted SUCCEEDED/KILLED states must not substitute for adapter observation.
- **Resilience & Governance:** Expired leases reject late intent writes, but tenant authorization, funded reservation and cancellation settlement require correction.

## 4. Architect’s Action Directive

1. Antigravity closes wrong-attempt ownership and cancellation truthfulness first, with independent negative regressions.
2. Implement scoped mutation authority and durable funded reservation/settlement primitives; document any intentionally deferred scheduler admission honestly.
3. Add versioned transactional migration and injected-failure recovery tests. Validate all raw receipts/outcomes are separated from trusted admission.
4. Rerun targeted checks and the repository quality gate, preserving passed/failed/skipped distinctions. Submit exact corrected hashes for independent review.
5. Do not start CC-04 dispatch against this rejected candidate. Safe design/documentation work may continue. Preserve the existing SBA board/branch and do not self-mark CC-03 accepted.

## Verification performed

Independent command: `python -m pytest tests/test_cc_03_coordinator_state.py tests/test_pm_evidence_bindings.py tests/test_coordinator_contract_sql.py tests/test_sba_03_plan_publication.py tests/test_scrum_board_actions.py -q`: **90 passed in 67.27 seconds**, no skips/failures.

Independent disposable database reproductions confirmed cross-attempt pre-spawn, 200,000 unfunded declared reservations against budget 10/appetite 0, and KILLED/CANCELED state claims after storage-only cancellation. No live agent process was launched. The reported full gate's 629 passed/20 skipped is Antigravity's evidence; skipped checks did not execute. No full gate was independently repeated after these blockers were reproduced. No backend code or deployed board state was modified by this review.
