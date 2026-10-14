"""Bounded, offline-first JWKS retrieval and cache with single-flight refresh and strict RSA validation."""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from typing import Callable

from cryptography.hazmat.primitives.asymmetric import rsa

from mas.pm.gateway.models import (
    DEFAULT_CACHE_TTL,
    FAILED_FETCH_COOLDOWN,
    MAX_JWKS_BYTES,
    MAX_JWKS_KEYS,
    UNKNOWN_KID_COOLDOWN,
    GatewayError,
)

logger = logging.getLogger(__name__)

GITHUB_JWKS_URL = "https://token.actions.githubusercontent.com/.well-known/jwks"


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """JSON object_pairs_hook enforcing uniqueness of all object keys."""
    res: dict[str, object] = {}
    for k, v in pairs:
        if k in res:
            raise ValueError(f"Duplicate JSON key: {k!r}")
        res[k] = v
    return res


def parse_nonfinite(c: str) -> object:
    """JSON parse_constant hook rejecting nonfinite numbers (NaN, Infinity)."""
    raise ValueError(f"Nonfinite numeric constants are forbidden in JSON: {c!r}")


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Refuses all HTTP redirects to prevent SSRF and open redirect vulnerabilities."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def default_jwks_fetcher(url: str) -> bytes:
    """Fixed-endpoint, TLS-verified HTTP GET with 64 KiB stream limit and zero redirects."""
    if url != GITHUB_JWKS_URL:
        raise GatewayError(f"Untrusted JWKS endpoint: {url!r}", status_code=503, code="JWKS_UNAVAILABLE")

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "MAS-Coordinator-Gateway/1.0", "Accept": "application/json"},
    )
    opener = urllib.request.build_opener(NoRedirectHandler)
    try:
        with opener.open(req, timeout=5.0) as resp:
            data = resp.read(MAX_JWKS_BYTES + 1)
            if len(data) > MAX_JWKS_BYTES:
                raise GatewayError(f"JWKS response exceeded {MAX_JWKS_BYTES} bytes", status_code=503, code="JWKS_UNAVAILABLE")
            return data
    except Exception as exc:
        logger.warning("JWKS HTTP fetch failed: %s", exc)
        raise GatewayError(f"JWKS endpoint fetch failed: {exc}", status_code=503, code="JWKS_UNAVAILABLE") from exc


def b64url_to_int(s: str) -> int:
    """Decode base64url-encoded string to integer."""
    padded = s + "=" * (-len(s) % 4)
    data = base64.urlsafe_b64decode(padded)
    return int.from_bytes(data, byteorder="big")


