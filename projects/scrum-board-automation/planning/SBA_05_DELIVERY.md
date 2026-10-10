# SBA-05 frontend candidate

Codex removed the hard-coded founder_lead caller; the server alone resolves the actor. Mutations fetch the authenticated same-origin session, require principal and csrf_token, attach X-CSRF-Token and use same-origin cookies. Credentials are not stored in browser storage or URLs. Session lookup failure blocks the mutation. Redirected API responses fail visibly instead of masquerading as successful JSON. Drawer errors are inside the modal top layer, persistent and announced via role=alert.

Backend dependency: Antigravity must provide the agreed cookie session/login/page serving and CSRF enforcement, including `GET /api/pm/v1/session` returning `{principal, tenant_id, permitted_actions, csrf_token}`. csrf_token is session-bound, not the login/Bearer secret; authenticate and set no-store on this response. Returning it here is a concrete frontend contract extension needed after reload. Existing legacy mutation URLs remain during versioned migration and must receive identical cookie authorization/CSRF enforcement. No backend files were changed.

Until that backend exists, the board retains available read behavior but blocks mutations with an error. This is intentional fail-closed behavior, not completed end-to-end authentication. Candidate requires real backend integration and independent review before SBA-05 is DONE.

Validation: four Playwright browser checks passed with controlled responses: valid session sends CSRF without actor claim; structured 403 error retained; modal error visible and focused; missing session sends no mutation. Screenshot captured and inspected at /workspace/review-evidence/sba05/rejected-action.png. These checks validate frontend handling, not live IAM/CSRF enforcement. No whole-repository or native computer-use test claim is made for this candidate.

## Unblocked follow-up and regression correction

The first helper replacement inadvertently removed board render/load helpers; direct request tests missed this. Restored those helpers and added persistent tests/test_scrum_board_actions.py covering real page load and user form interactions. Seven browser tests pass with controlled responses, including issue creation, transition, visible/focused denial, and missing/expired/unavailable session blocking. Ruff and diff whitespace checks pass. Requests now have a 15-second deadline and content exposes aria-busy. A corrected full-board modal screenshot was captured and inspected. No live backend/security test is claimed.

Prepared SBA_06_FRONTEND_SPEC.md and LIVE_INTEGRATION_CHECKLIST.md for actual backend integration. These specify activity/evidence rendering, freshness, recovery and live acceptance; they do not introduce a simulated live feed or mark dependent tasks DONE.

## Backend delivery and integration verification (Antigravity development team)

Per the backend dependency specified above, the Antigravity development team implemented and verified the complete session, CSRF, and static serving backend contracts.

### 1. Implemented backend architecture
- **Session Manager (`mas/pm/session.py`):**
  - Manages opaque 256-bit hex session secrets stored as SHA-256 hashes in `pm_sessions`.
  - Cryptographically separates `csrf_token` from the session secret, preventing token reflection attacks.
  - Enforces 8-hour hard maximum TTL and 30-minute idle inactivity timeout.
  - Supports IAM revocation chaining: revoking an underlying IAM token automatically cascades and revokes the associated cookie session.
  - Generates secure `Set-Cookie: mas_session=...; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800` headers.
- **Session and CSRF Endpoints (`mas/dashboard/server.py`):**
  - `GET /api/pm/v1/session`: Returns `{principal, tenant_id, permitted_actions, csrf_token}` with `Cache-Control: no-store`. Unauthenticated requests return `401 Unauthorized` with `Cache-Control: no-store`.
  - `POST /api/pm/v1/session/login`: Validates caller credentials (IAM token or dashboard auth token) and issues the `mas_session` cookie and session metadata.
  - `POST /api/pm/v1/session/logout`: Revokes the session record in `pm_sessions` and clears the cookie via `Max-Age=0`.
- **Strict Mutation Authorization & Server-Resolved Actor:**
  - Applied across all mutation endpoints (`/api/pm/transition`, `/api/pm/verdicts`, `/api/pm/issues/create`, `/api/pm/sprints/create`, `/api/pm/sprints/state`, `/api/pm/issues/assign_sprint`).
  - **No silent fallback:** If an `Authorization: Bearer` header is present but malformed or invalid, the server immediately returns `401 Unauthorized`, never checking or falling back to cookies.
  - **CSRF verification:** Requests using cookie sessions require a valid `X-CSRF-Token` matching the session; missing or invalid tokens immediately return `403 Forbidden`.
  - **Server-resolved actor:** Request payloads claiming an explicit `caller_principal` or `reviewer_principal` distinct from the authenticated actor are rejected with `403 Forbidden`.
