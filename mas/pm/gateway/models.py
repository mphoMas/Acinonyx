"""Data models, error classes, and configuration schemas for the GHA-03 Authentication Gateway."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import Field, model_validator

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


class GatewayError(Exception):
    """Base error for authentication gateway and admission failures."""

    def __init__(self, message: str, *, status_code: int = 400, code: str = "GATEWAY_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code

    def to_envelope(self, request_id: str = "req-untracked", timestamp: str = "") -> dict[str, Any]:
        return {
            "status": "ERROR",
            "code": self.code,
            "message": self.message,
            "timestamp": timestamp,
            "request_id": request_id,
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
