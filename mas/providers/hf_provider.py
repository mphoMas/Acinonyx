"""
mas.providers.hf_provider: Hugging Face Inference API LLM Provider.
Supports open-weights frontier models (Llama 3.3 70B, Qwen 2.5 Coder 32B, Mistral)
via official huggingface_hub.InferenceClient with zero-dependency REST fallback.

Architect: Acinonyx
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from mas.core.message import Message, Role, TokenUsage
from mas.providers.base import LLMProvider, ProviderResponse, ToolCall

logger = logging.getLogger("mas.providers.hf")


class HuggingFaceProvider(LLMProvider):
    """
    Inference provider for Hugging Face open-weights frontier models.
    Prioritizes huggingface_hub.InferenceClient if installed, with zero-dependency REST fallback.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        model_name: str = "meta-llama/Llama-3.3-70B-Instruct",
        endpoint_url: Optional[str] = None,
        timeout_sec: float = 90.0,
    ) -> None:
        self.token = token or os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        self.model_name = model_name
        self.endpoint_url = endpoint_url
        self.timeout_sec = timeout_sec

        self._client = None
        try:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(api_key=self.token, timeout=self.timeout_sec)
        except Exception:
            self._client = None

    def _sync_inference_client(self, api_messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> ProviderResponse:
        completion = self._client.chat.completions.create(
            model=self.model_name,
            messages=api_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = completion.choices[0]
        content_text = choice.message.content or ""
        token_usage = None
        if hasattr(completion, "usage") and completion.usage:
            token_usage = TokenUsage(
                prompt_tokens=getattr(completion.usage, "prompt_tokens", 0),
                completion_tokens=getattr(completion.usage, "completion_tokens", 0),
                total_tokens=getattr(completion.usage, "total_tokens", 0),
            )
        return ProviderResponse(
            content=content_text,
            token_usage=token_usage,
            finish_reason=choice.finish_reason or "stop",
        )

    def _sync_http_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        target_url = self.endpoint_url or f"https://router.huggingface.co/hf-inference/models/{self.model_name}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(target_url, data=data_bytes, headers=headers, method="POST")

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
        if not self.token:
            return ProviderResponse(
                content="HF_ERROR: HF_TOKEN or HUGGING_FACE_HUB_TOKEN is not set in environment or constructor.",
                finish_reason="error",
            )

        api_messages = []
        for m in messages:
            api_role = "system" if m.role == Role.SYSTEM else ("assistant" if m.role in (Role.ASSISTANT, Role.CRITIC) else "user")
            api_messages.append({"role": api_role, "content": m.content})

        if not api_messages:
            api_messages.append({"role": "user", "content": "Hello"})

        limit = max_tokens or 2048

        # Strategy 1: Use huggingface_hub.InferenceClient if available
        if self._client:
            try:
                return await asyncio.to_thread(self._sync_inference_client, api_messages, temperature, limit)
            except Exception as exc:
                logger.warning(f"InferenceClient error ({exc}), falling back to direct HTTP...")

        # Strategy 2: Fallback to direct HTTP request
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": limit,
        }

        try:
            raw_response = await asyncio.to_thread(self._sync_http_request, payload)
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace") if hasattr(he, "read") else str(he)
            return ProviderResponse(
                content=f"HF_HTTP_ERROR: HTTP {he.code}: {err_body}",
                finish_reason="error",
            )
        except urllib.error.URLError as ue:
            return ProviderResponse(
                content=f"HF_NETWORK_ERROR: {ue.reason}",
                finish_reason="error",
            )
        except Exception as exc:
            return ProviderResponse(
                content=f"HF_UNEXPECTED_ERROR: {str(exc)}",
                finish_reason="error",
            )

        choices = raw_response.get("choices", [])
        if not choices:
            return ProviderResponse(content="", finish_reason="stop")

        choice = choices[0]
        content_text = choice.get("message", {}).get("content", "")
        usage_data = raw_response.get("usage", {})
        token_usage = None
        if usage_data:
            token_usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

        return ProviderResponse(
            content=content_text,
            token_usage=token_usage,
            finish_reason=choice.get("finish_reason", "stop"),
        )
