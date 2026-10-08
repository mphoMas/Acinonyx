"""Ephemeral containers for candidate code; expected results stay on the host."""

from __future__ import annotations

import asyncio
import os
import re
import uuid

from .contracts import CandidateError, Limits, OutputLimitError, SwarmError, canonical, strict_json, text
from .process import run_process

DOCKER = ["docker", "--host=unix:///var/run/docker.sock"]
BOOTSTRAP = """import json,sys
job=json.loads(sys.stdin.read())
namespace={}
exec(compile(job['source'],'candidate.py','exec'),namespace)
result=namespace['solve'](job['input'])
print(json.dumps(result,allow_nan=False,separators=(',',':')))
"""


class DockerWorker:
    """Operator-selected immutable image, no host mounts, credentials or egress.

    Docker protects the host only to the extent its kernel/runtime does. It is
    not a microVM and is unsuitable for hostile public tenants without further
    isolation. The Docker socket belongs exclusively to the trusted coordinator.
    """

    def __init__(self, image: str, limits: Limits):
        if not re.fullmatch(r"(?:[a-zA-Z0-9./:_-]+@)?sha256:[0-9a-f]{64}", image):
            raise SwarmError("Worker image must be pinned by SHA-256 digest or local image ID")
        self.image, self.limits = image, limits
        self._slots = asyncio.Semaphore(limits.parallel_cases)
        self._env = {
            k: v
            for k, v in os.environ.items()
            if k not in {"DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"}
        }

    async def _docker(self, *args: str, data: bytes = b"", timeout: float = 10):
        return await run_process(DOCKER + list(args), data=data, timeout=timeout, output_limit=self.limits.output_bytes, env=self._env)

    async def check(self):
        rc, _, _ = await self._docker("image", "inspect", self.image)
        if rc:
            raise SwarmError("Pinned worker image unavailable; no host-execution fallback")

    async def _remove(self, name: str, created: bool):
        rc, _, _ = await self._docker("rm", "--force", name)
        if rc and created:
            raise SwarmError("Worker cleanup failed; operator intervention required")
        # Confirm removal through a successful daemon response. A failed inspect
        # alone could mean an offline daemon, not an absent container.
        for _ in range(20):
            selector = f"id={name}" if re.fullmatch(r"[0-9a-f]{12,64}", name) else f"name=^/{name}$"
            status, out, _ = await self._docker("ps", "--all", "--quiet", "--filter", selector)
            if status:
                raise SwarmError("Cannot confirm worker cleanup")
            if not out.strip():
                return
            await asyncio.sleep(0.05)
        raise SwarmError("Worker removal did not complete")

    async def evaluate(self, source: str, value, run_id: str):
        text(source, "source", self.limits.source_bytes)
        async with self._slots:
            name = "mas-swarm-" + uuid.uuid4().hex
            created = False
            try:
                args = [
                    "create",
                    "--name",
                    name,
                    "--label",
                    f"acinonyx.swarm.run={run_id}",
                    "--pull=never",
                    "--interactive",
                    "--network=none",
                    "--read-only",
                    "--user=65534:65534",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges:true",
                    "--memory=64m",
                    "--memory-swap=64m",
                    "--cpus=0.5",
                    "--pids-limit=32",
                    "--ulimit=nofile=64:64",
                    "--ulimit=core=0:0",
                    "--log-driver=none",
                    "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m",
                    "--workdir=/tmp",
                ]
                # Override Docker client proxy defaults: this worker has no egress.
                for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy"):
                    args += ["--env", key + "="]
                args += [self.image, "python", "-I", "-B", "-c", BOOTSTRAP]
                # Cancelling the Docker client cannot roll back a create already
                # accepted by the daemon. Join creation before removing its name.
                creation = asyncio.create_task(self._docker(*args))
                try:
                    rc, _, _ = await asyncio.shield(creation)
                    created = rc == 0
                except asyncio.CancelledError:
                    rc, _, _ = await creation
                    created = rc == 0
                    raise
                if rc:
                    raise SwarmError("Container creation failed")
                try:
                    rc, stdout, _ = await self._docker(
                        "start",
                        "--attach",
                        "--interactive",
                        name,
                        data=canonical({"source": source, "input": value}).encode(),
                        timeout=self.limits.worker_seconds,
                    )
                except (TimeoutError, OutputLimitError) as exc:
                    raise CandidateError("Candidate exceeded time or output policy") from exc
                status_rc, status, _ = await self._docker("inspect", "--format", "{{json .State}}", name)
                state = strict_json(status) if not status_rc else {}
                if status_rc or state.get("Running") is not False:
                    raise SwarmError("Worker state unavailable")
                if rc or state.get("ExitCode") != 0 or state.get("OOMKilled"):
                    raise CandidateError("Candidate process failed")
                try:
                    return strict_json(stdout)
                except SwarmError as exc:
                    raise CandidateError("Candidate did not return valid JSON") from exc
            finally:
                # Shield cleanup from workflow cancellation and wait for completion.
                cleanup = asyncio.create_task(self._remove(name, created))
                try:
                    await asyncio.shield(cleanup)
                except asyncio.CancelledError:
                    await cleanup
                    raise

    async def recover(self, run_id: str):
        """Remove only containers owned by this interrupted run."""
        rc, out, _ = await self._docker("ps", "--all", "--quiet", "--filter", f"label=acinonyx.swarm.run={run_id}")
        if rc:
            raise SwarmError("Worker recovery unavailable")
        for container in out.decode().split():
            if not re.fullmatch(r"[0-9a-f]{12,64}", container):
                raise SwarmError("Invalid recovery container ID")
            await self._remove(container, True)
