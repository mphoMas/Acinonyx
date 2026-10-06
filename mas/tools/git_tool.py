"""
mas.tools.git_tool: Git version control tools for autonomous engineering squads.
Provides branch management, commits, diffs, and repository status via MCP.

Architect: Acinonyx
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional
from mas.config import REPO_ROOT
from mas.mcp.protocol import MCPRegistry


GIT_BIN = f"{REPO_ROOT}/bin/git" if os.path.exists(f"{REPO_ROOT}/bin/git") else "git"
GIT_ENV = {
    **os.environ,
    "PATH": f"{REPO_ROOT}/bin:{os.environ.get('PATH', '')}",
    "GIT_EXEC_PATH": f"{REPO_ROOT}/bin/lib/git-core",
    "GIT_TEMPLATE_DIR": f"{REPO_ROOT}/bin/share/git-core/templates",
}


def _run_git(args: List[str], cwd: str) -> tuple[int, str, str]:
    """Execute git command with proper environment."""
    try:
        proc = subprocess.run(
            [GIT_BIN] + args,
            cwd=cwd,
            env=GIT_ENV,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


async def git_init_tool(repo_path: str = ".") -> Dict[str, Any]:
    """Initialize a new git repository."""
    os.makedirs(repo_path, exist_ok=True)
    code, out, err = _run_git(["init"], cwd=repo_path)
    if code == 0:
        # Set default user config if not present
        _run_git(["config", "user.name", "Acinonyx Agent"], cwd=repo_path)
        _run_git(["config", "user.email", "agent@acinonyx.ai"], cwd=repo_path)
        return {"success": True, "output": out or "Initialized empty Git repository."}
    return {"success": False, "error": err or out}


async def git_status_tool(repo_path: str = ".") -> Dict[str, Any]:
    """Get the current working tree status and branch."""
    code, out, err = _run_git(["status", "--short", "--branch"], cwd=repo_path)
    if code == 0:
        return {"success": True, "status": out}
    return {"success": False, "error": err or out}


async def git_add_tool(repo_path: str = ".", files: Optional[List[str]] = None) -> Dict[str, Any]:
    """Stage files for commit."""
    targets = files if files else ["."]
    code, out, err = _run_git(["add"] + targets, cwd=repo_path)
    if code == 0:
        return {"success": True, "staged": targets}
    return {"success": False, "error": err or out}


async def git_commit_tool(
    repo_path: str = ".",
    message: str = "Update code",
    author_name: str = "Acinonyx Agent",
    author_email: str = "agent@acinonyx.ai",
) -> Dict[str, Any]:
    """Commit staged changes."""
    env_args = [
        "-c", f"user.name={author_name}",
        "-c", f"user.email={author_email}",
        "commit", "-m", message
    ]
    code, out, err = _run_git(env_args, cwd=repo_path)
    if code == 0:
        return {"success": True, "output": out}
    return {"success": False, "error": err or out}


async def git_branch_tool(
    repo_path: str = ".",
    branch_name: str = "",
    checkout: bool = True,
) -> Dict[str, Any]:
    """Create a new branch and optionally check it out."""
    if not branch_name:
        # List branches
        code, out, err = _run_git(["branch", "-a"], cwd=repo_path)
        if code == 0:
            branches = [b.strip() for b in out.splitlines() if b.strip()]
            return {"success": True, "branches": branches}
        return {"success": False, "error": err}

    cmd = ["checkout", "-b", branch_name] if checkout else ["branch", branch_name]
    code, out, err = _run_git(cmd, cwd=repo_path)
    if code == 0:
        return {"success": True, "branch": branch_name, "checked_out": checkout, "output": out}
    return {"success": False, "error": err or out}


async def git_checkout_tool(repo_path: str = ".", branch_name: str = "main") -> Dict[str, Any]:
    """Switch to an existing branch."""
    code, out, err = _run_git(["checkout", branch_name], cwd=repo_path)
    if code == 0:
        return {"success": True, "branch": branch_name, "output": out}
    return {"success": False, "error": err or out}


async def git_diff_tool(repo_path: str = ".", staged: bool = False) -> Dict[str, Any]:
    """Show changes between commits, commit and working tree, etc."""
    cmd = ["diff", "--cached"] if staged else ["diff"]
    code, out, err = _run_git(cmd, cwd=repo_path)
    if code == 0:
        return {"success": True, "diff": out}
    return {"success": False, "error": err or out}


async def git_log_tool(repo_path: str = ".", max_count: int = 10) -> Dict[str, Any]:
    """Show commit logs."""
    code, out, err = _run_git(["log", f"-n{max_count}", "--oneline", "--decorate"], cwd=repo_path)
    if code == 0:
        commits = [line for line in out.splitlines() if line.strip()]
        return {"success": True, "commits": commits}
    return {"success": False, "error": err or out}


def register_git_tools(registry: MCPRegistry) -> None:
    """Register all git tools into an MCP registry."""
    registry.register_tool(
        name="git_init",
        description="Initialize a new Git repository at the specified directory path.",
        input_schema={
            "type": "object",
            "properties": {"repo_path": {"type": "string", "default": "."}},
        },
        handler=git_init_tool,
    )

    registry.register_tool(
        name="git_status",
        description="Get the Git status (branch and modified files) of a repository.",
        input_schema={
            "type": "object",
            "properties": {"repo_path": {"type": "string", "default": "."}},
        },
        handler=git_status_tool,
    )

    registry.register_tool(
        name="git_add",
        description="Stage files for Git commit.",
        input_schema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "default": "."},
                "files": {"type": "array", "items": {"type": "string"}},
            },
        },
        handler=git_add_tool,
    )

    registry.register_tool(
        name="git_commit",
        description="Commit staged files with a message and author info.",
        input_schema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "default": "."},
                "message": {"type": "string"},
                "author_name": {"type": "string", "default": "Acinonyx Agent"},
                "author_email": {"type": "string", "default": "agent@acinonyx.ai"},
            },
            "required": ["message"],
        },
        handler=git_commit_tool,
    )

    registry.register_tool(
        name="git_branch",
        description="Create a new Git branch and optionally check it out, or list existing branches.",
        input_schema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "default": "."},
                "branch_name": {"type": "string"},
                "checkout": {"type": "boolean", "default": True},
            },
        },
        handler=git_branch_tool,
    )

    registry.register_tool(
        name="git_checkout",
        description="Checkout an existing Git branch.",
        input_schema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "default": "."},
                "branch_name": {"type": "string"},
            },
            "required": ["branch_name"],
        },
        handler=git_checkout_tool,
    )

    registry.register_tool(
        name="git_diff",
        description="View git diff of unstaged or staged changes.",
        input_schema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "default": "."},
                "staged": {"type": "boolean", "default": False},
            },
        },
        handler=git_diff_tool,
    )

    registry.register_tool(
        name="git_log",
        description="Retrieve recent git commit history.",
        input_schema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "default": "."},
                "max_count": {"type": "integer", "default": 10},
            },
        },
        handler=git_log_tool,
    )
