"""
mas.pm.worker: Outbox scheduling worker, single-winner claims, and lease-recovery engine (CC-04).
Implements:
- Dependency-ready and funded task admission under single atomic transaction
- Monotonic attempt sequence allocation from persistent coordinator store
- Payload parameter allowlisting preventing override of task scope/budget/identity
- Single-winner CAS claim protocol on unlaunched (PENDING) intents
- Supervised execution lifecycle with active heartbeat thread, deadline enforcement, and stop signal
- Fail-closed error handling: execution exceptions transition to UNKNOWN_EXECUTION with preserved budget holds
- Strict validation of adapter results against requested/persisted identity and measurements
- Atomic lease-recovery and reaper engine transitioning expired PROCESSING to UNKNOWN_EXECUTION
"""

from __future__ import annotations

import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from mas.pm.db import PMDatabase
from mas.pm.fsm import FSMEngine
from mas.pm.guards import (
    validate_appetite,
    validate_dependencies,
    validate_scope_jail,
    validate_wip_limit,
)
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
        tokens_billed: Optional[int] = None,
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


class AdapterNotQualifiedError(RuntimeError):
    """Raised when an execution adapter does not satisfy the qualification policy."""
    pass


class BaseExecutionAdapter(ABC):
    """Abstract interface for execution runtime adapters."""

    supports_bounded_stop: bool = False
    cleanup_timeout_s: float = 0.5

    @abstractmethod
    def execute(
        self,
        request: AdapterExecutionRequest,
        run_id: str,
        emit_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> AdapterExecutionResult:
        """Executes the task and returns execution results."""
        pass


class SyntheticExecutionAdapter(BaseExecutionAdapter):
    """
    Controlled synthetic adapter for CC-04 scheduling and lease tests.
    Does NOT invoke external CLI processes (agy or codex).
    Supports programmable exit codes, spend, latency, event streaming, and cancellation.
    """

    supports_bounded_stop: bool = True
    cleanup_timeout_s: float = 0.5

    def __init__(
        self,
        exit_code: int = 0,
        tokens_billed: Optional[int] = 10,
        duration_seconds: float = 0.01,
        candidate_commit_sha: Optional[str] = "synthetic-sha-0001",
        events: Optional[List[Dict[str, Any]]] = None,
        simulate_crash: bool = False,
        status_override: Optional[str] = None,
        attempt_id_override: Optional[str] = None,
        run_id_override: Optional[str] = None,
    ) -> None:
        self.exit_code = exit_code
        self.tokens_billed = tokens_billed
        self.duration_seconds = duration_seconds
        self.candidate_commit_sha = candidate_commit_sha
        self.events = events or [{"type": "START", "data": {}}, {"type": "COMPLETE", "data": {}}]
        self.simulate_crash = simulate_crash
        self.status_override = status_override
        self.attempt_id_override = attempt_id_override
        self.run_id_override = run_id_override

    def execute(
        self,
        request: AdapterExecutionRequest,
        run_id: str,
        emit_event: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        stop_event: Optional[threading.Event] = None,
    ) -> AdapterExecutionResult:
        if emit_event:
            for ev in self.events:
                emit_event(ev.get("type", "PROGRESS"), ev.get("data", {}))

        step = 0.05
        elapsed = 0.0
        while elapsed < self.duration_seconds:
            if stop_event and stop_event.is_set():
                return AdapterExecutionResult(
                    attempt_id=self.attempt_id_override or request.attempt_id,
                    run_id=self.run_id_override or run_id,
                    status="CANCELED",
                    exit_code=130,
                    tokens_billed=self.tokens_billed if self.tokens_billed is not None else 0,
                    duration_seconds=elapsed,
                )
            sleep_time = min(step, self.duration_seconds - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time

        if self.simulate_crash:
            raise RuntimeError("Synthetic simulated execution crash / mid-run failure")

        effective_status = self.status_override or ("SUCCEEDED" if self.exit_code == 0 else "FAILED")
        return AdapterExecutionResult(
            attempt_id=self.attempt_id_override or request.attempt_id,
            run_id=self.run_id_override or run_id,
            status=effective_status,
            exit_code=self.exit_code,
            tokens_billed=self.tokens_billed,
            duration_seconds=self.duration_seconds,
            runtime_session_id=f"synthetic-session-{run_id}",
            candidate_commit_sha=self.candidate_commit_sha if (effective_status == "SUCCEEDED" and self.exit_code == 0) else None,
        )


class CoordinatorAdmissionEngine:
    """
    Validates and admits tasks into the coordinator outbox atomically under lock.
    Enforces:
    - Task state check (cannot auto-stage DONE or already active issues)
    - Pending plan reconciliation guard
    - Monotonic attempt sequence derived from persistent coordinator attempts
    - Dependency readiness (all blockers in pm_dependencies must be DONE)
    - Funded budget reservations (finite integer <= issue appetite and available project budget)
    - Strict allowlist on payload extra parameters (preventing scope or budget overrides)
    - Atomic execution: dependency check, attempt/intent creation, reservation, and FSM transition in ONE transaction
    """

    ALLOWED_EXTRA_PAYLOAD_KEYS = frozenset({"extra_metadata", "notes", "tags", "timeout_seconds"})

    def __init__(self, db: PMDatabase) -> None:
        self.db = db
        self.store = db.coordinator
        self.fsm = FSMEngine(db)

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
        Admits a task to STAGED / PENDING outbox intent in one atomic transaction.
        Fails closed on any inconsistency, unresolved dependencies, or exhausted budget.
        """
        with self.db.atomic_transaction() as conn:
            # 1. Fetch issue under lock
            cur = conn.execute("SELECT * FROM pm_issues WHERE id = ? OR key = ?", (issue_id, issue_id.upper()))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Issue {issue_id} not found")
            issue = self.db._row_to_issue(row)

            # 1. Check pending plan reconciliation
            if issue.has_pending_reconciliation:
                raise ValueError(f"Issue {issue.key} has pending plan reconciliation; explicit decision required before admission")

            # 2. Check for any active or unresolved intent/attempt on this issue
            active_row = conn.execute(
                """
                SELECT intent_id, status FROM pm_coordinator_intents
                WHERE issue_id = ? AND status IN ('PENDING', 'CLAIMED', 'PROCESSING', 'CANCEL_REQUESTED', 'UNKNOWN_EXECUTION')
                LIMIT 1
                """,
                (issue.id,),
            ).fetchone()
            if active_row:
                raise ValueError(
                    f"Issue {issue.key} already has an active or unresolved intent ({active_row['intent_id']}: {active_row['status']})"
                )

            # 3. Check task state: allow ONLY BACKLOG, REFINED (or STAGED if previous attempt was completed/settled)
            if issue.current_state == IssueState.DONE:
                raise ValueError(f"Issue {issue.key} is already in DONE state; cannot admit completed work")
            if issue.current_state not in (IssueState.BACKLOG, IssueState.REFINED, IssueState.STAGED):
                raise ValueError(
                    f"Issue {issue.key} is in state {issue.current_state.value}; "
                    f"only BACKLOG, REFINED, or STAGED tasks can be admitted to coordinator outbox"
                )

            # 4. Evaluate FSM admission guards under transaction
            validate_appetite(issue)
            validate_scope_jail(issue)
            validate_wip_limit(self.db, issue.project_id, IssueState.STAGED.value, conn=conn)

            # 5. Dependency validation under this transaction
            validate_dependencies(self.db, issue, conn=conn)

            # 4. Determine reservation amount (default to issue appetite if not specified)
            res_amount = budget_reservation if budget_reservation is not None else issue.appetite_tokens
            if not isinstance(res_amount, int) or isinstance(res_amount, bool):
                raise ValueError(f"budget_reservation must be an integer, got {type(res_amount).__name__}")
            if res_amount < 0:
                raise ValueError(f"budget_reservation must be non-negative, got {res_amount}")
            if res_amount > issue.appetite_tokens:
                raise ValueError(
                    f"Requested reservation {res_amount} exceeds issue appetite {issue.appetite_tokens}"
                )

            # 5. Monotonic attempt sequence derived from persistent coordinator attempts
            seq_row = conn.execute(
                "SELECT COALESCE(MAX(attempt_seq), 0) + 1 AS next_seq FROM pm_coordinator_attempts WHERE issue_id = ?",
                (issue.id,),
            ).fetchone()
            seq = seq_row["next_seq"] if seq_row else 1

            att_id = attempt_id or f"att_{issue.id}_{seq}_{int(time.time()*1000)}"
            int_id = intent_id or f"intent_{issue.id}_{seq}_{int(time.time()*1000)}"

            # 6. Fetch planning task_id from mapping
            map_row = conn.execute("SELECT task_id FROM pm_task_mappings WHERE local_issue_id = ?", (issue.id,)).fetchone()
            planning_task_id = map_row["task_id"] if map_row else (issue.task_id or issue.id)

            from mas.tenancy import current_binding
            binding = current_binding()
            tenant_id = binding.identity.tenant_id if binding else "default"

            # 7. Payload validation: filter payload_extra through strict allowlist
            safe_extra: Dict[str, Any] = {}
            if payload_extra:
                for k, v in payload_extra.items():
                    if k in self.ALLOWED_EXTRA_PAYLOAD_KEYS:
                        safe_extra[k] = v
                    else:
                        logger.debug(f"Ignoring unauthorized extra payload key '{k}' during admission")

            payload = {
                "prompt": prompt or f"Execute task {issue.key}: {issue.title}",
                "workspace_path": "",
                "path_whitelist": list(issue.path_whitelist),
                "budget_token_limit": res_amount,
                "admitted_policy_version": issue.policy_version,
                **safe_extra,
            }

            # 8. Create attempt and intent with budget reservation
            self.store.create_attempt(
                attempt_id=att_id,
                tenant_id=tenant_id,
                project_id=issue.project_id,
                issue_id=issue.id,
                task_id=planning_task_id,
                attempt_seq=seq,
                budget_tokens_allocated=res_amount,
                conn=conn,
            )
            intent = self.store.create_intent(
                intent_id=int_id,
                tenant_id=tenant_id,
                project_id=issue.project_id,
                issue_id=issue.id,
                task_id=planning_task_id,
                attempt_id=att_id,
                adapter_type=adapter_type,
                payload=payload,
                conn=conn,
            )

            # Record reservation in ledger
            if res_amount > 0:
                # Check available capacity
                proj_row = conn.execute(
                    "SELECT token_budget, tokens_consumed FROM pm_projects WHERE id = ?",
                    (issue.project_id,),
                ).fetchone()
                if not proj_row:
                    raise ValueError(f"Project {issue.project_id} not found")
                token_budget = proj_row["token_budget"]
                tokens_consumed = proj_row["tokens_consumed"]

                holds_row = conn.execute(
                    "SELECT COALESCE(SUM(amount - settled_amount), 0) AS open_holds FROM pm_coordinator_reservations WHERE project_id = ? AND status = 'HELD'",
                    (issue.project_id,),
                ).fetchone()
                open_holds = holds_row["open_holds"] if holds_row else 0
                available_capacity = token_budget - tokens_consumed - open_holds
                if res_amount > available_capacity:
                    raise ValueError(
                        f"Requested reservation {res_amount} exceeds available project capacity {available_capacity}"
                    )

                res_id = f"res_{att_id}"
                auth_ref = f"auth_{att_id}"
                now_iso = self.store._now_iso()
                conn.execute(
                    """
                    INSERT INTO pm_coordinator_reservations (
                        reservation_id, tenant_id, project_id, issue_id, attempt_id,
                        authorization_ref, amount, settled_amount, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, 'HELD', ?)
                    """,
                    (res_id, tenant_id, issue.project_id, issue.id, att_id, auth_ref, res_amount, now_iso),
                )

            # 9. FSM State progression: advance BACKLOG or REFINED to STAGED
            if issue.current_state == IssueState.BACKLOG:
                self.db.update_issue_state(
                    issue_id=issue.id,
                    new_state=IssueState.REFINED.value,
                    triggered_by="coordinator:admission",
                    reason="Pre-staged via coordinator admission",
                    conn=conn,
                )
                self.db.update_issue_state(
                    issue_id=issue.id,
                    new_state=IssueState.STAGED.value,
                    triggered_by="coordinator:admission",
                    reason="Admitted to coordinator outbox",
                    conn=conn,
                )
            elif issue.current_state == IssueState.REFINED:
                self.db.update_issue_state(
                    issue_id=issue.id,
                    new_state=IssueState.STAGED.value,
                    triggered_by="coordinator:admission",
                    reason="Admitted to coordinator outbox",
                    conn=conn,
                )

            return intent


class CoordinatorWorker:
    """
    Coordinator background scheduling worker and lease management daemon (CC-04).
    Features:
    - Single-winner CAS claim protocol on PENDING intents
    - Guarded pre-spawn transition to PROCESSING
    - Supervised execution with active heartbeat renewal thread
    - Enforced execution deadlines and stop signals
    - Strict result validation: binds identity to persisted request/run/fence
    - Preserves budget holds on crash / exception / unknown execution
    - Monotonic event cursor streaming into pm_coordinator_events
    - Fencing-token guarded completion
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
        execution_timeout_s: float = 30.0,
        cleanup_timeout_s: Optional[float] = None,
    ) -> None:
        self.db = db
        self.store = db.coordinator
        self.worker_id = worker_id
        selected_adapter = adapter or SyntheticExecutionAdapter()
        # Enforce qualified adapter policy: adapter must explicitly declare bounded stop support
        if not getattr(selected_adapter, "supports_bounded_stop", False):
            raise AdapterNotQualifiedError(
                f"Adapter {type(selected_adapter).__name__} does not satisfy qualification policy: "
                f"must declare supports_bounded_stop=True with terminable supervised execution boundary"
            )
        self.adapter = selected_adapter
        self.lease_timeout_s = max(lease_timeout_s, 2.0)
        self.heartbeat_interval_s = max(min(heartbeat_interval_s, self.lease_timeout_s / 2.0), 0.5)
        self.poll_interval_s = poll_interval_s
        self.execution_timeout_s = execution_timeout_s
        self.cleanup_timeout_s = (
            cleanup_timeout_s
            if cleanup_timeout_s is not None
            else getattr(self.adapter, "cleanup_timeout_s", 0.5)
        )
        self._running = False
        self._stop_requested = threading.Event()

    def process_one_intent(self, intent: CoordinatorIntent) -> bool:
        """
        Attempts to claim and execute a single intent with active heartbeat supervision and strict result validation.
        Returns True if claimed and processed, False if race was lost or state changed.
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
            return False

        # Step 2: Fetch updated intent to obtain new fencing generation
        updated_intent = self.store.get_intent(intent.intent_id)
        if not updated_intent:
            return False

        assigned_fencing = updated_intent.fencing_token
        run_id = f"run_{intent.intent_id}_{assigned_fencing}"

        # Revalidate admitted policy version before pre-spawn
        payload = updated_intent.payload or {}
        admitted_pv = payload.get("admitted_policy_version")
        if admitted_pv is not None:
            curr_issue = self.db.get_issue(updated_intent.issue_id)
            if curr_issue and curr_issue.policy_version != admitted_pv:
                logger.error(
                    f"Policy version changed for issue {updated_intent.issue_id} "
                    f"(admitted: {admitted_pv}, live: {curr_issue.policy_version}); aborting execution."
                )
                self.store.record_execution_interrupted(
                    intent_id=intent.intent_id,
                    worker_id=self.worker_id,
                    assigned_fencing_token=assigned_fencing,
                    error_message=f"STALE_POLICY_VERSION: admitted={admitted_pv}, live={curr_issue.policy_version}",
                )
                return False

        # Step 3: Guarded pre-spawn persistence (atomic policy/reconciliation/scope/funding validation)
        pre_spawn_ok = self.store.pre_spawn_intent(
            intent_id=intent.intent_id,
            worker_id=self.worker_id,
            assigned_fencing_token=assigned_fencing,
            now_epoch=time.time(),
            run_id=run_id,
            expected_policy_version=admitted_pv,
        )
        if not pre_spawn_ok:
            logger.warning(f"Guarded pre-spawn CAS/validation failed for intent {intent.intent_id}")
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message="PRE_SPAWN_VALIDATION_FAILED",
            )
            return False

        # Fetch persisted attempt to use genuine attempt_seq
        persisted_attempt = self.store.get_attempt(updated_intent.attempt_id)
        att_seq = persisted_attempt.attempt_seq if persisted_attempt else 1

        # Step 4: Prepare execution request
        payload = updated_intent.payload or {}
        req = AdapterExecutionRequest(
            tenant_id=updated_intent.tenant_id,
            project_id=updated_intent.project_id,
            issue_id=updated_intent.issue_id,
            task_id=updated_intent.task_id,
            attempt_id=updated_intent.attempt_id,
            attempt_seq=att_seq,
            fencing_token=assigned_fencing,
            runtime_type=updated_intent.adapter_type,
            prompt=payload.get("prompt", ""),
            workspace_path=payload.get("workspace_path", ""),
            path_whitelist=payload.get("path_whitelist", []),
            budget_token_limit=payload.get("budget_token_limit", 10_000),
            timeout_seconds=self.execution_timeout_s,
        )

        cursor_seq = 0
        cursor_lock = threading.Lock()
        execution_stop = threading.Event()
        heartbeat_failed = threading.Event()

        def emit_event(ev_type: str, ev_data: Dict[str, Any]) -> None:
            nonlocal cursor_seq
            if execution_stop.is_set() or self._stop_requested.is_set():
                logger.warning(f"Quarantining late run event '{ev_type}' for run {run_id} after stop requested or deadline expired")
                return
            with cursor_lock:
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

        # Step 5: Start active background heartbeat renewal thread
        # Capture context state for thread execution
        from mas.pm.coordinator import is_trusted_coord_admin, trusted_coordinator_admin_scope
        from mas.tenancy import current_binding, _binding
        current_admin = is_trusted_coord_admin()
        curr_b = current_binding()

        def heartbeat_loop():
            with trusted_coordinator_admin_scope(current_admin):
                b_tok = _binding.set(curr_b)
                try:
                    while not execution_stop.is_set() and not self._stop_requested.is_set():
                        # Use interruptible Event.wait rather than time.sleep
                        interrupted = execution_stop.wait(timeout=self.heartbeat_interval_s)
                        if interrupted or execution_stop.is_set() or self._stop_requested.is_set():
                            break
                        try:
                            hb_ok = self.store.heartbeat_intent(
                                intent_id=intent.intent_id,
                                worker_id=self.worker_id,
                                assigned_fencing_token=assigned_fencing,
                                now_epoch=time.time(),
                                lease_timeout_s=self.lease_timeout_s,
                            )
                            if not hb_ok:
                                logger.warning(f"Heartbeat lost or rejected for intent {intent.intent_id}")
                                heartbeat_failed.set()
                                break
                        except Exception as hb_err:
                            logger.warning(f"Heartbeat exception for intent {intent.intent_id}: {hb_err}")
                            heartbeat_failed.set()
                            break
                finally:
                    _binding.reset(b_tok)

        hb_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        hb_thread.start()

        # Step 6: Supervised execution with monotonic deadline latching & cancellation
        execution_result: Optional[AdapterExecutionResult] = None
        execution_exception: Optional[Exception] = None

        def run_adapter():
            nonlocal execution_result, execution_exception
            with trusted_coordinator_admin_scope(current_admin):
                b_tok = _binding.set(curr_b)
                try:
                    execution_result = self.adapter.execute(
                        req,
                        run_id=run_id,
                        emit_event=emit_event,
                        stop_event=self._stop_requested,
                    )
                except Exception as ex:
                    execution_exception = ex
                finally:
                    _binding.reset(b_tok)

        exec_thread = threading.Thread(target=run_adapter, daemon=True)
        exec_thread.start()

        deadline_epoch = time.monotonic() + self.execution_timeout_s
        timed_out = False

        # Monotonic supervision loop with bounded polling
        while exec_thread.is_alive():
            now_mono = time.monotonic()
            if now_mono >= deadline_epoch:
                timed_out = True
                break
            if self._stop_requested.is_set() or heartbeat_failed.is_set():
                break
            step_wait = min(0.05, max(0.001, deadline_epoch - now_mono))
            exec_thread.join(timeout=step_wait)

        if not timed_out and (time.monotonic() >= deadline_epoch or exec_thread.is_alive()):
            timed_out = True

        # Stop heartbeat thread and quarantine further activity
        execution_stop.set()
        hb_thread.join(timeout=1.0)

        # Case A: Monotonic deadline expiration latched
        if timed_out:
            logger.error(f"Execution timed out on run {run_id} after {self.execution_timeout_s}s (deadline latched)")
            self._stop_requested.set()
            # Enforce execution boundary termination: wait for adapter within cleanup deadline
            exec_thread.join(timeout=self.cleanup_timeout_s)
            terminated_within_boundary = not exec_thread.is_alive()
            if not terminated_within_boundary:
                logger.error(
                    f"Adapter execution survived stop signal on run {run_id} beyond cleanup deadline {self.cleanup_timeout_s}s; "
                    f"quarantining thread and preserving budget hold"
                )
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message=f"EXECUTION_TIMEOUT_{self.execution_timeout_s}S" + ("" if terminated_within_boundary else "_SURVIVED_CLEANUP_DEADLINE"),
            )
            return True

        # Case B: In-flight worker stop requested
        if self._stop_requested.is_set():
            logger.warning(f"Execution interrupted by worker stop request on run {run_id}")
            exec_thread.join(timeout=self.cleanup_timeout_s)
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message="ADAPTER_STATUS_CANCELED",
            )
            return True

        # Case C: Heartbeat authority lost mid-flight
        if heartbeat_failed.is_set():
            logger.error(f"Heartbeat authority lost during execution of run {run_id}")
            self._stop_requested.set()
            exec_thread.join(timeout=self.cleanup_timeout_s)
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message="HEARTBEAT_AUTHORITY_LOST",
            )
            return True

        # Case D: Execution crashed or threw an exception
        if execution_exception is not None:
            logger.error(f"Execution crashed on run {run_id}: {execution_exception}")
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message=f"CRASH: {execution_exception}",
            )
            return True

        # Step 7: Strict Validation of Adapter Execution Result
        result = execution_result
        if not result:
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message="NULL_ADAPTER_RESULT",
            )
            return True

        # 1. Identity binding check: attempt_id and run_id must match request
        if result.attempt_id != updated_intent.attempt_id or result.run_id != run_id:
            logger.error(
                f"Identity mismatch in adapter result: expected attempt={updated_intent.attempt_id}, run={run_id}; "
                f"got attempt={result.attempt_id}, run={result.run_id}"
            )
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message=f"IDENTITY_MISMATCH: attempt={result.attempt_id}, run={result.run_id}",
            )
            return True

        # 2. Measured usage check: tokens_billed must be a non-negative integer
        if result.tokens_billed is None or not isinstance(result.tokens_billed, int) or isinstance(result.tokens_billed, bool) or result.tokens_billed < 0:
            logger.error(f"Missing or invalid measured usage: tokens_billed={result.tokens_billed}")
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message=f"INVALID_USAGE_MEASUREMENT: tokens_billed={result.tokens_billed}",
            )
            return True

        # 3. Status consistency: exit_code must not be None
        if result.exit_code is None or not isinstance(result.exit_code, int) or isinstance(result.exit_code, bool):
            logger.error(f"Missing exit_code in adapter result: exit_code={result.exit_code}")
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message=f"MISSING_EXIT_CODE: exit_code={result.exit_code}",
            )
            return True

        # 4. Strict Result Schema and Consistency (Finding 1)
        # Allowed conclusive completion statuses are strictly SUCCEEDED or FAILED
        if result.status not in ("SUCCEEDED", "FAILED"):
            logger.warning(f"Adapter returned non-conclusive status '{result.status}' on run {run_id}")
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message=f"ADAPTER_STATUS_{result.status}",
            )
            return True

        if result.status == "SUCCEEDED":
            if result.exit_code != 0:
                logger.error(f"Contradictory result: status SUCCEEDED with non-zero exit_code={result.exit_code}")
                self.store.record_execution_interrupted(
                    intent_id=intent.intent_id,
                    worker_id=self.worker_id,
                    assigned_fencing_token=assigned_fencing,
                    error_message=f"CONTRADICTORY_RESULT: SUCCEEDED requires exit_code==0, got {result.exit_code}",
                )
                return True
            if not result.candidate_commit_sha or not result.candidate_commit_sha.strip():
                logger.error("Contradictory result: status SUCCEEDED missing candidate_commit_sha")
                self.store.record_execution_interrupted(
                    intent_id=intent.intent_id,
                    worker_id=self.worker_id,
                    assigned_fencing_token=assigned_fencing,
                    error_message="CONTRADICTORY_RESULT: SUCCEEDED requires candidate_commit_sha",
                )
                return True
        elif result.status == "FAILED":
            if result.exit_code == 0:
                logger.error("Contradictory result: status FAILED with exit_code=0")
                self.store.record_execution_interrupted(
                    intent_id=intent.intent_id,
                    worker_id=self.worker_id,
                    assigned_fencing_token=assigned_fencing,
                    error_message="CONTRADICTORY_RESULT: FAILED requires non-zero exit_code",
                )
                return True

        # 5. Complete intent (SUCCEEDED or FAILED) guarded by fencing generation, active lease, and policy version
        completed = self.store.complete_intent(
            intent_id=intent.intent_id,
            worker_id=self.worker_id,
            assigned_fencing_token=assigned_fencing,
            now_epoch=time.time(),
            exit_code=result.exit_code,
            candidate_commit_sha=result.candidate_commit_sha,
            tokens_spent=result.tokens_billed,
        )
        if not completed:
            logger.error(
                f"Complete intent rejected for {intent.intent_id} (stale policy version, expired lease, or changed fencing); "
                f"advancing fencing and preserving hold"
            )
            self.store.record_execution_interrupted(
                intent_id=intent.intent_id,
                worker_id=self.worker_id,
                assigned_fencing_token=assigned_fencing,
                error_message="COMPLETION_REJECTED_STALE_POLICY_OR_LEASE",
            )
            return False
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
            if self._stop_requested.is_set():
                break
            if self.process_one_intent(intent):
                processed += 1
        return processed

    def start_bounded(self, max_cycles: int = 10) -> int:
        """Runs the worker for a bounded number of polling iterations."""
        self._running = True
        self._stop_requested.clear()
        total_processed = 0
        for _ in range(max_cycles):
            if not self._running or self._stop_requested.is_set():
                break
            count = self.run_one_polling_cycle()
            total_processed += count
            if count == 0:
                time.sleep(self.poll_interval_s * (0.8 + 0.4 * random.random()))
        return total_processed

    def stop(self) -> None:
        """Signals worker to halt polling and cancel in-flight execution."""
        self._running = False
        self._stop_requested.set()
