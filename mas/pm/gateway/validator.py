"""Stateless observation ingestion and gateway validator for untrusted GitHub Actions CI."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import ValidationError

from mas.iam import MultiTenantIAM, TenantContext, TenantStatus
from mas.pm.delivery_validator import (
    DeliveryValidatorError,
    validate_artifact_archive,
)
from mas.pm.gateway.jwks import (
    JWKSCache,
    parse_nonfinite,
    reject_duplicate_keys,
)
from mas.pm.gateway.jwt_verifier import TokenVerifier
from mas.pm.gateway.models import (
    MAX_ARCHIVE_COMPRESSED_SIZE,
    MAX_BASE64_ARCHIVE_SIZE,
    MAX_REQUEST_BODY_SIZE,
    GatewayError,
    GitHubConnectorConfig,
    WitnessObservationSubmissionRequest,
    WitnessObservationValidationResponse,
)

logger = logging.getLogger(__name__)


def redact_sensitive(data: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow sanitized copy of audit data redacting authorization tokens and raw bodies."""
    sanitized = dict(data)
    for key in ("authorization", "bearer_token", "token", "artifact_archive_base64", "raw_body"):
        if key in sanitized:
            sanitized[key] = "[REDACTED]"
    return sanitized


class GatewayObservationValidator:
    """Stateless offline admission validator verifying OIDC tokens, connector policies, and observation boundaries."""

    def __init__(
        self,
        connector_registry: dict[tuple[str, str], GitHubConnectorConfig],
        iam: MultiTenantIAM,
        jwks_cache: JWKSCache,
        *,
        clock: Callable[[], float] = time.time,
        audit_logger: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.connector_registry = connector_registry
        self.iam = iam
        self.jwks_cache = jwks_cache
        self.clock = clock
        self.audit_logger = audit_logger
        self.token_verifier = TokenVerifier(jwks_cache, clock=clock)

    def validate_submission(
        self,
        auth_header: str | None,
        request_input: bytes | str | dict[str, Any],
    ) -> WitnessObservationValidationResponse:
        """Validate an observation submission request from an untrusted GHA worker."""
        request_id = f"req-{hashlib.sha256(str(self.clock()).encode()).hexdigest()[:8]}"

        try:
            return self._execute_validation(auth_header, request_input)
        except GatewayError as exc:
            self._log_audit(
                {
                    "request_id": request_id,
                    "event": "GATEWAY_VALIDATION_FAILED",
                    "status_code": exc.status_code,
                    "code": exc.code,
                    "message": exc.message,
                }
            )
            raise exc
        except Exception as exc:
            self._log_audit(
                {
                    "request_id": request_id,
                    "event": "GATEWAY_INTERNAL_ERROR",
                    "status_code": 500,
                    "code": "INTERNAL_ERROR",
                    "message": str(exc),
                }
            )
            raise GatewayError(f"Internal gateway validation error: {exc}", status_code=500, code="INTERNAL_ERROR") from exc

    def _execute_validation(
        self,
        auth_header: str | None,
        request_input: bytes | str | dict[str, Any],
    ) -> WitnessObservationValidationResponse:
        # 1. Inspect Authorization Header
        if not auth_header or not isinstance(auth_header, str):
            raise GatewayError("Missing Authorization header", status_code=401, code="INVALID_AUTHORIZATION_HEADER")

        if not auth_header.startswith("Bearer "):
            raise GatewayError("Authorization header must use Bearer scheme", status_code=401, code="INVALID_AUTHORIZATION_HEADER")

        token_str = auth_header[7:].strip()
        if not token_str:
            raise GatewayError("Empty Bearer token in Authorization header", status_code=401, code="INVALID_AUTHORIZATION_HEADER")

        # 2. Parse and Validate Request Payload
        request_data = self._parse_request_input(request_input)

        try:
            request = WitnessObservationSubmissionRequest.model_validate(request_data)
        except ValidationError as exc:
            raise GatewayError(f"Request validation failed: {exc}", status_code=422, code="EXTRA_FIELDS_FORBIDDEN") from exc

        # 3. Cryptographically Verify OIDC Token
        token_claims = self.token_verifier.verify_token(token_str)

        # 4. Resolve Server-Owned Connector Policy
        repo_coord = (token_claims["repository_id"], token_claims["repository_owner_id"])
        connector_config = self.connector_registry.get(repo_coord)
        if connector_config is None:
            raise GatewayError(
                f"Repository ID {repo_coord[0]!r} (owner {repo_coord[1]!r}) is not enrolled in delivery gates",
                status_code=403,
                code="REPOSITORY_NOT_ENROLLED",
            )

        if connector_config.status != "ACTIVE":
            raise GatewayError(f"GitHub connector for repository {repo_coord[0]} is revoked", status_code=403, code="CONNECTOR_REVOKED")

        # 5. Check Tenant Active Status in MultiTenantIAM
        tenant = self.iam.get_tenant(connector_config.tenant_id)
        if tenant is None or tenant.status != TenantStatus.ACTIVE:
            raise GatewayError(
                f"Tenant {connector_config.tenant_id!r} is inactive or revoked",
                status_code=403,
                code="TENANT_REVOKED",
            )

        # 6. Verify Reusable Workflow Pinning
        # Workflow SHA
        if token_claims["job_workflow_sha"] != connector_config.approved_workflow_sha:
            raise GatewayError(
                f"Workflow commit SHA {token_claims['job_workflow_sha']} does not match approved SHA {connector_config.approved_workflow_sha}",
                status_code=403,
                code="WORKFLOW_UNAPPROVED",
            )

        # Workflow ref must not be a mutable branch or tag ref
        job_wf_ref = token_claims["job_workflow_ref"]
        if "@refs/heads/" in job_wf_ref or "@refs/tags/" in job_wf_ref:
            raise GatewayError(
                f"Mutable workflow ref {job_wf_ref!r} is not pinned by commit SHA",
                status_code=403,
                code="WORKFLOW_NOT_PINNED",
            )

        expected_wf_ref = f"{connector_config.approved_workflow_repo}/{connector_config.approved_workflow_path}@{connector_config.approved_workflow_sha}"
        if job_wf_ref != expected_wf_ref:
            raise GatewayError(
                f"Workflow ref {job_wf_ref!r} does not match expected {expected_wf_ref!r}",
                status_code=403,
                code="WORKFLOW_UNAPPROVED",
            )

        # 7. Check Execution Conditions
        event_name = token_claims["event_name"]
        if event_name not in connector_config.permitted_events:
            raise GatewayError(
                f"GitHub event {event_name!r} is not permitted for delivery gates",
                status_code=403,
                code="CONDITION_DISALLOWED",
            )

        ref_pattern = connector_config.permitted_ref_patterns.get(event_name)
        if not ref_pattern or not re.fullmatch(ref_pattern, token_claims["ref"]):
            raise GatewayError(
                f"Caller ref {token_claims['ref']!r} does not match allowed pattern for event {event_name!r}",
                status_code=403,
                code="CONDITION_DISALLOWED",
            )

        if token_claims["runner_environment"] != connector_config.required_runner_env:
            raise GatewayError(
                f"Runner environment {token_claims['runner_environment']!r} does not match required {connector_config.required_runner_env!r}",
                status_code=403,
                code="CONDITION_DISALLOWED",
            )

        # 8. Verify Coordinate Binding
        if request.github_run_id != token_claims["run_id"]:
            raise GatewayError(
                f"Request github_run_id ({request.github_run_id}) does not match token run_id ({token_claims['run_id']})",
                status_code=400,
                code="COORDINATE_MISMATCH",
            )

        try:
            token_attempt_int = int(token_claims["run_attempt"])
        except ValueError as exc:
            raise GatewayError("Token run_attempt is not an integer", status_code=400, code="COORDINATE_MISMATCH") from exc

        if request.github_run_attempt != token_attempt_int:
            raise GatewayError(
                f"Request github_run_attempt ({request.github_run_attempt}) does not match token run_attempt ({token_attempt_int})",
                status_code=400,
                code="COORDINATE_MISMATCH",
            )

        if request.manifest.tenant_id != connector_config.tenant_id:
            raise GatewayError(
                f"Manifest tenant_id ({request.manifest.tenant_id}) does not match configured tenant ({connector_config.tenant_id})",
                status_code=400,
                code="COORDINATE_MISMATCH",
            )

        if request.manifest.project_id != connector_config.project_id:
            raise GatewayError(
                f"Manifest project_id ({request.manifest.project_id}) does not match configured project ({connector_config.project_id})",
                status_code=400,
                code="COORDINATE_MISMATCH",
            )

        if request.manifest.fencing_token != request.fencing_token:
            raise GatewayError(
                f"Manifest fencing token ({request.manifest.fencing_token}) does not match request ({request.fencing_token})",
                status_code=400,
                code="COORDINATE_MISMATCH",
            )

        # 9. Validate Artifact Archive
        artifact_digest: str | None = None
        artifacts_validated: bool = False

        # Determine if any observation references artifact files
        needs_artifacts = any(
            bool(obs.evidence_ref and not obs.evidence_ref.startswith("inline:") and obs.outcome in ("PASSED", "FAILED"))
            for obs in request.manifest.observations
        )

        if request.artifact_archive_base64 is not None:
            if len(request.artifact_archive_base64) > MAX_BASE64_ARCHIVE_SIZE:
                raise GatewayError(
                    f"Base64 artifact archive size ({len(request.artifact_archive_base64)}) exceeds limit",
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                )

            try:
                decoded_bytes = base64.b64decode(request.artifact_archive_base64, validate=True)
            except Exception as exc:
                raise GatewayError(f"Invalid base64 encoding in artifact archive: {exc}", status_code=400, code="INVALID_BASE64_PAYLOAD") from exc

            if len(decoded_bytes) > MAX_ARCHIVE_COMPRESSED_SIZE:
                raise GatewayError(
                    f"Decoded artifact archive size ({len(decoded_bytes)}) exceeds limit of {MAX_ARCHIVE_COMPRESSED_SIZE} bytes",
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                )

            try:
                validate_artifact_archive(decoded_bytes, observations=request.manifest.observations)
            except DeliveryValidatorError as exc:
                raise GatewayError(f"Artifact archive validation failed: {exc}", status_code=400, code="INVALID_ARTIFACT_ARCHIVE") from exc

            artifact_digest = hashlib.sha256(decoded_bytes).hexdigest()
            artifacts_validated = True
        elif needs_artifacts:
            raise GatewayError(
                "Observations declare artifact evidence but no artifact archive was submitted",
                status_code=400,
                code="ARTIFACTS_REQUIRED",
            )

        # 10. Recheck Tenant & Connector Status at Completion
        current_tenant = self.iam.get_tenant(connector_config.tenant_id)
        if current_tenant is None or current_tenant.status != TenantStatus.ACTIVE:
            raise GatewayError("Tenant was revoked during validation processing", status_code=403, code="TENANT_REVOKED")

        if connector_config.status != "ACTIVE":
            raise GatewayError("Connector was revoked during validation processing", status_code=403, code="CONNECTOR_REVOKED")

        # 11. Construct Ephemeral Witness Context (Internal restricted validation only)
        # Note: TenantContext is internal restricted context only; not an IAM bearer or session token.
        _ = TenantContext(
            tenant_id=connector_config.tenant_id,
            principal_id=f"gha-witness:{connector_config.repository_id}:{request.github_run_id}",
            roles={"witness"},
            scopes={"delivery:witness_observe"},
            token_id="",
            expires_at=float(token_claims["exp"]),
        )

        manifest_digest = hashlib.sha256(request.manifest.model_dump_json().encode("utf-8")).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()

        response = WitnessObservationValidationResponse(
            status="VALIDATED_UNTRUSTED_OBSERVATION",
            transport_authenticated=True,
            authority_verified=False,
            artifacts_validated=artifacts_validated,
            tenant_id=connector_config.tenant_id,
            project_id=connector_config.project_id,
            issue_id=request.manifest.issue_id,
            manifest_digest=manifest_digest,
            artifact_digest=artifact_digest,
            observation_count=len(request.manifest.observations),
            github_run_id=request.github_run_id,
            github_run_attempt=request.github_run_attempt,
            timestamp=timestamp,
        )

        self._log_audit(
            {
                "event": "OBSERVATION_VALIDATED",
                "tenant_id": connector_config.tenant_id,
                "project_id": connector_config.project_id,
                "issue_id": request.manifest.issue_id,
                "github_run_id": request.github_run_id,
                "github_run_attempt": request.github_run_attempt,
                "manifest_digest": manifest_digest,
                "artifact_digest": artifact_digest,
                "artifacts_validated": artifacts_validated,
                "authority_verified": False,
            }
        )

        return response

    def _parse_request_input(self, request_input: bytes | str | dict[str, Any]) -> dict[str, Any]:
        """Bounded parse of request input enforcing 18 MiB max length and duplicate key rejection."""
        if isinstance(request_input, dict):
            return request_input

        if isinstance(request_input, str):
            encoded = request_input.encode("utf-8")
        elif isinstance(request_input, bytes):
            encoded = request_input
        else:
            raise GatewayError("Request input must be bytes, str or dict", status_code=400, code="INVALID_REQUEST_BODY")

        if len(encoded) > MAX_REQUEST_BODY_SIZE:
            raise GatewayError(
                f"Request body length ({len(encoded)} bytes) exceeds maximum limit of {MAX_REQUEST_BODY_SIZE} bytes",
                status_code=413,
                code="PAYLOAD_TOO_LARGE",
            )

        try:
            text = encoded.decode("utf-8")
            data = json.loads(text, object_pairs_hook=reject_duplicate_keys, parse_constant=parse_nonfinite)
        except Exception as exc:
            raise GatewayError(f"Malformed request JSON body: {exc}", status_code=400, code="INVALID_REQUEST_BODY") from exc

        if not isinstance(data, dict):
            raise GatewayError("Request body must be a JSON object", status_code=400, code="INVALID_REQUEST_BODY")

        return data

    def _log_audit(self, event: dict[str, Any]) -> None:
        """Forward redacted event to configured audit logger if present."""
        if self.audit_logger:
            try:
                self.audit_logger(redact_sensitive(event))
            except Exception as exc:
                logger.warning("Audit logging callback failed: %s", exc)
