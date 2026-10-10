# SBA-05 frontend & backend candidate (Reworked)

Codex removed the hard-coded founder_lead caller; the server alone resolves the actor. Mutations fetch the authenticated same-origin session, require principal and csrf_token, attach X-CSRF-Token and use same-origin cookies. Credentials are not stored in browser storage or URLs. Session lookup failure blocks the mutation. Redirected API responses fail visibly instead of masquerading as successful JSON. Drawer errors are inside the modal top layer, persistent and announced via role=alert.

Backend dependency: Antigravity must provide the agreed cookie session/login/page serving and CSRF enforcement, including `GET /api/pm/v1/session` returning `{principal, tenant_id, permitted_actions, csrf_token}`. csrf_token is session-bound, not the login/Bearer secret; authenticate and set no-store on this response.

## Backend delivery and review remediations (Antigravity development team)

Per [SBA_02_05_BACKEND_REVIEW.md](SBA_02_05_BACKEND_REVIEW.md), the Antigravity development team remediated all architectural review findings across authentication, tenant cookie bridging, browser security, and session management.

### 1. Remediated backend architecture

- **Caller-selected identity prohibition:**
  - Login endpoint (`POST /api/pm/v1/session/login`) rejects client-supplied principal or tenant claims (returns `403 Forbidden`). Actor and tenant are resolved strictly from verified IAM credentials or fixed server configuration.
  - Fail-closed unconfigured authentication: If authentication is unconfigured, login and mutations return `401 Unauthorized`. Arbitrary Bearer tokens are never accepted.
- **Public IAM-backed tenant cookie bridge:**
  - `mas/iam.py`: Added public `validate_session()` verifying tenant active status, principal registration, session revocation, token hash match, and expiry; generates and registers `TenantContext`.
  - Added `get_permitted_actions()` deriving action claims dynamically from current authority rather than static broad defaults.
  - Added `suspend_principal(tenant_id, user_id)` revoking all active principal sessions and de-registering principal.
  - `mas/pm/session.py`: `create_session` stores SHA-256 digests (`iam_token_hash`, `iam_session_id`, `iam_expires_at`). Never stores raw IAM tokens in PM SQLite.
  - `get_session` validates session via public `iam.validate_session()`, dynamically attaching `tenant_context` and permitted actions.
  - `mas/tenancy.py`: `tenant_scope` accepts `TenantContext` directly, enforcing isolation, tenant checking, binding, and execution scope without bypassing guards.
- **Browser security & tenant portal serving:**
  - **Reachable unprivileged login page:** Delivered `portal/login.html` (public bootstrap, 200 OK without credentials).
  - **Authenticated tenant portal:** `TenantDashboardRequestHandler` redirects unauthenticated requests for `/portal/scrum.html` or `/portal` to `/portal/login.html` (`302 Found`). Authenticated requests serve the page inside `tenant_scope`. Cross-tenant data endpoints (`/portal/snapshot.json`) return `403 Forbidden`.
  - **Origin validation:** POST requests enforce loopback and `allowed_origins` checks against `Origin` and `Referer` headers (untrusted origins return `403 Forbidden`).
  - **CSRF protection:** Login issues session-bound `mas_csrf_token` cookie and returns `csrf_token` in JSON body. Logout (`POST /api/pm/v1/session/logout`) and all PM mutations require matching `X-CSRF-Token` on cookie sessions.
  - **Secure cookies:** Cookies issued with `Secure` flag for deployed HTTPS/non-loopback hosts; retains explicit development exception for loopback (`127.0.0.1`, `localhost`, `::1`).
  - **No silent fallback:** Invalid Bearer tokens immediately fail closed (`401 Unauthorized`), never falling back to cookie lookup.

### 2. Empirical integration test results

Test suite: `tests/test_sba_05_session_integration.py`  
Command: `python3 -m pytest tests/test_sba_05_session_integration.py -v`  
Result: 20 passed in 9.87s.

Key regressions verified:
1. `test_login_caller_selected_identity_prohibited`: Verifies client cannot forge reviewer or coordinator claims.
2. `test_unconfigured_auth_rejects_login`: Verifies server fails closed when authentication is unconfigured.
3. `test_arbitrary_bearer_rejected_in_pm_mutation`: Verifies arbitrary Bearer tokens return 401.
4. `test_tenant_cookie_authentication_and_api_access`: Verifies tenant cookie GET and POST through public IAM bridge.
5. `test_revoked_session_denies_cookie_access`: Verifies revoked sessions deny cookie access immediately.
6. `test_suspended_principal_denies_access`: Verifies suspended principals cannot authenticate.
7. `test_unprivileged_login_page_reachable`: Verifies `/portal/login.html` returns 200 unauthenticated.
8. `test_unauthenticated_portal_redirects_to_login`: Verifies unauthenticated `/portal/scrum.html` returns 302.
9. `test_login_origin_validation`: Verifies cross-origin login attempts return 403.
10. `test_logout_csrf_enforcement`: Verifies logout without valid CSRF header is rejected.
11. `test_secure_cookie_attribute`: Verifies `Secure` attribute on HTTPS hosts with loopback exception.
12. `test_real_browser_login_and_board_actions`: End-to-end browser login, cookie issue, board loading, and authenticated actions.

### 3. Live browser evidence

Browser verification script: `scripts/record_browser_evidence.py`  
Evidence captured in `workspace/review-evidence/`:
- `01_portal_login_page.png`: Unprivileged public login bootstrap rendered in headless Chromium.
- `02_scrum_board_authenticated.png`: Authenticated delivery board rendering live issues and columns in tenant scope.
- `BROWSER_EVIDENCE_REPORT.md`: Step-by-step verification log of redirect, login, cookie attributes, board loading, CSRF logout, and post-logout denial.
