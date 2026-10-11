# CC-03 Delivery: Durable Coordinator State and Outbox Storage

**Delivery Date:** 2026-10-11  
**Target Branch:** `feat/scrum-board-automation`  
**Delivery Scope:** CC-03 — Durable coordinator state, relational persistence schemas, outbox storage, and recovery tests.  
**Implementation Owner:** Antigravity (Backend, Engine, Runtime Integration)  
**Reviewer:** Codex (Frontend, UI/UX, Interface Requirements) / Independent Reviewer  
**Status:** **SUBMITTED FOR REVIEW** (Not self-certified as DONE per delivery ownership agreement).

---

## 1. Executive Summary

This delivery implements the complete persistence foundation and atomic lifecycle state management for **Capable Coordinator (CC-03)** in accordance with the accepted CC-02 contract specification ([`CC_02_COORDINATOR_CONTRACT.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/CC_02_COORDINATOR_CONTRACT.md)) and the resolution of all previous review findings.

The implementation establishes durable outbox records, attempts, physical runs, event cursors, and cryptographic evidence receipts without adding live agent dispatch or claiming runtime execution.

### Key Architectural Guarantees:
1. **Non-Destructive Additive Migration:** Existing `pm_task_mappings`, `pm_issues`, `pm_projects`, and `pm_evidence_links` schemas and records are preserved unconditionally. The additive column `legacy_task_id` is introduced alongside composite identity indices (`uq_coord_mapping_identity`, `uq_coord_issue_project`) to enable enforceable relational integrity.
2. **Strict Relational Ownership:** Multi-column composite foreign keys enforce that attempts, outbox intents, and physical runs cannot cross tenant, project, or task boundaries. Contradictory ownership is rejected directly at the SQLite database engine level.
3. **Atomic CAS Claims (Unlaunched Work Only):** Compare-And-Swap dispatch claims exclusively target `status = 'PENDING'` intents. Expired `PROCESSING` work is excluded from the claim path, eliminating redispatch hazards.
4. **Guarded Pre-Spawn Persistence (`SPAWN_INTENT`):** Before any physical run is spawned, the worker commits `status = 'PROCESSING'` and registers a `SPAWNING` run in a single atomic transaction requiring matching assigned worker, active generation token, and unexpired lease.
5. **Durable `UNKNOWN_EXECUTION` & Pessimistic Budget Holds:** When an in-flight worker's lease expires post-spawn, the reaper transitions the intent and attempt to `UNKNOWN_EXECUTION` and increments the fencing token. Automatic retries are strictly halted, and the full allocated token reservation is retained as a hold against project quotas.
6. **Cancellation vs. Late Results:** Cancellation advances the generation token atomically. Stale workers attempting completion after cancellation or reaping receive zero updated rows; late results are dropped.

---

## 2. Implemented Components & Schemas

### 2.1 Additive Persistence Schema ([`mas/pm/db.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/db.py))
- **`pm_coordinator_attempts`:** Tracks attempt iterations (`attempt_seq`), token budget reservation (`budget_tokens_allocated`), token spend (`budget_tokens_spent`), candidate commit SHA, status (`PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `UNKNOWN_EXECUTION`, `CANCELED`), and fencing generation.
- **`pm_coordinator_intents`:** Outbox storage tracking adapter type (`antigravity`, `codex`, `synthetic`), dispatch status, worker assignment, lease expiration/heartbeats, payload, and monotonic fencing generation.
- **`pm_coordinator_runs`:** Physical execution tracking with `uq_physical_dispatch UNIQUE (intent_id, fencing_token)`, enforcing that only one physical process run can be admitted per dispatch generation.
- **`pm_coordinator_events`:** Monotonic event cursor stream tracking with `uq_run_cursor UNIQUE (run_id, cursor_seq)`.
- **`pm_coordinator_evidence_receipts`:** Admitted evidence store enforcing `nonce UNIQUE` for cryptographic replay protection.

### 2.2 Data Models ([`mas/pm/models.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/models.py))
Added strongly typed Pydantic models:
- `CoordinatorAttempt`
- `CoordinatorIntent`
- `CoordinatorRun`
- `CoordinatorEvent`
- `CoordinatorEvidenceReceipt`
- Updated `TaskMapping` with optional `legacy_task_id: Optional[str] = None`.

