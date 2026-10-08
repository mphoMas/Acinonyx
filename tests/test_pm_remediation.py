"""
tests/test_pm_remediation.py: Verification suite for the 6 architectural/security defect remediations:
- PM-SEC-001: ExecutionContext principal derivation & impersonation prevention
- PM-SEC-002: Fail-closed empirical evidence & git object verification
- PM-SEC-003: Changeset scope jailing & forbidden path enforcement
- PM-CON-001: Atomic transaction serialization under concurrent worker threads
- PM-DATA-001: Conflict-free transactional sequence key allocation
- PM-GOV-001: Rework cycle tracking and stale critic verdict invalidation
- Scrum Layer: Sprint CRUD, state progression, and issue assignment
"""

from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import subprocess
import tempfile
import pytest

from mas.pm.db import PMDatabase
from mas.pm.fsm import FSMEngine
from mas.pm.guards import (
    ScopeJailViolationError,
    UnverifiedWorkError,
    WIPLimitExceededError,
)
from mas.pm.metrics import FlowMetricsEngine
from mas.pm.models import (
    CriticVerdict,
    CriticVerdictType,
    EvidenceLink,
    EvidenceType,
    Issue,
    IssueState,
    Project,
    Sprint,
    SprintState,
)
from mas.security import ExecutionContext


@pytest.fixture
def temp_pm_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "remediation_test_pm.db"
        db = PMDatabase(db_path)
        yield db


def test_pm_sec_001_impersonation_prevention(temp_pm_db):
    """PM-SEC-001: Asserts that ExecutionContext rejects impersonation attempts."""
    proj = temp_pm_db.create_project(Project(id="p1", key="SEC", name="Security Proj"))
    temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="SEC-1",
            title="Principal Test",
            current_state=IssueState.BACKLOG,
            appetite_tokens=20000,
            appetite_timeout_s=600,
        )
    )

    fsm = FSMEngine(temp_pm_db)

    # Scoped execution context for 'agent_alpha'
    with ExecutionContext.scope("agent_alpha"):
        # Attempting to claim to be 'chief_architect' must fail immediately
        with pytest.raises(PermissionError) as exc_info:
            fsm.transition("SEC-1", IssueState.REFINED, caller_principal="chief_architect")
        assert "ImpersonationAttemptError" in str(exc_info.value)

        # Transitioning matching current principal succeeds
        step = fsm.transition("SEC-1", IssueState.REFINED, caller_principal="agent_alpha")
        assert step.current_state == IssueState.REFINED

        # Transitioning with caller_principal=None resolves to authenticated principal
        temp_pm_db.update_issue_state("i1", IssueState.BACKLOG.value, "system")
        step_auto = fsm.transition("SEC-1", IssueState.REFINED)
        assert step_auto.current_state == IssueState.REFINED


def test_pm_sec_002_evidence_fail_closed(temp_pm_db, tmp_path):
    """PM-SEC-002: Asserts that non-existent commits and tampered files fail closed."""
    proj = temp_pm_db.create_project(Project(id="p1", key="EVD", name="Evidence Proj"))
    issue = temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="EVD-1",
            title="Evidence Fail Closed",
            current_state=IssueState.IN_PROGRESS,
            assignee_principal="coder",
            path_whitelist=["*"],
        )
    )

    fsm = FSMEngine(temp_pm_db)

    # 1. Non-existent git commit fails closed
    log_file = tmp_path / "valid.log"
    log_file.write_text("Test run output")
    log_hash = hashlib.sha256(log_file.read_bytes()).hexdigest()

    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-git-fake",
            issue_id=issue.id,
            evidence_type=EvidenceType.GIT_COMMIT,
            content_hash="deadbeefcafe1234567890abcdef1234567890ab",
            uri="git:commit:deadbeefcafe1234567890abcdef1234567890ab",
        )
    )
    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-test-ok",
            issue_id=issue.id,
            evidence_type=EvidenceType.TEST_RUN_LOG,
            content_hash=log_hash,
            uri=f"file://{log_file}",
            payload={"exit_code": 0},
        )
    )

    with pytest.raises(UnverifiedWorkError) as exc_git:
        fsm.transition("EVD-1", IssueState.VERIFICATION, caller_principal="coder")
    assert "Git commit verification failed" in str(exc_git.value)

    # 2. Fix git commit with real commit, but use non-existent log file
    real_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    conn = temp_pm_db._get_connection()
    with conn:
        conn.execute("UPDATE pm_evidence_links SET content_hash = ?, uri = ? WHERE id = 'ev-git-fake'", (real_sha, f"git:commit:{real_sha}"))
        conn.execute("UPDATE pm_evidence_links SET uri = 'file:///nonexistent/path/fake.log' WHERE id = 'ev-test-ok'")
    conn.close()

    with pytest.raises(UnverifiedWorkError) as exc_missing_log:
        fsm.transition("EVD-1", IssueState.VERIFICATION, caller_principal="coder")
    assert "does not exist on disk" in str(exc_missing_log.value)

    # 3. Test run exit code != 0 fails closed
    conn = temp_pm_db._get_connection()
    with conn:
        conn.execute("UPDATE pm_evidence_links SET uri = ?, payload = ? WHERE id = 'ev-test-ok'", (f"file://{log_file}", '{"exit_code": 1}'))
    conn.close()

    with pytest.raises(UnverifiedWorkError) as exc_fail_code:
        fsm.transition("EVD-1", IssueState.VERIFICATION, caller_principal="coder")
    assert "test run evidence indicates failure" in str(exc_fail_code.value)


