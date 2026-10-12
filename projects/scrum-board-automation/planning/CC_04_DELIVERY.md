# CC-04 Delivery: Authorized Scheduling & Task Admission Worker

**Date:** 12 October 2026  
**Baseline:** `0457e767` (Independent Review & Acceptance of CC-03 `a0c0aa51`)  
**Delivery Owner:** Antigravity (Backend, Engine, Runtime Integration)  
**Reviewer:** Codex / Independent Reviewer  
**Workstream:** Capable Coordinator (Priority 1)  
**Contract Reference:** `CC_02_COORDINATOR_CONTRACT.md` (Sections 4, 5, 7)  

---

## 1. Executive Summary & Delivered Architecture

Following the independent review and acceptance of CC-03, this delivery implements **CC-04** (`Implement authorized scheduling and task admission`) without activating live agent dispatch or modifying unapproved files.

### Key Implemented Capabilities:
1. **Task Admission Engine (`CoordinatorAdmissionEngine` in `mas.pm.worker`):**
   - **Dependency Readiness:** Enforces that all prerequisite dependencies in `pm_dependencies` are resolved to `DONE` state via `validate_dependencies()`. Blocks admission closed with `DependencyUnresolvedError`.
   - **Funded Execution Appetite:** Enforces finite non-negative integer budget reservations within issue appetite quotas and available project token capacities (`token_budget - tokens_consumed - open_holds`). Rejects proposed/planning budgets without allocated funds.
   - **Concurrency Guards:** Prevents duplicate concurrent executions on the same issue by checking for active `PENDING`, `CLAIMED`, `PROCESSING`, or `CANCEL_REQUESTED` intents.
   - **State Progression:** Atomically stages eligible issues to `STAGED` upon creating the outbox intent.
2. **Outbox Polling Worker (`CoordinatorWorker` in `mas.pm.worker`):**
   - **Single-Winner CAS Claims:** Executes atomic compare-and-swap claims on strictly `PENDING` intents with generation tokens, assigning worker ID and lease expiration epoch.
   - **Guarded Pre-Spawn Persistence:** Transitions `CLAIMED` intents to `PROCESSING` with run record creation and attempt progression to `RUNNING` inside a single transaction before dispatch.
   - **Event Cursor Streaming:** Streams monotonic event cursors (`0, 1, 2, ...`) directly into `pm_coordinator_events` without transaction locks.
   - **Bounded Polling & Jitter:** Configurable polling loops with backoff and graceful shutdown controls (`start_bounded()`, `stop()`).
3. **Lease Reaper & Expired Execution Engine:**
   - Periodically reaps expired leases:
     - Pre-spawn `CLAIMED` expiration -> `FAILED` (`CLAIM_TIMEOUT_PRE_SPAWN`).
     - In-flight `PROCESSING` expiration -> **`UNKNOWN_EXECUTION`**.
   - **Strict No-Redispatch Policy:** Automatically re-claiming or retrying `UNKNOWN_EXECUTION` work is prohibited.
   - **Pessimistic Hold Settlement:** Token budget reservations remain held (`HELD`) rather than released until authoritative termination/settlement.
4. **Controlled Synthetic Execution Adapter (`SyntheticExecutionAdapter`):**
   - Standardized adapter interface (`BaseExecutionAdapter`, `AdapterExecutionRequest`, `AdapterExecutionResult`).
   - Synthetic adapter verifies end-to-end scheduling and event emission without external process dependencies.
   - **Live agent dispatch (`agy` and `codex exec`) remains strictly gated.**

---

## 2. Regression & Verification Evidence

### 2.1 Targeted Test Suite
```bash
python3 -m pytest \
  tests/test_cc04_scheduler_worker.py \
  tests/test_cc03_final_corrections.py \
  tests/test_cc_03_coordinator_state.py \
  tests/test_pm_evidence_bindings.py \
  tests/test_coordinator_contract_sql.py \
  tests/test_sba_03_plan_publication.py \
  tests/test_scrum_board_actions.py -q
```
- **Result:** `120 passed in 35.51s` (zero failures, zero skips).
- **Coverage Highlights:**
  - `test_admission_rejects_unresolved_dependencies`: Verifies fail-closed dependency gates.
  - `test_admission_succeeds_when_dependencies_resolved`: Verifies staging once blockers reach `DONE`.
  - `test_admission_rejects_duplicate_active_intents`: Verifies single-active-intent invariant per issue.
  - `test_admission_rejects_excessive_or_exhausted_budget`: Verifies funded appetite caps.
  - `test_single_winner_claim_race`: Verifies concurrent CAS claim competition has exactly one winner.
  - `test_worker_end_to_end_execution_and_events`: Verifies full dispatch, execution, event cursors, and completion.
  - `test_expired_processing_lease_reaped_to_unknown_execution`: Verifies lease timeout reaper into `UNKNOWN_EXECUTION` with preserved budget holds.
  - `test_stale_worker_completion_rejected_after_reap`: Verifies stale worker outputs rejected via fencing tokens.

### 2.2 Full Quality Gate
```bash
bash scripts/run_quality_gate.sh
```
- **Stages Executed:**
  - [GATE 1/5] Code Style & Lints (`ruff check mas tests`): PASSED
  - [GATE 2/5] Runtime Health & Capabilities Matrix (`doctor`, `capabilities`): PASSED
  - [GATE 3/5] Local Research Assets & Links: PASSED
  - [GATE 4/5] Python Source Compilation: PASSED
  - [GATE 5/5] Full Test Suite: **660 passed, 20 skipped in 159.91s**
- **Outcome:** **`ALL QUALITY GATES PASSED (5/5)`**

---

## 3. Independent Handoff & Boundaries

- Implemented in `mas/pm/worker.py` and `mas/pm/coordinator.py`.
- Tests added in `tests/test_cc04_scheduler_worker.py`.
- No board records or task UUIDs altered.
- Live CLI dispatch remains disabled pending explicit CC-05 adapter integration approval.
