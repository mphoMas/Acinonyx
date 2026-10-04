"""
Tests for mas.tools.filesystem.
"""

import os
import shutil
import tempfile
import unittest
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.tools.filesystem import register_filesystem_tools


class TestFilesystemTools(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mas_fs_test_")
        self.registry = MCPRegistry()
        register_filesystem_tools(self.registry)
        self.client = MCPClient(self.registry)

    async def asyncTearDown(self):
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


if __name__ == "__main__":
    unittest.main()
