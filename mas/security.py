"""
mas.security: Tool ACLs, prompt-injection filters, and agent identity helpers.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set



INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.I),
    re.compile(r"jailbreak", re.I),
    re.compile(r"system\s*prompt\s*override", re.I),
    re.compile(r"<\s*/?\s*system\s*>", re.I),
    re.compile(r"exfiltrate|send\s+secrets|api[_-]?key", re.I),
]


@dataclass
class ToolACL:
    """Principal → allowed tool name set. Empty allowlist means deny-all when enforced."""

    default_allow: Set[str] = field(default_factory=set)
    principals: Dict[str, Set[str]] = field(default_factory=dict)

    def allow(self, principal: str, tools: List[str]) -> None:
        self.principals.setdefault(principal, set()).update(tools)

    def is_allowed(self, principal: Optional[str], tool_name: str) -> bool:
        if principal and principal in self.principals:
            return tool_name in self.principals[principal]
        return tool_name in self.default_allow


DEFAULT_SAFE_TOOLS = {
    "fs_read",
    "fs_list",
    "fs_glob",
    "git_status",
    "git_diff",
    "git_log",
    "pm_get_board_state",
    "pm_get_issue",
    "pm_list_issues",
}


def default_tool_acl() -> ToolACL:
    acl = ToolACL(default_allow=set(DEFAULT_SAFE_TOOLS))
    return acl


def sanitize_tool_arguments(arguments: Dict) -> Dict:
    """Redact obvious secrets and block classic injection strings in tool args."""
    cleaned: Dict = {}
    for key, value in (arguments or {}).items():
        if isinstance(value, str):
            for pat in INJECTION_PATTERNS:
                if pat.search(value):
                    raise PermissionError(
                        f"Blocked potential prompt-injection in tool argument '{key}'"
                    )
            if any(s in key.lower() for s in ("password", "secret", "token", "api_key")):
                cleaned[key] = "***REDACTED***"
            else:
                cleaned[key] = value
        else:
            cleaned[key] = value
    return cleaned


def filter_user_text(text: str) -> str:
    """Soft-filter user/tool text; raises on hard jailbreak attempts."""
    for pat in INJECTION_PATTERNS[:3]:
        if pat.search(text or ""):
            raise PermissionError("Blocked prompt-injection pattern in input text")
    return text


_current_principal: ContextVar[Optional[str]] = ContextVar("current_principal", default=None)


class ExecutionContext:
    """Thread-safe and task-safe execution context tracking authenticated principal."""

    @staticmethod
    def get_current_principal() -> Optional[str]:
        return _current_principal.get()

    @staticmethod
    def set_current_principal(principal: Optional[str]) -> None:
        _current_principal.set(principal)

    @classmethod
    @contextmanager
    def scope(cls, principal: str):
        token = _current_principal.set(principal)
        try:
            yield
        finally:
            _current_principal.reset(token)

    @staticmethod
    def resolve_authenticated_principal(claimed_principal: Optional[str] = None) -> str:
        """
        PM-SEC-001 & SEC-05: Derives authenticated principal and prohibits caller-supplied identity impersonation.
        Fails closed: Unverified callers (when no authenticated context exists) are strictly rejected.
        """
        current = ExecutionContext.get_current_principal()
        if not current:
            raise PermissionError("Unauthenticated operation: Execution context lacks a verified principal.")
        if claimed_principal and claimed_principal != current:
            raise PermissionError(
                f"ImpersonationAttemptError: Authenticated principal '{current}' cannot claim identity '{claimed_principal}'"
            )
        return current


def validate_reviewer_authorization(
    issue_key: str,
    author_principal: str,
    reviewer_principal: str,
    authenticated_principal: Optional[str] = None,
) -> None:
    """
    SEC-02 & SEC-05: Enforces reviewer authorization, separation of builder from reviewer,
    and verified reviewer identity.
    """
    if not reviewer_principal or not reviewer_principal.strip():
        raise PermissionError(f"Reviewer authorization failed for {issue_key}: missing reviewer principal.")
    if author_principal == reviewer_principal:
        raise PermissionError(
            f"Separation of duties violation for {issue_key}: author '{author_principal}' cannot review their own work."
        )
    if authenticated_principal and authenticated_principal != reviewer_principal:
        raise PermissionError(
            f"UnauthorizedReviewerError: Authenticated principal '{authenticated_principal}' is not authorized to act as reviewer '{reviewer_principal}' for {issue_key}."
        )


DEFAULT_VERDICT_SECRET = "acinonyx_verdict_signing_secret_v1_2026"


def sign_verdict_payload(
    issue_id: str,
    reviewer_principal: str,
    verdict_value: str,
    rework_cycle: int,
    commit_sha: Optional[str] = None,
    findings: Optional[Dict[str, Any]] = None,
    secret_key: Optional[str] = None,
) -> str:
    """
    GOV-02: Cryptographically signs a reviewer decision record with HMAC-SHA256.
    """
    import hashlib
    import hmac
    import json
    import os

    findings_json = json.dumps(findings or {}, sort_keys=True)
    payload = f"{issue_id}:{reviewer_principal}:{verdict_value}:{rework_cycle}:{commit_sha or ''}:{findings_json}"
    key = (secret_key or os.getenv("MAS_VERDICT_SECRET") or DEFAULT_VERDICT_SECRET).encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_verdict_signature(
    issue_id: str,
    reviewer_principal: str,
    verdict_value: str,
    rework_cycle: int,
    signature: str,
    commit_sha: Optional[str] = None,
    findings: Optional[Dict[str, Any]] = None,
    secret_key: Optional[str] = None,
) -> bool:
    """
    GOV-02: Verifies that a reviewer verdict decision record has not been forged or tampered with.
    """
    import hmac

    if not signature or not signature.strip():
        return False
    expected = sign_verdict_payload(
        issue_id=issue_id,
        reviewer_principal=reviewer_principal,
        verdict_value=verdict_value,
        rework_cycle=rework_cycle,
        commit_sha=commit_sha,
        findings=findings,
        secret_key=secret_key,
    )
    return hmac.compare_digest(expected, signature.strip())

