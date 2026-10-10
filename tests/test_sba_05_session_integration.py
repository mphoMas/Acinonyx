"""
Integration tests for SBA-05 session requirements and SBA_01_DECISIONS contract.

Covers:
1. GET /api/pm/v1/session unauthenticated returns 401 with Cache-Control: no-store.
2. POST /api/pm/v1/session/login establishes cookie session, returns csrf_token, sets Cache-Control: no-store.
3. GET /api/pm/v1/session with cookie returns 200, matching csrf_token and Cache-Control: no-store.
4. Mutation with cookie and valid X-CSRF-Token succeeds; server resolves actor.
5. Mutation with cookie and missing X-CSRF-Token returns 403 Forbidden.
6. Mutation with cookie and invalid/tampered X-CSRF-Token returns 403 Forbidden.
7. Caller impersonation attempt (claimed caller_principal != session principal) returns 403.
8. Logout revokes session server-side, clears cookie, and subsequent session requests return 401.
9. Bearer token authentication succeeds without requiring CSRF token.
10. No silent fallback: invalid Bearer token with valid cookie returns 401, never falls back to cookie.
11. Idle timeout: session older than 30 minutes without activity is rejected.
12. IAM revocation chaining: revoking underlying IAM token revokes linked cookie session.
13. Static /portal/ file serving serves files safely with nosniff header and rejects traversal.
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
from mas.pm.session import SessionManager, extract_session_cookie
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
    """Launches an isolated DashboardServer instance."""
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
        "principal": "operator_jane",
        "tenant_id": "tenant-alpha",
    }
    status, body, headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data=login_payload,
    )
    assert status == 200
    assert body["success"] is True
    assert body["principal"] == "operator_jane"
    assert body["tenant_id"] == "tenant-alpha"
    assert "csrf_token" in body
    assert len(body["csrf_token"]) == 64
    assert headers.get("Cache-Control") == "no-store"
    assert "Set-Cookie" in headers
    assert "mas_session=" in headers["Set-Cookie"]
    assert "HttpOnly" in headers["Set-Cookie"]


# 3. GET /api/pm/v1/session with cookie returns 200, matching csrf_token and Cache-Control: no-store
def test_get_session_with_valid_cookie(dashboard_server):
    base_url, _ = dashboard_server
    # Log in first
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "principal": "operator_jane"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]

    # Fetch session
    status, body, headers = http_request(
        f"{base_url}/api/pm/v1/session",
        headers={"Cookie": cookie},
    )
    assert status == 200
    assert body["principal"] == "operator_jane"
    assert body["csrf_token"] == login_body["csrf_token"]
    assert headers.get("Cache-Control") == "no-store"


# 4. Mutation with cookie and valid X-CSRF-Token succeeds; server resolves actor
def test_mutation_with_cookie_and_csrf_succeeds(dashboard_server):
    base_url, _ = dashboard_server
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "principal": "operator_jane"},
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


# 5. Mutation with cookie and missing X-CSRF-Token returns 403 Forbidden
def test_mutation_missing_csrf_returns_403(dashboard_server):
    base_url, _ = dashboard_server
    _, _, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "principal": "operator_jane"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]

    create_payload = {
        "project_key": "SESS",
        "title": "Should be rejected without CSRF",
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/issues/create",
        method="POST",
        headers={"Cookie": cookie},  # No X-CSRF-Token header
        data=create_payload,
    )
    assert status == 403
    assert "CSRF token missing" in body["error"]


# 6. Mutation with cookie and invalid/tampered X-CSRF-Token returns 403 Forbidden
def test_mutation_invalid_csrf_returns_403(dashboard_server):
    base_url, _ = dashboard_server
    _, _, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "principal": "operator_jane"},
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


# 7. Caller impersonation attempt returns 403 Forbidden
def test_caller_impersonation_returns_403(dashboard_server):
    base_url, _ = dashboard_server
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "principal": "real_operator"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]
    csrf_token = login_body["csrf_token"]

    # First create an issue
    _, create_res, _ = http_request(
        f"{base_url}/api/pm/issues/create",
        method="POST",
        headers={"Cookie": cookie, "X-CSRF-Token": csrf_token},
        data={"project_key": "SESS", "title": "Transition check"},
    )
    issue_key = create_res["result"]["issue_key"]

    # Transition attempting to claim a forged caller_principal
    transition_payload = {
        "issue_key": issue_key,
        "target_state": "REFINED",
        "caller_principal": "forged_admin_founder",  # Mismatch against session!
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/transition",
        method="POST",
        headers={"Cookie": cookie, "X-CSRF-Token": csrf_token},
        data=transition_payload,
    )
    assert status == 403
    assert "Caller identity must match" in body["error"]


# 8. Logout revokes session, clears cookie, subsequent requests 401
def test_logout_revokes_session_and_clears_cookie(dashboard_server):
    base_url, _ = dashboard_server
    _, _, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "principal": "operator_jane"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]

    # Logout
    status, body, logout_headers = http_request(
        f"{base_url}/api/pm/v1/session/logout",
        method="POST",
        headers={"Cookie": cookie},
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


# 9. Bearer token authentication succeeds without requiring CSRF token
def test_bearer_token_authentication_succeeds_without_csrf(dashboard_server):
    base_url, _ = dashboard_server
    bearer_headers = {"Authorization": "Bearer test-secret-bearer-token"}

    # Session read
    status, body, headers = http_request(
        f"{base_url}/api/pm/v1/session",
        headers=bearer_headers,
    )
    assert status == 200
    assert "csrf_token" in body
    assert headers.get("Cache-Control") == "no-store"

    # Mutation with Bearer token does NOT require X-CSRF-Token header
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


# 10. No silent fallback: invalid Bearer token with valid cookie returns 401 immediately
def test_invalid_bearer_does_not_fall_back_to_cookie(dashboard_server):
    base_url, _ = dashboard_server
    _, login_body, login_headers = http_request(
        f"{base_url}/api/pm/v1/session/login",
        method="POST",
        data={"token": "test-secret-bearer-token", "principal": "operator_jane"},
    )
    cookie = login_headers["Set-Cookie"].split(";")[0]
    csrf_token = login_body["csrf_token"]

    # Present an INVALID Bearer token alongside the VALID cookie
    conflicting_headers = {
        "Authorization": "Bearer INVALID_EXPIRED_TOKEN_123",
        "Cookie": cookie,
        "X-CSRF-Token": csrf_token,
    }
    status, body, _ = http_request(
        f"{base_url}/api/pm/v1/session",
        headers=conflicting_headers,
    )
    # Must reject with 401 and NEVER fall back to inspecting cookie!
    assert status == 401
    assert "Invalid bearer token" in body["error"]["message"]


# 11. Idle timeout: session older than 30 minutes without activity is rejected
def test_session_idle_timeout_rejection():
    db = get_pm_db()
    sm = SessionManager(db=db)
    secret, meta = sm.create_session("idle_operator")

    # Manually backdate last_activity_at in DB by 31 minutes
    token_hash = meta.get("token_hash") or sm.get_session(secret)["token_hash"]
    conn = db._get_connection()
    try:
        from datetime import datetime, timezone, timedelta
        past = (datetime.now(timezone.utc) - timedelta(minutes=31)).isoformat()
        with conn:
            conn.execute("UPDATE pm_sessions SET last_activity_at = ? WHERE token_hash = ?", (past, token_hash))
    finally:
        conn.close()

    # Querying the session now must return None due to idle timeout
    assert sm.get_session(secret) is None


# 12. IAM revocation chaining
def test_iam_revocation_chaining(tmp_path):
    from mas.iam import MultiTenantIAM, StandardRole
    iam = MultiTenantIAM()
    iam.create_tenant("chain_tenant", "Chain Tenant")
    iam.register_principal("chain_tenant", "operator_1", roles={StandardRole.TENANT_ADMIN.value})
    iam_token = iam.issue_token("chain_tenant", "operator_1")

    db = get_pm_db()
    sm = SessionManager(db=db, iam=iam)
    secret, _ = sm.create_session("chain_tenant:operator_1", tenant_id="chain_tenant", iam_token=iam_token)

    # Initially valid
    sess = sm.get_session(secret)
    assert sess is not None

    # Revoke IAM session
    iam.revoke_principal_sessions(iam_token, "operator_1")

    # Linked cookie session must now be rejected
    assert sm.get_session(secret) is None


# 13. Static /portal/ file serving serves files safely with nosniff and rejects traversal
def test_portal_file_serving_and_traversal_prevention(dashboard_server):
    base_url, _ = dashboard_server
    req = urllib.request.Request(f"{base_url}/portal/scrum.html")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        assert "text/html" in resp.headers.get("Content-Type", "")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        content = resp.read().decode("utf-8")
        assert "Mission Control" in content

    # Traversal escape rejected
    traversal_req = urllib.request.Request(f"{base_url}/portal/../../mas/pm/models.py")
    try:
        with urllib.request.urlopen(traversal_req, timeout=5) as resp:
            # Should not serve as a portal file
            assert resp.status in (403, 404)
    except urllib.error.HTTPError as err:
        assert err.code in (403, 404)
