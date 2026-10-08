"""
mas.tools.executor: Sandboxed execution tools exposed via MCP.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
import os
import re
import math
import shutil
import signal
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def _build_command_and_env(code: str) -> tuple[List[str], Dict[str, str]]:
    """Build isolated execution command and stripped environment."""
    bwrap_path = shutil.which("bwrap") if CONFIG.sandbox_python else None
    safe_env = {
        "PATH": "/usr/bin:/bin:" + os.path.dirname(sys.executable),
        "LANG": "C.UTF-8",
        "PYTHONUNBUFFERED": "1",
    }

    if CONFIG.sandbox_python and not bwrap_path:
        raise RuntimeError("Sandbox unavailable: bubblewrap is required; host execution refused")

    if bwrap_path:
        py_prefix = sys.prefix
        cmd = [
            bwrap_path,
            "--ro-bind", "/usr", "/usr",
            "--ro-bind-try", "/lib", "/lib",
            "--ro-bind-try", "/lib64", "/lib64",
            "--ro-bind-try", "/bin", "/bin",
            "--ro-bind-try", py_prefix, py_prefix,
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
        ]
        # Virtualenv interpreters may be symlinks into a runtime outside /usr.
        for runtime in {sys.base_prefix, str(Path(sys.executable).resolve().parent.parent)}:
            if runtime != py_prefix and not Path(runtime).is_relative_to("/usr"):
                cmd.extend(["--ro-bind", runtime, runtime])
        from mas.tools.filesystem import ALLOWED_PROJECT_ROOTS
        for root in ALLOWED_PROJECT_ROOTS:
            root_str = str(root)
            if os.path.exists(root_str):
                cmd.extend(["--bind-try", root_str, root_str])

        cmd.extend([
            "--unshare-all",
            "--clearenv",
            "--die-with-parent",
            "--setenv", "LANG", "C.UTF-8",
            "--setenv", "PYTHONUNBUFFERED", "1",
            sys.executable,
            "-c",
            code,
        ])
        return cmd, safe_env

    # Fallback to direct subprocess with stripped environment
    cmd = [sys.executable, "-c", code]
    return cmd, safe_env


def _preexec_limits() -> None:
    """Set process session group and resource limits."""
    os.setsid()
    try:
        import resource
        # Limit CPU time (seconds)
        resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
        # Limit address space / memory (512MB)
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        # Limit open file descriptors
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    except (ImportError, OSError, ValueError):
        raise


async def run_python_code(code: str, timeout_sec: float = 10.0) -> str:
    """
    Execute Python code in an isolated sub-process with timeout and sandbox checks.
    """
    denial = _sandbox_check(code)
    if denial:
        METRICS.incr("tools.run_python.denied")
        return denial

    if isinstance(timeout_sec, bool) or not isinstance(timeout_sec, (int, float)) or not math.isfinite(timeout_sec) or timeout_sec <= 0:
        return "ERROR: Timeout must be a finite positive number."
    capped = min(float(timeout_sec), CONFIG.max_python_timeout_sec)
    try:
        cmd, safe_env = _build_command_and_env(code)
    except RuntimeError as exc:
        return f"ERROR: {exc}"

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=_preexec_limits,
        env=safe_env,
    )
    async def bounded_read(stream):
        output = bytearray()
        while chunk := await stream.read(4096):
            output.extend(chunk)
            if len(output) > 65536:
                raise ValueError("Execution output limit exceeded")
        return bytes(output)

    tasks = [asyncio.create_task(bounded_read(proc.stdout)), asyncio.create_task(bounded_read(proc.stderr)), asyncio.create_task(proc.wait())]
    try:
        stdout, stderr, _ = await asyncio.wait_for(asyncio.gather(*tasks), timeout=capped)
        out_str = stdout.decode("utf-8", errors="replace")
        err_str = stderr.decode("utf-8", errors="replace")
        METRICS.incr("tools.run_python.calls")

        if proc.returncode != 0:
            return f"EXIT_FAILURE ({proc.returncode}):\nSTDERR:\n{err_str}\nSTDOUT:\n{out_str}"
        return out_str if out_str else "[Process finished with code 0, no output]"
    except ValueError:
        return "ERROR: Execution output limit exceeded."
    except asyncio.TimeoutError:
        METRICS.incr("tools.run_python.timeouts")
        return f"ERROR: Execution timed out after {capped} seconds."
    finally:
        # Cancellation and timeout must both kill descendants and reap the child.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        # Drain without retaining data: asyncio process.wait can otherwise hang
        # when a killed child left a paused stdout transport after overflow.
        async def discard(stream):
            while await stream.read(4096):
                pass
        await asyncio.gather(discard(proc.stdout), discard(proc.stderr), proc.wait())


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
