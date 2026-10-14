"""Data models, error classes, and configuration schemas for the GHA-03 Authentication Gateway."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Any, Literal, Mapping
from pydantic import Field, field_validator, model_validator

from mas.pm.delivery_validator import DeliveryManifest, StrictModel

SHA = r"^[0-9a-f]{40}$"
DIGITS = r"^\d+$"

# Independent resource caps
MAX_REQUEST_BODY_SIZE = 18 * 1024 * 1024       # 18 MiB total encoded request allowance
MAX_BASE64_ARCHIVE_SIZE = 16 * 1024 * 1024     # 16 MiB max base64-encoded string
MAX_MANIFEST_JSON_SIZE = 1 * 1024 * 1024       # 1 MiB max manifest JSON
MAX_ARCHIVE_COMPRESSED_SIZE = 12 * 1024 * 1024 # 12 MiB max decoded compressed archive bytes
MAX_JWT_LENGTH = 8192                          # 8192 bytes max raw JWT string
MAX_JWKS_BYTES = 64 * 1024                     # 64 KiB max JWKS response
MAX_JWKS_KEYS = 32                             # 32 keys max in JWKS
DEFAULT_CACHE_TTL = 86400.0                    # 24 hours
UNKNOWN_KID_COOLDOWN = 300.0                   # 5 minutes
FAILED_FETCH_COOLDOWN = 60.0                   # 60 seconds

PUBLIC_ERROR_MESSAGES: dict[str, str] = {
    "INVALID_AUTHORIZATION_HEADER": "Authorization header is missing, malformed, or does not use Bearer scheme.",
    "INVALID_JWT_FORMAT": "Authentication token format is invalid.",
    "INVALID_JWT_HEADER": "Authentication token header is invalid or contains unsupported parameters.",
    "INVALID_JWT_PAYLOAD": "Authentication token payload is invalid or malformed.",
    "UNSUPPORTED_ALGORITHM": "Authentication token algorithm is not permitted.",
    "INVALID_SIGNATURE": "Authentication token signature verification failed.",
    "MISSING_REQUIRED_CLAIM": "Authentication token is missing mandatory claims.",
    "INVALID_CLAIM_TYPE": "Authentication token claim type or format is invalid.",
    "INVALID_ISSUER": "Authentication token issuer is not recognized or trusted.",
    "UNTRUSTED_ISSUER": "Authentication token issuer is not recognized or trusted.",
    "INVALID_AUDIENCE": "Authentication token audience does not match expected coordinator audience.",
    "TOKEN_EXPIRED": "Authentication token has expired.",
    "TOKEN_FUTURE": "Authentication token is not yet valid (nbf in future).",
    "TOKEN_ISSUED_IN_FUTURE": "Authentication token was issued in the future (iat in future).",
    "INVALID_TOKEN_LIFETIME": "Authentication token lifetime is invalid or exceeds maximum allowable duration.",
    "TOKEN_AGE_EXCEEDED": "Authentication token age exceeds allowable threshold.",
    "UNKNOWN_KEY_THROTTLED": "Authentication token specifies an unknown key identifier and requests are throttled.",
    "UNKNOWN_KEY_ID": "Key identifier specified in token was not found in key set.",
    "JWKS_UNAVAILABLE": "Key set endpoint is unavailable or returned an invalid response.",
    "REPOSITORY_NOT_ENROLLED": "GitHub repository is not enrolled in delivery gates.",
    "CONNECTOR_REVOKED": "GitHub connector for this repository is revoked.",
    "CONNECTOR_REMOVED": "GitHub connector for this repository was removed during processing.",
    "CONNECTOR_GENERATION_CHANGED": "GitHub connector generation changed during processing.",
    "CONNECTOR_AUTHORITY_CHANGED": "GitHub connector authority configuration changed during processing.",
    "TENANT_REVOKED": "Tenant is inactive or revoked.",
    "WORKFLOW_UNAPPROVED": "Workflow definition or commit SHA is not approved for delivery gates.",
    "WORKFLOW_NOT_PINNED": "Workflow reference must be pinned by immutable commit SHA.",
    "CONDITION_DISALLOWED": "GitHub event, ref pattern, or runner environment is not permitted.",
    "COORDINATE_MISMATCH": "Request coordinates do not match token claims or connector configuration.",
    "FENCING_TOKEN_MISMATCH": "Manifest fencing token does not match submission request fencing token.",
    "INVALID_REQUEST_BODY": "Request payload is malformed or invalid JSON.",
    "INVALID_MANIFEST_STRUCTURE": "Delivery manifest structure or schema is invalid.",
    "EXTRA_FIELDS_FORBIDDEN": "Request schema validation failed or extraneous fields were provided.",
    "PAYLOAD_TOO_LARGE": "Request payload, manifest, or archive exceeds maximum size limit.",
    "INVALID_BASE64_PAYLOAD": "Artifact archive payload is not valid base64.",
    "INVALID_ARTIFACT_ARCHIVE": "Artifact archive structure, content, or verification failed.",
    "ARTIFACTS_REQUIRED": "Observations declare artifact evidence but no artifact archive was provided.",
    "INTERNAL_ERROR": "An internal gateway error occurred during observation validation.",
}


class GatewayError(Exception):
    """Base error for authentication gateway and admission failures.

    Public messages are strictly bounded to static messages from PUBLIC_ERROR_MESSAGES.
    Internal exception details, file paths, or sensitive input sentinels are retained
    strictly in the private 'diagnostic' attribute and NEVER emitted in public envelopes.
    """

    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int = 400,
        code: str = "GATEWAY_ERROR",
        request_id: str | None = None,
        diagnostic: str | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.request_id = request_id
        self.diagnostic = diagnostic
        # Strictly bounded public message from centralized mapping
        self.message = PUBLIC_ERROR_MESSAGES.get(code, "A gateway error occurred during validation.")
        super().__init__(self.message)

    def to_envelope(self, request_id: str | None = None, timestamp: str | None = None) -> dict[str, Any]:
        req_id = request_id or self.request_id or "req-untracked"
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        return {
            "status": "ERROR",
            "code": self.code,
            "message": self.message,
            "request_id": str(req_id)[:64],
            "timestamp": str(ts)[:64],
        }


class GitHubConnectorConfig(StrictModel):
    """Server-side configuration binding a GitHub repository to a MAS tenant and project."""

    tenant_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=128)
    repository_id: str = Field(pattern=DIGITS)
    repository_owner_id: str = Field(pattern=DIGITS)
    approved_workflow_repo: str = Field(min_length=1, max_length=128)
    approved_workflow_path: str = Field(min_length=1, max_length=256)
    approved_workflow_sha: str = Field(pattern=SHA)
    permitted_events: list[str] = Field(default_factory=lambda: ["pull_request", "workflow_dispatch"])
    permitted_ref_patterns: dict[str, str] = Field(
        default_factory=lambda: {
            "pull_request": r"^refs/pull/\d+/merge$",
            "workflow_dispatch": r"^refs/heads/main$",
        }
    )
    required_runner_env: str = Field(default="github-hosted")
    status: Literal["ACTIVE", "REVOKED"] = "ACTIVE"
    generation: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def validate_paths(self):
        if not self.approved_workflow_path.strip().startswith(".github/workflows/"):
            raise ValueError("approved_workflow_path must be under .github/workflows/")
        return self


class ConnectorRegistry:
    """Synchronized thread-safe registry interface for GitHub connector configurations."""

    def __init__(self, entries: Mapping[tuple[str, str], GitHubConnectorConfig] | None = None) -> None:
        self._lock = threading.RLock()
        self._entries: dict[tuple[str, str], GitHubConnectorConfig] = dict(entries or {})

    def get(self, key: tuple[str, str]) -> GitHubConnectorConfig | None:
        with self._lock:
            return self._entries.get(key)

    def register(self, config: GitHubConnectorConfig) -> None:
        with self._lock:
            key = (config.repository_id, config.repository_owner_id)
            self._entries[key] = config

    def remove(self, key: tuple[str, str]) -> GitHubConnectorConfig | None:
        with self._lock:
            return self._entries.pop(key, None)

    def snapshot(self) -> dict[tuple[str, str], GitHubConnectorConfig]:
        with self._lock:
            return dict(self._entries)

    def __getitem__(self, key: tuple[str, str]) -> GitHubConnectorConfig:
        with self._lock:
            return self._entries[key]

    def __setitem__(self, key: tuple[str, str], config: GitHubConnectorConfig) -> None:
        with self._lock:
            self._entries[key] = config

    def __delitem__(self, key: tuple[str, str]) -> None:
        with self._lock:
            del self._entries[key]

    def __contains__(self, key: tuple[str, str]) -> bool:
        with self._lock:
            return key in self._entries

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)


class WitnessObservationSubmissionRequest(StrictModel):
    """Strict schema for GHA witness observation submission."""

    manifest: DeliveryManifest
    artifact_archive_base64: str | None = Field(
        default=None,
        max_length=MAX_BASE64_ARCHIVE_SIZE,
        description="Optional base64-encoded ZIP artifact archive.",
    )
    fencing_token: int = Field(ge=1, description="Active coordinator intent fencing token.")
    github_run_id: str = Field(min_length=1, max_length=64, pattern=DIGITS)
    github_run_attempt: int = Field(ge=1, le=100)

    @field_validator("manifest", mode="before")
    @classmethod
    def validate_manifest_admission(cls, v: Any) -> Any:
        from mas.pm.delivery_validator import DeliveryValidatorError, validate_manifest_input

        # 1. Enforce 1 MiB nested manifest limit on dictionary / model representation
        if isinstance(v, DeliveryManifest):
            raw_dict = v.model_dump()
        elif isinstance(v, dict):
            raw_dict = v
        elif isinstance(v, (str, bytes)):
            raw_dict = None
            raw_len = len(v.encode("utf-8") if isinstance(v, str) else v)
            if raw_len > MAX_MANIFEST_JSON_SIZE:
                raise ValueError(f"Nested manifest size ({raw_len} bytes) exceeds limit of {MAX_MANIFEST_JSON_SIZE} bytes")
        else:
            raise ValueError(f"Invalid manifest input type: {type(v).__name__}")

        if raw_dict is not None:
            total = 0
            for chunk in json.JSONEncoder().iterencode(raw_dict):
                total += len(chunk.encode("utf-8"))
                if total > MAX_MANIFEST_JSON_SIZE:
                    raise ValueError(f"Nested manifest size ({total} bytes) exceeds limit of {MAX_MANIFEST_JSON_SIZE} bytes")

        try:
            return validate_manifest_input(v)
        except DeliveryValidatorError as exc:
            raise ValueError(f"Manifest admission failed: {exc}") from exc


class WitnessObservationValidationResponse(StrictModel):
    """Structured response returned upon successful witness observation validation."""

    status: Literal["VALIDATED_UNTRUSTED_OBSERVATION"] = "VALIDATED_UNTRUSTED_OBSERVATION"
    transport_authenticated: bool = True
    authority_verified: bool = False  # Observation only, not verifier or reviewer evidence
    artifacts_validated: bool = False
    tenant_id: str
    project_id: str
    issue_id: str
    manifest_digest: str  # SHA-256 hex digest of canonical manifest JSON
    artifact_digest: str | None = None
    observation_count: int
    github_run_id: str
    github_run_attempt: int
    timestamp: str
