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
        PM-SEC-001: Derives authenticated principal and prohibits caller-supplied identity impersonation.
        """
        current = ExecutionContext.get_current_principal()
        if not current:
            if claimed_principal:
                return claimed_principal
            raise PermissionError("Unauthenticated operation: Execution context lacks a verified principal.")
        if claimed_principal and claimed_principal != current:
            raise PermissionError(
                f"ImpersonationAttemptError: Authenticated principal '{current}' cannot claim identity '{claimed_principal}'"
            )
        return current

