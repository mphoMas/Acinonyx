"""
tests.test_live_gateway: Test suite verifying the OpenAI-compatible Live Model Gateway and enterprise wiring.
Architect: Acinonyx
"""

import unittest
from mas.core.message import Message, Role
from mas.organization.company import ConsultingEnterprise
from mas.organization.engagement import ConsultingEngagement
from mas.providers.gateway import ModelGatewayServer
from mas.providers.http_provider import OpenAICompatibleProvider


class TestLiveModelGateway(unittest.IsolatedAsyncioTestCase):
    gateway_server: ModelGatewayServer = None
    gateway_port = 8099

    @classmethod
    def setUpClass(cls):
        cls.gateway_server = ModelGatewayServer(port=cls.gateway_port)
        cls.gateway_server.start_background()
        # Give server a moment to bind
        import time
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        if cls.gateway_server:
            cls.gateway_server.shutdown()

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
        self.assertNotIn("PROVIDER_CONNECTION_ERROR", resp.content)
        self.assertNotIn("PROVIDER_REQUEST_ERROR", resp.content)
        self.assertTrue(len(resp.content) > 0)
        self.assertIsNotNone(resp.token_usage)
        self.assertGreater(resp.token_usage.total_tokens, 0)

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

        # Execute an end-to-end consulting engagement powered by live gateway
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
