# SBA-03 Delivery: Publish Conversation-Derived Plans into MAS-PM

**Delivery Date:** 2026-10-11  
**Target Branch:** `feat/scrum-board-automation`  
**Delivery Scope:** SBA-03 — Authenticated planning-publication endpoint and architect integration.  
**Implementation Owner:** Antigravity  
**Reviewer:** Codex  
**Status:** **SUBMITTED FOR REVIEW** (Not self-certified as DONE per delivery ownership agreement).

---

## 1. Executive Summary

This delivery implements the complete planning-publication contract specified in `BOARD_CONTRACT_V1.md` section 3 and the CEO authorization directive.

Codex, acting as system architect and Scrum master, can now convert CEO conversations into a structured plan and publish it directly into the MAS-PM board without requiring import scripts, manual SQL queries, or manual ticket creation.

The implementation strictly maintains:
1. **Deterministic Backend:** No LLM or free-form natural language interpretation inside backend endpoints.
2. **Atomic Consistency:** Plan records, task creation/updates, stable identity mappings, and dependency updates are committed in a single transaction or rolled back completely on any error.
3. **Active Work Inviolability:** In-flight tasks (`IN_PROGRESS`, `STAGED`, `VERIFICATION`, `JUDICIAL_REVIEW`, `DONE`) preserve their runtime state, assigned principal, consumed tokens, and attached evidence across revisions.
4. **Reconciliation Transparency:** Explicit tracking for modified acceptance criteria or path scopes on active tasks.
5. **Security & Multitenancy:** Tenant-qualified authorization, CSRF/token validation, payload size bounding (1 MiB), and path traversal protection.

---

## 2. Implemented Architecture & Components

### 2.1 Backend Models & Schema Migration ([`mas/pm/models.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/models.py), [`mas/pm/db.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/db.py))
- **`PlanTaskDefinition`:** Typed schema representing planned tasks, stable identities (`task_id`, `planning_reference`), hierarchy (`parent_task_id`), dependencies, path whitelists, acceptance criteria, proposed delivery owner, reviewer requirements, and proposed budget tokens.
- **`PlanPublicationRequest` & `PlanPublicationResponse`:** Pydantic v2 models validating incoming publication requests and structured response envelopes.
- **`pm_plans` Table:** Stores immutable revision records (`id`, `plan_id`, `revision`, `project_id`, `tenant_id`, `source_commit`, `scope_reference`, `published_by`, `published_at`, `payload_hash`, `raw_payload`).
- **`pm_idempotency_keys` Table:** Scoped idempotency storage with canonical SHA-256 request hashing and cached response payloads.
- **`pm_task_mappings` Table:** Maps stable planning identities (`planning_reference`, `task_id`) to internal UUIDs (`local_issue_id`) and deployment keys (`local_issue_key`).
- **`pm_issues` Planning Columns:** Columns `task_id`, `planning_reference`, `acceptance_criteria`, `proposed_delivery_owner`, `reviewer_requirement`, and `proposed_budget_tokens` added with non-destructive migrations.

### 2.2 Planning Publication Engine ([`mas/pm/plans.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/plans.py))
- **`PlanPublisherService`:**
  - Enforces `Idempotency-Key` replay (identical hash returns original receipt; mismatched hash raises `409 Conflict`).
  - Optimistic revision concurrency checking via `expected_previous_revision`.
  - Comprehensive pre-validation of complete graph:
    - Path safety validation (rejects `..`, absolute paths, null bytes).
    - Cyclic dependency detection using Kahn's algorithm / DFS.
    - Hierarchy cycle detection.
    - Duplicate planning references or task IDs within payload.
    - Contradictory database mappings (preventing reuse of IDs for disparate tasks).
  - Preserves runtime state for existing tasks.
  - Inserts new tasks directly into `IssueState.BACKLOG`.
  - Computes `changes_requiring_reconciliation` for active tasks whose scope or acceptance changed.
  - Atomic transaction wrapping all tables.

### 2.3 HTTP & Server Endpoints ([`mas/dashboard/server.py`](file:///home/acinonyx/Desktop/MAS/mas/dashboard/server.py))
- `POST /api/pm/v1/projects/{project_id_or_key}/plans`: Authenticated plan publication with 1 MiB payload limit and JSON error envelopes.
- `GET /api/pm/v1/projects/{project_id_or_key}/plans`: Retrieves plan revision history.
- `GET /api/pm/v1/projects/{project_id_or_key}/board`: Returns issues mapped to columns, with proposed delivery owners formatted for frontend display.

