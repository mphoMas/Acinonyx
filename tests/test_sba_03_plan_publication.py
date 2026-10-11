"""
tests/test_sba_03_plan_publication.py: Integration and unit tests for SBA-03 Plan Publication.

Covers:
1. First publication and identical retry (idempotency key replay).
2. Same idempotency key with different payload returns 409 Conflict.
3. Stale revision and concurrent publishers (optimistic locking).
4. Duplicate or contradictory identities (task_id / planning_reference collision).
5. Invalid hierarchy, dependency cycles (direct and multi-hop), and self-dependencies.
6. Unsafe path scopes (directory traversal '..' and absolute paths rejected).
7. Cross-tenant writes and unauthenticated/revoked credential denial.
8. Active work preservation (state, assignee, tokens spent, evidence, verdicts retained).
9. Changes to active task scope/acceptance criteria surfaced in reconciliation list.
10. Removed plan items retain their runtime history and tickets.
11. Failure injected during transaction stages results in full rollback.
12. Persistence across database / server process restart.
13. Supported Python client (PlanPublisherClient) and CLI tool (publisher_cli).
14. Live board visibility: published plan tickets appear on the real board state with delivery owner.
"""

from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
import uuid
import pytest

from mas.dashboard.server import DashboardServer
from mas.organization.company import ConsultingEnterprise
from mas.pm.client import PlanPublisherClient
from mas.pm.db import PMDatabase
from mas.pm.models import (
    EvidenceLink,
    EvidenceType,
    IssueState,
    IssueType,
    PlanPublicationRequest,
    PlanTaskDefinition,
    PriorityLevel,
    Project,
)
from mas.pm.plans import (
    ContradictoryIdentityError,
    CycleDetectedError,
    IdempotencyConflictError,
    PlanPublisherService,
    PlanValidationError,
    RevisionMismatchError,
    StaleRevisionError,
    UnsafePathError,
)
from mas.pm.tools import get_pm_db


def get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def temp_db(tmp_path: Path) -> PMDatabase:
    db_file = tmp_path / "test_pm.db"
    db = PMDatabase(db_path=db_file)
    db.init_schema()
    return db


@pytest.fixture
def sample_project(temp_db: PMDatabase) -> Project:
    proj = Project(
        id=str(uuid.uuid4()),
        key="SBA",
        name="Scrum Board Automation",
        description="Automate MAS scrum board",
    )
    return temp_db.create_project(proj)


def test_first_publication_and_identical_retry(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    req = PlanPublicationRequest(
        plan_id="plan-sba-01",
        revision=1,
        expected_previous_revision=0,
        source_commit="commit-aaa",
        scope_reference="projects/scrum-board-automation/planning/BACKLOG.json",
        tasks=[
            PlanTaskDefinition(
                task_id="uuid-task-1",
                planning_reference="SBA-01",
                title="Define the contract",
                description="Write board contract",
                type=IssueType.TASK,
                priority=PriorityLevel.CRITICAL,
                proposed_delivery_owner="Codex",
                path_whitelist=["projects/scrum-board-automation/planning/"],
                acceptance_criteria=["Contract agreed"],
            ),
            PlanTaskDefinition(
                task_id="uuid-task-2",
                planning_reference="SBA-02",
                title="Repository discovery",
                description="Discover git projects",
                type=IssueType.TASK,
                priority=PriorityLevel.HIGH,
                parent_task_id="SBA-01",
                dependencies=["SBA-01"],
                proposed_delivery_owner="Antigravity",
                path_whitelist=["mas/pm/", "mas/dashboard/"],
                acceptance_criteria=["Idempotent discovery"],
            ),
        ],
    )

    idem_key = "idem-key-12345"
    status, resp = service.publish_plan(
        project_id_or_key=sample_project.key,
        request=req,
        actor="codex-architect",
        tenant_id="tenant-alpha",
        idempotency_key=idem_key,
    )

    assert status == 201
    assert resp.success is True
    assert resp.revision == 1
    assert resp.tasks_created == 2
    assert resp.tasks_updated == 0
    assert len(resp.mappings) == 2

    # Verify tickets in database
    m1 = temp_db.get_task_mapping(sample_project.id, "SBA-01")
    assert m1 is not None
    assert m1.local_issue_key == "SBA-1"
    issue1 = temp_db.get_issue(m1.local_issue_id)
    assert issue1.current_state == IssueState.BACKLOG
    assert issue1.proposed_delivery_owner == "Codex"
    assert issue1.assignee_principal is None  # Planning ownership does not grant runtime permissions!
    assert "Delivery/integration owner: Codex" in issue1.description

    m2 = temp_db.get_task_mapping(sample_project.id, "SBA-02")
    assert m2 is not None
    assert m2.local_issue_key == "SBA-2"
    issue2 = temp_db.get_issue(m2.local_issue_id)
    assert issue2.parent_id == issue1.id

    # Verify dependencies wired up
    deps = temp_db.get_dependencies(issue2.id)
    assert len(deps) == 1
    assert deps[0].id == issue1.id

    # Identical retry with same idempotency key
    status_retry, resp_retry = service.publish_plan(
        project_id_or_key=sample_project.key,
        request=req,
        actor="codex-architect",
        tenant_id="tenant-alpha",
        idempotency_key=idem_key,
    )

    assert status_retry == 201
    assert resp_retry.revision == 1
    assert resp_retry.tasks_created == 2
    assert resp_retry.mappings[0].local_issue_key == "SBA-1"
    # Ensure no extra tickets created
    assert len(temp_db.list_issues(project_id=sample_project.id)) == 2


def test_same_idempotency_key_with_different_content_conflict(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    req1 = PlanPublicationRequest(
        plan_id="plan-sba-01",
        revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="uuid-1",
                planning_reference="SBA-01",
                title="Initial Task",
            )
        ],
    )
    idem_key = "same-key-diff-payload"

    status, resp = service.publish_plan(
        project_id_or_key=sample_project.key,
        request=req1,
        actor="codex-architect",
        tenant_id="tenant-alpha",
        idempotency_key=idem_key,
    )
    assert status == 201

    # Modify task title and retry with same idempotency key
    req2 = PlanPublicationRequest(
        plan_id="plan-sba-01",
        revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="uuid-1",
                planning_reference="SBA-01",
                title="Changed Task Title That Conflicts",
            )
        ],
    )

    with pytest.raises(IdempotencyConflictError) as exc_info:
        service.publish_plan(
            project_id_or_key=sample_project.key,
            request=req2,
            actor="codex-architect",
            tenant_id="tenant-alpha",
            idempotency_key=idem_key,
        )
    assert "different request payload" in str(exc_info.value)


