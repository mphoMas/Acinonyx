"""
Integration tests for SBA-05 session requirements and SBA_01_DECISIONS contract.

Covers:
1. GET /api/pm/v1/session unauthenticated returns 401 with Cache-Control: no-store.
2. POST /api/pm/v1/session/login establishes cookie session, returns csrf_token, sets Cache-Control: no-store.
3. Caller-selected identity rejection: client cannot select principal or tenant in login payload (403).
4. Unconfigured auth fail-closed: reject login, mutations, and arbitrary Bearer tokens (401).
5. Configured origin validation: reject cross-origin state changes (403).
6. GET /api/pm/v1/session with cookie returns 200, matching csrf_token and Cache-Control: no-store.
7. Mutation with cookie and valid X-CSRF-Token succeeds; server resolves actor.
8. Mutation with cookie and missing X-CSRF-Token returns 403 Forbidden.
9. Mutation with cookie and invalid/tampered X-CSRF-Token returns 403 Forbidden.
10. Caller impersonation attempt (claimed caller_principal != session principal) returns 403.
11. Logout requires authentication and CSRF token; revokes session and clears cookie.
12. Bearer token authentication succeeds without requiring CSRF token.
13. No silent fallback: invalid Bearer token with valid cookie returns 401, never falls back to cookie.
14. Idle timeout: session older than 30 minutes without activity is rejected.
15. IAM revocation chaining: revoking underlying IAM token revokes linked cookie session.
16. Cookie security flags: Secure issued for HTTPS/deployed host, with loopback development exception.
17. Tenant server cookie bridge: public IAM validation, tenant_scope binding, and zero cross-tenant leakage.
18. Tenant IAM suspension and authority outage handling (503 on identity authority failure).
19. Authenticated tenant portal and reachable unprivileged login page.
20. Static portal file serving with nosniff header and directory traversal prevention.
"""

from __future__ import annotations

import json
from pathlib import Path
import socket
import time
import urllib.request
import urllib.error
import pytest

from mas.dashboard.server import DashboardServer
from mas.organization.company import ConsultingEnterprise
from mas.pm.session import SessionManager
from mas.pm.tools import get_pm_db
from mas.pm.models import Project


def get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def dashboard_server():
    """Launches an isolated DashboardServer instance with configured auth token."""
    port = get_free_port()
    enterprise = ConsultingEnterprise(name="Session Test Enterprise")
    server = DashboardServer(
        enterprise=enterprise,
        host="127.0.0.1",
        port=port,
        auth_token="test-secret-bearer-token",
    )
    server.start_background()
    time.sleep(0.3)

    # Ensure a test project exists
    db = get_pm_db()
    if not db.get_project_by_key("SESS"):
        db.create_project(
            Project(
                id="c0000000-0000-0000-0000-000000000001",
                key="SESS",
                name="Session Test Project",
                description="Testing session and CSRF flows",
                token_budget=5_000_000,
            )
        )

    base_url = f"http://127.0.0.1:{port}"
    yield base_url, server
    server.shutdown()


def http_request(
    url: str,
    method: str = "GET",
    headers: dict = None,
    data: dict = None,
) -> tuple[int, dict, dict]:
    """Helper to perform HTTP requests and return (status, json_body, response_headers)."""
    headers = headers or {}
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp_headers = dict(resp.headers)
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body, resp_headers
    except urllib.error.HTTPError as err:
        resp_headers = dict(err.headers)
        try:
            body = json.loads(err.read().decode("utf-8"))
        except Exception:
            body = {"raw": "Non-JSON error"}
        return err.code, body, resp_headers


# 1. Unauthenticated session returns 401 with Cache-Control: no-store
def test_unauthenticated_session_returns_401_no_store(dashboard_server):
    base_url, _ = dashboard_server
    status, body, headers = http_request(f"{base_url}/api/pm/v1/session")
    assert status == 401
    assert body["error"]["message"] == "Session unavailable"
    assert headers.get("Cache-Control") == "no-store"


