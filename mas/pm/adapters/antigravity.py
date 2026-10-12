"""Bounded offline Antigravity adapter. Live network/credential broker not qualified.

All commands, including test commands and model discovery, run in a pinned no-mount,
no-egress container. This adapter is not registered for automatic live dispatch.
"""
from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Callable

from mas.pm.adapters.boundary import ContainerBoundary, finite_timeout, snapshot_workspace
from mas.pm.worker import AdapterExecutionRequest, AdapterExecutionResult, BaseExecutionAdapter
from mas.swarm.contracts import SwarmError, strict_json

DEFAULT_AGY_BIN = '/usr/local/bin/agy'
ALLOWED_ENV_VARS = frozenset({'PATH', 'LANG', 'LC_ALL', 'HTTP_PROXY', 'HTTPS_PROXY',
    'NO_PROXY', 'http_proxy', 'https_proxy', 'no_proxy', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
    'REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'NODE_EXTRA_CA_CERTS'})
RUNTIME_MARKERS = frozenset({'AGY_HEADLESS', 'AGY_RUN_ID', 'AGY_ATTEMPT_ID', 'AGY_TASK_ID'})


def sanitize_environment(source_env, extra_vars=None):
    result = {k: v for k, v in source_env.items() if k in ALLOWED_ENV_VARS}
    if set(extra_vars or {}) - RUNTIME_MARKERS:
        raise ValueError('Untrusted environment additions')
    result.update(extra_vars or {})
    return result


def sanitize_payload(text):
    # Only this sanitized tail is diagnostic; raw events are never published.
    text = re.sub(r'(?i)(secret|token|password|authorization|credential|api[_-]?key)\s*[:=]\s*\S+', r'\1=[REDACTED]', text)
    return re.sub(r'\b(?:github_pat_|ghp_|sk-)[A-Za-z0-9_\-]+', '[REDACTED]', text)[-2000:]


def query_available_models(boundary: ContainerBoundary, binary_path=DEFAULT_AGY_BIN):
    code, out, _ = boundary.run([binary_path, 'models', '--json'], timeout=10)
    if code:
        raise SwarmError('Live model discovery failed; substitution is forbidden')
    models = strict_json(out)
    if not isinstance(models, list) or not models or len(models) > 100 or any(
            not isinstance(v, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,100}', v) for v in models):
        raise SwarmError('Malformed live model discovery')
    return frozenset(models)


class AntigravityExecutionAdapter(BaseExecutionAdapter):
    supports_bounded_stop = True
    # Container control/cleanup has its own bounded daemon operations. Worker registry
    # remains synthetic-only until this implementation is independently qualified.
    cleanup_timeout_s = 30.0

    def __init__(self, *, image: str, binary_path=DEFAULT_AGY_BIN,
                 model='gemini-3.8-flash-high', allowed_models=None,
                 simulate_command=None, dynamic_model_check=True):
        self.boundary = ContainerBoundary(image)
        self.binary_path, self.model = binary_path, model
        self.simulate_command = simulate_command
        if simulate_command is not None:
            if not isinstance(simulate_command, list) or not simulate_command:
                raise ValueError('Test command must be nonempty argv')
            self.allowed_models = frozenset(allowed_models or {model})
        else:
            if not dynamic_model_check:
                raise PermissionError('Live discovery cannot be disabled')
            discovered = query_available_models(self.boundary, binary_path)
            self.allowed_models = discovered & frozenset(allowed_models) if allowed_models is not None else discovered
        if model not in self.allowed_models:
            raise ValueError('Requested model is not in allowed/available models')

    def execute(self, request: AdapterExecutionRequest, run_id: str,
                emit_event: Callable | None = None, stop_event: threading.Event | None = None):
        started = time.monotonic()
        def result(status, code, **kw):
            return AdapterExecutionResult(attempt_id=request.attempt_id, run_id=run_id,
                status=status, exit_code=code, duration_seconds=time.monotonic()-started, **kw)
        finite_timeout(request.timeout_seconds)
        if not request.workspace_path or not Path(request.workspace_path).is_dir():
            return result('FAILED', 1, tokens_billed=None, error_details={'error': 'Invalid workspace directory'})
        files = snapshot_workspace(Path(request.workspace_path), request.path_whitelist)
        command = self.simulate_command or [self.binary_path, '--print', request.prompt,
            '--output-format', 'stream-json', '--model', self.model]
        try:
            code, out, err = self.boundary.run(command, files=files,
                environment={'AGY_HEADLESS': '1', 'AGY_RUN_ID': run_id,
                             'AGY_ATTEMPT_ID': request.attempt_id, 'AGY_TASK_ID': request.task_id},
                timeout=request.timeout_seconds, stop=stop_event,
                identity={'run_id': run_id, 'tenant': request.tenant_id,
                          'principal': getattr(request, 'executor_principal', request.task_id), 'generation': request.fencing_token},
                authority_check=getattr(request, 'authorize_start', None))
        except (TimeoutError, InterruptedError, SwarmError) as exc:
            return result('UNKNOWN_EXECUTION', None, tokens_billed=None,
                error_details={'error': sanitize_payload(str(exc)), 'settlement_allowed': False})
        events = []
        try:
            for line in out.splitlines():
                if line.strip():
                    event = strict_json(line)
                    if not isinstance(event, dict):
                        raise ValueError('Invalid runtime event')
                    events.append(event)
            sessions = {e['session_id'] for e in events if 'session_id' in e}
            measurements = [e for e in events if e.get('type') == 'RESULT']
            if len(sessions) != 1 or len(measurements) != 1:
                raise ValueError('Missing or conflicting runtime measurements')
            session = next(iter(sessions))
            measurement = measurements[0]
            tokens = measurement.get('tokens_billed')
            candidate = measurement.get('candidate_commit_sha')
            if not isinstance(session, str) or not session or len(session) > 256:
                raise ValueError('Invalid session identity')
            if type(tokens) is not int or not 0 <= tokens <= request.budget_token_limit:
                raise ValueError('Missing, invalid or over-budget usage')
            if not isinstance(candidate, str) or not re.fullmatch('[0-9a-f]{40}', candidate):
                raise ValueError('Invalid candidate identity')
            if code:
                return result('FAILED', code, tokens_billed=tokens, runtime_session_id=session,
                    error_details={'stderr': sanitize_payload(err.decode(errors='replace'))})
            if emit_event:
                # Explicit test claim, never raw arbitrary stdout or completion evidence.
                emit_event('RUNTIME_OBSERVATION', {'runtime_session_id': session,
                    'tokens_billed': tokens, 'candidate_commit_sha': candidate,
                    'domain': 'TEST' if self.simulate_command else 'UNVERIFIED_RUNTIME'})
            return result('SUCCEEDED', code, tokens_billed=tokens,
                runtime_session_id=session, candidate_commit_sha=candidate)
        except (ValueError, SwarmError) as exc:
            return result('UNKNOWN_EXECUTION', code, tokens_billed=None,
                error_details={'error': str(exc), 'settlement_allowed': False})
