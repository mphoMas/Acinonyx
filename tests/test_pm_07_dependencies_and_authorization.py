"""
tests/test_pm_07_dependencies_and_authorization.py: Unit and integration tests for PM-07.
Validates:
- Dependency graph resolution and enforcement before execution or claim.
- FSM fail-closed behavior on unresolved dependencies.
- Authenticated assignment and reassignment authorization rules.
- Agent concurrency WIP enforcement during task claiming.
"""

import tempfile
from pathlib import Path
import pytest

from mas.pm.db import PMDatabase
from mas.pm.fsm import FSMEngine
from mas.pm.guards import (
    AssignmentAuthorizationError,
    DependencyUnresolvedError,
    WIPLimitExceededError,
)
from mas.pm.models import Issue, IssueState, IssueType, PriorityLevel, Project
from mas.pm.tools import pm_add_dependency, pm_assign_issue, pm_claim_task
from mas.security import ExecutionContext


@pytest.fixture
def test_pm():
    """Provides a fresh isolated PMDatabase in a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_pm07.db"
        db = PMDatabase(db_path)
        proj = Project(id="proj-1", key="MAS", name="Test Project", token_budget=1_000_000)
        db.create_project(proj)
        yield db


def _create_sample_issue(db: PMDatabase, key: str, title: str, assignee: str = None) -> Issue:
    issue = Issue(
        id=f"id-{key.lower()}",
        project_id="proj-1",
        key=key,
        title=title,
        description=f"Description for {key}",
        issue_type=IssueType.TASK,
        current_state=IssueState.STAGED,
        priority=PriorityLevel.HIGH,
        assignee_principal=assignee,
        appetite_tokens=50000,
        appetite_timeout_s=1800,
        path_whitelist=["mas/", "tests/"],
        forbidden_paths=[".env"],
    )
    return db.create_issue(issue)


def test_dependency_registration_and_querying(test_pm):
    task_a = _create_sample_issue(test_pm, "MAS-101", "Prerequisite Task A", "backend_engineer")
    task_b = _create_sample_issue(test_pm, "MAS-102", "Dependent Task B", "backend_engineer")

    # Self-dependency must fail
    with pytest.raises(ValueError, match="cannot depend on itself"):
        test_pm.add_dependency(task_a.id, task_a.id)

    # Register dependency: Task B depends on Task A
    pm_add_dependency("MAS-101", "MAS-102", db=test_pm)

    deps = test_pm.get_dependencies("MAS-102")
    assert len(deps) == 1
    assert deps[0].key == "MAS-101"

    unresolved = test_pm.get_unresolved_dependencies("MAS-102")
    assert len(unresolved) == 1
    assert unresolved[0].key == "MAS-101"

    # Mark Task A as DONE
    test_pm.update_issue_state(task_a.id, IssueState.DONE, triggered_by="test")
    unresolved_after = test_pm.get_unresolved_dependencies("MAS-102")
    assert len(unresolved_after) == 0


def test_fsm_blocks_transition_when_dependencies_unresolved(test_pm):
    task_a = _create_sample_issue(test_pm, "MAS-103", "Prerequisite Task A", "backend_engineer")
    task_b = _create_sample_issue(test_pm, "MAS-104", "Dependent Task B", "backend_engineer")

    test_pm.add_dependency(task_a.id, task_b.id)
    fsm = FSMEngine(test_pm)

    # Attempting to start Task B before Task A is DONE must fail closed
    with ExecutionContext.scope("backend_engineer"):
        with pytest.raises(DependencyUnresolvedError, match="blocked by unresolved dependencies"):
            fsm.transition("MAS-104", IssueState.IN_PROGRESS, caller_principal="backend_engineer")

    # Mark Task A as DONE
    test_pm.update_issue_state(task_a.id, IssueState.DONE, triggered_by="test")

    # Now Task B can enter IN_PROGRESS
    with ExecutionContext.scope("backend_engineer"):
        updated_b = fsm.transition("MAS-104", IssueState.IN_PROGRESS, caller_principal="backend_engineer")
        assert updated_b.current_state == IssueState.IN_PROGRESS


def test_pm_claim_task_enforces_dependencies(test_pm):
    task_a = _create_sample_issue(test_pm, "MAS-105", "Prerequisite Task A", None)
    task_b = _create_sample_issue(test_pm, "MAS-106", "Dependent Task B", None)

    test_pm.add_dependency(task_a.id, task_b.id)

    # Claiming Task B while Task A is not DONE must be rejected
    with ExecutionContext.scope("platform_sre"):
        with pytest.raises(DependencyUnresolvedError, match="blocked by unresolved dependencies"):
            pm_claim_task("MAS-106", agent_principal="platform_sre", caller_principal="platform_sre", db=test_pm)

    # Mark Task A as DONE
    test_pm.update_issue_state(task_a.id, IssueState.DONE, triggered_by="test")

    # Now claim succeeds
    with ExecutionContext.scope("platform_sre"):
        claim_res = pm_claim_task("MAS-106", agent_principal="platform_sre", caller_principal="platform_sre", db=test_pm)
        assert claim_res["status"] == "CLAIMED"
        assert claim_res["assignee_principal"] == "platform_sre"
        assert claim_res["current_state"] == "IN_PROGRESS"


def test_assignment_authorization_rules(test_pm):
    task = _create_sample_issue(test_pm, "MAS-107", "Security Task", None)

    # 1. Unassigned task can be assigned to self
    with ExecutionContext.scope("security_sre"):
        res = pm_assign_issue("MAS-107", "security_sre", caller_principal="security_sre", db=test_pm)
        assert res["status"] == "ASSIGNED"

    # 2. Unauthorized third-party agent cannot reassign someone else's task
    with ExecutionContext.scope("adversarial_red_team"):
        with pytest.raises(AssignmentAuthorizationError, match="Unauthorized reassignment"):
            pm_assign_issue(
                "MAS-107",
                "adversarial_red_team",
                caller_principal="adversarial_red_team",
                db=test_pm,
            )

    # 3. Current assignee CAN reassign or release
    with ExecutionContext.scope("security_sre"):
        res = pm_assign_issue("MAS-107", "qa_critic", caller_principal="security_sre", db=test_pm)
        assert res["status"] == "ASSIGNED"
        assert res["assignee_principal"] == "qa_critic"

    # 4. Authorized coordinator (chief_architect) CAN reassign
    with ExecutionContext.scope("chief_architect"):
        res = pm_assign_issue("MAS-107", "backend_engineer", caller_principal="chief_architect", db=test_pm)
        assert res["status"] == "ASSIGNED"
        assert res["assignee_principal"] == "backend_engineer"


def test_claim_task_enforces_agent_wip_limit(test_pm):
    task1 = _create_sample_issue(test_pm, "MAS-108", "Task 1", None)
    task2 = _create_sample_issue(test_pm, "MAS-109", "Task 2", None)

    # Agent claims Task 1
    with ExecutionContext.scope("qa_critic"):
        pm_claim_task("MAS-108", "qa_critic", caller_principal="qa_critic", db=test_pm)

    # Agent tries to claim Task 2 while Task 1 is still IN_PROGRESS -> must fail with WIPLimitExceededError
    with ExecutionContext.scope("qa_critic"):
        with pytest.raises(WIPLimitExceededError, match="already has 1 active task"):
            pm_claim_task("MAS-109", "qa_critic", caller_principal="qa_critic", db=test_pm)
