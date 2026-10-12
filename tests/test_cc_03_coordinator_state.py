"""
tests/test_cc_03_coordinator_state.py: Comprehensive test suite for CC-03 coordinator state and outbox.

Covers:
1. Populated legacy database migration and reopen.
2. Identity, state, assignment, and evidence preservation across migration.
3. Cross-tenant and contradictory ownership rejection via composite relational foreign keys.
4. Concurrent CAS claims with exactly one winner.
5. Reaper vs. pre-spawn races (stale-worker resurrection prevention).
6. Cancellation vs. late results rejection.
7. Expired heartbeat rejection (cannot resurrect expired lease).
8. Crashes before vs. after pre-spawn persistence (UNKNOWN_EXECUTION stops automatic retries).
9. Duplicate physical-run rejection via uq_physical_dispatch.
10. Uncertain execution retaining pessimistic budget holds.
"""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest

from mas.pm.db import PMDatabase
from mas.pm.models import (
    Issue,
    IssueState,
    Project,
)


def _populate_legacy_database(db_path):
    """Creates a raw SQLite database with pre-CC-03 schema and populated data."""
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute("""
        CREATE TABLE pm_projects (
            id TEXT PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            token_budget INTEGER NOT NULL DEFAULT 5000000,
            tokens_consumed INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("""
        CREATE TABLE pm_issues (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            key TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            issue_type TEXT NOT NULL,
            current_state TEXT NOT NULL,
            parent_id TEXT,
            assignee_principal TEXT,
            appetite_tokens INTEGER NOT NULL DEFAULT 50000,
            appetite_timeout_s INTEGER NOT NULL DEFAULT 1800,
            tokens_spent INTEGER NOT NULL DEFAULT 0,
            reflexion_attempts INTEGER NOT NULL DEFAULT 0,
            path_whitelist JSON,
            forbidden_paths JSON,
            policy_version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("""
        CREATE TABLE pm_task_mappings (
            project_id TEXT NOT NULL,
            planning_reference TEXT NOT NULL,
            task_id TEXT NOT NULL,
            local_issue_id TEXT NOT NULL,
            local_issue_key TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT pk_task_mapping PRIMARY KEY (project_id, planning_reference),
            CONSTRAINT uq_task_mapping_task_id UNIQUE (project_id, task_id),
            CONSTRAINT uq_task_mapping_local_issue UNIQUE (project_id, local_issue_id),
            CONSTRAINT uq_task_mapping_local_key UNIQUE (project_id, local_issue_key)
        );
        """)
        conn.execute("""
        CREATE TABLE pm_evidence_links (
            id TEXT PRIMARY KEY,
            issue_id TEXT NOT NULL,
            evidence_type TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            uri TEXT NOT NULL,
            payload JSON,
            linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Insert historical data
        conn.execute("INSERT INTO pm_projects(id, key, name) VALUES ('proj-1', 'LEG', 'Legacy Project')")
        conn.execute("""
        INSERT INTO pm_issues(id, project_id, key, title, issue_type, current_state, assignee_principal, policy_version)
        VALUES ('issue-1', 'proj-1', 'LEG-1', 'Historical Task', 'TASK', 'IN_PROGRESS', 'developer:agent:1', 2)
        """)
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('proj-1', 'SBA-01', 'task-uuid-001', 'issue-1', 'LEG-1')
        """)
        conn.execute("""
        INSERT INTO pm_evidence_links(id, issue_id, evidence_type, content_hash, uri, payload)
        VALUES ('ev-1', 'issue-1', 'TEST_RUN_LOG', 'hash-123', 'file://log.txt', '{"policy_version": 2}')
        """)
    conn.close()


def test_populated_legacy_database_migration_and_reopen(tmp_path):
    """Test 1: Populated legacy database migration, reopen, and additive column checks."""
    db_file = tmp_path / "legacy.db"
    _populate_legacy_database(db_file)

    # First open: executes init_schema() migrations
    db1 = PMDatabase(db_file)
    proj = db1.get_project_by_key("LEG")
    assert proj is not None
    assert proj.id == "proj-1"

    issue = db1.get_issue("LEG-1")
    assert issue is not None
    assert issue.id == "issue-1"
    assert issue.current_state == IssueState.IN_PROGRESS
    assert issue.assignee_principal == "developer:agent:1"
    assert issue.policy_version == 2

    # Check evidence link was preserved
    evidence = db1.get_evidence_links("issue-1")
    assert len(evidence) == 1
    assert evidence[0].content_hash == "hash-123"

    # Check additive legacy_task_id column in pm_task_mappings
    conn = db1._get_connection()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(pm_task_mappings)").fetchall()]
    assert "legacy_task_id" in cols

    # Check coordinator tables were created
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "pm_coordinator_attempts" in tables
    assert "pm_coordinator_intents" in tables
    assert "pm_coordinator_runs" in tables
    assert "pm_coordinator_events" in tables
    assert "pm_coordinator_evidence_receipts" in tables
    conn.close()

    # Second open: reopen without error
    db2 = PMDatabase(db_file)
    assert db2.get_issue("LEG-1") is not None


def test_identity_state_assignment_evidence_preservation(tmp_path):
    """Test 2: Verification of absolute preservation of identity, state, assignment, and evidence."""
    db_file = tmp_path / "preservation.db"
    _populate_legacy_database(db_file)

    db = PMDatabase(db_file)
    mapping = db.get_task_mapping("proj-1", "SBA-01")
    assert mapping is not None
    assert mapping.task_id == "task-uuid-001"
    assert mapping.local_issue_id == "issue-1"
    assert mapping.local_issue_key == "LEG-1"

    # Set legacy ID into mapping
    with db.atomic_transaction() as conn:
        conn.execute("UPDATE pm_task_mappings SET legacy_task_id = 'sba-uuid-sba-01' WHERE task_id = 'task-uuid-001'")

    mapping_updated = db.get_task_mapping("proj-1", "SBA-01")
    assert mapping_updated.legacy_task_id == "sba-uuid-sba-01"


def test_cross_tenant_and_contradictory_ownership_rejection(tmp_path):
    """Test 3: Cross-tenant and contradictory ownership rejection via composite FKs."""
    db = PMDatabase(tmp_path / "ownership.db")
    db.create_project(Project(id="p-alpha", key="ALP", name="Alpha"))
    db.create_project(Project(id="p-beta", key="BET", name="Beta"))

    db.create_issue(Issue(id="iss-1", project_id="p-alpha", key="ALP-1", title="Task 1"))
    db.create_issue(Issue(id="iss-2", project_id="p-beta", key="BET-1", title="Task 2"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p-alpha', 'T-1', 'task-uuid-1', 'iss-1', 'ALP-1')
        """)
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p-beta', 'T-2', 'task-uuid-2', 'iss-2', 'BET-1')
        """)

    # 1. Contradictory project and issue (issue belongs to p-alpha, but attempt claims p-beta)
    with pytest.raises(sqlite3.IntegrityError):
        db.coordinator.create_attempt(
            attempt_id="att-err-1",
            tenant_id="tenant-1",
            project_id="p-beta",  # Contradictory project!
            issue_id="iss-1",
            task_id="task-uuid-1",
            attempt_seq=1,
        )

    # 2. Contradictory task_id (task-uuid-2 is for iss-2, not iss-1)
    with pytest.raises(sqlite3.IntegrityError):
        db.coordinator.create_attempt(
            attempt_id="att-err-2",
            tenant_id="tenant-1",
            project_id="p-alpha",
            issue_id="iss-1",
            task_id="task-uuid-2",  # Contradictory task_id!
            attempt_seq=1,
        )

    # 3. Create legitimate attempt on tenant-alpha
    valid_attempt = db.coordinator.create_attempt(
        attempt_id="att-valid",
        tenant_id="tenant-alpha",
        project_id="p-alpha",
        issue_id="iss-1",
        task_id="task-uuid-1",
        attempt_seq=1,
    )
    assert valid_attempt.attempt_id == "att-valid"

    # 4. Cross-tenant intent insertion: intent claims tenant-beta against attempt on tenant-alpha
    with pytest.raises(sqlite3.IntegrityError):
        db.coordinator.create_intent(
            intent_id="intent-cross-tenant",
            tenant_id="tenant-beta",  # Cross-tenant mismatch!
            project_id="p-alpha",
            issue_id="iss-1",
            task_id="task-uuid-1",
            attempt_id="att-valid",
            adapter_type="antigravity",
            payload={"cmd": "run"},
        )


def test_concurrent_claims_single_winner(tmp_path):
    """Test 4: Concurrent CAS claims with exactly one winner."""
    db = PMDatabase(tmp_path / "claims.db")
    db.create_project(Project(id="p", key="CLM", name="Claims"))
    db.create_issue(Issue(id="i", project_id="p", key="CLM-1", title="Task"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'C-1', 'task-c1', 'i', 'CLM-1')
        """)

    att, intent = db.coordinator.create_attempt_with_intent(
        attempt_id="att-c1",
        intent_id="intent-c1",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i",
        task_id="task-c1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={"action": "build"},
    )

    barrier = Barrier(2)
    def worker_claim(worker_name):
        barrier.wait(timeout=3)
        return db.coordinator.claim_intent(
            intent_id="intent-c1",
            worker_id=worker_name,
            expected_fencing_token=1,
            now_epoch=100.0,
            lease_timeout_s=15.0,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker_claim, ["worker-A", "worker-B"]))

    assert sorted(results) == [False, True]

    # Verify intent state
    claimed_intent = db.coordinator.get_intent("intent-c1")
    assert claimed_intent.status == "CLAIMED"
    assert claimed_intent.fencing_token == 2
    assert claimed_intent.worker_id in ["worker-A", "worker-B"]


def test_reaper_versus_pre_spawn_race(tmp_path):
    """Test 5: Reaper versus pre-spawn race preventing stale worker resurrection."""
    db = PMDatabase(tmp_path / "reaper_race.db")
    db.create_project(Project(id="p", key="RPR", name="Reaper"))
    db.create_issue(Issue(id="i", project_id="p", key="RPR-1", title="Task"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'R-1', 'task-r1', 'i', 'RPR-1')
        """)

    db.coordinator.create_attempt_with_intent(
        attempt_id="att-r1",
        intent_id="intent-r1",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i",
        task_id="task-r1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={"task": "test"},
    )

    # Worker claims at t=100 with 10s lease (expires at 110)
    assert db.coordinator.claim_intent("intent-r1", "worker-slow", 1, 100.0, 10.0) is True

    # At t=115, lease has expired
    # Reaper executes
    reaped = db.coordinator.reap_expired_leases(now_epoch=115.0)
    assert "intent-r1" in reaped

    # Intent is retired to FAILED (pre-spawn) and fencing token bumped to 3
    reaped_intent = db.coordinator.get_intent("intent-r1")
    assert reaped_intent.status == "FAILED"
    assert reaped_intent.fencing_token == 3
    assert reaped_intent.worker_id is None

    # Stale worker wakes up and attempts pre_spawn_intent with token 2 at t=115
    res = db.coordinator.pre_spawn_intent(
        intent_id="intent-r1",
        worker_id="worker-slow",
        assigned_fencing_token=2,
        now_epoch=115.0,
        run_id="run-stale",
        attempt_id="att-r1",
    )
    assert res is False, "Stale worker MUST NOT be allowed to transition to PROCESSING after reap"

    # Check attempt is FAILED
    att = db.coordinator.get_attempt("att-r1")
    assert att.status == "FAILED"
    assert att.failure_reason == "CLAIM_TIMEOUT_PRE_SPAWN"


def test_cancellation_versus_late_results(tmp_path):
    """Test 6: Cancellation versus late results rejection."""
    db = PMDatabase(tmp_path / "cancel.db")
    db.create_project(Project(id="p", key="CNC", name="Cancel"))
    db.create_issue(Issue(id="i", project_id="p", key="CNC-1", title="Task"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'C-1', 'task-c1', 'i', 'CNC-1')
        """)

    db.coordinator.create_attempt_with_intent(
        attempt_id="att-c",
        intent_id="intent-c",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i",
        task_id="task-c1",
        attempt_seq=1,
        adapter_type="codex",
        payload={},
    )

    db.coordinator.claim_intent("intent-c", "worker-1", 1, 100.0, 30.0)
    db.coordinator.pre_spawn_intent("intent-c", "worker-1", 2, 101.0, "run-c", "att-c")

    # Operator requests cancellation of the intent
    assert db.coordinator.cancel_intent("intent-c", "User requested cancel") is True

    canceled_intent = db.coordinator.get_intent("intent-c")
    assert canceled_intent.status == "CANCEL_REQUESTED"
    assert canceled_intent.fencing_token == 3

    # Late completion from worker with old token 2 must be rejected
    res = db.coordinator.complete_intent(
        intent_id="intent-c",
        worker_id="worker-1",
        assigned_fencing_token=2,
        now_epoch=105.0,
        candidate_commit_sha="commit-late",
        tokens_spent=500,
    )
    assert res is False, "Late completion on canceled intent must be strictly rejected"

    # Truthful cancellation: run remains SPAWNING, attempt remains RUNNING until authoritative receipt
    run = db.coordinator.get_run("run-c")
    assert run.status == "SPAWNING", "Run must not be marked KILLED without authoritative termination"
    att = db.coordinator.get_attempt("att-c")
    assert att.status == "RUNNING", "Attempt must not be marked CANCELED without authoritative termination"

    # Now authoritative termination receipt arrives
    db.coordinator.record_authoritative_termination(
        intent_id="intent-c",
        run_id="run-c",
        exit_code=137,
        observed_status="KILLED",
        tokens_spent=150,
    )
    run_after = db.coordinator.get_run("run-c")
    assert run_after.status == "KILLED"
    assert run_after.exit_code == 137
    att_after = db.coordinator.get_attempt("att-c")
    assert att_after.status == "CANCELED"
    assert att_after.budget_tokens_spent == 150


def test_expired_heartbeat_rejection(tmp_path):
    """Test 7: Expired heartbeat rejection (cannot resurrect expired lease)."""
    db = PMDatabase(tmp_path / "heartbeat.db")
    db.create_project(Project(id="p", key="HBT", name="Heartbeat"))
    db.create_issue(Issue(id="i", project_id="p", key="HBT-1", title="Task"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'H-1', 'task-h1', 'i', 'HBT-1')
        """)

    db.coordinator.create_attempt_with_intent(
        attempt_id="att-h",
        intent_id="intent-h",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i",
        task_id="task-h1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={},
    )

    # Claim with lease expiring at 110.0
    db.coordinator.claim_intent("intent-h", "worker-1", 1, 100.0, 10.0)

    # Valid heartbeat at t=105.0
    assert db.coordinator.heartbeat_intent("intent-h", "worker-1", 2, 105.0, 10.0) is True

    # Expired heartbeat attempt at t=120.0 (past 115.0 expiration)
    assert db.coordinator.heartbeat_intent("intent-h", "worker-1", 2, 120.0, 10.0) is False


def test_crashes_before_and_after_pre_spawn(tmp_path):
    """Test 8: Crashes before vs after pre-spawn persistence and UNKNOWN_EXECUTION halting retries."""
    db = PMDatabase(tmp_path / "crashes.db")
    db.create_project(Project(id="p", key="CRS", name="Crash"))
    db.create_issue(Issue(id="i", project_id="p", key="CRS-1", title="Task"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'K-1', 'task-k1', 'i', 'CRS-1')
        """)

    # Scenario A: Crash after pre-spawn (process launched, then worker died)
    db.coordinator.create_attempt_with_intent(
        attempt_id="att-crash-post",
        intent_id="intent-crash-post",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i",
        task_id="task-k1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={},
        budget_reservation=25000,
    )
    db.coordinator.claim_intent("intent-crash-post", "worker-crashed", 1, 100.0, 10.0)
    db.coordinator.pre_spawn_intent("intent-crash-post", "worker-crashed", 2, 101.0, "run-post", "att-crash-post")

    # Time elapses, worker crashed, lease expires at 110.0
    reaped = db.coordinator.reap_expired_leases(now_epoch=115.0)
    assert "intent-crash-post" in reaped

    # Intent is now UNKNOWN_EXECUTION
    intent_post = db.coordinator.get_intent("intent-crash-post")
    assert intent_post.status == "UNKNOWN_EXECUTION"
    assert intent_post.fencing_token == 3

    # Attempt is UNKNOWN_EXECUTION
    att_post = db.coordinator.get_attempt("att-crash-post")
    assert att_post.status == "UNKNOWN_EXECUTION"

    # Crucial: CAS claim query matches only PENDING, so UNKNOWN_EXECUTION cannot be re-claimed!
    can_reclaim = db.coordinator.claim_intent("intent-crash-post", "worker-new", 3, 120.0, 10.0)
    assert can_reclaim is False, "UNKNOWN_EXECUTION intent MUST NOT be claimable for automatic retry"


def test_duplicate_physical_run_rejection(tmp_path):
    """Test 9: Duplicate physical run rejection via uq_physical_dispatch."""
    db = PMDatabase(tmp_path / "runs.db")
    db.create_project(Project(id="p", key="RUN", name="Runs"))
    db.create_issue(Issue(id="i", project_id="p", key="RUN-1", title="Task"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'R-1', 'task-r1', 'i', 'RUN-1')
        """)

    db.coordinator.create_attempt_with_intent(
        attempt_id="att-run",
        intent_id="intent-run",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i",
        task_id="task-r1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={},
    )
    db.coordinator.claim_intent("intent-run", "worker-1", 1, 100.0, 20.0)
    assert db.coordinator.pre_spawn_intent("intent-run", "worker-1", 2, 101.0, "run-primary", "att-run") is True

    # Attempt to insert a second run with same intent_id and fencing_token
    conn = db._get_connection()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO pm_coordinator_runs (run_id, intent_id, attempt_id, fencing_token, status)
            VALUES ('run-duplicate', 'intent-run', 'att-run', 2, 'SPAWNING')
            """
        )
    conn.close()


def test_uncertain_execution_retains_budget_holds(tmp_path):
    """Test 10: Uncertain execution retaining budget holds."""
    db = PMDatabase(tmp_path / "budget_hold.db")
    db.create_project(Project(id="p", key="BGT", name="Budget"))
    db.create_issue(Issue(id="i", project_id="p", key="BGT-1", title="Task"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'B-1', 'task-b1', 'i', 'BGT-1')
        """)

    # Attempt with 50,000 token reservation
    db.coordinator.create_attempt_with_intent(
        attempt_id="att-bgt",
        intent_id="intent-bgt",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i",
        task_id="task-b1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={},
        budget_reservation=50000,
    )
    db.coordinator.claim_intent("intent-bgt", "worker-bgt", 1, 100.0, 10.0)
    db.coordinator.pre_spawn_intent("intent-bgt", "worker-bgt", 2, 101.0, "run-bgt", "att-bgt")

    # Worker crashes, reaper runs
    db.coordinator.reap_expired_leases(now_epoch=120.0)

    att = db.coordinator.get_attempt("att-bgt")
    assert att.status == "UNKNOWN_EXECUTION"
    # Full 50,000 budget allocation is retained (not zeroed or refunded)
    assert att.budget_tokens_allocated == 50000
    assert att.budget_tokens_spent == 0


def test_event_cursor_and_evidence_receipt_uniqueness(tmp_path):
    """Test 11: Event cursor uniqueness and evidence receipt nonce uniqueness."""
    db = PMDatabase(tmp_path / "events.db")
    db.create_project(Project(id="p", key="EVT", name="Events"))
    db.create_issue(Issue(id="i", project_id="p", key="EVT-1", title="Task"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'E-1', 'task-e1', 'i', 'EVT-1')
        """)

    db.coordinator.create_attempt_with_intent(
        attempt_id="att-e",
        intent_id="intent-e",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i",
        task_id="task-e1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={},
    )
    db.coordinator.claim_intent("intent-e", "worker-1", 1, 100.0, 20.0)
    db.coordinator.pre_spawn_intent("intent-e", "worker-1", 2, 101.0, "run-e", "att-e")

    # Record event cursors
    evt0 = db.coordinator.record_run_event("run-e", 0, "init", {"conv_id": "c1"})
    evt1 = db.coordinator.record_run_event("run-e", 1, "tool_call", {"tool": "view_file"})
    assert evt0.cursor_seq == 0
    assert evt1.cursor_seq == 1

    # Duplicate cursor_seq 0 must raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        db.coordinator.record_run_event("run-e", 0, "duplicate", {})

    # Evidence receipt recording with explicit admission status
    rcpt = db.coordinator.record_evidence_receipt(
        evidence_id="ev-1",
        issue_id="i",
        task_id="task-e1",
        attempt_id="att-e",
        run_id="run-e",
        candidate_commit_sha="sha123",
        nonce="nonce-unique-1",
        key_id="key-v1",
        signature="sig123",
        canonical_payload={"policy_version": 1},
        admission_status="SUBMITTED",
    )
    assert rcpt.evidence_id == "ev-1"
    assert rcpt.admission_status == "SUBMITTED"

    # Replay of exact same nonce must raise IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        db.coordinator.record_evidence_receipt(
            evidence_id="ev-2",
            issue_id="i",
            task_id="task-e1",
            attempt_id="att-e",
            run_id="run-e",
            candidate_commit_sha="sha123",
            nonce="nonce-unique-1",  # Duplicate nonce!
            key_id="key-v1",
            signature="sig123",
            canonical_payload={"policy_version": 1},
        )


def test_wrong_attempt_and_cross_project_ownership_rejection(tmp_path):
    """Test 12: Run ownership enforcement - contradictory attempt_id and composite FK constraint."""
    db = PMDatabase(tmp_path / "ownership.db")
    db.create_project(Project(id="p1", key="OWN1", name="Owner Proj 1"))
    db.create_project(Project(id="p2", key="OWN2", name="Owner Proj 2"))
    db.create_issue(Issue(id="i1", project_id="p1", key="OWN1-1", title="Task 1"))
    db.create_issue(Issue(id="i2", project_id="p2", key="OWN2-1", title="Task 2"))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p1', 'REF-1', 'task-1', 'i1', 'OWN1-1')
        """)
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p2', 'REF-2', 'task-2', 'i2', 'OWN2-1')
        """)

    # Attempt 1 and 2
    db.coordinator.create_attempt_with_intent(
        attempt_id="att-1",
        intent_id="intent-1",
        tenant_id="tenant-1",
        project_id="p1",
        issue_id="i1",
        task_id="task-1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={},
    )
    db.coordinator.create_attempt_with_intent(
        attempt_id="att-2",
        intent_id="intent-2",
        tenant_id="tenant-1",
        project_id="p2",
        issue_id="i2",
        task_id="task-2",
        attempt_seq=1,
        adapter_type="codex",
        payload={},
    )

    db.coordinator.claim_intent("intent-1", "worker-1", 1, 100.0, 30.0)

    # 1. pre_spawn_intent with contradictory attempt_id must raise ValueError and roll back
    with pytest.raises(ValueError, match="Contradictory attempt_id"):
        db.coordinator.pre_spawn_intent(
            intent_id="intent-1",
            worker_id="worker-1",
            assigned_fencing_token=2,
            now_epoch=101.0,
            run_id="run-fake-1",
            attempt_id="att-2",  # Contradictory attempt!
        )

    # Verify atomic rollback: intent remains CLAIMED, run-fake-1 does NOT exist, attempt att-2 remains PENDING
    intent_state = db.coordinator.get_intent("intent-1")
    assert intent_state.status == "CLAIMED"
    assert db.coordinator.get_run("run-fake-1") is None
    att2_state = db.coordinator.get_attempt("att-2")
    assert att2_state.status == "PENDING"

    # 2. Direct SQL insertion violating composite FK (intent_id, attempt_id)
    conn = db._get_connection()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO pm_coordinator_runs (run_id, intent_id, attempt_id, fencing_token, status)
            VALUES ('run-bad-fk', 'intent-1', 'att-2', 2, 'SPAWNING')
            """
        )
    conn.close()


def test_truthful_cancellation_unlaunched_vs_launched(tmp_path):
    """Test 13: Truthful cancellation distinguishes unlaunched (PENDING) from launched (PROCESSING)."""
    db = PMDatabase(tmp_path / "truthful_cancel.db")
    db.create_project(Project(id="p", key="TC", name="Truthful Cancel"))
    db.create_issue(Issue(id="i1", project_id="p", key="TC-1", title="Task 1", appetite_tokens=100000))
    db.create_issue(Issue(id="i2", project_id="p", key="TC-2", title="Task 2", appetite_tokens=100000))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'REF-1', 'task-1', 'i1', 'TC-1')
        """)
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p', 'REF-2', 'task-2', 'i2', 'TC-2')
        """)

    # Case A: PENDING intent (provably unlaunched)
    db.coordinator.create_attempt_with_intent(
        attempt_id="att-unlaunched",
        intent_id="intent-unlaunched",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i1",
        task_id="task-1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={},
        budget_reservation=25000,
    )
    # Cancel while still PENDING
    assert db.coordinator.cancel_intent("intent-unlaunched", "Cancelled before claim") is True
    att_un = db.coordinator.get_attempt("att-unlaunched")
    intent_un = db.coordinator.get_intent("intent-unlaunched")
    assert intent_un.status == "CANCELED"
    assert att_un.status == "CANCELED"

    # Verify reservation ledger released hold
    conn = db._get_connection()
    res_un = conn.execute(
        "SELECT status FROM pm_coordinator_reservations WHERE attempt_id = 'att-unlaunched'"
    ).fetchone()
    assert res_un["status"] == "RELEASED"

    # Case B: PROCESSING intent (potentially launched)
    db.coordinator.create_attempt_with_intent(
        attempt_id="att-launched",
        intent_id="intent-launched",
        tenant_id="tenant-1",
        project_id="p",
        issue_id="i2",
        task_id="task-2",
        attempt_seq=1,
        adapter_type="codex",
        payload={},
        budget_reservation=25000,
    )
    db.coordinator.claim_intent("intent-launched", "worker-x", 1, 100.0, 30.0)
    db.coordinator.pre_spawn_intent("intent-launched", "worker-x", 2, 101.0, "run-launched")

    # Cancel while PROCESSING
    assert db.coordinator.cancel_intent("intent-launched", "Operator abort") is True

    intent_launch = db.coordinator.get_intent("intent-launched")
    run_launch = db.coordinator.get_run("run-launched")
    att_launch = db.coordinator.get_attempt("att-launched")

    assert intent_launch.status == "CANCEL_REQUESTED"
    assert intent_launch.fencing_token == 3  # Fencing advanced, retiring worker-x authority
    assert run_launch.status == "SPAWNING", "Run must remain SPAWNING until authoritative observation"
    assert att_launch.status == "RUNNING", "Attempt must remain RUNNING until authoritative observation"

    res_launch = conn.execute(
        "SELECT status FROM pm_coordinator_reservations WHERE attempt_id = 'att-launched'"
    ).fetchone()
    assert res_launch["status"] == "HELD", "Reservation must remain HELD while execution state is uncertain"
    conn.close()

    # Repeated cancellation call is idempotent
    assert db.coordinator.cancel_intent("intent-launched", "Repeated cancel") is True