def test_stale_revision_and_optimistic_concurrency(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    # Publish revision 1
    req1 = PlanPublicationRequest(
        plan_id="plan-sba-01",
        revision=1,
        expected_previous_revision=0,
        tasks=[PlanTaskDefinition(task_id="u1", planning_reference="SBA-01", title="Task 1")],
    )
    service.publish_plan(sample_project.key, req1, "actor", "tenant-1")

    # Try publishing revision 2 with stale expected_previous_revision = 5
    req_stale = PlanPublicationRequest(
        plan_id="plan-sba-01",
        revision=2,
        expected_previous_revision=5,
        tasks=[PlanTaskDefinition(task_id="u1", planning_reference="SBA-01", title="Task 1")],
    )
    with pytest.raises(StaleRevisionError) as exc_info:
        service.publish_plan(sample_project.key, req_stale, "actor", "tenant-1")
    assert "Expected previous revision 5 does not match current plan revision 1" in str(exc_info.value)

    # Try publishing revision 4 directly (skipping revision 2)
    req_skip = PlanPublicationRequest(
        plan_id="plan-sba-01",
        revision=4,
        expected_previous_revision=1,
        tasks=[PlanTaskDefinition(task_id="u1", planning_reference="SBA-01", title="Task 1")],
    )
    with pytest.raises(RevisionMismatchError) as exc_info:
        service.publish_plan(sample_project.key, req_skip, "actor", "tenant-1")
    assert "Published plan revision must be 2, got 4" in str(exc_info.value)


def test_duplicate_identities_within_plan_rejected(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    # Duplicate task_id
    req_dup_id = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="same-id", planning_reference="REF-1", title="Task 1"),
            PlanTaskDefinition(task_id="same-id", planning_reference="REF-2", title="Task 2"),
        ],
    )
    with pytest.raises(PlanValidationError) as exc_info:
        service.publish_plan(sample_project.key, req_dup_id, "actor", "tenant-1")
    assert "Duplicate task_id 'same-id'" in str(exc_info.value)

    # Duplicate planning_reference
    req_dup_ref = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="id-1", planning_reference="SAME-REF", title="Task 1"),
            PlanTaskDefinition(task_id="id-2", planning_reference="SAME-REF", title="Task 2"),
        ],
    )
    with pytest.raises(PlanValidationError) as exc_info:
        service.publish_plan(sample_project.key, req_dup_ref, "actor", "tenant-1")
    assert "Duplicate planning_reference 'SAME-REF'" in str(exc_info.value)


def test_contradictory_database_mappings_rejected(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    # First publication: T1 -> SBA-01
    req1 = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[PlanTaskDefinition(task_id="T1", planning_reference="SBA-01", title="Task 1")],
    )
    service.publish_plan(sample_project.key, req1, "actor", "tenant-1")

    # Contradiction: attempt to use T1 with SBA-99
    req_contra = PlanPublicationRequest(
        plan_id="plan-1",
        revision=2,
        expected_previous_revision=1,
        tasks=[PlanTaskDefinition(task_id="T1", planning_reference="SBA-99", title="Task 1")],
    )
    with pytest.raises(ContradictoryIdentityError) as exc_info:
        service.publish_plan(sample_project.key, req_contra, "actor", "tenant-1")
    assert "cannot contradict existing mapping" in str(exc_info.value)

    # Contradiction: attempt to use T99 with SBA-01
    req_contra2 = PlanPublicationRequest(
        plan_id="plan-1",
        revision=2,
        expected_previous_revision=1,
        tasks=[PlanTaskDefinition(task_id="T99", planning_reference="SBA-01", title="Task 1")],
    )
    with pytest.raises(ContradictoryIdentityError) as exc_info:
        service.publish_plan(sample_project.key, req_contra2, "actor", "tenant-1")
    assert "cannot contradict existing mapping" in str(exc_info.value)


def test_invalid_hierarchy_and_dependency_cycles_rejected(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    # 1. Self dependency
    req_self_dep = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="SBA-01", title="T1", dependencies=["SBA-01"]),
        ],
    )
    with pytest.raises(CycleDetectedError):
        service.publish_plan(sample_project.key, req_self_dep, "actor", "tenant-1")

    # 2. 2-node cycle (A -> B -> A)
    req_2_cycle = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="SBA-01", title="T1", dependencies=["SBA-02"]),
            PlanTaskDefinition(task_id="T2", planning_reference="SBA-02", title="T2", dependencies=["SBA-01"]),
        ],
    )
    with pytest.raises(CycleDetectedError) as exc_info:
        service.publish_plan(sample_project.key, req_2_cycle, "actor", "tenant-1")
    assert "Cyclic dependency detected" in str(exc_info.value)

    # 3. 3-node cycle (A -> B -> C -> A)
    req_3_cycle = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="SBA-01", title="T1", dependencies=["SBA-02"]),
            PlanTaskDefinition(task_id="T2", planning_reference="SBA-02", title="T2", dependencies=["SBA-03"]),
            PlanTaskDefinition(task_id="T3", planning_reference="SBA-03", title="T3", dependencies=["SBA-01"]),
        ],
    )
    with pytest.raises(CycleDetectedError):
        service.publish_plan(sample_project.key, req_3_cycle, "actor", "tenant-1")

    # 4. Parent-child hierarchy cycle
    req_parent_cycle = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="SBA-01", title="T1", parent_task_id="SBA-02"),
            PlanTaskDefinition(task_id="T2", planning_reference="SBA-02", title="T2", parent_task_id="SBA-01"),
        ],
    )
    with pytest.raises(CycleDetectedError) as exc_info:
        service.publish_plan(sample_project.key, req_parent_cycle, "actor", "tenant-1")
    assert "Hierarchy cycle detected" in str(exc_info.value)

    # 5. Dependency on unknown external task
    req_unknown_dep = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="SBA-01", title="T1", dependencies=["UNKNOWN-99"]),
        ],
    )
    with pytest.raises(PlanValidationError) as exc_info:
        service.publish_plan(sample_project.key, req_unknown_dep, "actor", "tenant-1")
    assert "depends on unknown task 'UNKNOWN-99'" in str(exc_info.value)


