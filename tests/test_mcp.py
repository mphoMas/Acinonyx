"""
Tests for mas.mcp (JSON-RPC 2.0 protocol and MCP Client/Server).
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


if __name__ == "__main__":
    unittest.main()
