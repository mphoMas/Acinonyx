# Independent CC-04 resubmission review

Date: 12 October 2026. Candidate `490e2ce0`. CC-03 independent acceptance remains recorded; this review concerns CC-04 only.

## 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK) for CC-04 acceptance and live runtime integration.** Crash hold preservation, mismatched identities, measured usage and transactional admission have improved. Result consistency, deadline enforcement and in-flight termination still do not meet the stated guarantees.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Contradictory result status becomes success.** Validation rejects a list of uncertain statuses but does not require SUCCEEDED/FAILED or enforce consistency with exit_code. Independent controlled adapter returns matching identities, status FAILED, exit 0, spend 1 and a candidate; attempt becomes SUCCEEDED. Unknown status strings can follow the same path. **Solution:** strict result schema and explicit allowed status/exit/candidate combinations. Conflicting/unknown status is quarantined UNKNOWN_EXECUTION with hold retained; measured failure settles actual spend without fabrication. Add FAILED/0, SUCCEEDED/nonzero, unknown enum and malformed result tests.

2. **Deadline expiry can disappear during heartbeat cleanup.** Code joins execution with timeout, then joins heartbeat for up to one second, then checks exec_thread.is_alive. An overrun can finish during cleanup and be accepted as on-time. Independent probe: execution deadline .01 seconds, adapter runs .2 seconds, worker accepts COMPLETED/SUCCEEDED. **Solution:** latch deadline expiration at its actual monotonic deadline before cleanup; elapsed completion after deadline cannot reset that fact. Use interruptible Event.wait for heartbeat sleeps. Quarantine expired runs regardless of eventual result, retain holds and reject late completion.

3. **No confirmed bounded termination.** Timeout sets an event and returns while execution thread can still run. stop_event is cooperative; Python daemon threads do not enforce process containment. Authority-loss detection is handled after waiting for the execution timeout rather than interrupting supervision immediately. **Solution:** restrict qualification to adapters with a verified stop contract or supervise execution in a terminable isolated process. Observe confirmed termination within a cleanup deadline, otherwise leave UNKNOWN_EXECUTION and quarantine late events/results. Monitor worker stop, heartbeat failure and authority revocation while waiting. Never claim zero surviving execution merely because a stop event was set. Add an adapter that ignores stop and attempts a late side effect.

4. **Admission still bypasses the real FSM guards.** Raw update_issue_state with BACKLOG->REFINED->STAGED changes edge shape but does not execute FSM policy/WIP/assignment guards. Only DONE is rejected; other executing/review states remain admissible when no active intent exists. Policy version/candidate freshness is not bound into the launch authorization. **Solution:** explicitly allow eligible task states, apply the same guarded FSM decisions inside the admission transaction, and bind admitted scope/budget/plan-policy version for pre-spawn revalidation. WIP saturation and policy changes must fail without committing intent or reservation. Do not treat direct SQL state updates as FSM governance.

### Medium Severity

- Zero-token tasks can be admitted without a reservation; live worker admission must require funded authorization. Synthetic no-cost fixtures require explicit separation from real runtime admission.
- Worker uses its injected adapter regardless of intent.adapter_type; routing/capability allowlist and synthetic-versus-live labeling need enforcement before runtime adapters are enabled.
- Event persistence failures remain swallowed. Define degraded/fail-closed behavior and reject or quarantine event streams after ownership retirement.

### Low Severity

- Correct the delivery statement that signals guarantee no orphaned execution. Report cooperative cancellation as measured capability, not enforced containment.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Active heartbeat and transaction support are useful; wait ordering and stop supervision remain unsafe.
- **Data:** Identity checks improve, but status/exit consistency and immutable admission policy need enforcement.
- **AI:** No live runtime invocation is qualified. Controlled results cannot be promoted merely because exit defaults appear successful.
- **Resilience/Governance:** Unknown budget holds now survive tested exceptions; actual deadlines and stale-policy admission still require correction.

## 4. Architect’s Action Directive

1. Antigravity closes contradictory result admission and latches monotonic deadline expiry before cleanup.
2. Implement verified bounded adapter shutdown or restrict the admitted adapter capability accordingly; test ignored stop and late effects.
3. Replace direct state progression with transaction-compatible FSM policy checks and policy-version launch binding.
4. Rerun targeted and full repository checks and submit exact candidate. Preserve CC-03, frontend and cleanup commits; live dispatch stays gated. Design work on later adapters may continue without activation.

## Independent evidence

`python -m pytest tests/test_cc04_scheduler_worker.py tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_pm_evidence_bindings.py tests/test_coordinator_contract_sql.py tests/test_sba_03_plan_publication.py tests/test_scrum_board_actions.py -q`: **129 passed in 60.77 seconds**, no failures/skips.

Disposable controlled adapters independently confirmed FAILED/exit0 -> COMPLETED/SUCCEEDED and .2-second execution with .01-second deadline -> COMPLETED/SUCCEEDED. No live provider processes or deployed board were used. No backend implementation was changed; no full gate repeated after reproduced blockers. Reported 20 skipped tests remain unexecuted.
