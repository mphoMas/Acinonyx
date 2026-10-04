"""
mas.tools.executor: Sandboxed execution tools exposed via MCP.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
import re
import sys
from typing import Any, Optional

from mas.config import CONFIG
from mas.observability import METRICS


FORBIDDEN_IMPORT_PATTERNS = [
    r"\bimport\s+subprocess\b",
    r"\bfrom\s+subprocess\s+import\b",
    r"\bimport\s+socket\b",
    r"\bfrom\s+socket\s+import\b",
    r"\bimport\s+ctypes\b",
    r"\bfrom\s+ctypes\s+import\b",
    r"\b__import__\s*\(",
    r"\beval\s*\(",
    r"\bexec\s*\(",
]


def _sandbox_check(code: str) -> Optional[str]:
    if not CONFIG.sandbox_python:
        return None
    for pat in FORBIDDEN_IMPORT_PATTERNS:
        if re.search(pat, code):
            return f"ERROR: Sandbox denied pattern matching /{pat}/"
    return None


async def run_python_code(code: str, timeout_sec: float = 10.0) -> str:
    """
    Execute Python code in an isolated sub-process with timeout and sandbox checks.
    """
    denial = _sandbox_check(code)
    if denial:
        METRICS.incr("tools.run_python.denied")
        return denial

    capped = min(float(timeout_sec or CONFIG.max_python_timeout_sec), CONFIG.max_python_timeout_sec)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=capped)
        out_str = stdout.decode("utf-8", errors="replace")
        err_str = stderr.decode("utf-8", errors="replace")
        METRICS.incr("tools.run_python.calls")

        if proc.returncode != 0:
            return f"EXIT_FAILURE ({proc.returncode}):\nSTDERR:\n{err_str}\nSTDOUT:\n{out_str}"
        return out_str if out_str else "[Process finished with code 0, no output]"
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        METRICS.incr("tools.run_python.timeouts")
        return f"ERROR: Execution timed out after {capped} seconds."


def register_default_tools(registry: Any) -> None:
    """Register standard tools into an MCPRegistry instance."""
    registry.register_tool(
        name="run_python",
        description="Executes a Python 3 code snippet in a sandboxed subprocess.",
        input_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python 3 code string to execute"},
                "timeout_sec": {"type": "number", "description": "Maximum execution time in seconds", "default": 10.0},
            },
            "required": ["code"],
        },
        handler=run_python_code,
    )
