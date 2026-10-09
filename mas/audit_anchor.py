"""Fresh, authenticated external checkpoints; no offline/cache fallback."""
from __future__ import annotations

import json
import math
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


class AnchorError(PermissionError):
    """Authority cannot be proven fresh against the independent witness."""


def checkpoint(value):
    if not isinstance(value, dict) or set(value) != {"sequence", "hash"}:
        raise AnchorError("Malformed audit checkpoint")
    seq, digest = value["sequence"], value["hash"]
    if type(seq) is not int or not 0 <= seq <= 2**63 - 1 or not isinstance(digest, str):
        raise AnchorError("Malformed audit checkpoint")
    if (seq == 0 and digest != "") or (seq > 0 and not re.fullmatch(r"[a-f0-9]{64}", digest)):
        raise AnchorError("Malformed audit checkpoint")
    return dict(value)


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise ValueError("Invalid JSON constant")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


class HTTPAuditAnchor:
    def __init__(self, url: str, namespace: str, token: str, *, timeout: float = 3):
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("Audit witness requires an HTTPS origin without credentials or query")
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", namespace):
            raise ValueError("Invalid audit witness namespace")
        if not isinstance(token, str) or not 32 <= len(token) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ValueError("Audit witness requires a private bearer credential")
        if type(timeout) not in (float, int) or not math.isfinite(timeout) or not 0 < timeout <= 10:
            raise ValueError("Audit witness deadline must be between zero and ten seconds")
        self.url, self.namespace, self._token, self.timeout = url.rstrip("/"), namespace, token, timeout

    @property
    def binding(self):
        return {"url": self.url, "namespace": self.namespace}

    def _request(self, action, **fields):
        nonce = secrets.token_hex(32)
        payload = {"url": self.url, "namespace": self.namespace, "token": self._token, "timeout": self.timeout, "request": {"action": action, "nonce": nonce, **fields}}
        allowed = {"PATH", "LANG", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE", "CODEX_PROXY_CERT"}
        environment = {name: value for name, value in os.environ.items() if name in allowed or name.startswith("CODEX_PROXY_")}
        try:
            # A trusted killable worker bounds the entire network exchange, not
            # just each socket read. Bearer credentials travel only through stdin.
            result = subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("anchor_http_worker.py"))], input=json.dumps(payload), text=True, capture_output=True, timeout=self.timeout, env=environment)
            if result.returncode != 0 or len(result.stdout) > 8192:
                raise AnchorError("Audit witness unavailable or rejected the checkpoint")
            reply = strict_json(result.stdout)
            if not isinstance(reply, dict) or set(reply) != {"namespace", "nonce", "checkpoint"} or reply["nonce"] != nonce or reply["namespace"] != self.namespace:
                raise AnchorError("Audit witness response freshness or namespace mismatch")
            return checkpoint(reply["checkpoint"])
        except AnchorError:
            raise
        except (OSError, subprocess.TimeoutExpired, ValueError, TypeError) as exc:
            raise AnchorError("Audit witness unavailable or invalid") from exc

    def verify(self, current):
        if self._request("read") != checkpoint(current):
            raise AnchorError("Identity authority differs from external audit witness")

    def advance(self, expected, target):
        expected, target = checkpoint(expected), checkpoint(target)
        if target == expected:
            self.verify(expected)
        elif self._request("advance", expected=expected, target=target) != target:
            raise AnchorError("Audit witness did not acknowledge the proposed checkpoint")
