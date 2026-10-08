"""
tests/test_gov_05_adversarial_judicial_review.py: Adversarial judicial-review attack suite for GOV-05.
Simulates active adversarial threats against the MAS-PM judicial review system:
1. Forged HMAC verdict signatures
2. Replayed or tampered evidence hashes and records
3. Missing reviewer verdicts (failing closed)
4. Conflicting judicial decisions (REJECT/HARD_FAIL vs PASS)
5. Builder impersonation and self-approval attempts
6. Direct SQLite persistence tampering attempts (triggers)
7. Stale verdict reuse across rework cycles
"""

import sqlite3
import tempfile
from pathlib import Path
import pytest

from mas.pm.db import PMDatabase
from mas.pm.fsm import FSMEngine
from mas.pm.guards import (
    SeparationOfDutiesError,
    UnverifiedWorkError,
)
from mas.pm.models import (
    CriticVerdict,
    CriticVerdictType,
    EvidenceLink,
    EvidenceType,
    Issue,
    IssueState,
    IssueType,
    PriorityLevel,
    Project,
)
from mas.security import (
    ExecutionContext,
    sign_verdict_payload,
)


@pytest.fixture
def adversarial_env():
    """Provides an isolated test environment with a fresh PM database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        db_path = tmp_path / "adversarial_pm.db"
        db = PMDatabase(db_path)
        proj = Project(id="proj-adv", key="ADV", name="Adversarial Test", token_budget=1_000_000)
        db.create_project(proj)
        yield db, tmp_path


def _create_staged_task(db: PMDatabase, key: str, assignee: str = "backend_engineer") -> Issue:
    issue = Issue(
        id=f"id-{key.lower()}",
        project_id="proj-adv",
        key=key,
        title=f"Task {key}",
        description=f"Adversarial test task {key}",
        issue_type=IssueType.TASK,
        current_state=IssueState.STAGED,
        priority=PriorityLevel.CRITICAL,
        assignee_principal=assignee,
        appetite_tokens=50000,
        appetite_timeout_s=1800,
        path_whitelist=["mas/", "tests/"],
        forbidden_paths=[".env"],
    )
    return db.create_issue(issue)


def test_adversarial_attack_forged_verdict_signature(adversarial_env):
    db, tmp_path = adversarial_env
    task = _create_staged_task(db, "ADV-01", "backend_engineer")

    # Move to IN_PROGRESS then VERIFICATION
    db.update_issue_state(task.id, IssueState.VERIFICATION, triggered_by="test")

    # Adversary inserts a verdict with a forged / tampered HMAC signature
    fake_signature = "a" * 64
    verdict = CriticVerdict(
        id="v-forged-1",
        issue_id=task.id,
        reviewer_principal="qa_critic",
        verdict=CriticVerdictType.PASS,
        rework_cycle=0,
        commit_sha="abcd1234abcd1234abcd1234abcd1234abcd1234",
        findings={"status": "fake_pass"},
        signature=fake_signature,
    )
    # Direct DB record without auth check to simulate raw insertion
    db.record_verdict(verdict, enforce_auth=False)

    fsm = FSMEngine(db)
    with ExecutionContext.scope("qa_critic"):
        with pytest.raises(UnverifiedWorkError, match="Cryptographic signature verification failed"):
            fsm.transition("ADV-01", IssueState.JUDICIAL_REVIEW, caller_principal="qa_critic")


def test_adversarial_attack_missing_critic_reviews(adversarial_env):
    db, _ = adversarial_env
    task = _create_staged_task(db, "ADV-02", "backend_engineer")
    db.update_issue_state(task.id, IssueState.VERIFICATION, triggered_by="test")

    # Only qa_critic submits a valid PASS verdict; adversarial_red_team is missing
    sig = sign_verdict_payload(
        issue_id=task.id,
        reviewer_principal="qa_critic",
        verdict_value="PASS",
        rework_cycle=0,
        commit_sha="",
        findings={"audit": "ok"},
    )
    verdict = CriticVerdict(
        id="v-missing-1",
        issue_id=task.id,
        reviewer_principal="qa_critic",
        verdict=CriticVerdictType.PASS,
        rework_cycle=0,
        findings={"audit": "ok"},
        signature=sig,
    )
    db.record_verdict(verdict, enforce_auth=False)

    fsm = FSMEngine(db)
    # Stage 4 requires both qa_critic and adversarial_red_team
    with ExecutionContext.scope("chief_architect"):
        with pytest.raises(UnverifiedWorkError, match="missing required PASS verdicts.*adversarial_red_team"):
            fsm.transition("ADV-02", IssueState.JUDICIAL_REVIEW, caller_principal="chief_architect")


def test_adversarial_attack_conflicting_decisions(adversarial_env):
    db, _ = adversarial_env
    task = _create_staged_task(db, "ADV-03", "backend_engineer")
    db.update_issue_state(task.id, IssueState.VERIFICATION, triggered_by="test")

    # qa_critic gives PASS
    sig_qa = sign_verdict_payload(
        issue_id=task.id,
        reviewer_principal="qa_critic",
        verdict_value="PASS",
        rework_cycle=0,
        commit_sha="",
        findings={"audit": "ok"},
    )
    v_qa = CriticVerdict(
        id="v-qa-pass",
        issue_id=task.id,
        reviewer_principal="qa_critic",
        verdict=CriticVerdictType.PASS,
        rework_cycle=0,
        findings={"audit": "ok"},
        signature=sig_qa,
    )
    db.record_verdict(v_qa, enforce_auth=False)

    # adversarial_red_team issues REJECT_REWORK
    sig_red = sign_verdict_payload(
        issue_id=task.id,
        reviewer_principal="adversarial_red_team",
        verdict_value="REJECT_REWORK",
        rework_cycle=0,
        commit_sha="",
        findings={"vulnerability": "scope escape detected"},
    )
    v_red = CriticVerdict(
        id="v-red-reject",
        issue_id=task.id,
        reviewer_principal="adversarial_red_team",
        verdict=CriticVerdictType.REJECT_REWORK,
        rework_cycle=0,
        findings={"vulnerability": "scope escape detected"},
        signature=sig_red,
    )
    db.record_verdict(v_red, enforce_auth=False)

    fsm = FSMEngine(db)
    # Attempt to transition to JUDICIAL_REVIEW must fail closed
    with ExecutionContext.scope("chief_architect"):
        with pytest.raises(UnverifiedWorkError, match="received REJECT_REWORK verdict"):
            fsm.transition("ADV-03", IssueState.JUDICIAL_REVIEW, caller_principal="chief_architect")


def test_adversarial_attack_builder_self_review(adversarial_env):
    db, _ = adversarial_env
    task = _create_staged_task(db, "ADV-04", "backend_engineer")
    db.update_issue_state(task.id, IssueState.VERIFICATION, triggered_by="test")

    # Builder backend_engineer attempts to cast verdict on its own task -> SQLite trigger aborts
    v_self = CriticVerdict(
        id="v-self-1",
        issue_id=task.id,
        reviewer_principal="backend_engineer",
        verdict=CriticVerdictType.PASS,
        rework_cycle=0,
        findings={"self": "approved"},
        signature="sig_self",
    )
    with pytest.raises(sqlite3.IntegrityError, match="SeparationOfDutiesViolation"):
        db.record_verdict(v_self, enforce_auth=False)

    # Builder attempts to call FSM transition on its own task to JUDICIAL_REVIEW
    fsm = FSMEngine(db)
    with ExecutionContext.scope("backend_engineer"):
        with pytest.raises(SeparationOfDutiesError, match="strictly prohibited from evaluating"):
            fsm.transition("ADV-04", IssueState.JUDICIAL_REVIEW, caller_principal="backend_engineer")


def test_adversarial_attack_direct_evidence_tampering(adversarial_env):
    db, _ = adversarial_env
    task = _create_staged_task(db, "ADV-05", "backend_engineer")

    evidence = EvidenceLink(
        id="ev-adv-1",
        issue_id=task.id,
        evidence_type=EvidenceType.TEST_RUN_LOG,
        content_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        uri="artifacts/test.log",
        payload={"tests": 5},
    )
    db.attach_evidence(evidence)

    # Attempt direct SQL UPDATE on pm_evidence_links -> must abort with IntegrityError
    with pytest.raises(sqlite3.IntegrityError, match="TamperViolationError"):
        with db.atomic_transaction() as conn:
            conn.execute(
                "UPDATE pm_evidence_links SET content_hash = 'tampered_hash' WHERE id = 'ev-adv-1'"
            )

    # Attempt direct SQL DELETE on pm_evidence_links -> must abort with IntegrityError
    with pytest.raises(sqlite3.IntegrityError, match="TamperViolationError"):
        with db.atomic_transaction() as conn:
            conn.execute(
                "DELETE FROM pm_evidence_links WHERE id = 'ev-adv-1'"
            )


def test_adversarial_attack_stale_verdict_rework_cycle(adversarial_env):
    db, _ = adversarial_env
    task = _create_staged_task(db, "ADV-06", "backend_engineer")
    db.update_issue_state(task.id, IssueState.VERIFICATION, triggered_by="test")

    # Approved in rework_cycle 0
    sig_qa = sign_verdict_payload(
        issue_id=task.id,
        reviewer_principal="qa_critic",
        verdict_value="PASS",
        rework_cycle=0,
        commit_sha="",
        findings={},
    )
    sig_red = sign_verdict_payload(
        issue_id=task.id,
        reviewer_principal="adversarial_red_team",
        verdict_value="PASS",
        rework_cycle=0,
        commit_sha="",
        findings={},
    )
    db.record_verdict(
        CriticVerdict(id="v1", issue_id=task.id, reviewer_principal="qa_critic", verdict=CriticVerdictType.PASS, rework_cycle=0, signature=sig_qa),
        enforce_auth=False,
    )
    db.record_verdict(
        CriticVerdict(id="v2", issue_id=task.id, reviewer_principal="adversarial_red_team", verdict=CriticVerdictType.PASS, rework_cycle=0, signature=sig_red),
        enforce_auth=False,
    )

    # Now task is rejected back to REJECTED_REWORK, bumping rework_cycle to 1
    fsm = FSMEngine(db)
    with ExecutionContext.scope("chief_architect"):
        fsm.transition("ADV-06", IssueState.REJECTED_REWORK, caller_principal="chief_architect", reason="Defect discovered")

    issue_ref = db.get_issue("ADV-06")
    assert issue_ref.rework_cycle == 1

    # Transition to IN_PROGRESS then VERIFICATION for cycle 1
    with ExecutionContext.scope("backend_engineer"):
        fsm.transition("ADV-06", IssueState.IN_PROGRESS, caller_principal="backend_engineer")
    db.update_issue_state(task.id, IssueState.VERIFICATION, triggered_by="test")

    # Stale cycle 0 verdicts must NOT satisfy cycle 1 requirements
    with ExecutionContext.scope("chief_architect"):
        with pytest.raises(UnverifiedWorkError, match="missing required PASS verdicts for rework cycle 1"):
            fsm.transition("ADV-06", IssueState.JUDICIAL_REVIEW, caller_principal="chief_architect")