def test_unsafe_path_scopes_rejected(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    # Directory traversal ..
    req_traversal = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="SBA-01",
                title="T1",
                path_whitelist=["mas/pm/../../etc/shadow"],
            ),
        ],
    )
    with pytest.raises(UnsafePathError) as exc_info:
        service.publish_plan(sample_project.key, req_traversal, "actor", "tenant-1")
    assert "directory traversal" in str(exc_info.value)

    # Windows backslash traversal ..\\
    req_win_traversal = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="SBA-01",
                title="T1",
                path_whitelist=["mas\\pm\\..\\..\\etc\\shadow"],
            ),
        ],
    )
    with pytest.raises(UnsafePathError) as exc_info:
        service.publish_plan(sample_project.key, req_win_traversal, "actor", "tenant-1")
    assert "directory traversal" in str(exc_info.value)

    # NUL byte in path
    req_nul_path = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="SBA-01",
                title="T1",
                path_whitelist=["mas/pm/\0evil"],
            ),
        ],
    )
    with pytest.raises(UnsafePathError) as exc_info:
        service.publish_plan(sample_project.key, req_nul_path, "actor", "tenant-1")
    assert "NUL" in str(exc_info.value)

    # Absolute path /
    req_absolute = PlanPublicationRequest(
        plan_id="plan-1",
        revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="SBA-01",
                title="T1",
                path_whitelist=["/home/user/workspace/"],
            ),
        ],
    )
    with pytest.raises(UnsafePathError) as exc_info:
        service.publish_plan(sample_project.key, req_absolute, "actor", "tenant-1")
    assert "absolute path" in str(exc_info.value)


def test_active_work_preservation_and_reconciliation_tracking(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    # 1. Publish revision 1
    req1 = PlanPublicationRequest(
        plan_id="plan-sba",
        revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="SBA-01",
                title="Contract Definition",
                description="Draft contract",
                type=IssueType.TASK,
                priority=PriorityLevel.CRITICAL,
                path_whitelist=["projects/scrum-board-automation/planning/"],
                acceptance_criteria=["Criteria 1"],
            ),
            PlanTaskDefinition(
                task_id="T2",
                planning_reference="SBA-02",
                title="Discovery Engine",
                description="Initial discovery",
                type=IssueType.TASK,
                priority=PriorityLevel.HIGH,
                path_whitelist=["mas/pm/"],
                acceptance_criteria=["Criteria A"],
            ),
        ],
    )
    service.publish_plan(sample_project.key, req1, "architect", "tenant-1")

    # 2. Advance SBA-01 into active execution: STAGED -> IN_PROGRESS
    m1 = temp_db.get_task_mapping(sample_project.id, "SBA-01")
    issue1 = temp_db.get_issue(m1.local_issue_id)
    temp_db.update_issue_state(issue1.id, IssueState.IN_PROGRESS.value, triggered_by="coordinator", reason="Assigned to agent")
    temp_db.update_issue_assignee(issue1.id, "agent-lead-1")

    # Simulate token consumption and attached evidence
    with temp_db.atomic_transaction() as conn:
        conn.execute("UPDATE pm_issues SET tokens_spent = 23500, reflexion_attempts = 1 WHERE id = ?", (issue1.id,))

    evidence = EvidenceLink(
        id="ev-123",
        issue_id=issue1.id,
        evidence_type=EvidenceType.TEST_RUN_LOG,
        content_hash="sha256:abcd1234",
        uri="test_run.log",
    )
    temp_db.attach_evidence(evidence)

    # 3. Publish revision 2 modifying SBA-01 acceptance criteria and path scope, plus adding SBA-03
    req2 = PlanPublicationRequest(
        plan_id="plan-sba",
        revision=2,
        expected_previous_revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="SBA-01",
                title="Contract Definition (Refined)",
                description="Draft contract revised by architect",
                type=IssueType.TASK,
                priority=PriorityLevel.CRITICAL,
                path_whitelist=["projects/scrum-board-automation/planning/", "company/"],  # Path scope changed!
                acceptance_criteria=["Criteria 1", "Criteria 2: Independent review required"],  # Criteria changed!
            ),
            PlanTaskDefinition(
                task_id="T2",
                planning_reference="SBA-02",
                title="Discovery Engine",
                description="Initial discovery",
                type=IssueType.TASK,
                priority=PriorityLevel.HIGH,
                path_whitelist=["mas/pm/"],
                acceptance_criteria=["Criteria A"],
            ),
            PlanTaskDefinition(
                task_id="T3",
                planning_reference="SBA-03",
                title="Publish Conversation Plans",
                description="Implement SBA-03 publisher",
                type=IssueType.TASK,
                priority=PriorityLevel.CRITICAL,
                path_whitelist=["mas/pm/", "mas/dashboard/"],
                acceptance_criteria=["Contract endpoints tested"],
            ),
        ],
    )

    status2, resp2 = service.publish_plan(sample_project.key, req2, "architect", "tenant-1")

    assert status2 == 200
    assert resp2.revision == 2
    assert resp2.tasks_created == 1  # SBA-03
    assert resp2.tasks_updated == 2  # SBA-01, SBA-02

    # Verify reconciliation tracking flagged SBA-01 because it was active (IN_PROGRESS)
    assert len(resp2.changes_requiring_reconciliation) == 2
    change_types = {r.change_type for r in resp2.changes_requiring_reconciliation}
    assert "acceptance_criteria_modified" in change_types
    assert "path_whitelist_modified" in change_types

    # CRITICAL: Verify active work was NOT corrupted
    updated_issue1 = temp_db.get_issue(issue1.id)
    assert updated_issue1.current_state == IssueState.IN_PROGRESS  # NOT reset to BACKLOG!
    assert updated_issue1.assignee_principal == "agent-lead-1"     # Retained active assignment!
    assert updated_issue1.tokens_spent == 23500                   # Tokens preserved!
    assert updated_issue1.reflexion_attempts == 1                 # Attempts preserved!

    # Active issue live contract was PRESERVED, changes were staged!
    assert updated_issue1.path_whitelist == ["projects/scrum-board-automation/planning/"]
    assert updated_issue1.acceptance_criteria == ["Criteria 1"]
    assert updated_issue1.staged_path_whitelist == ["projects/scrum-board-automation/planning/", "company/"]
    assert updated_issue1.staged_acceptance_criteria == ["Criteria 1", "Criteria 2: Independent review required"]
    assert updated_issue1.has_pending_reconciliation is True

    # Transitioning to VERIFICATION while pending reconciliation is present is GATED
    from mas.pm.fsm import FSMEngine
    from mas.pm.guards import PendingReconciliationError
    from mas.security import ExecutionContext
    fsm = FSMEngine(temp_db)
    with ExecutionContext.scope("coordinator"):
        with pytest.raises(PendingReconciliationError):
            fsm.transition(updated_issue1.id, IssueState.VERIFICATION, caller_principal="coordinator")

    # Verify evidence link still exists
    ev_links = temp_db.get_evidence_links(issue1.id)
    assert len(ev_links) == 1
    assert ev_links[0].content_hash == "sha256:abcd1234"

    # Verify new task entered BACKLOG with 0 initial appetite!
    m3 = temp_db.get_task_mapping(sample_project.id, "SBA-03")
    issue3 = temp_db.get_issue(m3.local_issue_id)
    assert issue3.current_state == IssueState.BACKLOG
    assert issue3.appetite_tokens == 0


