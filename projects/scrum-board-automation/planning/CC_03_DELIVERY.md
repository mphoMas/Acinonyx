# CC-03 Delivery: Durable Coordinator State and Outbox Storage (Remediated)

**Delivery Date:** 2026-10-12  
**Target Branch:** `feat/scrum-board-automation`  
**Delivery Scope:** CC-03 — Durable coordinator state, relational persistence schemas, outbox storage, funded reservation ledger, tenant authority, truthful cancellation, and failure-recovery tests.  
**Implementation Owner:** Antigravity (Backend, Engine, Runtime Integration)  
**Reviewer:** Codex (Frontend, UI/UX, Interface Requirements) / Independent Reviewer  
**Status:** **SUBMITTED FOR REVIEW** (Strictly following delivery ownership agreement; not self-certified as DONE).

---

## 1. Executive Summary & Resolution of Blockers

This updated delivery resolves all five blockers and medium-severity findings detailed in [`CC_03_INDEPENDENT_REVIEW.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/CC_03_INDEPENDENT_REVIEW.md) (`fae7d566`):

1. **Run Ownership Enforcement & Composite Relational Integrity:**
   - In `CoordinatorStore.pre_spawn_intent`, the attempt identity is derived strictly from the intent record (`SELECT attempt_id FROM pm_coordinator_intents WHERE intent_id = ?`).
   - If a caller supplies an optional `attempt_id`, it is strictly verified against `intent["attempt_id"]`. Any contradiction immediately raises `ValueError` and rolls back the transaction.
   - Enforced composite foreign key `CONSTRAINT uq_intent_attempt_pair UNIQUE (intent_id, attempt_id)` on `pm_coordinator_intents` and composite foreign key `FOREIGN KEY(intent_id, attempt_id) REFERENCES pm_coordinator_intents(intent_id, attempt_id) ON DELETE CASCADE` on `pm_coordinator_runs`.
   - Covered by independent regression tests attempting contradictory attempt IDs and cross-project assignments with verified rollback.

2. **Truthful Cancellation:**
   - Distinguishes cancellation intent from observed runtime outcome.
   - For provably unlaunched work (`status = 'PENDING'`), cancellation immediately transitions both intent and attempt to `CANCELED` and releases the reservation hold in the ledger.
   - For potentially launched work (`status IN ('CLAIMED', 'PROCESSING')`), `cancel_intent` transitions the intent to `CANCEL_REQUESTED`, advances the fencing token to retire worker authority, clears `worker_id`, and advances the attempt's fencing token.
   - Crucially, physical runs are **NOT** fabricated as `KILLED` and attempts are **NOT** marked `CANCELED` without an authoritative termination receipt (`record_authoritative_termination()`). Token budget holds remain `HELD`.
   - Repeated cancellation requests are fully idempotent.

3. **Durable Funded Budget Reservation Ledger:**
   - Created table `pm_coordinator_reservations` tracking `reservation_id`, `tenant_id`, `project_id`, `issue_id`, `attempt_id`, `authorization_ref`, `amount`, `settled_amount`, `status ('HELD', 'SETTLED', 'RELEASED')`, and timestamps.
   - In `create_attempt_with_intent` (inside an atomic `BEGIN IMMEDIATE` transaction):
     - Validates that `budget_reservation` is a finite non-negative integer (rejecting bools, floats, strings, and negatives).
     - Validates against issue appetite: `budget_reservation <= issue.appetite_tokens`.
     - Validates against available project capacity: `available = token_budget - tokens_consumed - open_holds`, where `open_holds = SUM(amount - settled_amount) WHERE project_id = ? AND status = 'HELD'`. Rejects concurrent over-allocations.
     - Atomically logs the funded hold in `pm_coordinator_reservations`.

4. **Tenant Authority & Scoped Access:**
   - `CoordinatorStore` validates tenant authority on all mutations against active `current_binding()`.
   - Verifies `binding.identity.tenant_id == tenant_id`, rejecting mismatched tenant IDs with `PermissionError`.
   - Enforces `binding.require("storage:write")`.
   - Provides explicit `trusted_coordinator_admin_scope()` for local internal administrative execution.
   - Tested under multi-tenant IAM with valid, mismatched, and read-only credentials.

5. **Versioned Transactional Migration & Injected Rollback Verification:**
   - Implemented `pm_schema_migrations` table tracking migration version (`2026101201`), name (`cc_03_coordinator_state`), checksum (`cc03_sha256_composite_ownership_v1`), and application timestamp.
   - Migration executes inside an explicit `BEGIN IMMEDIATE;` ... `COMMIT;` transaction with `PRAGMA integrity_check`.
   - Additive column migrations inspect `PRAGMA table_info` before applying alterations.
   - Regression test injects a failure midway through migration to prove all-or-nothing rollback.

6. **Separating Observations from Claims (Raw vs. Admitted Evidence):**
   - Added `admission_status ('SUBMITTED', 'ADMITTED', 'REJECTED')` to `pm_coordinator_evidence_receipts`.
   - Raw receipts submitted by workers default to `SUBMITTED`, explicitly quarantining untrusted submissions until cryptographic admission.
   - `complete_intent` requires authoritative candidate commit SHA and exit code before settling tokens and recording `SUCCEEDED`/`EXITED`.

---

## 2. Implemented Components & Schemas

### 2.1 Relational Schemas ([`mas/pm/db.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/db.py))
- `pm_schema_migrations`: Versioned migration ledger.
- `pm_coordinator_attempts`: Tracks attempts, composite identity, allocated/spent tokens, and fencing tokens.
- `pm_coordinator_intents`: Outbox storage with composite `(intent_id, attempt_id)` unique constraint.
- `pm_coordinator_runs`: Physical execution tracking with composite FK `(intent_id, attempt_id)` and `uq_physical_dispatch UNIQUE (intent_id, fencing_token)`.
- `pm_coordinator_reservations`: Durable funded budget reservation ledger with status `HELD`, `SETTLED`, or `RELEASED`.
- `pm_coordinator_events`: Monotonic event cursor stream tracking with `uq_run_cursor UNIQUE (run_id, cursor_seq)`.
- `pm_coordinator_evidence_receipts`: Replay-protected receipt store with explicit `admission_status`.

