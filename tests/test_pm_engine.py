"""
tests/test_pm_engine.py: Comprehensive test suite and pilot validation for MAS-PM.
Validates:
- FSM state progression and lifecycle invariants
- Strict Little's Law WIP limits and agent concurrency limits
- Separation of Builder and Judge enforcement
- Scope jail path normalization and traversal prevention
- Cryptographic evidence SHA-256 verification
- Finite reflexion circuit breaker trips
- Flow metrics, CFD snapshots, and MCP tool registry integration
"""

import hashlib
import tempfile
from pathlib import Path
import pytest

from mas.pm.db import PMDatabase
from mas.pm.fsm import FSMEngine
from mas.pm.guards import (
    CircuitBreakerTrippedError,
    ScopeJailViolationError,
    SeparationOfDutiesError,
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
    IssueType,
    Project,
)
from mas.pm.tools import register_pm_tools
from mas.mcp.protocol import MCPRegistry
from mas.security import ExecutionContext


@pytest.fixture(autouse=True)
def auto_authenticate_legacy_pm_engine(monkeypatch):
    """Ensures legacy direct transition and verdict calls in test_pm_engine.py run with caller principal scope."""
    orig_transition = FSMEngine.transition

    def patched_transition(self, issue_id_or_key, target_state, caller_principal=None, *args, **kwargs):
        if caller_principal and ExecutionContext.get_current_principal() is None:
            with ExecutionContext.scope(caller_principal):
                return orig_transition(self, issue_id_or_key, target_state, caller_principal, *args, **kwargs)
        return orig_transition(self, issue_id_or_key, target_state, caller_principal, *args, **kwargs)

    monkeypatch.setattr(FSMEngine, "transition", patched_transition)

    orig_record_verdict = PMDatabase.record_verdict

    def patched_record_verdict(self, verdict, enforce_auth=True, *args, **kwargs):
        if ExecutionContext.get_current_principal() is None:
            with ExecutionContext.scope(verdict.reviewer_principal):
                return orig_record_verdict(self, verdict, enforce_auth=enforce_auth, *args, **kwargs)
        return orig_record_verdict(self, verdict, enforce_auth=enforce_auth, *args, **kwargs)

    monkeypatch.setattr(PMDatabase, "record_verdict", patched_record_verdict)