### 2.3 Coordinator Service Engine ([`mas/pm/coordinator.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/coordinator.py))
`CoordinatorStore` provides atomic lifecycle operations:
- `create_attempt()` & `create_intent()`: Enforce composite relational ownership.
- `create_attempt_with_intent()`: Atomic transaction reserving execution budget and staging outbox intent.
- `claim_intent()`: Atomic CAS claim query advancing fencing token.
- `pre_spawn_intent()`: Guarded pre-spawn persistence inserting run record before process launch.
- `heartbeat_intent()`: Renews unexpired lease; rejects expired leases.
- `complete_intent()`: Guarded completion settling actual token spend and updating run status.
- `reap_expired_leases()`: Differentiates pre-spawn (`FAILED`) vs post-spawn (`UNKNOWN_EXECUTION`) lease expiration.
- `cancel_intent()`: Advances generation and cancels intent/attempt/run.
- `record_run_event()`: Ingests streaming event cursors.
- `record_evidence_receipt()`: Enforces nonce replay prevention.

---

## 3. Empirical Verification & Test Evidence

### 3.1 Targeted Test Suite Execution
```bash
python3 -m pytest \
  tests/test_cc_03_coordinator_state.py \
  tests/test_pm_evidence_bindings.py \
  tests/test_coordinator_contract_sql.py \
  tests/test_sba_03_plan_publication.py \
  tests/test_scrum_board_actions.py -q
```
**Outcome:** `90 passed in 31.16s`.

### 3.2 Full Repository Quality Gate Execution
```bash
bash scripts/run_quality_gate.sh
```
**Outcome:** `629 passed, 20 skipped in 144.12s (0:02:24)`.  
**Verdict:** `✅ ALL QUALITY GATES PASSED (5/5)`.

### 3.3 Verification Matrix of Required Scenarios

| Test Case | Method in `test_cc_03_coordinator_state.py` | Result |
| :--- | :--- | :--- |
| **Populated Legacy DB Migration & Reopen** | `test_populated_legacy_database_migration_and_reopen` | **PASSED** |
| **Identity, State, Assignment Preservation** | `test_identity_state_assignment_evidence_preservation` | **PASSED** |
| **Cross-Tenant & Contradictory Ownership Rejection** | `test_cross_tenant_and_contradictory_ownership_rejection` | **PASSED** |
| **Concurrent Claims (Single Winner)** | `test_concurrent_claims_single_winner` | **PASSED** |
| **Reaper vs. Pre-Spawn Race** | `test_reaper_versus_pre_spawn_race` | **PASSED** |
| **Cancellation vs. Late Results** | `test_cancellation_versus_late_results` | **PASSED** |
| **Expired Heartbeat Rejection** | `test_expired_heartbeat_rejection` | **PASSED** |
| **Crashes Before vs. After Pre-Spawn** | `test_crashes_before_and_after_pre_spawn` | **PASSED** |
| **Duplicate Physical-Run Rejection** | `test_duplicate_physical_run_rejection` | **PASSED** |
| **Uncertain Execution Budget Hold Retention** | `test_uncertain_execution_retains_budget_holds` | **PASSED** |
| **Event Cursor & Nonce Replay Prevention** | `test_event_cursor_and_evidence_receipt_uniqueness` | **PASSED** |

---

## 4. Operational Boundaries & Next Steps

1. **Storage-Only Milestone:** Storage records attest to durable coordinator state and outbox tracking. No live CLI processes (`agy` or `codex exec`) were invoked in this milestone; execution was not simulated as completed.
2. **Frontend Preservation:** Frontend milestone commit `77ba7083` remains intact; all 23 browser action tests in `tests/test_scrum_board_actions.py` pass without regression.
3. **Next Dependency-Ready Task:** **CC-04 (Outbox Worker & Lease Reaper Background Daemon)** — Implementation of background polling worker, lease reaper loop, and transition dispatching based on this persistence layer.
