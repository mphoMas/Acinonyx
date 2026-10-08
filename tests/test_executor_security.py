"""
Tests for SEC-01: OS-Level sandboxing, process group containment, environment stripping.
"""

import os
import asyncio
from unittest.mock import patch
import unittest
from mas.tools.executor import run_python_code


class TestSandboxedPythonExecutor(unittest.IsolatedAsyncioTestCase):

    async def test_environment_variables_stripped(self):
        """Assert that process environment is stripped of host secrets."""
        os.environ["MAS_SECRET_TOKEN_XYZ"] = "super-sensitive-host-token-123"
        try:
            res = await run_python_code(
                "import os\n"
                "print('FOUND' if 'MAS_SECRET_TOKEN_XYZ' in os.environ else 'STRIPPED')"
            )
            self.assertEqual(res.strip(), "STRIPPED")
        finally:
            os.environ.pop("MAS_SECRET_TOKEN_XYZ", None)

    async def test_network_isolation_under_sandbox(self):
        """Assert that untrusted code cannot connect to external sockets."""
        res = await run_python_code(
            "import urllib.request\n"
            "try:\n"
            "    urllib.request.urlopen('http://1.1.1.1', timeout=1)\n"
            "    print('CONNECTED')\n"
            "except Exception as e:\n"
            "    print('BLOCKED')\n"
        )
        self.assertEqual(res.strip(), "BLOCKED")

    async def test_timeout_and_process_group_cleanup(self):
        """Assert that long running code or sub-processes are terminated cleanly on timeout."""
        res = await run_python_code(
            "import time\n"
            "time.sleep(5)\n"
            "print('SHOULD_NOT_REACH')",
            timeout_sec=0.5,
        )
        self.assertIn("Execution timed out", res)

    async def test_missing_sandbox_never_falls_back_to_host(self):
        with patch("mas.tools.executor.shutil.which", return_value=None):
            res = await run_python_code("print('HOST_EXECUTED')")
        self.assertIn("host execution refused", res)
        self.assertNotIn("HOST_EXECUTED", res)

    async def test_output_limit_and_invalid_timeouts(self):
        self.assertIn("output limit", await run_python_code("print('x' * 1000000)"))
        for timeout in (float("nan"), float("inf"), -1, 0, True, "bad"):
            self.assertIn("finite positive", await run_python_code("print(1)", timeout))

    async def test_cancellation_reaps_executor(self):
        from mas.tools.executor import asyncio as executor_asyncio
        original = executor_asyncio.create_subprocess_exec
        children = []
        async def capture(*args, **kwargs):
            child = await original(*args, **kwargs)
            children.append(child)
            return child
        with patch("mas.tools.executor.asyncio.create_subprocess_exec", side_effect=capture):
            task = asyncio.create_task(run_python_code("import time; time.sleep(30)"))
            await asyncio.sleep(0.1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].returncode)


if __name__ == "__main__":
    unittest.main()
