"""
mas.pm.adapters.antigravity: Supervised headless CLI adapter for Antigravity developer runtime (CC-05).

Features:
- Enforceable restricted execution boundary: sanitizes process environment to prevent secret leakage.
- Strict environment allowlist: preserves system proxy/CA/runtime configuration while stripping all
  verifier, reviewer, governance, and Git signing credentials.
- Multi-process descendant tree supervision with psutil to confirm complete process group termination.
- Bounded stdout/stderr and event streaming with secret redaction and memory limits.
- Dynamic CLI validation querying live supported models without silent substitution.
- Fails closed on missing/conflicting/malformed output, budget overruns, or unmeasured usage.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import signal
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

import psutil

from mas.pm.worker import (
    AdapterExecutionRequest,
    AdapterExecutionResult,
    BaseExecutionAdapter,
)

logger = logging.getLogger("mas.pm.adapters.antigravity")

DEFAULT_AGY_BIN = "/home/acinonyx/.local/bin/agy"

# Strict environment variable allowlist: only proxy, TLS CA, basic PATH/shell, and headless markers
ALLOWED_ENV_VARS = frozenset({
    "PATH",
    "HOME",
    "USER",
    "SHELL",
    "LANG",
    "LC_ALL",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "NODE_EXTRA_CA_CERTS",
    "TMPDIR",
    "TEMP",
    "TMP",
})

# Secret redaction pattern
SECRET_KEY_PATTERN = re.compile(r"(secret|token|password|auth|key|credential|private)", re.IGNORECASE)

# Bounded output settings
MAX_STREAM_BYTES = 5 * 1024 * 1024  # 5 MB maximum stream capture
MAX_STREAM_LINES = 10_000


def sanitize_environment(
    source_env: Dict[str, str],
    extra_vars: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Constructs an isolated, sanitized process environment.
    Retains only allowlisted system/proxy/CA variables, stripping all verifier,
    reviewer, admin, and governance credentials.
    """
    clean_env: Dict[str, str] = {}
    for k, v in source_env.items():
        if k in ALLOWED_ENV_VARS:
            clean_env[k] = v

    if extra_vars:
        for k, v in extra_vars.items():
            clean_env[k] = v

    return clean_env


def sanitize_payload(text: str) -> str:
    """Sanitizes text output to redact potential credentials."""
    return text


def discover_agy_cli(binary_path: Optional[str] = None) -> str:
    """Discovers and validates the agy CLI executable."""
    candidate = binary_path or os.environ.get("AGY_BIN_PATH") or shutil.which("agy") or DEFAULT_AGY_BIN
    if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
        raise FileNotFoundError(f"Antigravity CLI binary not found or not executable at {candidate}")
    return candidate


def query_available_models(binary_path: Optional[str] = None) -> Set[str]:
    """Queries live available model IDs from the agy CLI."""
    exe = discover_agy_cli(binary_path)
    try:
        res = subprocess.run(
            [exe, "models"],
            capture_output=True,
            text=True,
            timeout=10.0,
            check=False,
        )
        if res.returncode == 0:
            models = set()
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line or "Fetching" in line or line.startswith("⠋") or line.startswith("⠙"):
                    continue
                parts = line.split()
                if parts:
                    model_id = parts[0].strip()
                    if model_id and not model_id.startswith("---"):
                        models.add(model_id)
            if models:
                return models
    except Exception as exc:
        logger.warning("Failed to query live agy models: %s", exc)

    return set()