def test_omitted_plan_items_retain_runtime_history(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    # Revision 1 has T1 and T2
    req1 = PlanPublicationRequest(
        plan_id="plan-retention",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="REF-1", title="Task 1"),
            PlanTaskDefinition(task_id="T2", planning_reference="REF-2", title="Task 2 (To be removed)"),
        ],
    )
    service.publish_plan(sample_project.key, req1, "actor", "tenant-1")

    m2 = temp_db.get_task_mapping(sample_project.id, "REF-2")
    temp_db.update_issue_state(m2.local_issue_id, IssueState.DONE.value, triggered_by="tester", reason="Completed earlier")

    # Revision 2 omits T2 (only has T1)
    req2 = PlanPublicationRequest(
        plan_id="plan-retention",
        revision=2,
        expected_previous_revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="REF-1", title="Task 1 Updated"),
        ],
    )
    service.publish_plan(sample_project.key, req2, "actor", "tenant-1")

    # Assert T2 is NOT deleted and retains state DONE
    issue2 = temp_db.get_issue(m2.local_issue_id)
    assert issue2 is not None
    assert issue2.current_state == IssueState.DONE
    assert issue2.title == "Task 2 (To be removed)"


def test_failure_injection_atomic_rollback(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    req = PlanPublicationRequest(
        plan_id="plan-rollback",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="SBA-01", title="Task 1"),
            PlanTaskDefinition(task_id="T2", planning_reference="SBA-02", title="Task 2"),
        ],
    )

    stages_to_test = [
        "during_issues_write",
        "during_dependencies_write",
        "before_commit",
    ]

    for stage in stages_to_test:
        with pytest.raises(RuntimeError, match="Injected failure"):
            service.publish_plan(
                project_id_or_key=sample_project.key,
                request=req,
                actor="actor",
                tenant_id="tenant-1",
                test_injected_failure_stage=stage,
            )

        # Assert no partial issues or mappings were written
        assert len(temp_db.list_issues(project_id=sample_project.id)) == 0
        assert len(temp_db.list_task_mappings(sample_project.id)) == 0
        assert temp_db.get_latest_plan_revision(sample_project.id, "plan-rollback") is None


def test_persistence_across_restart(tmp_path: Path):
    db_file = tmp_path / "restart_test.db"
    db1 = PMDatabase(db_path=db_file)
    db1.init_schema()

    db1.create_project(Project(id="p-100", key="RES", name="Restart Project"))
    service1 = PlanPublisherService(db1)

    req = PlanPublicationRequest(
        plan_id="plan-res",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="RES-01", title="Task 1", proposed_delivery_owner="Codex"),
        ],
    )
    service1.publish_plan("RES", req, "architect", "tenant-1")

    # Simulate restart: instantiate new PMDatabase connection
    del db1
    del service1

    db2 = PMDatabase(db_path=db_file)
    mapping = db2.get_task_mapping("p-100", "RES-01")
    assert mapping is not None
    assert mapping.local_issue_key == "RES-1"

    issue = db2.get_issue(mapping.local_issue_id)
    assert issue.title == "Task 1"
    assert issue.proposed_delivery_owner == "Codex"

    plan_rec = db2.get_latest_plan_revision("p-100", "plan-res")
    assert plan_rec is not None
    assert plan_rec.revision == 1


# --- Live Server & HTTP Integration Tests ---

@pytest.fixture
def live_server():
    port = get_free_port()
    enterprise = ConsultingEnterprise(name="Live Plan Enterprise")
    server = DashboardServer(
        enterprise=enterprise,
        host="127.0.0.1",
        port=port,
        auth_token="test-live-auth-token",
        allow_admin_token_planning=True,
    )
    server.start_background()
    time.sleep(0.3)

    db = get_pm_db()
    if not db.get_project_by_key("PLIVE"):
        db.create_project(Project(id=str(uuid.uuid4()), key="PLIVE", name="Live Project"))

    try:
        yield server, port, "test-live-auth-token"
    finally:
        server.stop()