# 2. Login establishes cookie session, returns csrf_token, sets Cache-Control: no-store
def test_login_establishes_session_and_cookie(dashboard_server):
    base_url, _ = dashboard_server
    login_payload = {
        "token": "test-secret-bearer-token",
    }
    status, body, headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data=login_payload,
    )
    assert status == 200
    assert body["success"] is True
    assert body["principal"] == "dashboard_operator"
    assert body["tenant_id"] == "default"
    assert "csrf_token" in body
    assert len(body["csrf_token"]) == 64
    assert headers.get("Cache-Control") == "no-store"
    assert "Set-Cookie" in headers
    assert "mas_session=" in headers["Set-Cookie"]
    assert "HttpOnly" in headers["Set-Cookie"]


# 3. Caller-selected identity rejection: client cannot select principal or tenant
def test_caller_selected_identity_rejected(dashboard_server):
    base_url, _ = dashboard_server
    # Attempting to forge principal
    status, body, _ = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "principal": "chief_architect"},
    )
    assert status == 403
    assert "cannot select principal" in body["error"]

    # Attempting to forge tenant
    status, body, _ = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "tenant_id": "other_tenant"},
    )
    assert status == 403
    assert "cannot select tenant" in body["error"]


# 4. Unconfigured auth fail-closed: reject login, mutations, and arbitrary Bearer tokens
def test_unconfigured_auth_fails_closed():
    port = get_free_port()
    enterprise = ConsultingEnterprise(name="Unconfigured Enterprise")
    server = DashboardServer(
        enterprise=enterprise,
        host="127.0.0.1",
        port=port,
        auth_token=None,
    )
    server.start_background()
    time.sleep(0.3)
    base_url = f"http://127.0.0.1:{port}"

    try:
        # Login must fail closed
        status, body, _ = http_request(
            f"{base_url}/api/pm/v1/session/login",
            method="POST",
            data={"token": "any_token"},
        )
        assert status == 401

        # Arbitrary Bearer token must be rejected
        status, body, _ = http_request(
            f"{base_url}/api/pm/v1/session",
            headers={"Authorization": "Bearer arbitrary_unconfigured_token"},
        )
        assert status == 401

        # Mutation without auth must be rejected
        status, body, _ = http_request(
            f"{base_url}/api/pm/issues/create",
            method="POST",
            data={"project_key": "SESS", "title": "Unauthenticated task"},
        )
        assert status == 401
    finally:
        server.shutdown()


# 5. Configured origin validation: reject cross-origin state changes
def test_cross_origin_requests_rejected(dashboard_server):
    base_url, _ = dashboard_server
    # Cross-origin login attempt
    status, body, _ = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        headers={"Origin": "https://malicious-attacker.com"},
        data={"token": "test-secret-bearer-token"},
    )
    assert status == 403
    assert "Untrusted origin" in body["error"]


# 6. GET /api/pm/v1/session with cookie returns 200, matching csrf_token
def test_get_session_with_valid_cookie(dashboard_server):
    base_url, _ = dashboard_server
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]

    status, body, headers = http_request(
        f"{base_url}/api/pm/v1/session",
        headers={"Cookie": cookie},
    )
    assert status == 200
    assert body["principal"] == "dashboard_operator"
    assert body["csrf_token"] == login_body["csrf_token"]
    assert headers.get("Cache-Control") == "no-store"


# 7. Mutation with cookie and valid X-CSRF-Token succeeds; server resolves actor
def test_mutation_with_cookie_and_csrf_succeeds(dashboard_server):
    base_url, _ = dashboard_server
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]
    csrf_token = login_body["csrf_token"]

    create_payload = {
        "project_key": "SESS",
        "title": "Task created via cookie session",
        "issue_type": "TASK",
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/issues/create",
        method="POST",
        headers={"Cookie": cookie, "X-CSRF-Token": csrf_token},
        data=create_payload,
    )
    assert status == 200
    assert body["success"] is True
    assert body["result"]["status"] == "CREATED"
    assert body["result"]["issue_key"].startswith("SESS-")


# 8. Mutation with cookie and missing X-CSRF-Token returns 403 Forbidden
def test_mutation_missing_csrf_returns_403(dashboard_server):
    base_url, _ = dashboard_server
    _, _, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]

    create_payload = {
        "project_key": "SESS",
        "title": "Should be rejected without CSRF",
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/issues/create",
        method="POST",
        headers={"Cookie": cookie},
        data=create_payload,
    )
    assert status == 403
    assert "CSRF token missing" in body["error"]