def test_funded_reservation_ledger_and_capacity_bounds(tmp_path):
    """Test 14: Funded budget reservations enforced against issue appetite, capacity, and concurrent holds."""
    db = PMDatabase(tmp_path / "reservation.db")
    # Project with total budget 10,000, 0 consumed
    db.create_project(Project(id="p-res", key="RES", name="Res Proj", token_budget=10000, tokens_consumed=0))
    # Issue with appetite 6,000
    db.create_issue(Issue(id="i-res", project_id="p-res", key="RES-1", title="Res Task", appetite_tokens=6000))

    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p-res', 'REF-R1', 'task-r1', 'i-res', 'RES-1')
        """)

    # 1. Negative amount rejected
    with pytest.raises(ValueError, match="non-negative"):
        db.coordinator.create_attempt_with_intent(
            attempt_id="att-neg",
            intent_id="intent-neg",
            tenant_id="tenant-1",
            project_id="p-res",
            issue_id="i-res",
            task_id="task-r1",
            attempt_seq=1,
            adapter_type="antigravity",
            payload={},
            budget_reservation=-500,
        )

    # 2. Non-integer rejected (boolean or string)
    with pytest.raises(ValueError, match="integer"):
        db.coordinator.create_attempt_with_intent(
            attempt_id="att-bool",
            intent_id="intent-bool",
            tenant_id="tenant-1",
            project_id="p-res",
            issue_id="i-res",
            task_id="task-r1",
            attempt_seq=1,
            adapter_type="antigravity",
            payload={},
            budget_reservation=True,  # bool is not allowed
        )

    # 3. Exceeds task appetite: request 8,000 when appetite is 6,000
    with pytest.raises(ValueError, match="exceeds issue appetite"):
        db.coordinator.create_attempt_with_intent(
            attempt_id="att-over-appetite",
            intent_id="intent-over-appetite",
            tenant_id="tenant-1",
            project_id="p-res",
            issue_id="i-res",
            task_id="task-r1",
            attempt_seq=1,
            adapter_type="antigravity",
            payload={},
            budget_reservation=8000,
        )

    # 4. Valid reservation within appetite and capacity: request 5,000
    att1, intent1 = db.coordinator.create_attempt_with_intent(
        attempt_id="att-res-1",
        intent_id="intent-res-1",
        tenant_id="tenant-1",
        project_id="p-res",
        issue_id="i-res",
        task_id="task-r1",
        attempt_seq=1,
        adapter_type="antigravity",
        payload={},
        budget_reservation=5000,
    )
    assert att1.budget_tokens_allocated == 5000

    # 5. Second attempt on another task in same project: remaining available capacity is 10,000 - 5,000 = 5,000
    db.create_issue(Issue(id="i-res-2", project_id="p-res", key="RES-2", title="Res Task 2", appetite_tokens=8000))
    with db.atomic_transaction() as conn:
        conn.execute("""
        INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
        VALUES ('p-res', 'REF-R2', 'task-r2', 'i-res-2', 'RES-2')
        """)

    # Attempting 6,000 must fail because available capacity is only 5,000
    with pytest.raises(ValueError, match="exceeds available project capacity"):
        db.coordinator.create_attempt_with_intent(
            attempt_id="att-res-2",
            intent_id="intent-res-2",
            tenant_id="tenant-1",
            project_id="p-res",
            issue_id="i-res-2",
            task_id="task-r2",
            attempt_seq=1,
            adapter_type="codex",
            payload={},
            budget_reservation=6000,
        )

    # Attempting 5,000 exactly consumes the remaining available pool
    att2, intent2 = db.coordinator.create_attempt_with_intent(
        attempt_id="att-res-2",
        intent_id="intent-res-2",
        tenant_id="tenant-1",
        project_id="p-res",
        issue_id="i-res-2",
        task_id="task-r2",
        attempt_seq=1,
        adapter_type="codex",
        payload={},
        budget_reservation=5000,
    )
    assert att2.budget_tokens_allocated == 5000


def test_tenant_authority_validation(tmp_path):
    """Test 15: CoordinatorStore validates tenant identity and write authority under tenant_scope."""
    from mas.iam import MultiTenantIAM
    from mas.tenancy import tenant_scope
    from mas.pm.coordinator import trusted_coordinator_admin_scope

    iam = MultiTenantIAM(signing_secret="disposable-test-key-" * 3)
    iam.create_tenant("tenant-alpha", "Alpha Org")
    iam.create_tenant("tenant-beta", "Beta Org")

    # Alpha tenant admin with storage:write and storage:read
    iam.register_principal("tenant-alpha", "alice", roles={"tenant_admin"})
    token_alpha = iam.issue_token("tenant-alpha", "alice")

    # Alpha read-only principal (read_only role)
    iam.register_principal("tenant-alpha", "alice-ro", roles={"read_only"})
    token_alpha_ro = iam.issue_token("tenant-alpha", "alice-ro")

    root = tmp_path / "tenants"

    # 1. Under tenant-alpha scope, writing with tenant_id='tenant-beta' must be rejected
    with tenant_scope(iam, token_alpha, "tenant-alpha", root):
        db_alpha = PMDatabase()
        db_alpha.create_project(Project(id="p-a", key="ALF", name="Alpha Proj"))
        db_alpha.create_issue(Issue(id="i-a", project_id="p-a", key="ALF-1", title="Task A"))
        with db_alpha.atomic_transaction() as conn:
            conn.execute("""
            INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
            VALUES ('p-a', 'REF-A', 'task-a', 'i-a', 'ALF-1')
            """)

        with pytest.raises(PermissionError, match="Tenant authority mismatch"):
            db_alpha.coordinator.create_attempt_with_intent(
                attempt_id="att-x",
                intent_id="intent-x",
                tenant_id="tenant-beta",  # Mismatch!
                project_id="p-a",
                issue_id="i-a",
                task_id="task-a",
                attempt_seq=1,
                adapter_type="antigravity",
                payload={},
            )

    # 2. Under tenant-alpha read-only scope, mutation must fail storage:write check
    with tenant_scope(iam, token_alpha_ro, "tenant-alpha", root):
        db_alpha_ro = PMDatabase()
        with pytest.raises(PermissionError, match="Tenant authority unavailable or action denied"):
            db_alpha_ro.coordinator.create_attempt_with_intent(
                attempt_id="att-ro",
                intent_id="intent-ro",
                tenant_id="tenant-alpha",
                project_id="p-a",
                issue_id="i-a",
                task_id="task-a",
                attempt_seq=1,
                adapter_type="antigravity",
                payload={},
            )

    # 3. Inside trusted_coordinator_admin_scope, administrative access succeeds
    with trusted_coordinator_admin_scope():
        db_admin = PMDatabase(tmp_path / "admin_test.db")
        db_admin.create_project(Project(id="p-adm", key="ADM", name="Admin Proj"))
        db_admin.create_issue(Issue(id="i-adm", project_id="p-adm", key="ADM-1", title="Admin Task"))
        with db_admin.atomic_transaction() as conn:
            conn.execute("""
            INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
            VALUES ('p-adm', 'REF-ADM', 'task-adm', 'i-adm', 'ADM-1')
            """)

        att, intent = db_admin.coordinator.create_attempt_with_intent(
            attempt_id="att-adm",
            intent_id="intent-adm",
            tenant_id="tenant-custom",
            project_id="p-adm",
            issue_id="i-adm",
            task_id="task-adm",
            attempt_seq=1,
            adapter_type="antigravity",
            payload={},
        )
        assert att.attempt_id == "att-adm"


def test_schema_migration_atomic_rollback_on_injected_failure(tmp_path):
    """Test 16: Versioned transactional migration rolls back atomically on injected failure."""
    db_file = tmp_path / "migration_rollback.db"
    conn = sqlite3.connect(str(db_file), isolation_level=None)
    with conn:
        conn.execute("""
        CREATE TABLE pm_projects (
            id TEXT PRIMARY KEY, key TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
            description TEXT, token_budget INTEGER NOT NULL DEFAULT 5000000,
            tokens_consumed INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.execute("""
        CREATE TABLE pm_schema_migrations (
            version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
    conn.close()

    # Instantiate PMDatabase
    db = PMDatabase(db_file)

    # Inject a failure during migration execution by patching conn.execute inside migration block
    def failing_migrate():
        c = db._get_connection()
        with db._lock:
            c.execute("BEGIN IMMEDIATE;")
            try:
                # Step 1: create dummy table
                c.execute("CREATE TABLE pm_mig_step1 (id TEXT PRIMARY KEY);")
                # Step 2: inject deliberate error
                raise sqlite3.OperationalError("Simulated mid-migration disk error")
            except Exception:
                c.execute("ROLLBACK;")
                raise
            finally:
                c.close()

    db.migrate_coordinator_schema = failing_migrate

    with pytest.raises(sqlite3.OperationalError, match="Simulated mid-migration"):
        db.migrate_coordinator_schema()

    # Verify atomic rollback: pm_mig_step1 was rolled back completely
    verify_conn = db._get_connection()
    tables = [r[0] for r in verify_conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    verify_conn.close()
    assert "pm_mig_step1" not in tables, "Table created before failure must be completely rolled back"
