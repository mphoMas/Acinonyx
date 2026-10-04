"""
tests/test_live_providers.py: Unit tests for Gemini, Claude, and Hugging Face LLM Providers.
Validates formatting, error boundaries, factory routing, and enterprise attachment.
"""

import asyncio
import os
import unittest
from mas.core.message import Message, Role
from mas.organization.company import AcinonyxEnterprise
from mas.providers import (
    ClaudeProvider,
    GeminiProvider,
    HuggingFaceProvider,
    MockLLMProvider,
    OpenAICompatibleProvider,
    create_llm_provider,
)


class TestLiveLLMProviders(unittest.IsolatedAsyncioTestCase):

    def test_factory_instantiation(self):
        """Verify universal factory creates proper provider instances."""
        gemini = create_llm_provider("gemini", api_key="dummy_gemini_key")
        self.assertIsInstance(gemini, GeminiProvider)
        self.assertEqual(gemini.api_key, "dummy_gemini_key")

        claude = create_llm_provider("claude", api_key="dummy_claude_key")
        self.assertIsInstance(claude, ClaudeProvider)
        self.assertEqual(claude.api_key, "dummy_claude_key")

        hf = create_llm_provider("huggingface", api_key="dummy_hf_token")
        self.assertIsInstance(hf, HuggingFaceProvider)
        self.assertEqual(hf.token, "dummy_hf_token")

        openai = create_llm_provider("openai", api_key="dummy_openai_key")
        self.assertIsInstance(openai, OpenAICompatibleProvider)

        mock = create_llm_provider("mock")
        self.assertIsInstance(mock, MockLLMProvider)

    async def test_gemini_provider_error_boundary_no_key(self):
        """Verify GeminiProvider handles missing API key gracefully."""
        # Unset keys if in env for test isolation
        gemini = GeminiProvider(api_key=None)
        # Force None in case env had something
        gemini.api_key = None
        msgs = [Message(sender="user", recipient="gemini", role=Role.USER, content="Hello")]
        resp = await gemini.generate(msgs)
        self.assertEqual(resp.finish_reason, "error")
        self.assertIn("GEMINI_ERROR", resp.content)

    async def test_claude_provider_error_boundary_no_key(self):
        """Verify ClaudeProvider handles missing API key gracefully."""
        claude = ClaudeProvider(api_key=None)
        claude.api_key = None
        msgs = [Message(sender="user", recipient="claude", role=Role.USER, content="Hello")]
        resp = await claude.generate(msgs)
        self.assertEqual(resp.finish_reason, "error")
        self.assertIn("CLAUDE_ERROR", resp.content)

    async def test_hf_provider_error_boundary_no_token(self):
        """Verify HuggingFaceProvider handles missing token gracefully."""
        hf = HuggingFaceProvider(token=None)
        hf.token = None
        msgs = [Message(sender="user", recipient="hf", role=Role.USER, content="Hello")]
        resp = await hf.generate(msgs)
        self.assertEqual(resp.finish_reason, "error")
        self.assertIn("HF_ERROR", resp.content)

    def test_enterprise_attach_provider(self):
        """Verify attach_llm_provider wires the provider across all 7 Capability Guilds."""
        enterprise = AcinonyxEnterprise()
        provider = GeminiProvider(api_key="test-key")

        enterprise.attach_llm_provider(provider)

        # Check key agents across departments have the provider attached
        self.assertIs(enterprise.market_researcher.llm_provider, provider)
        self.assertIs(enterprise.chief_architect.llm_provider, provider)
        self.assertIs(enterprise.backend_engineer.llm_provider, provider)
        self.assertIs(enterprise.adversarial_red_team.llm_provider, provider)
        self.assertIs(enterprise.qa_critic.llm_provider, provider)
        self.assertIs(enterprise.finops_governor.llm_provider, provider)


if __name__ == "__main__":
    unittest.main()