@pytest.fixture
def temp_pm_db():
    """Provides an isolated SQLite database fixture in a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_pm.db"
        db = PMDatabase(db_path)
        yield db


def test_project_and_issue_crud(temp_pm_db):
    project = Project(
        id="proj-1",
        key="CORE",
        name="MAS Core System",
        token_budget=2_000_000,
    )
    saved_proj = temp_pm_db.create_project(project)
    assert saved_proj.key == "CORE"

    issue = Issue(
        id="iss-1",
        project_id=saved_proj.id,
        key="CORE-1",
        title="Implement Sandbox",
        issue_type=IssueType.TASK,
        current_state=IssueState.BACKLOG,
        assignee_principal="senior_engineer",
        path_whitelist=["mas/tools/*"],
    )
    saved_issue = temp_pm_db.create_issue(issue)
    assert saved_issue.key == "CORE-1"
    assert saved_issue.current_state == IssueState.BACKLOG

    fetched = temp_pm_db.get_issue("CORE-1")
    assert fetched is not None
    assert fetched.title == "Implement Sandbox"
    assert fetched.path_whitelist == ["mas/tools/*"]


def test_full_happy_path_fsm_lifecycle(temp_pm_db, tmp_path):
    proj = temp_pm_db.create_project(
        Project(id="p1", key="CORE", name="Core")
    )
    issue = temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="CORE-1",
            title="Secure Tools",
            current_state=IssueState.BACKLOG,
            assignee_principal="senior_engineer",
            appetite_tokens=40000,
            appetite_timeout_s=1200,
            path_whitelist=["*"],
        )
    )

    fsm = FSMEngine(temp_pm_db)

    # 1. BACKLOG -> REFINED
    step1 = fsm.transition("CORE-1", IssueState.REFINED, caller_principal="product_lead")
    assert step1.current_state == IssueState.REFINED

    # 2. REFINED -> STAGED
    step2 = fsm.transition("CORE-1", IssueState.STAGED, caller_principal="chief_architect")
    assert step2.current_state == IssueState.STAGED

    # 3. STAGED -> IN_PROGRESS
    step3 = fsm.transition("CORE-1", IssueState.IN_PROGRESS, caller_principal="senior_engineer")
    assert step3.current_state == IssueState.IN_PROGRESS

    # Attach empirical evidence
    import subprocess
    head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    log_file = tmp_path / "test_run.log"
    log_file.write_text("Tests passed: 12 passed, 0 failed.")
    log_hash = hashlib.sha256(log_file.read_bytes()).hexdigest()

    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-git",
            issue_id=issue.id,
            evidence_type=EvidenceType.GIT_COMMIT,
            content_hash=head_sha,
            uri=f"git:commit:{head_sha}",
        )
    )
    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-test",
            issue_id=issue.id,
            evidence_type=EvidenceType.TEST_RUN_LOG,
            content_hash=log_hash,
            uri=f"file://{log_file}",
            payload={"exit_code": 0, "passed": 12, "failed": 0},
        )
    )

    # 4. IN_PROGRESS -> VERIFICATION
    step4 = fsm.transition("CORE-1", IssueState.VERIFICATION, caller_principal="senior_engineer")
    assert step4.current_state == IssueState.VERIFICATION

    # Cast Stage 4 Critic Verdicts
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v-qa",
            issue_id=issue.id,
            reviewer_principal="qa_critic",
            verdict=CriticVerdictType.PASS,
            findings={"coverage": 92.5},
            signature="",
        )
    )
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v-sec",
            issue_id=issue.id,
            reviewer_principal="adversarial_red_team",
            verdict=CriticVerdictType.PASS,
            findings={"vulnerabilities": 0},
            signature="",
        )
    )

    # 5. VERIFICATION -> JUDICIAL_REVIEW (caller must not be senior_engineer)
    step5 = fsm.transition("CORE-1", IssueState.JUDICIAL_REVIEW, caller_principal="qa_critic")
    assert step5.current_state == IssueState.JUDICIAL_REVIEW

    # Cast Stage 5 Chief Architect Verdict
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v-arch",
            issue_id=issue.id,
            reviewer_principal="chief_architect",
            verdict=CriticVerdictType.PASS,
            findings={"contract_compliance": "100%"},
            signature="",
        )
    )

    # 6. JUDICIAL_REVIEW -> DONE
    step6 = fsm.transition("CORE-1", IssueState.DONE, caller_principal="CIOAgent")
    assert step6.current_state == IssueState.DONE


def test_separation_of_builder_and_judge_enforcement(temp_pm_db):
    """Enforces that the author/assignee cannot approve its own work."""
    proj = temp_pm_db.create_project(Project(id="p1", key="CORE", name="Core"))
    issue = temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="CORE-1",
            title="Secure Tools",
            current_state=IssueState.VERIFICATION,
            assignee_principal="senior_engineer",
            path_whitelist=["mas/tools/*"],
        )
    )

    # Record passing verdicts
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v1",
            issue_id=issue.id,
            reviewer_principal="qa_critic",
            verdict=CriticVerdictType.PASS,
        )
    )
    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v2",
            issue_id=issue.id,
            reviewer_principal="adversarial_red_team",
            verdict=CriticVerdictType.PASS,
        )
    )

    fsm = FSMEngine(temp_pm_db)

    # Assignee senior_engineer attempts to approve transition to JUDICIAL_REVIEW
    with pytest.raises(SeparationOfDutiesError) as exc_info:
        fsm.transition("CORE-1", IssueState.JUDICIAL_REVIEW, caller_principal="senior_engineer")
    assert "strictly prohibited" in str(exc_info.value)

    # Independent agent succeeds
    step = fsm.transition("CORE-1", IssueState.JUDICIAL_REVIEW, caller_principal="qa_critic")
    assert step.current_state == IssueState.JUDICIAL_REVIEW

    temp_pm_db.record_verdict(
        CriticVerdict(
            id="v3",
            issue_id=issue.id,
            reviewer_principal="chief_architect",
            verdict=CriticVerdictType.PASS,
        )
    )

    # Assignee senior_engineer attempts to approve transition to DONE
    with pytest.raises(SeparationOfDutiesError) as exc_info2:
        fsm.transition("CORE-1", IssueState.DONE, caller_principal="senior_engineer")
    assert "strictly prohibited" in str(exc_info2.value)


def test_wip_limit_and_concurrency_enforcement(temp_pm_db):
    """Verifies that Little's Law column WIP limits and per-agent limits are enforced."""
    proj = temp_pm_db.create_project(Project(id="p1", key="CORE", name="Core"))
    fsm = FSMEngine(temp_pm_db)

    # Create 4 issues already in IN_PROGRESS (Column limit is 4)
    for idx in range(1, 5):
        temp_pm_db.create_issue(
            Issue(
                id=f"ip-{idx}",
                project_id=proj.id,
                key=f"CORE-{idx}",
                title=f"Task {idx}",
                current_state=IssueState.IN_PROGRESS,
                assignee_principal=f"engineer_{idx}",
            )
        )

    # 5th issue in STAGED
    temp_pm_db.create_issue(
        Issue(
            id="ip-5",
            project_id=proj.id,
            key="CORE-5",
            title="Task 5",
            current_state=IssueState.STAGED,
            assignee_principal="engineer_5",
        )
    )

    # Transitioning 5th issue to IN_PROGRESS must be rejected by WIP limit guard
    with pytest.raises(WIPLimitExceededError) as exc_info:
        fsm.transition("CORE-5", IssueState.IN_PROGRESS, caller_principal="engineer_5")
    assert "WIP limit exceeded" in str(exc_info.value)

    # Per-agent concurrency limit check: engineer_1 already has CORE-1 in IN_PROGRESS
    # Create CORE-6 staged for engineer_1
    temp_pm_db.create_issue(
        Issue(
            id="ip-6",
            project_id=proj.id,
            key="CORE-6",
            title="Task 6",
            current_state=IssueState.STAGED,
            assignee_principal="engineer_1",
        )
    )
    # Move CORE-1 out of IN_PROGRESS to free up column WIP
    temp_pm_db.update_issue_state("ip-1", IssueState.VERIFICATION.value, "devops")

    # Now column WIP is 3/4, but engineer_1 still has 0 active in progress? Wait, CORE-1 moved to VERIFICATION!
    # Let's put CORE-1 back in IN_PROGRESS to test per-agent limit
    temp_pm_db.update_issue_state("ip-1", IssueState.IN_PROGRESS.value, "devops")
    # Move CORE-2 to VERIFICATION so column has room (3/4)
    temp_pm_db.update_issue_state("ip-2", IssueState.VERIFICATION.value, "devops")

    # Now column count is 3, but engineer_1 already has CORE-1 in IN_PROGRESS
    with pytest.raises(WIPLimitExceededError) as agent_exc:
        fsm.transition("CORE-6", IssueState.IN_PROGRESS, caller_principal="engineer_1")
    assert "Agent concurrency limit exceeded" in str(agent_exc.value)


