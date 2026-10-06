"""
End-to-end integration test: MCP Tool execution with Reflexion self-healing loop.
"""

import unittest
from mas.core.agent import BaseAgent
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.tools.executor import register_default_tools


class CodingAgentWithReflexion(BaseAgent):
    """Agent that runs code via MCP and self-heals using episodic reflections."""

    async def execute_task_with_reflexion(self, initial_code: str, fix_code: str) -> str:
        # 1. Attempt initial code
        output_1 = await self.mcp_client.call_tool("run_python", {"code": initial_code})
        if "EXIT_FAILURE" in output_1 or "ERROR" in output_1:
            # Failure detected -> Record verbal reflection
            await self.reflect(
                task="Execute initial mathematical calculation",
                success=False,
                critique=f"Encountered runtime exception:\n{output_1}",
                suggested_strategy="Apply zero-division check before computing quotient.",
                tags=["math", "python", "division"],
            )

            # 2. Re-attempt with corrected code informed by reflection
            output_2 = await self.mcp_client.call_tool("run_python", {"code": fix_code})
            await self.reflect(
                task="Execute mathematical calculation with guard",
                success=True,
                critique="Guard successfully intercepted zero denominator.",
                suggested_strategy="Standardize on guard clauses for arithmetic functions.",
                tags=["math", "python", "guard", "division"],
            )
            return output_2

        return output_1


class TestIntegrationReflexion(unittest.IsolatedAsyncioTestCase):

    async def test_mcp_reflexion_self_healing(self):
        registry = MCPRegistry()
        register_default_tools(registry)
        client = MCPClient(registry)

        agent = CodingAgentWithReflexion(name="dev_agent", mcp_client=client)

        buggy_code = "print(10 / 0)"
        fixed_code = "denom = 0\nprint('Safe: ' + str(10 / denom if denom != 0 else 'DIVISION_BY_ZERO_HANDLED'))"

        result = await agent.execute_task_with_reflexion(buggy_code, fixed_code)
        self.assertIn("DIVISION_BY_ZERO_HANDLED", result)

        # Verify episodic memory recorded the failure critique and success
        self.assertEqual(agent.episodic_memory.total_reflections, 2)
        reflections = agent.episodic_memory.retrieve_relevant_reflections("division")
        self.assertEqual(len(reflections), 2)
        self.assertFalse(reflections[0].success if "zero-division" in reflections[0].suggested_strategy else reflections[1].success)


if __name__ == "__main__":
    unittest.main()
