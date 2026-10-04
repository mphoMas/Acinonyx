"""
tests.test_tools_git_package: Unit tests for Git and UV package MCP tools.
Architect: Acinonyx
"""

import os
import shutil
import tempfile
import unittest
from mas.mcp.protocol import MCPRegistry
from mas.tools.git_tool import register_git_tools, git_init_tool, git_status_tool, git_add_tool, git_commit_tool, git_branch_tool
from mas.tools.package_tool import register_package_tools, uv_pip_list_tool


class TestGitTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    async def test_git_init_and_status(self):
        res = await git_init_tool(repo_path=self.test_dir)
        self.assertTrue(res.get("success"), f"Init failed: {res}")

        status_res = await git_status_tool(repo_path=self.test_dir)
        self.assertTrue(status_res.get("success"))

    async def test_git_add_commit_and_branch(self):
        await git_init_tool(repo_path=self.test_dir)

        # Create a test file
        test_file = os.path.join(self.test_dir, "hello.txt")
        with open(test_file, "w") as f:
            f.write("Hello Acinonyx")

        # Add & commit
        add_res = await git_add_tool(repo_path=self.test_dir, files=["hello.txt"])
        self.assertTrue(add_res.get("success"))

        commit_res = await git_commit_tool(repo_path=self.test_dir, message="Initial commit")
        self.assertTrue(commit_res.get("success"))

        # Create branch
        branch_res = await git_branch_tool(repo_path=self.test_dir, branch_name="feature/agentic-ai")
        self.assertTrue(branch_res.get("success"))
        self.assertEqual(branch_res.get("branch"), "feature/agentic-ai")


class TestPackageTools(unittest.IsolatedAsyncioTestCase):
    async def test_uv_pip_list(self):
        res = await uv_pip_list_tool()
        # uv pip list should execute successfully
        self.assertTrue(res.get("success"), f"UV list failed: {res}")
        self.assertIn("installed", res)


class TestMCPRegistryIntegration(unittest.TestCase):
    def test_tools_registered_in_mcp(self):
        registry = MCPRegistry()
        register_git_tools(registry)
        register_package_tools(registry)

        tool_names = list(registry.tools.keys())
        expected_tools = [
            "git_init", "git_status", "git_add", "git_commit",
            "git_branch", "git_checkout", "git_diff", "git_log",
            "uv_pip_install", "uv_pip_list", "uv_venv_create",
        ]
        for exp in expected_tools:
            self.assertIn(exp, tool_names)


if __name__ == "__main__":
    unittest.main()
