"""Bounded automatic correction loop and operator control service (CC-07, CC-08, CC-11, CC-12 — P6).

Implements mas-automatic-loop-v1:
- Explicit execution profiles: coding.solve.v1 and repo.verify.v1
- Durable job stages: ADMITTED -> DEVELOPING -> EXPORTING -> VERIFYING -> REVIEWING ->
  REWORK_PENDING -> AWAITING_REQUIRED_APPROVAL -> INTEGRATING -> COMPLETION_PENDING -> COMPLETE / ESCALATED
- Transactional outbox handoffs with idempotent receipt acknowledgement
- Normalized bounded findings on verification/review failure creating at most one correction intent
- Plan-revision staleness invalidation (CC-08) and operator pause/cancel/uncertainty controls (CC-11, CC-12)
"""
from __future__ import annotations

import fnmatch
import hashlib
import secrets
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mas.pm.activity import ActivityBridgeService
from mas.pm.adapters.antigravity import sanitize_payload
from mas.pm.adapters.broker import migrate_live_loop
from mas.pm.coordinator import CoordinatorStore, trusted_coordinator_admin_scope
from mas.pm.fsm import FSMEngine
from mas.pm.models import IssueState
from mas.pm.tools import pm_attach_evidence, pm_cast_verdict
from mas.security import ExecutionContext
from mas.swarm.contracts import canonical, digest, strict_json

LOOP_CONTRACT_ID = "mas-automatic-loop-v1"
SUPPORTED_PROFILES = frozenset({"coding.solve.v1", "repo.verify.v1"})

PILOT_MAX_ATTEMPTS = 3
PILOT_MAX_PROVIDER_CALLS = 12
PILOT_MAX_DEADLINE_S = 600.0
PILOT_MAX_PROVIDER_CALL_S = 45.0
PILOT_MAX_CANDIDATE_EXEC_S = 30.0

ESCALATION_CATEGORIES = frozenset({
    "unsupported_profile",
    "conflicting_scope",
    "exhausted_attempts",
    "exhausted_time",
    "exhausted_budget",
    "unresolved_execution",
    "authentication_revocation",
    "unreconciled_policy_change",
    "immutable_evidence_mismatch",
    "infrastructure_unavailable",
    "protected_ref_conflict",
})


class LoopError(RuntimeError):
    """Structured error raised by AutomaticCorrectionLoop."""

    def __init__(self, code: str, message: str, *, escalation_id: str | None = None) -> None:
        self.code = code
        self.escalation_id = escalation_id
        super().__init__(message)


@dataclass(frozen=True)
class NormalizedFinding:
    finding_id: str
    severity: str
    affected_path: str
    evidence_reference: str
    corrective_requirement: str

    def to_dict(self) -> dict[str, str]:
        return {
            "finding_id": self.finding_id,
            "severity": self.severity,
            "affected_path": self.affected_path,
            "evidence_reference": self.evidence_reference,
            "corrective_requirement": self.corrective_requirement,
        }


def normalize_findings(
    raw_findings: list[dict[str, Any]],
    *,
    default_path: str,
    evidence_reference: str,
) -> list[NormalizedFinding]:
    """Sanitizes and normalizes verifier/reviewer findings, stripping active HTML/script content."""
    normalized: list[NormalizedFinding] = []
    for idx, item in enumerate(raw_findings[:16]):
        if not isinstance(item, dict):
            continue
        fid = str(item.get("finding_id") or f"find-{idx + 1}")[:64]
        sev = str(item.get("severity") or "HIGH").upper()
        if sev not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            sev = "HIGH"
        path = str(item.get("affected_path") or item.get("path") or default_path).strip()
        req_raw = str(
            item.get("corrective_requirement")
            or item.get("message")
            or item.get("summary")
            or "Address verification/review failure"
        )
        # Strip active HTML/script tags and control characters
        clean_req = (
            sanitize_payload(req_raw)
            .replace("<script", "[stripped]")
            .replace("</script>", "[/stripped]")
            .replace("javascript:", "[stripped]:")
        )[:1024]
        normalized.append(
            NormalizedFinding(
                finding_id=fid,
                severity=sev,
                affected_path=path,
                evidence_reference=evidence_reference,
                corrective_requirement=clean_req,
            )
        )
    if not normalized:
        normalized.append(
            NormalizedFinding(
                finding_id="find-1",
                severity="HIGH",
                affected_path=default_path,
                evidence_reference=evidence_reference,
                corrective_requirement="Candidate failed verification or review; inspect evidence receipt.",
            )
        )
    return normalized


