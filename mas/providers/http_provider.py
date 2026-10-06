"""
mas.providers.http_provider: Dependency-free async HTTP provider for OpenAI/Ollama compatible endpoints.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from mas.core.message import ContentType, Message, TokenUsage
from mas.providers.base import LLMProvider, ProviderResponse, ToolCall


class OpenAICompatibleProvider(LLMProvider):
    """
    HTTP provider for OpenAI, Ollama, vLLM, or other OpenAI-compatible REST endpoints.
    Uses standard library urllib wrapped in asyncio.to_thread for zero-dependency portability.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        api_key: Optional[str] = None,
        model_name: str = "llama3",
        timeout_sec: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "no-key-required"
        self.model_name = model_name
        self.timeout_sec = timeout_sec

    def _sync_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        # Automatically bypass system proxy for loopback/localhost requests
        if "127.0.0.1" in url or "localhost" in url:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(req, timeout=self.timeout_sec) as response:
                res_body = response.read().decode("utf-8")
                return json.loads(res_body)
        else:
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
        # Convert MAS messages to OpenAI chat format
        api_messages = []
        for m in messages:
            content_payload: Any = m.content
            if isinstance(m.content, list):
                content_payload = m.content
            elif getattr(m, "content_type", None) == ContentType.IMAGE and isinstance(m.content, str):
                url = m.content
                if not (url.startswith("http://") or url.startswith("https://") or url.startswith("data:image")):
                    url = f"data:image/webp;base64,{m.content}"
                content_payload = [
                    {"type": "image_url", "image_url": {"url": url}}
                ]
            api_messages.append({
                "role": m.role.value if m.role.value in ("system", "user", "assistant") else "assistant",
                "content": content_payload,
            })

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": temperature,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        # Map tools if provided
        if tools:
            formatted_tools = []
            for t in tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": t.get("inputSchema", {}),
                    },
                })
            payload["tools"] = formatted_tools

        try:
            raw_response = await asyncio.to_thread(self._sync_request, payload)
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="replace") if hasattr(he, "read") else str(he)
            return ProviderResponse(
                content=f"PROVIDER_HTTP_ERROR: HTTP {he.code}: {err_body}",
                finish_reason="error",
            )
        except urllib.error.URLError as e:
            return ProviderResponse(
                content=f"PROVIDER_CONNECTION_ERROR: Failed to connect to '{self.base_url}': {str(e)}",
                finish_reason="error",
            )
        except Exception as ex:
            return ProviderResponse(
                content=f"PROVIDER_REQUEST_ERROR: {str(ex)}",
                finish_reason="error",
            )

        # Parse choices and tool calls
        choices = raw_response.get("choices", [])
        if not choices:
            return ProviderResponse(content="", finish_reason="empty")

        first_choice = choices[0]
        msg_obj = first_choice.get("message", {})
        content = msg_obj.get("content") or ""

        tool_calls = []
        raw_tc = msg_obj.get("tool_calls") or []
        for tc in raw_tc:
            fn = tc.get("function", {})
            args_str = fn.get("arguments", "{}")
            try:
                parsed_args = json.loads(args_str)
            except Exception:
                parsed_args = {"raw": args_str}

            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=fn.get("name", ""),
                    arguments=parsed_args,
                )
            )

        # Parse usage
        usage_data = raw_response.get("usage", {})
        token_usage = TokenUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return ProviderResponse(
            content=content,
            tool_calls=tool_calls,
            token_usage=token_usage,
            finish_reason=first_choice.get("finish_reason", "stop"),
        )
