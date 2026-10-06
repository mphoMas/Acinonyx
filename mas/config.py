"""
mas.config: Central runtime configuration and capability wiring.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Repository root, overridable via MAS_WORKSPACE (keeps the package portable across hosts / CI).
REPO_ROOT = Path(os.environ.get("MAS_WORKSPACE") or Path(__file__).resolve().parents[1])


@dataclass
class RuntimeConfig:
    """Single source of truth for MAS runtime behaviour."""

    workspace_root: Path = field(default_factory=lambda: REPO_ROOT)
    audit_log_path: Path = field(
        default_factory=lambda: REPO_ROOT / "workspace" / "audit" / "events.jsonl"
    )
    require_llm: bool = False
    allow_mock_provider: bool = True
    live_dispatch: bool = False
    tool_acl_enabled: bool = True
    sandbox_python: bool = True
    max_python_timeout_sec: float = 10.0
    mission_token_budget: int = 250_000
    default_subtask_timeout_sec: float = 30.0
    default_subtask_retries: int = 1
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None
    allowed_project_roots: List[str] = field(default_factory=list)
    version: str = "0.2.0"

    @classmethod
    def from_env(cls, workspace_root: Optional[str | Path] = None) -> "RuntimeConfig":
        root = Path(workspace_root or os.environ.get("MAS_WORKSPACE", str(REPO_ROOT)))
        audit = Path(os.environ.get("MAS_AUDIT_LOG", str(root / "workspace" / "audit" / "events.jsonl")))
        roots_raw = os.environ.get("MAS_ALLOWED_ROOTS", "")
        roots = [r.strip() for r in roots_raw.split(":") if r.strip()] or [
            str(root),
            "/srv/mas-projects",
            "/tmp",
        ]
        return cls(
            workspace_root=root,
            audit_log_path=audit,
            require_llm=_env_bool("MAS_REQUIRE_LLM", False),
            allow_mock_provider=_env_bool("MAS_ALLOW_MOCK_PROVIDER", True),
            live_dispatch=_env_bool("MAS_ENABLE_LIVE_DISPATCH", False),
            tool_acl_enabled=_env_bool("MAS_TOOL_ACL", True),
            sandbox_python=_env_bool("MAS_SANDBOX_PYTHON", True),
            max_python_timeout_sec=_env_float("MAS_PYTHON_TIMEOUT", 10.0),
            mission_token_budget=_env_int("MAS_TOKEN_BUDGET", 250_000),
            default_subtask_timeout_sec=_env_float("MAS_SUBTASK_TIMEOUT", 30.0),
            default_subtask_retries=_env_int("MAS_SUBTASK_RETRIES", 1),
            llm_base_url=os.environ.get("MAS_LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL"),
            llm_model=os.environ.get("MAS_LLM_MODEL") or os.environ.get("OPENAI_MODEL"),
            llm_api_key=os.environ.get("MAS_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
            allowed_project_roots=roots,
        )


# Process-wide default; callers may replace via configure().
CONFIG = RuntimeConfig.from_env()


def configure(config: Optional[RuntimeConfig] = None) -> RuntimeConfig:
    """Replace or refresh the process-wide config."""
    global CONFIG
    CONFIG = config or RuntimeConfig.from_env()
    return CONFIG