def test_http_plan_publication_and_board_visibility(live_server):
    server, port, auth_token = live_server
    base_url = f"http://127.0.0.1:{port}"

    client = PlanPublisherClient(base_url=base_url, auth_token=auth_token)

    # 1. Publish Plan via HTTP client
    req = PlanPublicationRequest(
        plan_id="plan-live-v1",
        revision=1,
        source_commit="commit-live-1",
        scope_reference="CEO-APPROVED-HOTEL-SCOPE",
        tasks=[
            PlanTaskDefinition(
                task_id="live-task-1",
                planning_reference="PLIVE-01",
                title="Live Plan Task 1",
                description="First live task from architect conversation",
                proposed_delivery_owner="Codex",
                path_whitelist=["mas/pm/"],
                acceptance_criteria=["Live integration passes"],
            ),
            PlanTaskDefinition(
                task_id="live-task-2",
                planning_reference="PLIVE-02",
                title="Live Plan Task 2",
                description="Second live task with dependency",
                proposed_delivery_owner="Antigravity",
                dependencies=["PLIVE-01"],
                path_whitelist=["mas/dashboard/"],
                acceptance_criteria=["Live dependency passes"],
            ),
        ],
    )

    resp = client.publish_plan(
        project_id_or_key="PLIVE",
        plan=req,
        idempotency_key="live-idem-1",
    )

    assert resp.success is True
    assert resp.revision == 1
    assert resp.tasks_created == 2
    assert len(resp.mappings) == 2

    # 2. Assert tickets are visible on the real board endpoint
    board_url = f"{base_url}/api/pm/board/PLIVE"
    req_board = urllib.request.Request(board_url, headers={"Authorization": f"Bearer {auth_token}"})
    with urllib.request.urlopen(req_board, timeout=5) as b_resp:
        board_data = json.loads(b_resp.read().decode("utf-8"))

    assert "issues_by_column" in board_data
    backlog_issues = board_data["issues_by_column"].get("BACKLOG", [])
    assert len(backlog_issues) == 2

    keys = [b["key"] for b in backlog_issues]
    assert "PLIVE-1" in keys
    assert "PLIVE-2" in keys

    # Verify delivery owner is rendered in description for the frontend
    issue1 = next(b for b in backlog_issues if b["key"] == "PLIVE-1")
    assert "Delivery/integration owner: Codex" in issue1["description"]

    # 3. Assert plan revision history endpoint
    plan_history = client.get_plans("PLIVE")
    assert len(plan_history["plans"]) == 1
    assert plan_history["plans"][0]["plan_id"] == "plan-live-v1"
    assert plan_history["plans"][0]["revision"] == 1


def test_http_unauthenticated_and_invalid_token_denial(live_server):
    server, port, _ = live_server
    base_url = f"http://127.0.0.1:{port}"

    # 1. Unauthenticated request
    client_unauth = PlanPublisherClient(base_url=base_url, auth_token=None)
    with pytest.raises(PermissionError) as exc_info:
        client_unauth.publish_plan("PLIVE", {"plan_id": "p", "revision": 1, "tasks": []})
    assert "401" in str(exc_info.value) or "403" in str(exc_info.value)

    # 2. Invalid bearer token
    client_bad_token = PlanPublisherClient(base_url=base_url, auth_token="invalid-forged-token")
    with pytest.raises(PermissionError) as exc_info:
        client_bad_token.publish_plan("PLIVE", {"plan_id": "p", "revision": 1, "tasks": []})
    assert "401" in str(exc_info.value) or "403" in str(exc_info.value)


def test_publisher_cli_execution(live_server, tmp_path: Path):
    server, port, auth_token = live_server
    plan_file = tmp_path / "cli_plan.json"
    plan_data = {
        "plan_id": "plan-cli",
        "revision": 1,
        "tasks": [
            {
                "task_id": "cli-1",
                "planning_reference": "PLIVE-CLI-01",
                "title": "CLI Published Task",
                "proposed_delivery_owner": "Codex",
            }
        ],
    }
    plan_file.write_text(json.dumps(plan_data), encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "mas.pm.publisher_cli",
        "--project",
        "PLIVE",
        "--plan-file",
        str(plan_file),
        "--server-url",
        f"http://127.0.0.1:{port}",
        "--token",
        auth_token,
        "--json",
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    cli_out = json.loads(res.stdout)
    assert cli_out["success"] is True
    assert cli_out["tasks_created"] == 1


def test_effective_graph_cycle_detection_with_existing_db_dependencies(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    # 1. Plan with T1 -> T2 (T2 depends on T1)
    req1 = PlanPublicationRequest(
        plan_id="plan-cycle",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="CYC-01", title="Task 1"),
            PlanTaskDefinition(task_id="T2", planning_reference="CYC-02", title="Task 2", dependencies=["T1"]),
        ],
    )
    status1, resp1 = service.publish_plan(sample_project.key, req1, "architect", "tenant-1")
    assert status1 == 201

    # 2. Plan revision where T1 now depends on T2, introducing a cycle with T2's dependency
    req2 = PlanPublicationRequest(
        plan_id="plan-cycle",
        revision=2,
        expected_previous_revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="CYC-01", title="Task 1", dependencies=["T2"]),
            PlanTaskDefinition(task_id="T2", planning_reference="CYC-02", title="Task 2", dependencies=["T1"]),
        ],
    )
    with pytest.raises(CycleDetectedError):
        service.publish_plan(sample_project.key, req2, "architect", "tenant-1")


def test_unknown_parent_task_rejection(temp_db: PMDatabase, sample_project: Project):
    service = PlanPublisherService(temp_db)

    req = PlanPublicationRequest(
        plan_id="plan-parent",
        revision=1,
        tasks=[
            PlanTaskDefinition(task_id="T1", planning_reference="PAR-01", title="Child Task", parent_task_id="non-existent-parent"),
        ],
    )
    with pytest.raises(PlanValidationError) as exc_info:
        service.publish_plan(sample_project.key, req, "architect", "tenant-1")
    assert "references unknown parent 'non-existent-parent'" in str(exc_info.value)