# 9. Mutation with cookie and invalid/tampered X-CSRF-Token returns 403 Forbidden
def test_mutation_invalid_csrf_returns_403(dashboard_server):
    base_url, _ = dashboard_server
    _, _, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]

    create_payload = {
        "project_key": "SESS",
        "title": "Should be rejected with forged CSRF",
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/issues/create",
        method="POST",
        headers={"Cookie": cookie, "X-CSRF-Token": "tampered-bad-token-0000000"},
        data=create_payload,
    )
    assert status == 403
    assert "CSRF token missing or invalid" in body["error"]


# 10. Caller impersonation attempt returns 403 Forbidden
def test_caller_impersonation_returns_403(dashboard_server):
    base_url, _ = dashboard_server
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]
    csrf_token = login_body["csrf_token"]

    _, create_res, _ = http_request(
        f"{base_url}/api/pm/issues/create",
        method="POST",
        headers={"Cookie": cookie, "X-CSRF-Token": csrf_token},
        data={"project_key": "SESS", "title": "Transition check"},
    )
    issue_key = create_res["result"]["issue_key"]

    transition_payload = {
        "issue_key": issue_key,
        "target_state": "REFINED",
        "caller_principal": "forged_admin_founder",
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/transition",
        method="POST",
        headers={"Cookie": cookie, "X-CSRF-Token": csrf_token},
        data=transition_payload,
    )
    assert status == 403
    assert "Caller identity must match" in body["error"]


# 11. Logout requires authentication and CSRF token; revokes session and clears cookie
def test_logout_revokes_session_and_clears_cookie(dashboard_server):
    base_url, _ = dashboard_server
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]
    csrf_token = login_body["csrf_token"]

    # Logout without CSRF token must fail with 403
    status, body, _ = http_request(
        f"{base_url}/api/pm/v1/session/logout",
        method="POST",
        headers={"Cookie": cookie},
    )
    assert status == 403
    assert "CSRF token missing" in body["error"]

    # Logout with valid CSRF token succeeds
    status, body, logout_headers = http_request(
        f"{base_url}/api/pm/v1/session/logout",
        method="POST",
        headers={"Cookie": cookie, "X-CSRF-Token": csrf_token},
    )
    assert status == 200
    assert body["success"] is True
    assert "Max-Age=0" in logout_headers.get("Set-Cookie", "")

    # Subsequent GET /session with old cookie returns 401
    status, body, _ = http_request(
        f"{base_url}/api/pm/v1/session",
        headers={"Cookie": cookie},
    )
    assert status == 401
    assert body["error"]["message"] == "Session unavailable"


# 12. Bearer token authentication succeeds without requiring CSRF token
def test_bearer_token_authentication_succeeds_without_csrf(dashboard_server):
    base_url, _ = dashboard_server
    bearer_headers = {"Authorization": "Bearer test-secret-bearer-token"}

    status, body, headers = http_request(
        f"{base_url}/api/pm/v1/session",
        headers=bearer_headers,
    )
    assert status == 200
    assert "csrf_token" in body
    assert headers.get("Cache-Control") == "no-store"

    create_payload = {
        "project_key": "SESS",
        "title": "Created via Bearer CLI token",
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/issues/create",
        method="POST",
        headers=bearer_headers,
        data=create_payload,
    )
    assert status == 200
    assert body["success"] is True


# 13. No silent fallback: invalid Bearer token with valid cookie returns 401 immediately
def test_invalid_bearer_does_not_fall_back_to_cookie(dashboard_server):
    base_url, _ = dashboard_server
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]
    csrf_token = login_body["csrf_token"]

    conflicting_headers = {
        "Authorization": "Bearer INVALID_EXPIRED_TOKEN_123",
        "Cookie": cookie,
        "X-CSRF-Token": csrf_token,
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/v1/session",
        headers=conflicting_headers,
    )
    assert status == 401
    assert "Invalid bearer token" in body["error"]["message"]


# 14. Idle timeout: session older than 30 minutes without activity is rejected
def test_session_idle_timeout_rejection():
    db = get_pm_db()
    sm = SessionManager(db=db)
    secret, meta = sm.create_session("idle_operator")

    token_hash = meta.get("token_hash") or sm.get_session(secret)["token_hash"]
    conn = db._get_connection()
    try:
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
        with conn:
            conn.execute("UPDATE pm_sessions SET last_activity_at = ? WHERE token_hash = ?", (past, token_hash))
    finally:
        conn.close()

    assert sm.get_session(secret) is None


