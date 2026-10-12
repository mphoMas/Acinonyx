# Independent CC-04 review: 07294b0f

Date: 12 October 2026. Candidate `07294b0f`. CC-03 acceptance remains unchanged.

## 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK) for CC-04 acceptance/live adapter integration.** Exact-class registry checks now reject unqualified subclasses. The same registered adapter now exposes configuration that disables stopping and runs arbitrary callbacks, so qualification can still be bypassed without changing class identity.

## 2. Architectural Audit & Critical Findings

### High Severity (Blocker)

**Registered adapter has unsafe test escape hatches.** SyntheticExecutionAdapter accepts ignore_stop_signal=True and an arbitrary on_stop callback. Worker registration validates class identity but not these options. Independent reproduction uses the exact registered class, duration .2, ignore_stop_signal=True, callback writing a disposable file, execution timeout .01 and cleanup .01. Worker returns .026 seconds; file is absent on return and present afterward. Intent honestly remains UNKNOWN_EXECUTION and budget uncertainty is retained, but local execution still survives its admitted boundary.

**Required solution:** qualify both implementation AND configuration. Reject ignore_stop_signal=True and arbitrary callbacks before worker admission, or remove these test-only hooks from the registered runtime implementation. Keep uncooperative fault injection in separate private test adapters that the production registry rejects; do not add another equivalent escape hatch. Use interruptible event waiting for the approved adapter's delay and validate the supported cleanup contract. Alternatively use an actually terminable execution boundary for arbitrary callback/test execution.

Regression must instantiate the exact registered class with dangerous options and prove rejection before claim/funding/execution. The normal approved configuration must stop with no surviving adapter activity, late file effects or accepted late results after the observation window.

### Medium Severity

- Deadline validation claims finite numbers but checks only type and >0. Independent construction with execution_timeout_s=float('inf') succeeds. Use math.isfinite and explicit permitted bounds for execution, cleanup, heartbeat, lease and polling values. Reject booleans, NaN/Infinity and incompatible timing relationships; tests must cover inherited/default adapter cleanup values too.
- Pre-spawn still permits missing reservation rows. Keep low-level compatibility separate from worker-admissible funded intents; require an explicit valid policy/funding record in the supported worker path before future live dispatch.

### Low Severity

- Correct the handoff claim “confirmed bounded termination” until unsafe registered configurations are rejected and measured stop tests pass.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Class allowlist improves routing but configuration can negate its cancellation guarantee.
- **Data:** Holds preserve uncertainty; timed-out execution must not continue changing external state through admitted callbacks.
- **AI:** Only synthetic scaffolding exists here; runtime adapters remain separately gated.
- **Resilience/Governance:** Finite timing and registry configuration validation remain necessary.

## 4. Architect’s Action Directive

1. Antigravity removes or rejects stop-disabling/callback hooks from qualified worker adapters. Keep fault injection outside the qualified registry.
2. Enforce finite bounded timing values and approved cleanup behavior, including defaults; add exact-class dangerous configuration regressions.
3. Submit measured targeted/full checks and corrected candidate. CC-03 stays accepted; CC-04/live dispatch remains gated. Preserve same board/branch and prior milestones.

## Independent evidence

Exact registered class probe: worker_return_seconds=.026, file_at_return=false, file_after_return=true, intent=UNKNOWN_EXECUTION. Infinite execution timeout accepted. No live agent processes, production credentials or deployed board used; no backend code changed; full gate not independently repeated after reproduced blocker.

Independent targeted command: `python -m pytest tests/test_cc04_scheduler_worker.py tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_pm_evidence_bindings.py tests/test_coordinator_contract_sql.py tests/test_sba_03_plan_publication.py tests/test_scrum_board_actions.py -q`: **140 passed in 72.73 seconds**, no failures/skips. These do not cover the registered unsafe configuration reproduction. Reported skips remain unexecuted.