def test_scope_jail_directory_traversal_rejection(temp_pm_db):
    """Verifies Condition 3 of review: prevents directory traversal in path whitelist."""
    proj = temp_pm_db.create_project(Project(id="p1", key="CORE", name="Core"))
    temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="CORE-1",
            title="Malicious Scope",
            current_state=IssueState.REFINED,
            path_whitelist=["mas/tools/../../../../etc/passwd"],
        )
    )

    fsm = FSMEngine(temp_pm_db)
    with pytest.raises(ScopeJailViolationError) as exc_info:
        fsm.transition("CORE-1", IssueState.STAGED, caller_principal="product_lead")
    assert "escapes workspace boundary" in str(exc_info.value)


def test_evidence_integrity_sha256_verification(temp_pm_db, tmp_path):
    """Verifies Condition 2 of review: dynamically validates SHA-256 hashes of real files."""
    proj = temp_pm_db.create_project(Project(id="p1", key="CORE", name="Core"))
    issue = temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="CORE-1",
            title="Real Test Run",
            current_state=IssueState.IN_PROGRESS,
            assignee_principal="senior_engineer",
        )
    )

    # Create real test log file on disk
    test_log = tmp_path / "test_out.log"
    test_log.write_text("All 10 tests passed successfully.")
    correct_hash = hashlib.sha256(test_log.read_bytes()).hexdigest()

    # Add valid git commit evidence
    import subprocess
    head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-git",
            issue_id=issue.id,
            evidence_type=EvidenceType.GIT_COMMIT,
            content_hash=head_sha,
            uri=f"git:commit:{head_sha}",
        )
    )

    # Attach with TAMPERED hash
    temp_pm_db.attach_evidence(
        EvidenceLink(
            id="ev-test-tampered",
            issue_id=issue.id,
            evidence_type=EvidenceType.TEST_RUN_LOG,
            content_hash="tampered_fake_hash_9999",
            uri=f"file://{test_log}",
            payload={"exit_code": 0},
        )
    )

    fsm = FSMEngine(temp_pm_db)
    with pytest.raises(UnverifiedWorkError) as exc_info:
        fsm.transition("CORE-1", IssueState.VERIFICATION, caller_principal="senior_engineer")
    assert "Evidence integrity mismatch" in str(exc_info.value)

    # Evidence is immutable: correcting an old record must be rejected.
    import sqlite3
    conn = temp_pm_db._get_connection()
    try:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"), conn:
            conn.execute("UPDATE pm_evidence_links SET content_hash = ? WHERE id = 'ev-test-tampered'", (correct_hash,))
    finally:
        conn.close()
    # A clean independent issue with genuine evidence may pass verification.
    temp_pm_db.create_issue(Issue(id="i2", project_id=proj.id, key="CORE-2", title="Valid evidence", current_state=IssueState.IN_PROGRESS, assignee_principal="senior_engineer"))
    temp_pm_db.attach_evidence(EvidenceLink(id="ev-git-valid", issue_id="i2", evidence_type=EvidenceType.GIT_COMMIT, content_hash=head_sha, uri=f"git:commit:{head_sha}"))
    temp_pm_db.attach_evidence(EvidenceLink(id="ev-test-valid", issue_id="i2", evidence_type=EvidenceType.TEST_RUN_LOG, content_hash=correct_hash, uri=f"file://{test_log}", payload={"exit_code": 0}))
    step = fsm.transition("CORE-2", IssueState.VERIFICATION, caller_principal="senior_engineer")
    assert step.current_state == IssueState.VERIFICATION


