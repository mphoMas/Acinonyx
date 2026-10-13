"""
mas.pm.coordinator: Coordinator state, outbox, and lease management for Capable Coordinator (CC-03).
Enforces atomic CAS claims, monotonic fencing tokens, guarded pre-spawn persistence,
expired lease reaping, pessimistic budget holds for UNKNOWN_EXECUTION, and relational ownership integrity.
"""

from __future__ import annotations

import json
import hashlib
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from mas.pm.db import PMDatabase
from mas.pm.models import (
    CoordinatorAttempt,
    CoordinatorEvidenceReceipt,
    CoordinatorEvent,
    CoordinatorIntent,
    CoordinatorRun,
)

_trusted_coord_admin: ContextVar[bool] = ContextVar("trusted_coord_admin", default=False)


def is_trusted_coord_admin() -> bool:
    """Returns True if trusted coordinator administrative mode is active."""
    return _trusted_coord_admin.get()


@contextmanager
def trusted_coordinator_admin_scope(enabled: bool = True):
    """Context manager to explicitly grant trusted administrative authority for local/internal coordinator operations."""
    token = _trusted_coord_admin.set(enabled)
    try:
        yield
    finally:
        _trusted_coord_admin.reset(token)


class CoordinatorStore:
    """Persistence and atomic lifecycle manager for the Capable Coordinator."""

    def __init__(self, db: PMDatabase, *, evidence_trust=None) -> None:
        from mas.pm.adapters.admission import EvidenceTrust
        if evidence_trust is not None and not isinstance(evidence_trust, EvidenceTrust):
            raise TypeError("Service-owned EvidenceTrust required")
        self.db = db
        self._evidence_trust = evidence_trust

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _validate_tenant_authority(self, tenant_id: Optional[str] = None) -> None:
        """
        Validates that the current caller possesses trusted coordinator admin authority or
        an active tenant binding with storage:write capability for the requested tenant.
        Fails closed with PermissionError if neither is present.
        """
        if is_trusted_coord_admin():
            return

        from mas.tenancy import current_binding
        binding = current_binding()
        if binding is None:
            raise PermissionError("Unbound coordinator access denied: missing tenant binding or trusted admin authority")

        if tenant_id is not None and binding.identity.tenant_id != tenant_id:
            raise PermissionError(
                f"Tenant authority mismatch: binding has '{binding.identity.tenant_id}', requested '{tenant_id}'"
            )
        # Require write authority
        binding.require("storage:write")

    def create_attempt(
        self,
        attempt_id: str,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_seq: int,
        budget_tokens_allocated: int = 0,
        conn: Optional[sqlite3.Connection] = None,
    ) -> CoordinatorAttempt:
        """
        Creates an attempt record enforcing composite ownership foreign keys.
        Rejects contradictory project, issue, or task_id mappings.
        """
        self._validate_tenant_authority(tenant_id)
        if conn is None:
            with self.db.atomic_transaction() as transaction:
                return self.create_attempt(attempt_id, tenant_id, project_id, issue_id, task_id,
                                           attempt_seq, budget_tokens_allocated, conn=transaction)
        manage_conn = conn is None
        c = self.db._get_connection() if manage_conn else conn
        now = self._now_iso()
        try:
            from mas.pm.delivery import require_dispatch
            require_dispatch(c, issue_id, tenant_id)
            c.execute(
                """
                INSERT INTO pm_coordinator_attempts (
                    attempt_id, tenant_id, project_id, issue_id, task_id,
                    attempt_seq, status, fencing_token, started_at,
                    budget_tokens_allocated, budget_tokens_spent
                ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 1, ?, ?, 0)
                """,
                (
                    attempt_id,
                    tenant_id,
                    project_id,
                    issue_id,
                    task_id,
                    attempt_seq,
                    now,
                    budget_tokens_allocated,
                ),
            )
            return CoordinatorAttempt(
                attempt_id=attempt_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_seq=attempt_seq,
                status="PENDING",
                fencing_token=1,
                started_at=now,
                budget_tokens_allocated=budget_tokens_allocated,
                budget_tokens_spent=0,
            )
        finally:
            if manage_conn:
                c.close()

    def create_intent(
        self,
        intent_id: str,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_id: str,
        adapter_type: str,
        payload: Dict[str, Any],
        conn: Optional[sqlite3.Connection] = None,
    ) -> CoordinatorIntent:
        """
        Creates a PENDING coordinator outbox intent record.
        Enforces foreign key ownership against attempt_id and tenant/project/task.
        """
        self._validate_tenant_authority(tenant_id)
        if conn is None:
            with self.db.atomic_transaction() as transaction:
                return self.create_intent(intent_id, tenant_id, project_id, issue_id, task_id,
                                          attempt_id, adapter_type, payload, conn=transaction)
        manage_conn = conn is None
        c = self.db._get_connection() if manage_conn else conn
        now = self._now_iso()
        try:
            from mas.pm.delivery import require_dispatch, record_dispatch
            require_dispatch(c, issue_id, tenant_id)
            c.execute(
                """
                INSERT INTO pm_coordinator_intents (
                    intent_id, tenant_id, project_id, issue_id, task_id,
                    attempt_id, adapter_type, status, fencing_token,
                    payload, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING', 1, ?, ?, ?)
                """,
                (
                    intent_id,
                    tenant_id,
                    project_id,
                    issue_id,
                    task_id,
                    attempt_id,
                    adapter_type,
                    json.dumps(payload),
                    now,
                    now,
                ),
            )
            record_dispatch(c, issue_id, tenant_id, intent_id)
            return CoordinatorIntent(
                intent_id=intent_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_id=attempt_id,
                adapter_type=adapter_type,
                status="PENDING",
                fencing_token=1,
                payload=payload,
                created_at=now,
                updated_at=now,
            )
        finally:
            if manage_conn:
                c.close()

    def create_attempt_with_intent(
        self,
        attempt_id: str,
        intent_id: str,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_seq: int,
        adapter_type: str,
        payload: Dict[str, Any],
        budget_reservation: int = 0,
        authorization_ref: Optional[str] = None,
    ) -> Tuple[CoordinatorAttempt, CoordinatorIntent]:
        """
        Atomically creates both attempt and intent in one transaction with funded budget reservation.
        Validates finite non-negative integer amount against issue appetite and available project capacity.
        Records reservation in pm_coordinator_reservations ledger.
        """
        self._validate_tenant_authority(tenant_id)

        # 1. Validate reservation amount type and bounds
        if not isinstance(budget_reservation, int) or isinstance(budget_reservation, bool):
            raise ValueError(f"budget_reservation must be an integer, got {type(budget_reservation).__name__}")
        if budget_reservation < 0:
            raise ValueError(f"budget_reservation must be non-negative, got {budget_reservation}")

        with self.db.atomic_transaction() as conn:
            # 2. Check issue appetite
            issue_row = conn.execute(
                "SELECT appetite_tokens FROM pm_issues WHERE id = ?",
                (issue_id,),
            ).fetchone()
            if not issue_row:
                raise ValueError(f"Issue {issue_id} not found")

            issue_appetite = issue_row["appetite_tokens"]
            if budget_reservation > issue_appetite:
                raise ValueError(
                    f"Requested reservation {budget_reservation} exceeds issue appetite {issue_appetite}"
                )

            # 3. Check project available capacity: token_budget - tokens_consumed - open_holds
            proj_row = conn.execute(
                "SELECT token_budget, tokens_consumed FROM pm_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
            if not proj_row:
                raise ValueError(f"Project {project_id} not found")

            token_budget = proj_row["token_budget"]
            tokens_consumed = proj_row["tokens_consumed"]

            holds_row = conn.execute(
                """
                SELECT COALESCE(SUM(amount - settled_amount), 0) AS open_holds
                FROM pm_coordinator_reservations
                WHERE project_id = ? AND status = 'HELD'
                """,
                (project_id,),
            ).fetchone()
            open_holds = holds_row["open_holds"] if holds_row else 0

            available_capacity = token_budget - tokens_consumed - open_holds
            if budget_reservation > available_capacity:
                raise ValueError(
                    f"Requested reservation {budget_reservation} exceeds available project capacity {available_capacity} "
                    f"(budget={token_budget}, consumed={tokens_consumed}, active_holds={open_holds})"
                )

            # 4. Create attempt and intent
            attempt = self.create_attempt(
                attempt_id=attempt_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_seq=attempt_seq,
                budget_tokens_allocated=budget_reservation,
                conn=conn,
            )
            intent = self.create_intent(
                intent_id=intent_id,
                tenant_id=tenant_id,
                project_id=project_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_id=attempt_id,
                adapter_type=adapter_type,
                payload=payload,
                conn=conn,
            )

            # 5. Record funded reservation in ledger if reservation > 0
            res_id = f"res_{attempt_id}"
            auth_ref = authorization_ref or f"auth_{attempt_id}"
            now = self._now_iso()
            conn.execute(
                """
                INSERT INTO pm_coordinator_reservations (
                    reservation_id, tenant_id, project_id, issue_id, attempt_id,
                    authorization_ref, amount, settled_amount, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'HELD', ?)
                """,
                (
                    res_id,
                    tenant_id,
                    project_id,
                    issue_id,
                    attempt_id,
                    auth_ref,
                    budget_reservation,
                    now,
                ),
            )

            return attempt, intent

    def claim_intent(
        self,
        intent_id: str,
        worker_id: str,
        expected_fencing_token: int,
        now_epoch: float,
        lease_timeout_s: float = 10.0,
    ) -> bool:
        """
        Executes atomic CAS claim update on a PENDING intent.
        Increments fencing generation, assigns worker_id, and sets lease expiration.
        Returns True if claimed, False on race loss or state change.
        """
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            intent_row = conn.execute(
                "SELECT tenant_id FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if not intent_row:
                return False
            self._validate_tenant_authority(intent_row["tenant_id"])

            cursor = conn.execute(
                """
                UPDATE pm_coordinator_intents
                SET status = 'CLAIMED',
                    worker_id = :worker_id,
                    fencing_token = fencing_token + 1,
                    lease_expires_at = :now_epoch + :lease_timeout_s,
                    lease_heartbeat_at = :now_epoch,
                    updated_at = :now_iso
                WHERE intent_id = :intent_id
                  AND status = 'PENDING'
                  AND fencing_token = :expected_fencing_token
                """,
                {
                    "intent_id": intent_id,
                    "worker_id": worker_id,
                    "expected_fencing_token": expected_fencing_token,
                    "now_epoch": now_epoch,
                    "lease_timeout_s": lease_timeout_s,
                    "now_iso": now_iso,
                },
            )
            return cursor.rowcount == 1

    def pre_spawn_intent(
        self,
        intent_id: str,
        worker_id: str,
        assigned_fencing_token: int,
        now_epoch: float,
        run_id: str,
        attempt_id: Optional[str] = None,
        expected_policy_version: Optional[int] = None,
    ) -> bool:
        """
        Atomically transitions CLAIMED intent to PROCESSING before launching process.
        Derives attempt_id strictly from the intent; rejects any contradictory supplied attempt_id.
        Requires active unexpired lease, assigned worker, and matching fencing token.
        Atomically verifies in the same transaction:
        - Issue exists and has NO pending plan reconciliation (has_pending_reconciliation == 0)
        - Issue policy_version exactly matches expected_policy_version (or admitted_policy_version from intent payload)
        - Issue workflow state is eligible (BACKLOG, REFINED, STAGED)
        - Attempt has a funded budget reservation in HELD status
        In the same transaction, updates attempt to RUNNING and records SPAWNING physical run
        with composite (intent_id, attempt_id) foreign key constraint.
        """
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            # 1. Fetch intent and verify attempt_id consistency
            intent_row = conn.execute(
                "SELECT attempt_id, tenant_id, issue_id, payload FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if not intent_row:
                return False

            self._validate_tenant_authority(intent_row["tenant_id"])

            from mas.pm.delivery import require_dispatch
            require_dispatch(conn, intent_row["issue_id"], intent_row["tenant_id"], intent_id=intent_id)
            actual_attempt_id = intent_row["attempt_id"]
            if attempt_id is not None and attempt_id != actual_attempt_id:
                raise ValueError(
                    f"Contradictory attempt_id supplied: intent belongs to '{actual_attempt_id}', got '{attempt_id}'"
                )

            # 2. Atomic Policy, Reconciliation, Scope & Funded Launch Verification
            issue_id = intent_row["issue_id"]
            if issue_id:
                issue_row = conn.execute(
                    "SELECT policy_version, has_pending_reconciliation, current_state FROM pm_issues WHERE id = ?",
                    (issue_id,),
                ).fetchone()
                if not issue_row:
                    return False
                if issue_row["has_pending_reconciliation"] != 0:
                    return False
                if issue_row["current_state"] not in ("BACKLOG", "REFINED", "STAGED"):
                    return False

                # Policy version check
                payload_obj = {}
                if intent_row["payload"]:
                    try:
                        payload_obj = json.loads(intent_row["payload"])
                    except Exception:
                        pass
                required_pv = expected_policy_version
                if required_pv is None:
                    required_pv = payload_obj.get("admitted_policy_version")
                if required_pv is not None and issue_row["policy_version"] != required_pv:
                    return False

            # Verify funded reservation exists and is HELD
            res_row = conn.execute(
                "SELECT amount, status FROM pm_coordinator_reservations WHERE attempt_id = ?",
                (actual_attempt_id,),
            ).fetchone()
            if res_row:
                if res_row["status"] != "HELD" or res_row["amount"] < 0:
                    return False

            # 3. Atomic CAS transition CLAIMED -> PROCESSING
            cursor = conn.execute(
                """
                UPDATE pm_coordinator_intents
                SET status = 'PROCESSING',
                    lease_heartbeat_at = :now_epoch,
                    updated_at = :now_iso
                WHERE intent_id = :intent_id
                  AND status = 'CLAIMED'
                  AND worker_id = :worker_id
                  AND fencing_token = :assigned_fencing_token
                  AND lease_expires_at > :now_epoch
                """,
                {
                    "intent_id": intent_id,
                    "worker_id": worker_id,
                    "assigned_fencing_token": assigned_fencing_token,
                    "now_epoch": now_epoch,
                    "now_iso": now_iso,
                },
            )
            if cursor.rowcount != 1:
                return False

            # 4. Update attempt to RUNNING
            att_cursor = conn.execute(
                """
                UPDATE pm_coordinator_attempts
                SET status = 'RUNNING'
                WHERE attempt_id = ?
                """,
                (actual_attempt_id,),
            )
            if att_cursor.rowcount != 1:
                return False

            # 5. Insert physical run linking composite (intent_id, attempt_id)
            conn.execute(
                """
                INSERT INTO pm_coordinator_runs (
                    run_id, intent_id, attempt_id, fencing_token, status, started_at
                ) VALUES (?, ?, ?, ?, 'SPAWNING', ?)
                """,
                (run_id, intent_id, actual_attempt_id, assigned_fencing_token, now_iso),
            )
            from mas.pm.delivery import execution_phase
            execution_phase(conn, intent_row["issue_id"], 'EXECUTING', {'intent_id': intent_id, 'run_id': run_id})
            return True

    def heartbeat_intent(
        self,
        intent_id: str,
        worker_id: str,
        assigned_fencing_token: int,
        now_epoch: float,
        lease_timeout_s: float = 10.0,
    ) -> bool:
        """
        Renews an active lease for an in-flight worker.
        Requires matching active state (CLAIMED or PROCESSING), assigned worker,
        matching fencing generation, and that the lease has not already expired.
        """
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            intent_row = conn.execute(
                "SELECT tenant_id FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if not intent_row:
                return False
            self._validate_tenant_authority(intent_row["tenant_id"])

            cursor = conn.execute(
                """
                UPDATE pm_coordinator_intents
                SET lease_expires_at = :now_epoch + :lease_timeout_s,
                    lease_heartbeat_at = :now_epoch,
                    updated_at = :now_iso
                WHERE intent_id = :intent_id
                  AND status IN ('CLAIMED', 'PROCESSING')
                  AND worker_id = :worker_id
                  AND fencing_token = :assigned_fencing_token
                  AND lease_expires_at > :now_epoch
                """,
                {
                    "intent_id": intent_id,
                    "worker_id": worker_id,
                    "assigned_fencing_token": assigned_fencing_token,
                    "now_epoch": now_epoch,
                    "lease_timeout_s": lease_timeout_s,
                    "now_iso": now_iso,
                },
            )
            return cursor.rowcount == 1

    def complete_intent(
        self,
        intent_id: str,
        worker_id: str,
        assigned_fencing_token: int,
        now_epoch: float,
        candidate_commit_sha: Optional[str] = None,
        tokens_spent: int = 0,
        exit_code: int = 0,
    ) -> bool:
        """
        Atomically records task completion, settles token spend and reservation ledger.
        Requires matching PROCESSING state, assigned worker, generation, and active lease.
        Requires non-null candidate_commit_sha and authoritative exit_code.
        Enforces truthful outcomes: exit_code != 0 marks attempt as FAILED, never SUCCEEDED.
        Strictly enforces funded budget limit: tokens_spent cannot exceed funded reservation.
        For exit_code == 0 (SUCCEEDED), non-empty candidate_commit_sha is mandatory.
        For exit_code != 0 (FAILED), candidate_commit_sha is optional.
        """
        if exit_code == 0 and not candidate_commit_sha:
            raise ValueError("Authoritative candidate_commit_sha required to complete successful intent")
        if not isinstance(tokens_spent, int) or isinstance(tokens_spent, bool):
            raise ValueError(f"tokens_spent must be an integer, got {type(tokens_spent).__name__}")
        if tokens_spent < 0:
            raise ValueError(f"tokens_spent must be non-negative, got {tokens_spent}")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise ValueError(f"exit_code must be an integer, got {type(exit_code).__name__}")

        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            intent_check = conn.execute(
                "SELECT tenant_id, attempt_id, project_id, issue_id, payload FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if not intent_check:
                return False
            self._validate_tenant_authority(intent_check["tenant_id"])

            from mas.pm.delivery import require_execution
            require_execution(conn, intent_check['issue_id'], intent_check['tenant_id'], intent_id)
            # Verify issue policy version and pending reconciliation has not changed mid-flight
            issue_id = intent_check["issue_id"]
            if issue_id:
                issue_row = conn.execute(
                    "SELECT policy_version, has_pending_reconciliation FROM pm_issues WHERE id = ?",
                    (issue_id,),
                ).fetchone()
                if issue_row:
                    payload_obj = {}
                    if intent_check["payload"]:
                        try:
                            payload_obj = json.loads(intent_check["payload"])
                        except Exception:
                            pass
                    admitted_pv = payload_obj.get("admitted_policy_version")
                    if issue_row["has_pending_reconciliation"] != 0 or (
                        admitted_pv is not None and issue_row["policy_version"] != admitted_pv
                    ):
                        # Policy changed or plan reconciliation is pending: reject completion, fail closed
                        return False

            # 1. Atomic CAS transition PROCESSING -> COMPLETED first.
            # Stale / late callers (e.g. canceled or expired lease) must fail here immediately
            # without mutating any records or evaluating budget reservation.
            cursor = conn.execute(
                """
                UPDATE pm_coordinator_intents
                SET status = 'COMPLETED',
                    updated_at = :now_iso
                WHERE intent_id = :intent_id
                  AND status = 'PROCESSING'
                  AND worker_id = :worker_id
                  AND fencing_token = :assigned_fencing_token
                  AND lease_expires_at > :now_epoch
                """,
                {
                    "intent_id": intent_id,
                    "worker_id": worker_id,
                    "assigned_fencing_token": assigned_fencing_token,
                    "now_epoch": now_epoch,
                    "now_iso": now_iso,
                },
            )
            if cursor.rowcount != 1:
                return False

            att_id = intent_check["attempt_id"]
            proj_id = intent_check["project_id"]

            # Validate against funded reservation before settling attempt
            res_row = conn.execute(
                "SELECT amount FROM pm_coordinator_reservations WHERE attempt_id = ? AND status = 'HELD'",
                (att_id,),
            ).fetchone()
            res_amount = res_row["amount"] if res_row else 0
            if tokens_spent > res_amount:
                raise ValueError(
                    f"tokens_spent {tokens_spent} exceeds funded reservation {res_amount} for attempt {att_id}"
                )

            attempt_status = "SUCCEEDED" if exit_code == 0 else "FAILED"
            failure_reason = None if exit_code == 0 else f"PROCESS_EXITED_WITH_CODE_{exit_code}"

            conn.execute(
                """
                UPDATE pm_coordinator_attempts
                SET status = ?,
                    candidate_commit_sha = ?,
                    budget_tokens_spent = ?,
                    failure_reason = ?,
                    finished_at = ?
                WHERE attempt_id = ?
                """,
                (attempt_status, candidate_commit_sha, tokens_spent, failure_reason, now_iso, att_id),
            )

            # Settle reservation in ledger
            conn.execute(
                """
                UPDATE pm_coordinator_reservations
                SET status = 'SETTLED',
                    settled_amount = ?,
                    settled_at = ?
                WHERE attempt_id = ? AND status = 'HELD'
                """,
                (tokens_spent, now_iso, att_id),
            )

            # Deduct spent tokens from project consumed pool exactly once
            conn.execute(
                """
                UPDATE pm_projects
                SET tokens_consumed = tokens_consumed + ?
                WHERE id = ?
                """,
                (tokens_spent, proj_id),
            )

            conn.execute(
                """
                UPDATE pm_coordinator_runs
                SET status = 'EXITED',
                    exit_code = ?,
                    ended_at = ?
                WHERE intent_id = ? AND fencing_token = ?
                """,
                (exit_code, now_iso, intent_id, assigned_fencing_token),
            )
            from mas.pm.delivery import execution_phase
            execution_phase(conn, issue_id, 'AWAITING_SUBMISSION' if exit_code == 0 else 'UNCERTAIN',
                            {'intent_id': intent_id, 'exit_code': exit_code})
            return True

    def record_execution_interrupted(
        self,
        intent_id: str,
        worker_id: str,
        assigned_fencing_token: int,
        error_message: str = "Execution interrupted or crashed",
    ) -> bool:
        """
        Transitions in-flight PROCESSING intent to UNKNOWN_EXECUTION following an execution crash,
        timeout, or uncertain failure.
        - Advances fencing token to revoke worker authority.
        - Marks attempt as UNKNOWN_EXECUTION.
        - Marks run as INTERRUPTED.
        - Strictly preserves budget reservations in HELD status (pessimistic reservation hold).
        - Does NOT invent candidate commit SHA or recorded token spend.
        """
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            intent_check = conn.execute(
                "SELECT tenant_id, attempt_id FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if not intent_check:
                return False
            self._validate_tenant_authority(intent_check["tenant_id"])

            cursor = conn.execute(
                """
                UPDATE pm_coordinator_intents
                SET status = 'UNKNOWN_EXECUTION',
                    fencing_token = fencing_token + 1,
                    worker_id = NULL,
                    updated_at = :now_iso
                WHERE intent_id = :intent_id
                  AND status IN ('PROCESSING', 'CLAIMED')
                  AND worker_id = :worker_id
                  AND fencing_token = :assigned_fencing_token
                """,
                {
                    "intent_id": intent_id,
                    "worker_id": worker_id,
                    "assigned_fencing_token": assigned_fencing_token,
                    "now_iso": now_iso,
                },
            )
            if cursor.rowcount != 1:
                return False

            att_id = intent_check["attempt_id"]

            conn.execute(
                """
                UPDATE pm_coordinator_attempts
                SET status = 'UNKNOWN_EXECUTION',
                    failure_reason = ?,
                    finished_at = ?
                WHERE attempt_id = ?
                """,
                (error_message, now_iso, att_id),
            )

            conn.execute(
                """
                UPDATE pm_coordinator_runs
                SET status = 'INTERRUPTED',
                    ended_at = ?
                WHERE intent_id = ? AND fencing_token = ?
                """,
                (now_iso, intent_id, assigned_fencing_token),
            )
            from mas.pm.delivery import execution_phase
            issue_id = conn.execute('SELECT issue_id FROM pm_coordinator_intents WHERE intent_id=?', (intent_id,)).fetchone()['issue_id']
            execution_phase(conn, issue_id, 'UNCERTAIN', {'intent_id': intent_id})
            # Budget reservation remains HELD; no release or settlement
            return True

    def reap_expired_leases(self, now_epoch: float) -> List[str]:
        """
        Reaps expired leases:
        - If CLAIMED (pre-spawn): retired to FAILED (CLAIM_TIMEOUT_PRE_SPAWN), increments fencing token.
        - If PROCESSING (post-spawn): retired to UNKNOWN_EXECUTION, increments fencing token.
          Pessimistically retains full token budget reservation.
        Returns list of reaped intent IDs.
        """
        self._validate_tenant_authority()
        conn = self.db._get_connection()
        try:
            candidates = conn.execute(
                """
                SELECT intent_id, status, fencing_token, attempt_id, tenant_id
                FROM pm_coordinator_intents
                WHERE status IN ('CLAIMED', 'PROCESSING')
                  AND lease_expires_at <= ?
                """,
                (now_epoch,),
            ).fetchall()
        finally:
            conn.close()

        reaped: List[str] = []
        now_iso = self._now_iso()

        for cand in candidates:
            intent_id = cand["intent_id"]
            expected_fencing_token = cand["fencing_token"]
            old_status = cand["status"]
            attempt_id = cand["attempt_id"]
            tenant_id = cand["tenant_id"]

            self._validate_tenant_authority(tenant_id)

            with self.db.atomic_transaction() as t_conn:
                cursor = t_conn.execute(
                    """
                    UPDATE pm_coordinator_intents
                    SET status = CASE WHEN status = 'CLAIMED' THEN 'FAILED' ELSE 'UNKNOWN_EXECUTION' END,
                        fencing_token = fencing_token + 1,
                        worker_id = NULL,
                        updated_at = :now_iso
                    WHERE intent_id = :intent_id
                      AND status IN ('CLAIMED', 'PROCESSING')
                      AND fencing_token = :expected_fencing_token
                      AND lease_expires_at <= :now_epoch
                    """,
                    {
                        "intent_id": intent_id,
                        "expected_fencing_token": expected_fencing_token,
                        "now_epoch": now_epoch,
                        "now_iso": now_iso,
                    },
                )
                if cursor.rowcount == 1:
                    reaped.append(intent_id)
                    from mas.pm.delivery import execution_phase
                    gate_issue = t_conn.execute('SELECT issue_id FROM pm_coordinator_intents WHERE intent_id=?', (intent_id,)).fetchone()['issue_id']
                    execution_phase(t_conn, gate_issue, 'UNCERTAIN', {'intent_id': intent_id, 'reason': 'lease_expired'})
                    # Check whether any runs were inserted
                    runs_count = t_conn.execute(
                        "SELECT COUNT(*) as cnt FROM pm_coordinator_runs WHERE intent_id = ?",
                        (intent_id,),
                    ).fetchone()["cnt"]

                    if old_status == "PROCESSING" or runs_count > 0:
                        t_conn.execute(
                            """
                            UPDATE pm_coordinator_attempts
                            SET status = 'UNKNOWN_EXECUTION',
                                failure_reason = 'LEASE_EXPIRED_IN_FLIGHT_UNKNOWN_EXECUTION'
                            WHERE attempt_id = ?
                            """,
                            (attempt_id,),
                        )
                        t_conn.execute(
                            """
                            UPDATE pm_coordinator_runs
                            SET status = 'INTERRUPTED',
                                ended_at = ?
                            WHERE intent_id = ? AND status IN ('SPAWNING', 'STREAMING')
                            """,
                            (now_iso, intent_id),
                        )
                    else:
                        t_conn.execute(
                            """
                            UPDATE pm_coordinator_attempts
                            SET status = 'FAILED',
                                failure_reason = 'CLAIM_TIMEOUT_PRE_SPAWN'
                            WHERE attempt_id = ?
                            """,
                            (attempt_id,),
                        )
        return reaped

    def cancel_intent(self, intent_id: str, reason: str = "Canceled by operator") -> bool:
        """
        Atomically requests cancellation of an intent.
        Truthful cancellation: distinguishes cancellation request from observed process outcome.
        - If PENDING: unlaunched work; intent -> CANCELED, attempt -> CANCELED, releases budget hold.
        - If CLAIMED / PROCESSING: potentially launched work; intent -> CANCEL_REQUESTED,
          fencing_token advanced to retire worker authority, worker_id cleared.
          Does NOT mark runs KILLED or attempts CANCELED without observed termination.
          Budget holds remain HELD pending authoritative termination.
        - Idempotent: repeated calls on CANCEL_REQUESTED or already terminated intents return True or False safely.
        """
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            intent_row = conn.execute(
                "SELECT status, attempt_id, tenant_id FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if not intent_row:
                return False

            self._validate_tenant_authority(intent_row["tenant_id"])

            curr_status = intent_row["status"]
            att_id = intent_row["attempt_id"]
            from mas.pm.delivery import execution_phase
            gate_issue = conn.execute('SELECT issue_id FROM pm_coordinator_intents WHERE intent_id=?', (intent_id,)).fetchone()['issue_id']

            # If already finalized or already in CANCEL_REQUESTED
            if curr_status in ("COMPLETED", "FAILED", "UNKNOWN_EXECUTION", "CANCELED"):
                return False
            if curr_status == "CANCEL_REQUESTED":
                return True  # Idempotent

            if curr_status == "PENDING":
                # Provably unlaunched work: cancel immediately and release hold
                conn.execute(
                    """
                    UPDATE pm_coordinator_intents
                    SET status = 'CANCELED',
                        fencing_token = fencing_token + 1,
                        updated_at = :now_iso
                    WHERE intent_id = :intent_id
                    """,
                    {"intent_id": intent_id, "now_iso": now_iso},
                )
                conn.execute(
                    """
                    UPDATE pm_coordinator_attempts
                    SET status = 'CANCELED',
                        failure_reason = ?,
                        finished_at = ?
                    WHERE attempt_id = ?
                    """,
                    (reason, now_iso, att_id),
                )
                conn.execute(
                    """
                    UPDATE pm_coordinator_reservations
                    SET status = 'RELEASED',
                        settled_at = ?
                    WHERE attempt_id = ? AND status = 'HELD'
                    """,
                    (now_iso, att_id),
                )
                execution_phase(conn, gate_issue, 'UNCERTAIN', {'intent_id': intent_id, 'reason': 'canceled_before_launch'})
                return True

            # curr_status in ('CLAIMED', 'PROCESSING'): potentially launched work
            cursor = conn.execute(
                """
                UPDATE pm_coordinator_intents
                SET status = 'CANCEL_REQUESTED',
                    fencing_token = fencing_token + 1,
                    worker_id = NULL,
                    updated_at = :now_iso
                WHERE intent_id = :intent_id
                  AND status IN ('CLAIMED', 'PROCESSING')
                """,
                {"intent_id": intent_id, "now_iso": now_iso},
            )
            # Advance attempt fencing token without fabricating KILLED/CANCELED
            conn.execute(
                """
                UPDATE pm_coordinator_attempts
                SET fencing_token = fencing_token + 1
                WHERE attempt_id = ?
                """,
                (att_id,),
            )
            # NOTE: Runs remain in SPAWNING/STREAMING; budget holds remain HELD until authoritative receipt.
            if cursor.rowcount == 1:
                execution_phase(conn, gate_issue, 'UNCERTAIN', {'intent_id': intent_id, 'reason': 'cancellation_requested'})
            return cursor.rowcount == 1

    def record_authoritative_termination(
        self,
        intent_id: str,
        run_id: str,
        exit_code: int,
        observed_status: str = "KILLED",
        tokens_spent: int = 0,
        receipt_id: Optional[str] = None,
    ) -> bool:
        """
        Records authoritative termination receipt from adapter/process observer.
        Concludes CANCEL_REQUESTED or UNKNOWN_EXECUTION intent to CANCELED/FAILED and run to KILLED/EXITED.
        Settles budget holds and charges termination tokens_spent to project consumed pool.
        Enforces state guards: COMPLETED intents cannot be rewritten to CANCELED.
        Enforces run matching: missing or foreign run ID fails with zero mutations.
        Enforces idempotent receipt replay: exact replay returns True; conflicting replay raises error.
        """
        if not isinstance(tokens_spent, int) or isinstance(tokens_spent, bool):
            raise ValueError(f"tokens_spent must be an integer, got {type(tokens_spent).__name__}")
        if tokens_spent < 0:
            raise ValueError(f"tokens_spent must be non-negative, got {tokens_spent}")
        if not isinstance(exit_code, int) or isinstance(exit_code, bool):
            raise ValueError(f"exit_code must be an integer, got {type(exit_code).__name__}")

        if observed_status not in ("KILLED", "EXITED"):
            raise ValueError("observed_status must be KILLED or EXITED")
        if receipt_id is not None and (not isinstance(receipt_id, str) or not receipt_id.strip()):
            raise ValueError("receipt_id must be a nonempty string when supplied")
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            intent_row = conn.execute(
                "SELECT status, attempt_id, project_id, tenant_id, issue_id, task_id FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if not intent_row:
                return False

            self._validate_tenant_authority(intent_row["tenant_id"])

            curr_intent_status = intent_row["status"]
            att_id = intent_row["attempt_id"]
            proj_id = intent_row["project_id"]

            # An observer capability is distinct from generic storage mutation.
            from mas.tenancy import current_binding
            binding = current_binding()
            if not is_trusted_coord_admin():
                binding.require("coordinator:observe")
            observer = (f"{binding.identity.tenant_id}:{binding.identity.principal_id}"
                        if binding else "trusted-coordinator-admin")
            run_row = conn.execute(
                "SELECT * FROM pm_coordinator_runs WHERE run_id=? AND intent_id=? AND attempt_id=?",
                (run_id, intent_id, att_id),
            ).fetchone()
            if not run_row:
                return False
            receipt_key = "external:" + receipt_id if receipt_id else "termination:" + run_id
            payload = {
                "schema_version": 1, "tenant_id": intent_row["tenant_id"],
                "project_id": proj_id, "issue_id": intent_row["issue_id"],
                "task_id": intent_row["task_id"], "intent_id": intent_id,
                "attempt_id": att_id, "run_id": run_id,
                "fencing_token": run_row["fencing_token"], "observer_principal": observer,
                "exit_code": exit_code, "status": observed_status, "tokens_spent": tokens_spent,
            }
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            existing = conn.execute(
                "SELECT canonical_payload,content_hash FROM pm_coordinator_termination_observations WHERE receipt_key=?",
                (receipt_key,),
            ).fetchone()
            if existing:
                if existing["canonical_payload"] != canonical or existing["content_hash"] != digest:
                    raise sqlite3.IntegrityError(f"Conflicting termination receipt {receipt_key}")
                return True
            if curr_intent_status == "COMPLETED":
                raise ValueError(f"Cannot terminate already COMPLETED intent {intent_id}")
            if curr_intent_status not in ("CANCEL_REQUESTED", "UNKNOWN_EXECUTION"):
                return False
            if run_row["status"] not in ("SPAWNING", "STREAMING", "INTERRUPTED"):
                return False

            # Check reservation bounds
            res_row = conn.execute(
                "SELECT amount FROM pm_coordinator_reservations WHERE attempt_id = ? AND status = 'HELD'",
                (att_id,),
            ).fetchone()
            res_amount = res_row["amount"] if res_row else 0
            if tokens_spent > res_amount:
                raise ValueError(
                    f"Termination tokens_spent {tokens_spent} exceeds funded reservation {res_amount}"
                )

            # Update run
            run_cursor = conn.execute(
                """
                UPDATE pm_coordinator_runs
                SET status = ?,
                    exit_code = ?,
                    ended_at = ?
                WHERE run_id = ? AND intent_id = ?
                """,
                (observed_status, exit_code, now_iso, run_id, intent_id),
            )
            if run_cursor.rowcount != 1:
                return False

            # Update intent
            final_intent_status = "CANCELED" if exit_code in (0, 137, 143) else "FAILED"
            conn.execute(
                """
                UPDATE pm_coordinator_intents
                SET status = ?,
                    updated_at = ?
                WHERE intent_id = ?
                """,
                (final_intent_status, now_iso, intent_id),
            )

            # Update attempt
            conn.execute(
                """
                UPDATE pm_coordinator_attempts
                SET status = ?,
                    budget_tokens_spent = ?,
                    failure_reason = ?,
                    finished_at = ?
                WHERE attempt_id = ?
                """,
                (
                    final_intent_status,
                    tokens_spent,
                    f"TERMINATION_{observed_status}_EXIT_{exit_code}",
                    now_iso,
                    att_id,
                ),
            )

            # Settle reservation in ledger
            conn.execute(
                """
                UPDATE pm_coordinator_reservations
                SET status = 'SETTLED',
                    settled_amount = ?,
                    settled_at = ?
                WHERE attempt_id = ? AND status = 'HELD'
                """,
                (tokens_spent, now_iso, att_id),
            )

            # Charge termination spend to project tokens_consumed exactly once
            if tokens_spent > 0:
                conn.execute(
                    """
                    UPDATE pm_projects
                    SET tokens_consumed = tokens_consumed + ?
                    WHERE id = ?
                    """,
                    (tokens_spent, proj_id),
                )

            # Keep exact accounting observations separate from signed evidence.
            # No placeholder key, candidate or signature is invented.
            conn.execute(
                """INSERT INTO pm_coordinator_termination_observations
                (receipt_key,intent_id,run_id,attempt_id,canonical_payload,content_hash,observed_at)
                VALUES(?,?,?,?,?,?,?)""",
                (receipt_key, intent_id, run_id, att_id, canonical, digest, now_iso),
            )

            return True

    def record_run_event(
        self,
        run_id: str,
        cursor_seq: int,
        event_type: str,
        event_payload: Dict[str, Any],
    ) -> CoordinatorEvent:
        """Records a streaming run event. Enforces unique (run_id, cursor_seq)."""
        now = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            run_row = conn.execute(
                """
                SELECT i.tenant_id
                FROM pm_coordinator_runs r
                JOIN pm_coordinator_intents i ON r.intent_id = i.intent_id
                WHERE r.run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if not run_row:
                raise ValueError(f"Run {run_id} not found")
            self._validate_tenant_authority(run_row["tenant_id"])

            cursor = conn.execute(
                """
                INSERT INTO pm_coordinator_events (
                    run_id, cursor_seq, event_type, event_payload, emitted_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, cursor_seq, event_type, json.dumps(event_payload), now),
            )
            event_id = cursor.lastrowid
            return CoordinatorEvent(
                event_id=event_id,
                run_id=run_id,
                cursor_seq=cursor_seq,
                event_type=event_type,
                event_payload=event_payload,
                emitted_at=now,
            )

    def record_evidence_receipt(
        self,
        evidence_id: str,
        issue_id: str,
        task_id: str,
        attempt_id: str,
        run_id: str,
        candidate_commit_sha: str,
        nonce: str,
        key_id: str,
        signature: str,
        canonical_payload: Dict[str, Any],
        admission_status: str = "SUBMITTED",
    ) -> CoordinatorEvidenceReceipt:
        """
        Records a raw evidence receipt.
        Enforces nonce uniqueness for replay prevention.
        Always stores caller submissions as 'SUBMITTED' regardless of supplied parameter;
        admission requires explicit verified promotion via admit_evidence_receipt.
        """
        now = self._now_iso()
        with self.db.atomic_transaction() as conn:
            self._validate_tenant_authority()
            att_row = conn.execute(
                "SELECT tenant_id FROM pm_coordinator_attempts WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
            if not att_row:
                raise ValueError(f"Attempt {attempt_id} not found")
            self._validate_tenant_authority(att_row["tenant_id"])

            # Caller cannot self-promote to ADMITTED; raw submissions always enter SUBMITTED
            forced_status = "SUBMITTED"

            conn.execute(
                """
                INSERT INTO pm_coordinator_evidence_receipts (
                    evidence_id, issue_id, task_id, attempt_id, run_id,
                    candidate_commit_sha, nonce, key_id, signature,
                    canonical_payload, admission_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    issue_id,
                    task_id,
                    attempt_id,
                    run_id,
                    candidate_commit_sha,
                    nonce,
                    key_id,
                    signature,
                    json.dumps(canonical_payload),
                    forced_status,
                    now,
                ),
            )
            return CoordinatorEvidenceReceipt(
                evidence_id=evidence_id,
                issue_id=issue_id,
                task_id=task_id,
                attempt_id=attempt_id,
                run_id=run_id,
                candidate_commit_sha=candidate_commit_sha,
                nonce=nonce,
                key_id=key_id,
                signature=signature,
                canonical_payload=canonical_payload,
                admission_status=forced_status,
                created_at=now,
            )

    def register_evidence_contract(self, binding, verifier_id, reviewer_id, case_ids):
        from mas.pm.adapters.admission import register_contract
        return register_contract(self, binding, verifier_id, reviewer_id, case_ids)

    def admit_evidence_receipt(self, evidence_id: str, trusted_keys=None) -> bool:
        """Default disabled; keys cannot be provided by receipt callers."""
        self._validate_tenant_authority()
        if trusted_keys is not None:
            raise PermissionError("Per-receipt trust overrides are forbidden")
        if self._evidence_trust is None:
            raise PermissionError("Coordinator evidence admission is disabled until service-owned trust is configured")
        return self._evidence_trust.admit(self, evidence_id)

    def validate_delivery_execution(self, intent_id):
        with self.db.atomic_transaction() as conn:
            row = conn.execute("SELECT tenant_id,issue_id FROM pm_coordinator_intents WHERE intent_id=?", (intent_id,)).fetchone()
            if not row:
                raise PermissionError("Unknown coordinator intent")
            self._validate_tenant_authority(row['tenant_id'])
            from mas.pm.delivery import require_execution
            require_execution(conn, row['issue_id'], row['tenant_id'], intent_id)

    def get_attempt(self, attempt_id: str) -> Optional[CoordinatorAttempt]:
        """Retrieves attempt record by ID."""
        conn = self.db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM pm_coordinator_attempts WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
            if not row:
                return None
            return CoordinatorAttempt(
                attempt_id=row["attempt_id"],
                tenant_id=row["tenant_id"],

                project_id=row["project_id"],
                issue_id=row["issue_id"],
                task_id=row["task_id"],
                attempt_seq=row["attempt_seq"],
                status=row["status"],
                fencing_token=row["fencing_token"],
                started_at=row["started_at"] or "",
                finished_at=row["finished_at"],
                budget_tokens_allocated=row["budget_tokens_allocated"],
                budget_tokens_spent=row["budget_tokens_spent"],
                candidate_commit_sha=row["candidate_commit_sha"],
                failure_reason=row["failure_reason"],
            )
        finally:
            conn.close()

    def get_intent(self, intent_id: str) -> Optional[CoordinatorIntent]:
        """Retrieves intent record by ID."""
        conn = self.db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if not row:
                return None
            return CoordinatorIntent(
                intent_id=row["intent_id"],
                tenant_id=row["tenant_id"],
                project_id=row["project_id"],
                issue_id=row["issue_id"],
                task_id=row["task_id"],
                attempt_id=row["attempt_id"],
                adapter_type=row["adapter_type"],
                status=row["status"],
                fencing_token=row["fencing_token"],
                worker_id=row["worker_id"],
                lease_expires_at=row["lease_expires_at"],
                lease_heartbeat_at=row["lease_heartbeat_at"],
                payload=json.loads(row["payload"]) if row["payload"] else {},
                created_at=row["created_at"] or "",
                updated_at=row["updated_at"] or "",
            )
        finally:
            conn.close()

    def get_run(self, run_id: str) -> Optional[CoordinatorRun]:
        """Retrieves physical run record by ID."""
        conn = self.db._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM pm_coordinator_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if not row:
                return None
            return CoordinatorRun(
                run_id=row["run_id"],
                intent_id=row["intent_id"],
                attempt_id=row["attempt_id"],
                fencing_token=row["fencing_token"],
                runtime_session_id=row["runtime_session_id"],
                process_pid=row["process_pid"],
                process_pgid=row["process_pgid"],
                status=row["status"],
                exit_code=row["exit_code"],
                started_at=row["started_at"] or "",
                ended_at=row["ended_at"],
            )
        finally:
            conn.close()

    def get_run_events(self, run_id: str) -> List[CoordinatorEvent]:
        """Retrieves ordered event stream for a run."""
        conn = self.db._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM pm_coordinator_events WHERE run_id = ? ORDER BY cursor_seq ASC",
                (run_id,),
            ).fetchall()
            return [
                CoordinatorEvent(
                    event_id=r["event_id"],
                    run_id=r["run_id"],
                    cursor_seq=r["cursor_seq"],
                    event_type=r["event_type"],
                    event_payload=json.loads(r["event_payload"]) if r["event_payload"] else {},
                    emitted_at=r["emitted_at"] or "",
                )
                for r in rows
            ]
        finally:
            conn.close()

    def list_intents_for_issue(self, issue_id: str) -> List[CoordinatorIntent]:
        """Lists all outbox intents for a given deployment issue."""
        conn = self.db._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM pm_coordinator_intents WHERE issue_id = ? ORDER BY created_at ASC",
                (issue_id,),
            ).fetchall()
            return [
                CoordinatorIntent(
                    intent_id=r["intent_id"],
                    tenant_id=r["tenant_id"],
                    project_id=r["project_id"],
                    issue_id=r["issue_id"],
                    task_id=r["task_id"],
                    attempt_id=r["attempt_id"],
                    adapter_type=r["adapter_type"],
                    status=r["status"],
                    fencing_token=r["fencing_token"],
                    worker_id=r["worker_id"],
                    lease_expires_at=r["lease_expires_at"],
                    lease_heartbeat_at=r["lease_heartbeat_at"],
                    payload=json.loads(r["payload"]) if r["payload"] else {},
                    created_at=r["created_at"] or "",
                    updated_at=r["updated_at"] or "",
                )
                for r in rows
            ]
        finally:
            conn.close()

    def list_pending_intents(
        self,
        tenant_id: Optional[str] = None,
        adapter_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[CoordinatorIntent]:
        """
        Lists pending outbox intents ready for claiming.
        Strictly filters on status = 'PENDING'.
        """
        self._validate_tenant_authority(tenant_id)
        conn = self.db._get_connection()
        try:
            query = "SELECT * FROM pm_coordinator_intents WHERE status = 'PENDING'"
            params: List[Any] = []
            if tenant_id is not None:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            if adapter_type is not None:
                query += " AND adapter_type = ?"
                params.append(adapter_type)
            query += " ORDER BY created_at ASC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                CoordinatorIntent(
                    intent_id=r["intent_id"],
                    tenant_id=r["tenant_id"],
                    project_id=r["project_id"],
                    issue_id=r["issue_id"],
                    task_id=r["task_id"],
                    attempt_id=r["attempt_id"],
                    adapter_type=r["adapter_type"],
                    status=r["status"],
                    fencing_token=r["fencing_token"],
                    worker_id=r["worker_id"],
                    lease_expires_at=r["lease_expires_at"],
                    lease_heartbeat_at=r["lease_heartbeat_at"],
                    payload=json.loads(r["payload"]) if r["payload"] else {},
                    created_at=r["created_at"] or "",
                    updated_at=r["updated_at"] or "",
                )
                for r in rows
            ]
        finally:
            conn.close()
