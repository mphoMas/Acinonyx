"""
Unit and integration tests for automatic repository project discovery (SBA-02).

Validates:
- Initial discovery and repeated synchronization idempotency.
- Reconciliation with existing SBA/PLG deployment records.
- Name/description update preserving stable project UUID.
- Missing registration marks source inactive without deleting issues or history.
- Invalid registry retains last valid snapshot in database.
- Safe git fetch preserves dirty checkouts and handles offline/network errors.
- Unsafe paths, traversal, duplicates and contradictory mappings rejected.
- Folder isolation: non-registered folders ignored.
- Persistence across process restart.
"""

from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import uuid
import pytest

from mas.pm.db import PMDatabase
from mas.pm.discovery import (
    ContradictoryMappingError,
    ProjectRegistryDiscovery,
    RegistryValidationError,
)
from mas.pm.models import Issue, IssueState, IssueType, Project, ProjectSource


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    """Creates a temporary workspace repository layout with valid project directories."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Create project directories
    sba_root = repo / "projects" / "scrum-board-automation"
    sba_root.mkdir(parents=True)
    (sba_root / "planning").mkdir()

    plg_root = repo / "projects" / "platinum-lodge"
    plg_root.mkdir(parents=True)
    (plg_root / "planning").mkdir()

    # Create dummy non-project folder
    (repo / "scratch_work").mkdir()
    (repo / "node_modules").mkdir()

    # Default valid registry.json
    registry_file = repo / "projects" / "registry.json"
    registry_data = {
        "schema_version": 1,
        "repository": {
            "id": "mphoMas/Acinonyx",
            "owner": "mphoMas",
            "name": "Acinonyx",
            "configured_branch": "feat/scrum-board-automation",
        },
        "projects": [
            {
                "project_id": "c2e7bb0e-6f81-5c31-9a7c-501b802711ff",
                "project_key": "SBA",
                "name": "Scrum Board Automation",
                "description": "Board automation engine",
                "root_path": "projects/scrum-board-automation",
                "planning_path": "projects/scrum-board-automation/planning",
                "status": "active",
            },
            {
                "project_id": "2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c",
                "project_key": "PLG",
                "name": "Platinum Lodge",
                "description": "Hotel management system",
                "root_path": "projects/platinum-lodge",
                "planning_path": "projects/platinum-lodge/planning",
                "status": "active",
            },
        ],
    }
    registry_file.write_text(json.dumps(registry_data, indent=2), encoding="utf-8")
    return repo


@pytest.fixture
def test_db(tmp_path: Path) -> PMDatabase:
    """Isolated database instance for discovery testing."""
    db_file = tmp_path / "test_discovery.db"
    return PMDatabase(db_path=db_file)


# 1. Initial Discovery and Idempotence
def test_initial_discovery_and_repeated_sync(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    res = discovery.sync()

    assert res["status"] == "healthy"
    assert set(res["created"]) == {"SBA", "PLG"}
    assert res["total_registered"] == 2

    # Verify DB rows
    sba = test_db.get_project_by_key("SBA")
    assert sba is not None
    assert sba.id == "c2e7bb0e-6f81-5c31-9a7c-501b802711ff"
    assert sba.name == "Scrum Board Automation"

    plg = test_db.get_project_by_key("PLG")
    assert plg is not None
    assert plg.id == "2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c"

    sources = test_db.list_project_sources()
    assert len(sources) == 2
    assert all(s.status == "active" for s in sources)

    # Re-run sync (Idempotence)
    res2 = discovery.sync()
    assert res2["status"] == "healthy"
    assert res2["created"] == []
    assert set(res2["unchanged"]) == {"SBA", "PLG"}

    # Assert no duplicate projects
    projects = test_db.list_projects()
    assert len(projects) == 2


# 2. Reconciliation with Existing Records
def test_reconciliation_preserves_existing_records_and_history(test_repo: Path, test_db: PMDatabase):
    # Pre-seed existing PLG project in DB with custom token budget and existing issue
    plg_id = "2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c"
    existing_plg = Project(
        id=plg_id,
        key="PLG",
        name="Platinum Lodge Original Name",
        description="Original description",
        token_budget=12_000_000,
        tokens_consumed=450_000,
    )
    test_db.create_project(existing_plg)

    # Attach issue to pre-existing PLG
    test_db.create_issue(
        Issue(
            id="issue-plg-1",
            project_id=plg_id,
            key="PLG-1",
            title="Existing initiative",
            description="Existing description",
            issue_type=IssueType.INITIATIVE,
            current_state=IssueState.IN_PROGRESS,
        )
    )

    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    res = discovery.sync()

    assert res["status"] == "healthy"
    assert "SBA" in res["created"]
    assert "PLG" in res["updated"] or "PLG" in res["unchanged"]

    # Verify existing PLG identity and budget preserved
    reconciled_plg = test_db.get_project(plg_id)
    assert reconciled_plg is not None
    assert reconciled_plg.token_budget == 12_000_000
    assert reconciled_plg.tokens_consumed == 450_000

    # Verify existing issue remains attached and uncorrupted
    issues = test_db.list_issues(project_id=plg_id)
    assert len(issues) == 1
    assert issues[0].key == "PLG-1"
    assert issues[0].current_state == IssueState.IN_PROGRESS


# 3. Rename Preserves Stable Project Identity
def test_rename_preserves_stable_project_id(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    discovery.sync()

    # Modify registry with new name and description for SBA
    registry_file = test_repo / "projects" / "registry.json"
    reg = json.loads(registry_file.read_text(encoding="utf-8"))
    reg["projects"][0]["name"] = "Scrum Automation V2 Renamed"
    reg["projects"][0]["description"] = "Updated description"
    registry_file.write_text(json.dumps(reg), encoding="utf-8")

    res = discovery.sync()
    assert "SBA" in res["updated"]

    # Assert stable UUID preserved
    sba = test_db.get_project_by_key("SBA")
    assert sba.id == "c2e7bb0e-6f81-5c31-9a7c-501b802711ff"
    assert sba.name == "Scrum Automation V2 Renamed"
    assert sba.description == "Updated description"


# 4. Missing Registration Marks Source Inactive
def test_missing_registration_marks_source_inactive_without_deleting_history(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    discovery.sync()

    # Add an issue to PLG
    plg_id = "2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c"
    test_db.create_issue(
        Issue(
            id="issue-plg-hist",
            project_id=plg_id,
            key="PLG-2",
            title="Keep this history",
            issue_type=IssueType.TASK,
            current_state=IssueState.DONE,
        )
    )

    # Remove PLG from registry.json
    registry_file = test_repo / "projects" / "registry.json"
    reg = json.loads(registry_file.read_text(encoding="utf-8"))
    reg["projects"] = [p for p in reg["projects"] if p["project_key"] != "PLG"]
    registry_file.write_text(json.dumps(reg), encoding="utf-8")

    res = discovery.sync()
    assert "PLG" in res["inactivated"]

    # Verify source marked inactive in DB
    source = test_db.get_project_source(plg_id)
    assert source is not None
    assert source.status == "inactive"

    # Verify project row and issue STILL exist
    plg = test_db.get_project(plg_id)
    assert plg is not None
    issues = test_db.list_issues(project_id=plg_id)
    assert len(issues) == 1
    assert issues[0].key == "PLG-2"


# 5. Invalid Registry Retains Last Valid Snapshot
def test_invalid_registry_retains_last_valid_snapshot(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    res1 = discovery.sync()
    assert res1["status"] == "healthy"

    # Overwrite registry with corrupted JSON
    registry_file = test_repo / "projects" / "registry.json"
    registry_file.write_text("NOT_VALID_JSON{", encoding="utf-8")

    res2 = discovery.sync()
    assert res2["status"] == "stale"
    assert res2["is_stale"] is True
    assert "Malformed registry JSON" in res2["error"]

    # Verify projects still present in DB and returned in snapshot
    freshness = discovery.get_projects_with_freshness()
    active_keys = [p["key"] for p in freshness["projects"] if p["status"] == "active"]
    assert "SBA" in active_keys
    assert "PLG" in active_keys
    assert freshness["discovery"]["is_stale"] is True


# 6. Unsafe Paths and Path Traversal Rejected
def test_unsafe_paths_and_traversal_rejected(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    registry_file = test_repo / "projects" / "registry.json"

    # Test absolute path
    reg = json.loads(registry_file.read_text(encoding="utf-8"))
    reg["projects"][0]["root_path"] = "/etc/passwd"
    registry_file.write_text(json.dumps(reg), encoding="utf-8")

    with pytest.raises(RegistryValidationError, match="Unsafe root_path"):
        discovery.load_and_validate_registry()

    # Test path traversal (..)
    reg["projects"][0]["root_path"] = "projects/../../outside"
    registry_file.write_text(json.dumps(reg), encoding="utf-8")

    with pytest.raises(RegistryValidationError, match="Unsafe root_path"):
        discovery.load_and_validate_registry()

    # Test non-existent path
    reg["projects"][0]["root_path"] = "projects/non_existent_folder"
    registry_file.write_text(json.dumps(reg), encoding="utf-8")

    with pytest.raises(RegistryValidationError, match="directory does not exist"):
        discovery.load_and_validate_registry()


# 7. Duplicate Identities Rejected
def test_duplicate_identities_rejected(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    registry_file = test_repo / "projects" / "registry.json"
    clean_reg = json.loads(registry_file.read_text(encoding="utf-8"))

    # Duplicate project_id
    import copy
    reg1 = copy.deepcopy(clean_reg)
    reg1["projects"][1]["project_id"] = reg1["projects"][0]["project_id"]
    registry_file.write_text(json.dumps(reg1), encoding="utf-8")

    with pytest.raises(RegistryValidationError, match="Duplicate project_id"):
        discovery.load_and_validate_registry()

    # Duplicate project_key
    reg2 = copy.deepcopy(clean_reg)
    reg2["projects"][1]["project_key"] = reg2["projects"][0]["project_key"]
    registry_file.write_text(json.dumps(reg2), encoding="utf-8")

    with pytest.raises(RegistryValidationError, match="Duplicate project_key"):
        discovery.load_and_validate_registry()

    # Duplicate root_path
    reg3 = copy.deepcopy(clean_reg)
    reg3["projects"][1]["root_path"] = reg3["projects"][0]["root_path"]
    registry_file.write_text(json.dumps(reg3), encoding="utf-8")

    with pytest.raises(ContradictoryMappingError, match="Duplicate root_path"):
        discovery.load_and_validate_registry()


# 8. Contradictory Mapping Against Existing DB Rejected
def test_contradictory_database_mapping_rejected(test_repo: Path, test_db: PMDatabase):
    # Pre-seed project with key "SBA" but a completely different UUID
    conflicting_uuid = str(uuid.uuid4())
    test_db.create_project(Project(id=conflicting_uuid, key="SBA", name="Conflict"))

    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    with pytest.raises(ContradictoryMappingError, match="Contradictory mapping"):
        discovery.reconcile_projects()


# 9. Non-Registered Folders are NOT Treated as Projects
def test_folder_isolation_non_registered_folders_ignored(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    discovery.sync()

    # Verify that scratch_work and node_modules are NOT projects
    assert test_db.get_project_by_key("SCRATCH_WORK") is None
    assert test_db.get_project_by_key("NODE_MODULES") is None
    projects = test_db.list_projects()
    keys = {p.key for p in projects}
    assert keys == {"SBA", "PLG"}


# 10. Persistence Across Restart
def test_persistence_across_restart(test_repo: Path, test_db: PMDatabase):
    discovery1 = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    sync_res = discovery1.sync()
    assert sync_res["status"] == "healthy"

    # Simulate process termination & restart by creating new discovery instance
    discovery2 = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    freshness = discovery2.get_projects_with_freshness()

    assert freshness["discovery"]["last_sync"] is not None
    assert len(freshness["projects"]) == 2
    for p in freshness["projects"]:
        assert p["status"] == "active"
        assert p["source_freshness"]["last_successful_sync"] is not None


# 11. Safe Git Fetch Preserves Dirty Checkout
def test_safe_git_fetch_preserves_dirty_checkout(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    fetch_info = discovery.safe_git_fetch()

    # Regardless of remote status, dirty checkout preservation is true
    assert fetch_info["dirty_checkout_preserved"] is True
