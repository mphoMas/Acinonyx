"""Strict RS256 JWT parsing and cryptographic verification against GitHub OIDC claims."""

from __future__ import annotations

import base64
import json
import math
import re
import time
from typing import Any, Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from mas.pm.gateway.jwks import (
    JWKSCache,
    parse_nonfinite,
    reject_duplicate_keys,
)
from mas.pm.gateway.models import (
    MAX_JWT_LENGTH,
    GatewayError,
)

B64URL_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
HEX40_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGITS_PATTERN = re.compile(r"^\d+$")

REQUIRED_CLAIMS = (
    "iss",
    "aud",
    "repository_id",
    "repository_owner_id",
    "job_workflow_ref",
    "job_workflow_sha",
    "event_name",
    "ref",
    "runner_environment",
    "run_id",
    "run_attempt",
    "iat",
    "exp",
)


def b64url_decode(segment: str) -> bytes:
    """Decode base64url segment, rejecting non-base64url characters and invalid padding."""
    if not segment or not B64URL_PATTERN.fullmatch(segment):
        raise GatewayError(status_code=401, code="INVALID_JWT_FORMAT", diagnostic="Malformed base64url segment")
    padded = segment + "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(padded)
    except Exception as exc:
        raise GatewayError(status_code=401, code="INVALID_JWT_FORMAT", diagnostic=f"Base64url decoding failed: {exc}") from exc


def validate_numeric_date(val: Any, field_name: str) -> float:
    """Ensure value is a finite number, strictly rejecting booleans and non-numeric types."""
    if isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val):
        raise GatewayError(
            status_code=401,
            code="INVALID_CLAIM_TYPE",
            diagnostic=f"Field {field_name!r} must be finite numeric timestamp, got {type(val).__name__}",
        )
    return float(val)


