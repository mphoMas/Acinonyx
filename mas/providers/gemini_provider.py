"""
mas.providers.gemini_provider: Google Gemini LLM Provider (Zero-Dependency REST).
Supports Gemini 2.0 Flash, Gemini 1.5 Pro, system instructions, tools, and token metrics.

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


class GeminiProvider(LLMProvider):
    """
    Direct REST provider for Google Gemini models via generativelanguage API.
    Zero external dependencies, supports system instructions, function calling,
    and automatic token tracking.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3.8-flash",
        timeout_sec: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        self.timeout_sec = timeout_sec

    def _sync_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["x-goog-api-key"] = self.api_key

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
                content="GEMINI_ERROR: GEMINI_API_KEY or GOOGLE_API_KEY is not set in environment or constructor.",
                finish_reason="error",
            )

        contents = []
        system_instruction = None

        for m in messages:
            if m.role == Role.SYSTEM and system_instruction is None:
                system_instruction = {"parts": [{"text": m.content}]}
                continue

            gemini_role = "model" if m.role in (Role.ASSISTANT, Role.CRITIC) else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": m.content}],
            })

        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Hello"}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = system_instruction

        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        # Function/Tool declarations
        if tools:
            func_decls = []
            for t in tools:
                func_decls.append({
                    "name": t.get("name"),
                    "description": t.get("description", ""),
                    "parameters": t.get("inputSchema", {}),
                })
            payload["tools"] = [{"functionDeclarations": func_decls}]

        try:
            raw_response = await asyncio.to_thread(self._sync_request, payload)
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace") if hasattr(he, "read") else str(he)
            return ProviderResponse(
                content=f"GEMINI_HTTP_ERROR: HTTP {he.code}: {err_body}",
                finish_reason="error",
            )
        except urllib.error.URLError as ue:
            return ProviderResponse(
                content=f"GEMINI_NETWORK_ERROR: {ue.reason}",
                finish_reason="error",
            )
        except Exception as exc:
            return ProviderResponse(
                content=f"GEMINI_UNEXPECTED_ERROR: {str(exc)}",
                finish_reason="error",
            )

        # Parse response
        candidates = raw_response.get("candidates", [])
        if not candidates:
            return ProviderResponse(content="", finish_reason="stop")

        candidate = candidates[0]
        content_part = candidate.get("content", {})
        parts = content_part.get("parts", [])

        text_content = ""
        tool_calls: List[ToolCall] = []

        for p in parts:
            if "text" in p:
                text_content += p["text"]
            elif "functionCall" in p:
                fc = p["functionCall"]
                tool_calls.append(
                    ToolCall(
                        id=fc.get("name", "call_gemini"),
                        name=fc.get("name", ""),
                        arguments=fc.get("args", {}),
                    )
                )

        # Usage metadata
        usage_meta = raw_response.get("usageMetadata", {})
        token_usage = None
        if usage_meta:
            token_usage = TokenUsage(
                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                total_tokens=usage_meta.get("totalTokenCount", 0),
            )

        return ProviderResponse(
            content=text_content,
            tool_calls=tool_calls,
            token_usage=token_usage,
            finish_reason=candidate.get("finishReason", "stop"),
        )
