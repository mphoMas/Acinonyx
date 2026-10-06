"""
mas.tools.package_tool: UV package management and isolated virtualenv execution for MAS agents.
Architect: Acinonyx
"""

from __future__ import annotations

import os
import subprocess
from typing import Any, Dict, List, Optional
from mas.config import REPO_ROOT
from mas.mcp.protocol import MCPRegistry


UV_BIN = f"{REPO_ROOT}/bin/uv" if os.path.exists(f"{REPO_ROOT}/bin/uv") else "uv"


def _run_uv(args: List[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            [UV_BIN] + args,
            cwd=cwd or f"{REPO_ROOT}",
            capture_output=True,
            text=True,
            timeout=120,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


async def uv_pip_install_tool(
    packages: List[str],
    venv_path: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Install Python packages using UV."""
    args = ["pip", "install"] + packages
    if venv_path:
        args += ["--python", venv_path]
    if extra_args:
        args += extra_args

    code, out, err = _run_uv(args)
    if code == 0:
        return {"success": True, "packages": packages, "output": out or "Installation completed."}
    return {"success": False, "error": err or out}


async def uv_pip_list_tool(venv_path: Optional[str] = None) -> Dict[str, Any]:
    """List installed packages using UV."""
    args = ["pip", "list"]
    if venv_path:
        args += ["--python", venv_path]

    code, out, err = _run_uv(args)
    if code == 0:
        return {"success": True, "installed": out}
    return {"success": False, "error": err or out}


async def uv_venv_create_tool(
    destination: str = ".venv",
    python_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an isolated virtual environment using UV."""
    args = ["venv", destination]
    if python_version:
        args += ["--python", python_version]

    code, out, err = _run_uv(args)
    if code == 0:
        return {"success": True, "venv_path": destination, "output": out or f"Virtualenv created at {destination}"}
    return {"success": False, "error": err or out}


def register_package_tools(registry: MCPRegistry) -> None:
    """Register UV package management tools into an MCP registry."""
    registry.register_tool(
        name="uv_pip_install",
        description="Install Python dependencies using ultra-fast UV package manager.",
        input_schema={
            "type": "object",
            "properties": {
                "packages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of package names and specs (e.g. ['requests', 'fastapi>=0.100'])",
                },
                "venv_path": {
                    "type": "string",
                    "description": "Optional path to target virtualenv python",
                },
            },
            "required": ["packages"],
        },
        handler=uv_pip_install_tool,
    )

    registry.register_tool(
        name="uv_pip_list",
        description="List all installed Python packages in current or specified environment.",
        input_schema={
            "type": "object",
            "properties": {
                "venv_path": {"type": "string", "description": "Optional virtualenv path"},
            },
        },
        handler=uv_pip_list_tool,
    )

    registry.register_tool(
        name="uv_venv_create",
        description="Create an isolated virtual environment using UV.",
        input_schema={
            "type": "object",
            "properties": {
                "destination": {"type": "string", "default": ".venv"},
                "python_version": {"type": "string"},
            },
        },
        handler=uv_venv_create_tool,
    )