def test_pm_sec_003_scope_jail_git_changeset(temp_pm_db, tmp_path):
    """PM-SEC-003: Asserts that commits modifying files outside whitelist or in forbidden paths fail closed."""
    proj = temp_pm_db.create_project(Project(id="p1", key="SCP", name="Scope Proj"))
    # Issue restricted strictly to nonexistent test folder
    issue = temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="SCP-1",
            title="Strict Scope Task",
            current_state=IssueState.IN_PROGRESS,
            assignee_principal="coder",
            path_whitelist=["mas/isolated_sandbox/*"],
            forbidden_paths=["mas/security.py", "*.env"],
        )
    )

    real_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    log_file = tmp_path / "valid.log"
    log_file.write_text("OK")
    log_hash = hashlib.sha256(log_file.read_bytes()).hexdigest()

    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-git",
            issue_id=issue.id,
            evidence_type=EvidenceType.GIT_COMMIT,
            content_hash=real_sha,
            uri=f"git:commit:{real_sha}",
        )
    )
    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-test",
            issue_id=issue.id,
            evidence_type=EvidenceType.TEST_RUN_LOG,
            content_hash=log_hash,
            uri=f"file://{log_file}",
            payload={"exit_code": 0},
        )
    )

    fsm = FSMEngine(temp_pm_db)
    # HEAD modified files outside mas/isolated_sandbox/* (e.g. mas/pm/db.py)
    with pytest.raises(ScopeJailViolationError) as exc_scope:
        fsm.transition("SCP-1", IssueState.VERIFICATION, caller_principal="coder")
    assert "violates scope jail" in str(exc_scope.value) or "modified out-of-scope file" in str(exc_scope.value)


def test_pm_con_001_atomic_wip_concurrency(temp_pm_db):
    """PM-CON-001: Asserts that 10 concurrent threads cannot exceed WIP limit of 4."""
    proj = temp_pm_db.create_project(Project(id="p1", key="CON", name="Concurrency Proj"))
    fsm = FSMEngine(temp_pm_db)

    # Create 10 issues in STAGED
    issue_keys = []
    for idx in range(1, 11):
        key = f"CON-{idx}"
        temp_pm_db.create_issue(
            Issue(
                id=f"con-{idx}",
                project_id=proj.id,
                key=key,
                title=f"Concurrent Task {idx}",
                current_state=IssueState.STAGED,
                assignee_principal=f"worker_{idx}",
                path_whitelist=["*"],
            )
        )
        issue_keys.append(key)

    successes = []
    rejections = []

    def attempt_transition(key: str, worker: str):
        try:
            fsm.transition(key, IssueState.IN_PROGRESS, caller_principal=worker)
            successes.append(key)
        except WIPLimitExceededError:
            rejections.append(key)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(attempt_transition, key, f"worker_{idx+1}")
            for idx, key in enumerate(issue_keys)
        ]
        for f in futures:
            f.result()

    # Column WIP limit for IN_PROGRESS is 4
    assert len(successes) == 4, f"Expected exactly 4 transitions into IN_PROGRESS, got {len(successes)}"
    assert len(rejections) == 6, f"Expected 6 rejections due to WIP limit, got {len(rejections)}"

    count = temp_pm_db.count_issues_in_state(proj.id, IssueState.IN_PROGRESS.value)
    assert count == 4


def test_pm_data_001_atomic_sequence_key_allocation(temp_pm_db):
    """PM-DATA-001: Asserts concurrent key allocations produce contiguous, zero-duplicate keys."""
    keys = []

    def allocate_key():
        return temp_pm_db.next_issue_key("ATOMIC")

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(allocate_key) for _ in range(25)]
        for f in futures:
            keys.append(f.result())

    assert len(keys) == 25
    assert len(set(keys)) == 25, "Expected all 25 keys to be unique, but collisions were detected."

    expected_keys = {f"ATOMIC-{i}" for i in range(1, 26)}
    assert set(keys) == expected_keys