- **Static Portal Serving:**
  - `/portal/*` serves Codex HTML, CSS, JS, and image assets with `X-Content-Type-Options: nosniff`.
  - Directory traversal attacks (`..`) and repository escapes outside `portal/` are rejected with 404/403.

### 2. Empirical integration test results
Test command:
```bash
python3 -m pytest tests/test_sba_05_session_integration.py -v
```
Actual output:
```
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0 -- /home/acinonyx/anaconda3/bin/python3
cachedir: .pytest_cache
rootdir: /home/acinonyx/Desktop/MAS
configfile: pyproject.toml
plugins: anyio-4.12.1
collecting ... collected 13 items

tests/test_sba_05_session_integration.py::test_unauthenticated_session_returns_401_no_store PASSED [  7%]
tests/test_sba_05_session_integration.py::test_login_establishes_session_and_cookie PASSED [ 15%]
tests/test_sba_05_session_integration.py::test_get_session_with_valid_cookie PASSED [ 23%]
tests/test_sba_05_session_integration.py::test_mutation_with_cookie_and_csrf_succeeds PASSED [ 30%]
tests/test_sba_05_session_integration.py::test_mutation_missing_csrf_returns_403 PASSED [ 38%]
tests/test_sba_05_session_integration.py::test_mutation_invalid_csrf_returns_403 PASSED [ 46%]
tests/test_sba_05_session_integration.py::test_caller_impersonation_returns_403 PASSED [ 53%]
tests/test_sba_05_session_integration.py::test_logout_revokes_session_and_clears_cookie PASSED [ 61%]
tests/test_sba_05_session_integration.py::test_bearer_token_authentication_succeeds_without_csrf PASSED [ 69%]
tests/test_sba_05_session_integration.py::test_invalid_bearer_does_not_fall_back_to_cookie PASSED [ 76%]
tests/test_sba_05_session_integration.py::test_session_idle_timeout_rejection PASSED [ 84%]
tests/test_sba_05_session_integration.py::test_iam_revocation_chaining PASSED [ 92%]
tests/test_sba_05_session_integration.py::test_portal_file_serving_and_traversal_prevention PASSED [100%]

============================== 13 passed in 9.14s ==============================
```

Full regression suite:
```bash
python3 -m pytest tests/test_sba_02_discovery.py tests/test_scrum_board_actions.py tests/test_dashboard.py tests/test_tenant_boundary.py tests/test_durable_identity.py tests/test_revision_security.py tests/test_pm_engine.py tests/test_pm_remediation.py tests/test_pm_07_dependencies_and_authorization.py tests/test_sba_05_session_integration.py
```
Actual output:
```
============================= 122 passed in 23.05s =============================
```

### 3. Live server endpoint verification
Verified against live daemon `http://127.0.0.1:8080`:
- `GET /api/pm/v1/session` unauthenticated: `HTTP/1.0 401 Unauthorized`, `Cache-Control: no-store`, `{"error": {"message": "Session unavailable"}}`.
- `POST /api/pm/v1/session/login`: `HTTP/1.0 200 OK`, `Set-Cookie: mas_session=...; Path=/; HttpOnly; SameSite=Lax; Max-Age=28800`, returns `{principal, tenant_id, permitted_actions, csrf_token}`.
- `GET /api/pm/v1/session` with session cookie: `HTTP/1.0 200 OK`, `Cache-Control: no-store`.
- `POST /api/pm/issues/create` with cookie + CSRF: `HTTP/1.0 200 OK`, creates `SBA-10`.
- `POST /api/pm/issues/create` with cookie but missing CSRF: `HTTP/1.0 403 Forbidden`, `{"error": "Forbidden: CSRF token missing or invalid"}`.
- `POST /api/pm/v1/session/logout`: `HTTP/1.0 200 OK`, `Set-Cookie: mas_session=; ... Max-Age=0`.
- Post-logout `GET /api/pm/v1/session`: `HTTP/1.0 401 Unauthorized`.

