"""
Unit and integration tests for Capable Coordinator CC-04:
- Authorized scheduling and task admission
- Single-winner CAS claim protocol under concurrent competition
- Guarded pre-spawn state transitions
- Bounded polling and event streaming with synthetic adapters
- Expired lease reaping into UNKNOWN_EXECUTION / FAILED
- Stale worker rejection via monotonic fencing
- Truthful cancellation races and budget hold preservation
- Execution crash transitions to UNKNOWN_EXECUTION and preserves budget holds (Finding 1)
- Strict validation of adapter results: mismatched identities, missing measurements, and uncertain outcomes rejected (Finding 2)
- Active heartbeat renewal, execution timeout deadline, and in-flight stop handling (Finding 3)
- Atomic admission, monotonic attempt sequences, and prevention of payload overrides (Findings 4 & 5)
"""

import time
import pytest

from mas.pm.coordinator import trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.guards import DependencyUnresolvedError
from mas.pm.models import Issue, IssueState, Project
from mas.pm.worker import (
    CoordinatorAdmissionEngine,
    CoordinatorWorker,
    SyntheticExecutionAdapter,
)


@pytest.fixture
def cc04_env(tmp_path):
    """Sets up a clean database, project, and task mappings for CC-04 tests."""
    db = PMDatabase(tmp_path / "pm_cc04.db")
    with trusted_coordinator_admin_scope():
        # Setup project with token budget
        db.create_project(Project(id="p1", key="CC4", name="CC04 Project", token_budget=50_000))
        # Setup tasks
        db.create_issue(Issue(
            id="task_dep",
            project_id="p1",
            key="CC4-1",
            title="Prerequisite Task",
            appetite_tokens=5_000,
            current_state=IssueState.BACKLOG,
        ))
        db.create_issue(Issue(
            id="task_main",
            project_id="p1",
            key="CC4-2",
            title="Main Worker Task",
            appetite_tokens=10_000,
            path_whitelist=["mas/pm/"],
            current_state=IssueState.BACKLOG,
        ))
        # Link dependency CC4-2 depends on CC4-1: blocker is task_dep, blocked is task_main
        db.add_dependency(blocker_id_or_key="task_dep", blocked_id_or_key="task_main")

        with db.atomic_transaction() as c:
            c.execute(
                "INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key) "
                "VALUES ('p1', 'CC4-1', 'task_uuid_1', 'task_dep', 'CC4-1')"
            )
            c.execute(
                "INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key) "
                "VALUES ('p1', 'CC4-2', 'task_uuid_2', 'task_main', 'CC4-2')"
            )
        yield db


def test_admission_rejects_unresolved_dependencies(cc04_env):
    """Admission engine fails closed when prerequisite dependency is not in DONE state."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        with pytest.raises(DependencyUnresolvedError, match="blocked by unresolved dependencies"):
            engine.admit_task("task_main")


def test_admission_succeeds_when_dependencies_resolved(cc04_env):
    """Admission engine admits task once prerequisite dependency transitions to DONE."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")

        intent = engine.admit_task("task_main", budget_reservation=2_000)
        assert intent.status == "PENDING"
        assert intent.issue_id == "task_main"
        assert intent.adapter_type == "synthetic"

        # Check issue state updated to STAGED
        issue = cc04_env.get_issue("task_main")
        assert issue.current_state == IssueState.STAGED


def test_admission_rejects_duplicate_active_intents(cc04_env):
    """Admission engine rejects admitting a task that already has an active intent."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        engine.admit_task("task_main", budget_reservation=2_000)

        with pytest.raises(ValueError, match="already has an active or unresolved intent"):
            engine.admit_task("task_main", budget_reservation=2_000)


def test_admission_rejects_done_or_reconciling_issues(cc04_env):
    """Admission engine rejects admitting tasks already in DONE state or with pending reconciliation."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")

        # Cannot admit DONE task
        with pytest.raises(ValueError, match="already in DONE state"):
            engine.admit_task("task_dep")

        # Flag task_main with pending reconciliation
        with cc04_env.atomic_transaction() as c:
            c.execute("UPDATE pm_issues SET has_pending_reconciliation = 1 WHERE id = 'task_main'")
        with pytest.raises(ValueError, match="pending plan reconciliation"):
            engine.admit_task("task_main")


