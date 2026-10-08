"""
mas.pm.fsm: Finite State Machine (FSM) engine for issue lifecycles in MAS-PM.
Enforces transition rules, atomic execution, and programmatic guard evaluation.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Set

from mas.pm.db import PMDatabase
from mas.pm.guards import (
    PMGuardError,
    assert_separation_of_builder_and_judge,
    check_circuit_breaker,
    validate_appetite,
    validate_critic_verdicts,
    validate_evidence,
    validate_scope_jail,
    validate_wip_limit,
)
from mas.pm.models import Issue, IssueState
from mas.security import ExecutionContext


class InvalidStateTransitionError(PMGuardError):
    """Raised when an illegal edge is traversed in the FSM graph."""
    pass


# Directed Transition Graph
ALLOWED_TRANSITIONS: Dict[IssueState, Set[IssueState]] = {
    IssueState.BACKLOG: {IssueState.REFINED, IssueState.BLOCKED},
    IssueState.REFINED: {IssueState.STAGED, IssueState.BACKLOG, IssueState.BLOCKED},
    IssueState.STAGED: {IssueState.IN_PROGRESS, IssueState.REFINED, IssueState.BLOCKED},
    IssueState.IN_PROGRESS: {IssueState.VERIFICATION, IssueState.BLOCKED, IssueState.REJECTED_REWORK},
    IssueState.VERIFICATION: {
        IssueState.JUDICIAL_REVIEW,
        IssueState.REJECTED_REWORK,
        IssueState.BLOCKED,
    },
    IssueState.JUDICIAL_REVIEW: {
        IssueState.DONE,
        IssueState.REJECTED_REWORK,
        IssueState.BLOCKED,
    },
    IssueState.REJECTED_REWORK: {IssueState.IN_PROGRESS, IssueState.BLOCKED},
    IssueState.BLOCKED: {IssueState.REFINED, IssueState.BACKLOG, IssueState.IN_PROGRESS},
    IssueState.DONE: set(),  # Terminal state
}


class FSMEngine:
    """Finite State Machine engine executing atomic guarded transitions."""

    def __init__(self, db: PMDatabase) -> None:
        self.db = db
        self._lock = threading.RLock()

    def can_transition(self, current_state: IssueState, target_state: IssueState) -> bool:
        """Returns True if the transition graph contains the directed edge."""
        allowed = ALLOWED_TRANSITIONS.get(current_state, set())
        return target_state in allowed

    def transition(
        self,
        issue_id_or_key: str,
        target_state: IssueState | str,
        caller_principal: Optional[str] = None,
        reason: str = "",
        required_critics_stage4: Optional[List[str]] = None,
        required_critics_stage5: Optional[List[str]] = None,
        enforce_git_commit: bool = True,
    ) -> Issue:
        """
        Executes an atomic state transition with full guard evaluation.
        PM-SEC-001: Resolves authenticated principal against ExecutionContext.
        PM-CON-001: Serializes check-and-set inside atomic transaction with re-entrant lock.
        PM-GOV-001: Version-tracks rework cycles on rejection.
        """
        # PM-SEC-001: Prohibit caller impersonation
        caller_principal = ExecutionContext.resolve_authenticated_principal(caller_principal)

        if isinstance(target_state, str):
            target_state = IssueState(target_state)

        stage4_critics = required_critics_stage4 or ["qa_critic", "adversarial_red_team"]
        stage5_critics = required_critics_stage5 or ["chief_architect"]

        with self._lock:
            with self.db.atomic_transaction() as conn:
                # Fetch issue inside atomic transaction
                cur = conn.execute(
                    "SELECT * FROM pm_issues WHERE id = ? OR key = ?",
                    (issue_id_or_key, issue_id_or_key.upper()),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Issue '{issue_id_or_key}' not found.")
                issue = self.db._row_to_issue(row)

                current = issue.current_state

                if current == target_state:
                    return issue  # No-op idempotent

                if not self.can_transition(current, target_state):
                    raise InvalidStateTransitionError(
                        f"Illegal transition from '{current.value}' to '{target_state.value}' for issue {issue.key}."
                    )

                # Evaluate Guards based on transition edge
                increment_reflexion = False
                increment_rework_cycle = False
                blocker_reason = None

                if current == IssueState.BACKLOG and target_state == IssueState.REFINED:
                    validate_appetite(issue)

                elif current == IssueState.REFINED and target_state == IssueState.STAGED:
                    validate_scope_jail(issue)

                elif current == IssueState.STAGED and target_state == IssueState.IN_PROGRESS:
                    check_circuit_breaker(issue)
                    validate_wip_limit(self.db, issue.project_id, target_state.value, issue.assignee_principal, conn=conn)

                elif current == IssueState.IN_PROGRESS and target_state == IssueState.VERIFICATION:
                    validate_evidence(self.db, issue, enforce_git_commit=enforce_git_commit)
                    validate_wip_limit(self.db, issue.project_id, target_state.value, conn=conn)

                elif current == IssueState.VERIFICATION and target_state == IssueState.JUDICIAL_REVIEW:
                    assert_separation_of_builder_and_judge(issue, caller_principal)
                    validate_critic_verdicts(self.db, issue, stage4_critics)
                    validate_wip_limit(self.db, issue.project_id, target_state.value, conn=conn)

                elif current == IssueState.JUDICIAL_REVIEW and target_state == IssueState.DONE:
                    assert_separation_of_builder_and_judge(issue, caller_principal)
                    validate_critic_verdicts(self.db, issue, stage5_critics)

                elif target_state == IssueState.REJECTED_REWORK:
                    assert_separation_of_builder_and_judge(issue, caller_principal)
                    increment_reflexion = True
                    increment_rework_cycle = True

                elif current == IssueState.REJECTED_REWORK and target_state == IssueState.IN_PROGRESS:
                    check_circuit_breaker(issue)
                    validate_wip_limit(self.db, issue.project_id, target_state.value, issue.assignee_principal, conn=conn)

                elif target_state == IssueState.BLOCKED:
                    blocker_reason = reason or "Transitioned to BLOCKED"

                # Commit update to DB within atomic transaction
                self.db.update_issue_state(
                    issue_id=issue.id,
                    new_state=target_state.value,
                    triggered_by=caller_principal,
                    reason=reason,
                    increment_reflexion=increment_reflexion,
                    increment_rework_cycle=increment_rework_cycle,
                    blocker_reason=blocker_reason,
                    conn=conn,
                )

        updated = self.db.get_issue(issue.id)
        assert updated is not None
        return updated
