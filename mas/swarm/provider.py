"""Live OpenAI-compatible provider, explicit errors and measured usage."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from .contracts import SwarmError, canonical, exact_keys, strict_json, text
from .process import run_process


class LiveProvider:
    def __init__(self, url: str, model: str, api_key: str):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise SwarmError("Provider requires an operator-configured HTTPS endpoint")
        text(model, "model", 128)
        text(api_key, "provider credential", 4096)
        self.url, self.model, self._key = url.rstrip("/"), model, api_key

    async def check_model(self, *, timeout: float = 15):
        payload = canonical({"operation": "models", "url": self.url, "key": self._key, "timeout": timeout}).encode()
        names = {
            "PATH",
            "LANG",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "no_proxy",
        }
        rc, stdout, _ = await run_process(
            [sys.executable, "-I", str(Path(__file__).with_name("provider_worker.py"))],
            data=payload,
            timeout=timeout,
            output_limit=32768,
            env={k: v for k, v in os.environ.items() if k in names},
        )
        if rc:
            raise SwarmError("Authenticated model discovery failed")
        models = exact_keys(strict_json(stdout), {"models"})["models"]
        if not isinstance(models, list) or self.model not in models:
            raise SwarmError("Requested model ID is unavailable; no silent substitution")
        return {"url": self.url, "model": self.model}

    async def complete(self, messages: list[dict], *, max_tokens: int, timeout: float, output_limit: int):
        payload = canonical(
            {"url": self.url, "model": self.model, "key": self._key, "messages": messages, "max_tokens": max_tokens, "timeout": timeout}
        ).encode()
        if len(payload) > 131072:
            raise SwarmError("Provider request exceeds byte limit")
        # This trusted subprocess needs proxy/CA configuration, not the rest of
        # the coordinator's credentials. The candidate never sees any of it.
        names = {
            "PATH",
            "LANG",
            "SSL_CERT_FILE",
            "SSL_CERT_DIR",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "NO_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "no_proxy",
        }
        env = {k: v for k, v in os.environ.items() if k in names}
        rc, stdout, _ = await run_process(
            [sys.executable, "-I", str(Path(__file__).with_name("provider_worker.py"))],
            data=payload,
            timeout=timeout,
            output_limit=output_limit,
            env=env,
        )
        if rc:
            failure = strict_json(stdout)
            category = failure.get("error") if isinstance(failure, dict) else None
            allowed = {"request", "response_json", "completion_schema", "incomplete_completion", "http_error"}
            category = category if category in allowed else "unknown"
            status = failure.get("status") if isinstance(failure, dict) else None
            status = status if type(status) is int and 100 <= status <= 599 else None
            raise SwarmError(f"Live provider failed ({category}, status={status}); no simulated success fallback")
        response = exact_keys(strict_json(stdout), {"content", "usage"})
        text(response["content"], "model output", output_limit)
        usage = response["usage"]
        if not isinstance(usage, dict):
            raise SwarmError("Provider must supply actual usage")
        counts = [usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")]
        # Gemini may charge thinking tokens in total_tokens without including
        # them in visible completion_tokens. Charge the full reported total;
        # never accept a total lower than the visible components.
        if any(type(x) is not int or x < 0 for x in counts) or counts[2] < counts[0] + counts[1] or counts[1] > max_tokens:
            raise SwarmError("Invalid provider token usage")
        return response["content"], counts[2]
