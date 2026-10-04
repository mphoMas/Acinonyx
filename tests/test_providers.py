"""
Tests for mas.providers (MockLLMProvider, ToolCall handling in BaseAgent).
"""

import unittest
from mas.core.agent import BaseAgent
from mas.core.message import Message, Role
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.providers.base import ProviderResponse, ToolCall
from mas.providers.mock_provider import MockLLMProvider


class TestProviders(unittest.IsolatedAsyncioTestCase):

    async def test_mock_provider_fallback(self):
        provider = MockLLMProvider(default_response="Simulated AI response.")
        msg = Message(content="What is MAS?")
        resp = await provider.generate([msg])
        self.assertIn("Simulated AI response", resp.content)
        self.assertIsNotNone(resp.token_usage)

    async def test_agent_react_tool_calling_with_provider(self):
        # 1. Setup MCP with a tool
        registry = MCPRegistry()

        async def multiply(x: int, y: int) -> int:
            return x * y

        registry.register_tool(
            name="multiply",
            description="Multiply two numbers",
            input_schema={"type": "object", "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}}},
            handler=multiply,
        )
        client = MCPClient(registry)

        # 2. Setup mock provider that triggers a tool call on first turn, then final answer on second
        call_count = 0
        provider = MockLLMProvider()

        def rule_predicate(msgs):
            nonlocal call_count
            return True

        def rule_handler(msgs):
            nonlocal call_count
            call_count += 1
            # If tool result message exists in context, return final answer
            if any(m.role == Role.TOOL for m in msgs):
                return ProviderResponse(content="Final Answer: The product is 42.")
            # Otherwise request tool call
            return ProviderResponse(
                content="I need to multiply 6 and 7.",
                tool_calls=[ToolCall(id="call_1", name="multiply", arguments={"x": 6, "y": 7})],
            )

        provider.add_rule(rule_predicate, rule_handler)

        # 3. Create Agent with provider and client
        agent = BaseAgent(name="calc_agent", mcp_client=client, llm_provider=provider)
        incoming = Message(content="Calculate 6 * 7")

        response = await agent.step(incoming)
        self.assertEqual(response.content, "Final Answer: The product is 42.")
        self.assertEqual(call_count, 2)

        # Verify tool result was recorded in agent's working memory
        tool_msgs = [m for m in agent.working_memory.get_context() if m.role == Role.TOOL]
        self.assertEqual(len(tool_msgs), 1)
        self.assertIn("42", tool_msgs[0].content)


if __name__ == "__main__":
    unittest.main()
