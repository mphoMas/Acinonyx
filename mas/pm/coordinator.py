"""
mas.pm.coordinator: Coordinator state, outbox, and lease management for Capable Coordinator (CC-03).
Enforces atomic CAS claims, monotonic fencing tokens, guarded pre-spawn persistence,
expired lease reaping, pessimistic budget holds for UNKNOWN_EXECUTION, and relational ownership integrity.
"""

from __future__ import annotations

import json
import sqlite3
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


class CoordinatorStore:
    """Persistence and atomic lifecycle manager for the Capable Coordinator."""

    def __init__(self, db: PMDatabase) -> None:
        self.db = db

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

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
        manage_conn = conn is None
        c = self.db._get_connection() if manage_conn else conn
        now = self._now_iso()
        try:
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
        manage_conn = conn is None
        c = self.db._get_connection() if manage_conn else conn
        now = self._now_iso()
        try:
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
    ) -> Tuple[CoordinatorAttempt, CoordinatorIntent]:
        """Atomically creates both attempt and intent in one transaction with budget reservation."""
        with self.db.atomic_transaction() as conn:
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
        conn = self.db._get_connection()
        try:
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
        finally:
            conn.close()

    def pre_spawn_intent(
        self,
        intent_id: str,
        worker_id: str,
        assigned_fencing_token: int,
        now_epoch: float,
        run_id: str,
        attempt_id: Optional[str] = None,
    ) -> bool:
        """
        Atomically transitions CLAIMED intent to PROCESSING before launching process.
        Requires active unexpired lease, assigned worker, and matching fencing token.
        In the same transaction, updates attempt to RUNNING and records SPAWNING physical run.
        """
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
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

            # Retrieve attempt_id if not supplied
            att_id = attempt_id
            if not att_id:
                row = conn.execute(
                    "SELECT attempt_id FROM pm_coordinator_intents WHERE intent_id = ?",
                    (intent_id,),
                ).fetchone()
                if not row:
                    return False
                att_id = row["attempt_id"]

            conn.execute(
                """
                UPDATE pm_coordinator_attempts
                SET status = 'RUNNING'
                WHERE attempt_id = ?
                """,
                (att_id,),
            )

            conn.execute(
                """
                INSERT INTO pm_coordinator_runs (
                    run_id, intent_id, attempt_id, fencing_token, status, started_at
                ) VALUES (?, ?, ?, ?, 'SPAWNING', ?)
                """,
                (run_id, intent_id, att_id, assigned_fencing_token, now_iso),
            )
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
        conn = self.db._get_connection()
        try:
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
        finally:
            conn.close()

    def complete_intent(
        self,
        intent_id: str,
        worker_id: str,
        assigned_fencing_token: int,
        now_epoch: float,
        candidate_commit_sha: Optional[str] = None,
        tokens_spent: int = 0,
    ) -> bool:
        """
        Atomically records task completion and settles token spend.
        Requires matching PROCESSING state, assigned worker, generation, and active lease.
        """
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
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

            row = conn.execute(
                "SELECT attempt_id FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if row:
                att_id = row["attempt_id"]
                conn.execute(
                    """
                    UPDATE pm_coordinator_attempts
                    SET status = 'SUCCEEDED',
                        candidate_commit_sha = ?,
                        budget_tokens_spent = ?,
                        finished_at = ?
                    WHERE attempt_id = ?
                    """,
                    (candidate_commit_sha, tokens_spent, now_iso, att_id),
                )

            conn.execute(
                """
                UPDATE pm_coordinator_runs
                SET status = 'EXITED',
                    ended_at = ?
                WHERE intent_id = ? AND fencing_token = ?
                """,
                (now_iso, intent_id, assigned_fencing_token),
            )
            return True

    def reap_expired_leases(self, now_epoch: float) -> List[str]:
        """
        Reaps expired leases:
        - If CLAIMED (pre-spawn): retired to FAILED (CLAIM_TIMEOUT_PRE_SPAWN), increments fencing token.
        - If PROCESSING (post-spawn): retired to UNKNOWN_EXECUTION, increments fencing token.
          Pessimistically retains full token budget reservation.
        Returns list of reaped intent IDs.
        """
        conn = self.db._get_connection()
        try:
            candidates = conn.execute(
                """
                SELECT intent_id, status, fencing_token, attempt_id
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
        Atomically cancels an active intent.
        Retires generation token and updates attempt to CANCELED.
        """
        now_iso = self._now_iso()
        with self.db.atomic_transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE pm_coordinator_intents
                SET status = 'CANCEL_REQUESTED',
                    fencing_token = fencing_token + 1,
                    worker_id = NULL,
                    updated_at = :now_iso
                WHERE intent_id = :intent_id
                  AND status NOT IN ('COMPLETED', 'FAILED', 'UNKNOWN_EXECUTION', 'CANCELED')
                """,
                {"intent_id": intent_id, "now_iso": now_iso},
            )
            if cursor.rowcount != 1:
                return False

            row = conn.execute(
                "SELECT attempt_id FROM pm_coordinator_intents WHERE intent_id = ?",
                (intent_id,),
            ).fetchone()
            if row:
                att_id = row["attempt_id"]
                conn.execute(
                    """
                    UPDATE pm_coordinator_attempts
                    SET status = 'CANCELED',
                        failure_reason = ?
                    WHERE attempt_id = ?
                    """,
                    (reason, att_id),
                )

            conn.execute(
                """
                UPDATE pm_coordinator_runs
                SET status = 'KILLED',
                    ended_at = ?
                WHERE intent_id = ? AND status IN ('SPAWNING', 'STREAMING')
                """,
                (now_iso, intent_id),
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
        conn = self.db._get_connection()
        try:
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
        finally:
            conn.close()

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
    ) -> CoordinatorEvidenceReceipt:
        """Records an admitted evidence receipt. Enforces nonce uniqueness for replay prevention."""
        now = self._now_iso()
        conn = self.db._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO pm_coordinator_evidence_receipts (
                    evidence_id, issue_id, task_id, attempt_id, run_id,
                    candidate_commit_sha, nonce, key_id, signature,
                    canonical_payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                created_at=now,
            )
        finally:
            conn.close()

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
