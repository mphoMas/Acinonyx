"""Bounded subprocess I/O and cancellation, with no shell invocation."""

from __future__ import annotations

import asyncio
import os
import signal

from .contracts import OutputLimitError


async def run_process(
    argv: list[str], *, data: bytes = b"", timeout: float = 10, output_limit: int = 32768, env: dict | None = None
) -> tuple[int, bytes, bytes]:
    proc = await asyncio.create_subprocess_exec(
        *argv,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        start_new_session=True,
    )

    async def read(stream):
        result = bytearray()
        while chunk := await stream.read(4096):
            result.extend(chunk)
            if len(result) > output_limit:
                raise OutputLimitError("Process output limit exceeded")
        return bytes(result)

    async def write():
        try:
            proc.stdin.write(data)
            await proc.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            proc.stdin.close()

    tasks = [
        asyncio.create_task(read(proc.stdout)),
        asyncio.create_task(read(proc.stderr)),
        asyncio.create_task(write()),
        asyncio.create_task(proc.wait()),
    ]
    try:
        stdout, stderr, _, code = await asyncio.wait_for(asyncio.gather(*tasks), timeout)
        return code, stdout, stderr
    finally:
        for task in tasks:
            task.cancel()
        # Also terminate descendants that retained pipes after the parent exited.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await asyncio.gather(*tasks, return_exceptions=True)
        async def discard(stream):
            while await stream.read(4096):
                pass
        await asyncio.gather(discard(proc.stdout), discard(proc.stderr), proc.wait())
