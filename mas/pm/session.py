"""
mas.pm.session: Authenticated browser session management and CSRF enforcement (SBA-05).

Provides:
- Opaque IAM-backed cookie sessions (mas_session) with token digests stored in SQLite.
- Session-bound CSRF token issuance and timing-safe validation.
- Idle timeout (30 min) and hard TTL (8 hr) enforcement.
- Chained revocation to underlying IAM sessions through public IAM validation.
- No bearer secret leakage; CSRF token distinct from session secret.
- Secure cookie issuance for deployed HTTPS with loopback development exception.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from http.cookies import SimpleCookie
import hmac
import json
import logging
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

from mas.pm.db import PMDatabase
from mas.pm.tools import get_pm_db

logger = logging.getLogger("mas.pm.session")

DEFAULT_SESSION_TTL = 28800  # 8 hours
DEFAULT_IDLE_TIMEOUT = 1800  # 30 minutes
SESSION_COOKIE_NAME = "mas_session"

ALL_PM_ACTIONS = [
    "storage:read",
    "storage:write",
    "tools:execute",
    "issues:create",
    "issues:transition",
    "verdicts:record",
]


class SessionManager:
    """Manages browser sessions, CSRF tokens, and IAM session validation."""

    def __init__(self, db: Optional[PMDatabase] = None, iam: Any = None) -> None:
        self._db = db
        self.iam = iam

    @property
    def db(self) -> PMDatabase:
        if self._db is None:
            self._db = get_pm_db()
        return self._db

    def create_session(
        self,
        principal: str,
        tenant_id: str = "default",
        permitted_actions: Optional[List[str]] = None,
        ttl_seconds: int = DEFAULT_SESSION_TTL,
        iam_token: Optional[str] = None,
        iam_session_id: Optional[str] = None,
        iam_token_hash: Optional[str] = None,
        iam_expires_at: Optional[float] = None,
        context: Optional[Any] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Creates a new opaque session without storing raw IAM bearer tokens in SQLite.
        Returns:
            (session_secret, session_metadata)
            where session_secret is the plaintext bearer cookie,
            and session_metadata contains csrf_token, principal, tenant_id, permitted_actions.
        """
        session_secret = secrets.token_hex(32)
        token_hash = hashlib.sha256(session_secret.encode("utf-8")).hexdigest()
        csrf_token = secrets.token_hex(32)
        now = time.time()
        now_iso = datetime.now(timezone.utc).isoformat()
        expires_at = now + ttl_seconds

        if context is None and iam_token and self.iam is not None:
            try:
                context = self.iam.verify_token(iam_token)
            except Exception:
                pass

        if context is not None:
            iam_session_id = getattr(context, "token_id", None) or iam_session_id
            iam_expires_at = getattr(context, "expires_at", None) or iam_expires_at

        if iam_token and not iam_token_hash:
            iam_token_hash = hashlib.sha256(iam_token.encode("utf-8")).hexdigest()

        issued_roles_json = None
        issued_scopes_json = None
        if context is not None:
            issued_roles_json = json.dumps(sorted(context.roles))
            issued_scopes_json = json.dumps(sorted(context.scopes))

        if context is not None and self.iam is not None and hasattr(self.iam, "get_permitted_actions"):
            actions = self.iam.get_permitted_actions(context, ALL_PM_ACTIONS)
        else:
            actions = permitted_actions or ALL_PM_ACTIONS

        conn = self.db._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO pm_sessions (
                        token_hash, csrf_token, principal, tenant_id, permitted_actions,
                        iam_token_hash, iam_session_id, iam_expires_at, created_at,
                        last_activity_at, expires_at, is_revoked,
                        issued_roles, issued_scopes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        token_hash,
                        csrf_token,
                        principal,
                        tenant_id,
                        json.dumps(actions),
                        iam_token_hash,
                        iam_session_id,
                        iam_expires_at,
                        now_iso,
                        now_iso,
                        expires_at,
                        issued_roles_json,
                        issued_scopes_json,
                    ),
                )
        finally:
            conn.close()

        metadata = {
            "principal": principal,
            "tenant_id": tenant_id,
            "permitted_actions": actions,
            "csrf_token": csrf_token,
            "expires_at": expires_at,
            "created_at": now_iso,
        }
        return session_secret, metadata

    def get_session(self, session_secret: str) -> Optional[Dict[str, Any]]:
        """
        Validates a session secret and returns its metadata.
        Verifies:
        1. Token hash exists and is_revoked == 0.
        2. Absolute expiration has not passed.
        3. Idle timeout (30 min) has not elapsed.
        4. Underlying IAM token/session validated through public IAM authority.
        """
        if not session_secret or not isinstance(session_secret, str):
            return None

        token_hash = hashlib.sha256(session_secret.encode("utf-8")).hexdigest()
        conn = self.db._get_connection()
        try:
            cur = conn.execute("SELECT * FROM pm_sessions WHERE token_hash = ?", (token_hash,))
            row = cur.fetchone()
            if not row:
                return None

            if row["is_revoked"]:
                return None

            now = time.time()
            if now > row["expires_at"]:
                return None

            # Idle timeout verification
            last_act_str = row["last_activity_at"]
            try:
                dt = datetime.fromisoformat(last_act_str)
                last_act = dt.timestamp()
            except Exception:
                last_act = now

            if now - last_act > DEFAULT_IDLE_TIMEOUT:
                return None

            # Public IAM-backed session check
            tenant_context = None
            iam_sid = row["iam_session_id"] if "iam_session_id" in row.keys() else None
            iam_token_hash = row["iam_token_hash"] if "iam_token_hash" in row.keys() else None
            iam_expires = row["iam_expires_at"] if "iam_expires_at" in row.keys() else None

            issued_roles = None
            if "issued_roles" in row.keys() and row["issued_roles"]:
                try:
                    issued_roles = json.loads(row["issued_roles"])
                except Exception:
                    pass

            issued_scopes = None
            if "issued_scopes" in row.keys() and row["issued_scopes"]:
                try:
                    issued_scopes = json.loads(row["issued_scopes"])
                except Exception:
                    pass

            if self.iam is not None and (iam_sid or iam_token_hash):
                user_id = row["principal"].split(":", 1)[1] if ":" in row["principal"] else row["principal"]
                tenant_id = row["tenant_id"]
                try:
                    if iam_sid and hasattr(self.iam, "validate_session"):
                        tenant_context = self.iam.validate_session(
                            tenant_id=tenant_id,
                            user_id=user_id,
                            session_id=iam_sid,
                            token_hash=iam_token_hash,
                            expires=iam_expires,
                            issued_roles=issued_roles,
                            issued_scopes=issued_scopes,
                        )
                    elif hasattr(self.iam, "_check_session") and iam_sid:
                        self.iam._check_session(tenant_id, user_id, iam_sid, iam_expires, iam_token_hash)
                    elif iam_token_hash and hasattr(self.iam, "_sessions"):
                        matched = False
                        for sess in self.iam._sessions.values():
                            if sess.get("token_hash") == iam_token_hash:
                                matched = True
                                if sess.get("revoked"):
                                    self.revoke_session(session_secret)
                                    return None
                                break
                        if not matched and self.iam._sessions:
                            self.revoke_session(session_secret)
                            return None
                except Exception as exc:
                    logger.info("IAM session validation failed (%s), revoking session", exc)
                    self.revoke_session(session_secret)
                    return None

            # Touch activity timestamp
            now_iso = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute(
                    "UPDATE pm_sessions SET last_activity_at = ? WHERE token_hash = ?",
                    (now_iso, token_hash),
                )

            actions = []
            if tenant_context is not None and hasattr(self.iam, "get_permitted_actions"):
                actions = self.iam.get_permitted_actions(tenant_context, ALL_PM_ACTIONS)
            else:
                try:
                    actions = json.loads(row["permitted_actions"])
                except Exception:
                    pass

            return {
                "principal": row["principal"],
                "tenant_id": row["tenant_id"],
                "permitted_actions": actions,
                "csrf_token": row["csrf_token"],
                "expires_at": row["expires_at"],
                "token_hash": token_hash,
                "tenant_context": tenant_context,
            }
        finally:
            conn.close()

    def revoke_session(self, session_secret: str) -> bool:
        """Revokes a session by secret."""
        if not session_secret:
            return False
        token_hash = hashlib.sha256(session_secret.encode("utf-8")).hexdigest()
        conn = self.db._get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE pm_sessions SET is_revoked = 1 WHERE token_hash = ?",
                    (token_hash,),
                )
                return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def verify_csrf(session_data: Optional[Dict[str, Any]], csrf_token_header: Optional[str]) -> bool:
        """Timing-safe CSRF validation."""
        if not session_data or not csrf_token_header:
            return False
        expected = session_data.get("csrf_token", "")
        if not expected:
            return False
        return hmac.compare_digest(str(expected), str(csrf_token_header))


