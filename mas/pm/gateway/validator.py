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
    ConnectorPolicySnapshot,
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
        if key in ("authorization", "bearer_token", "token", "artifact_archive_base64", "raw_body", "jwt"):
            sanitized[key] = "[REDACTED]"
        elif isinstance(val, str):
            clean = re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", val)
            clean = re.sub(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+", "[REDACTED_JWT]", clean)
            sanitized[key] = clean
        elif isinstance(val, dict):
            sanitized[key] = redact_sensitive(val)
        elif isinstance(val, list):
            sanitized[key] = [
                redact_sensitive(item) if isinstance(item, dict)
                else (
                    re.sub(r"Bearer\s+[A-Za-z0-9_\-\.]+", "Bearer [REDACTED]", re.sub(r"eyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+", "[REDACTED_JWT]", item))
                    if isinstance(item, str) else item
                )
                for item in val
            ]
        else:
            sanitized[key] = val
    return sanitized


class GatewayObservationValidator:
    """Stateless offline admission validator verifying OIDC tokens, connector policies, and observation boundaries."""

    def __init__(
        self,
        connector_registry: ConnectorRegistry | Mapping[tuple[str, str], GitHubConnectorConfig | ConnectorPolicySnapshot],
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

    def _lookup_connector(self, coord: tuple[str, str]) -> ConnectorPolicySnapshot | None:
        """Resolve current connector entry from registry interface as an immutable policy snapshot."""
        entry = None
        if hasattr(self.connector_registry, "get_snapshot"):
            entry = self.connector_registry.get_snapshot(coord)
        elif hasattr(self.connector_registry, "get"):
            entry = self.connector_registry.get(coord)
        else:
            try:
                entry = self.connector_registry[coord]
            except (KeyError, TypeError):
                entry = None

        if entry is None:
            return None
        if isinstance(entry, ConnectorPolicySnapshot):
            return entry
        if isinstance(entry, GitHubConnectorConfig):
            return ConnectorPolicySnapshot.from_config(entry)
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
            safe_diag = "category=INTERNAL_ERROR"
            self._log_audit(
                {
                    "request_id": request_id,
                    "event": "GATEWAY_INTERNAL_ERROR",
                    "status_code": 500,
                    "code": "INTERNAL_ERROR",
                    "message": "Internal gateway validation error",
                    "diagnostic": safe_diag,
                }
            )
            raise GatewayError(
                status_code=500,
                code="INTERNAL_ERROR",
                request_id=request_id,
                diagnostic='category=INTERNAL_ERROR',
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
            is_oversized = False
            for err in exc.errors():
                msg = str(err.get("msg", ""))
                err_type = str(err.get("type", ""))
                if "exceeds limit" in msg or "PAYLOAD_TOO_LARGE" in msg or "too_large" in err_type:
                    is_oversized = True
                    break
            if is_oversized:
                raise GatewayError(
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                    request_id=request_id,
                    diagnostic='category=PAYLOAD_TOO_LARGE',
                ) from exc

            error_types = {err.get("type") for err in exc.errors()}
            if "extra_forbidden" in error_types:
                raise GatewayError(
                    status_code=422,
                    code="EXTRA_FIELDS_FORBIDDEN",
                    request_id=request_id,
                    diagnostic='category=EXTRA_FIELDS_FORBIDDEN',
                ) from exc
            raise GatewayError(
                status_code=422,
                code="INVALID_MANIFEST_STRUCTURE",
                request_id=request_id,
                diagnostic='category=INVALID_MANIFEST_STRUCTURE',
            ) from exc

        # 3. Cryptographically Verify OIDC Token
        token_claims = self.token_verifier.verify_token(token_str)

        # 4. Resolve Server-Owned Connector Policy & Snapshot Authority Coordinates
        repo_coord = (token_claims["repository_id"], token_claims["repository_owner_id"])
        initial_snapshot = self._lookup_connector(repo_coord)
        if initial_snapshot is None:
            raise GatewayError(
                status_code=403,
                code="REPOSITORY_NOT_ENROLLED",
                request_id=request_id,
                diagnostic='category=REPOSITORY_NOT_ENROLLED',
            )

        if initial_snapshot.status != "ACTIVE":
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_REVOKED",
                request_id=request_id,
                diagnostic='category=CONNECTOR_REVOKED',
            )

        # Retain initial identity snapshot for completion verification
        snap_tenant_id = initial_snapshot.tenant_id
        snap_project_id = initial_snapshot.project_id
        snap_approved_wf_sha = initial_snapshot.approved_workflow_sha
        snap_approved_wf_path = initial_snapshot.approved_workflow_path
        snap_approved_wf_repo = initial_snapshot.approved_workflow_repo
        snap_required_runner = initial_snapshot.required_runner_env

        # 5. Check Initial Tenant Active Status in MultiTenantIAM
        tenant = self.iam.get_tenant(snap_tenant_id)
        if tenant is None or tenant.status != TenantStatus.ACTIVE:
            raise GatewayError(
                status_code=403,
                code="TENANT_REVOKED",
                request_id=request_id,
                diagnostic='category=TENANT_REVOKED',
            )

        # 6. Verify Reusable Workflow Pinning
        if token_claims["job_workflow_sha"] != snap_approved_wf_sha:
            raise GatewayError(
                status_code=403,
                code="WORKFLOW_UNAPPROVED",
                request_id=request_id,
                diagnostic='category=WORKFLOW_UNAPPROVED',
            )

        job_wf_ref = token_claims["job_workflow_ref"]
        if "@refs/heads/" in job_wf_ref or "@refs/tags/" in job_wf_ref:
            raise GatewayError(
                status_code=403,
                code="WORKFLOW_NOT_PINNED",
                request_id=request_id,
                diagnostic='category=WORKFLOW_NOT_PINNED',
            )

        expected_wf_ref = f"{snap_approved_wf_repo}/{snap_approved_wf_path}@{snap_approved_wf_sha}"
        if job_wf_ref != expected_wf_ref:
            raise GatewayError(
                status_code=403,
                code="WORKFLOW_UNAPPROVED",
                request_id=request_id,
                diagnostic='category=WORKFLOW_UNAPPROVED',
            )

        # 7. Check Execution Conditions
        event_name = token_claims["event_name"]
        if event_name not in initial_snapshot.permitted_events:
            raise GatewayError(
                status_code=403,
                code="CONDITION_DISALLOWED",
                request_id=request_id,
                diagnostic='category=CONDITION_DISALLOWED',
            )

        ref_pattern = initial_snapshot.get_ref_pattern(event_name)
        if not ref_pattern or not re.fullmatch(ref_pattern, token_claims["ref"]):
            raise GatewayError(
                status_code=403,
                code="CONDITION_DISALLOWED",
                request_id=request_id,
                diagnostic='category=CONDITION_DISALLOWED',
            )

        if token_claims["runner_environment"] != snap_required_runner:
            raise GatewayError(
                status_code=403,
                code="CONDITION_DISALLOWED",
                request_id=request_id,
                diagnostic='category=CONDITION_DISALLOWED',
            )

        # 8. Verify Coordinate Binding
        if request.github_run_id != token_claims["run_id"]:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic='category=COORDINATE_MISMATCH',
            )

        try:
            token_attempt_int = int(token_claims["run_attempt"])
        except ValueError as exc:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic='category=COORDINATE_MISMATCH',
            ) from exc

        if request.github_run_attempt != token_attempt_int:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic='category=COORDINATE_MISMATCH',
            )

        if request.manifest.tenant_id != snap_tenant_id:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic='category=COORDINATE_MISMATCH',
            )

        if request.manifest.project_id != snap_project_id:
            raise GatewayError(
                status_code=400,
                code="COORDINATE_MISMATCH",
                request_id=request_id,
                diagnostic='category=COORDINATE_MISMATCH',
            )

        if request.manifest.fencing_token != request.fencing_token:
            raise GatewayError(
                status_code=409,
                code="FENCING_TOKEN_MISMATCH",
                request_id=request_id,
                diagnostic='category=FENCING_TOKEN_MISMATCH',
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
                    diagnostic='category=PAYLOAD_TOO_LARGE',
                )

            try:
                decoded_bytes = base64.b64decode(request.artifact_archive_base64, validate=True)
            except Exception as exc:
                raise GatewayError(
                    status_code=400,
                    code="INVALID_BASE64_PAYLOAD",
                    request_id=request_id,
                    diagnostic='category=INVALID_BASE64_PAYLOAD',
                ) from exc

            if len(decoded_bytes) > MAX_ARCHIVE_COMPRESSED_SIZE:
                raise GatewayError(
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                    request_id=request_id,
                    diagnostic='category=PAYLOAD_TOO_LARGE',
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
                        diagnostic='category=PAYLOAD_TOO_LARGE',
                    ) from exc
                raise GatewayError(
                    status_code=400,
                    code="INVALID_ARTIFACT_ARCHIVE",
                    request_id=request_id,
                    diagnostic='category=INVALID_ARTIFACT_ARCHIVE',
                ) from exc

            artifact_digest = hashlib.sha256(decoded_bytes).hexdigest()
            artifacts_validated = True
        elif needs_artifacts:
            raise GatewayError(
                status_code=400,
                code="ARTIFACTS_REQUIRED",
                request_id=request_id,
                diagnostic='category=ARTIFACTS_REQUIRED',
            )

        # 10. Recheck Tenant & Connector Status at Completion
        current_tenant = self.iam.get_tenant(snap_tenant_id)
        if current_tenant is None or current_tenant.status != TenantStatus.ACTIVE:
            raise GatewayError(
                status_code=403,
                code="TENANT_REVOKED",
                request_id=request_id,
                diagnostic='category=TENANT_REVOKED',
            )

        current_snapshot = self._lookup_connector(repo_coord)
        if current_snapshot is None:
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_REMOVED",
                request_id=request_id,
                diagnostic='category=CONNECTOR_REMOVED',
            )

        if current_snapshot.status != "ACTIVE":
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_REVOKED",
                request_id=request_id,
                diagnostic='category=CONNECTOR_REVOKED',
            )

        if current_snapshot.generation != initial_snapshot.generation:
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_GENERATION_CHANGED",
                request_id=request_id,
                diagnostic='category=CONNECTOR_GENERATION_CHANGED',
            )

        if current_snapshot.canonical_digest != initial_snapshot.canonical_digest:
            raise GatewayError(
                status_code=403,
                code="CONNECTOR_AUTHORITY_CHANGED",
                request_id=request_id,
                diagnostic='category=CONNECTOR_AUTHORITY_CHANGED',
            )

        # 11. Construct Ephemeral Witness Context (Internal restricted validation only)
        # Note: TenantContext is an internal ephemeral structure only; not an IAM bearer, session, or credential.
        _ = TenantContext(
            tenant_id=snap_tenant_id,
            principal_id=f"gha-witness:{initial_snapshot.repository_id}:{request.github_run_id}",
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
                        diagnostic='category=PAYLOAD_TOO_LARGE',
                    )
            data = request_input
        elif isinstance(request_input, (bytes, str)):
            encoded = request_input if isinstance(request_input, bytes) else request_input.encode("utf-8")
            if len(encoded) > MAX_REQUEST_BODY_SIZE:
                raise GatewayError(
                    status_code=413,
                    code="PAYLOAD_TOO_LARGE",
                    request_id=request_id,
                    diagnostic='category=PAYLOAD_TOO_LARGE',
                )
            try:
                text = encoded.decode("utf-8")
                data = json.loads(text, object_pairs_hook=reject_duplicate_keys, parse_constant=parse_nonfinite)
            except Exception as exc:
                raise GatewayError(
                    status_code=400,
                    code="INVALID_REQUEST_BODY",
                    request_id=request_id,
                    diagnostic='category=INVALID_REQUEST_BODY',
                ) from exc
            if not isinstance(data, dict):
                raise GatewayError(
                    status_code=400,
                    code="INVALID_REQUEST_BODY",
                    request_id=request_id,
                    diagnostic='category=INVALID_REQUEST_BODY',
                )
        else:
            raise GatewayError(
                status_code=400,
                code="INVALID_REQUEST_BODY",
                request_id=request_id,
                diagnostic='category=INVALID_REQUEST_BODY',
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
                            diagnostic='category=PAYLOAD_TOO_LARGE',
                        )
            elif isinstance(manifest_val, (str, bytes)):
                enc_len = len(manifest_val.encode("utf-8") if isinstance(manifest_val, str) else manifest_val)
                if enc_len > MAX_MANIFEST_JSON_SIZE:
                    raise GatewayError(
                        status_code=413,
                        code="PAYLOAD_TOO_LARGE",
                        request_id=request_id,
                        diagnostic='category=PAYLOAD_TOO_LARGE',
                    )

        return data

    def _log_audit(self, event: dict[str, Any]) -> None:
        """Forward redacted event to configured audit logger if present."""
        if self.audit_logger:
            try:
                self.audit_logger(redact_sensitive(event))
            except Exception:
                logger.warning('Gateway audit callback failed')
