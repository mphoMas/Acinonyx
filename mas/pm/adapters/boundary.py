"""No-mount, no-egress container execution for coordinator adapters.

The Docker socket is used only by the trusted supervisor. No host execution fallback
exists. This is a supervised pilot boundary, not a hostile multi-tenant microVM.
"""
from __future__ import annotations

import asyncio
import base64
import math
import os
import re
import threading
import uuid
from pathlib import Path

from mas.swarm.contracts import OutputLimitError, SwarmError, canonical, strict_json
from mas.swarm.process import run_process

DOCKER = ['docker', '--host=unix:///var/run/docker.sock']
BOOTSTRAP = '''import base64,json,os,subprocess,sys
job=json.loads(sys.stdin.read())
os.makedirs('/tmp/workspace',exist_ok=True)
for name,content in job['files'].items():
    path='/tmp/workspace/'+name
    os.makedirs(os.path.dirname(path),exist_ok=True)
    with open(path,'wb') as f: f.write(base64.b64decode(content))
os.chdir('/tmp/workspace')
sys.exit(subprocess.call(job['command'],env={'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':'/tmp/home','LANG':'C.UTF-8',**job['environment']}))
'''


def finite_timeout(value: float, maximum: float = 120) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= maximum:
        raise ValueError('Timeout must be a finite positive number within operational bounds')
    return float(value)


def snapshot_workspace(root: Path, paths: list[str]) -> dict[str, str]:
    """Copy only explicit regular files; never follow links or copy home/credential trees."""
    root = root.resolve(strict=True)
    if not paths or len(paths) > 256:
        raise ValueError('An explicit bounded file allowlist is required')
    result = {}
    total = 0
    for name in paths:
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError('Invalid workspace path')
        if any(part in {'.git', '.ssh', '.aws', '.codex', '.env'} for part in path.parts):
            raise ValueError('Credential/control files cannot enter execution boundary')
        current = root
        for part in path.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError('Workspace symlinks are forbidden')
        if not current.is_file():
            raise ValueError('Allowlist entries must be regular files')
        data = current.read_bytes()
        total += len(data)
        if total > 2 * 1024 * 1024:
            raise ValueError('Workspace snapshot exceeds byte limit')
        result[path.as_posix()] = base64.b64encode(data).decode('ascii')
    return result


class ContainerBoundary:
    def __init__(self, image: str, output_limit: int = 65536):
        if not isinstance(image, str) or not re.fullmatch(r'(?:[a-zA-Z0-9./:_-]+@)?sha256:[0-9a-f]{64}', image):
            raise ValueError('Execution image must be pinned by SHA-256')
        if type(output_limit) is not int or not 1024 <= output_limit <= 65536:
            raise ValueError('Invalid output limit')
        self.image = image
        self.output_limit = output_limit
        # Preserve session transport/CA configuration for Docker client, never pass it
        # (or daemon-configured proxy credentials) to the candidate container.
        self.client_env = {k: v for k, v in os.environ.items() if k not in {
            'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'}}

    async def _docker(self, *args, data=b'', timeout=10):
        try:
            return await run_process(DOCKER + list(args), data=data, timeout=timeout,
                                     output_limit=self.output_limit, env=self.client_env)
        except TimeoutError:
            raise
        except OSError as exc:
            raise SwarmError('Docker control unavailable; execution boundary not confirmed') from exc

    async def _remove(self, name):
        # Removal is required even if create failed: daemon may have accepted it.
        await self._docker('rm', '--force', name)
        code, out, _ = await self._docker('ps', '--all', '--quiet', '--filter', f'name=^/{name}$')
        if code or out.strip():
            raise SwarmError('Cannot confirm whole execution boundary removal')

    async def _execute(self, command, files, environment, timeout, stop):
        name = 'mas-coordinator-' + uuid.uuid4().hex
        args = ['create', '--name', name, '--pull=never', '--interactive', '--network=none',
                '--read-only', '--user=65534:65534', '--cap-drop=ALL',
                '--security-opt=no-new-privileges:true', '--memory=128m', '--memory-swap=128m',
                '--cpus=0.5', '--pids-limit=32', '--ulimit=nofile=64:64', '--ulimit=core=0:0',
                '--log-driver=none', '--tmpfs=/tmp:rw,nosuid,nodev,size=32m', '--workdir=/tmp']
        for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
                    'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy'):
            args += ['--env', key + '=']
        args += [self.image, 'python', '-I', '-B', '-c', BOOTSTRAP]
        try:
            code, _, err = await self._docker(*args)
            if code:
                raise SwarmError('Container creation unavailable: ' + err.decode(errors='replace')[-200:])
            task = asyncio.create_task(self._docker('start', '--attach', '--interactive', name,
                data=canonical({'command': command, 'files': files, 'environment': environment}).encode(), timeout=timeout))
            try:
                while not task.done():
                    if stop is not None and stop.is_set():
                        task.cancel()
                        await asyncio.gather(task, return_exceptions=True)
                        raise InterruptedError('Execution canceled')
                    await asyncio.sleep(0.01)
                code, out, err = await task
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
            status, raw, _ = await self._docker('inspect', '--format', '{{json .State}}', name)
            state = strict_json(raw) if not status else {}
            if status or state.get('Running') is not False or state.get('OOMKilled'):
                raise SwarmError('Execution state unavailable or resource limit exceeded')
            if state.get('ExitCode') != code:
                raise SwarmError('Execution exit status mismatch')
            return code, out, err
        finally:
            await self._remove(name)

    def run(self, command: list[str], *, files=None, environment=None, timeout=30,
            stop: threading.Event | None = None):
        finite_timeout(timeout)
        if not isinstance(command, list) or not command or len(command) > 64 or any(
                not isinstance(v, str) or not v or len(v.encode()) > 32768 for v in command):
            raise ValueError('Invalid bounded argv')
        environment = environment or {}
        if set(environment) - {'AGY_HEADLESS', 'AGY_RUN_ID', 'AGY_ATTEMPT_ID', 'AGY_TASK_ID'}:
            raise ValueError('Only runtime markers may enter execution environment')
        return asyncio.run(self._execute(command, files or {}, environment, timeout, stop))


__all__ = ['ContainerBoundary', 'OutputLimitError', 'snapshot_workspace', 'finite_timeout']