### 2.4 Architect Integration Tooling
1. **Python SDK Client ([`mas/pm/client.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/client.py)):**
   `PlanPublisherClient` for programmatic publishing with automatic idempotency and exception mapping.
2. **CLI Utility ([`mas/pm/publisher_cli.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/publisher_cli.py)):**
   Command-line tool supporting file paths (`--plan-file`) or STDIN piping.
3. **Agent MCP Tool ([`mas/pm/tools.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/tools.py)):**
   `pm_publish_plan` registered in MAS-PM tool suite for Codex agent execution.
4. **Architect Guide ([`projects/scrum-board-automation/planning/ARCHITECT_PLANNING_GUIDE.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ARCHITECT_PLANNING_GUIDE.md)):**
   Comprehensive usage guide for Codex.

---

## 3. Test Coverage & Verification Results

### 3.1 SBA-03 Dedicated Test Suite (`tests/test_sba_03_plan_publication.py`)
14 tests covering all failure and success scenarios specified in the contract:
- `test_first_publication_and_identical_retry`: Verified first publication allocates keys (`SBA-1`, `SBA-2`) and identical retry returns cached response without duplicating tickets.
- `test_same_idempotency_key_with_different_content_conflict`: Verified HTTP 409 conflict when payload differs under the same key.
- `test_stale_revision_and_optimistic_concurrency`: Verified HTTP 409 when `expected_previous_revision` does not match latest revision.
- `test_duplicate_identities_within_plan_rejected`: Verified rejection of duplicate `task_id` or `planning_reference`.
- `test_contradictory_database_mappings_rejected`: Verified rejection when trying to remap an existing reference to a different task.
- `test_invalid_hierarchy_and_dependency_cycles_rejected`: Verified cycle detection for dependencies and parent-child loops.
- `test_unsafe_path_scopes_rejected`: Verified rejection of `../`, `/etc/passwd`, and unsafe wildcards.
- `test_active_work_preservation_and_reconciliation_tracking`: Verified active tasks (`IN_PROGRESS`) retain state, assignee, spent tokens (23,500), reflexion attempts, and evidence links; changes to criteria are returned in reconciliation items.
- `test_omitted_plan_items_retain_runtime_history`: Verified omitted tasks are not deleted and keep state (`DONE`).
- `test_failure_injection_atomic_rollback`: Injected failures at each transaction stage; verified 100% clean rollback.
- `test_persistence_across_restart`: Verified full persistence of plans, issues, and mappings across database reload.
- `test_http_plan_publication_and_board_visibility`: Verified live HTTP publication into server and asserted that tickets appear in the `BACKLOG` column of the board endpoint (`/api/pm/board/PLIVE`).
- `test_http_unauthenticated_and_invalid_token_denial`: Verified 401 unauthenticated and invalid token rejections.
- `test_publisher_cli_execution`: Verified CLI execution publishing plan from file via subprocess.

**Result:** **14 passed in 2.95s**, zero failures.

### 3.2 Regression Suites
- SBA-02 Discovery Suite (`tests/test_sba_02_discovery.py`): **22 passed**.
- SBA-05 Session Integration Suite (`tests/test_sba_05_session_integration.py`): **23 passed**.
- Combined regression: **45 passed in 16.65s**, zero failures.

### 3.3 Static Analysis & Lint
- `python3 -m ruff check mas/pm/ mas/dashboard/ tests/test_sba_03_plan_publication.py`: **Clean, zero warnings/errors**.

---

## 4. Setup, Migration & Operational Notes

- **Database Migrations:** Schema migrations in [`mas/pm/db.py`](file:///home/acinonyx/Desktop/MAS/mas/pm/db.py) are non-destructive and apply automatically on `PMDatabase` initialization:
  - Creates `pm_plans` and `pm_idempotency_keys` tables and indices if not present.
  - Adds planning columns to existing `pm_issues` tables via `PRAGMA table_info` checks.
- **Tenant Isolation:** Plan records and idempotency keys are strictly bound to `tenant_id`.
- **Payload Bounding:** HTTP request body is capped at 1 MiB; larger payloads receive HTTP 413.

---

## 5. Remaining Limitations & Handoff Conditions

1. **Frontend Styling & Column Dragging:** Codex owns frontend UI. Backlog cards created via plans appear with title, key, priority, and `Delivery/integration owner: <Owner>` in their description for immediate transparency.
2. **SBA-04 Dependency:** Antigravity agent execution events (work started/progress/evidence) remain out of scope for SBA-03 and are kept in SBA-04.
3. **No Self-Certification:** Per team delivery ownership agreement, Antigravity does not certify SBA-03 as DONE. We submit this delivery to Codex for independent review.
