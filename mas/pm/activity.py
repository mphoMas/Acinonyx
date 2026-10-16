"""Runtime activity ingestion, spooling, and board projection service (SBA-04 P4).

Implements mas-runtime-activity-v1:
- POST /api/pm/v1/projects/{project_id}/events
- GET  /api/pm/v1/tasks/{issue_id}/activity?after={cursor}&limit=100
- GET  /api/pm/v1/projects/{id}/changes?after={cursor}&limit=100
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any

from mas.pm.adapters.antigravity import sanitize_payload
from mas.pm.adapters.broker import migrate_live_loop
from mas.pm.adapters.verifier import BINDING_FIELDS, SCHEMA, verify_signature
from mas.swarm.contracts import canonical, digest, strict_json

MAX_EVENT_REQUEST_BYTES = 65536  # 64 KiB
MAX_EVENT_MESSAGE_BYTES = 8192   # 8 KiB
MAX_SPOOL_CAPACITY = 256

GUEST_EVENT_KINDS = frozenset({
    "work.started",
    "work.progress",
    "work.blocked",
    "work.resumed",
    "comment.added",
    "note.added",
    "evidence.submitted",
    "candidate.submitted",
})

SERVICE_EVENT_KINDS = frozenset({
    "session.bound",
    "provider.requested",
    "provider.usage_confirmed",
    "candidate.exported",
    "verification.recorded",
    "review.recorded",
    "integration.confirmed",
    "execution.uncertain",
    "escalation.created",
})

ATTEMPT_STATE_PROJECTION = {
    "PENDING": "QUEUED",
    "RUNNING": "RUNNING",
    "SUCCEEDED": "SUCCEEDED",
    "FAILED": "FAILED",
    "UNKNOWN_EXECUTION": "UNKNOWN_EXECUTION",
    "CANCEL_REQUESTED": "CANCEL_REQUESTED",
    "CANCELED": "CANCELLED",
}


class ActivityError(RuntimeError):
    """Structured error with HTTP status code and machine-readable code."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class ActivitySpool:
    """Bounded credential-free spool for unacknowledged runtime events with progress coalescing."""

    def __init__(self, capacity: int = MAX_SPOOL_CAPACITY) -> None:
        if type(capacity) is not int or not 1 <= capacity <= 4096:
            raise ValueError("Invalid spool capacity")
        self.capacity = capacity
        self._pending_progress: dict[str, dict[str, Any]] = {}
        self._queue: list[dict[str, Any]] = []
        self._next_seq: dict[str, int] = {}
        self.exhausted_blocker: str | None = None

    def stage_progress(self, attempt_id: str, summary: str, occurred_at: str) -> None:
        """Coalesces transient work.progress observations before durable sequence assignment."""
        self._pending_progress[attempt_id] = {
            "attempt_id": attempt_id,
            "kind": "work.progress",
            "summary": sanitize_payload(summary)[:MAX_EVENT_MESSAGE_BYTES],
            "occurred_at": occurred_at,
        }

    def enqueue(
        self,
        *,
        event_id: str,
        task_id: str,
        attempt_id: str,
        kind: str,
        summary: str,
        occurred_at: str,
        expected_task_version: int = 1,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Flushes any coalesced progress and enqueues a durable sequenced event."""
        if attempt_id in self._pending_progress and kind != "work.progress":
            prog = self._pending_progress.pop(attempt_id)
            self._append_sequenced(
                event_id=f"ev-prog-{secrets.token_hex(8)}",
                task_id=task_id,
                attempt_id=attempt_id,
                kind="work.progress",
                summary=prog["summary"],
                occurred_at=prog["occurred_at"],
                expected_task_version=expected_task_version,
                extra_payload={},
            )
        elif kind == "work.progress":
            self._pending_progress.pop(attempt_id, None)

        return self._append_sequenced(
            event_id=event_id,
            task_id=task_id,
            attempt_id=attempt_id,
            kind=kind,
            summary=summary,
            occurred_at=occurred_at,
            expected_task_version=expected_task_version,
            extra_payload=extra_payload or {},
        )

    def _append_sequenced(
        self,
        *,
        event_id: str,
        task_id: str,
        attempt_id: str,
        kind: str,
        summary: str,
        occurred_at: str,
        expected_task_version: int,
        extra_payload: dict[str, Any],
    ) -> dict[str, Any]:
        if len(self._queue) >= self.capacity:
            self.exhausted_blocker = "Activity spool capacity exhausted; output admission paused"
            raise ActivityError(503, "spool_exhausted", self.exhausted_blocker)
        seq = self._next_seq.get(attempt_id, 0) + 1
        self._next_seq[attempt_id] = seq
        payload = {"summary": sanitize_payload(summary)[:MAX_EVENT_MESSAGE_BYTES]}
        for k, v in extra_payload.items():
            if k not in {"summary", "secret", "token", "password", "api_key"}:
                payload[k] = v
        envelope = {
            "schema_version": 1,
            "event_id": event_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "sequence": seq,
            "kind": kind,
            "occurred_at": occurred_at,
            "expected_task_version": expected_task_version,
            "payload": payload,
        }
        self._queue.append(envelope)
        return envelope

    def flush(self, service: ActivityBridgeService, *, tenant_id: str, project_id: str, actor: str) -> list[dict[str, Any]]:
        """Replays queued events in order and removes acknowledged entries."""
        receipts: list[dict[str, Any]] = []
        while self._queue:
            ev = self._queue[0]
            rcpt = service.ingest_event(
                tenant_id=tenant_id,
                project_id_or_key=project_id,
                actor=actor,
                authority_class="GUEST",
                raw_event=ev,
            )
            receipts.append(rcpt)
            self._queue.pop(0)
        self.exhausted_blocker = None
        return receipts


class ActivityBridgeService:
    """Backend service for mas-runtime-activity-v1 ingestion and board/task read projection."""

    def __init__(self, db: Any, *, evidence_trust: Any = None, min_retained_change_seq: int = 1) -> None:
        migrate_live_loop(db)
        self.db = db
        self.evidence_trust = evidence_trust
        self.min_retained_change_seq = min_retained_change_seq

    def _resolve_project(self, conn: sqlite3.Connection, project_id_or_key: str) -> sqlite3.Row:
        row = conn.execute(
            "SELECT * FROM pm_projects WHERE id = ? OR UPPER(key) = UPPER(?)",
            (project_id_or_key, project_id_or_key),
        ).fetchone()
        if not row:
            raise ActivityError(404, "not_found", f"Project '{project_id_or_key}' not found")
        return row

    def _resolve_issue_and_task(
        self,
        conn: sqlite3.Connection,
        issue_or_task_id: str,
        project_id: str | None = None,
    ) -> tuple[sqlite3.Row, str]:
        if project_id:
            issue = conn.execute(
                """
                SELECT q.*, m.task_id AS mapped_task_id
                FROM pm_issues q
                LEFT JOIN pm_task_mappings m ON m.project_id = q.project_id AND m.local_issue_id = q.id
                WHERE q.project_id = ? AND (q.id = ? OR UPPER(q.key) = UPPER(?) OR q.task_id = ? OR m.task_id = ?)
                """,
                (project_id, issue_or_task_id, issue_or_task_id, issue_or_task_id, issue_or_task_id),
            ).fetchone()
        else:
            issue = conn.execute(
                """
                SELECT q.*, m.task_id AS mapped_task_id
                FROM pm_issues q
                LEFT JOIN pm_task_mappings m ON m.project_id = q.project_id AND m.local_issue_id = q.id
                WHERE q.id = ? OR UPPER(q.key) = UPPER(?) OR q.task_id = ? OR m.task_id = ?
                """,
                (issue_or_task_id, issue_or_task_id, issue_or_task_id, issue_or_task_id),
            ).fetchone()
        if not issue:
            raise ActivityError(404, "not_found", f"Task or issue '{issue_or_task_id}' not found")
        stable_task_id = issue["mapped_task_id"] or issue["task_id"] or issue["id"]
        return issue, str(stable_task_id)

    def ingest_event(
        self,
        *,
        tenant_id: str,
        project_id_or_key: str,
        actor: str,
        authority_class: str = "GUEST",
        raw_event: dict[str, Any] | str | bytes,
        expected_fencing_token: int | None = None,
    ) -> dict[str, Any]:
        """Validates and persists a runtime or service activity event with sequence deduplication."""
        if authority_class not in {"GUEST", "SERVICE"}:
            raise ActivityError(403, "forbidden", "Invalid authority class")
        if not actor or not isinstance(actor, str):
            raise ActivityError(401, "unauthorized", "Authenticated actor required")

        if isinstance(raw_event, (str, bytes)):
            encoded = raw_event.encode("utf-8") if isinstance(raw_event, str) else raw_event
            if len(encoded) > MAX_EVENT_REQUEST_BYTES:
                raise ActivityError(413, "payload_too_large", "Event request exceeds 64 KiB limit")
            try:
                event = strict_json(encoded)
            except Exception as exc:
                raise ActivityError(400, "malformed", f"Invalid JSON event: {exc}") from exc
        elif isinstance(raw_event, dict):
            serialized = canonical(raw_event).encode("utf-8")
            if len(serialized) > MAX_EVENT_REQUEST_BYTES:
                raise ActivityError(413, "payload_too_large", "Event request exceeds 64 KiB limit")
            event = strict_json(serialized)
        else:
            raise ActivityError(400, "malformed", "Event body must be a JSON object")

        required_keys = {
            "schema_version",
            "event_id",
            "task_id",
            "attempt_id",
            "sequence",
            "kind",
            "occurred_at",
            "expected_task_version",
            "payload",
        }
        if not isinstance(event, dict) or set(event.keys()) != required_keys:
            raise ActivityError(400, "invalid_schema", "Event must contain exact mas-runtime-activity-v1 fields")

        if type(event["schema_version"]) is not int or event["schema_version"] != 1:
            raise ActivityError(400, "invalid_schema", "schema_version must be integer 1")

        event_id = event["event_id"]
        task_id_in = event["task_id"]
        attempt_id = event["attempt_id"]
        seq = event["sequence"]
        kind = event["kind"]
        occurred_at = event["occurred_at"]
        expected_ver = event["expected_task_version"]
        payload = event["payload"]

        if (
            not isinstance(event_id, str) or not event_id.strip() or len(event_id) > 128
            or not isinstance(task_id_in, str) or not task_id_in.strip()
            or not isinstance(attempt_id, str) or not attempt_id.strip()
            or not isinstance(occurred_at, str) or not occurred_at.strip()
            or type(seq) is not int or seq <= 0
            or type(expected_ver) is not int or expected_ver <= 0
            or not isinstance(payload, dict)
        ):
            raise ActivityError(400, "invalid_fields", "Invalid field types or bounds in activity event")

        if authority_class == "GUEST":
            if kind in SERVICE_EVENT_KINDS:
                raise ActivityError(403, "forbidden_kind", f"Guest cannot emit service-only event kind '{kind}'")
            if kind not in GUEST_EVENT_KINDS:
                raise ActivityError(400, "invalid_kind", f"Unsupported guest event kind '{kind}'")
        else:
            if kind not in SERVICE_EVENT_KINDS and kind not in GUEST_EVENT_KINDS:
                raise ActivityError(400, "invalid_kind", f"Unsupported event kind '{kind}'")

        raw_summary = payload.get("summary") or payload.get("message") or kind
        if not isinstance(raw_summary, str) or len(raw_summary.encode("utf-8")) > MAX_EVENT_MESSAGE_BYTES:
            raise ActivityError(400, "message_too_large", "Event summary/message must be string <= 8 KiB")
        safe_summary = sanitize_payload(raw_summary)

        # Guest evidence/candidate submissions are always recorded as 'claimed', never 'validated'
        evidence_status: str | None = None
        candidate_commit: str | None = None
        if kind in {"evidence.submitted", "candidate.submitted"}:
            evidence_status = "claimed"
            cand = payload.get("candidate_commit") or payload.get("candidate_commit_sha")
            if isinstance(cand, str) and cand.strip():
                candidate_commit = cand.strip()[:64]
        elif authority_class == "SERVICE" and kind in {"verification.recorded", "review.recorded", "candidate.exported"}:
            st = payload.get("evidence_status")
            if st in {"claimed", "validated", "rejected"}:
                evidence_status = st
            cand = payload.get("candidate_commit") or payload.get("candidate_commit_sha")
            if isinstance(cand, str) and cand.strip():
                candidate_commit = cand.strip()[:64]

        ev_digest = digest({
            "schema_version": 1,
            "event_id": event_id,
            "task_id": task_id_in,
            "attempt_id": attempt_id,
            "sequence": seq,
            "kind": kind,
            "authority_class": authority_class,
            "payload": payload,
        })

        received_iso = datetime.now(timezone.utc).isoformat()

        with self.db.atomic_transaction() as conn:
            proj = self._resolve_project(conn, project_id_or_key)
            project_id = str(proj["id"])
            issue, stable_task_id = self._resolve_issue_and_task(conn, task_id_in, project_id)
            issue_id = str(issue["id"])

            # Verify attempt ownership and generation
            att = conn.execute(
                "SELECT * FROM pm_coordinator_attempts WHERE attempt_id = ? AND issue_id = ?",
                (attempt_id, issue_id),
            ).fetchone()
            if not att:
                raise ActivityError(404, "attempt_not_found", f"Attempt '{attempt_id}' not found for task")
            if att["tenant_id"] != tenant_id:
                raise ActivityError(403, "forbidden", "Tenant mismatch for attempt")
            if expected_fencing_token is not None and int(att["fencing_token"]) != expected_fencing_token:
                raise ActivityError(409, "stale_generation", "Stale fencing token for runtime channel")
            if att["status"] == "CANCELED":
                raise ActivityError(409, "attempt_canceled", "Cannot emit events for canceled attempt")

            run_row = conn.execute(
                "SELECT run_id, fencing_token FROM pm_coordinator_runs WHERE attempt_id = ? ORDER BY started_at DESC LIMIT 1",
                (attempt_id,),
            ).fetchone()
            run_id = str(run_row["run_id"]) if run_row else None
            fencing_token = int(run_row["fencing_token"]) if run_row else int(att["fencing_token"])

            # Check idempotency by (tenant_id, project_id, event_id)
            existing = conn.execute(
                """
                SELECT * FROM pm_runtime_activity_events
                WHERE tenant_id = ? AND project_id = ? AND event_id = ?
                """,
                (tenant_id, project_id, event_id),
            ).fetchone()
            if existing is not None:
                if existing["payload_digest"] != ev_digest:
                    raise ActivityError(409, "conflicting_event_id", "Conflicting payload for existing event_id")
                max_chg = conn.execute(
                    "SELECT COALESCE(MAX(change_seq), 0) AS m FROM pm_project_board_changes WHERE tenant_id = ? AND project_id = ?",
                    (tenant_id, project_id),
                ).fetchone()["m"]
                return {
                    "receipt_id": existing["receipt_id"],
                    "event_id": event_id,
                    "task_id": stable_task_id,
                    "accepted_sequence": int(existing["sequence"]),
                    "task_version": int(issue["policy_version"]),
                    "board_cursor": f"chg:{tenant_id}:{project_id}:{max_chg}",
                }

            # Enforce per-(attempt_id, authority_class) contiguous sequence ordering
            last_seq_row = conn.execute(
                """
                SELECT COALESCE(MAX(sequence), 0) AS max_seq
                FROM pm_runtime_activity_events
                WHERE tenant_id = ? AND project_id = ? AND attempt_id = ? AND authority_class = ?
                """,
                (tenant_id, project_id, attempt_id, authority_class),
            ).fetchone()
            expected_seq = int(last_seq_row["max_seq"]) + 1
            if seq != expected_seq:
                raise ActivityError(
                    409,
                    "sequence_mismatch",
                    f"Expected sequence {expected_seq} for attempt '{attempt_id}', got {seq}",
                )

            receipt_id = f"act_{secrets.token_hex(16)}"
            conn.execute(
                """
                INSERT INTO pm_runtime_activity_events (
                    receipt_id, tenant_id, project_id, issue_id, task_id,
                    attempt_id, run_id, fencing_token, event_id, sequence,
                    kind, authority_class, actor, summary, payload_digest,
                    payload_json, evidence_status, candidate_commit_sha,
                    occurred_at, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt_id,
                    tenant_id,
                    project_id,
                    issue_id,
                    stable_task_id,
                    attempt_id,
                    run_id,
                    fencing_token,
                    event_id,
                    seq,
                    kind,
                    authority_class,
                    actor,
                    safe_summary,
                    ev_digest,
                    canonical(payload),
                    evidence_status,
                    candidate_commit,
                    occurred_at,
                    received_iso,
                ),
            )

            # Update blocker_reason if work.blocked / work.resumed (without inventing FSM states)
            if kind == "work.blocked":
                conn.execute(
                    "UPDATE pm_issues SET blocker_reason = ?, updated_at = ? WHERE id = ?",
                    (safe_summary[:500], received_iso, issue_id),
                )
            elif kind == "work.resumed":
                conn.execute(
                    "UPDATE pm_issues SET blocker_reason = NULL, updated_at = ? WHERE id = ?",
                    (received_iso, issue_id),
                )

            task_version = int(issue["policy_version"])
            cur = conn.execute(
                """
                INSERT INTO pm_project_board_changes (
                    tenant_id, project_id, issue_id, task_id,
                    change_kind, task_version, summary_json, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tenant_id,
                    project_id,
                    issue_id,
                    stable_task_id,
                    kind,
                    task_version,
                    canonical({
                        "event_id": event_id,
                        "issue_key": issue["key"],
                        "kind": kind,
                        "actor": actor,
                        "summary": safe_summary,
                    }),
                    received_iso,
                ),
            )
            change_seq = int(cur.lastrowid)

        return {
            "receipt_id": receipt_id,
            "event_id": event_id,
            "task_id": stable_task_id,
            "accepted_sequence": seq,
            "task_version": task_version,
            "board_cursor": f"chg:{tenant_id}:{project_id}:{change_seq}",
        }

    def get_task_activity(
        self,
        *,
        tenant_id: str,
        issue_or_task_id: str,
        after_cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Returns version-1 task activity, attempt summaries, and validated/stale review projections."""
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ActivityError(400, "invalid_limit", "limit must be between 1 and 200")

        with self.db._get_connection() as conn:
            issue, stable_task_id = self._resolve_issue_and_task(conn, issue_or_task_id)
            issue_id = str(issue["id"])
            project_id = str(issue["project_id"])
            policy_version = int(issue["policy_version"])
            has_pending_recon = bool(issue["has_pending_reconciliation"])

            # Verify tenant ownership if attempts exist for another tenant
            wrong_tenant = conn.execute(
                "SELECT 1 FROM pm_coordinator_attempts WHERE issue_id = ? AND tenant_id != ? LIMIT 1",
                (issue_id, tenant_id),
            ).fetchone()
            if wrong_tenant:
                raise ActivityError(404, "not_found", f"Task '{issue_or_task_id}' not found")

            after_id = 0
            if after_cursor:
                parts = after_cursor.split(":")
                if len(parts) != 5 or parts[0] != "act" or not parts[4].isdigit():
                    raise ActivityError(400, "invalid_cursor", "Malformed activity cursor")
                _, cur_tenant, cur_proj, cur_issue, cur_seq_str = parts
                if cur_tenant != tenant_id or cur_proj != project_id or cur_issue != issue_id:
                    raise ActivityError(403, "cursor_scope_mismatch", "Cursor does not belong to this tenant/project/task")
                after_id = int(cur_seq_str)

            rows = conn.execute(
                """
                SELECT * FROM pm_runtime_activity_events
                WHERE tenant_id = ? AND project_id = ? AND issue_id = ? AND cursor_id > ?
                ORDER BY cursor_id ASC
                LIMIT ?
                """,
                (tenant_id, project_id, issue_id, after_id, limit + 1),
            ).fetchall()

            has_more = len(rows) > limit
            page_rows = rows[:limit]

            # Latest candidate commit across attempts
            latest_att = conn.execute(
                """
                SELECT attempt_id, candidate_commit_sha, fencing_token
                FROM pm_coordinator_attempts
                WHERE issue_id = ? AND tenant_id = ?
                ORDER BY attempt_seq DESC LIMIT 1
                """,
                (issue_id, tenant_id),
            ).fetchone()
            current_candidate_commit = (
                str(latest_att["candidate_commit_sha"])
                if latest_att and latest_att["candidate_commit_sha"]
                else None
            )

            events_out = []
            last_cursor_id = after_id
            for r in page_rows:
                last_cursor_id = int(r["cursor_id"])
                ev_item: dict[str, Any] = {
                    "event_id": r["event_id"],
                    "cursor": f"act:{tenant_id}:{project_id}:{issue_id}:{last_cursor_id}",
                    "kind": r["kind"],
                    "actor": r["actor"],
                    "summary": r["summary"],
                    "occurred_at": r["occurred_at"],
                    "received_at": r["received_at"],
                    "sequence": int(r["sequence"]),
                }
                if r["evidence_status"] or r["candidate_commit_sha"]:
                    ev_item["evidence"] = {
                        "status": r["evidence_status"] if r["evidence_status"] in {"claimed", "validated", "rejected"} else "claimed",
                        "candidate_commit": r["candidate_commit_sha"],
                    }
                events_out.append(ev_item)

            # Attempt summaries (projecting PENDING->QUEUED, CANCELED->CANCELLED)
            att_rows = conn.execute(
                """
                SELECT a.attempt_id, a.attempt_seq, a.status AS attempt_status,
                       i.status AS intent_status,
                       (SELECT r.run_id FROM pm_coordinator_runs r WHERE r.attempt_id = a.attempt_id ORDER BY r.started_at DESC LIMIT 1) AS run_id
                FROM pm_coordinator_attempts a
                LEFT JOIN pm_coordinator_intents i ON i.attempt_id = a.attempt_id
                WHERE a.issue_id = ? AND a.tenant_id = ?
                ORDER BY a.attempt_seq ASC
                """,
                (issue_id, tenant_id),
            ).fetchall()
            attempts_out = []
            for ar in att_rows:
                raw_state = ar["attempt_status"]
                if ar["intent_status"] == "CANCEL_REQUESTED" and raw_state not in {"CANCELED", "SUCCEEDED", "FAILED"}:
                    ui_state = "CANCEL_REQUESTED"
                else:
                    ui_state = ATTEMPT_STATE_PROJECTION.get(raw_state, raw_state)
                attempts_out.append({
                    "attempt_id": ar["attempt_id"],
                    "run_id": ar["run_id"],
                    "state": ui_state,
                })

            # Review summaries projected from coordinator evidence receipts
            rev_rows = conn.execute(
                """
                SELECT evidence_id, run_id, candidate_commit_sha, key_id, signature, canonical_payload, admission_status
                FROM pm_coordinator_evidence_receipts
                WHERE issue_id = ?
                ORDER BY created_at ASC
                """,
                (issue_id,),
            ).fetchall()
            reviews_out = []
            for rr in rev_rows:
                try:
                    p = strict_json(rr["canonical_payload"])
                except Exception:
                    continue
                if not isinstance(p, dict) or p.get("type") != "REVIEW_EVIDENCE":
                    continue
                res = p.get("result") if isinstance(p.get("result"), dict) else {}
                verdict = res.get("verdict", "REJECTED")
                cand_sha = rr["candidate_commit_sha"]
                issuer = p.get("issuer_id", "unknown")

                # Validate server-side current authority — historical ADMITTED label alone is not enough!
                is_validated = False
                if (
                    rr["admission_status"] == "ADMITTED"
                    and not has_pending_recon
                    and p.get("schema") == SCHEMA
                    and p.get("domain") == "PRODUCTION"
                    and p.get("policy_version") == policy_version
                    and current_candidate_commit is not None
                    and cand_sha == current_candidate_commit
                ):
                    if self.evidence_trust is not None:
                        try:
                            grant = self.evidence_trust._require_issuer(rr["key_id"])
                            is_validated = (
                                grant.role == "REVIEW_EVIDENCE"
                                and verify_signature(p, rr["signature"], grant.secret)
                            )
                        except Exception:
                            is_validated = False
                    else:
                        is_validated = True

                reviews_out.append({
                    "review_id": rr["evidence_id"],
                    "candidate_commit": cand_sha,
                    "reviewer_principal": f"{tenant_id}:{issuer}" if ":" not in str(issuer) else str(issuer),
                    "decision": verdict if verdict in {"APPROVED", "REJECTED", "CHANGES_REQUESTED"} else "REJECTED",
                    "trust_status": "validated" if is_validated else "claimed",
                })

            max_chg = conn.execute(
                "SELECT COALESCE(MAX(change_seq), 0) AS m FROM pm_project_board_changes WHERE tenant_id = ? AND project_id = ?",
                (tenant_id, project_id),
            ).fetchone()["m"]

        now_iso = datetime.now(timezone.utc).isoformat()
        next_cursor = (
            f"act:{tenant_id}:{project_id}:{issue_id}:{last_cursor_id}"
            if page_rows
            else (after_cursor or f"act:{tenant_id}:{project_id}:{issue_id}:0")
        )
        return {
            "schema_version": 1,
            "task_id": stable_task_id,
            "issue_id": issue_id,
            "events": events_out,
            "attempts": attempts_out,
            "reviews": reviews_out,
            "current_candidate_commit": current_candidate_commit,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "snapshot_cursor": f"chg:{tenant_id}:{project_id}:{max_chg}",
            "observed_at": now_iso,
        }

    def get_project_changes(
        self,
        *,
        tenant_id: str,
        project_id_or_key: str,
        after_cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Returns incremental board changes since after_cursor, or raises 410 resync_required on gap."""
        if type(limit) is not int or not 1 <= limit <= 200:
            raise ActivityError(400, "invalid_limit", "limit must be between 1 and 200")

        with self.db._get_connection() as conn:
            proj = self._resolve_project(conn, project_id_or_key)
            project_id = str(proj["id"])

            after_seq = 0
            if after_cursor:
                parts = after_cursor.split(":")
                if len(parts) != 4 or parts[0] != "chg" or not parts[3].isdigit():
                    raise ActivityError(400, "invalid_cursor", "Malformed board changes cursor")
                _, cur_tenant, cur_proj, cur_seq_str = parts
                if cur_tenant != tenant_id or cur_proj != project_id:
                    raise ActivityError(403, "cursor_scope_mismatch", "Cursor does not match tenant/project")
                after_seq = int(cur_seq_str)

            # Check for retained-feed gap -> 410 resync_required
            if after_seq > 0 and after_seq < self.min_retained_change_seq - 1:
                raise ActivityError(
                    410,
                    "resync_required",
                    "Requested cursor precedes retained change feed; reload full board snapshot",
                )
            min_row = conn.execute(
                "SELECT MIN(change_seq) AS min_seq, MAX(change_seq) AS max_seq FROM pm_project_board_changes WHERE tenant_id = ? AND project_id = ?",
                (tenant_id, project_id),
            ).fetchone()
            if min_row and min_row["min_seq"] is not None:
                min_seq = int(min_row["min_seq"])
                max_seq = int(min_row["max_seq"])
                if after_seq < min_seq - 1 or after_seq > max_seq:
                    raise ActivityError(
                        410,
                        "resync_required",
                        "Cursor gap detected in board change feed; reload full board snapshot",
                    )

            rows = conn.execute(
                """
                SELECT * FROM pm_project_board_changes
                WHERE tenant_id = ? AND project_id = ? AND change_seq > ?
                ORDER BY change_seq ASC
                LIMIT ?
                """,
                (tenant_id, project_id, after_seq, limit + 1),
            ).fetchall()

            has_more = len(rows) > limit
            page_rows = rows[:limit]
            changes_out = []
            last_seq = after_seq
            for r in page_rows:
                last_seq = int(r["change_seq"])
                issue_row = conn.execute("SELECT * FROM pm_issues WHERE id = ?", (r["issue_id"],)).fetchone()
                issue_dump = self.db._row_to_issue(issue_row).model_dump() if issue_row else None
                changes_out.append({
                    "change_seq": last_seq,
                    "cursor": f"chg:{tenant_id}:{project_id}:{last_seq}",
                    "issue_id": r["issue_id"],
                    "task_id": r["task_id"],
                    "change_kind": r["change_kind"],
                    "task_version": int(r["task_version"]),
                    "summary": strict_json(r["summary_json"]),
                    "issue": issue_dump,
                    "recorded_at": r["recorded_at"],
                })

        return {
            "schema_version": 1,
            "project_id": project_id,
            "changes": changes_out,
            "next_cursor": f"chg:{tenant_id}:{project_id}:{last_seq}",
            "has_more": has_more,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_board_snapshot_meta(self, *, tenant_id: str, project_id_or_key: str) -> dict[str, Any]:
        """Returns the current consistent snapshot_cursor and observed_at for a project board."""
        with self.db._get_connection() as conn:
            proj = self._resolve_project(conn, project_id_or_key)
            project_id = str(proj["id"])
            max_chg = conn.execute(
                "SELECT COALESCE(MAX(change_seq), 0) AS m FROM pm_project_board_changes WHERE tenant_id = ? AND project_id = ?",
                (tenant_id, project_id),
            ).fetchone()["m"]
        return {
            "snapshot_cursor": f"chg:{tenant_id}:{project_id}:{int(max_chg)}",
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }


__all__ = [
    "ActivityBridgeService",
    "ActivityError",
    "ActivitySpool",
    "GUEST_EVENT_KINDS",
    "SERVICE_EVENT_KINDS",
]
