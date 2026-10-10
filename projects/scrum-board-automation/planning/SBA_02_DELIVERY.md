# SBA-02 delivery candidate: Automatic repository project discovery

Under CEO owner authorization, the Antigravity development team implemented automatic project discovery and reconciliation for configured repository projects per [BOARD_CONTRACT_V1.md](BOARD_CONTRACT_V1.md) Section 2 and [SBA_01_DECISIONS.md](SBA_01_DECISIONS.md).

## 1. Implemented behavior

- **Authoritative registry (`projects/registry.json`):** Defines repository identity (`mphoMas/Acinonyx`, branch `feat/scrum-board-automation`) and registers `SBA` (`c2e7bb0e-6f81-5c31-9a7c-501b802711ff`) and `PLG` (`2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c`) with repository-relative paths. Arbitrary folders are not treated as projects.
- **Engine reconciliation (`mas/pm/discovery.py`):**
  - Validates schema version, UUID format, alphanumeric project key (2–10 chars), repository metadata, and directory paths.
  - Reconciles discovered projects against SQLite database idempotently without duplicating records or destroying task, evidence, or review history.
  - Updates project names and descriptions while preserving stable project UUIDs.
  - Rejects unsafe paths (absolute paths, `..` directory traversal, repository escapes) and non-existent folders.
  - Rejects duplicate identities, duplicate root paths, and contradictory key/UUID database reassignments.
  - Marks removed sources `inactive` while retaining historic tasks and state.
  - Preserves dirty checkouts: `safe_git_fetch` verifies `git status --porcelain` and runs non-destructive `git fetch origin <branch>`, never resetting the working tree or index.
  - Retains last valid snapshot and marks `is_stale: true` with error telemetry if the registry is invalid or network fetch fails.
  - Persists synchronization metadata across process restarts (`get_projects_with_freshness` falls back to DB persisted state).
  - Background daemon resyncs periodically (every 30s) or on registry mtime change.
- **Persistence (`mas/pm/db.py`, `mas/pm/models.py`):** Added `pm_project_sources` table and `ProjectSource` model, plus `pm_task_mappings` table and `TaskMapping` model.
- **Public API (`mas/dashboard/server.py`):** Exposed `GET /api/pm/v1/projects` alongside legacy routes.

## 2. API contract for Codex frontend consumption

Endpoint: `GET /api/pm/v1/projects`
Authentication: Same-origin cookie or Bearer token (per Section 6).

Sample response:
```json
{
  "projects": [
    {
      "id": "c2e7bb0e-6f81-5c31-9a7c-501b802711ff",
      "key": "SBA",
      "name": "Scrum Board Automation",
      "description": "Make the MAS board an automatically maintained view of repository projects, approved plans and authenticated agent execution.",
      "token_budget": 5000000,
      "tokens_consumed": 0,
      "root_path": "projects/scrum-board-automation",
      "planning_path": "projects/scrum-board-automation/planning",
      "status": "active",
      "source_freshness": {
        "repository_id": "mphoMas/Acinonyx",
        "configured_branch": "feat/scrum-board-automation",
        "source_revision": "cd459515e2561279a30d5b0b0f352cd6ac86bcf9",
        "last_successful_sync": "2026-10-10T20:19:55.406075+00:00",
        "last_error": null,
        "is_stale": false,
        "status": "active"
      }
    },
    {
      "id": "2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c",
      "key": "PLG",
      "name": "Platinum Lodge — multi-property hotel management",
      "description": "Planning initiation: production reservations/check-in, billing/payments and housekeeping. Codex frontend/design/art; Antigravity development team backend. No active execution.",
      "token_budget": 0,
      "tokens_consumed": 0,
      "root_path": "projects/platinum-lodge",
      "planning_path": "projects/platinum-lodge/planning",
      "status": "active",
      "source_freshness": {
        "repository_id": "mphoMas/Acinonyx",
        "configured_branch": "feat/scrum-board-automation",
        "source_revision": "cd459515e2561279a30d5b0b0f352cd6ac86bcf9",
        "last_successful_sync": "2026-10-10T20:19:55.410357+00:00",
        "last_error": null,
        "is_stale": false,
        "status": "active"
      }
    }
  ],
  "discovery": {
    "last_sync": "2026-10-10T20:19:55Z",
    "source_revision": "cd459515e2561279a30d5b0b0f352cd6ac86bcf9",
    "is_stale": false,
    "error": null
  }
}
```

