# Independent CC-04 review

Date: 12 October 2026. Candidate `2aee5ac9`. Prior independent CC-03 acceptance: `0457e767` reviewing Codex `a0c0aa51`.

## 1. Verdict & Executive Summary

**CC-03 independent acceptance is recorded. CC-04: REJECTED (REQUIRES RE-WORK).** The worker can claim and execute controlled synthetic tasks, but exception/result paths violate uncertainty and usage conservation. Claimed heartbeat, timeout and safe task-admission guarantees are not implemented sufficiently to qualify worker/runtime integration.

This does not reopen the accepted CC-03 corrections. No live runtime dispatch is approved by this review.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Crash settles unknown usage as measured zero.** worker.process_one_intent catches execution exceptions and calls complete_intent with invented candidate `crash-unverified`, exit -1 and tokens 0. Independent synthetic-crash reproduction: intent COMPLETED, attempt FAILED, reservation SETTLED, spend 0. **Impact:** potentially executed/billed work loses its hold and can be funded again. **Fix:** a fenced explicit interruption transition sets UNKNOWN_EXECUTION and preserves HELD reservation; store error observation without inventing candidate/spend. Never call normal completion for uncertain exceptions.

2. **Unknown/mismatched result becomes success.** Worker ignores result.status, attempt_id, run_id; result.exit_code or 0 and tokens_billed or 0 convert absent measurements to success/zero. Independent controlled adapter returns foreign attempt/run IDs, UNKNOWN_EXECUTION, null exit/usage and a candidate string: worker records COMPLETED/SUCCEEDED/SETTLED with zero spend. **Fix:** strict result model; bind identity to persisted request/run/fence; validate status/outcome consistency and measured usage. Unknown/missing result fields keep uncertainty and hold; conflicting identities are quarantined, never admitted. Failed measured execution must settle actual usage without requiring a successful candidate artifact.

3. **No bounded execution, heartbeat or in-flight shutdown.** heartbeat_interval_s is stored but never used. Adapter.execute is synchronous without enforced deadline or cancellation interface; stop only ends a later polling iteration. Healthy executions exceeding a lease fail settlement, while hung adapters prevent bounded shutdown. **Fix:** implement a supervised bounded lifecycle with independently renewed lease, deadline and stop signal; propagate authority/fencing loss to cancellation and uncertainty. Validate duration/poll/lease configuration. Add slow, hung, revoked, expired and canceled adapter tests, including no surviving worker execution after confirmed shutdown. A cycle count does not bound execute duration.

4. **Admission bypasses state and admission atomicity.** Eligibility/dependency/active-intent checks occur before reservation transaction; UNKNOWN_EXECUTION is excluded from active checks; raw update_issue_state skips FSM policy and occurs after committed intent. Pending changes, forbidden task states or concurrent plan edits can therefore evade coherent admission. Attempt sequence derives from reflexion_attempts instead of persisted coordinator attempt sequence; repeat admission can reuse seq=1. **Fix:** one authorized transaction revalidates task/plan/version, dependencies, unresolved execution and funded allocation, creates attempt/intent and records valid FSM transition. Allocate monotonic attempt_seq from persistent attempts under lock. Never auto-stage DONE or unresolved work. Add competing admission, revision change, post-commit failure and retry-after-settlement regressions.

5. **Execution scope/budget can be overridden by payload_extra.** Its final dictionary expansion replaces server-derived whitelist and token limit; worker then uses those values as request authority. **Fix:** allowlist harmless extra fields, forbid override of tenant/task/run/scope/budget/timeout identity, and derive authority from current admitted server policy. Request attempt_seq must use the persisted attempt rather than hardcoded 1. Adapter routing must match admitted runtime type; synthetic execution cannot masquerade as real developer execution.

### Medium Severity

- emit_event swallows persistence failures and execution proceeds; subsequent events/results can imply a complete stream despite missing receipts. Define fail-closed or explicitly degraded policy, with cursor deduplication and recovery evidence.
- Result session/run outcome metadata is not persisted as observed lifecycle updates. Separate synthetic fixture claims, process observations, verified evidence and task acceptance.
- Worker addition does not implement live Antigravity/Codex communication; CC-05/06 and verifier/admission gates remain separate.

### Low Severity

- Narrow the delivery's heartbeat/graceful-shutdown claims to actual implementation until bounded lifecycle tests pass.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** CAS claims work; adapter supervision and admission transaction boundaries remain incomplete.
- **Data:** Result identities and sequence allocation require exact persistence binding.
- **AI:** Synthetic transport is qualification scaffolding, not trusted live execution. UNKNOWN/null outcomes cannot become success.
- **Resilience/Governance:** Crash/retry budget holds and scope authority must survive every failure path.

## 4. Architect’s Action Directive

1. Antigravity fixes exception and strict-result admission first, adding the two reproduced negative cases with hold preservation.
2. Implement bounded execution supervision, heartbeat and stop handling against controlled adapters; no live CLI activation.
3. Make task admission atomic, FSM-governed, version-bound and monotonically sequenced; reject payload authority overrides.
4. Run targeted and full repository checks, report skips separately and submit exact candidate for independent CC-04 review. Preserve accepted CC-03 and frontend/cleanup commits, same SBA board and branch.

## Independent verification

Targeted command: `python -m pytest tests/test_cc04_scheduler_worker.py tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_pm_evidence_bindings.py tests/test_coordinator_contract_sql.py tests/test_sba_03_plan_publication.py tests/test_scrum_board_actions.py -q`: **120 passed in 62.84 seconds**, no failures/skips.

Independent disposable controlled-adapter probes confirmed crash -> COMPLETED/FAILED/SETTLED/0 and mismatched UNKNOWN result -> COMPLETED/SUCCEEDED/SETTLED/0. No live agent execution, production credentials or deployed board changes occurred. No backend code was modified; full gate was not independently repeated after these failures were reproduced. Antigravity's 660 passed/20 skipped gate remains reported evidence, not 680 executed tests.