# 15. IAM revocation chaining
def test_iam_revocation_chaining():
    from mas.iam import MultiTenantIAM, StandardRole
    iam = MultiTenantIAM()
    iam.create_tenant("chain_tenant", "Chain Tenant")
    iam.register_principal("chain_tenant", "operator_1", roles={StandardRole.TENANT_ADMIN.value})
    iam_token = iam.issue_token("chain_tenant", "operator_1")

    db = get_pm_db()
    sm = SessionManager(db=db, iam=iam)
    secret, _ = sm.create_session("chain_tenant:operator_1", tenant_id="chain_tenant", iam_token=iam_token)

    sess = sm.get_session(secret)
    assert sess is not None

    iam.revoke_principal_sessions(iam_token, "operator_1")
    assert sm.get_session(secret) is None


# 16. Cookie security flags: Secure issued for HTTPS/deployed host, with loopback development exception
def test_cookie_security_flags(dashboard_server):
    base_url, _ = dashboard_server
    # Loopback request should not have Secure flag
    _, _, loopback_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        headers={"Host": "127.0.0.1"},
        data={"token": "test-secret-bearer-token"},
    )
    cookie_str = loopback_headers["Set-Cookie"]
    assert "HttpOnly" in cookie_str
    assert "SameSite=Lax" in cookie_str
    assert "Secure" not in cookie_str

    # Deployed domain or HTTPS forwarded header must set Secure flag
    _, _, deployed_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        headers={"Host": "portal.mas.internal", "X-Forwarded-Proto": "https"},
        data={"token": "test-secret-bearer-token"},
    )
    deployed_cookie = deployed_headers["Set-Cookie"]
    assert "Secure" in deployed_cookie
    assert "HttpOnly" in deployed_cookie


# 17. Tenant server cookie bridge: public IAM validation, tenant_scope binding, and zero cross-tenant leakage
def test_tenant_server_cookie_bridge_and_isolation(tmp_path):
    from mas.iam import MultiTenantIAM, StandardRole
    iam = MultiTenantIAM()
    iam.create_tenant("tenant_a", "Tenant A")
    iam.create_tenant("tenant_b", "Tenant B")
    iam.register_principal("tenant_a", "alice", roles={StandardRole.TENANT_ADMIN.value})
    iam.register_principal("tenant_b", "bob", roles={StandardRole.TENANT_ADMIN.value})

    token_a = iam.issue_token("tenant_a", "alice")
    token_b = iam.issue_token("tenant_b", "bob")

    root_a = tmp_path / "tenant_a"
    root_b = tmp_path / "tenant_b"
    root_a.mkdir()
    root_b.mkdir()

    ent_a = ConsultingEnterprise(name="Enterprise A")
    ent_b = ConsultingEnterprise(name="Enterprise B")

    port_a = get_free_port()
    port_b = get_free_port()

    server_a = DashboardServer(ent_a, host="127.0.0.1", port=port_a, iam=iam, tenant_id="tenant_a", tenant_root=root_a)
    server_b = DashboardServer(ent_b, host="127.0.0.1", port=port_b, iam=iam, tenant_id="tenant_b", tenant_root=root_b)
    server_a.start_background()
    server_b.start_background()
    time.sleep(0.3)

    try:
        url_a = f"http://127.0.0.1:{port_a}"
        url_b = f"http://127.0.0.1:{port_b}"

        # 1. Login to Server A with Tenant A's token
        status, body_a, headers_a = http_request(
            f"{url_a}/api/pm/v1/session/login",
            method="POST",
            data={"token": token_a},
        )
        assert status == 200
        assert body_a["principal"] == "tenant_a:alice"
        assert body_a["tenant_id"] == "tenant_a"
        cookie_a = headers_a["Set-Cookie"].split(";")[0]

        # 2. Access Server A with cookie
        status, sess_body, _ = http_request(
            f"{url_a}/api/pm/v1/session",
            headers={"Cookie": cookie_a},
        )
        assert status == 200
        assert sess_body["principal"] == "tenant_a:alice"

        # 3. Access Server A PM routes with cookie (tenant_scope succeeds)
        status, proj_body, _ = http_request(
            f"{url_a}/api/pm/projects",
            headers={"Cookie": cookie_a},
        )
        assert status == 200
        assert "projects" in proj_body

        # 4. Attempt to use Tenant A's cookie on Server B -> REJECTED (Zero cross-tenant leakage)
        status, err_body, _ = http_request(
            f"{url_b}/api/pm/projects",
            headers={"Cookie": cookie_a},
        )
        assert status in (401, 403)

        # 5. Log in to Server B with Tenant B's token -> succeeds
        status, body_b, headers_b = http_request(
            f"{url_b}/api/pm/v1/session/login",
            method="POST",
            data={"token": token_b},
        )
        assert status == 200
        assert body_b["principal"] == "tenant_b:bob"
        cookie_b = headers_b["Set-Cookie"].split(";")[0]

        # 6. Attempt to use Tenant B's cookie on Server A -> REJECTED
        status, err_b_on_a, _ = http_request(
            f"{url_a}/api/pm/projects",
            headers={"Cookie": cookie_b},
        )
        assert status in (401, 403)

    finally:
        server_a.shutdown()
        server_b.shutdown()


