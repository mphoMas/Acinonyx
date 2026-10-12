# Independent CC-04 review: f6d2f34a

Date: 12 October 2026. Candidate `f6d2f34a`. CC-03 remains independently accepted.

## 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK) for CC-04 acceptance and live adapter activation.** Strict conclusive-result consistency, latched deadlines, scope/WIP checks and hold preservation improve this revision. Two reproduced gaps remain: unconfirmed execution termination and non-atomic policy authorization at launch.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Adapter execution survives a timeout.** Worker supervision still uses a daemon Python thread and a cooperative event. After timeout it records UNKNOWN_EXECUTION and returns, without joining/terminating adapter execution. The new uncooperative test only checks absence of an event immediately; it does not observe later filesystem effects or surviving execution. Independent controlled adapter ignores stop, sleeps .2 seconds, then writes a real disposable file. Worker returned at .038 seconds for a .03-second deadline; the file appeared after return. Holds remain retained, which is correct, but does not establish bounded execution containment. **Required fix:** either restrict CC-04 to an explicitly enforced set of qualified controlled adapters, rejecting unsupported stop capabilities, or run adapter work in an actually terminable supervised execution boundary. Observe termination within cleanup deadline; reject/quarantine late IPC results/events; unknown remote effects retain holds. Tests must wait past the side-effect deadline and inspect execution survival. Do not describe event suppression as cancellation of external effects.

2. **Policy authorization races pre-spawn.** Worker reads current policy in a separate operation, then calls pre_spawn_intent whose atomic update does not revalidate admitted policy/version/pending reconciliation. Independent controlled interleaving updates issue policy from 1 to 2 immediately before the actual pre-spawn call; worker executes and completes using the admitted old payload. **Required fix:** inside the pre-spawn transaction, re-read issue policy, pending reconciliation, admitted scope/funded authorization and eligible workflow state. Require the exact admitted policy in the guarded launch update; insert the run and update attempt only after that same decision succeeds. Policy changes after launch must revoke/fence active authority before admitting stale results; define safe interruption/reconciliation rather than merely matching a previously fetched object. Add competing plan update/pre-spawn and pending-reconciliation regressions.

### Medium Severity

- Synthetic-versus-live adapter routing must be enforced by a capability registry/allowlist, not only documented. Arbitrary injected adapters do not inherit qualified cancellation behavior from SyntheticExecutionAdapter.
- Zero reservation and caller-manufactured authorization labels must not become live funded admission; retain explicit controlled-only boundaries until the runtime milestone qualifies allocation/authority.
- Delivery claims mypy, bandit and production build gates, but scripts/run_quality_gate.sh still runs Ruff, CLI doctor/capabilities, research links, compileall and pytest. Correct the receipt labels; no evidence that the additional tools ran is supplied.

### Low Severity

- State the measured cancellation guarantee precisely: local event suppression and UNKNOWN_EXECUTION are implemented; confirmed physical/remote termination is not established.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Deadline latching is better; daemon threads do not bound uncooperative execution.
- **Data:** Policy version exists but must participate in the same transaction that authorizes launch and binds subsequent outcome admission.
- **AI:** No live agent communication/dispatch acceptance follows from controlled adapter success.
- **Resilience/Governance:** Uncertain holds are preserved; authority revocation must be atomic with execution authorization and stale result admission.

## 4. Architect’s Action Directive

1. Antigravity closes the actual adapter termination boundary or narrows admission through an enforced qualified-adapter policy. Test a late filesystem effect, not only stream events.
2. Move policy/scope/reconciliation/funded launch checks into guarded pre-spawn transaction and test competing updates; define in-flight policy invalidation.
3. Correct verification gate labels, rerun targeted/full checks and submit an exact corrected candidate for independent review. Keep CC-03 accepted, same SBA board/branch and live runtime dispatch gated.

## Independent verification

Controlled probe returned worker_return_seconds=.038, late_file_on_return=false, late_file_after_return=true, intent_state=UNKNOWN_EXECUTION. Policy-race probe completed an intent after live policy advanced to 2 while admitted payload remained at policy 1. Both probes use disposable local databases/adapters, not production processes. No backend application files or deployed board were modified. No full gate repeated after reproduced blockers; reported skips remain unexecuted.

Independent targeted command: `python -m pytest tests/test_cc04_scheduler_worker.py tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_pm_evidence_bindings.py tests/test_coordinator_contract_sql.py tests/test_sba_03_plan_publication.py tests/test_scrum_board_actions.py -q`: **134 passed in 59.39 seconds**, no failures/skips. These passes do not cover or refute the independent late-effect and atomic-launch failures.
