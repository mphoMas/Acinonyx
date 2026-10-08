"""
Tests for mas.tools.filesystem and SEC-02 strict filesystem jailing.
"""

import os
import shutil
import tempfile
import unittest
from mas.config import REPO_ROOT
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.tools.filesystem import (
    ALLOWED_PROJECT_ROOTS,
    register_filesystem_tools,
    set_allowed_roots,
)


class TestFilesystemTools(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mas_fs_test_")
        self.orig_roots = list(ALLOWED_PROJECT_ROOTS)
        set_allowed_roots([REPO_ROOT, self.test_dir])
        self.registry = MCPRegistry()
        register_filesystem_tools(self.registry)
        self.registry.tool_acl.allow("fs_engineer", ["fs_write", "fs_read", "fs_list", "fs_glob"])
        self.client = MCPClient(self.registry, default_principal="fs_engineer")

    async def asyncTearDown(self):
        set_allowed_roots(self.orig_roots)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    async def test_fs_write_and_read(self):
        target = os.path.join(self.test_dir, "sub", "test.txt")
        content = "MAS-Core high-throughput runtime test payload."

        # Write
        res_write = await self.client.call_tool("fs_write", {"path": target, "content": content})
        self.assertIn("SUCCESS", res_write)

        # Read
        res_read = await self.client.call_tool("fs_read", {"path": target})
        self.assertEqual(res_read, content)

    async def test_fs_list_and_glob(self):
        file1 = os.path.join(self.test_dir, "file1.txt")
        file2 = os.path.join(self.test_dir, "file2.py")
        await self.client.call_tool("fs_write", {"path": file1, "content": "1"})
        await self.client.call_tool("fs_write", {"path": file2, "content": "2"})

        # List
        res_list = await self.client.call_tool("fs_list", {"path": self.test_dir})
        self.assertIn("file1.txt", res_list)
        self.assertIn("file2.py", res_list)

        # Glob
        res_glob = await self.client.call_tool("fs_glob", {"pattern": f"{self.test_dir}/*.py"})
        self.assertIn("file2.py", res_glob)
        self.assertNotIn("file1.txt", res_glob)

    async def test_boundary_enforcement_outside_roots(self):
        """Verify reading and listing arbitrary host paths outside boundary is denied."""
        # fs_read on /etc/hosts
        res_read = await self.client.call_tool("fs_read", {"path": "/etc/hosts"})
        self.assertIn("ERROR: Access denied", res_read)

        # fs_list on /etc
        res_list = await self.client.call_tool("fs_list", {"path": "/etc"})
        self.assertIn("ERROR: Access denied", res_list)

        # fs_glob on /etc/*
        res_glob = await self.client.call_tool("fs_glob", {"pattern": "/etc/*"})
        self.assertIn("ERROR: Access denied", res_glob)

    async def test_symlink_escape_denial(self):
        """Verify symlink pointing outside allowed root cannot be read or listed."""
        symlink_target = os.path.join(self.test_dir, "escape_link")
        try:
            os.symlink("/etc", symlink_target)
            res_list = await self.client.call_tool("fs_list", {"path": symlink_target})
            self.assertIn("ERROR: Access denied", res_list)
        except (OSError, NotImplementedError):
            pass


if __name__ == "__main__":
    unittest.main()
