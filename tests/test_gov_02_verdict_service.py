"""
Regression and authorization tests for GOV-02:
- Independent reviewer verdict service
- Only authenticated reviewer actions create verdicts; unauthenticated scripts cannot manufacture approvals
- Cryptographic HMAC-SHA256 signing of reviewer decision records
- Separation of builder and judge enforcement on verdict submission
- Tamper detection on decision records
"""
import pytest

from mas.security import ExecutionContext, sign_verdict_payload, verify_verdict_signature
from mas.pm.db import PMDatabase
from mas.pm.guards import UnverifiedWorkError, validate_critic_verdicts
from mas.pm.models import (
    CriticVerdict,
    CriticVerdictType,
    Issue,
    IssueState,
    Project,
)
from mas.pm.tools import pm_record_verdict


@pytest.fixture
def gov_db(tmp_path):
    db = PMDatabase(tmp_path / "gov_test.db")
    proj = db.create_project(Project(id="p-gov", key="GOV", name="Governance Project"))
    issue = db.create_issue(
        Issue(
            id="i-gov-1",
            project_id=proj.id,
            key="GOV-10",
            title="Verdict Service Task",
            current_state=IssueState.VERIFICATION,
            assignee_principal="backend_engineer",
            rework_cycle=0,
        )
    )
    return db, issue


def test_gov_02_unauthenticated_verdict_creation_rejected(gov_db):
    """Verify that unauthenticated callers cannot manufacture verdicts."""
    db, issue = gov_db
    ExecutionContext.set_current_principal(None)

    verdict = CriticVerdict(
        id="v-unauth",
        issue_id=issue.id,
        reviewer_principal="adversarial_red_team",
        verdict=CriticVerdictType.PASS,
        rework_cycle=0,
    )

    with pytest.raises(PermissionError) as exc_info:
        db.record_verdict(verdict, enforce_auth=True)
    assert "Unauthenticated operation" in str(exc_info.value)


def test_gov_02_mismatched_principal_verdict_rejected(gov_db):
    """Verify that an authenticated agent cannot impersonate another reviewer to forge a verdict."""
    db, issue = gov_db

    verdict = CriticVerdict(
        id="v-forged",
        issue_id=issue.id,
        reviewer_principal="adversarial_red_team",
        verdict=CriticVerdictType.PASS,
        rework_cycle=0,
    )

    # Scoped as product_lead attempting to record as adversarial_red_team
    with ExecutionContext.scope("product_lead"):
        with pytest.raises(PermissionError) as exc_info:
            db.record_verdict(verdict, enforce_auth=True)
        assert "UnauthorizedVerdictError" in str(exc_info.value)


def test_gov_02_separation_of_builder_and_judge_rejected(gov_db):
    """Verify that the assignee cannot record a review verdict on their own task."""
    db, issue = gov_db

    # Assignee is backend_engineer
    verdict = CriticVerdict(
        id="v-self-review",
        issue_id=issue.id,
        reviewer_principal="backend_engineer",
        verdict=CriticVerdictType.PASS,
        rework_cycle=0,
    )

    with ExecutionContext.scope("backend_engineer"):
        with pytest.raises(PermissionError) as exc_info:
            db.record_verdict(verdict, enforce_auth=True)
        assert "SeparationOfDutiesError" in str(exc_info.value)


def test_gov_02_authenticated_reviewer_verdict_signing(gov_db):
    """Verify that an authentic reviewer creates a cryptographically signed decision record."""
    db, issue = gov_db

    verdict = CriticVerdict(
        id="v-valid-1",
        issue_id=issue.id,
        reviewer_principal="adversarial_red_team",
        verdict=CriticVerdictType.PASS,
        findings={"security_posture": "VERIFIED_HARDENED", "audit_passed": True},
        rework_cycle=0,
        commit_sha="a1b2c3d4e5f6",
    )

    with ExecutionContext.scope("adversarial_red_team"):
        recorded = db.record_verdict(verdict, enforce_auth=True)

    assert recorded.signature != ""
    assert len(recorded.signature) == 64  # SHA-256 hex string

    # Verify signature
    is_valid = verify_verdict_signature(
        issue_id=recorded.issue_id,
        reviewer_principal=recorded.reviewer_principal,
        verdict_value="PASS",
        rework_cycle=recorded.rework_cycle,
        signature=recorded.signature,
        commit_sha=recorded.commit_sha,
        findings=recorded.findings,
    )
    assert is_valid is True


def test_gov_02_tampered_verdict_detected(gov_db):
    """Verify that tampering with verdict findings or fields invalidates the cryptographic signature."""
    db, issue = gov_db

    verdict = CriticVerdict(
        id="v-tamper",
        issue_id=issue.id,
        reviewer_principal="adversarial_red_team",
        verdict=CriticVerdictType.PASS,
        findings={"verdict_note": "Authentic original"},
        rework_cycle=0,
    )

    with ExecutionContext.scope("adversarial_red_team"):
        recorded = db.record_verdict(verdict, enforce_auth=True)

    # Tampered signature should fail verification
    assert verify_verdict_signature(
        issue_id=recorded.issue_id,
        reviewer_principal=recorded.reviewer_principal,
        verdict_value="PASS",
        rework_cycle=recorded.rework_cycle,
        signature="tampered_bad_signature" + "0" * 42,
        findings=recorded.findings,
    ) is False

    # Tampered findings should fail verification
    assert verify_verdict_signature(
        issue_id=recorded.issue_id,
        reviewer_principal=recorded.reviewer_principal,
        verdict_value="PASS",
        rework_cycle=recorded.rework_cycle,
        signature=recorded.signature,
        findings={"verdict_note": "Forged modified findings"},
    ) is False


def test_gov_02_pm_record_verdict_service_tool(gov_db):
    """Verify the pm_record_verdict tool service integration."""
    db, issue = gov_db

    with ExecutionContext.scope("adversarial_red_team"):
        res = pm_record_verdict(
            issue_key=issue.key,
            verdict="PASS",
            findings={"code_review": "Passed with 0 defects"},
            commit_sha="112233445566",
            db=db,
        )

    assert res["status"] == "RECORDED"
    assert res["issue_key"] == issue.key
    assert res["reviewer_principal"] == "adversarial_red_team"
    assert res["verdict"] == "PASS"
    assert len(res["signature"]) == 64

    # Ensure validate_critic_verdicts passes with authentic signed verdict
    validate_critic_verdicts(db, issue, required_roles=["adversarial_red_team"])
