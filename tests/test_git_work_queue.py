"""Regression tests for Git-tracked work allocation and board import."""
from mas.pm.db import PMDatabase
from mas.pm.git_queue import load_manifest, next_tasks, sync


def test_manifest_is_valid_and_assignments_are_independent():
    data = load_manifest()
    assert len(data["tasks"]) >= 24
    assert len({task["id"] for task in data["tasks"]}) == len(data["tasks"])
    assert all(task["assignee_principal"] != task["reviewer_principal"] for task in data["tasks"])


def test_sync_is_idempotent_and_preserves_backlog(tmp_path):
    data = load_manifest()
    total_tasks = len(data["tasks"])
    db = PMDatabase(tmp_path / "pm.db")
    first = sync(db=db)
    assert len(first["created"]) == total_tasks
    second = sync(db=db)
    assert second["created"] == []
    assert len(second["skipped"]) == total_tasks
    project = db.get_project_by_key("MAS")
    issues = db.list_issues(project_id=project.id)
    assert len(issues) == total_tasks
    assert all(issue.current_state.value == "BACKLOG" for issue in issues)
    assert all(issue.assignee_principal for issue in issues)


def test_agent_pickup_respects_dependencies(tmp_path):
    db = PMDatabase(tmp_path / "pm.db")
    sync(db=db)
    security = next_tasks("security_sre", db=db)
    sec_ids = [task["id"] for task in security]
    assert "SEC-01" in sec_ids
    assert "SEC-05" in sec_ids
    frontend = next_tasks("frontend_engineer", db=db)
    assert frontend == []
    platform = next_tasks("platform_sre", db=db)
    plat_ids = [task["id"] for task in platform]
    assert "OPS-01" in plat_ids
    assert "OPS-09" in plat_ids


def test_sync_reconciles_unassigned_issues(tmp_path):
    db = PMDatabase(tmp_path / "pm.db")
    sync(db=db)
    project = db.get_project_by_key("MAS")
    issue = db.list_issues(project_id=project.id)[0]
    # Set assignee to None to simulate unassigned backlog state
    db.update_issue_assignee(issue.id, None)
    refreshed = db.get_issue(issue.id)
    assert refreshed.assignee_principal is None

    # Reconcile via sync
    result = sync(db=db, reconcile_assignees=True)
    assert len(result["reconciled"]) >= 1
    reconciled_issue = db.get_issue(issue.id)
    assert reconciled_issue.assignee_principal is not None
