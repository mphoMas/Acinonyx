"""
mas.pm.client: Authenticated client for publishing conversation-derived plans into MAS-PM.
Enables Codex, acting as architect and Scrum master, to publish structured plans directly.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Union

from mas.pm.models import PlanPublicationRequest, PlanPublicationResponse
from mas.pm.plans import (
    ContradictoryIdentityError,
    CycleDetectedError,
    IdempotencyConflictError,
    PlanError,
    PlanValidationError,
    ProjectNotFoundError,
    RevisionMismatchError,
    StaleRevisionError,
    UnsafePathError,
)


class PlanPublisherClient:
    """
    Authenticated client for publishing project plans to the MAS-PM service.
    Credentials and configuration can be passed explicitly or loaded from secure environment.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        self.base_url = (base_url or os.environ.get("MAS_SERVER_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.auth_token = auth_token or os.environ.get("MAS_AUTH_TOKEN")
        self.tenant_id = tenant_id or os.environ.get("MAS_TENANT_ID", "default")

    def publish_plan(
        self,
        project_id_or_key: str,
        plan: Union[PlanPublicationRequest, Dict[str, Any], str],
        idempotency_key: Optional[str] = None,
    ) -> PlanPublicationResponse:
        """
        Publishes a structured plan to POST /api/pm/v1/projects/{project_id}/plans.

        Args:
            project_id_or_key: Project UUID or Project Key (e.g. 'SBA', 'PLG')
            plan: PlanPublicationRequest instance, dict, or JSON string
            idempotency_key: Optional idempotency key for deduplication and atomic retries

        Returns:
            PlanPublicationResponse detailing applied revision, issue mappings, and reconciliations.

        Raises:
            IdempotencyConflictError: If idempotency key was reused with different payload (409)
            StaleRevisionError: If optimistic revision check failed (409)
            PlanValidationError: If schema, hierarchy, or dependency check failed (400)
            ProjectNotFoundError: If project does not exist in target tenant (404)
            PermissionError: If unauthenticated or unauthorized (401 / 403)
            PlanError: For other unexpected failures
        """
        if isinstance(plan, str):
            payload_dict = json.loads(plan)
        elif isinstance(plan, PlanPublicationRequest):
            payload_dict = plan.model_dump()
        elif isinstance(plan, dict):
            payload_dict = plan
        else:
            raise ValueError("Plan must be a PlanPublicationRequest, dict, or JSON string")

        url = f"{self.base_url}/api/pm/v1/projects/{project_id_or_key}/plans"
        payload_bytes = json.dumps(payload_dict).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(payload_bytes)),
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp_bytes = resp.read()
                data = json.loads(resp_bytes.decode("utf-8"))
                return PlanPublicationResponse(**data)

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_body)
                err_info = err_json.get("error", {})
                if isinstance(err_info, str):
                    code = "error"
                    msg = err_info
                else:
                    code = err_info.get("code", "error")
                    msg = err_info.get("message", str(e))
            except Exception:
                code = "error"
                msg = err_body or str(e)

            if e.code == 409:
                if code == "idempotency_conflict":
                    raise IdempotencyConflictError(msg)
                elif code == "stale_revision":
                    raise StaleRevisionError(msg)
                elif code == "revision_mismatch":
                    raise RevisionMismatchError(msg)
                else:
                    raise PlanError(msg, code=code)

            elif e.code == 400:
                if code == "cycle_detected":
                    raise CycleDetectedError(msg)
                elif code == "unsafe_path":
                    raise UnsafePathError(msg)
                elif code == "contradictory_identity":
                    raise ContradictoryIdentityError(msg)
                else:
                    raise PlanValidationError(msg)

            elif e.code == 404:
                raise ProjectNotFoundError(msg)

            elif e.code in (401, 403):
                raise PermissionError(f"HTTP {e.code}: {msg}")

            else:
                raise PlanError(f"HTTP {e.code}: {msg}", code=code)

    def get_plans(self, project_id_or_key: str) -> Dict[str, Any]:
        """Retrieves published plan revision history for a project."""
        url = f"{self.base_url}/api/pm/v1/projects/{project_id_or_key}/plans"
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def reconcile_staged_changes(
        self,
        project_id_or_key: str,
        issue_id_or_key: str,
        decision: str,
        expected_proposal_id: str,
        expected_proposal_rev: int,
        expected_base_policy_version: int,
    ) -> Dict[str, Any]:
        """
        Reconciles staged changes on an active issue via POST /api/pm/v1/projects/{project_id}/issues/{issue_key}/reconcile.
        Mandatory version bindings and explicit decision must be provided.
        """
        from mas.pm.plans import StaleProposalError, PlanValidationError, ProjectNotFoundError, PlanError

        url = f"{self.base_url}/api/pm/v1/projects/{project_id_or_key}/issues/{issue_id_or_key}/reconcile"
        payload = {
            "decision": decision,
            "expected_proposal_id": expected_proposal_id,
            "expected_proposal_rev": expected_proposal_rev,
            "expected_base_policy_version": expected_base_policy_version,
        }
        payload_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Content-Length": str(len(payload_bytes)),
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        req = urllib.request.Request(url, data=payload_bytes, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            try:
                err_json = json.loads(err_body)
                msg = err_json.get("error", {}).get("message", err_body)
                code = err_json.get("error", {}).get("code", "")
            except Exception:
                msg = err_body
                code = ""

            if e.code == 409:
                raise StaleProposalError(msg)
            elif e.code == 400:
                raise PlanValidationError(msg)
            elif e.code == 404:
                raise ProjectNotFoundError(msg)
            elif e.code in (401, 403):
                raise PermissionError(f"HTTP {e.code}: {msg}")
            else:
                raise PlanError(f"HTTP {e.code}: {msg}", code=code)