def test_pm_gov_001_stale_verdict_invalidation_on_rework(temp_pm_db, tmp_path):
    """PM-GOV-001: Asserts that rework cycles invalidate prior critic approvals."""
    proj = temp_pm_db.create_project(Project(id="p1", key="GOV", name="Governance Proj"))
    issue = temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="GOV-1",
            title="Governance Review",
            current_state=IssueState.VERIFICATION,
            assignee_principal="coder",
            path_whitelist=["*"],
        )
    )

    fsm = FSMEngine(temp_pm_db)

    # Cycle 0: Add PASS verdicts
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v-qa-1",
            issue_id=issue.id,
            reviewer_principal="qa_critic",
            verdict=CriticVerdictType.PASS,
            rework_cycle=0,
        )
    )
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v-sec-1",
            issue_id=issue.id,
            reviewer_principal="adversarial_red_team",
            verdict=CriticVerdictType.PASS,
            rework_cycle=0,
        )
    )

    # Successfully transition to JUDICIAL_REVIEW
    step = fsm.transition("GOV-1", IssueState.JUDICIAL_REVIEW, caller_principal="qa_critic")
    assert step.current_state == IssueState.JUDICIAL_REVIEW

    # Chief architect rejects to REJECTED_REWORK
    fsm.transition("GOV-1", IssueState.REJECTED_REWORK, caller_principal="chief_architect", reason="Defect in edge case")
    reworked = temp_pm_db.get_issue("GOV-1")
    assert reworked.current_state == IssueState.REJECTED_REWORK
    assert reworked.rework_cycle == 1

    # Move back to IN_PROGRESS then VERIFICATION
    fsm.transition("GOV-1", IssueState.IN_PROGRESS, caller_principal="coder")

    real_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    log_file = tmp_path / "valid.log"
    log_file.write_text("OK")
    log_hash = hashlib.sha256(log_file.read_bytes()).hexdigest()

    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-git",
            issue_id=issue.id,
            evidence_type=EvidenceType.GIT_COMMIT,
            content_hash=real_sha,
            uri=f"git:commit:{real_sha}",
        )
    )
    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-test",
            issue_id=issue.id,
            evidence_type=EvidenceType.TEST_RUN_LOG,
            content_hash=log_hash,
            uri=f"file://{log_file}",
            payload={"exit_code": 0},
        )
    )

    fsm.transition("GOV-1", IssueState.VERIFICATION, caller_principal="coder")

    # Attempting to transition to JUDICIAL_REVIEW must fail because cycle 0 verdicts are stale!
    with pytest.raises(UnverifiedWorkError) as exc_stale:
        fsm.transition("GOV-1", IssueState.JUDICIAL_REVIEW, caller_principal="qa_critic")
    assert "missing required PASS verdicts for rework cycle 1" in str(exc_stale.value)

    # Cast fresh Cycle 1 verdicts
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v-qa-2",
            issue_id=issue.id,
            reviewer_principal="qa_critic",
            verdict=CriticVerdictType.PASS,
            rework_cycle=1,
        )
    )
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v-sec-2",
            issue_id=issue.id,
            reviewer_principal="adversarial_red_team",
            verdict=CriticVerdictType.PASS,
            rework_cycle=1,
        )
    )

    # Now transition succeeds!
    step_fresh = fsm.transition("GOV-1", IssueState.JUDICIAL_REVIEW, caller_principal="qa_critic")
    assert step_fresh.current_state == IssueState.JUDICIAL_REVIEW


def test_scrum_sprint_lifecycle_and_assignment(temp_pm_db):
    """Scrum Layer: Tests Sprint creation, issue assignment, activation, and board metrics."""
    proj = temp_pm_db.create_project(Project(id="p1", key="SCRUM", name="Scrum Proj"))

    # 1. Create Sprint
    sprint = Sprint(
        id="sprint-1",
        project_id=proj.id,
        name="Sprint 1: Core Security Hardening",
        goal="Remediate 6 blocking architectural defects",
        state=SprintState.FUTURE,
    )
    temp_pm_db.create_sprint(sprint)

    fetched_sprint = temp_pm_db.get_sprint("sprint-1")
    assert fetched_sprint is not None
    assert fetched_sprint.name == "Sprint 1: Core Security Hardening"
    assert fetched_sprint.state == SprintState.FUTURE

    # 2. Create Issue and assign to Sprint
    issue = temp_pm_db.create_issue(
        Issue(
            id="iss-1",
            project_id=proj.id,
            key="SCRUM-1",
            title="Implement Transactional Sequences",
            current_state=IssueState.BACKLOG,
            sprint_id="sprint-1",
        )
    )
    assert issue.sprint_id == "sprint-1"

    # 3. Activate Sprint
    temp_pm_db.update_sprint_state("sprint-1", SprintState.ACTIVE)
    active_sprint = temp_pm_db.get_sprint("sprint-1")
    assert active_sprint.state == SprintState.ACTIVE

    # 4. Board State reflects sprint and active_sprint_id
    metrics = FlowMetricsEngine(temp_pm_db)
    board = metrics.get_board_state("SCRUM")
    assert board.active_sprint_id == "sprint-1"
    assert len(board.sprints) == 1
    assert board.sprints[0].id == "sprint-1"