# --- Cookie Helpers ---

def should_secure_cookie(host: str = "127.0.0.1", headers: Any = None) -> bool:
    """
    Returns True for deployed HTTPS cookies; False only for explicit loopback development.
    """
    if headers and hasattr(headers, "get"):
        proto = headers.get("X-Forwarded-Proto", "").strip().lower()
        if proto == "https":
            return True
    clean_host = host.split(":")[0].strip().lower()
    if clean_host in ("127.0.0.1", "localhost", "::1"):
        return False
    return True


def extract_session_cookie(headers: Any) -> Optional[str]:
    """Extracts mas_session cookie from request headers."""
    cookie_str = headers.get("Cookie") if hasattr(headers, "get") else None
    if not cookie_str:
        return None
    try:
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        if SESSION_COOKIE_NAME in cookie:
            return cookie[SESSION_COOKIE_NAME].value
    except Exception:
        pass
    return None


def make_session_cookie(
    session_secret: str,
    secure: Optional[bool] = None,
    max_age: int = DEFAULT_SESSION_TTL,
    host: str = "127.0.0.1",
    headers: Any = None,
) -> str:
    """Constructs Set-Cookie header string for mas_session."""
    is_sec = secure if secure is not None else should_secure_cookie(host=host, headers=headers)
    sec = "; Secure" if is_sec else ""
    return f"{SESSION_COOKIE_NAME}={session_secret}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}{sec}"


def make_clear_session_cookie(
    secure: Optional[bool] = None,
    host: str = "127.0.0.1",
    headers: Any = None,
) -> str:
    """Constructs Set-Cookie header string to clear mas_session."""
    is_sec = secure if secure is not None else should_secure_cookie(host=host, headers=headers)
    sec = "; Secure" if is_sec else ""
    return f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{sec}"