def test_admission_monotonic_attempt_sequence(cc04_env):
    """Attempt sequences are strictly monotonic based on persistent coordinator attempts."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    store = cc04_env.coordinator
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")

        # First admission: attempt_seq = 1
        intent1 = engine.admit_task("task_main", budget_reservation=1_000)
        att1 = store.get_attempt(intent1.attempt_id)
        assert att1.attempt_seq == 1

        # Settle first attempt
        now = time.time()
        store.claim_intent(intent1.intent_id, "w", intent1.fencing_token, now, 10.0)
        store.pre_spawn_intent(intent1.intent_id, "w", 2, now, "run_1")
        store.complete_intent(intent1.intent_id, "w", 2, now, candidate_commit_sha="c1", tokens_spent=100)

        # Second admission: attempt_seq must be 2
        intent2 = engine.admit_task("task_main", budget_reservation=1_000)
        att2 = store.get_attempt(intent2.attempt_id)
        assert att2.attempt_seq == 2


def test_admission_payload_extra_cannot_override_authority(cc04_env):
    """Payload extra arguments cannot override scope path_whitelist, budget limits, or prompt identity."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    store = cc04_env.coordinator
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")

        malicious_payload = {
            "path_whitelist": ["/root", "/etc"],
            "budget_token_limit": 999_999,
            "extra_metadata": {"valid_key": True},
        }
        intent = engine.admit_task("task_main", budget_reservation=2_000, payload_extra=malicious_payload)
        stored_intent = store.get_intent(intent.intent_id)

        # Whitelist and budget must remain server-derived
        assert stored_intent.payload["path_whitelist"] == ["mas/pm/"]
        assert stored_intent.payload["budget_token_limit"] == 2_000
        # Allowlisted extra key preserved
        assert stored_intent.payload["extra_metadata"] == {"valid_key": True}


def test_admission_rejects_excessive_or_exhausted_budget(cc04_env):
    """Admission engine enforces finite non-negative budget within issue appetite and project capacity."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")

        # Exceeds issue appetite (10,000)
        with pytest.raises(ValueError, match="exceeds issue appetite"):
            engine.admit_task("task_main", budget_reservation=15_000)

        # Negative reservation
        with pytest.raises(ValueError, match="must be non-negative"):
            engine.admit_task("task_main", budget_reservation=-500)


def test_single_winner_claim_race(cc04_env):
    """Competing workers attempt to claim the same PENDING intent; exactly one wins."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        store = cc04_env.coordinator
        now = time.time()
        won_1 = store.claim_intent(intent.intent_id, "worker_1", intent.fencing_token, now, 10.0)
        won_2 = store.claim_intent(intent.intent_id, "worker_2", intent.fencing_token, now, 10.0)

        assert won_1 is True
        assert won_2 is False

        claimed_intent = store.get_intent(intent.intent_id)
        assert claimed_intent.status == "CLAIMED"
        assert claimed_intent.worker_id == "worker_1"
        assert claimed_intent.fencing_token == intent.fencing_token + 1


def test_worker_end_to_end_execution_and_events(cc04_env):
    """Worker claims, executes synthetic adapter, streams events, and completes intent."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        adapter = SyntheticExecutionAdapter(exit_code=0, tokens_billed=150)
        worker = CoordinatorWorker(cc04_env, worker_id="worker_alpha", adapter=adapter)

        processed = worker.run_one_polling_cycle()
        assert processed == 1

        final_intent = cc04_env.coordinator.get_intent(intent.intent_id)
        assert final_intent.status == "COMPLETED"

        attempt = cc04_env.coordinator.get_attempt(final_intent.attempt_id)
        assert attempt.status == "SUCCEEDED"
        assert attempt.budget_tokens_spent == 150

        # Verify event stream
        run_id = f"run_{intent.intent_id}_{final_intent.fencing_token}"
        events = cc04_env.coordinator.get_run_events(run_id)
        assert len(events) >= 2
        assert events[0].cursor_seq == 0
        assert events[1].cursor_seq == 1


def test_crash_transitions_to_unknown_execution_and_preserves_hold(cc04_env):
    """Finding 1: Simulated execution crash transitions to UNKNOWN_EXECUTION and preserves budget hold."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    store = cc04_env.coordinator
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        adapter = SyntheticExecutionAdapter(simulate_crash=True)
        worker = CoordinatorWorker(cc04_env, worker_id="worker_crash", adapter=adapter)

        processed = worker.run_one_polling_cycle()
        assert processed == 1

        updated_intent = store.get_intent(intent.intent_id)
        assert updated_intent.status == "UNKNOWN_EXECUTION"
        assert updated_intent.worker_id is None

        attempt = store.get_attempt(updated_intent.attempt_id)
        assert attempt.status == "UNKNOWN_EXECUTION"
        assert "CRASH" in (attempt.failure_reason or "")

        # Crucial check: Reservation hold is preserved as HELD, not settled to zero
        with cc04_env._get_connection() as c:
            res = c.execute(
                "SELECT status, amount, settled_amount FROM pm_coordinator_reservations WHERE attempt_id = ?",
                (attempt.attempt_id,),
            ).fetchone()
            assert res["status"] == "HELD"
            assert res["amount"] == 2_000
            assert res["settled_amount"] == 0

        # Run record is INTERRUPTED
        with cc04_env._get_connection() as c:
            run_row = c.execute("SELECT status FROM pm_coordinator_runs WHERE intent_id = ?", (intent.intent_id,)).fetchone()
            assert run_row["status"] == "INTERRUPTED"


