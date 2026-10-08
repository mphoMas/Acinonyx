"""
Tests for mas.mcp (JSON-RPC 2.0 protocol and MCP Client/Server) and SEC-03 Tool ACL.
"""

import unittest
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient


class TestMCPImplementation(unittest.IsolatedAsyncioTestCase):

    async def test_tool_registration_and_execution(self):
        registry = MCPRegistry()

        async def calculate_sum(a: int, b: int) -> int:
            return a + b

        registry.register_tool(
            name="add",
            description="Add two integers",
            input_schema={
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"},
                },
                "required": ["a", "b"],
            },
            handler=calculate_sum,
            allow_default=True,
        )

        client = MCPClient(registry)

        # 1. Test tools/list
        tools = await client.list_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["name"], "add")

        # 2. Test tools/call
        result = await client.call_tool("add", {"a": 15, "b": 27})
        self.assertEqual(result, "42")

    async def test_resource_registration_and_read(self):
        registry = MCPRegistry()

        async def get_system_status() -> str:
            return "ALL_SYSTEMS_NOMINAL"

        registry.register_resource(
            uri="status://health",
            name="System Health",
            description="Returns current node health",
            handler=get_system_status,
        )

        client = MCPClient(registry)

        # 1. Test resources/list
        resources = await client.list_resources()
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0]["uri"], "status://health")

        # 2. Test resources/read
        content = await client.read_resource("status://health")
        self.assertEqual(content, "ALL_SYSTEMS_NOMINAL")

    async def test_error_handling(self):
        registry = MCPRegistry()
        client = MCPClient(registry)

        # Calling non-existent tool should raise RuntimeError
        with self.assertRaises(RuntimeError) as ctx:
            await client.call_tool("non_existent_tool")
        self.assertIn("Tool 'non_existent_tool' not found", str(ctx.exception))

    async def test_tool_acl_unauthenticated_caller_denied_sensitive_tools(self):
        """SEC-03: Assert unauthenticated callers cannot call run_python or fs_write."""
        from mas.tools.executor import register_default_tools
        from mas.tools.filesystem import register_filesystem_tools

        registry = MCPRegistry()
        register_default_tools(registry)
        register_filesystem_tools(registry)
        client = MCPClient(registry)

        # 1. Unauthenticated run_python denied
        with self.assertRaises(RuntimeError) as ctx:
            await client.call_tool("run_python", {"code": "print(1)"})
        self.assertIn("ACL denied", str(ctx.exception))

        # 2. Unauthenticated fs_write denied
        with self.assertRaises(RuntimeError) as ctx:
            await client.call_tool("fs_write", {"path": "test.txt", "content": "data"})
        self.assertIn("ACL denied", str(ctx.exception))

        # 3. Safe read-only tool allowed for unauthenticated caller
        res = await client.call_tool("fs_glob", {"pattern": "*.nonexistent_mas_test"})
        self.assertIn("No matches found", res)

    async def test_tool_acl_authorized_principal_allowed_sensitive_tools(self):
        """SEC-03: Assert authorized principal can execute granted sensitive tools."""
        from mas.tools.executor import register_default_tools

        registry = MCPRegistry()
        register_default_tools(registry)
        registry.tool_acl.allow("senior_engineer", ["run_python"])
        client = MCPClient(registry)

        res = await client.call_tool(
            "run_python",
            {"code": "print(1234)"},
            principal="senior_engineer",
        )
        self.assertEqual(res.strip(), "1234")


if __name__ == "__main__":
    unittest.main()
