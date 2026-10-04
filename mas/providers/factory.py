"""
mas.providers.factory: Universal LLM Provider Factory and Auto-Discovery Engine.
Dynamically resolves and instantiates Gemini, Claude, Hugging Face, or OpenAI providers.

Architect: Acinonyx
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from mas.providers.base import LLMProvider
from mas.providers.claude_provider import ClaudeProvider
from mas.providers.gemini_provider import GeminiProvider
from mas.providers.hf_provider import HuggingFaceProvider
from mas.providers.http_provider import OpenAICompatibleProvider
from mas.providers.mock_provider import MockLLMProvider

logger = logging.getLogger("mas.providers")


def create_llm_provider(
    provider_name: str = "auto",
    model_name: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs,
) -> LLMProvider:
    """
    Factory function to instantiate an LLMProvider based on explicit name or auto-discovery.

    Supported provider_name values:
    - "gemini" | "google"
    - "claude" | "anthropic"
    - "huggingface" | "hf"
    - "openai" | "ollama"
    - "mock" | "demo"
    - "auto" (inspects environment variables in prioritized order)
    """
    name_lower = provider_name.strip().lower()

    if name_lower in ("gemini", "google"):
        return GeminiProvider(
            api_key=api_key,
            model_name=model_name or "gemini-3.8-flash",
            **kwargs,
        )

    if name_lower in ("claude", "anthropic"):
        return ClaudeProvider(
            api_key=api_key,
            model_name=model_name or "claude-3-5-sonnet-20241022",
            **kwargs,
        )

    if name_lower in ("huggingface", "hf"):
        return HuggingFaceProvider(
            token=api_key,
            model_name=model_name or "meta-llama/Llama-3.3-70B-Instruct",
            **kwargs,
        )

    if name_lower in ("openai", "ollama", "vllm"):
        return OpenAICompatibleProvider(
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
            model_name=model_name or "gpt-4o",
            **kwargs,
        )

    if name_lower in ("mock", "demo", "offline"):
        return MockLLMProvider(**kwargs)

    # -------------------------------------------------------------------------
    # Auto-Discovery Mode: inspect environment keys
    # -------------------------------------------------------------------------
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        logger.info("AutoLLMProvider: Auto-detected Gemini credentials.")
        return GeminiProvider(model_name=model_name or "gemini-3.8-flash", **kwargs)

    if os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY"):
        logger.info("AutoLLMProvider: Auto-detected Claude credentials.")
        return ClaudeProvider(model_name=model_name or "claude-3-5-sonnet-20241022", **kwargs)

    if os.getenv("OPENAI_API_KEY"):
        logger.info("AutoLLMProvider: Auto-detected OpenAI credentials.")
        return OpenAICompatibleProvider(
            base_url=kwargs.get("base_url", "https://api.openai.com/v1"),
            model_name=model_name or "gpt-4o",
            **kwargs,
        )

    if os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN"):
        logger.info("AutoLLMProvider: Auto-detected Hugging Face token.")
        return HuggingFaceProvider(model_name=model_name or "meta-llama/Llama-3.3-70B-Instruct", **kwargs)

    # Fallback to Mock/Offline provider if no live API keys are found
    logger.warning("AutoLLMProvider: No live LLM API keys detected. Falling back to MockLLMProvider.")
    return MockLLMProvider(**kwargs)
