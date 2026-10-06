"""
mas.providers.mock_provider: Deterministic mock provider for offline testing and benchmarking.
Architect: Acinonyx
"""

from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
from mas.core.message import Message, TokenUsage
from mas.providers.base import LLMProvider, ProviderResponse


class MockLLMProvider(LLMProvider):
    """
    Deterministic LLM provider for tests, simulations, and benchmark evaluation.
    Allows registering custom response generators or rule-based triggers.
    """

    def __init__(self, default_response: str = "Mock response generated.") -> None:
        self.default_response = default_response
        self._rules: List[tuple[Callable[[List[Message]], bool], Callable[[List[Message]], ProviderResponse]]] = []

    def add_rule(
        self,
        predicate: Callable[[List[Message]], bool],
        handler: Callable[[List[Message]], ProviderResponse],
    ) -> None:
        """Register a condition-based response generator."""
        self._rules.append((predicate, handler))

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ProviderResponse:
        # Check custom rules in order of registration
        for predicate, handler in self._rules:
            if predicate(messages):
                return handler(messages)

        # Default fallback response with estimated token count
        last_msg = messages[-1].content if messages else ""
        prompt_len = sum(len(m.content.split()) for m in messages)
        completion_text = f"{self.default_response} (Re: {last_msg[:30]}...)"
        comp_len = len(completion_text.split())

        return ProviderResponse(
            content=completion_text,
            token_usage=TokenUsage.from_counts(prompt=prompt_len, completion=comp_len),
        )