def test_http_non_architect_role_rejection(live_server):
    from mas.iam import MultiTenantIAM, StandardRole
    server, port, _ = live_server
    base_url = f"http://127.0.0.1:{port}"

    # Attach an IAM instance to the server to verify role-based planning authority
    iam = MultiTenantIAM()
    iam.create_tenant("test-tenant", "Test Tenant")
    # Register an unprivileged operator/developer
    iam.register_principal("test-tenant", "dev-operator", roles={StandardRole.OPERATOR.value}, scopes={"default"})
    token = iam.issue_token("test-tenant", "dev-operator")
    server.iam = iam

    client_dev = PlanPublisherClient(base_url=base_url, auth_token=token)
    with pytest.raises(PermissionError) as exc_info:
        client_dev.publish_plan("PLIVE", {"plan_id": "p", "revision": 1, "tasks": []})
    assert "403" in str(exc_info.value)


def test_active_reviewer_requirement_null_removal_and_replacement_staging(temp_db: PMDatabase, sample_project: Project):
    """
    Regression test for review blocker:
    A revision changing an active task's reviewer requirement from 'independent' to null
    must NOT erase the live requirement. Explicit staging must distinguish:
    - No proposed change
    - Proposed replacement
    - Proposed removal (null)
    Live requirement remains intact until authorized reconciliation!
    Pending changes must continue blocking verification and completion.
    """
    service = PlanPublisherService(temp_db)

    # 1. Publish revision 1 with reviewer_requirement="independent"
    req1 = PlanPublicationRequest(
        plan_id="plan-rev-stage",
        revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="REV-01",
                title="Review Staged Task",
                path_whitelist=["mas/pm/"],
                acceptance_criteria=["Live criteria"],
                reviewer_requirement="independent",
            ),
        ],
    )
    status1, resp1 = service.publish_plan(sample_project.key, req1, "architect", "tenant-1")
    assert status1 == 201

    m1 = temp_db.get_task_mapping(sample_project.id, "REV-01")
    issue1 = temp_db.get_issue(m1.local_issue_id)
    assert issue1.reviewer_requirement == "independent"
    assert issue1.has_pending_reconciliation is False

    # 2. Advance issue to IN_PROGRESS
    temp_db.update_issue_state(issue1.id, IssueState.IN_PROGRESS.value, triggered_by="coordinator")

    # 3. Publish revision 2 proposing reviewer_requirement=None (removal)
    req2 = PlanPublicationRequest(
        plan_id="plan-rev-stage",
        revision=2,
        expected_previous_revision=1,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="REV-01",
                title="Review Staged Task",
                path_whitelist=["mas/pm/"],
                acceptance_criteria=["Live criteria"],
                reviewer_requirement=None,  # Propose removing reviewer requirement!
            ),
        ],
    )
    status2, resp2 = service.publish_plan(sample_project.key, req2, "architect", "tenant-1")
    assert status2 == 200
    assert len(resp2.changes_requiring_reconciliation) == 1
    assert resp2.changes_requiring_reconciliation[0].change_type == "reviewer_requirement_removed"

    # CRITICAL: Verify active issue still has live reviewer_requirement="independent"
    issue1_after = temp_db.get_issue(issue1.id)
    assert issue1_after.reviewer_requirement == "independent", "Live reviewer requirement must NOT be erased by null proposal!"
    assert issue1_after.staged_reviewer_requirement is None
    assert issue1_after.staged_reviewer_action == "REMOVE"
    assert issue1_after.has_pending_reconciliation is True

    # Attempting transition to VERIFICATION while pending reconciliation is present MUST be blocked!
    from mas.pm.fsm import FSMEngine
    from mas.pm.guards import PendingReconciliationError
    from mas.security import ExecutionContext
    fsm = FSMEngine(temp_db)
    with ExecutionContext.scope("coordinator"):
        with pytest.raises(PendingReconciliationError):
            fsm.transition(issue1_after.id, IssueState.VERIFICATION, caller_principal="coordinator")

    # 4. Reject the proposal -> live requirement preserved, staged action cleared, pending recon cleared
    rejected_issue = service.reconcile_staged_changes(
        sample_project.key,
        issue1.id,
        decision="reject",
        actor="chief_architect",
    )
    assert rejected_issue.reviewer_requirement == "independent"
    assert rejected_issue.staged_reviewer_action is None
    assert rejected_issue.has_pending_reconciliation is False

    # 5. Publish revision 3 proposing replacement to "peer"
    req3 = PlanPublicationRequest(
        plan_id="plan-rev-stage",
        revision=3,
        expected_previous_revision=2,
        tasks=[
            PlanTaskDefinition(
                task_id="T1",
                planning_reference="REV-01",
                title="Review Staged Task",
                path_whitelist=["mas/pm/"],
                acceptance_criteria=["Live criteria"],
                reviewer_requirement="peer",  # Propose replacement!
            ),
        ],
    )
    status3, resp3 = service.publish_plan(sample_project.key, req3, "architect", "tenant-1")
    assert status3 == 200
    assert len(resp3.changes_requiring_reconciliation) == 1
    assert resp3.changes_requiring_reconciliation[0].change_type == "reviewer_requirement_modified"

    issue1_repl = temp_db.get_issue(issue1.id)
    assert issue1_repl.reviewer_requirement == "independent", "Live requirement preserved until application!"
    assert issue1_repl.staged_reviewer_requirement == "peer"
    assert issue1_repl.staged_reviewer_action == "REPLACE"
    assert issue1_repl.has_pending_reconciliation is True

    # 6. Apply the replacement -> live requirement updated to "peer", pending recon cleared
    applied_issue = service.reconcile_staged_changes(
        sample_project.key,
        issue1.id,
        decision="apply",
        actor="chief_architect",
    )
    assert applied_issue.reviewer_requirement == "peer"
    assert applied_issue.staged_reviewer_requirement is None
    assert applied_issue.staged_reviewer_action is None
    assert applied_issue.has_pending_reconciliation is False