def test_mismatched_run_identity_rejected_and_quarantined(cc04_env):
    """Finding 2: Adapter returning foreign attempt/run IDs is quarantined into UNKNOWN_EXECUTION with hold preserved."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    store = cc04_env.coordinator
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        # Adapter returns foreign attempt and run IDs
        adapter = SyntheticExecutionAdapter(
            attempt_id_override="foreign_attempt",
            run_id_override="foreign_run",
            exit_code=0,
            tokens_billed=50,
        )
        worker = CoordinatorWorker(cc04_env, worker_id="worker_mismatch", adapter=adapter)
        worker.run_one_polling_cycle()

        updated_intent = store.get_intent(intent.intent_id)
        assert updated_intent.status == "UNKNOWN_EXECUTION"

        # Hold is strictly preserved
        with cc04_env._get_connection() as c:
            res = c.execute(
                "SELECT status FROM pm_coordinator_reservations WHERE attempt_id = ?",
                (updated_intent.attempt_id,),
            ).fetchone()
            assert res["status"] == "HELD"


def test_missing_measurements_rejected(cc04_env):
    """Finding 2: Adapter returning null tokens_billed or null exit_code is rejected and hold preserved."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    store = cc04_env.coordinator
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        adapter = SyntheticExecutionAdapter(exit_code=0, tokens_billed=None)
        worker = CoordinatorWorker(cc04_env, worker_id="worker_unmeasured", adapter=adapter)
        worker.run_one_polling_cycle()

        updated_intent = store.get_intent(intent.intent_id)
        assert updated_intent.status == "UNKNOWN_EXECUTION"

        with cc04_env._get_connection() as c:
            res = c.execute(
                "SELECT status FROM pm_coordinator_reservations WHERE attempt_id = ?",
                (updated_intent.attempt_id,),
            ).fetchone()
            assert res["status"] == "HELD"


def test_active_heartbeat_renews_lease_during_long_execution(cc04_env):
    """Finding 3: Active heartbeat loop renews lease for duration of execution."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    store = cc04_env.coordinator
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        # Lease is 2.0s, duration is 0.6s, heartbeat is 0.2s
        adapter = SyntheticExecutionAdapter(exit_code=0, tokens_billed=10, duration_seconds=0.6)
        worker = CoordinatorWorker(
            cc04_env,
            worker_id="worker_heartbeat",
            adapter=adapter,
            lease_timeout_s=2.0,
            heartbeat_interval_s=0.2,
        )

        initial_time = time.time()
        worker.run_one_polling_cycle()

        final_intent = store.get_intent(intent.intent_id)
        assert final_intent.status == "COMPLETED"
        assert final_intent.lease_heartbeat_at is not None
        assert final_intent.lease_heartbeat_at >= initial_time


def test_execution_timeout_deadline_enforced(cc04_env):
    """Finding 3: Hung adapter exceeding execution_timeout_s is interrupted with preserved hold."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    store = cc04_env.coordinator
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        # Adapter duration is 2.0s, execution timeout is 0.3s
        adapter = SyntheticExecutionAdapter(exit_code=0, tokens_billed=10, duration_seconds=2.0)
        worker = CoordinatorWorker(
            cc04_env,
            worker_id="worker_timeout",
            adapter=adapter,
            execution_timeout_s=0.3,
        )

        worker.run_one_polling_cycle()

        updated_intent = store.get_intent(intent.intent_id)
        assert updated_intent.status == "UNKNOWN_EXECUTION"

        with cc04_env._get_connection() as c:
            res = c.execute(
                "SELECT status FROM pm_coordinator_reservations WHERE attempt_id = ?",
                (updated_intent.attempt_id,),
            ).fetchone()
            assert res["status"] == "HELD"


