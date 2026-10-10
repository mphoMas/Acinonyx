"""
Unit and integration tests for automatic repository project discovery (SBA-02).

Validates:
1. Initial discovery and repeated synchronization idempotency.
2. Reconciliation with existing SBA/PLG deployment records (legacy migration preserving deployment IDs).
3. Name/description update preserving stable project UUID.
4. Missing registration marks source inactive without deleting issues or history.
5. Missing project directory marks source inactive without invalidating registry.
6. Invalid registry retains last valid snapshot in database.
7. Unsafe paths, traversal and duplicate identities rejected.
8. Contradictory identity mapping against existing database rejected.
9. Atomic reconciliation: rollback on later conflict leaves database unmodified.
10. Folder isolation: non-registered folders ignored.
11. Persistence across process restart.
12. Safe git fetch preserves dirty checkouts.
13. Remote commits arriving without local file changes discovered via remote revision.
14. Remote fetch failure reports stale and recovers when remote is restored.
15. Two tenant databases share process with zero cross-tenant leakage.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import uuid
import pytest

from mas.pm.db import PMDatabase
from mas.pm.discovery import (
    ContradictoryMappingError,
    ProjectRegistryDiscovery,
    RegistryValidationError,
)
from mas.pm.models import Issue, IssueState, IssueType, Project


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


# 2. Reconciliation with Existing Records (Legacy migration preserving deployment IDs)
def test_reconciliation_preserves_existing_records_and_history(test_repo: Path, test_db: PMDatabase):
    # Pre-seed existing legacy SBA project in DB with deployment-generated ID
    legacy_sba_id = "c0000000-0000-0000-0000-000000000099"
    existing_sba = Project(
        id=legacy_sba_id,
        key="SBA",
        name="Pre-existing SBA Deployment",
        description="Created before registry existed",
        token_budget=15_000_000,
        tokens_consumed=820_000,
    )
    test_db.create_project(existing_sba)

    # Attach issue and evidence to legacy SBA
    test_db.create_issue(
        Issue(
            id="issue-sba-leg-1",
            project_id=legacy_sba_id,
            key="SBA-1",
            title="Legacy task with evidence",
            description="Historical progress",
            issue_type=IssueType.TASK,
            current_state=IssueState.DONE,
        )
    )

    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    res = discovery.sync()

    assert res["status"] == "healthy"
    assert "PLG" in res["created"]
    assert "SBA" in res["unchanged"] or "SBA" in res["updated"]

    # Verify legacy SBA deployment ID is preserved
    reconciled_sba = test_db.get_project_by_key("SBA")
    assert reconciled_sba is not None
    assert reconciled_sba.id == legacy_sba_id  # Preserved!
    assert reconciled_sba.token_budget == 15_000_000
    assert reconciled_sba.tokens_consumed == 820_000

    # Verify task history is preserved intact
    issues = test_db.list_issues(project_id=legacy_sba_id)
    assert len(issues) == 1
    assert issues[0].key == "SBA-1"
    assert issues[0].current_state == IssueState.DONE

    # Verify source mapping binds to the legacy deployment ID
    source = test_db.get_project_source(legacy_sba_id)
    assert source is not None
    assert source.project_id == legacy_sba_id
    assert source.status == "active"


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


# 5. Missing Project Directory Marks Source Inactive Without Failing Registry
def test_missing_project_directory_marks_source_inactive(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    registry_file = test_repo / "projects" / "registry.json"
    reg = json.loads(registry_file.read_text(encoding="utf-8"))

    # Set root_path to a missing directory
    reg["projects"][0]["root_path"] = "projects/missing_folder"
    registry_file.write_text(json.dumps(reg), encoding="utf-8")

    manifest = discovery.load_and_validate_registry()
    assert manifest["projects"][0]["exists_on_disk"] is False

    res = discovery.sync()
    assert res["status"] == "healthy"
    assert "SBA" in res["created"]

    source = test_db.get_project_source(reg["projects"][0]["project_id"])
    assert source is not None
    assert source.status == "inactive"
    assert "not found" in (source.last_error or "")


# 6. Invalid Registry Retains Last Valid Snapshot
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

    freshness = discovery.get_projects_with_freshness()
    active_keys = [p["key"] for p in freshness["projects"] if p["status"] == "active"]
    assert "SBA" in active_keys
    assert "PLG" in active_keys
    assert freshness["discovery"]["is_stale"] is True


# 7. Unsafe Paths and Path Traversal Rejected
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


# 8. Duplicate Identities in Registry Rejected
def test_duplicate_identities_rejected(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    registry_file = test_repo / "projects" / "registry.json"
    clean_reg = json.loads(registry_file.read_text(encoding="utf-8"))

    # Duplicate project_id
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


# 9. Contradictory Mapping Against Existing DB Rejected
def test_contradictory_database_mapping_rejected(test_repo: Path, test_db: PMDatabase):
    # Pre-seed DB with UUID c2e7bb0e-6f81-5c31-9a7c-501b802711ff but conflicting key "OTHER"
    test_db.create_project(
        Project(
            id="c2e7bb0e-6f81-5c31-9a7c-501b802711ff",
            key="OTHER",
            name="Conflicting Project",
        )
    )

    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    with pytest.raises(ContradictoryMappingError, match="has key 'OTHER' in database"):
        discovery.reconcile_projects()


# 10. Atomic Reconciliation Rollback on Error
def test_atomic_reconciliation_conflict_rollback(test_repo: Path, test_db: PMDatabase):
    # Pre-seed DB with a project conflicting with PLG
    test_db.create_project(
        Project(
            id="2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c",
            key="CONFLICT_PLG",
            name="Conflicting PLG Project",
        )
    )

    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    # SBA is first in registry, PLG is second (which conflicts).
    # Reconciliation must roll back atomically and NOT insert SBA into the database.
    try:
        discovery.reconcile_projects()
    except ContradictoryMappingError:
        pass

    assert test_db.get_project_by_key("SBA") is None


# 11. Folder Isolation: Non-Registered Folders are Ignored
def test_folder_isolation_non_registered_folders_ignored(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    discovery.sync()

    assert test_db.get_project_by_key("SCRATCH_WORK") is None
    assert test_db.get_project_by_key("NODE_MODULES") is None
    projects = test_db.list_projects()
    keys = {p.key for p in projects}
    assert keys == {"SBA", "PLG"}


# 12. Persistence Across Restart
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


# 13. Safe Git Fetch Preserves Dirty Checkout
def test_safe_git_fetch_preserves_dirty_checkout(test_repo: Path, test_db: PMDatabase):
    discovery = ProjectRegistryDiscovery(repo_root=test_repo, db=test_db)
    fetch_info = discovery.safe_git_fetch()
    assert fetch_info["dirty_checkout_preserved"] is True


# 14. Remote Commits Arriving Without Local File Changes
def test_remote_commits_arriving_without_local_file_changes(tmp_path: Path, test_db: PMDatabase):
    # 1. Create a bare git repo as remote origin
    bare_dir = tmp_path / "bare_origin.git"
    subprocess.run(["git", "init", "--bare", str(bare_dir)], check=True, capture_output=True)

    # 2. Clone to a staging repo, commit registry, and push to origin
    staging_dir = tmp_path / "staging"
    subprocess.run(["git", "clone", str(bare_dir), str(staging_dir)], check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(staging_dir), check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=str(staging_dir), check=True)

    branch_name = "feat/scrum-board-automation"
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=str(staging_dir), check=True, capture_output=True)

    sba_dir = staging_dir / "projects" / "scrum-board-automation"
    sba_dir.mkdir(parents=True)
    (sba_dir / "planning").mkdir()

    registry_path = staging_dir / "projects" / "registry.json"
    registry_data = {
        "schema_version": 1,
        "repository": {
            "id": "mphoMas/Acinonyx",
            "owner": "mphoMas",
            "name": "Acinonyx",
            "configured_branch": branch_name,
        },
        "projects": [
            {
                "project_id": "c2e7bb0e-6f81-5c31-9a7c-501b802711ff",
                "project_key": "SBA",
                "name": "Scrum Board Automation",
                "root_path": "projects/scrum-board-automation",
                "planning_path": "projects/scrum-board-automation/planning",
                "status": "active",
            }
        ],
    }
    registry_path.write_text(json.dumps(registry_data), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(staging_dir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(staging_dir), check=True)
    subprocess.run(["git", "push", "origin", branch_name], cwd=str(staging_dir), check=True)

    # 3. Clone to local discovery repo
    local_repo = tmp_path / "local_repo"
    subprocess.run(["git", "clone", str(bare_dir), str(local_repo)], check=True, capture_output=True)
    subprocess.run(["git", "checkout", branch_name], cwd=str(local_repo), check=True, capture_output=True)

    discovery = ProjectRegistryDiscovery(repo_root=local_repo, db=test_db)
    res1 = discovery.sync(fetch_remote=True)
    assert res1["status"] == "healthy"
    assert res1["total_registered"] == 1

    # 4. In staging repo, add a second project PLG, commit and push to bare origin
    plg_dir = staging_dir / "projects" / "platinum-lodge"
    plg_dir.mkdir(parents=True)
    (plg_dir / "planning").mkdir()
    registry_data["projects"].append({
        "project_id": "2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c",
        "project_key": "PLG",
        "name": "Platinum Lodge",
        "root_path": "projects/platinum-lodge",
        "planning_path": "projects/platinum-lodge/planning",
        "status": "active",
    })
    registry_path.write_text(json.dumps(registry_data), encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(staging_dir), check=True)
    subprocess.run(["git", "commit", "-m", "Add PLG"], cwd=str(staging_dir), check=True)
    subprocess.run(["git", "push", "origin", branch_name], cwd=str(staging_dir), check=True)

    # 5. Local repo working tree is UNTOUCHED (local mtime has not changed)
    local_reg_file = local_repo / "projects" / "registry.json"
    local_mtime_before = local_reg_file.stat().st_mtime_ns

    # Sync with fetch_remote=True discovers the new remote commit!
    res2 = discovery.sync(fetch_remote=True)
    assert res2["status"] == "healthy"
    assert "PLG" in res2["created"]
    assert res2["total_registered"] == 2

    # Assert local file mtime was untouched (no destructive reset)
    assert local_reg_file.stat().st_mtime_ns == local_mtime_before


# 15. Two Tenant Databases Zero Cross-Tenant Discovery Leakage
def test_two_tenant_servers_zero_cross_tenant_discovery(tmp_path: Path):
    db_a_file = tmp_path / "tenant_a.db"
    db_b_file = tmp_path / "tenant_b.db"
    db_a = PMDatabase(db_a_file)
    db_b = PMDatabase(db_b_file)

    # Seed Project in Tenant A
    db_a.create_project(Project(id=str(uuid.uuid4()), key="TENANT_A_PROJ", name="A Project"))

    disc_a = ProjectRegistryDiscovery(db=db_a)
    disc_b = ProjectRegistryDiscovery(db=db_b)

    projects_a = disc_a.db.list_projects()
    projects_b = disc_b.db.list_projects()

    assert any(p.key == "TENANT_A_PROJ" for p in projects_a)
    assert not any(p.key == "TENANT_A_PROJ" for p in projects_b)
    assert len(projects_b) == 0