### What Codex frontend must consume:
1. **Project Selection:** Bind project queries by `project.id` (stable UUID) rather than project name.
2. **Freshness & Stale Indicator:** Display top-level `discovery.is_stale` or project `source_freshness.is_stale` with an explicit badge/banner when true, showing `last_sync` time and short git revision.
3. **Inactive Source Presentation:** Projects with `status: "inactive"` must be visibly marked as archived/inactive without hiding existing tasks or history.
4. **Resilience to Sync Errors:** If `discovery.error` is present, display a non-blocking warning notification; do not crash the board drawer.

## 3. Test verification evidence

### SBA-02 Discovery test suite (`tests/test_sba_02_discovery.py`)
Command:
```bash
python3 -m pytest tests/test_sba_02_discovery.py -v
```
Actual output:
```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0 -- /home/acinonyx/anaconda3/bin/python3
cachedir: .pytest_cache
rootdir: /home/acinonyx/Desktop/MAS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 11 items

tests/test_sba_02_discovery.py::test_initial_discovery_and_repeated_sync PASSED [  9%]
tests/test_sba_02_discovery.py::test_reconciliation_preserves_existing_records_and_history PASSED [ 18%]
tests/test_sba_02_discovery.py::test_rename_preserves_stable_project_id PASSED [ 27%]
tests/test_sba_02_discovery.py::test_missing_registration_marks_source_inactive_without_deleting_history PASSED [ 36%]
tests/test_sba_02_discovery.py::test_invalid_registry_retains_last_valid_snapshot PASSED [ 45%]
tests/test_sba_02_discovery.py::test_unsafe_paths_and_traversal_rejected PASSED [ 54%]
tests/test_sba_02_discovery.py::test_duplicate_identities_rejected PASSED [ 63%]
tests/test_sba_02_discovery.py::test_contradictory_database_mapping_rejected PASSED [ 72%]
tests/test_sba_02_discovery.py::test_folder_isolation_non_registered_folders_ignored PASSED [ 81%]
tests/test_sba_02_discovery.py::test_persistence_across_restart PASSED   [ 90%]
tests/test_sba_02_discovery.py::test_safe_git_fetch_preserves_dirty_checkout PASSED [100%]

============================== 11 passed in 0.27s ==============================
```

### Core regression suite
Command:
```bash
python3 -m pytest tests/test_dashboard.py tests/test_pm_engine.py tests/test_pm_remediation.py tests/test_pm_07_dependencies_and_authorization.py
```
Actual output:
```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/acinonyx/Desktop/MAS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 34 items

tests/test_dashboard.py ............                                     [ 35%]
tests/test_pm_engine.py ........                                         [ 58%]
tests/test_pm_remediation.py .........                                   [ 85%]
tests/test_pm_07_dependencies_and_authorization.py .....                 [100%]

============================== 34 passed in 2.18s ==============================
```

### Live server query
Command:
```bash
curl -s http://127.0.0.1:8080/api/pm/v1/projects | python3 -m json.tool
```
Returns 200 OK with `discovery.source_revision` matching `cd459515e2561279a30d5b0b0f352cd6ac86bcf9` and healthy registered status for SBA and PLG.

## 4. Deployment and setup requirements

- Working tree requires `projects/registry.json` present.
- Git binary accessible in PATH for revision discovery and safe fetch.
- Server requires local write access to SQLite database (`mas_pm.db`).
- GitHub credentials stay strictly server-side if remote fetch is enabled.

## 5. Remaining blockers and limitations

- **Independent technical review:** Remains PENDING appointment. Antigravity does not declare independent approval; counterparty review by Codex is requested.
- **Runtime issue state:** SBA-02 (local SBA-2) remains in `BACKLOG` in `mas_pm.db`. Runtime tickets cannot advance to `IN_PROGRESS` or `DONE` without authorized token appetite budget and independent judge evaluation.
- **Downstream dependencies:** SBA-03 (plan ingestion) and SBA-04 (agent progress adapter) remain gated on formal review acceptance.