def test_reflexion_circuit_breaker(temp_pm_db):
    """Verifies that an issue exceeding 3 reflexion attempts trips the circuit breaker."""
    proj = temp_pm_db.create_project(Project(id="p1", key="CORE", name="Core"))
    temp_pm_db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="CORE-1",
            title="Flapping Task",
            current_state=IssueState.IN_PROGRESS,
            assignee_principal="senior_engineer",
            reflexion_attempts=0,
        )
    )

    fsm = FSMEngine(temp_pm_db)

    # Simulate 3 cycles of rejection
    for attempt in range(1, 4):
        # Move to REJECTED_REWORK
        fsm.transition("CORE-1", IssueState.REJECTED_REWORK, caller_principal="qa_critic", reason="Bug")
        reworked = temp_pm_db.get_issue("CORE-1")
        assert reworked.reflexion_attempts == attempt

        if attempt < 3:
            fsm.transition("CORE-1", IssueState.IN_PROGRESS, caller_principal="senior_engineer")
            fsm.transition("CORE-1", IssueState.IN_PROGRESS, caller_principal="senior_engineer")  # Idempotent or no-op

    # At attempt 3, moving back from REJECTED_REWORK to IN_PROGRESS trips circuit breaker!
    with pytest.raises(CircuitBreakerTrippedError) as exc_info:
        fsm.transition("CORE-1", IssueState.IN_PROGRESS, caller_principal="senior_engineer")
    assert "Circuit breaker tripped" in str(exc_info.value)


def test_mcp_pm_tool_registry_and_board_metrics(temp_pm_db):
    """Verifies tool handlers and board metrics generation."""
    registry = MCPRegistry()
    register_pm_tools(registry, db=temp_pm_db)

    # 1. Create Project
    p_res = registry.call_tool(
        "pm_create_project",
        {
            "key": "ACX",
            "name": "Acinonyx Operations",
            "token_budget": 10_000_000,
        },
    )
    assert p_res["status"] == "CREATED"
    assert p_res["project_key"] == "ACX"

    # 2. Create Issue
    i_res = registry.call_tool(
        "pm_create_issue",
        {
            "project_key": "ACX",
            "title": "Deploy Vector Index",
            "issue_type": "TASK",
            "assignee_principal": "data_engineer",
            "appetite_tokens": 60000,
            "path_whitelist": ["mas/memory/*"],
        },
    )
    assert i_res["status"] == "CREATED"
    assert i_res["issue_key"] == "ACX-1"

    # 3. Transition to REFINED then STAGED
    t1 = registry.call_tool(
        "pm_transition_issue",
        {
            "issue_key": "ACX-1",
            "target_state": "REFINED",
            "caller_principal": "product_lead",
        },
    )
    assert t1["current_state"] == "REFINED"

    t2 = registry.call_tool(
        "pm_transition_issue",
        {
            "issue_key": "ACX-1",
            "target_state": "STAGED",
            "caller_principal": "chief_architect",
        },
    )
    assert t2["current_state"] == "STAGED"

    # 4. Board State
    board = registry.call_tool("pm_get_board_state", {"project_key": "ACX"})
    assert board["project_key"] == "ACX"
    assert board["columns"]["STAGED"]["count"] == 1
    assert board["flow_health"] == "OPTIMAL"

    # 5. Flow Metrics & CFD Snapshots
    metrics_engine = FlowMetricsEngine(temp_pm_db)
    snapshot = metrics_engine.capture_cfd_snapshot(p_res["project_id"])
    assert snapshot.staged_count == 1
    assert snapshot.backlog_count == 0