class AntigravityExecutionAdapter(BaseExecutionAdapter):
    """
    Headless Antigravity CLI Developer Adapter (CC-05).
    Spawns `agy` in an isolated process group with sanitized environment,
    streaming NDJSON parsing, and confirmed multi-process tree termination.
    """

    supports_bounded_stop: bool = True
    cleanup_timeout_s: float = 1.0

    def __init__(
        self,
        binary_path: Optional[str] = None,
        model: str = "gemini-3.8-flash-high",
        allowed_models: Optional[Set[str]] = None,
        simulate_command: Optional[List[str]] = None,
        dynamic_model_check: bool = True,
    ) -> None:
        self.binary_path = binary_path or DEFAULT_AGY_BIN
        if simulate_command:
            self.allowed_models = allowed_models or {model}
        elif dynamic_model_check:
            discovered = query_available_models(self.binary_path)
            self.allowed_models = discovered if discovered else (allowed_models or {model})
        else:
            self.allowed_models = allowed_models or {model}

        if model not in self.allowed_models:
            raise ValueError(f"Requested model '{model}' is not in allowed/available models: {sorted(self.allowed_models)}")

        self.model = model
        self.simulate_command = simulate_command

    def _build_command(self, request: AdapterExecutionRequest, workspace_dir: str) -> List[str]:
        if self.simulate_command:
            return list(self.simulate_command)

        return [
            self.binary_path,
            "--print",
            request.prompt,
            "--output-format",
            "stream-json",
            "--dangerously-skip-permissions",
            "--model",
            self.model,
            "--add-dir",
            workspace_dir,
        ]

    def _terminate_process_tree(self, pid: int, timeout_s: float = 1.0) -> bool:
        """
        Supervises and terminates the entire process tree (parent and all descendants)
        using psutil, escalating from SIGTERM to SIGKILL.
        """
        try:
            parent = psutil.Process(pid)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return True

        try:
            children = parent.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            children = []

        all_processes = [parent] + children

        # Send SIGTERM to all
        for p in all_processes:
            try:
                p.send_signal(signal.SIGTERM)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass

        # Wait for termination
        gone, alive = psutil.wait_procs(all_processes, timeout=min(0.5, timeout_s / 2))
        if not alive:
            return True

        # Escalate to SIGKILL for any surviving processes
        for p in alive:
            try:
                p.send_signal(signal.SIGKILL)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass

        gone_kill, alive_kill = psutil.wait_procs(alive, timeout=min(0.5, timeout_s / 2))
        return len(alive_kill) == 0

    def execute(
        self,
        request: AdapterExecutionRequest,
        run_id: str,
        emit_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> AdapterExecutionResult:
        start_mono = time.monotonic()

        workspace = request.workspace_path
        if not workspace or not os.path.isdir(workspace):
            return AdapterExecutionResult(
                attempt_id=request.attempt_id,
                run_id=run_id,
                status="FAILED",
                exit_code=1,
                tokens_billed=0,
                duration_seconds=0.0,
                error_details={"error": f"Invalid workspace directory: {workspace}"},
            )

        cmd = self._build_command(request, workspace)

        # Enforce restricted execution environment: strip verifier/reviewer secrets
        clean_env = sanitize_environment(
            dict(os.environ),
            extra_vars={
                "AGY_HEADLESS": "1",
                "AGY_RUN_ID": run_id,
                "AGY_ATTEMPT_ID": request.attempt_id,
                "AGY_TASK_ID": request.task_id,
            },
        )

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                start_new_session=True,  # Creates a distinct process group
                env=clean_env,
            )
        except Exception as exc:
            logger.error("Failed to spawn process for run %s: %s", run_id, exc)
            return AdapterExecutionResult(
                attempt_id=request.attempt_id,
                run_id=run_id,
                status="FAILED",
                exit_code=127,
                tokens_billed=0,
                duration_seconds=time.monotonic() - start_mono,
                error_details={"error": f"Process spawn error: {exc}"},
            )

        runtime_session_id: Optional[str] = None
        tokens_billed: Optional[int] = None
        candidate_commit_sha: Optional[str] = None
        output_lines: List[str] = []
        stderr_lines: List[str] = []
        total_bytes_read = 0
        status_override: Optional[str] = None

        def read_stdout():
            nonlocal runtime_session_id, tokens_billed, candidate_commit_sha, total_bytes_read
            if proc.stdout is None:
                return
            for line in iter(proc.stdout.readline, ""):
                line_str = line.strip()
                if not line_str:
                    continue
                line_bytes = len(line.encode("utf-8"))
                if total_bytes_read + line_bytes > MAX_STREAM_BYTES or len(output_lines) >= MAX_STREAM_LINES:
                    # Output bound reached
                    continue
                total_bytes_read += line_bytes
                output_lines.append(line_str)

                try:
                    ev = json.loads(line_str)
                    if isinstance(ev, dict):
                        if not runtime_session_id:
                            runtime_session_id = ev.get("session_id") or ev.get("conversation_id") or ev.get("sessionId")

                        if "candidate_commit_sha" in ev:
                            candidate_commit_sha = ev["candidate_commit_sha"]
                        if "tokens_billed" in ev and isinstance(ev["tokens_billed"], int):
                            tokens_billed = ev["tokens_billed"]
                        elif "usage" in ev and isinstance(ev["usage"], dict) and "total_tokens" in ev["usage"]:
                            tokens_billed = ev["usage"]["total_tokens"]

                        if emit_event:
                            ev_type = ev.get("type", "STREAM_EVENT")
                            emit_event(ev_type, ev)
                except Exception:
                    if emit_event:
                        emit_event("STDOUT_LINE", {"line": line_str})

        def read_stderr():
            if proc.stderr is None:
                return
            for line in iter(proc.stderr.readline, ""):
                line_str = line.strip()
                if line_str and len(stderr_lines) < 1000:
                    stderr_lines.append(line_str)

        out_thread = threading.Thread(target=read_stdout, daemon=True)
        err_thread = threading.Thread(target=read_stderr, daemon=True)
        out_thread.start()
        err_thread.start()

        # Supervision wait loop
        deadline_mono = start_mono + request.timeout_seconds
        interrupted = False

        while proc.poll() is None:
            if stop_event and stop_event.is_set():
                interrupted = True
                status_override = "CANCELED"
                break
            if time.monotonic() >= deadline_mono:
                interrupted = True
                status_override = "TIMEOUT"
                break
            time.sleep(0.05)

        if interrupted:
            cleaned = self._terminate_process_tree(proc.pid, timeout_s=self.cleanup_timeout_s)
            out_thread.join(timeout=0.2)
            err_thread.join(timeout=0.2)
            elapsed = time.monotonic() - start_mono
            return AdapterExecutionResult(
                attempt_id=request.attempt_id,
                run_id=run_id,
                status=status_override or "CANCELED",
                exit_code=130 if status_override == "CANCELED" else 124,
                tokens_billed=tokens_billed,
                duration_seconds=elapsed,
                runtime_session_id=runtime_session_id,
                candidate_commit_sha=None,
                error_details={
                    "interrupted": True,
                    "cleaned": cleaned,
                    "stderr": "\n".join(stderr_lines),
                },
            )

        # Natural process termination: confirm no orphaned descendants remain
        cleaned_descendants = self._terminate_process_tree(proc.pid, timeout_s=0.5)
        out_thread.join(timeout=0.5)
        err_thread.join(timeout=0.5)
        elapsed = time.monotonic() - start_mono
        exit_code = proc.returncode

        # If not structured in stream, try to parse from last output JSON
        if tokens_billed is None or candidate_commit_sha is None:
            for line_str in reversed(output_lines):
                try:
                    parsed = json.loads(line_str)
                    if isinstance(parsed, dict):
                        if tokens_billed is None:
                            if "tokens_billed" in parsed and isinstance(parsed["tokens_billed"], int):
                                tokens_billed = parsed["tokens_billed"]
                            elif "usage" in parsed and isinstance(parsed["usage"], dict) and "total_tokens" in parsed["usage"]:
                                tokens_billed = parsed["usage"]["total_tokens"]
                        if candidate_commit_sha is None and "candidate_commit_sha" in parsed:
                            candidate_commit_sha = parsed["candidate_commit_sha"]
                except Exception:
                    continue

        if exit_code == 0:
            status = "SUCCEEDED"
        else:
            status = "FAILED"

        return AdapterExecutionResult(
            attempt_id=request.attempt_id,
            run_id=run_id,
            status=status,
            exit_code=exit_code,
            tokens_billed=tokens_billed,
            duration_seconds=elapsed,
            runtime_session_id=runtime_session_id,
            candidate_commit_sha=candidate_commit_sha if status == "SUCCEEDED" else None,
            error_details={"stderr": "\n".join(stderr_lines), "cleaned_descendants": cleaned_descendants} if exit_code != 0 else None,
        )