class TokenVerifier:
    """Stateless cryptographic RS256 token parser and claims boundary validator."""

    def __init__(
        self,
        jwks_cache: JWKSCache,
        *,
        clock: Callable[[], float] = time.time,
        expected_audience: str = "mas-coordinator-delivery",
        expected_issuer: str = "https://token.actions.githubusercontent.com",
    ) -> None:
        self.jwks_cache = jwks_cache
        self.clock = clock
        self.expected_audience = expected_audience
        self.expected_issuer = expected_issuer

    def verify_token(self, token_str: str) -> dict[str, Any]:
        """Perform full cryptographic RS256 verification and strict claims inspection."""
        if not isinstance(token_str, str):
            raise GatewayError(status_code=401, code="INVALID_JWT_FORMAT", diagnostic="Token is not a string")

        if len(token_str) > MAX_JWT_LENGTH:
            raise GatewayError(
                status_code=413,
                code="PAYLOAD_TOO_LARGE",
                diagnostic=f"Token length ({len(token_str)} bytes) exceeds limit of {MAX_JWT_LENGTH} bytes",
            )

        parts = token_str.split(".")
        if len(parts) != 3:
            raise GatewayError(
                status_code=401,
                code="INVALID_JWT_FORMAT",
                diagnostic=f"JWT must contain exactly three segments, found {len(parts)}",
            )

        header_b64, payload_b64, signature_b64 = parts

        # 1. Parse header
        header_bytes = b64url_decode(header_b64)
        try:
            header_text = header_bytes.decode("utf-8")
            header = json.loads(header_text, object_pairs_hook=reject_duplicate_keys, parse_constant=parse_nonfinite)
        except Exception as exc:
            raise GatewayError(status_code=401, code="INVALID_JWT_HEADER", diagnostic=f"Malformed header JSON: {exc}") from exc

        if not isinstance(header, dict):
            raise GatewayError(status_code=401, code="INVALID_JWT_HEADER", diagnostic="JWT header must be a JSON object")

        # Disallowed and required header parameters
        allowed_headers = {"alg", "kid", "typ"}
        extra_headers = set(header.keys()) - allowed_headers
        if extra_headers:
            raise GatewayError(
                status_code=401,
                code="INVALID_JWT_HEADER",
                diagnostic=f"Disallowed header parameters in JWT: {sorted(extra_headers)}",
            )

        alg = header.get("alg")
        if alg != "RS256":
            raise GatewayError(status_code=401, code="UNSUPPORTED_ALGORITHM", diagnostic=f"Unsupported algorithm {alg!r}")

        kid = header.get("kid")
        if not kid or not isinstance(kid, str) or len(kid) > 128:
            raise GatewayError(status_code=401, code="INVALID_JWT_HEADER", diagnostic="Missing or invalid kid in header")

        typ = header.get("typ")
        if typ is not None and str(typ).upper() != "JWT":
            raise GatewayError(status_code=401, code="INVALID_JWT_HEADER", diagnostic=f"Unsupported typ {typ!r}")

        # 2. Cryptographic signature check
        public_key = self.jwks_cache.get_key(kid)
        signed_data = f"{header_b64}.{payload_b64}".encode("ascii")
        signature_bytes = b64url_decode(signature_b64)

        try:
            public_key.verify(signature_bytes, signed_data, padding.PKCS1v15(), hashes.SHA256())
        except InvalidSignature as exc:
            raise GatewayError(status_code=401, code="INVALID_SIGNATURE", diagnostic="RSA signature verification failed") from exc
        except Exception as exc:
            raise GatewayError(status_code=401, code="INVALID_SIGNATURE", diagnostic=f"Signature check error: {exc}") from exc

        # 3. Parse payload
        payload_bytes = b64url_decode(payload_b64)
        try:
            payload_text = payload_bytes.decode("utf-8")
            payload = json.loads(payload_text, object_pairs_hook=reject_duplicate_keys, parse_constant=parse_nonfinite)
        except Exception as exc:
            raise GatewayError(status_code=401, code="INVALID_JWT_PAYLOAD", diagnostic=f"Malformed payload JSON: {exc}") from exc

        if not isinstance(payload, dict):
            raise GatewayError(status_code=401, code="INVALID_JWT_PAYLOAD", diagnostic="JWT payload must be a JSON object")

        # 4. Required claims presence and formats
        for claim in REQUIRED_CLAIMS:
            if claim not in payload:
                raise GatewayError(status_code=401, code="MISSING_REQUIRED_CLAIM", diagnostic=f"Missing required claim: {claim!r}")

        # Numeric string formats
        for field in ("repository_id", "repository_owner_id", "run_id", "run_attempt"):
            val = payload.get(field)
            if not isinstance(val, str) or not DIGITS_PATTERN.fullmatch(val):
                raise GatewayError(status_code=401, code="INVALID_CLAIM_TYPE", diagnostic=f"Claim {field!r} is not digits")

        # Workflow SHA format
        wf_sha = payload.get("job_workflow_sha")
        if not isinstance(wf_sha, str) or not HEX40_PATTERN.fullmatch(wf_sha):
            raise GatewayError(status_code=401, code="INVALID_CLAIM_TYPE", diagnostic="Claim 'job_workflow_sha' is not 40 hex")

        # Issuer check
        if payload.get("iss") != self.expected_issuer:
            raise GatewayError(
                status_code=401,
                code="INVALID_ISSUER",
                diagnostic=f"Expected issuer {self.expected_issuer!r}, got {payload.get('iss')!r}",
            )

        # Audience check
        aud = payload.get("aud")
        aud_valid = (isinstance(aud, str) and aud == self.expected_audience) or (
            isinstance(aud, list) and self.expected_audience in aud
        )
        if not aud_valid:
            raise GatewayError(
                status_code=401,
                code="INVALID_AUDIENCE",
                diagnostic=f"Expected audience {self.expected_audience!r}, got {aud!r}",
            )

        # 5. Strict temporal checks
        now = self.clock()
        iat = validate_numeric_date(payload["iat"], "iat")
        exp = validate_numeric_date(payload["exp"], "exp")
        nbf = validate_numeric_date(payload["nbf"], "nbf") if "nbf" in payload else None

        # Positive lifetime
        if exp <= iat:
            raise GatewayError(
                status_code=401,
                code="INVALID_TOKEN_LIFETIME",
                diagnostic=f"Token exp ({exp}) must be strictly greater than iat ({iat})",
            )

        # Maximum token age (15 minutes from iat) - checked BEFORE lifetime check for deterministic age precedence
        age = now - iat
        if age > 900.0:
            raise GatewayError(
                status_code=401,
                code="TOKEN_AGE_EXCEEDED",
                diagnostic=f"Token age ({age:.1f}s) exceeds maximum allowed 900 seconds",
            )

        # Maximum lifetime (15 minutes)
        lifetime = exp - iat
        if lifetime > 900.0:
            raise GatewayError(
                status_code=401,
                code="INVALID_TOKEN_LIFETIME",
                diagnostic=f"Token lifetime ({lifetime}s) exceeds maximum allowed 900 seconds",
            )

        # Clock skew bounds (<= 30s)
        if iat > now + 30.0:
            raise GatewayError(status_code=401, code="TOKEN_ISSUED_IN_FUTURE", diagnostic="Token issued in the future (iat > now + 30s)")

        if nbf is not None and nbf > now + 30.0:
            raise GatewayError(status_code=401, code="TOKEN_FUTURE", diagnostic="Token is not active yet (nbf > now + 30s)")

        if now > exp + 30.0:
            raise GatewayError(status_code=401, code="TOKEN_EXPIRED", diagnostic="Token has expired (now > exp + 30s)")

        return payload