class JWKSCache:
    """Thread-safe bounded JWKS cache enforcing 24h TTL, single-flight refresh, and cool-down."""

    def __init__(
        self,
        endpoint_url: str = GITHUB_JWKS_URL,
        *,
        cache_ttl: float = DEFAULT_CACHE_TTL,
        unknown_kid_cooldown: float = UNKNOWN_KID_COOLDOWN,
        failed_fetch_cooldown: float = FAILED_FETCH_COOLDOWN,
        fetcher: Callable[[str], bytes] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.cache_ttl = cache_ttl
        self.unknown_kid_cooldown = unknown_kid_cooldown
        self.failed_fetch_cooldown = failed_fetch_cooldown
        self._fetcher = fetcher or default_jwks_fetcher
        self._clock = clock
        self._lock = threading.Lock()

        # State
        self._keys: dict[str, rsa.RSAPublicKey] = {}
        self._last_fetched_at: float = 0.0
        self._last_failed_at: float = 0.0

    @property
    def key_count(self) -> int:
        return len(self._keys)

    def get_key(self, kid: str) -> rsa.RSAPublicKey:
        """Retrieve an RSA public key by kid, triggering single-flight refresh when appropriate."""
        if not kid or not isinstance(kid, str) or len(kid) > 128:
            raise GatewayError("Missing or invalid kid in token header", status_code=401, code="INVALID_JWT_HEADER")

        now = self._clock()

        # 1. Fast path: key in fresh cache
        if kid in self._keys and (now - self._last_fetched_at) < self.cache_ttl:
            return self._keys[kid]

        # 2. Acquire lock for single-flight refresh
        with self._lock:
            now = self._clock()

            # Double check if another thread refreshed it
            if kid in self._keys and (now - self._last_fetched_at) < self.cache_ttl:
                return self._keys[kid]

            # Outage throttling
            if (now - self._last_failed_at) < self.failed_fetch_cooldown:
                raise GatewayError("JWKS endpoint is temporarily unavailable (cooldown active)", status_code=503, code="JWKS_UNAVAILABLE")

            # Unknown key throttling when cache is fresh
            cache_is_fresh = self._last_fetched_at > 0 and (now - self._last_fetched_at) < self.cache_ttl
            if cache_is_fresh and kid not in self._keys:
                if (now - self._last_fetched_at) < self.unknown_kid_cooldown:
                    raise GatewayError(
                        f"Unknown key ID {kid!r}; refresh throttled ({self.unknown_kid_cooldown}s cooldown)",
                        status_code=401,
                        code="UNKNOWN_KEY_THROTTLED",
                    )

            # Perform bounded fetch
            try:
                raw_bytes = self._fetcher(self.endpoint_url)
                new_keys = self._parse_and_validate_jwks(raw_bytes)
                self._keys = new_keys
                self._last_fetched_at = now
            except GatewayError as exc:
                self._last_failed_at = now
                raise exc
            except Exception as exc:
                self._last_failed_at = now
                raise GatewayError(f"JWKS resolution failed: {exc}", status_code=503, code="JWKS_UNAVAILABLE") from exc

            if kid not in self._keys:
                raise GatewayError(f"Key ID {kid!r} not found in JWKS", status_code=401, code="UNKNOWN_KEY_ID")

            return self._keys[kid]

    def _parse_and_validate_jwks(self, raw_bytes: bytes) -> dict[str, rsa.RSAPublicKey]:
        """Strictly parse JWKS response, enforcing key count, duplicate rejection, and RSA bounds."""
        if len(raw_bytes) > MAX_JWKS_BYTES:
            raise GatewayError(f"JWKS response exceeded {MAX_JWKS_BYTES} bytes", status_code=503, code="JWKS_UNAVAILABLE")

        try:
            text = raw_bytes.decode("utf-8")
            payload = json.loads(text, object_pairs_hook=reject_duplicate_keys, parse_constant=parse_nonfinite)
        except Exception as exc:
            raise GatewayError(f"Malformed JWKS JSON: {exc}", status_code=503, code="JWKS_UNAVAILABLE") from exc

        if not isinstance(payload, dict) or "keys" not in payload:
            raise GatewayError("JWKS payload must be a JSON object containing a 'keys' list", status_code=503, code="JWKS_UNAVAILABLE")

        keys_list = payload["keys"]
        if not isinstance(keys_list, list):
            raise GatewayError("JWKS 'keys' must be a list", status_code=503, code="JWKS_UNAVAILABLE")

        if len(keys_list) > MAX_JWKS_KEYS:
            raise GatewayError(f"JWKS key count exceeds limit of {MAX_JWKS_KEYS}", status_code=503, code="JWKS_UNAVAILABLE")

        parsed_keys: dict[str, rsa.RSAPublicKey] = {}
        for entry in keys_list:
            if not isinstance(entry, dict):
                continue

            kid = entry.get("kid")
            if not isinstance(kid, str) or not kid.strip():
                continue

            if kid in parsed_keys:
                raise GatewayError(f"Duplicate kid {kid!r} detected in JWKS response", status_code=503, code="JWKS_UNAVAILABLE")

            # Validate key metadata
            kty = entry.get("kty")
            if kty != "RSA":
                continue  # Skip or ignore non-RSA keys safely

            use = entry.get("use")
            if use is not None and use != "sig":
                continue  # Key not designated for signatures

            n_str = entry.get("n")
            e_str = entry.get("e")
            if not isinstance(n_str, str) or not isinstance(e_str, str):
                continue

            try:
                n = b64url_to_int(n_str)
                e = b64url_to_int(e_str)

                # RSA Parameter constraints
                modulus_bits = n.bit_length()
                if not (2048 <= modulus_bits <= 4096):
                    logger.warning("Ignoring RSA key with unsupported modulus size %d bits", modulus_bits)
                    continue

                if not (3 <= e <= 65537):
                    logger.warning("Ignoring RSA key with unsupported exponent %d", e)
                    continue

                public_key = rsa.RSAPublicNumbers(e, n).public_key()
                parsed_keys[kid] = public_key
            except Exception as exc:
                logger.warning("Failed to construct RSA public key for kid %s: %s", kid, exc)
                continue

        if not parsed_keys:
            raise GatewayError("JWKS response contained no valid RSA public keys", status_code=503, code="JWKS_UNAVAILABLE")

        return parsed_keys
