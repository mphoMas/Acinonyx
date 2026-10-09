"""
Local scripted gateway transport and enterprise wiring; not live model-quality evidence.
Architect: Acinonyx
"""

import unittest
import os
from unittest.mock import patch
from mas.core.message import Message, Role
from mas.organization.company import ConsultingEnterprise
from mas.organization.engagement import ConsultingEngagement
from mas.providers.gateway import ModelGatewayRequestHandler, ModelGatewayServer, TokenBudgetGovernor
from mas.providers.http_provider import OpenAICompatibleProvider


class TestLiveModelGateway(unittest.IsolatedAsyncioTestCase):
    gateway_server: ModelGatewayServer = None
    def setUp(self):
        # Each case owns a normal budget. An earlier demo must not consume the
        # transport case's quota; operator environment cannot arm fixture calls.
        environment = patch.dict(os.environ, {"OPENAI_BASE_URL": "", "OPENAI_API_KEY": ""})
        environment.start()
        self.addCleanup(environment.stop)
        budget = patch.object(ModelGatewayRequestHandler, "governor", TokenBudgetGovernor())
        budget.start()
        self.addCleanup(budget.stop)
        self.gateway_server = ModelGatewayServer(port=0)
        self.addCleanup(self.gateway_server.shutdown)
        self.gateway_port = self.gateway_server.server.server_address[1]
        self.gateway_server.start_background()

    async def test_openai_compatible_provider_live_generation(self):
        provider = OpenAICompatibleProvider(
            base_url=f"http://127.0.0.1:{self.gateway_port}/v1",
            model_name="acinonyx-core-v1",
        )

        messages = [
            Message(role=Role.SYSTEM, content="You are a senior software engineer."),
            Message(role=Role.USER, content="Implement a high-throughput async queue in Python."),
        ]

        resp = await provider.generate(messages)
        self.assertNotEqual(resp.finish_reason, "error", resp.content)
        self.assertNotIn("PROVIDER_CONNECTION_ERROR", resp.content)
        self.assertNotIn("PROVIDER_REQUEST_ERROR", resp.content)
        self.assertTrue(len(resp.content) > 0)
        self.assertIsNotNone(resp.token_usage)
        self.assertGreater(resp.token_usage.total_tokens, 0)

    async def test_fixture_budget_exhaustion_returns_error_without_usage(self):
        ModelGatewayRequestHandler.governor.max_total_tokens = 0
        provider = OpenAICompatibleProvider(base_url=f"http://127.0.0.1:{self.gateway_port}/v1")
        response = await provider.generate([Message(role=Role.USER, content="Return input")])
        self.assertEqual(response.finish_reason, "error")
        self.assertIn("HTTP 429", response.content)
        self.assertIsNone(response.token_usage)

    async def test_enterprise_wired_with_live_gateway(self):
        enterprise = ConsultingEnterprise(name="Cognitive Enterprise Corp")
        provider = OpenAICompatibleProvider(
            base_url=f"http://127.0.0.1:{self.gateway_port}/v1",
            model_name="acinonyx-core-v1",
        )
        enterprise.attach_llm_provider(provider)

        # Confirm all department agents have the provider attached
        for dept in enterprise.departments.values():
            for agent in dept.members.values():
                self.assertIsNotNone(agent.llm_provider, f"Agent {agent.name} missing provider")

        # Exercise scripted fixture wiring; artifact shape is not quality evidence.
        engagement = ConsultingEngagement(enterprise)
        artifacts = await engagement.execute_engagement(
            client_name="OmniHealth SaaS",
            raw_rfp="Need an enterprise HIPAA telehealth platform with real-time video and encrypted audit trails.",
        )

        self.assertIn("OmniHealth", artifacts.client_name)
        self.assertTrue(len(artifacts.client_brief) > 0)
        self.assertTrue(len(artifacts.prd) > 0)
        self.assertTrue(len(artifacts.design_system) > 0)
        self.assertTrue(len(artifacts.engineering_summary) > 0)


if __name__ == "__main__":
    unittest.main()
