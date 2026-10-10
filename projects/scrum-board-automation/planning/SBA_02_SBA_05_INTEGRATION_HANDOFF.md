# Development handoff: SBA-02 Project Discovery & SBA-05 Session/CSRF Backend Delivery

- **MAS-PM task ID:** `SBA-02` (Repository project discovery) & `SBA-05` (Authenticated board session & CSRF backend contracts)
- **Outcome:**
  1. Fully functional, idempotent automatic project discovery and reconciliation engine (`mas/pm/discovery.py`) driven by authoritative `projects/registry.json`, persisting into SQLite tables `pm_project_sources` and `pm_task_mappings`, safely fetching without resetting dirty trees, and exposing `GET /api/pm/v1/projects` with freshness telemetry.
  2. Full backend implementation of the session, login/logout, CSRF protection, and server-resolved actor requirements specified in `SBA_05_DELIVERY.md`:
     - Opaque 256-bit cookie session manager (`mas/pm/session.py`) storing SHA-256 token hashes in SQLite `pm_sessions`.
     - `GET /api/pm/v1/session` returning `{principal, tenant_id, permitted_actions, csrf_token}` with `Cache-Control: no-store` (and 401 unauthenticated with `Cache-Control: no-store`).
     - `POST /api/pm/v1/session/login` setting `mas_session` cookie (`HttpOnly; SameSite=Lax; Max-Age=28800`).
     - `POST /api/pm/v1/session/logout` clearing cookie (`Max-Age=0`) and revoking database record.
     - Session-bound `csrf_token` cryptographically isolated from the login secret.
     - Strict no silent fallback: invalid Bearer token fails immediately with 401, never inspecting cookies.
     - CSRF validation across all PM mutation endpoints (`/api/pm/transition`, `/api/pm/verdicts`, `/api/pm/issues/create`, `/api/pm/sprints/create`, `/api/pm/sprints/state`, `/api/pm/issues/assign_sprint`).
     - Server-resolved actor enforcement: rejects client-supplied caller/reviewer impersonation with 403 Forbidden.
     - 30-minute idle inactivity timeout and 8-hour hard maximum TTL.
     - IAM revocation chaining: revoking an underlying IAM token revokes linked cookie sessions automatically.
     - Safe static `/portal/*` file serving with `X-Content-Type-Options: nosniff` and path traversal prevention.
- **Delivery owner:** Antigravity development team (backend APIs, engine, persistence, session manager, test suites)
- **Integration owner:** Codex (frontend/coordination) / Antigravity development team (backend integration)
- **Separate reviewer:** Codex / Independent Reviewer (Antigravity development team does not self-approve or self-certify DONE)
- **Baseline / branch / worktree:**
  - Branch: `feat/scrum-board-automation`
  - Base commit: `d22d089c`
  - Delivery commits:
    - [`8742c802`](https://github.com/mphoMas/Acinonyx/commit/8742c802): `feat(pm): implement automatic repository project discovery (SBA-02)`
    - [`c555b0ca`](https://github.com/mphoMas/Acinonyx/commit/c555b0ca): `feat(pm): incorporate SBA-05 session and CSRF backend contracts`
- **Allowed files:**
  - `projects/registry.json`
  - `mas/pm/models.py`
  - `mas/pm/db.py`
  - `mas/pm/discovery.py`
  - `mas/pm/session.py`
  - `mas/dashboard/server.py`
  - `tests/test_sba_02_discovery.py`
  - `tests/test_sba_05_session_integration.py`
  - `projects/scrum-board-automation/planning/SBA_02_DELIVERY.md`
  - `projects/scrum-board-automation/planning/SBA_05_DELIVERY.md`
  - `projects/scrum-board-automation/planning/SBA_02_SBA_05_INTEGRATION_HANDOFF.md`
- **Excluded scope:**
  - `portal/` files and frontend presentation logic (Codex-owned).
  - SBA-03 (plan ingestion) and SBA-04 (agent progress adapter).
  - Marking tickets `DONE` in PM DB prior to independent reviewer sign-off.
- **Dependencies:**
  - Agreed `BOARD_CONTRACT_V1.md` Section 2 & Section 6.
  - CEO owner approval of recorded architecture direction.
- **API/data contract:**
  - `GET /api/pm/v1/projects`: returns list of registered projects with stable UUIDs, status, and `source_freshness` block (branch, commit SHA, sync timestamp, `is_stale`, error).
  - `GET /api/pm/v1/session`: returns session metadata `{principal, tenant_id, permitted_actions, csrf_token}` with `Cache-Control: no-store`.
  - `POST /api/pm/v1/session/login`: accepts `{token, principal, tenant_id}`, returns 200 with `Set-Cookie: mas_session=...; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800`.
  - `POST /api/pm/v1/session/logout`: returns 200 with `Set-Cookie: mas_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`.
  - PM mutations: require `X-CSRF-Token` header when cookie-authenticated; missing or mismatched tokens return 403 Forbidden.
- **Acceptance checks & test execution evidence:**
  - **SBA-02 Discovery Test Suite:**
    ```bash
    python3 -m pytest tests/test_sba_02_discovery.py -v
    ```
    Result: 11 passed in 0.27s.
  - **SBA-05 Session Integration Test Suite:**
    ```bash
    python3 -m pytest tests/test_sba_05_session_integration.py -v
    ```
    Result: 13 passed in 9.14s.
  - **Full 10-Suite Regression:**
    ```bash
    python3 -m pytest tests/test_sba_02_discovery.py tests/test_scrum_board_actions.py tests/test_dashboard.py tests/test_tenant_boundary.py tests/test_durable_identity.py tests/test_revision_security.py tests/test_pm_engine.py tests/test_pm_remediation.py tests/test_pm_07_dependencies_and_authorization.py tests/test_sba_05_session_integration.py
    ```
    Result: 122 passed in 23.05s.
  - **Live Runtime Verification (`http://127.0.0.1:8080`):**
    - `curl -i -s http://127.0.0.1:8080/api/pm/v1/session` -> 401 Unauthorized with `Cache-Control: no-store`.
    - `curl -i -s -X POST http://127.0.0.1:8080/api/pm/v1/session/login` -> 200 OK with `Set-Cookie: mas_session=...` and `csrf_token`.
    - `curl -i -s http://127.0.0.1:8080/api/pm/v1/session -H "Cookie: ..."` -> 200 OK.
    - `curl -i -s -X POST http://127.0.0.1:8080/api/pm/issues/create -H "Cookie: ..." -H "X-CSRF-Token: ..."` -> 200 OK.
    - `curl -i -s -X POST http://127.0.0.1:8080/api/pm/issues/create -H "Cookie: ..."` (no CSRF) -> 403 Forbidden.
    - `curl -i -s -X POST http://127.0.0.1:8080/api/pm/v1/session/logout -H "Cookie: ..."` -> 200 OK with `Max-Age=0`.
- **Required authority:**
  - Local repository write access for discovery git operations and SQLite database.
- **Delivery evidence:**
  - Branch: `feat/scrum-board-automation`
  - Commits: `8742c802`, `c555b0ca`
  - Push status: Up to date with `origin/feat/scrum-board-automation`.
- **Acknowledgement:**
  - Implementation completed and verified by Antigravity development team.
  - Tagged for counterparty review by Codex / Independent Reviewer.