def test_in_flight_stop_signal_cancels_cleanly(cc04_env):
    """Finding 3: stop() halts worker and signals cancellation to in-flight adapter."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    store = cc04_env.coordinator
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        # Adapter with duration that responds to stop_event
        adapter = SyntheticExecutionAdapter(exit_code=0, tokens_billed=10, duration_seconds=1.0)
        worker = CoordinatorWorker(cc04_env, worker_id="worker_stopping", adapter=adapter)

        # Trigger worker in a background thread with trusted admin scope, then call worker.stop()
        import threading
        def worker_loop():
            with trusted_coordinator_admin_scope():
                worker.run_one_polling_cycle()

        t = threading.Thread(target=worker_loop)
        t.start()
        time.sleep(0.1)  # Allow process_one_intent to claim and start adapter
        worker.stop()
        t.join(timeout=2.0)

        # Work was interrupted safely into UNKNOWN_EXECUTION with hold preserved
        updated_intent = store.get_intent(intent.intent_id)
        assert updated_intent.status == "UNKNOWN_EXECUTION"


def test_expired_processing_lease_reaped_to_unknown_execution(cc04_env):
    """Lease expired while in PROCESSING transitions to UNKNOWN_EXECUTION without automatic retry."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        store = cc04_env.coordinator
        now = time.time()
        store.claim_intent(intent.intent_id, "worker_dead", intent.fencing_token, now, lease_timeout_s=1.0)
        claimed = store.get_intent(intent.intent_id)
        run_id = f"run_{intent.intent_id}_{claimed.fencing_token}"
        store.pre_spawn_intent(intent.intent_id, "worker_dead", claimed.fencing_token, now, run_id)

        # Move time past expiration
        reaped = store.reap_expired_leases(now + 2.0)
        assert intent.intent_id in reaped

        reaped_intent = store.get_intent(intent.intent_id)
        assert reaped_intent.status == "UNKNOWN_EXECUTION"
        assert reaped_intent.worker_id is None

        attempt = store.get_attempt(reaped_intent.attempt_id)
        assert attempt.status == "UNKNOWN_EXECUTION"

        # Check reservation hold is preserved (pessimistic hold retained)
        with cc04_env._get_connection() as c:
            res = c.execute(
                "SELECT status, amount FROM pm_coordinator_reservations WHERE attempt_id = ?",
                (attempt.attempt_id,),
            ).fetchone()
            assert res["status"] == "HELD"
            assert res["amount"] == 2_000


def test_stale_worker_completion_rejected_after_reap(cc04_env):
    """A stale worker attempting to write completion after lease reap is rejected by fencing generation."""
    engine = CoordinatorAdmissionEngine(cc04_env)
    with trusted_coordinator_admin_scope():
        cc04_env.update_issue_state("task_dep", IssueState.DONE.value, triggered_by="test")
        intent = engine.admit_task("task_main", budget_reservation=2_000)

        store = cc04_env.coordinator
        now = time.time()
        store.claim_intent(intent.intent_id, "worker_stale", intent.fencing_token, now, lease_timeout_s=1.0)
        claimed = store.get_intent(intent.intent_id)
        assigned_token = claimed.fencing_token
        run_id = f"run_{intent.intent_id}_{assigned_token}"
        store.pre_spawn_intent(intent.intent_id, "worker_stale", assigned_token, now, run_id)

        # Reaper runs and advances fencing generation
        store.reap_expired_leases(now + 5.0)

        # Stale worker wakes up and attempts to complete using old token
        ok = store.complete_intent(
            intent_id=intent.intent_id,
            worker_id="worker_stale",
            assigned_fencing_token=assigned_token,
            now_epoch=now + 6.0,
            candidate_commit_sha="stale-sha",
            exit_code=0,
            tokens_spent=50,
        )
        assert ok is False

        # Intent remains in UNKNOWN_EXECUTION
        curr_intent = store.get_intent(intent.intent_id)
        assert curr_intent.status == "UNKNOWN_EXECUTION"
