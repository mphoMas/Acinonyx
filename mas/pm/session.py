"""
mas.pm.session: Authenticated browser session management and CSRF enforcement (SBA-05).

Provides:
- Opaque IAM-backed cookie sessions (mas_session) with token digests stored in SQLite.
- Session-bound CSRF token issuance and timing-safe validation.
- Idle timeout (30 min) and hard TTL (8 hr) enforcement.
- Chained revocation to underlying IAM sessions.
- No bearer secret leakage; CSRF token distinct from session secret.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from http.cookies import SimpleCookie
import hmac
import json
import logging
from pathlib import Path
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

from mas.pm.db import PMDatabase
from mas.pm.tools import get_pm_db

logger = logging.getLogger("mas.pm.session")

DEFAULT_SESSION_TTL = 28800  # 8 hours
DEFAULT_IDLE_TIMEOUT = 1800  # 30 minutes
SESSION_COOKIE_NAME = "mas_session"


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
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Creates a new opaque session.
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

        actions = permitted_actions or [
            "storage:read",
            "storage:write",
            "tools:execute",
            "issues:create",
            "issues:transition",
            "verdicts:record",
        ]

        iam_token_hash = None
        if iam_token:
            iam_token_hash = hashlib.sha256(iam_token.encode("utf-8")).hexdigest()

        conn = self.db._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO pm_sessions (
                        token_hash, csrf_token, principal, tenant_id, permitted_actions,
                        iam_token_hash, created_at, last_activity_at, expires_at, is_revoked
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        token_hash,
                        csrf_token,
                        principal,
                        tenant_id,
                        json.dumps(actions),
                        iam_token_hash,
                        now_iso,
                        now_iso,
                        expires_at,
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
        4. Underlying IAM token (if linked) remains unrevoked.
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
                # ISO datetime to timestamp
                dt = datetime.fromisoformat(last_act_str)
                last_act = dt.timestamp()
            except Exception:
                last_act = now

            if now - last_act > DEFAULT_IDLE_TIMEOUT:
                return None

            # IAM underlying session check
            iam_token_hash = row["iam_token_hash"]
            if iam_token_hash and self.iam is not None:
                # If IAM has store or in-memory sessions, check if revoked
                if hasattr(self.iam, "_store") and self.iam._store:
                    session_rec = self.iam._store.get_session(iam_token_hash)
                    if not session_rec or session_rec.get("revoked"):
                        self.revoke_session(session_secret)
                        return None
                elif hasattr(self.iam, "_sessions"):
                    # Check in-memory IAM sessions
                    matched = False
                    for sess in self.iam._sessions.values():
                        if sess.get("token_hash") == iam_token_hash:
                            matched = True
                            if sess.get("revoked"):
                                self.revoke_session(session_secret)
                                return None
                            break
                    # If token was issued by IAM but not found or revoked
                    if not matched and self.iam._sessions:
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

    def revoke_principal_sessions(self, principal: str) -> int:
        """Revokes all sessions for a principal."""
        conn = self.db._get_connection()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE pm_sessions SET is_revoked = 1 WHERE principal = ?",
                    (principal,),
                )
                return cur.rowcount
        finally:
            conn.close()

    @staticmethod
    def verify_csrf(session_data: Dict[str, Any], csrf_token_header: Optional[str]) -> bool:
        """Timing-safe comparison between expected session csrf_token and header value."""
        if not csrf_token_header or not session_data:
            return False
        expected = session_data.get("csrf_token", "")
        if not expected:
            return False
        return hmac.compare_digest(str(expected), str(csrf_token_header))


# --- Cookie Helpers ---

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


def make_session_cookie(session_secret: str, secure: bool = False, max_age: int = DEFAULT_SESSION_TTL) -> str:
    """Constructs Set-Cookie header string for mas_session."""
    sec = "; Secure" if secure else ""
    return f"{SESSION_COOKIE_NAME}={session_secret}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}{sec}"


def make_clear_session_cookie(secure: bool = False) -> str:
    """Constructs Set-Cookie header string to clear mas_session."""
    sec = "; Secure" if secure else ""
    return f"{SESSION_COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0{sec}"
