"""
mas.providers.base: Abstract LLM provider interface and response schemas.
Architect: Acinonyx
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from mas.core.message import Message, TokenUsage


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ProviderResponse:
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    token_usage: Optional[TokenUsage] = None
    finish_reason: str = "stop"


class LLMProvider(ABC):
    """Abstract interface for LLM inference providers."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ProviderResponse:
        """Generate a response given context messages and optional tool definitions."""
        pass
