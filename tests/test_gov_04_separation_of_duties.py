"""
tests/test_gov_04_separation_of_duties.py: Rigorous test suite for GOV-04:
Separation of duties across API, service, and persistence boundaries.
"""

import sqlite3
import pytest

from mas.pm.db import PMDatabase
from mas.pm.guards import SeparationOfDutiesError, assert_separation_of_builder_and_judge
from mas.pm.models import (
    CriticVerdict,
    CriticVerdictType,
    Issue,
    IssueState,
    Project,
)
from mas.pm.tools import pm_record_verdict
from mas.security import ExecutionContext


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_pm.db"
    db = PMDatabase(db_path)
    proj = Project(id="proj-gov-04", key="MAS", name="MAS Project")
    db.create_project(proj)
    return db


@pytest.fixture
def builder_issue(test_db):
    issue = Issue(
        id="issue-gov-04-test",
        project_id="proj-gov-04",
        key="MAS-104",
        title="Separation of duties test task",
        description="Testing builder and reviewer separation across all layers",
        issue_type="TASK",
        current_state=IssueState.VERIFICATION,
        assignee_principal="backend_engineer",
        path_whitelist=["mas/pm/", "tests/"],
    )
    return test_db.create_issue(issue)


def test_persistence_trigger_blocks_builder_self_review(test_db, builder_issue):
    """Verifies that direct database inserts for self-review are aborted by SQLite trigger."""
    conn = sqlite3.connect(test_db.db_path)
    with pytest.raises(sqlite3.IntegrityError, match="SeparationOfDutiesViolation"):
        conn.execute(
            """
            INSERT INTO pm_critic_verdicts (id, issue_id, reviewer_principal, verdict, findings, signature, rework_cycle)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "v-raw-bypass",
                builder_issue.id,
                "backend_engineer",  # Same as assignee!
                "PASS",
                "{}",
                "sig_fake",
                0,
            ),
        )
    conn.close()


def test_service_boundary_blocks_builder_self_review(test_db, builder_issue):
    """Verifies that service-level verdict recording prevents assignee from self-approving."""
    with ExecutionContext.scope("backend_engineer"):
        with pytest.raises(PermissionError, match="SeparationOfDutiesError"):
            pm_record_verdict(
                issue_key=builder_issue.key,
                verdict="PASS",
                findings={"audit": "self approval"},
                db=test_db,
            )


def test_service_boundary_blocks_reviewer_impersonation(test_db, builder_issue):
    """Verifies that an agent cannot impersonate another reviewer principal."""
    verdict = CriticVerdict(
        id="v-impersonate",
        issue_id=builder_issue.id,
        reviewer_principal="adversarial_red_team",  # Claiming to be red team
        verdict=CriticVerdictType.PASS,
        findings={},
    )
    # But executing as backend_engineer
    with ExecutionContext.scope("backend_engineer"):
        with pytest.raises(PermissionError, match="UnauthorizedVerdictError"):
            test_db.record_verdict(verdict, enforce_auth=True)


def test_guard_blocks_builder_from_transitioning_to_done(builder_issue):
    """Verifies that assert_separation_of_builder_and_judge blocks builder from transitioning to review/done."""
    with pytest.raises(SeparationOfDutiesError, match="prohibited from evaluating, reviewing, or approving"):
        assert_separation_of_builder_and_judge(builder_issue, caller_principal="backend_engineer")


def test_authorized_independent_reviewer_succeeds(test_db, builder_issue):
    """Verifies that genuine independent reviewer (adversarial_red_team) records signed verdict cleanly."""
    with ExecutionContext.scope("adversarial_red_team"):
        result = pm_record_verdict(
            issue_key=builder_issue.key,
            verdict="PASS",
            findings={"audit": "genuine independent evaluation", "result": "PASS"},
            db=test_db,
        )

    assert result["status"] == "RECORDED"
    assert result["reviewer_principal"] == "adversarial_red_team"
    assert result["verdict"] == "PASS"
    assert result["signature"].startswith("sig_") or len(result["signature"]) == 64
