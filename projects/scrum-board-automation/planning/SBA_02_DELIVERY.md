# SBA-02 delivery candidate: Automatic repository project discovery (Reworked)

Under CEO owner authorization, the Antigravity development team implemented automatic project discovery and reconciliation for configured repository projects per [BOARD_CONTRACT_V1.md](BOARD_CONTRACT_V1.md) Section 2, [SBA_01_DECISIONS.md](SBA_01_DECISIONS.md), and [SBA_02_05_BACKEND_REVIEW.md](SBA_02_05_BACKEND_REVIEW.md).

## 1. Implemented behavior & review remediations

- **Authoritative registry (`projects/registry.json`):**
  - Defines repository identity (`mphoMas/Acinonyx`, branch `feat/scrum-board-automation`) and registers `SBA` (`c2e7bb0e-6f81-5c31-9a7c-501b802711ff`) and `PLG` (`2a2e70fc-0d6e-4d52-84ee-6818f2c61a7c`) with repository-relative paths. Arbitrary folders are not treated as projects.
- **Engine reconciliation (`mas/pm/discovery.py`):**
  - **Remote revision synchronization:** Reads the configured remote revision/registry (`git show <revision>:projects/registry.json`) using an isolated reader without modifying local worktrees or overwriting dirty checkouts.
  - **Periodic sync with remote fetch:** Periodic synchronization (`fetch_remote=True` default) fetches remote commits safely (`git fetch origin <branch>`), inspecting incoming remote commits even when working tree mtimes are unchanged.
  - **Stale reporting on fetch failure:** When remote fetch fails (e.g. network partition or invalid remote), the discovery engine retains the last valid snapshot, marks `is_stale = True`, records the error in freshness telemetry, and reports status `stale` (never masking failure as healthy).
  - **Existing legacy project migration:** Implemented reviewed stable-ID binding migration. Discovered project keys matching pre-existing database records retain their original deployment-generated UUIDs (`target_id = existing_by_key.id`), binding source tracking without destroying issues, evidence links, or review verdicts.
  - **Atomic transaction reconciliation:** Pre-validates all registry entries and candidate paths in Phase 1 before applying database mutations in Phase 2 within a single atomic SQLite transaction (`with conn:`). Later conflicts cause a clean rollback rather than partial state.
  - **Missing paths recorded as inactive:** Missing directories on disk or in git revisions do not invalidate the entire registry; rather, individual project sources are marked `inactive` with `exists_on_disk = False`.
  - **Per-tenant database binding:** Removed process-global database caching in `get_project_discovery()`. Discovery binds explicitly to the current tenant execution context (`current_binding().database`) or server-supplied instance, preventing cross-tenant data leakage.
- **Persistence (`mas/pm/db.py`, `mas/pm/models.py`):**
  - `pm_project_sources` table and `ProjectSource` model track source binding, repo identity, configured branch, commit revision, and status.
  - `pm_task_mappings` table and `TaskMapping` model preserve external/planning mapping.
- **Public API (`mas/dashboard/server.py`):** Exposed `GET /api/pm/v1/projects` alongside legacy routes with tenant-scoped isolation.

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
        "source_revision": "5ca8094180c1ced1ebe7990353f8023bb3254426",
        "last_successful_sync": "2026-10-10T21:40:58.246414+00:00",
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
        "source_revision": "5ca8094180c1ced1ebe7990353f8023bb3254426",
        "last_successful_sync": "2026-10-10T21:40:58.246414+00:00",
        "last_error": null,
        "is_stale": false,
        "status": "active"
      }
    }
  ]
}
```

## 3. Regression verification

Test suite: `tests/test_sba_02_discovery.py`  
Command: `python3 -m pytest tests/test_sba_02_discovery.py -v`  
Result: 15 passed in 0.54s.

Specific regressions verified:
1. `test_remote_commit_sync_without_local_file_change`: Verifies sync fetches and reconciles bare-origin commits without local working-tree file modifications.
2. `test_dirty_checkout_preserved_during_sync`: Verifies uncommitted files in working tree remain intact across fetch and sync.
3. `test_fetch_failure_reports_stale_and_preserves_snapshot`: Verifies network/fetch failures report `status = "stale"`, `is_stale = True`, and preserve the last valid snapshot.
4. `test_legacy_existing_project_migration_preserves_identity_and_issues`: Verifies pre-existing projects retain deployment UUIDs and existing issues/evidence across discovery.
5. `test_atomic_reconciliation_rolls_back_on_later_conflict`: Verifies atomic transaction rolls back cleanly when an entry in the registry conflicts.
6. `test_missing_source_path_marks_inactive_not_invalid`: Verifies missing folders are marked `inactive` without invalidating the whole registry.
7. `test_tenant_isolation_two_servers_no_cross_leakage`: Verifies two tenant servers sharing a process do not leak discovered project state.
