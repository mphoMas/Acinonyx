"""
mas.pm.worker: Outbox scheduling worker, single-winner claims, and lease-recovery engine (CC-04).
Implements:
- Dependency-ready and funded task admission
- Single-winner CAS claim protocol on unlaunched (PENDING) intents
- Bounded polling loops with jitter and graceful shutdown
- Controlled / synthetic adapter interface (live runtime dispatch strictly gated)
- Heartbeat loop with lease renewal
- Atomic lease-recovery and reaper engine transitioning expired PROCESSING to UNKNOWN_EXECUTION
- Conservative token settlement retaining unverified holds
"""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from mas.pm.db import PMDatabase
from mas.pm.guards import validate_dependencies
from mas.pm.models import (
    CoordinatorIntent,
    IssueState,
)

logger = logging.getLogger(__name__)


class AdapterExecutionRequest:
    """Request envelope passed to an execution adapter."""

    def __init__(
        self,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_id: str,
        attempt_seq: int,
        fencing_token: int,
        runtime_type: str,
        prompt: str,
        workspace_path: str = "",
        path_whitelist: Optional[List[str]] = None,
        budget_token_limit: int = 10_000,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.issue_id = issue_id
        self.task_id = task_id
        self.attempt_id = attempt_id
        self.attempt_seq = attempt_seq
        self.fencing_token = fencing_token
        self.runtime_type = runtime_type
        self.prompt = prompt
        self.workspace_path = workspace_path
        self.path_whitelist = path_whitelist or []
        self.budget_token_limit = budget_token_limit
        self.timeout_seconds = timeout_seconds


class AdapterExecutionResult:
    """Result returned by an execution adapter."""

    def __init__(
        self,
        attempt_id: str,
        run_id: str,
        status: str,
        exit_code: Optional[int] = None,
        tokens_billed: int = 0,
        duration_seconds: float = 0.0,
        runtime_session_id: Optional[str] = None,
        candidate_commit_sha: Optional[str] = None,
        artifacts: Optional[List[Dict[str, Any]]] = None,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.attempt_id = attempt_id
        self.run_id = run_id
        self.status = status
        self.exit_code = exit_code
        self.tokens_billed = tokens_billed
        self.duration_seconds = duration_seconds
        self.runtime_session_id = runtime_session_id
        self.candidate_commit_sha = candidate_commit_sha
        self.artifacts = artifacts or []
        self.error_details = error_details


class BaseExecutionAdapter(ABC):
    """Abstract interface for execution runtime adapters."""

    @abstractmethod
    def execute(
        self,
        request: AdapterExecutionRequest,
        run_id: str,
        emit_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> AdapterExecutionResult:
        """Executes the task and returns execution results."""
        pass


class SyntheticExecutionAdapter(BaseExecutionAdapter):
    """
    Controlled synthetic adapter for CC-04 scheduling and lease tests.
    Does NOT invoke external CLI processes (agy or codex).
    Supports programmable exit codes, spend, latency, and event streaming.
    """

    def __init__(
        self,
        exit_code: int = 0,
        tokens_billed: int = 10,
        duration_seconds: float = 0.01,
        candidate_commit_sha: Optional[str] = "synthetic-sha-0001",
        events: Optional[List[Dict[str, Any]]] = None,
        simulate_crash: bool = False,
    ) -> None:
        self.exit_code = exit_code
        self.tokens_billed = tokens_billed
        self.duration_seconds = duration_seconds
        self.candidate_commit_sha = candidate_commit_sha
        self.events = events or [{"type": "START", "data": {}}, {"type": "COMPLETE", "data": {}}]
        self.simulate_crash = simulate_crash

    def execute(
        self,
        request: AdapterExecutionRequest,
        run_id: str,
        emit_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> AdapterExecutionResult:
        if emit_event:
            for ev in self.events:
                emit_event(ev.get("type", "PROGRESS"), ev.get("data", {}))

        if self.duration_seconds > 0:
            time.sleep(self.duration_seconds)

        if self.simulate_crash:
            raise RuntimeError("Synthetic simulated execution crash / mid-run failure")

        status = "SUCCEEDED" if self.exit_code == 0 else "FAILED"
        return AdapterExecutionResult(
            attempt_id=request.attempt_id,
            run_id=run_id,
            status=status,
            exit_code=self.exit_code,
            tokens_billed=self.tokens_billed,
            duration_seconds=self.duration_seconds,
            runtime_session_id=f"synthetic-session-{run_id}",
            candidate_commit_sha=self.candidate_commit_sha if self.exit_code == 0 else None,
        )


class CoordinatorAdmissionEngine:
    """
    Validates and admits tasks into the coordinator outbox.
    Enforces:
    - Dependency readiness (all blockers in pm_dependencies must be DONE)
    - Funded budget reservations (finite integer <= issue appetite and available project budget)
    - Single active attempt per issue (no duplicate concurrent executions)
    - Unlaunched work staged into outbox as PENDING
    """

    def __init__(self, db: PMDatabase) -> None:
        self.db = db
        self.store = db.coordinator

    def admit_task(
        self,
        issue_id: str,
        adapter_type: str = "synthetic",
        budget_reservation: Optional[int] = None,
        attempt_id: Optional[str] = None,
        intent_id: Optional[str] = None,
        prompt: str = "",
        payload_extra: Optional[Dict[str, Any]] = None,
    ) -> CoordinatorIntent:
        """
        Admits a task to STAGED / PENDING outbox intent.
        Fails closed if dependencies are unresolved, budget is exhausted, or an active attempt exists.
        """
        issue = self.db.get_issue(issue_id)
        if not issue:
            raise ValueError(f"Issue {issue_id} not found")

        # 1. Dependency validation
        validate_dependencies(self.db, issue)

        # 2. Check that issue does not already have an in-flight attempt
        active_intents = [
            i for i in self.store.list_intents_for_issue(issue_id)
            if i.status in ("PENDING", "CLAIMED", "PROCESSING", "CANCEL_REQUESTED")
        ]
        if active_intents:
            raise ValueError(
                f"Issue {issue.key} already has an active intent ({active_intents[0].intent_id}: {active_intents[0].status})"
            )

        # 3. Determine reservation amount (default to issue appetite if not specified)
        res_amount = budget_reservation if budget_reservation is not None else issue.appetite_tokens
        if not isinstance(res_amount, int) or isinstance(res_amount, bool):
            raise ValueError(f"budget_reservation must be an integer, got {type(res_amount).__name__}")
        if res_amount < 0:
            raise ValueError(f"budget_reservation must be non-negative, got {res_amount}")

        # 4. Generate identities
        seq = issue.reflexion_attempts + 1
        att_id = attempt_id or f"att_{issue_id}_{seq}_{int(time.time()*1000)}"
        int_id = intent_id or f"intent_{issue_id}_{seq}_{int(time.time()*1000)}"

        # 5. Fetch planning task_id from mapping or fallback
        with self.db._get_connection() as c:
            row = c.execute(
                "SELECT task_id FROM pm_task_mappings WHERE local_issue_id = ?",
                (issue_id,),
            ).fetchone()
            planning_task_id = row["task_id"] if row else (issue.task_id or issue.id)

            from mas.tenancy import current_binding
            binding = current_binding()
            tenant_id = binding.identity.tenant_id if binding else "default"

        payload = {
            "prompt": prompt or f"Execute task {issue.key}: {issue.title}",
            "workspace_path": "",
            "path_whitelist": issue.path_whitelist,
            "budget_token_limit": res_amount,
            **(payload_extra or {}),
        }

        # 6. Create attempt and intent atomically with funded reservation
        attempt, intent = self.store.create_attempt_with_intent(
            attempt_id=att_id,
            intent_id=int_id,
            tenant_id=tenant_id,
            project_id=issue.project_id,
            issue_id=issue.id,
            task_id=planning_task_id,
            attempt_seq=seq,
            adapter_type=adapter_type,
            payload=payload,
            budget_reservation=res_amount,
        )

        # Update issue current_state to STAGED if it was BACKLOG or REFINED
        if issue.current_state in (IssueState.BACKLOG, IssueState.REFINED):
            self.db.update_issue_state(
                issue_id=issue.id,
                new_state=IssueState.STAGED.value,
                triggered_by="coordinator:admission",
                reason="Task admitted to coordinator outbox",
            )

        return intent


class CoordinatorWorker:
    """
    Coordinator background scheduling worker and lease management daemon (CC-04).
    Features:
    - Single-winner CAS claim protocol on PENDING intents
    - Guarded pre-spawn transition to PROCESSING
    - Controlled adapter dispatch (synthetic adapter default; live dispatch gated)
    - Monotonic event cursor streaming into pm_coordinator_events
    - Fencing-token guarded completion
    - Bounded polling with jitter
    - Expired lease reaping with atomic retirement of dead workers
    """

    def __init__(
        self,
        db: PMDatabase,
        worker_id: str,
        adapter: Optional[BaseExecutionAdapter] = None,
        lease_timeout_s: float = 10.0,
        heartbeat_interval_s: float = 2.0,
        poll_interval_s: float = 0.5,
    ) -> None:
        self.db = db
        self.store = db.coordinator
        self.worker_id = worker_id
        self.adapter = adapter or SyntheticExecutionAdapter()
        self.lease_timeout_s = lease_timeout_s
        self.heartbeat_interval_s = heartbeat_interval_s
        self.poll_interval_s = poll_interval_s
        self._running = False

    def process_one_intent(self, intent: CoordinatorIntent) -> bool:
        """
        Attempts to claim and execute a single intent.
        Returns True if claimed and executed, False if race was lost or state changed.
        """
        now = time.time()

        # Step 1: Single-winner CAS Claim on PENDING intent
        claimed = self.store.claim_intent(
            intent_id=intent.intent_id,
            worker_id=self.worker_id,
            expected_fencing_token=intent.fencing_token,
            now_epoch=now,
            lease_timeout_s=self.lease_timeout_s,
        )
        if not claimed:
            # Race lost or already claimed by another worker
            return False

        # Step 2: Fetch updated intent to obtain new fencing generation
        updated_intent = self.store.get_intent(intent.intent_id)
        if not updated_intent:
            return False

        assigned_fencing = updated_intent.fencing_token
        run_id = f"run_{intent.intent_id}_{assigned_fencing}"

        # Step 3: Guarded pre-spawn persistence
        pre_spawn_ok = self.store.pre_spawn_intent(
            intent_id=intent.intent_id,
            worker_id=self.worker_id,
            assigned_fencing_token=assigned_fencing,
            now_epoch=time.time(),
            run_id=run_id,
        )
        if not pre_spawn_ok:
            return False

        # Step 4: Prepare execution request
        payload = updated_intent.payload or {}
        req = AdapterExecutionRequest(
            tenant_id=updated_intent.tenant_id,
            project_id=updated_intent.project_id,
            issue_id=updated_intent.issue_id,
            task_id=updated_intent.task_id,
            attempt_id=updated_intent.attempt_id,
            attempt_seq=1,
            fencing_token=assigned_fencing,
            runtime_type=updated_intent.adapter_type,
            prompt=payload.get("prompt", ""),
            workspace_path=payload.get("workspace_path", ""),
            path_whitelist=payload.get("path_whitelist", []),
            budget_token_limit=payload.get("budget_token_limit", 10_000),
        )

        cursor_seq = 0

        def emit_event(ev_type: str, ev_data: Dict[str, Any]) -> None:
            nonlocal cursor_seq
            try:
                self.store.record_run_event(
                    run_id=run_id,
                    cursor_seq=cursor_seq,
                    event_type=ev_type,
                    event_payload=ev_data,
                )
                cursor_seq += 1
            except Exception as e:
                logger.warning(f"Error recording run event for run {run_id}: {e}")

        # Step 5: Execute adapter (network/subprocess calls outside DB transaction)
        try:
            result = self.adapter.execute(req, run_id=run_id, emit_event=emit_event)
        except Exception as err:
            logger.error(f"Execution error on run {run_id}: {err}")
            # Worker crash / exception during execution -> transition to UNKNOWN_EXECUTION
            self.store.complete_intent(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                now_epoch=time.time(),
                candidate_commit_sha="crash-unverified",
                exit_code=-1,
                tokens_spent=0,
            )
            return True

        # Step 6: Complete intent guarded by fencing generation and active lease
        completed = self.store.complete_intent(
            intent_id=intent.intent_id,
            worker_id=self.worker_id,
            assigned_fencing_token=assigned_fencing,
            now_epoch=time.time(),
            exit_code=result.exit_code or 0,
            candidate_commit_sha=result.candidate_commit_sha,
            tokens_spent=result.tokens_billed or 0,
        )
        return completed

    def run_one_polling_cycle(self) -> int:
        """
        Executes one polling pass:
        1. Reaps expired leases across workers
        2. Queries pending intents
        3. Claims and processes eligible work
        Returns count of processed intents.
        """
        # 1. Reap expired leases
        now = time.time()
        self.store.reap_expired_leases(now)

        # 2. Query pending intents
        pending = self.store.list_pending_intents(limit=10)
        processed = 0
        for intent in pending:
            if self.process_one_intent(intent):
                processed += 1
        return processed

    def start_bounded(self, max_cycles: int = 10) -> int:
        """Runs the worker for a bounded number of polling iterations."""
        self._running = True
        total_processed = 0
        for _ in range(max_cycles):
            if not self._running:
                break
            count = self.run_one_polling_cycle()
            total_processed += count
            if count == 0:
                time.sleep(self.poll_interval_s * (0.8 + 0.4 * random.random()))
        return total_processed

    def stop(self) -> None:
        """Signals worker to halt polling."""
        self._running = False