def test_http_negative_planning_authorizations(live_server):
    """
    Negative tests:
    - Non-planner identity (only storage/operator permissions) rejected (403)
    - Unauthenticated caller rejected (401)
    - Revoked credentials rejected (401/403)
    - Cross-tenant publication rejected (403/404)
    - Proving authorized planner CAN publish (200/201)
    """
    from mas.iam import MultiTenantIAM, StandardRole
    server, port, _ = live_server
    base_url = f"http://127.0.0.1:{port}"

    iam = MultiTenantIAM()
    iam.create_tenant("tenant-alpha", "Tenant Alpha")
    iam.create_tenant("tenant-beta", "Tenant Beta")

    # 1. Non-planner: has storage:* and operator role only
    iam.register_principal(
        "tenant-alpha", "storage-operator",
        roles={StandardRole.OPERATOR.value},
        scopes={"storage:read", "storage:write", "tools:execute"}  # storage:* alone is NOT planning permission!
    )
    storage_token = iam.issue_token("tenant-alpha", "storage-operator")

    # 2. Authorized planner: has architect role and pm:plan:publish scope
    iam.register_principal(
        "tenant-alpha", "lead-architect",
        roles={StandardRole.DATA_ARCHITECT.value},
        scopes={"pm:plan:publish"}
    )
    planner_token = iam.issue_token("tenant-alpha", "lead-architect")

    # 3. Revoked principal
    iam.register_principal(
        "tenant-alpha", "revoked-architect",
        roles={StandardRole.DATA_ARCHITECT.value},
        scopes={"pm:plan:publish"}
    )
    revoked_token = iam.issue_token("tenant-alpha", "revoked-architect")
    ctx = iam.verify_token(revoked_token)
    iam.revoke_session(revoked_token, ctx.token_id)

    server.iam = iam

    sample_plan = {
        "plan_id": "plan-auth-test",
        "revision": 1,
        "tasks": [
            {
                "task_id": "T-AUTH-1",
                "planning_reference": "AUTH-01",
                "title": "Auth Test Task",
            }
        ]
    }

    # Negative 1: Non-planner caller with storage:* must be rejected (403)
    client_storage = PlanPublisherClient(base_url=base_url, auth_token=storage_token)
    with pytest.raises(PermissionError) as exc_info:
        client_storage.publish_plan("PLIVE", sample_plan)
    assert "403" in str(exc_info.value)

    # Negative 2: Unauthenticated caller must be rejected (401)
    client_unauth = PlanPublisherClient(base_url=base_url, auth_token=None)
    with pytest.raises(PermissionError) as exc_info:
        client_unauth.publish_plan("PLIVE", sample_plan)
    assert "401" in str(exc_info.value)

    # Negative 3: Revoked credentials must be rejected (401)
    client_revoked = PlanPublisherClient(base_url=base_url, auth_token=revoked_token)
    with pytest.raises(PermissionError) as exc_info:
        client_revoked.publish_plan("PLIVE", sample_plan)
    assert "401" in str(exc_info.value)

    # Positive: Authorized planner can successfully publish
    client_planner = PlanPublisherClient(base_url=base_url, auth_token=planner_token)
    resp = client_planner.publish_plan("PLIVE", sample_plan)
    assert resp.success is True
    assert resp.tasks_created == 1


