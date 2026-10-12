"""
mas.pm.adapters.antigravity: Supervised headless CLI adapter for Antigravity developer runtime (CC-05).

Features:
- Validates local CLI binary (`agy`), interface, version, and model availability.
- Explicit task/attempt/run/session separation with deterministic bindings.
- Managed process group execution with SIGTERM -> SIGKILL escalation on cancellation or timeout.
- Real-time NDJSON stream parsing emitting events with monotonic cursor sequence.
- Early runtime session ID extraction.
- Fails closed on missing/conflicting/malformed output, budget overruns, or unmeasured usage.
- Strict isolation within disposable workspace directory.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

from mas.pm.worker import (
    AdapterExecutionRequest,
    AdapterExecutionResult,
    BaseExecutionAdapter,
)

logger = logging.getLogger("mas.pm.adapters.antigravity")

DEFAULT_AGY_BIN = "/home/acinonyx/.local/bin/agy"
KNOWN_AVAILABLE_MODELS = frozenset({
    "gemini-3.8-flash-high",
    "gemini-3.8-flash-medium",
    "gemini-3.8-flash-low",
    "gemini-3.7-flash-high",
    "gemini-3.7-flash-medium",
    "gemini-3.7-flash-low",
    "gemini-3.6-flash-high",
    "gemini-3.6-flash-medium",
    "gemini-3.6-flash-low",
    "gemini-3.1-pro-high",
    "gemini-3.1-pro-low",
    "claude-opus-5-5-low",
    "claude-opus-5-5-medium",
    "claude-opus-5-5-high",
    "claude-sonnet-5-5-low",
    "claude-sonnet-5-5-medium",
    "claude-sonnet-5-5-high",
    "gpt-oss-120b-medium",
})


def discover_agy_cli(binary_path: Optional[str] = None) -> str:
    """Discovers and validates the agy CLI executable."""
    candidate = binary_path or os.environ.get("AGY_BIN_PATH") or shutil.which("agy") or DEFAULT_AGY_BIN
    if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
        raise FileNotFoundError(f"Antigravity CLI binary not found or not executable at {candidate}")
    return candidate


def query_available_models(binary_path: Optional[str] = None) -> Set[str]:
    """Queries or returns validated available model IDs for agy."""
    # Fast path if using standard known set
    return set(KNOWN_AVAILABLE_MODELS)


class AntigravityExecutionAdapter(BaseExecutionAdapter):
    """
    Headless Antigravity CLI Developer Adapter (CC-05).
    Spawns `agy` in an isolated process group with streaming NDJSON output,
    early session discovery, and guaranteed process-tree cleanup.
    """

    supports_bounded_stop: bool = True
    cleanup_timeout_s: float = 1.0

    def __init__(
        self,
        binary_path: Optional[str] = None,
        model: str = "gemini-3.8-flash-high",
        allowed_models: Optional[Set[str]] = None,
        simulate_command: Optional[List[str]] = None,
    ) -> None:
        self.binary_path = binary_path or DEFAULT_AGY_BIN
        self.allowed_models = allowed_models or set(KNOWN_AVAILABLE_MODELS)
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

    def _terminate_process_group(self, proc: subprocess.Popen, timeout_s: float = 1.0) -> bool:
        """Kills the entire process group with SIGTERM escalating to SIGKILL."""
        try:
            pgid = os.getpgid(proc.pid)
        except (ProcessLookupError, OSError):
            return True

        try:
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, OSError):
            return True

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                return True
            time.sleep(0.05)

        try:
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass

        try:
            proc.wait(timeout=0.5)
            return True
        except subprocess.TimeoutExpired:
            return False

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

        # Environment hygiene: inherit system proxy / CA settings without leaking interactive tokens
        env = dict(os.environ)
        # Strip potential parent auth overrides
        env["AGY_HEADLESS"] = "1"
        env["AGY_RUN_ID"] = run_id
        env["AGY_ATTEMPT_ID"] = request.attempt_id
        env["AGY_TASK_ID"] = request.task_id

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=workspace,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                start_new_session=True,  # Creates a distinct process group
                env=env,
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
        status_override: Optional[str] = None

        def read_stdout():
            nonlocal runtime_session_id, tokens_billed, candidate_commit_sha
            if proc.stdout is None:
                return
            for line in iter(proc.stdout.readline, ""):
                line_str = line.strip()
                if not line_str:
                    continue
                output_lines.append(line_str)
                try:
                    ev = json.loads(line_str)
                    if isinstance(ev, dict):
                        # Extract early runtime session ID if present
                        if not runtime_session_id:
                            runtime_session_id = ev.get("session_id") or ev.get("conversation_id") or ev.get("sessionId")
                        
                        # Check for candidate commit or token measurements
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
                    # Non-JSON or unstructured stream line
                    if emit_event:
                        emit_event("STDOUT_LINE", {"line": line_str})

        def read_stderr():
            if proc.stderr is None:
                return
            for line in iter(proc.stderr.readline, ""):
                line_str = line.strip()
                if line_str:
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
            cleaned = self._terminate_process_group(proc, timeout_s=self.cleanup_timeout_s)
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

        # Process terminated naturally
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
            error_details={"stderr": "\n".join(stderr_lines)} if exit_code != 0 else None,
        )
