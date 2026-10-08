"""
mas.pm.fsm: Finite State Machine (FSM) engine for issue lifecycles in MAS-PM.
Enforces transition rules, atomic execution, and programmatic guard evaluation.
"""

from __future__ import annotations

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

    def can_transition(self, current_state: IssueState, target_state: IssueState) -> bool:
        """Returns True if the transition graph contains the directed edge."""
        allowed = ALLOWED_TRANSITIONS.get(current_state, set())
        return target_state in allowed

    def transition(
        self,
        issue_id_or_key: str,
        target_state: IssueState | str,
        caller_principal: str,
        reason: str = "",
        required_critics_stage4: Optional[List[str]] = None,
        required_critics_stage5: Optional[List[str]] = None,
    ) -> Issue:
        """
        Executes an atomic state transition with full guard evaluation.
        Satisfies Condition 1 of Adversarial Review: runs inside atomic transaction.
        """
        if isinstance(target_state, str):
            target_state = IssueState(target_state)

        stage4_critics = required_critics_stage4 or ["qa_critic", "adversarial_red_team"]
        stage5_critics = required_critics_stage5 or ["chief_architect"]

        # Fetch issue first
        issue = self.db.get_issue(issue_id_or_key)
        if not issue:
            raise ValueError(f"Issue '{issue_id_or_key}' not found.")

        current = issue.current_state

        if current == target_state:
            return issue  # No-op idempotent

        if not self.can_transition(current, target_state):
            raise InvalidStateTransitionError(
                f"Illegal transition from '{current.value}' to '{target_state.value}' for issue {issue.key}."
            )

        # Evaluate Guards based on transition edge
        increment_reflexion = False

        if current == IssueState.BACKLOG and target_state == IssueState.REFINED:
            validate_appetite(issue)

        elif current == IssueState.REFINED and target_state == IssueState.STAGED:
            validate_scope_jail(issue)

        elif current == IssueState.STAGED and target_state == IssueState.IN_PROGRESS:
            check_circuit_breaker(issue)
            validate_wip_limit(self.db, issue.project_id, target_state.value, issue.assignee_principal)

        elif current == IssueState.IN_PROGRESS and target_state == IssueState.VERIFICATION:
            validate_evidence(self.db, issue)
            validate_wip_limit(self.db, issue.project_id, target_state.value)

        elif current == IssueState.VERIFICATION and target_state == IssueState.JUDICIAL_REVIEW:
            assert_separation_of_builder_and_judge(issue, caller_principal)
            validate_critic_verdicts(self.db, issue, stage4_critics)
            validate_wip_limit(self.db, issue.project_id, target_state.value)

        elif current == IssueState.JUDICIAL_REVIEW and target_state == IssueState.DONE:
            assert_separation_of_builder_and_judge(issue, caller_principal)
            validate_critic_verdicts(self.db, issue, stage5_critics)

        elif target_state == IssueState.REJECTED_REWORK:
            assert_separation_of_builder_and_judge(issue, caller_principal)
            increment_reflexion = True

        elif current == IssueState.REJECTED_REWORK and target_state == IssueState.IN_PROGRESS:
            check_circuit_breaker(issue)
            validate_wip_limit(self.db, issue.project_id, target_state.value, issue.assignee_principal)

        # Commit update to DB
        self.db.update_issue_state(
            issue_id=issue.id,
            new_state=target_state.value,
            triggered_by=caller_principal,
            reason=reason,
            increment_reflexion=increment_reflexion,
        )

        updated = self.db.get_issue(issue.id)
        assert updated is not None
        return updated
