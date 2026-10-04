"""
tests/test_react_tools.py: Comprehensive unit and integration tests for external tool calling.
Tests sandboxed Python execution, live web search, ReAct tool extraction, and agent loop execution.

Architect: Acinonyx
"""

import asyncio
import os
import unittest
from mas.core.agent import BaseAgent, _extract_text_tool_calls
from mas.core.message import ContentType, Message, Role, TokenUsage
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.providers.base import LLMProvider, ProviderResponse, ToolCall
from mas.tools.browser_tool import register_browser_tools, web_search_tool
from mas.tools.executor import register_default_tools, run_python_code


class MockReActProvider(LLMProvider):
    """Mock LLM provider that simulates a 2-turn ReAct reasoning loop."""

    def __init__(self, tool_to_call: str, tool_args: dict, final_answer: str):
        self.tool_to_call = tool_to_call
        self.tool_args = tool_args
        self.final_answer = final_answer
        self.call_count = 0

    async def generate(self, messages, tools=None, **kwargs) -> ProviderResponse:
        self.call_count += 1
        if self.call_count == 1:
            # Turn 1: Emit tool call
            return ProviderResponse(
                content=f'```json\n{{"tool": "{self.tool_to_call}", "arguments": {{"code": "{self.tool_args.get("code", "")}"}}}}\n```',
                token_usage=TokenUsage(prompt_tokens=20, completion_tokens=30, total_tokens=50),
            )
        else:
            # Turn 2: Synthesize final answer after observing tool output
            return ProviderResponse(
                content=self.final_answer,
                token_usage=TokenUsage(prompt_tokens=60, completion_tokens=40, total_tokens=100),
            )


class TestReActTools(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.registry = MCPRegistry()
        register_default_tools(self.registry)
        register_browser_tools(self.registry)
        self.mcp_client = MCPClient(self.registry)

    async def test_run_python_sandbox_math(self):
        """Verify run_python executes safe mathematical code and returns output."""
        res = await run_python_code("print(100 * 42)")
        self.assertEqual(res.strip(), "4200")

    async def test_run_python_sandbox_forbidden_denial(self):
        """Verify run_python blocks forbidden subprocess/socket imports."""
        res = await run_python_code("import subprocess\nsubprocess.run(['ls'])")
        self.assertIn("Sandbox denied pattern matching", res)

        res2 = await run_python_code("import socket\ns = socket.socket()")
        self.assertIn("Sandbox denied pattern matching", res2)

    async def test_web_search_tool(self):
        """Verify web_search_tool returns structured results with query echo."""
        res = await web_search_tool(query="FastAPI distributed rate limiting", max_results=3)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("query"), "FastAPI distributed rate limiting")
        self.assertGreater(len(res.get("results", [])), 0)
        self.assertIn("items", res)

    def test_extract_text_tool_calls_json_block(self):
        """Verify tool extraction from markdown JSON code fences."""
        available = {"web_search", "run_python"}
        text = 'Here is the plan:\n```json\n{"tool": "run_python", "arguments": {"code": "print(42)"}}\n```'
        calls = _extract_text_tool_calls(text, available)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "run_python")
        self.assertEqual(calls[0].arguments, {"code": "print(42)"})

    def test_extract_text_tool_calls_react_action(self):
        """Verify tool extraction from Action / Action Input text patterns."""
        available = {"web_search", "run_python"}
        text = "Thought: Need to search.\nAction: web_search\nAction Input: {\"query\": \"OAuth2 best practices\"}\nObservation:"
        calls = _extract_text_tool_calls(text, available)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "web_search")
        self.assertEqual(calls[0].arguments, {"query": "OAuth2 best practices"})

    async def test_agent_react_reasoning_loop(self):
        """Verify agent executes full ReAct loop: tool call -> execution -> observation -> final answer."""
        provider = MockReActProvider(
            tool_to_call="run_python",
            tool_args={"code": "print(7 * 6)"},
            final_answer="The calculated product is 42.",
        )

        agent = BaseAgent(
            name="research_bot",
            mcp_client=self.mcp_client,
            llm_provider=provider,
        )

        msg = Message(
            sender="supervisor",
            recipient="research_bot",
            role=Role.USER,
            content="What is 7 times 6?",
        )

        response_msg = await agent.step(msg)

        # 1. Final answer matches expected synthesis
        self.assertEqual(response_msg.content, "The calculated product is 42.")
        # 2. Both turns burned tokens
        self.assertEqual(agent.total_tokens_consumed, 150)
        # 3. Provider was called exactly 2 times (Tool turn + Final turn)
        self.assertEqual(provider.call_count, 2)

        # 4. Working memory contains the full provenance: User -> Assistant -> Tool -> Assistant
        context = agent.working_memory.get_context()
        roles = [m.role for m in context]
        self.assertIn(Role.USER, roles)
        self.assertIn(Role.ASSISTANT, roles)
        self.assertIn(Role.TOOL, roles)

        # 5. Tool result contained '42'
        tool_msgs = [m for m in context if m.role == Role.TOOL]
        self.assertTrue(any("42" in m.content for m in tool_msgs))


if __name__ == "__main__":
    unittest.main()