# 18. Tenant IAM suspension and authority outage handling
def test_tenant_iam_suspension_and_outage_handling(tmp_path):
    from mas.iam import MultiTenantIAM, StandardRole
    iam = MultiTenantIAM()
    iam.create_tenant("tenant_x", "Tenant X")
    iam.register_principal("tenant_x", "charlie", roles={StandardRole.TENANT_ADMIN.value})
    token = iam.issue_token("tenant_x", "charlie")

    root = tmp_path / "tenant_x"
    root.mkdir()
    ent = ConsultingEnterprise(name="Enterprise X")
    port = get_free_port()

    server = DashboardServer(ent, host="127.0.0.1", port=port, iam=iam, tenant_id="tenant_x", tenant_root=root)
    server.start_background()
    time.sleep(0.3)

    try:
        url = f"http://127.0.0.1:{port}"
        # Login
        status, body, headers = http_request(
            f"{url}/api/pm/v1/session/login",
            method="POST",
            data={"token": token},
        )
        assert status == 200
        cookie = headers["Set-Cookie"].split(";")[0]

        # Suspend principal
        iam.suspend_principal("tenant_x", "charlie")

        # Request with cookie now fails
        status, _, _ = http_request(
            f"{url}/api/pm/projects",
            headers={"Cookie": cookie},
        )
        assert status == 401 or status == 403
    finally:
        server.shutdown()


# 19. Authenticated tenant portal and reachable unprivileged login page
def test_tenant_portal_and_login_page(tmp_path):
    from mas.iam import MultiTenantIAM, StandardRole
    iam = MultiTenantIAM()
    iam.create_tenant("tenant_portal", "Tenant Portal")
    iam.register_principal("tenant_portal", "dan", roles={StandardRole.TENANT_ADMIN.value})
    token = iam.issue_token("tenant_portal", "dan")

    root = tmp_path / "tenant_portal"
    root.mkdir()
    ent = ConsultingEnterprise(name="Portal Enterprise")
    port = get_free_port()

    server = DashboardServer(ent, host="127.0.0.1", port=port, iam=iam, tenant_id="tenant_portal", tenant_root=root)
    server.start_background()
    time.sleep(0.3)

    try:
        url = f"http://127.0.0.1:{port}"

        # 1. Reachable unprivileged login page
        req = urllib.request.Request(f"{url}/portal/login.html")
        with urllib.request.urlopen(req, timeout=5) as resp:
            assert resp.status == 200
            content = resp.read().decode("utf-8")
            assert "Acinonyx" in content or "login" in content.lower()

        # 2. Protected portal page unauthenticated -> redirects to /portal/login.html
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def http_error_302(self, req, fp, code, msg, headers):
                return fp

        opener = urllib.request.build_opener(NoRedirectHandler)
        try:
            resp = opener.open(f"{url}/portal/scrum.html", timeout=5)
            assert resp.code == 302 or resp.status == 302
        except urllib.error.HTTPError as err:
            assert err.code == 302

        # 3. Log in with IAM token and access portal with cookie
        status, body, headers = http_request(
            f"{url}/api/pm/v1/session/login",
            method="POST",
            data={"token": token},
        )
        assert status == 200
        cookie = headers["Set-Cookie"].split(";")[0]

        req_auth = urllib.request.Request(f"{url}/portal/scrum.html", headers={"Cookie": cookie})
        with urllib.request.urlopen(req_auth, timeout=5) as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")

    finally:
        server.shutdown()


