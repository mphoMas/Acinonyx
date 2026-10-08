"""
Tests for mas.squad.squad (EngineeringSquad autonomous build & self-healing test loop).
"""

import os
import shutil
import tempfile
import unittest
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.squad.squad import EngineeringSquad
from mas.tools.executor import register_default_tools
from mas.config import REPO_ROOT
from mas.tools.filesystem import ALLOWED_PROJECT_ROOTS, register_filesystem_tools, set_allowed_roots


class TestEngineeringSquad(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mas_squad_test_")
        self.orig_roots = list(ALLOWED_PROJECT_ROOTS)
        set_allowed_roots([REPO_ROOT, self.test_dir])
        self.registry = MCPRegistry()
        register_default_tools(self.registry)
        register_filesystem_tools(self.registry)
        self.client = MCPClient(self.registry)

    async def asyncTearDown(self):
        set_allowed_roots(self.orig_roots)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    async def test_squad_autonomous_mission_with_repair(self):
        squad = EngineeringSquad(mcp_client=self.client, max_repair_attempts=2)

        code_file = os.path.join(self.test_dir, "calc_module.py")
        test_file = os.path.join(self.test_dir, "test_calc_module.py")

        # Simulator: Attempt 1 produces a bug; Attempt 2 fixes it!
        def code_generator(spec: str, attempt: int) -> str:
            if attempt == 1:
                return "def add(a, b):\n    return a - b  # Deliberate bug\n"
            return "def add(a, b):\n    return a + b  # Corrected\n"

        def test_generator(spec: str, attempt: int) -> str:
            # We import calc_module relatively by ensuring python sys.path
            return (
                f"import unittest, sys\n"
                f"sys.path.insert(0, '{self.test_dir}')\n"
                f"import calc_module\n\n"
                f"class TestCalc(unittest.TestCase):\n"
                f"    def test_add(self):\n"
                f"        self.assertEqual(calc_module.add(2, 3), 5)\n\n"
                f"if __name__ == '__main__':\n"
                f"    unittest.main()\n"
            )

        mission_result = await squad.run_mission(
            task_name="Arithmetic Addition Module",
            requirements="Implement add(a, b) that returns sum of a and b",
            target_code_file=code_file,
            target_test_file=test_file,
            code_generator_fn=code_generator,
            test_generator_fn=test_generator,
        )

        # Assert mission succeeded after 2 attempts (with 1 self-repair round)
        self.assertTrue(mission_result.success)
        self.assertEqual(mission_result.attempts, 2)
        self.assertEqual(len(mission_result.reflections), 1)
        self.assertIn("AssertionError", mission_result.reflections[0])

        # Verify files were persisted to disk via MCP filesystem
        self.assertTrue(os.path.exists(code_file))
        self.assertTrue(os.path.exists(test_file))


if __name__ == "__main__":
    unittest.main()
