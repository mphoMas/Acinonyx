"""
mas.providers.claude_provider: Anthropic Claude LLM Provider (Zero-Dependency REST).
Supports Claude 3.7 Sonnet, Claude 3.5 Sonnet, Haiku, tools, system prompts, and token tracking.

Architect: Acinonyx
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from mas.core.message import Message, Role, TokenUsage
from mas.providers.base import LLMProvider, ProviderResponse, ToolCall


class ClaudeProvider(LLMProvider):
    """
    Direct REST provider for Anthropic Claude models via Messages API.
    Zero external dependencies, supports system prompts, tools, and token metrics.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "claude-3-5-sonnet-20241022",
        timeout_sec: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        self.model_name = model_name
        self.timeout_sec = timeout_sec

    def _sync_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body)

    async def generate(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ProviderResponse:
        if not self.api_key:
            return ProviderResponse(
                content="CLAUDE_ERROR: ANTHROPIC_API_KEY or CLAUDE_API_KEY is not set in environment or constructor.",
                finish_reason="error",
            )

        api_messages = []
        system_prompt = None

        for m in messages:
            if m.role == Role.SYSTEM and system_prompt is None:
                system_prompt = m.content
                continue

            claude_role = "assistant" if m.role in (Role.ASSISTANT, Role.CRITIC) else "user"
            api_messages.append({
                "role": claude_role,
                "content": m.content,
            })

        if not api_messages:
            api_messages.append({"role": "user", "content": "Hello"})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": api_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        # Map tools if provided
        if tools:
            formatted_tools = []
            for t in tools:
                formatted_tools.append({
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "input_schema": t.get("inputSchema", {}),
                })
            payload["tools"] = formatted_tools

        try:
            raw_response = await asyncio.to_thread(self._sync_request, payload)
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace") if hasattr(he, "read") else str(he)
            return ProviderResponse(
                content=f"CLAUDE_HTTP_ERROR: HTTP {he.code}: {err_body}",
                finish_reason="error",
            )
        except urllib.error.URLError as ue:
            return ProviderResponse(
                content=f"CLAUDE_NETWORK_ERROR: {ue.reason}",
                finish_reason="error",
            )
        except Exception as exc:
            return ProviderResponse(
                content=f"CLAUDE_UNEXPECTED_ERROR: {str(exc)}",
                finish_reason="error",
            )

        # Parse Anthropic content blocks
        text_content = ""
        tool_calls: List[ToolCall] = []

        for block in raw_response.get("content", []):
            if block.get("type") == "text":
                text_content += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", "call_claude"),
                        name=block.get("name", ""),
                        arguments=block.get("input", {}),
                    )
                )

        # Usage
        usage = raw_response.get("usage", {})
        token_usage = None
        if usage:
            prompt_tokens = usage.get("input_tokens", 0)
            completion_tokens = usage.get("output_tokens", 0)
            token_usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

        return ProviderResponse(
            content=text_content,
            tool_calls=tool_calls,
            token_usage=token_usage,
            finish_reason=raw_response.get("stop_reason", "stop"),
        )