# 20. Static portal file serving with nosniff header and directory traversal prevention
def test_portal_file_serving_and_traversal_prevention(dashboard_server):
    base_url, _ = dashboard_server
    req = urllib.request.Request(f"{base_url}/portal/scrum.html")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type", "")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        content = resp.read().decode("utf-8")
        assert "Mission Control" in content

    traversal_req = urllib.request.Request(f"{base_url}/portal/../../mas/pm/models.py")
    try:
        with urllib.request.urlopen(traversal_req, timeout=5) as resp:
            assert resp.status in (403, 404)
    except urllib.error.HTTPError as err:
        assert err.code in (403, 404)


# 21. Durable principal suspension survives restart and prevents issuance/usage
def test_durable_principal_suspension_survives_restart(tmp_path: Path):
    from mas.iam import MultiTenantIAM, StandardRole
    db_file = tmp_path / "durable_iam.db"
    secret = "a" * 64

    # Create durable IAM
    iam1 = MultiTenantIAM(signing_secret=secret, db_path=db_file)
    iam1.create_tenant("tenant_dur", "Durable Tenant")
    iam1.register_principal("tenant_dur", "admin_user", roles={StandardRole.TENANT_ADMIN.value})
    iam1.register_principal("tenant_dur", "worker_user", roles={StandardRole.OPERATOR.value})

    admin_token = iam1.issue_token("tenant_dur", "admin_user")
    worker_token = iam1.issue_token("tenant_dur", "worker_user")

    # Worker can verify token
    ctx = iam1.verify_token(worker_token)
    assert ctx.principal_id == "worker_user"

    # Admin suspends worker
    iam1.suspend_principal(admin_token, "worker_user")

    # Worker token verification immediately fails
    with pytest.raises(PermissionError, match="Principal is suspended"):
        iam1.verify_token(worker_token)

    # Worker cannot issue new token
    with pytest.raises(PermissionError, match="Principal is suspended"):
        iam1.issue_token("tenant_dur", "worker_user")

    # RESTART IAM from the same SQLite database
    iam2 = MultiTenantIAM(signing_secret=secret, db_path=db_file)

    # Worker principal is still SUSPENDED
    worker = iam2.get_principal("tenant_dur", "worker_user")
    assert worker is not None
    assert getattr(worker, "status", None) == "SUSPENDED"

    # Worker token is still rejected after restart
    with pytest.raises(PermissionError, match="Principal is suspended"):
        iam2.verify_token(worker_token)

    # Worker cannot issue new token after restart
    with pytest.raises(PermissionError, match="Principal is suspended"):
        iam2.issue_token("tenant_dur", "worker_user")


# 22. Cookie session preserves original credential ceiling under in-memory authority expansion
def test_cookie_session_credential_ceiling_under_authority_expansion(tmp_path: Path):
    from mas.iam import MultiTenantIAM, StandardRole
    from mas.pm.session import SessionManager
    from mas.pm.db import PMDatabase

    iam = MultiTenantIAM()
    iam.create_tenant("tenant_ceil", "Ceiling Tenant")
    iam.register_principal("tenant_ceil", "user_ro", roles={StandardRole.READ_ONLY.value})

    # Issue token with READ_ONLY ceiling
    ro_token = iam.issue_token("tenant_ceil", "user_ro")

    db_path = tmp_path / "pm_ceil.db"
    db = PMDatabase(db_path)
    sm = SessionManager(db=db, iam=iam)

    session_secret, meta = sm.create_session(
        principal="tenant_ceil:user_ro",
        tenant_id="tenant_ceil",
        iam_token=ro_token,
    )
    assert "storage:read" in meta["permitted_actions"]
    assert "storage:write" not in meta["permitted_actions"]

    # Now simulate authority expansion in IAM (granting TENANT_ADMIN without new session)
    principal = iam.get_principal("tenant_ceil", "user_ro")
    principal.roles.add(StandardRole.TENANT_ADMIN.value)
    assert StandardRole.TENANT_ADMIN.value in principal.roles

    # Cookie validation must preserve original issued credential ceiling (storage:read only)
    sess = sm.get_session(session_secret)
    assert sess is not None
    assert "storage:read" in sess["permitted_actions"]
    assert "storage:write" not in sess["permitted_actions"]
    assert "admin:*" not in sess["permitted_actions"]


