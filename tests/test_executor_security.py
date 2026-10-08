"""
Tests for SEC-01: OS-Level sandboxing, process group containment, environment stripping.
"""

import os
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


if __name__ == "__main__":
    unittest.main()