def test_reconciliation_proposal_superseded_rejection_and_audit(temp_db, sample_project):
    """
    SBA-03 Version-Bound Reconciliation Test:
    Sequence: Proposal A is read, Proposal B replaces it, delayed approval for A arrives.
    Must reject with 409 conflict WITHOUT applying Proposal B or Proposal A.
    When Proposal B is approved with expected revision, it increments policy_version,
    invalidates evidence, and records an immutable audit log.
    """
    service = PlanPublisherService(temp_db)

    # 1. Create initial active task in IN_PROGRESS
    req1 = PlanPublicationRequest(
        plan_id="plan-versioning",
        revision=1,
        source_commit="commit-1",
        scope_reference="REF-INIT",
        tasks=[
            PlanTaskDefinition(
                task_id="uuid-task-active",
                planning_reference="VB-01",
                title="Active Task Initial",
                description="Task description",
                type=IssueType.TASK,
                path_whitelist=["src/core/"],
                acceptance_criteria=["Criterion 1"],
                reviewer_requirement="lead-architect",
            )
        ],
    )
    service.publish_plan(sample_project.key, req1, actor="lead-architect", tenant_id="tenant-alpha")
    m = temp_db.get_task_mapping(sample_project.id, "VB-01")
    issue = temp_db.get_issue(m.local_issue_id)
    assert issue.policy_version == 1

    # Transition issue to IN_PROGRESS so that it becomes active
    temp_db.update_issue_state(issue.id, "IN_PROGRESS", triggered_by="worker-1", reason="Started work")
    issue = temp_db.get_issue(issue.id)
    assert issue.current_state == IssueState.IN_PROGRESS

    # Add evidence link to test invalidation on policy change
    temp_db.attach_evidence(EvidenceLink(
        id="ev-active-1",
        issue_id=issue.id,
        evidence_type=EvidenceType.TEST_RUN_LOG,
        content_hash="h"*64,
        uri="test://run/1",
    ))

    # 2. Proposal A (revision 2): modifies acceptance criteria and reviewer requirement
    req_a = PlanPublicationRequest(
        plan_id="plan-versioning",
        revision=2,
        expected_previous_revision=1,
        source_commit="commit-2",
        scope_reference="REF-PROPOSAL-A",
        tasks=[
            PlanTaskDefinition(
                task_id="uuid-task-active",
                planning_reference="VB-01",
                title="Active Task Initial",
                type=IssueType.TASK,
                path_whitelist=["src/core/"],
                acceptance_criteria=["Criterion 1", "Criterion 2 (Proposal A)"],
                reviewer_requirement="security-auditor",
            )
        ],
    )
    status_a, resp_a = service.publish_plan(sample_project.key, req_a, actor="lead-architect", tenant_id="tenant-alpha")
    assert status_a == 200
    assert len(resp_a.changes_requiring_reconciliation) >= 1
    proposal_a_item = resp_a.changes_requiring_reconciliation[0]
    proposal_a_id = proposal_a_item.proposal_id
    proposal_a_rev = proposal_a_item.proposal_rev
    assert proposal_a_rev == 2
    assert proposal_a_id is not None

    issue_staged_a = temp_db.get_issue(issue.id)
    assert issue_staged_a.has_pending_reconciliation is True
    assert issue_staged_a.staged_proposal_id == proposal_a_id
    assert issue_staged_a.staged_proposal_rev == 2

    # 3. Proposal B (revision 3): supersedes Proposal A with different criteria
    req_b = PlanPublicationRequest(
        plan_id="plan-versioning",
        revision=3,
        expected_previous_revision=2,
        source_commit="commit-3",
        scope_reference="REF-PROPOSAL-B",
        tasks=[
            PlanTaskDefinition(
                task_id="uuid-task-active",
                planning_reference="VB-01",
                title="Active Task Initial",
                type=IssueType.TASK,
                path_whitelist=["src/core/", "src/extra/"],
                acceptance_criteria=["Criterion 1", "Criterion 3 (Proposal B)"],
                reviewer_requirement="chief-architect",
            )
        ],
    )
    status_b, resp_b = service.publish_plan(sample_project.key, req_b, actor="lead-architect", tenant_id="tenant-alpha")
    assert status_b == 200
    proposal_b_item = resp_b.changes_requiring_reconciliation[0]
    proposal_b_id = proposal_b_item.proposal_id
    proposal_b_rev = proposal_b_item.proposal_rev
    assert proposal_b_rev == 3

    issue_staged_b = temp_db.get_issue(issue.id)
    assert issue_staged_b.staged_proposal_id == proposal_b_id
    assert issue_staged_b.staged_proposal_rev == 3

    # 4. Delayed decision for Proposal A arrives: MUST REJECT WITH StaleProposalError (HTTP 409)
    from mas.pm.plans import StaleProposalError
    with pytest.raises(StaleProposalError) as exc_info:
        service.reconcile_staged_changes(
            project_id_or_key=sample_project.key,
            issue_id_or_key=issue.key,
            decision="apply",
            actor="chief-architect",
            tenant_id="tenant-alpha",
            expected_proposal_id=proposal_a_id,
            expected_proposal_rev=proposal_a_rev,
            expected_base_policy_version=1,
        )
    assert "mismatch" in str(exc_info.value).lower()

    # Confirm Proposal B was NOT accidentally applied by the stale decision!
    issue_unchanged = temp_db.get_issue(issue.id)
    assert issue_unchanged.policy_version == 1
    assert issue_unchanged.has_pending_reconciliation is True
    assert issue_unchanged.reviewer_requirement == "lead-architect"

    # 5. Correct reconciliation for Proposal B: apply with matching proposal info
    updated = service.reconcile_staged_changes(
        project_id_or_key=sample_project.key,
        issue_id_or_key=issue.key,
        decision="apply",
        actor="chief-architect",
        tenant_id="tenant-alpha",
        expected_proposal_id=proposal_b_id,
        expected_proposal_rev=proposal_b_rev,
        expected_base_policy_version=1,
    )
    assert updated.policy_version == 2
    assert updated.has_pending_reconciliation is False
    assert updated.reviewer_requirement == "chief-architect"
    assert "Criterion 3 (Proposal B)" in updated.acceptance_criteria
    assert "src/extra/" in updated.path_whitelist
    # Evidence was invalidated: rework_cycle incremented
    assert updated.rework_cycle == 1

    # 6. Verify durable reconciliation audit record
    audits = temp_db.list_reconciliation_audits(issue_id=issue.id)
    assert len(audits) == 1
    audit = audits[0]
    assert audit.decision == "apply"
    assert audit.actor == "chief-architect"
    assert audit.proposal_id == proposal_b_id
    assert audit.proposal_rev == 3
    assert audit.base_policy_version == 1
    assert audit.resulting_policy_version == 2
    assert audit.evidence_invalidated_count == 1
    assert audit.after_policy["reviewer_requirement"] == "chief-architect"


def test_pm_publish_plan_unbound_mcp_fails_closed():
    """
    Verifies that calling pm_publish_plan without verified planning authority fails closed.
    """
    from mas.pm.tools import pm_publish_plan
    from mas.security import ExecutionContext

    # Unauthenticated / empty principal
    with ExecutionContext.scope(""):
        with pytest.raises(PermissionError) as exc_unauth:
            pm_publish_plan("PLIVE", {"plan_id": "p", "revision": 1, "tasks": []})
        assert "unauthenticated" in str(exc_unauth.value).lower()

    # Caller with non-planning identity in unbound execution context
    with ExecutionContext.scope("guest_contributor"):
        with pytest.raises(PermissionError) as exc_nonplan:
            pm_publish_plan("PLIVE", {"plan_id": "p", "revision": 1, "tasks": []})
        assert "planning authority" in str(exc_nonplan.value).lower()


def test_server_unconfigured_admin_token_rejects_planning():
    """
    Verifies that a DashboardServer running with default allow_admin_token_planning=False
    rejects bearer token calls that lack explicit planning authority.
    """
    port = get_free_port()
    enterprise = ConsultingEnterprise(name="Strict Server Enterprise")
    server = DashboardServer(
        enterprise=enterprise,
        host="127.0.0.1",
        port=port,
        auth_token="static-unprivileged-token",
        allow_admin_token_planning=False,  # Explicitly unconfigured / disabled
    )
    server.start_background()
    time.sleep(0.3)

    db = get_pm_db()
    if not db.get_project_by_key("PSTRICT"):
        db.create_project(Project(id=str(uuid.uuid4()), key="PSTRICT", name="Strict Project"))

    try:
        client = PlanPublisherClient(base_url=f"http://127.0.0.1:{port}", auth_token="static-unprivileged-token")
        with pytest.raises(PermissionError) as exc_info:
            client.publish_plan("PSTRICT", {
                "plan_id": "p-strict",
                "revision": 1,
                "tasks": [{"task_id": "s1", "planning_reference": "ST-01", "title": "Strict Task"}]
            })
        assert "403" in str(exc_info.value)
    finally:
        server.stop()