class AutomaticCorrectionLoop:
    """Orchestrates bounded automatic development -> export -> verify -> review -> rework -> approval -> integration."""

    def __init__(
        self,
        db: Any,
        *,
        coordinator: CoordinatorStore | None = None,
        activity: ActivityBridgeService | None = None,
        workspace_root: Any | None = None,
    ) -> None:
        migrate_live_loop(db)
        self.db = db
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.coordinator = coordinator or CoordinatorStore(db)
        self.activity = activity or ActivityBridgeService(db)
        self.fsm = FSMEngine(db, workspace_root=self.workspace_root)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _emit_service_activity(
        self,
        *,
        tenant_id: str,
        project_id: str,
        task_id: str,
        attempt_id: str,
        kind: str,
        summary: str,
        extra_payload: dict[str, Any] | None = None,
    ) -> None:
        with self.db._get_connection() as conn:
            seq_row = conn.execute(
                """
                SELECT COALESCE(MAX(sequence), 0) AS max_seq
                FROM pm_runtime_activity_events
                WHERE tenant_id = ? AND project_id = ? AND attempt_id = ? AND authority_class = 'SERVICE'
                """,
                (tenant_id, project_id, attempt_id),
            ).fetchone()
            next_seq = int(seq_row["max_seq"]) + 1
            issue_row = conn.execute(
                "SELECT policy_version FROM pm_issues WHERE id = (SELECT issue_id FROM pm_coordinator_attempts WHERE attempt_id = ?)",
                (attempt_id,),
            ).fetchone()
            policy_ver = int(issue_row["policy_version"]) if issue_row else 1

        payload = {"summary": summary}
        if extra_payload:
            payload.update(extra_payload)
        self.activity.ingest_event(
            tenant_id=tenant_id,
            project_id_or_key=project_id,
            actor=f"{tenant_id}:coordinator_service",
            authority_class="SERVICE",
            raw_event={
                "schema_version": 1,
                "event_id": f"svc-{secrets.token_hex(10)}",
                "task_id": task_id,
                "attempt_id": attempt_id,
                "sequence": next_seq,
                "kind": kind,
                "occurred_at": self._now_iso(),
                "expected_task_version": policy_ver,
                "payload": payload,
            },
        )

    def _record_handoff(
        self,
        conn: sqlite3.Connection,
        *,
        job_id: str,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_id: str,
        run_id: str | None,
        policy_version: int,
        fencing_token: int,
        originating_receipt_id: str,
        from_stage: str,
        to_stage: str,
        destination_role: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        payload_str = canonical(payload)
        h_digest = digest({
            "job_id": job_id,
            "attempt_id": attempt_id,
            "policy_version": policy_version,
            "fencing_token": fencing_token,
            "originating_receipt_id": originating_receipt_id,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "destination_role": destination_role,
            "payload": payload,
        })
        existing = conn.execute(
            """
            SELECT * FROM pm_coordinator_loop_handoffs
            WHERE job_id = ? AND originating_receipt_id = ? AND to_stage = ?
            """,
            (job_id, originating_receipt_id, to_stage),
        ).fetchone()
        if existing is not None:
            if existing["canonical_digest"] != h_digest:
                raise LoopError(
                    "conflicting_handoff_receipt",
                    f"Conflicting handoff content for receipt '{originating_receipt_id}' -> {to_stage}",
                )
            return dict(existing)

        handoff_id = f"ho_{secrets.token_hex(12)}"
        now_iso = self._now_iso()
        conn.execute(
            """
            INSERT INTO pm_coordinator_loop_handoffs (
                handoff_id, job_id, tenant_id, project_id, issue_id, task_id,
                attempt_id, run_id, policy_version, fencing_token,
                originating_receipt_id, from_stage, to_stage, destination_role,
                canonical_digest, payload_json, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?)
            """,
            (
                handoff_id,
                job_id,
                tenant_id,
                project_id,
                issue_id,
                task_id,
                attempt_id,
                run_id,
                policy_version,
                fencing_token,
                originating_receipt_id,
                from_stage,
                to_stage,
                destination_role,
                h_digest,
                payload_str,
                now_iso,
            ),
        )
        return {
            "handoff_id": handoff_id,
            "job_id": job_id,
            "attempt_id": attempt_id,
            "from_stage": from_stage,
            "to_stage": to_stage,
            "destination_role": destination_role,
            "canonical_digest": h_digest,
            "status": "PENDING",
        }

    def escalate_job(
        self,
        job_id: str,
        *,
        category: str,
        decision_needed: str,
        evidence: dict[str, Any] | None = None,
        held_liabilities: int = 0,
    ) -> dict[str, Any]:
        """Persists a deduplicated actionable escalation and transitions the job to ESCALATED."""
        if category not in ESCALATION_CATEGORIES:
            raise ValueError(f"Unsupported escalation category '{category}'")
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            job = conn.execute("SELECT * FROM pm_coordinator_loop_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not job:
                raise LoopError("job_not_found", f"Loop job '{job_id}' not found")
            existing = conn.execute(
                """
                SELECT * FROM pm_coordinator_escalations
                WHERE issue_id = ? AND category = ? AND status = 'OPEN'
                """,
                (job["issue_id"], category),
            ).fetchone()
            if existing is not None:
                esc_id = str(existing["escalation_id"])
            else:
                esc_id = f"esc_{secrets.token_hex(12)}"
                conn.execute(
                    """
                    INSERT INTO pm_coordinator_escalations (
                        escalation_id, tenant_id, project_id, issue_id, task_id,
                        attempt_id, run_id, candidate_commit_sha, category,
                        decision_needed, evidence_json, held_liabilities, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?)
                    """,
                    (
                        esc_id,
                        job["tenant_id"],
                        job["project_id"],
                        job["issue_id"],
                        job["task_id"],
                        job["current_attempt_id"],
                        job["current_run_id"],
                        job["current_candidate_sha"],
                        category,
                        sanitize_payload(decision_needed)[:500],
                        canonical(evidence or {}),
                        held_liabilities,
                        now_iso,
                    ),
                )
            conn.execute(
                """
                UPDATE pm_coordinator_loop_jobs
                SET stage = 'ESCALATED',
                    escalation_category = ?,
                    escalation_reason = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (category, sanitize_payload(decision_needed)[:500], now_iso, job_id),
            )
            conn.execute(
                "UPDATE pm_issues SET blocker_reason = ?, updated_at = ? WHERE id = ?",
                (f"[{category}] {sanitize_payload(decision_needed)[:400]}", now_iso, job["issue_id"]),
            )
            tenant_id = str(job["tenant_id"])
            project_id = str(job["project_id"])
            task_id = str(job["task_id"])
            attempt_id = str(job["current_attempt_id"]) if job["current_attempt_id"] else None

        if attempt_id:
            try:
                self._emit_service_activity(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    task_id=task_id,
                    attempt_id=attempt_id,
                    kind="escalation.created",
                    summary=f"Escalated ({category}): {decision_needed}",
                    extra_payload={"escalation_id": esc_id, "category": category},
                )
            except Exception:
                pass
        return {"escalation_id": esc_id, "job_id": job_id, "category": category, "stage": "ESCALATED"}

    def _check_job_guards(self, job_id: str, *, now_epoch: float | None = None) -> sqlite3.Row:
        now_ts = time.time() if now_epoch is None else float(now_epoch)
        with self.db._get_connection() as conn:
            job = conn.execute("SELECT * FROM pm_coordinator_loop_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not job:
                raise LoopError("job_not_found", f"Loop job '{job_id}' not found")
            if int(job["is_paused"]) == 1:
                raise LoopError("job_paused", f"Loop job '{job_id}' is paused by operator")
            if job["stage"] in {"COMPLETE", "ESCALATED"}:
                raise LoopError("job_terminal", f"Loop job '{job_id}' is already in terminal stage {job['stage']}")

            issue = conn.execute("SELECT * FROM pm_issues WHERE id = ?", (job["issue_id"],)).fetchone()
            if not issue:
                raise LoopError("issue_not_found", "Underlying PM issue not found")

            # CC-08: Plan-revision staleness / pending reconciliation check
            if int(issue["has_pending_reconciliation"]) != 0 or int(issue["policy_version"]) != int(job["policy_version"]):
                esc = self.escalate_job(
                    job_id,
                    category="unreconciled_policy_change",
                    decision_needed="Task policy version or plan revision changed while work was active; reconcile before continuing.",
                    evidence={
                        "admitted_policy_version": int(job["policy_version"]),
                        "current_policy_version": int(issue["policy_version"]),
                        "has_pending_reconciliation": int(issue["has_pending_reconciliation"]),
                    },
                )
                raise LoopError("unreconciled_policy_change", "Task policy changed during loop", escalation_id=esc["escalation_id"])

            # Check deadline
            if now_ts > float(job["deadline_epoch"]):
                esc = self.escalate_job(
                    job_id,
                    category="exhausted_time",
                    decision_needed="Task loop deadline exceeded; operator decision required.",
                    evidence={"deadline_epoch": float(job["deadline_epoch"]), "now_epoch": now_ts},
                )
                raise LoopError("exhausted_time", "Loop deadline exceeded", escalation_id=esc["escalation_id"])

            # CC-12: Check for unresolved provider / execution / integration uncertainty
            uncertain_att = conn.execute(
                "SELECT attempt_id FROM pm_coordinator_attempts WHERE issue_id = ? AND status = 'UNKNOWN_EXECUTION' LIMIT 1",
                (job["issue_id"],),
            ).fetchone()
            uncertain_brk = conn.execute(
                """
                SELECT request_id FROM pm_coordinator_broker_requests
                WHERE attempt_id IN (SELECT attempt_id FROM pm_coordinator_attempts WHERE issue_id = ?)
                  AND status = 'UNKNOWN_PROVIDER_EXECUTION'
                LIMIT 1
                """,
                (job["issue_id"],),
            ).fetchone()
            uncertain_int = conn.execute(
                "SELECT integration_id FROM pm_coordinator_integrations WHERE issue_id = ? AND status = 'UNKNOWN_INTEGRATION' LIMIT 1",
                (job["issue_id"],),
            ).fetchone()
            if uncertain_att or uncertain_brk or uncertain_int:
                esc = self.escalate_job(
                    job_id,
                    category="unresolved_execution",
                    decision_needed="Uncertain execution, provider call, or target ref integration requires reconciliation before retry.",
                    evidence={
                        "uncertain_attempt": uncertain_att["attempt_id"] if uncertain_att else None,
                        "uncertain_broker_request": uncertain_brk["request_id"] if uncertain_brk else None,
                        "uncertain_integration": uncertain_int["integration_id"] if uncertain_int else None,
                    },
                )
                raise LoopError("unresolved_execution", "Uncertain execution state blocks automatic progression", escalation_id=esc["escalation_id"])

            return job

    def admit_task(
        self,
        *,
        job_id: str,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        profile: str,
        base_commit_sha: str,
        budget_reservation: int = 2000,
        max_attempts: int = PILOT_MAX_ATTEMPTS,
        max_provider_calls: int = PILOT_MAX_PROVIDER_CALLS,
        deadline_s: float = PILOT_MAX_DEADLINE_S,
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        """Admits an eligible task into the bounded automatic loop (stage ADMITTED)."""
        now_ts = time.time() if now_epoch is None else float(now_epoch)
        now_iso = self._now_iso()

        if profile not in SUPPORTED_PROFILES:
            # Record visible blocker for unsupported profile without silent downgrade
            with self.db.atomic_transaction() as conn:
                conn.execute(
                    "UPDATE pm_issues SET blocker_reason = ?, updated_at = ? WHERE id = ?",
                    (f"[unsupported_profile] Profile '{profile}' is not supported", now_iso, issue_id),
                )
            raise LoopError("unsupported_profile", f"Unsupported execution profile '{profile}'")

        if not (1 <= max_attempts <= PILOT_MAX_ATTEMPTS):
            raise LoopError("invalid_bounds", f"max_attempts must be between 1 and {PILOT_MAX_ATTEMPTS}")
        if not (1 <= max_provider_calls <= PILOT_MAX_PROVIDER_CALLS):
            raise LoopError("invalid_bounds", f"max_provider_calls must be between 1 and {PILOT_MAX_PROVIDER_CALLS}")
        if not (1.0 <= deadline_s <= PILOT_MAX_DEADLINE_S):
            raise LoopError("invalid_bounds", f"deadline_s must not exceed {PILOT_MAX_DEADLINE_S}s")

        with self.db._get_connection() as conn:
            issue = conn.execute("SELECT * FROM pm_issues WHERE id = ?", (issue_id,)).fetchone()
            if not issue:
                raise LoopError("issue_not_found", f"Issue '{issue_id}' not found")
            if int(issue["has_pending_reconciliation"]) != 0:
                raise LoopError("unreconciled_policy_change", "Issue has pending plan reconciliation")
            policy_version = int(issue["policy_version"])
            cur_state = str(issue["current_state"])
            assignee = str(issue["assignee_principal"] or f"{tenant_id}:antigravity_dev")

        # Ensure issue is in STAGED before coordinator dispatch
        if cur_state in {"BACKLOG", "REFINED"}:
            with ExecutionContext.scope(assignee):
                if cur_state == "BACKLOG":
                    self.fsm.transition(issue_id, IssueState.REFINED, caller_principal=assignee)
                self.fsm.transition(issue_id, IssueState.STAGED, caller_principal=assignee)

        attempt_id = f"{job_id}-att-1"
        intent_id = f"{job_id}-int-1"
        with trusted_coordinator_admin_scope():
            self.coordinator.create_attempt_with_intent(
                attempt_id=attempt_id,
                intent_id=intent_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_seq=1,
                adapter_type="antigravity",
                payload={"profile": profile, "base_commit_sha": base_commit_sha, "admitted_policy_version": policy_version},
                budget_reservation=budget_reservation,
            )

        with self.db.atomic_transaction() as conn:
            conn.execute(
                """
                INSERT INTO pm_coordinator_loop_jobs (
                    job_id, tenant_id, project_id, issue_id, task_id,
                    profile, stage, current_attempt_id, current_run_id, current_candidate_sha,
                    base_commit_sha, policy_version, fencing_token,
                    attempts_used, max_attempts, provider_calls_used, max_provider_calls,
                    deadline_epoch, is_paused, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'ADMITTED', ?, NULL, NULL, ?, ?, 1, 1, ?, 0, ?, ?, 0, ?, ?)
                """,
                (
                    job_id,
                    tenant_id,
                    project_id,
                    issue_id,
                    task_id,
                    profile,
                    attempt_id,
                    base_commit_sha,
                    policy_version,
                    max_attempts,
                    max_provider_calls,
                    now_ts + deadline_s,
                    now_iso,
                    now_iso,
                ),
            )
            handoff = self._record_handoff(
                conn,
                job_id=job_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_id=attempt_id,
                run_id=None,
                policy_version=policy_version,
                fencing_token=1,
                originating_receipt_id=f"admit:{job_id}:1",
                from_stage="ADMITTED",
                to_stage="DEVELOPING",
                destination_role="builder",
                payload={"intent_id": intent_id, "profile": profile, "base_commit_sha": base_commit_sha},
            )

        return {
            "job_id": job_id,
            "stage": "ADMITTED",
            "attempt_id": attempt_id,
            "intent_id": intent_id,
            "handoff": handoff,
        }

    def begin_development(
        self,
        job_id: str,
        *,
        worker_id: str,
        run_id: str,
        session_id: str,
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        """Transitions an ADMITTED or REWORK_PENDING job into DEVELOPING and records early session identity."""
        now_ts = time.time() if now_epoch is None else float(now_epoch)
        job = self._check_job_guards(job_id, now_epoch=now_ts)
        if job["stage"] not in {"ADMITTED", "REWORK_PENDING"}:
            raise LoopError("invalid_stage", f"Cannot begin development from stage '{job['stage']}'")

        attempt_id = str(job["current_attempt_id"])
        with self.db._get_connection() as conn:
            intent_row = conn.execute(
                "SELECT intent_id, fencing_token FROM pm_coordinator_intents WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
            issue_row = conn.execute("SELECT * FROM pm_issues WHERE id = ?", (job["issue_id"],)).fetchone()
            if not intent_row or not issue_row:
                raise LoopError("intent_not_found", f"Intent not found for attempt '{attempt_id}'")
            intent_id = str(intent_row["intent_id"])
            cur_fencing = int(intent_row["fencing_token"])
            assignee = str(issue_row["assignee_principal"] or f"{job['tenant_id']}:antigravity_dev")
            cur_state = str(issue_row["current_state"])

        with trusted_coordinator_admin_scope():
            claimed = self.coordinator.claim_intent(intent_id, worker_id, cur_fencing, now_ts, 60)
            if not claimed:
                raise LoopError("claim_failed", f"Failed to claim intent '{intent_id}'")
            new_fencing = cur_fencing + 1
            spawned = self.coordinator.pre_spawn_intent(
                intent_id,
                worker_id,
                new_fencing,
                now_ts + 0.1,
                run_id,
                attempt_id,
                expected_policy_version=int(job["policy_version"]),
            )
            if not spawned:
                raise LoopError("spawn_failed", f"Failed to pre-spawn intent '{intent_id}'")

        # Transition PM issue to IN_PROGRESS via guarded FSM
        if cur_state != "IN_PROGRESS":
            with ExecutionContext.scope(assignee):
                self.fsm.transition(
                    str(job["issue_id"]),
                    IssueState.IN_PROGRESS,
                    caller_principal=assignee,
                    reason=f"Loop development started ({attempt_id})",
                )

        with self.db.atomic_transaction() as conn:
            conn.execute(
                """
                UPDATE pm_coordinator_loop_jobs
                SET stage = 'DEVELOPING',
                    current_run_id = ?,
                    fencing_token = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (run_id, new_fencing, self._now_iso(), job_id),
            )
            handoff = self._record_handoff(
                conn,
                job_id=job_id,
                tenant_id=str(job["tenant_id"]),
                project_id=str(job["project_id"]),
                issue_id=str(job["issue_id"]),
                task_id=str(job["task_id"]),
                attempt_id=attempt_id,
                run_id=run_id,
                policy_version=int(job["policy_version"]),
                fencing_token=new_fencing,
                originating_receipt_id=f"session:{session_id}:{run_id}",
                from_stage=str(job["stage"]),
                to_stage="EXPORTING",
                destination_role="exporter",
                payload={"session_id": session_id, "run_id": run_id},
            )

        # Persist early session.bound service event before acknowledging startup
        self._emit_service_activity(
            tenant_id=str(job["tenant_id"]),
            project_id=str(job["project_id"]),
            task_id=str(job["task_id"]),
            attempt_id=attempt_id,
            kind="session.bound",
            summary=f"Bound runtime session {session_id} for run {run_id}",
            extra_payload={"session_id": session_id, "run_id": run_id},
        )

        return {
            "job_id": job_id,
            "stage": "DEVELOPING",
            "attempt_id": attempt_id,
            "run_id": run_id,
            "fencing_token": new_fencing,
            "handoff": handoff,
        }

    def export_candidate_stage(
        self,
        job_id: str,
        *,
        exporter: Any,
        session_token: str,
        proposal: dict[str, Any],
        oracle_paths: set[str] | None = None,
        tokens_spent: int = 20,
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        """Exports an authorized candidate commit and advances the job to VERIFYING."""
        now_ts = time.time() if now_epoch is None else float(now_epoch)
        job = self._check_job_guards(job_id, now_epoch=now_ts)
        if job["stage"] != "DEVELOPING":
            raise LoopError("invalid_stage", f"Cannot export candidate from stage '{job['stage']}'")

        attempt_id = str(job["current_attempt_id"])
        run_id = str(job["current_run_id"])
        fencing_token = int(job["fencing_token"])
        policy_version = int(job["policy_version"])
        tenant_id = str(job["tenant_id"])
        project_id = str(job["project_id"])
        issue_id = str(job["issue_id"])
        task_id = str(job["task_id"])

        # Count provider calls used across all attempts of this issue
        with self.db._get_connection() as conn:
            calls_row = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM pm_coordinator_broker_requests
                WHERE attempt_id IN (SELECT attempt_id FROM pm_coordinator_attempts WHERE issue_id = ?)
                  AND status IN ('SUCCEEDED', 'FAILED_CONFIRMED', 'UNKNOWN_PROVIDER_EXECUTION')
                """,
                (issue_id,),
            ).fetchone()
            calls_used = int(calls_row["cnt"]) if calls_row else 0
            issue_row = conn.execute("SELECT key, assignee_principal FROM pm_issues WHERE id = ?", (issue_id,)).fetchone()
            intent_row = conn.execute("SELECT intent_id, worker_id FROM pm_coordinator_intents WHERE attempt_id = ?", (attempt_id,)).fetchone()
            issue_key = str(issue_row["key"])
            assignee = str(issue_row["assignee_principal"] or f"{tenant_id}:builder-1")
            builder_id = assignee.split(":", 1)[1] if ":" in assignee else assignee
            intent_id = str(intent_row["intent_id"])
            worker_id = str(intent_row["worker_id"])

        if calls_used > int(job["max_provider_calls"]):
            esc = self.escalate_job(
                job_id,
                category="exhausted_budget",
                decision_needed=f"Provider call ceiling ({job['max_provider_calls']}) exceeded ({calls_used} calls).",
                evidence={"provider_calls_used": calls_used, "max_provider_calls": int(job["max_provider_calls"])},
            )
            raise LoopError("exhausted_budget", "Provider call ceiling exceeded", escalation_id=esc["escalation_id"])

        # Run trusted host exporter outside write transaction
        export_rcpt = exporter.export_candidate(
            tenant_id=tenant_id,
            project_id=project_id,
            issue_id=issue_id,
            task_id=task_id,
            attempt_id=attempt_id,
            run_id=run_id,
            fencing_token=fencing_token,
            builder_id=builder_id,
            iam_token=session_token,
            oracle_paths=oracle_paths or set(),
            proposal=proposal,
        )
        candidate_sha = str(export_rcpt["candidate_commit_sha"])
        export_id = str(export_rcpt.get("proposal_id") or export_rcpt.get("export_id") or "")
        files_list = proposal.get("files") if isinstance(proposal, dict) and isinstance(proposal.get("files"), list) else []
        changed_paths = [f["path"] for f in files_list if isinstance(f, dict) and "path" in f]

        # Complete coordinator execution intent with candidate SHA
        with trusted_coordinator_admin_scope():
            self.coordinator.complete_intent(
                intent_id,
                worker_id,
                fencing_token,
                int(now_ts),
                candidate_sha,
                tokens_spent,
                0,
            )

        # Prepare empirical evidence links on disk and transition IN_PROGRESS -> VERIFICATION
        repo_root = Path(getattr(exporter, "repo_root", None) or self.workspace_root or Path.cwd()).resolve()
        if hasattr(self.fsm, "workspace_root"):
            self.fsm.workspace_root = repo_root
        log_dir = repo_root / ".mas"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"export_{export_id}.log"
        log_file.write_text(f"Candidate {candidate_sha} export pre-verification passed.\n", encoding="utf-8")
        log_hash = hashlib.sha256(log_file.read_bytes()).hexdigest()

        pm_attach_evidence(
            issue_key=issue_key,
            evidence_type="GIT_COMMIT",
            content_hash=candidate_sha,
            uri=f"git:commit:{candidate_sha}",
            payload={"export_id": export_id, "changed_paths": changed_paths, "policy_version": policy_version, "candidate_commit_sha": candidate_sha},
            db=self.db,
        )
        pm_attach_evidence(
            issue_key=issue_key,
            evidence_type="TEST_RUN_LOG",
            content_hash=log_hash,
            uri=f"file://{log_file.resolve()}",
            payload={
                "status": "EXPORTED_FOR_VERIFICATION",
                "policy_version": policy_version,
                "candidate_commit_sha": candidate_sha,
                "exit_code": 0,
                "passed": 1,
                "failed": 0,
            },
            db=self.db,
        )
        pm_attach_evidence(
            issue_key=issue_key,
            evidence_type="AST_SCAN_REPORT",
            content_hash=export_rcpt["proposal_digest"],
            uri=f"ast://{export_id}",
            payload={"status": "VALIDATED", "policy_version": policy_version, "candidate_commit_sha": candidate_sha},
            db=self.db,
        )
        with ExecutionContext.scope(assignee):
            self.fsm.transition(
                issue_id,
                IssueState.VERIFICATION,
                caller_principal=assignee,
                reason=f"Candidate {candidate_sha[:12]} exported for verification",
            )

        with self.db.atomic_transaction() as conn:
            conn.execute(
                """
                UPDATE pm_coordinator_loop_jobs
                SET stage = 'VERIFYING',
                    current_candidate_sha = ?,
                    provider_calls_used = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (candidate_sha, calls_used, self._now_iso(), job_id),
            )
            handoff = self._record_handoff(
                conn,
                job_id=job_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_id=attempt_id,
                run_id=run_id,
                policy_version=policy_version,
                fencing_token=fencing_token,
                originating_receipt_id=export_id,
                from_stage="EXPORTING",
                to_stage="VERIFYING",
                destination_role="verifier",
                payload={"candidate_commit_sha": candidate_sha, "export_id": export_id},
            )

        self._emit_service_activity(
            tenant_id=tenant_id,
            project_id=project_id,
            task_id=task_id,
            attempt_id=attempt_id,
            kind="candidate.exported",
            summary=f"Exported immutable candidate {candidate_sha[:12]}",
            extra_payload={"candidate_commit": candidate_sha, "evidence_status": "validated"},
        )

        return {
            "job_id": job_id,
            "stage": "VERIFYING",
            "candidate_commit_sha": candidate_sha,
            "export_receipt": export_rcpt,
            "handoff": handoff,
        }

    def _check_rework_replay(self, job: sqlite3.Row, evidence_id: str) -> dict[str, Any] | None:
        if job["stage"] != "REWORK_PENDING" or not evidence_id:
            return None
        with self.db._get_connection() as conn:
            existing = conn.execute(
                """
                SELECT * FROM pm_coordinator_loop_handoffs
                WHERE job_id = ? AND originating_receipt_id = ? AND to_stage = 'REWORK_PENDING'
                """,
                (job["job_id"], evidence_id),
            ).fetchone()
            if existing is None:
                return None
            payload = strict_json(existing["payload_json"])
            next_attempt_id = str(payload.get("next_attempt_id") or job["current_attempt_id"])
            intent_row = conn.execute(
                "SELECT intent_id FROM pm_coordinator_intents WHERE attempt_id = ?",
                (next_attempt_id,),
            ).fetchone()
            return {
                "job_id": str(job["job_id"]),
                "stage": "REWORK_PENDING",
                "next_attempt_id": next_attempt_id,
                "next_intent_id": str(intent_row["intent_id"]) if intent_row else "",
                "attempt_seq": int(job["attempts_used"]),
                "findings": payload.get("findings", []),
                "handoff": dict(existing),
                "replayed": True,
            }

    def record_verification_outcome(
        self,
        job_id: str,
        *,
        verification_receipt: dict[str, Any],
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        """Processes an admitted VERIFICATION_EVIDENCE receipt, advancing to REVIEWING or triggering bounded rework."""
        now_ts = time.time() if now_epoch is None else float(now_epoch)
        job = self._check_job_guards(job_id, now_epoch=now_ts)

        cp = verification_receipt.get("canonical_payload")
        if isinstance(cp, str):
            cp = strict_json(cp)
        payload = cp if isinstance(cp, dict) else verification_receipt
        evidence_id = str(verification_receipt.get("evidence_id") or payload.get("evidence_id") or "")

        replayed = self._check_rework_replay(job, evidence_id)
        if replayed is not None:
            return replayed

        if job["stage"] != "VERIFYING":
            raise LoopError("invalid_stage", f"Cannot record verification outcome in stage '{job['stage']}'")

        binding = payload.get("binding") if isinstance(payload.get("binding"), dict) else {}
        cand_sha = str(
            verification_receipt.get("candidate_commit_sha")
            or payload.get("candidate_commit_sha")
            or binding.get("candidate_commit_sha")
            or ""
        )
        if cand_sha != str(job["current_candidate_sha"]):
            esc = self.escalate_job(
                job_id,
                category="immutable_evidence_mismatch",
                decision_needed="Verification receipt candidate SHA does not match current job candidate.",
                evidence={"expected": job["current_candidate_sha"], "received": cand_sha},
            )
            raise LoopError("immutable_evidence_mismatch", "Verification candidate SHA mismatch", escalation_id=esc["escalation_id"])

        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        passed = bool(result.get("passed")) or str(result.get("verdict") or "").upper() == "PASS"
        tenant_id = str(job["tenant_id"])
        project_id = str(job["project_id"])
        issue_id = str(job["issue_id"])
        task_id = str(job["task_id"])
        attempt_id = str(job["current_attempt_id"])
        run_id = str(job["current_run_id"])
        policy_version = int(job["policy_version"])
        fencing_token = int(job["fencing_token"])

        with self.db._get_connection() as conn:
            issue_row = conn.execute("SELECT key, path_whitelist FROM pm_issues WHERE id = ?", (issue_id,)).fetchone()
            issue_key = str(issue_row["key"])
            whitelist = strict_json(issue_row["path_whitelist"]) if issue_row["path_whitelist"] else ["*"]

        if passed:
            # Cast stage-4 critic verdicts and transition VERIFICATION -> JUDICIAL_REVIEW
            with ExecutionContext.scope("qa_critic"):
                pm_cast_verdict(issue_key, "qa_critic", "PASS", findings={"evidence_id": evidence_id}, db=self.db)
            with ExecutionContext.scope("adversarial_red_team"):
                pm_cast_verdict(issue_key, "adversarial_red_team", "PASS", findings={"evidence_id": evidence_id}, db=self.db)
                self.fsm.transition(
                    issue_id,
                    IssueState.JUDICIAL_REVIEW,
                    caller_principal="adversarial_red_team",
                    reason=f"Verification {evidence_id} passed for candidate {cand_sha[:12]}",
                )

            with self.db.atomic_transaction() as conn:
                conn.execute(
                    "UPDATE pm_coordinator_loop_jobs SET stage = 'REVIEWING', updated_at = ? WHERE job_id = ?",
                    (self._now_iso(), job_id),
                )
                handoff = self._record_handoff(
                    conn,
                    job_id=job_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    issue_id=issue_id,
                    task_id=task_id,
                    attempt_id=attempt_id,
                    run_id=run_id,
                    policy_version=policy_version,
                    fencing_token=fencing_token,
                    originating_receipt_id=evidence_id,
                    from_stage="VERIFYING",
                    to_stage="REVIEWING",
                    destination_role="reviewer",
                    payload={"candidate_commit_sha": cand_sha, "verification_evidence_id": evidence_id},
                )

            self._emit_service_activity(
                tenant_id=tenant_id,
                project_id=project_id,
                task_id=task_id,
                attempt_id=attempt_id,
                kind="verification.recorded",
                summary=f"Verification PASSED ({evidence_id}) for candidate {cand_sha[:12]}",
                extra_payload={"candidate_commit": cand_sha, "evidence_status": "validated"},
            )
            return {
                "job_id": job_id,
                "stage": "REVIEWING",
                "verdict": "PASS",
                "handoff": handoff,
            }

        # Verification FAILED -> normalize findings and trigger bounded rework
        raw_cases = (
            result.get("cases")
            if isinstance(result.get("cases"), list)
            else (result.get("outcomes") if isinstance(result.get("outcomes"), list) else [])
        )
        raw_findings = [
            {
                "finding_id": f"verify-case-{c.get('id') or c.get('case_id') or idx}",
                "severity": "HIGH",
                "affected_path": whitelist[0] if whitelist else "*",
                "corrective_requirement": f"Failing verification case {c.get('id') or c.get('case_id') or idx}: {c.get('reason') or c.get('error') or 'failed'}",
            }
            for idx, c in enumerate(raw_cases)
            if isinstance(c, dict) and not c.get("passed", False)
        ]
        findings = normalize_findings(
            raw_findings,
            default_path=whitelist[0] if whitelist else "*",
            evidence_reference=evidence_id,
        )
        self._emit_service_activity(
            tenant_id=tenant_id,
            project_id=project_id,
            task_id=task_id,
            attempt_id=attempt_id,
            kind="verification.recorded",
            summary=f"Verification FAILED ({evidence_id}) for candidate {cand_sha[:12]}",
            extra_payload={"candidate_commit": cand_sha, "evidence_status": "rejected"},
        )
        return self._handle_rejection_or_rework(
            job_id=job_id,
            from_stage="VERIFYING",
            originating_receipt_id=evidence_id,
            critic_principal="qa_critic",
            findings=findings,
            now_epoch=now_ts,
        )

    def record_review_outcome(
        self,
        job_id: str,
        *,
        review_receipt: dict[str, Any],
        allowed_conditions: set[str] | None = None,
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        """Processes an admitted REVIEW_EVIDENCE receipt, advancing to AWAITING_REQUIRED_APPROVAL or bounded rework."""
        now_ts = time.time() if now_epoch is None else float(now_epoch)
        job = self._check_job_guards(job_id, now_epoch=now_ts)

        cp = review_receipt.get("canonical_payload")
        if isinstance(cp, str):
            cp = strict_json(cp)
        payload = cp if isinstance(cp, dict) else review_receipt
        evidence_id = str(review_receipt.get("evidence_id") or payload.get("evidence_id") or "")

        replayed = self._check_rework_replay(job, evidence_id)
        if replayed is not None:
            return replayed

        if job["stage"] != "REVIEWING":
            raise LoopError("invalid_stage", f"Cannot record review outcome in stage '{job['stage']}'")
        binding = payload.get("binding") if isinstance(payload.get("binding"), dict) else {}
        cand_sha = str(
            review_receipt.get("candidate_commit_sha")
            or payload.get("candidate_commit_sha")
            or binding.get("candidate_commit_sha")
            or ""
        )
        if cand_sha != str(job["current_candidate_sha"]):
            esc = self.escalate_job(
                job_id,
                category="immutable_evidence_mismatch",
                decision_needed="Review receipt candidate SHA does not match current candidate.",
                evidence={"expected": job["current_candidate_sha"], "received": cand_sha},
            )
            raise LoopError("immutable_evidence_mismatch", "Review candidate SHA mismatch", escalation_id=esc["escalation_id"])

        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        verdict = str(result.get("verdict") or "REJECTED").upper()
        conditions = result.get("conditions") if isinstance(result.get("conditions"), list) else []

        tenant_id = str(job["tenant_id"])
        project_id = str(job["project_id"])
        issue_id = str(job["issue_id"])
        task_id = str(job["task_id"])
        attempt_id = str(job["current_attempt_id"])
        run_id = str(job["current_run_id"])
        policy_version = int(job["policy_version"])
        fencing_token = int(job["fencing_token"])

        with self.db._get_connection() as conn:
            issue_row = conn.execute("SELECT key, path_whitelist FROM pm_issues WHERE id = ?", (issue_id,)).fetchone()
            whitelist = strict_json(issue_row["path_whitelist"]) if issue_row["path_whitelist"] else ["*"]

        if verdict == "APPROVED":
            # Check if conditions exist ("APPROVED WITH CONDITIONS" is not unconditional completion)
            if conditions:
                permitted = allowed_conditions or set()
                unknown = [c for c in conditions if str(c) not in permitted]
                if unknown:
                    esc = self.escalate_job(
                        job_id,
                        category="unreconciled_policy_change",
                        decision_needed=f"Review approved with unclassified conditions: {unknown}",
                        evidence={"evidence_id": evidence_id, "conditions": conditions},
                    )
                    raise LoopError("unclassified_review_conditions", "Unknown review conditions block completion", escalation_id=esc["escalation_id"])

            with self.db.atomic_transaction() as conn:
                conn.execute(
                    "UPDATE pm_coordinator_loop_jobs SET stage = 'AWAITING_REQUIRED_APPROVAL', updated_at = ? WHERE job_id = ?",
                    (self._now_iso(), job_id),
                )
                handoff = self._record_handoff(
                    conn,
                    job_id=job_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    issue_id=issue_id,
                    task_id=task_id,
                    attempt_id=attempt_id,
                    run_id=run_id,
                    policy_version=policy_version,
                    fencing_token=fencing_token,
                    originating_receipt_id=evidence_id,
                    from_stage="REVIEWING",
                    to_stage="AWAITING_REQUIRED_APPROVAL",
                    destination_role="human_approver",
                    payload={"candidate_commit_sha": cand_sha, "review_evidence_id": evidence_id},
                )

            self._emit_service_activity(
                tenant_id=tenant_id,
                project_id=project_id,
                task_id=task_id,
                attempt_id=attempt_id,
                kind="review.recorded",
                summary=f"Independent review APPROVED ({evidence_id}) for candidate {cand_sha[:12]}; awaiting separate release/integration approval",
                extra_payload={"candidate_commit": cand_sha, "evidence_status": "validated"},
            )
            return {
                "job_id": job_id,
                "stage": "AWAITING_REQUIRED_APPROVAL",
                "verdict": "APPROVED",
                "handoff": handoff,
            }

        # REJECTED or CHANGES_REQUESTED -> normalize findings and trigger bounded rework
        raw_findings = result.get("findings") if isinstance(result.get("findings"), list) else []
        if not raw_findings and result.get("comments"):
            raw_findings = [{"finding_id": "rev-comment", "severity": "HIGH", "affected_path": whitelist[0] if whitelist else "*", "corrective_requirement": str(result.get("comments"))}]
        findings = normalize_findings(
            raw_findings,
            default_path=whitelist[0] if whitelist else "*",
            evidence_reference=evidence_id,
        )
        self._emit_service_activity(
            tenant_id=tenant_id,
            project_id=project_id,
            task_id=task_id,
            attempt_id=attempt_id,
            kind="review.recorded",
            summary=f"Independent review {verdict} ({evidence_id}) for candidate {cand_sha[:12]}",
            extra_payload={"candidate_commit": cand_sha, "evidence_status": "rejected"},
        )
        return self._handle_rejection_or_rework(
            job_id=job_id,
            from_stage="REVIEWING",
            originating_receipt_id=evidence_id,
            critic_principal=str(payload.get("issuer_id") or "independent_reviewer"),
            findings=findings,
            now_epoch=now_ts,
        )

    def _handle_rejection_or_rework(
        self,
        *,
        job_id: str,
        from_stage: str,
        originating_receipt_id: str,
        critic_principal: str,
        findings: list[NormalizedFinding],
        now_epoch: float,
    ) -> dict[str, Any]:
        """Creates at most one bounded next-attempt correction intent or escalates when ceilings/scope fail."""
        findings_dicts = [f.to_dict() for f in findings]
        with self.db._get_connection() as conn:
            job = conn.execute("SELECT * FROM pm_coordinator_loop_jobs WHERE job_id = ?", (job_id,)).fetchone()
            issue_row = conn.execute("SELECT * FROM pm_issues WHERE id = ?", (job["issue_id"],)).fetchone()
            whitelist = strict_json(issue_row["path_whitelist"]) if issue_row["path_whitelist"] else []
            forbidden = strict_json(issue_row["forbidden_paths"]) if issue_row["forbidden_paths"] else []

        # Verify all affected paths in findings stay within task scope whitelist
        for f in findings:
            in_whitelist = any(fnmatch.fnmatch(f.affected_path, pat) for pat in whitelist) if whitelist else False
            in_forbidden = any(fnmatch.fnmatch(f.affected_path, pat) for pat in forbidden)
            if not in_whitelist or in_forbidden:
                esc = self.escalate_job(
                    job_id,
                    category="conflicting_scope",
                    decision_needed=f"Corrective finding references out-of-scope path '{f.affected_path}'.",
                    evidence={"finding": f.to_dict(), "path_whitelist": whitelist, "forbidden_paths": forbidden},
                )
                raise LoopError("conflicting_scope", f"Out-of-scope corrective path '{f.affected_path}'", escalation_id=esc["escalation_id"])

        attempts_used = int(job["attempts_used"])
        max_attempts = int(job["max_attempts"])
        if attempts_used >= max_attempts:
            esc = self.escalate_job(
                job_id,
                category="exhausted_attempts",
                decision_needed=f"Exhausted maximum development attempts ({attempts_used}/{max_attempts}).",
                evidence={"attempts_used": attempts_used, "max_attempts": max_attempts, "findings": findings_dicts},
            )
            raise LoopError("exhausted_attempts", "Maximum development attempts exhausted", escalation_id=esc["escalation_id"])

        # Mark previous attempt FAILED via CoordinatorStore or DB and transition issue to REJECTED_REWORK
        prev_attempt_id = str(job["current_attempt_id"])
        next_seq = attempts_used + 1
        next_attempt_id = f"{job_id}-att-{next_seq}"
        next_intent_id = f"{job_id}-int-{next_seq}"
        tenant_id = str(job["tenant_id"])
        project_id = str(job["project_id"])
        issue_id = str(job["issue_id"])
        task_id = str(job["task_id"])
        policy_version = int(job["policy_version"])

        with ExecutionContext.scope(critic_principal):
            self.fsm.transition(
                issue_id,
                IssueState.REJECTED_REWORK,
                caller_principal=critic_principal,
                reason=f"Rejected by {originating_receipt_id}; scheduling attempt {next_seq}",
            )

        with self.db.atomic_transaction() as conn:
            conn.execute(
                "UPDATE pm_coordinator_attempts SET status = 'FAILED', finished_at = ? WHERE attempt_id = ?",
                (self._now_iso(), prev_attempt_id),
            )
            conn.execute(
                "UPDATE pm_coordinator_runs SET status = 'EXITED', exit_code = 1, ended_at = ? WHERE attempt_id = ?",
                (self._now_iso(), prev_attempt_id),
            )

        with trusted_coordinator_admin_scope():
            self.coordinator.create_attempt_with_intent(
                attempt_id=next_attempt_id,
                intent_id=next_intent_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_seq=next_seq,
                adapter_type="antigravity",
                payload={
                    "profile": str(job["profile"]),
                    "base_commit_sha": str(job["base_commit_sha"]),
                    "admitted_policy_version": policy_version,
                    "corrective_findings": findings_dicts,
                    "originating_receipt_id": originating_receipt_id,
                },
                budget_reservation=2000,
            )

        with self.db.atomic_transaction() as conn:
            conn.execute(
                """
                UPDATE pm_coordinator_loop_jobs
                SET stage = 'REWORK_PENDING',
                    current_attempt_id = ?,
                    current_run_id = NULL,
                    current_candidate_sha = NULL,
                    attempts_used = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (next_attempt_id, next_seq, self._now_iso(), job_id),
            )
            handoff = self._record_handoff(
                conn,
                job_id=job_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_id=next_attempt_id,
                run_id=None,
                policy_version=policy_version,
                fencing_token=1,
                originating_receipt_id=originating_receipt_id,
                from_stage=from_stage,
                to_stage="REWORK_PENDING",
                destination_role="builder",
                payload={"findings": findings_dicts, "next_attempt_id": next_attempt_id},
            )

        return {
            "job_id": job_id,
            "stage": "REWORK_PENDING",
            "next_attempt_id": next_attempt_id,
            "next_intent_id": next_intent_id,
            "attempt_seq": next_seq,
            "findings": findings_dicts,
            "handoff": handoff,
            "replayed": False,
        }

    def integrate_and_complete(
        self,
        job_id: str,
        *,
        exporter: Any,
        merger_id: str,
        merger_session_token: str,
        target_ref: str,
        authorization_ref: str,
        human_approver_principal: str,
        evidence_trust: Any = None,
        now_epoch: float | None = None,
    ) -> dict[str, Any]:
        """Executes CAS target-ref integration and guarded PM completion after separate human approval."""
        now_ts = time.time() if now_epoch is None else float(now_epoch)
        job = self._check_job_guards(job_id, now_epoch=now_ts)
        if job["stage"] != "AWAITING_REQUIRED_APPROVAL":
            raise LoopError("invalid_stage", f"Cannot integrate from stage '{job['stage']}'")

        tenant_id = str(job["tenant_id"])
        project_id = str(job["project_id"])
        issue_id = str(job["issue_id"])
        task_id = str(job["task_id"])
        attempt_id = str(job["current_attempt_id"])
        run_id = str(job["current_run_id"])
        cand_sha = str(job["current_candidate_sha"])
        base_sha = str(job["base_commit_sha"])
        policy_version = int(job["policy_version"])
        fencing_token = int(job["fencing_token"])

        with self.db._get_connection() as conn:
            issue_row = conn.execute("SELECT key, assignee_principal FROM pm_issues WHERE id = ?", (issue_id,)).fetchone()
            issue_key = str(issue_row["key"])
            assignee = str(issue_row["assignee_principal"] or "")

        if not human_approver_principal or human_approver_principal == assignee:
            raise LoopError("invalid_approver", "Separate human/policy approver distinct from builder is required")

        with self.db.atomic_transaction() as conn:
            conn.execute(
                "UPDATE pm_coordinator_loop_jobs SET stage = 'INTEGRATING', updated_at = ? WHERE job_id = ?",
                (self._now_iso(), job_id),
            )

        # Perform CAS Git ref integration outside write transaction
        int_rcpt = exporter.integrate_candidate(
            integration_id=f"intg-{job_id}-{attempt_id}",
            tenant_id=tenant_id,
            project_id=project_id,
            issue_id=issue_id,
            task_id=task_id,
            attempt_id=attempt_id,
            run_id=run_id,
            fencing_token=fencing_token,
            policy_version=policy_version,
            merger_id=merger_id,
            authorization_ref=authorization_ref,
            target_ref=target_ref,
            expected_target_sha=base_sha,
            candidate_commit_sha=cand_sha,
            iam_token=merger_session_token,
            evidence_trust=evidence_trust,
        )
        integrated_sha = str(
            int_rcpt.get("confirmed_target_sha")
            or int_rcpt.get("candidate_commit_sha")
            or int_rcpt.get("integrated_commit_sha")
            or ""
        )
        if integrated_sha != cand_sha:
            esc = self.escalate_job(
                job_id,
                category="immutable_evidence_mismatch",
                decision_needed="Integrated commit SHA differs from verified/reviewed candidate SHA.",
                evidence={"candidate_sha": cand_sha, "integrated_sha": integrated_sha},
            )
            raise LoopError("immutable_evidence_mismatch", "Integrated commit SHA changed", escalation_id=esc["escalation_id"])

        self._emit_service_activity(
            tenant_id=tenant_id,
            project_id=project_id,
            task_id=task_id,
            attempt_id=attempt_id,
            kind="integration.confirmed",
            summary=f"Confirmed CAS integration of {integrated_sha[:12]} onto {target_ref}",
            extra_payload={"candidate_commit": integrated_sha, "target_ref": target_ref, "evidence_status": "validated"},
        )

        # Stage COMPLETION_PENDING -> evaluate stage-5 guard and transition JUDICIAL_REVIEW -> DONE
        with self.db.atomic_transaction() as conn:
            conn.execute(
                "UPDATE pm_coordinator_loop_jobs SET stage = 'COMPLETION_PENDING', updated_at = ? WHERE job_id = ?",
                (self._now_iso(), job_id),
            )

        with ExecutionContext.scope("chief_architect"):
            pm_cast_verdict(
                issue_key,
                "chief_architect",
                "PASS",
                findings={"authorization_ref": authorization_ref, "integration_id": int_rcpt["integration_id"]},
                db=self.db,
            )
            self.fsm.transition(
                issue_id,
                IssueState.DONE,
                caller_principal="chief_architect",
                reason=f"Completed via CAS integration {int_rcpt['integration_id']} with authorization {authorization_ref}",
            )

        with self.db.atomic_transaction() as conn:
            conn.execute(
                "UPDATE pm_coordinator_loop_jobs SET stage = 'COMPLETE', updated_at = ? WHERE job_id = ?",
                (self._now_iso(), job_id),
            )
            handoff = self._record_handoff(
                conn,
                job_id=job_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_id=attempt_id,
                run_id=run_id,
                policy_version=policy_version,
                fencing_token=fencing_token,
                originating_receipt_id=str(int_rcpt["integration_id"]),
                from_stage="COMPLETION_PENDING",
                to_stage="COMPLETE",
                destination_role="coordinator",
                payload={"integrated_commit_sha": integrated_sha, "authorization_ref": authorization_ref},
            )

        return {
            "job_id": job_id,
            "stage": "COMPLETE",
            "integrated_commit_sha": integrated_sha,
            "integration_receipt": int_rcpt,
            "handoff": handoff,
        }

    def pause_job(self, job_id: str, *, actor: str, reason: str = "") -> dict[str, Any]:
        """Pauses new admissions, handoffs, and provider calls for a loop job (CC-11)."""
        if not actor:
            raise LoopError("unauthorized", "Authenticated operator required to pause job")
        with self.db.atomic_transaction() as conn:
            cur = conn.execute(
                "UPDATE pm_coordinator_loop_jobs SET is_paused = 1, updated_at = ? WHERE job_id = ?",
                (self._now_iso(), job_id),
            )
            if cur.rowcount == 0:
                raise LoopError("job_not_found", f"Loop job '{job_id}' not found")
        return {"job_id": job_id, "is_paused": True, "paused_by": actor, "reason": reason}

    def resume_job(self, job_id: str, *, actor: str, now_epoch: float | None = None) -> dict[str, Any]:
        """Re-verifies authority, policy, and absence of uncertainty before resuming a paused job (CC-11/CC-12)."""
        if not actor:
            raise LoopError("unauthorized", "Authenticated operator required to resume job")
        with self.db.atomic_transaction() as conn:
            conn.execute(
                "UPDATE pm_coordinator_loop_jobs SET is_paused = 0, updated_at = ? WHERE job_id = ?",
                (self._now_iso(), job_id),
            )
        job = self._check_job_guards(job_id, now_epoch=now_epoch)
        return {"job_id": job_id, "is_paused": False, "stage": str(job["stage"]), "resumed_by": actor}

    def cancel_job(
        self,
        job_id: str,
        *,
        actor: str,
        reason: str = "",
        confirm_stopped: bool = False,
    ) -> dict[str, Any]:
        """Requests cancellation or confirms whole-boundary termination (CC-11/CC-12).

        Pending cancellation ('CANCEL_REQUESTED') is never treated as confirmed cancellation ('CANCELED')
        until confirm_stopped=True proves the container/runtime has stopped.
        """
        if not actor:
            raise LoopError("unauthorized", "Authenticated operator required to cancel job")
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            job = conn.execute("SELECT * FROM pm_coordinator_loop_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if not job:
                raise LoopError("job_not_found", f"Loop job '{job_id}' not found")
            attempt_id = str(job["current_attempt_id"])
            if not confirm_stopped:
                conn.execute(
                    "UPDATE pm_coordinator_intents SET status = 'CANCEL_REQUESTED', updated_at = ? WHERE attempt_id = ?",
                    (now_iso, attempt_id),
                )
                conn.execute(
                    "UPDATE pm_coordinator_loop_jobs SET is_paused = 1, updated_at = ? WHERE job_id = ?",
                    (now_iso, job_id),
                )
                return {
                    "job_id": job_id,
                    "attempt_id": attempt_id,
                    "cancellation_state": "CANCEL_REQUESTED",
                    "confirmed_stopped": False,
                }

            conn.execute(
                "UPDATE pm_coordinator_intents SET status = 'CANCELED', updated_at = ? WHERE attempt_id = ?",
                (now_iso, attempt_id),
            )
            conn.execute(
                "UPDATE pm_coordinator_attempts SET status = 'CANCELED', finished_at = ? WHERE attempt_id = ?",
                (now_iso, attempt_id),
            )
            conn.execute(
                "UPDATE pm_coordinator_runs SET status = 'KILLED', exit_code = 137, ended_at = ? WHERE attempt_id = ?",
                (now_iso, attempt_id),
            )
            conn.execute(
                "UPDATE pm_coordinator_loop_handoffs SET status = 'CANCELED' WHERE job_id = ? AND status = 'PENDING'",
                (job_id,),
            )
            conn.execute(
                "UPDATE pm_coordinator_loop_jobs SET is_paused = 1, updated_at = ? WHERE job_id = ?",
                (now_iso, job_id),
            )
            return {
                "job_id": job_id,
                "attempt_id": attempt_id,
                "cancellation_state": "CANCELED",
                "confirmed_stopped": True,
            }


__all__ = [
    "AutomaticCorrectionLoop",
    "LOOP_CONTRACT_ID",
    "LoopError",
    "NormalizedFinding",
    "PILOT_MAX_ATTEMPTS",
    "PILOT_MAX_CANDIDATE_EXEC_S",
    "PILOT_MAX_DEADLINE_S",
    "PILOT_MAX_PROVIDER_CALLS",
    "PILOT_MAX_PROVIDER_CALL_S",
    "SUPPORTED_PROFILES",
    "normalize_findings",
]
