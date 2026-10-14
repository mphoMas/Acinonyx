"""Stateless observation ingestion and gateway validator for untrusted GitHub Actions CI."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

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
    MAX_MANIFEST_JSON_SIZE,
    MAX_REQUEST_BODY_SIZE,
    ConnectorRegistry,
    GatewayError,
    GitHubConnectorConfig,
    WitnessObservationSubmissionRequest,
    WitnessObservationValidationResponse,
)

logger = logging.getLogger(__name__)


def redact_sensitive(data: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized copy of audit data redacting authorization tokens, JWTs, and payloads."""
    sanitized: dict[str, Any] = {}
    for key, val in data.items():
        if key in ("authorization", "bearer_token", "token", "artifact_archive_base64", "raw_body"):
            sanitized[key] = "[REDACTED]"
        elif isinstance(val, str):
            clean = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", val)
            clean = re.sub(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+", "[REDACTED_JWT]", clean)
            sanitized[key] = clean
        else:
            sanitized[key] = val
    return sanitized


class GatewayObservationValidator:
    """Stateless offline admission validator verifying OIDC tokens, connector policies, and observation boundaries."""

    def __init__(
        self,
        connector_registry: ConnectorRegistry | Mapping[tuple[str, str], GitHubConnectorConfig],
        iam: MultiTenantIAM,
        jwks_cache: JWKSCache,
        *,
        clock: Callable[[], float] = time.time,
        audit_logger: Callable[[dict[str, Any]], None] | None = None,
        on_validation_stage: Callable[[str], None] | None = None,
    ) -> None:
        self.connector_registry = connector_registry
        self.iam = iam
        self.jwks_cache = jwks_cache
        self.clock = clock
        self.audit_logger = audit_logger
        self.on_validation_stage = on_validation_stage
        self.token_verifier = TokenVerifier(jwks_cache, clock=clock)

    def _lookup_connector(self, coord: tuple[str, str]) -> GitHubConnectorConfig | None:
        """Resolve current connector entry from registry interface."""
        if hasattr(self.connector_registry, "get"):
            return self.connector_registry.get(coord)
        try:
            return self.connector_registry[coord]
        except (KeyError, TypeError):
            return None

    def _notify_stage(self, stage: str) -> None:
        """Notify stage hook if registered (used for testing mid-validation concurrency and updates)."""
        if self.on_validation_stage:
            self.on_validation_stage(stage)

    def validate_submission(
        self,
        auth_header: str | None,
        request_input: bytes | str | dict[str, Any],
    ) -> WitnessObservationValidationResponse:
        """Validate an observation submission request from an untrusted GHA worker."""
        request_id = f"req-{hashlib.sha256(f'{self.clock()}:{id(request_input)}'.encode()).hexdigest()[:12]}"

        try:
            return self._execute_validation(auth_header, request_input, request_id)
        except GatewayError as exc:
            exc.request_id = request_id
            self._log_audit(
                {
                    "request_id": request_id,
                    "event": "GATEWAY_VALIDATION_FAILED",
                    "status_code": exc.status_code,
                    "code": exc.code,
                    "message": exc.message,
                    "diagnostic": exc.diagnostic,
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
                    "message": "Internal gateway validation error",
                    "diagnostic": str(exc),
                }
            )
            raise GatewayError(
                status_code=500,
                code="INTERNAL_ERROR",
                request_id=request_id,
                diagnostic=str(exc),
            ) from exc

    def _execute_validation(
        self,
        auth_header: str | None,
        request_input: bytes | str | dict[str, Any],
        request_id: str,
    ) -> WitnessObservationValidationResponse:
        # 1. Inspect Authorization Header
        if not auth_header or not isinstance(auth_header, str):
            raise GatewayError(status_code=401, code="INVALID_AUTHORIZATION_HEADER", request_id=request_id)

        if not auth_header.startswith("Bearer "):
            raise GatewayError(status_code=401, code="INVALID_AUTHORIZATION_HEADER", request_id=request_id)

        token_str = auth_header[7:].strip()
        if not token_str:
            raise GatewayError(status_code=401, code="INVALID_AUTHORIZATION_HEADER", request_id=request_id)

        # 2. Parse and Validate Request Payload
        request_data = self._parse_request_input(request_input, request_id)

        try:
            request = WitnessObservationSubmissionRequest.model_validate(request_data)
        except ValidationError as exc:
            exc_str = str(exc)
            if "exceeds limit" in exc_str or "PAYLOAD_TOO_LARGE" in exc_str:
                raise GatewayError(
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                    request_id=request_id,
                    diagnostic=exc_str,
                ) from exc
            if "extra_forbidden" in exc_str or "Extra inputs are not permitted" in exc_str:
                raise GatewayError(
                    status_code=422,
                    code="EXTRA_FIELDS_FORBIDDEN",
                    request_id=request_id,
                    diagnostic=exc_str,
                ) from exc
            raise GatewayError(
                status_code=422,
                code="INVALID_MANIFEST_STRUCTURE",
                request_id=request_id,
                diagnostic=exc_str,
            ) from exc

        # 3. Cryptographically Verify OIDC Token
        token_claims = self.token_verifier.verify_token(token_str)

        # 4. Resolve Server-Owned Connector Policy & Snapshot Authority Coordinates
        repo_coord = (token_claims["repository_id"], token_claims["repository_owner_id"])
        initial_config = self._lookup_connector(repo_coord)
        if initial_config is None:
            raise GatewayError(
                status_code=403,
                code="REPOSITORY_NOT_ENROLLED",
                request_id=request_id,
                diagnostic=f"Repository ID {repo_coord[0]!r} (owner {repo_coord[1]!r}) is not enrolled",
            )

        if initial_config.status != "ACTIVE":
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_REVOKED",
                request_id=request_id,
                diagnostic=f"GitHub connector for repository {repo_coord[0]} is revoked",
            )

        # Retain initial identity & generation snapshot for completion verification
        snap_generation = initial_config.generation
        snap_tenant_id = initial_config.tenant_id
        snap_project_id = initial_config.project_id
        snap_approved_wf_sha = initial_config.approved_workflow_sha
        snap_approved_wf_path = initial_config.approved_workflow_path
        snap_approved_wf_repo = initial_config.approved_workflow_repo
        snap_required_runner = initial_config.required_runner_env

        # 5. Check Initial Tenant Active Status in MultiTenantIAM
        tenant = self.iam.get_tenant(snap_tenant_id)
        if tenant is None or tenant.status != TenantStatus.ACTIVE:
            raise GatewayError(
                status_code=403,
                code="TENANT_REVOKED",
                request_id=request_id,
                diagnostic=f"Tenant {snap_tenant_id!r} is inactive or revoked",
            )

        # 6. Verify Reusable Workflow Pinning
        if token_claims["job_workflow_sha"] != snap_approved_wf_sha:
            raise GatewayError(
                status_code=403,
                code="WORKFLOW_UNAPPROVED",
                request_id=request_id,
                diagnostic=f"Workflow commit SHA {token_claims['job_workflow_sha']} does not match approved SHA {snap_approved_wf_sha}",
            )

        job_wf_ref = token_claims["job_workflow_ref"]
        if "@refs/heads/" in job_wf_ref or "@refs/tags/" in job_wf_ref:
            raise GatewayError(
                status_code=403,
                code="WORKFLOW_NOT_PINNED",
                request_id=request_id,
                diagnostic=f"Mutable workflow ref {job_wf_ref!r} is not pinned by commit SHA",
            )

        expected_wf_ref = f"{snap_approved_wf_repo}/{snap_approved_wf_path}@{snap_approved_wf_sha}"
        if job_wf_ref != expected_wf_ref:
            raise GatewayError(
                status_code=403,
                code="WORKFLOW_UNAPPROVED",
                request_id=request_id,
                diagnostic=f"Workflow ref {job_wf_ref!r} does not match expected {expected_wf_ref!r}",
            )

        # 7. Check Execution Conditions
        event_name = token_claims["event_name"]
        if event_name not in initial_config.permitted_events:
            raise GatewayError(
                status_code=403,
                code="CONDITION_DISALLOWED",
                request_id=request_id,
                diagnostic=f"GitHub event {event_name!r} is not permitted for delivery gates",
            )

        ref_pattern = initial_config.permitted_ref_patterns.get(event_name)
        if not ref_pattern or not re.fullmatch(ref_pattern, token_claims["ref"]):
            raise GatewayError(
                status_code=403,
                code="CONDITION_DISALLOWED",
                request_id=request_id,
                diagnostic=f"Caller ref {token_claims['ref']!r} does not match allowed pattern for event {event_name!r}",
            )

        if token_claims["runner_environment"] != snap_required_runner:
            raise GatewayError(
                status_code=403,
                code="CONDITION_DISALLOWED",
                request_id=request_id,
                diagnostic=f"Runner environment {token_claims['runner_environment']!r} does not match required {snap_required_runner!r}",
            )

        # 8. Verify Coordinate Binding
        if request.github_run_id != token_claims["run_id"]:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic=f"Request github_run_id ({request.github_run_id}) does not match token run_id ({token_claims['run_id']})",
            )

        try:
            token_attempt_int = int(token_claims["run_attempt"])
        except ValueError as exc:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic="Token run_attempt is not an integer",
            ) from exc

        if request.github_run_attempt != token_attempt_int:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic=f"Request github_run_attempt ({request.github_run_attempt}) does not match token run_attempt ({token_attempt_int})",
            )

        if request.manifest.tenant_id != snap_tenant_id:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic=f"Manifest tenant_id ({request.manifest.tenant_id}) does not match configured tenant ({snap_tenant_id})",
            )

        if request.manifest.project_id != snap_project_id:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic=f"Manifest project_id ({request.manifest.project_id}) does not match configured project ({snap_project_id})",
            )

        if request.manifest.fencing_token != request.fencing_token:
            raise GatewayError(
                status_code=409,
                code="FENCING_TOKEN_MISMATCH",
                request_id=request_id,
                diagnostic=f"Manifest fencing token ({request.manifest.fencing_token}) does not match request ({request.fencing_token})",
            )

        # 9. Validate Artifact Archive
        artifact_digest: str | None = None
        artifacts_validated: bool = False

        needs_artifacts = any(
            bool(obs.evidence_ref and not obs.evidence_ref.startswith("inline:") and obs.outcome in ("PASSED", "FAILED"))
            for obs in request.manifest.observations
        )

        self._notify_stage("artifact_validation")

        if request.artifact_archive_base64 is not None:
            if len(request.artifact_archive_base64) > MAX_BASE64_ARCHIVE_SIZE:
                raise GatewayError(
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                    request_id=request_id,
                    diagnostic=f"Base64 artifact archive size ({len(request.artifact_archive_base64)}) exceeds limit",
                )

            try:
                decoded_bytes = base64.b64decode(request.artifact_archive_base64, validate=True)
            except Exception as exc:
                raise GatewayError(
                    status_code=400,
                    code="INVALID_BASE64_PAYLOAD",
                    request_id=request_id,
                    diagnostic=f"Invalid base64 encoding in artifact archive: {exc}",
                ) from exc

            if len(decoded_bytes) > MAX_ARCHIVE_COMPRESSED_SIZE:
                raise GatewayError(
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                    request_id=request_id,
                    diagnostic=f"Decoded artifact archive size ({len(decoded_bytes)}) exceeds limit of {MAX_ARCHIVE_COMPRESSED_SIZE} bytes",
                )

            try:
                validate_artifact_archive(decoded_bytes, observations=request.manifest.observations)
            except DeliveryValidatorError as exc:
                exc_str = str(exc)
                if "exceeds" in exc_str and "limit" in exc_str:
                    raise GatewayError(
                        status_code=413,
                        code="PAYLOAD_TOO_LARGE",
                        request_id=request_id,
                        diagnostic=exc_str,
                    ) from exc
                raise GatewayError(
                    status_code=400,
                    code="INVALID_ARTIFACT_ARCHIVE",
                    request_id=request_id,
                    diagnostic=exc_str,
                ) from exc

            artifact_digest = hashlib.sha256(decoded_bytes).hexdigest()
            artifacts_validated = True
        elif needs_artifacts:
            raise GatewayError(
                status_code=400,
                code="ARTIFACTS_REQUIRED",
                request_id=request_id,
                diagnostic="Observations declare artifact evidence but no artifact archive was submitted",
            )

        # 10. Recheck Tenant & Connector Status at Completion
        current_tenant = self.iam.get_tenant(snap_tenant_id)
        if current_tenant is None or current_tenant.status != TenantStatus.ACTIVE:
            raise GatewayError(
                status_code=403,
                code="TENANT_REVOKED",
                request_id=request_id,
                diagnostic=f"Tenant {snap_tenant_id} is inactive or revoked",
            )

        current_config = self._lookup_connector(repo_coord)
        if current_config is None:
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_REMOVED",
                request_id=request_id,
                diagnostic=f"Connector for repository {repo_coord} was removed during processing",
            )

        if current_config.status != "ACTIVE":
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_REVOKED",
                request_id=request_id,
                diagnostic=f"Connector for repository {repo_coord} was revoked during processing",
            )

        if current_config.generation != snap_generation:
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_GENERATION_CHANGED",
                request_id=request_id,
                diagnostic=f"Connector generation changed from {snap_generation} to {current_config.generation}",
            )

        if (
            current_config.tenant_id != snap_tenant_id
            or current_config.project_id != snap_project_id
            or current_config.approved_workflow_sha != snap_approved_wf_sha
            or current_config.approved_workflow_path != snap_approved_wf_path
            or current_config.approved_workflow_repo != snap_approved_wf_repo
            or current_config.required_runner_env != snap_required_runner
        ):
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_AUTHORITY_CHANGED",
                request_id=request_id,
                diagnostic="Connector authority configuration mutated during validation processing",
            )

        # 11. Construct Ephemeral Witness Context (Internal restricted validation only)
        # Note: TenantContext is an internal ephemeral structure only; not an IAM bearer, session, or credential.
        _ = TenantContext(
            tenant_id=snap_tenant_id,
            principal_id=f"gha-witness:{initial_config.repository_id}:{request.github_run_id}",
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
            tenant_id=snap_tenant_id,
            project_id=snap_project_id,
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
                "request_id": request_id,
                "event": "OBSERVATION_VALIDATED",
                "tenant_id": snap_tenant_id,
                "project_id": snap_project_id,
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

    def _parse_request_input(
        self,
        request_input: bytes | str | dict[str, Any],
        request_id: str,
    ) -> dict[str, Any]:
        """Bounded parse of request input enforcing 18 MiB envelope limit, 1 MiB nested manifest limit, and duplicate key rejection."""
        if isinstance(request_input, dict):
            # 1. Bounded serialization of dictionary envelope to prevent memory blow-up while checking 18 MiB cap
            total_env_size = 0
            for chunk in json.JSONEncoder().iterencode(request_input):
                total_env_size += len(chunk.encode("utf-8"))
                if total_env_size > MAX_REQUEST_BODY_SIZE:
                    raise GatewayError(
                        status_code=413,
                        code="PAYLOAD_TOO_LARGE",
                        request_id=request_id,
                        diagnostic=f"Dictionary envelope ({total_env_size} bytes) exceeds limit of {MAX_REQUEST_BODY_SIZE} bytes",
                    )
            data = request_input
        elif isinstance(request_input, (bytes, str)):
            encoded = request_input if isinstance(request_input, bytes) else request_input.encode("utf-8")
            if len(encoded) > MAX_REQUEST_BODY_SIZE:
                raise GatewayError(
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                    request_id=request_id,
                    diagnostic=f"Request body length ({len(encoded)} bytes) exceeds maximum limit of {MAX_REQUEST_BODY_SIZE} bytes",
                )
            try:
                text = encoded.decode("utf-8")
                data = json.loads(text, object_pairs_hook=reject_duplicate_keys, parse_constant=parse_nonfinite)
            except Exception as exc:
                raise GatewayError(
                    status_code=400,
                    code="INVALID_REQUEST_BODY",
                    request_id=request_id,
                    diagnostic=f"Malformed request JSON body: {exc}",
                ) from exc
            if not isinstance(data, dict):
                raise GatewayError(
                    status_code=400,
                    code="INVALID_REQUEST_BODY",
                    request_id=request_id,
                    diagnostic="Request body must be a JSON object",
                )
        else:
            raise GatewayError(
                status_code=400,
                code="INVALID_REQUEST_BODY",
                request_id=request_id,
                diagnostic="Request input must be bytes, str or dict",
            )

        # 2. Universal bounded check on nested manifest representation before expensive operations
        manifest_val = data.get("manifest")
        if manifest_val is not None:
            if isinstance(manifest_val, dict):
                total_man_size = 0
                for chunk in json.JSONEncoder().iterencode(manifest_val):
                    total_man_size += len(chunk.encode("utf-8"))
                    if total_man_size > MAX_MANIFEST_JSON_SIZE:
                        raise GatewayError(
                            status_code=413,
                            code="PAYLOAD_TOO_LARGE",
                            request_id=request_id,
                            diagnostic=f"Nested manifest size ({total_man_size} bytes) exceeds limit of {MAX_MANIFEST_JSON_SIZE} bytes",
                        )
            elif isinstance(manifest_val, (str, bytes)):
                enc_len = len(manifest_val.encode("utf-8") if isinstance(manifest_val, str) else manifest_val)
                if enc_len > MAX_MANIFEST_JSON_SIZE:
                    raise GatewayError(
                        status_code=413,
                        code="PAYLOAD_TOO_LARGE",
                        request_id=request_id,
                        diagnostic=f"Nested manifest size ({enc_len} bytes) exceeds limit of {MAX_MANIFEST_JSON_SIZE} bytes",
                    )

        return data

    def _log_audit(self, event: dict[str, Any]) -> None:
        """Forward redacted event to configured audit logger if present."""
        if self.audit_logger:
            try:
                self.audit_logger(redact_sensitive(event))
            except Exception as exc:
                logger.warning("Audit logging callback failed: %s", exc)