### 2.2 Data Models ([`mas/pm/models.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/models.py))
- `CoordinatorAttempt`
- `CoordinatorIntent`
- `CoordinatorRun`
- `CoordinatorEvent`
- `CoordinatorEvidenceReceipt` (with `admission_status: str = "SUBMITTED"`)
- `CoordinatorReservation` (with `status: str = "HELD"`, amounts, refs)

### 2.3 Coordinator Service Engine ([`mas/pm/coordinator.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/coordinator.py))
- `trusted_coordinator_admin_scope()`
- `create_attempt_with_intent()` with funded capacity validation and reservation ledger recording.
- `claim_intent()` with atomic CAS update.
- `pre_spawn_intent()` with strictly derived attempt ownership and composite FK linking.
- `cancel_intent()` with truthful cancellation distinguishing unlaunched from potentially running work.
- `record_authoritative_termination()` for processing actual adapter/observer termination receipts.
- `complete_intent()` requiring authoritative candidate and exit code.
- `record_evidence_receipt()` with explicit admission status.

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
**Outcome:** `103 passed in 33.68s` (0 skips, 0 failures).

### 3.2 Full Repository Quality Gate Execution
```bash
bash scripts/run_quality_gate.sh
```
**Outcome:** `643 passed, 20 skipped in 149.49s (0:02:29)`.  
**Verdict:** `✅ ALL QUALITY GATES PASSED (5/5)`.

### 3.3 Verification Matrix of Scenarios (Including 8 Negative Acceptance Cases)

| Scenario / Negative Case | Method in `test_cc_03_coordinator_state.py` | Verdict |
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
| **Run Ownership & Contradictory Attempt Rejection** | `test_wrong_attempt_and_cross_project_ownership_rejection` | **PASSED** |
| **Truthful Cancellation: Unlaunched vs. Launched** | `test_truthful_cancellation_unlaunched_vs_launched` | **PASSED** |
| **Funded Reservation Ledger & Capacity Bounds** | `test_funded_reservation_ledger_and_capacity_bounds` | **PASSED** |
| **Tenant Authority & Scoped Access** | `test_tenant_authority_validation` | **PASSED** |
| **Schema Migration Atomic Rollback on Injected Failure** | `test_schema_migration_atomic_rollback_on_injected_failure` | **PASSED** |
| **Negative Case 1: Unbound caller denied on all mutations** | `test_negative_case_1_unbound_caller_every_mutation_denied` | **PASSED** |
| **Negative Case 2: Exit 42 records FAILED, never SUCCEEDED** | `test_negative_case_2_exit_42_records_failed_not_succeeded` | **PASSED** |
| **Negative Case 3: Reserve 10, spend 20 rejects overdraft** | `test_negative_case_3_reserve_10_spend_20_rejects_overdraft` | **PASSED** |
| **Negative Case 4: Termination with missing/foreign run** | `test_negative_case_4_termination_with_missing_or_foreign_run_zero_mutations` | **PASSED** |
| **Negative Case 5: Termination of COMPLETED rejected; exact replay idempotent** | `test_negative_case_5_termination_of_completed_rejected_and_receipt_replay_idempotent` | **PASSED** |
| **Negative Case 6: Cancellation spend charged once; unknown retains hold** | `test_negative_case_6_cancellation_spend_and_unknown_spend_retention` | **PASSED** |
| **Negative Case 7: Actual 284cb877 DB upgraded, constraints verified** | `test_negative_case_7_upgrade_from_actual_284cb877_schema` | **PASSED** |
| **Negative Case 8: Untrusted ADMITTED status forced to SUBMITTED** | `test_negative_case_8_caller_admitted_status_or_fake_receipt_cannot_obtain_trusted_admission` | **PASSED** |

---

## 4. Operational Boundaries

1. **Storage-Only Milestone:** CC-03 establishes relational persistence, outbox invariants, funded reservations, and truthful lifecycle state. No live agent daemon process is run in this milestone; storage records do not manufacture measured completion.
2. **Frontend & Codex Commits Preserved:** Commits `77ba7083` (frontend milestone), `03da60da` (Codex evidence binding fixes), and `d36a85fe` (fixture cleanup) remain intact; all browser and action tests pass without regression.
3. **No Premature Dispatch (CC-04):** CC-04 daemon dispatch remains strictly gated and will not begin until independent review approval.