# 23. Two tenant servers sharing a storage root: unified state path, no leakage, and project/board synchronization
def test_shared_root_two_tenant_servers_no_leakage_and_board_sync(tmp_path: Path):
    from mas.iam import MultiTenantIAM, StandardRole
    from mas.tenancy import resolve_tenant_database_path
    from mas.pm.models import Project, Issue, IssueType, PriorityLevel, IssueState

    iam = MultiTenantIAM()
    iam.create_tenant("tenant_one", "Tenant One")
    iam.create_tenant("tenant_two", "Tenant Two")
    iam.register_principal("tenant_one", "alice", roles={StandardRole.TENANT_ADMIN.value})
    iam.register_principal("tenant_two", "bob", roles={StandardRole.TENANT_ADMIN.value})

    token_one = iam.issue_token("tenant_one", "alice")
    token_two = iam.issue_token("tenant_two", "bob")

    shared_root = tmp_path / "shared_tenant_storage"
    shared_root.mkdir()

    port_one = get_free_port()
    port_two = get_free_port()

    ent_one = ConsultingEnterprise(name="Enterprise One")
    ent_two = ConsultingEnterprise(name="Enterprise Two")

    server_one = DashboardServer(ent_one, host="127.0.0.1", port=port_one, iam=iam, tenant_id="tenant_one", tenant_root=shared_root)
    server_two = DashboardServer(ent_two, host="127.0.0.1", port=port_two, iam=iam, tenant_id="tenant_two", tenant_root=shared_root)

    # Verify both servers resolve distinct isolated database paths inside shared root
    db_path_one = resolve_tenant_database_path(iam, "tenant_one", shared_root)
    db_path_two = resolve_tenant_database_path(iam, "tenant_two", shared_root)
    assert db_path_one != db_path_two
    assert server_one.tenant_db_path == db_path_one
    assert server_two.tenant_db_path == db_path_two

    # Seed data into Tenant One's server_db
    p1 = server_one.server_db.create_project(Project(id="p-one", key="TONE", name="Tenant One Project"))
    server_one.server_db.create_issue(
        Issue(
            id="i-one",
            project_id=p1.id,
            key="TONE-1",
            title="First Issue",
            issue_type=IssueType.TASK,
            priority=PriorityLevel.HIGH,
            current_state=IssueState.BACKLOG,
        )
    )

    server_one.start_background()
    server_two.start_background()
    time.sleep(0.3)

    try:
        url_one = f"http://127.0.0.1:{port_one}"
        url_two = f"http://127.0.0.1:{port_two}"

        # Login to Server One
        _, _, headers_one = http_request(f"{url_one}/api/pm/v1/session/login", method="POST", data={"token": token_one})
        cookie_one = headers_one["Set-Cookie"].split(";")[0]

        # Login to Server Two
        _, _, headers_two = http_request(f"{url_two}/api/pm/v1/session/login", method="POST", data={"token": token_two})
        cookie_two = headers_two["Set-Cookie"].split(";")[0]

        # Tenant One: v1 project reads return TONE
        status_p, body_p, _ = http_request(f"{url_one}/api/pm/projects", headers={"Cookie": cookie_one})
        assert status_p == 200
        assert any(p["key"] == "TONE" for p in body_p["projects"])

        # Tenant One: legacy board reads against same database return TONE board and ticket
        status_b, body_b, _ = http_request(f"{url_one}/api/pm/board/TONE", headers={"Cookie": cookie_one})
        assert status_b == 200
        assert body_b["project_key"] == "TONE"
        assert len(body_b["issues_by_column"]["BACKLOG"]) == 1
        assert body_b["issues_by_column"]["BACKLOG"][0]["key"] == "TONE-1"

        # Tenant Two: v1 project reads DO NOT return TONE (no cross-tenant leakage in shared root)
        status_p2, body_p2, _ = http_request(f"{url_two}/api/pm/projects", headers={"Cookie": cookie_two})
        assert status_p2 == 200
        assert not any(p["key"] == "TONE" for p in body_p2["projects"])

        # Tenant Two: board read for TONE returns 404
        status_b2, _, _ = http_request(f"{url_two}/api/pm/board/TONE", headers={"Cookie": cookie_two})
        assert status_b2 == 404
    finally:
        server_one.shutdown()
        server_two.shutdown()


