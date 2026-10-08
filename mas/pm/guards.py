"""
mas.pm.guards: Transition guards and policy enforcement for MAS-PM.
Enforces:
- Separation of Builder and Judge
- Strict Little's Law WIP limits
- Scope jail path normalization and traversal prevention
- Cryptographic evidence SHA-256 verification
- Multi-perspective judicial verdict assertions
- Finite reflexion and token circuit breakers
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Optional

from mas.pm.db import PMDatabase
from mas.pm.models import (
    CriticVerdictType,
    EvidenceType,
    Issue,
    IssueState,
)


class PMGuardError(Exception):
    """Base class for PM guard violations."""
    pass


class SeparationOfDutiesError(PMGuardError):
    """Raised when an author agent attempts to review or approve its own work."""
    pass


class WIPLimitExceededError(PMGuardError):
    """Raised when transitioning into a column that has reached its WIP capacity."""
    pass


class ScopeJailViolationError(PMGuardError):
    """Raised when task boundaries are missing or attempt directory traversal escapes."""
    pass


class UnshapedTaskError(PMGuardError):
    """Raised when task lacks concrete appetite or problem statement."""
    pass


class UnverifiedWorkError(PMGuardError):
    """Raised when required empirical evidence (tests, git commits, hashes) is missing or invalid."""
    pass


class CircuitBreakerTrippedError(PMGuardError):
    """Raised when reflexion count or token expenditure exceeds appetite limits."""
    pass


# Default Column WIP Limits (governed by Little's Law)
COLUMN_WIP_LIMITS = {
    IssueState.IN_PROGRESS.value: 4,
    IssueState.VERIFICATION.value: 2,
    IssueState.JUDICIAL_REVIEW.value: 2,
}
MAX_AGENT_CONCURRENT_TASKS = 1


def assert_separation_of_builder_and_judge(issue: Issue, caller_principal: str) -> None:
    """
    Enforces Separation of Builder and Judge.
    The agent assigned to implement an issue cannot review, verify, or judicially approve it.
    """
    if issue.assignee_principal and caller_principal == issue.assignee_principal:
        raise SeparationOfDutiesError(
            f"Agent '{caller_principal}' is the assignee of {issue.key} and is strictly "
            f"prohibited from evaluating, reviewing, or approving its own work."
        )


def validate_appetite(issue: Issue) -> None:
    """Validates that a task has a defined appetite before leaving BACKLOG."""
    if issue.appetite_tokens <= 0:
        raise UnshapedTaskError(f"Issue {issue.key} has invalid token appetite: {issue.appetite_tokens}")
    if issue.appetite_timeout_s <= 0:
        raise UnshapedTaskError(f"Issue {issue.key} has invalid timeout appetite: {issue.appetite_timeout_s}")


def validate_scope_jail(issue: Issue, workspace_root: Optional[Path] = None) -> None:
    """
    Validates that a task has explicit scope boundaries.
    Enforces Condition 3 of Adversarial Review: resolves paths and prevents traversal escapes.
    """
    if not issue.path_whitelist:
        raise ScopeJailViolationError(
            f"Issue {issue.key} lacks a path_whitelist. All tasks entering STAGED must be scope-jailed."
        )

    root = (workspace_root or Path.cwd()).resolve()
    for pattern in issue.path_whitelist:
        if ".." in pattern:
            # Check resolved path
            clean_path = (root / pattern.replace("*", "")).resolve()
            if not clean_path.is_relative_to(root):
                raise ScopeJailViolationError(
                    f"Scope jail violation in {issue.key}: pattern '{pattern}' escapes workspace boundary."
                )


def validate_wip_limit(
    db: PMDatabase,
    project_id: str,
    target_state: str,
    assignee: Optional[str] = None,
) -> None:
    """
    Validates Little's Law WIP capacity before state transition commits.
    """
    limit = COLUMN_WIP_LIMITS.get(target_state)
    if limit is not None:
        current_count = db.count_issues_in_state(project_id, target_state)
        if current_count >= limit:
            raise WIPLimitExceededError(
                f"Column WIP limit exceeded for state '{target_state}' "
                f"[Current: {current_count}, Limit: {limit}]. Flow throttled per Little's Law."
            )

    if target_state == IssueState.IN_PROGRESS.value and assignee:
        active_for_agent = db.count_agent_active_issues(assignee)
        if active_for_agent >= MAX_AGENT_CONCURRENT_TASKS:
            raise WIPLimitExceededError(
                f"Agent concurrency limit exceeded: '{assignee}' already has {active_for_agent} "
                f"active task in progress (Max: {MAX_AGENT_CONCURRENT_TASKS})."
            )


def validate_evidence(db: PMDatabase, issue: Issue, workspace_root: Optional[Path] = None) -> None:
    """
    Validates empirical evidence before transition to VERIFICATION.
    Enforces Condition 2 of Adversarial Review: dynamically verifies real SHA-256 hashes if files exist.
    """
    links = db.get_evidence_links(issue.id)
    if not links:
        raise UnverifiedWorkError(f"Issue {issue.key} has no attached evidence. Cannot transition to VERIFICATION.")

    has_git = any(lnk.evidence_type == EvidenceType.GIT_COMMIT for lnk in links)
    has_test = any(lnk.evidence_type == EvidenceType.TEST_RUN_LOG for lnk in links)

    if not has_git:
        raise UnverifiedWorkError(f"Issue {issue.key} lacks mandatory GIT_COMMIT evidence.")
    if not has_test:
        raise UnverifiedWorkError(f"Issue {issue.key} lacks mandatory TEST_RUN_LOG evidence.")

    # Check test exit code in payload
    for link in links:
        if link.evidence_type == EvidenceType.TEST_RUN_LOG:
            exit_code = link.payload.get("exit_code")
            if exit_code != 0:
                raise UnverifiedWorkError(
                    f"Issue {issue.key} test run evidence indicates failure (exit_code={exit_code})."
                )

        # Hash verification on local artifacts if reachable
        if link.uri.startswith("file://") or (not link.uri.startswith("http") and not link.uri.startswith("git:")):
            clean_uri = link.uri.replace("file://", "")
            file_path = Path(clean_uri)
            if file_path.is_file():
                calculated_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
                if calculated_hash.lower() != link.content_hash.lower():
                    raise UnverifiedWorkError(
                        f"Evidence integrity mismatch for {clean_uri}: "
                        f"Expected hash {link.content_hash}, calculated {calculated_hash}."
                    )


def validate_critic_verdicts(db: PMDatabase, issue: Issue, required_roles: List[str]) -> None:
    """
    Validates that required independent critic roles have issued unanimous PASS verdicts.
    """
    verdicts = db.get_verdicts(issue.id)
    roles_passed = set()

    for v in verdicts:
        if v.verdict == CriticVerdictType.HARD_FAIL:
            raise UnverifiedWorkError(
                f"Issue {issue.key} received HARD_FAIL verdict from {v.reviewer_principal}: {v.findings}"
            )
        if v.verdict == CriticVerdictType.REJECT_REWORK:
            raise UnverifiedWorkError(
                f"Issue {issue.key} received REJECT_REWORK verdict from {v.reviewer_principal}: {v.findings}"
            )
        if v.verdict == CriticVerdictType.PASS:
            roles_passed.add(v.reviewer_principal)

    missing = [role for role in required_roles if role not in roles_passed]
    if missing:
        raise UnverifiedWorkError(
            f"Issue {issue.key} is missing required PASS verdicts from independent critics: {missing}"
        )


def check_circuit_breaker(issue: Issue) -> None:
    """
    Checks if an issue has exceeded its finite reflexion attempts or token appetite.
    """
    if issue.reflexion_attempts >= 3:
        raise CircuitBreakerTrippedError(
            f"Circuit breaker tripped on {issue.key}: Reflexion attempts reached cap of 3. "
            f"Halting execution to prevent infinite loop / thrash."
        )
    if issue.tokens_spent >= issue.appetite_tokens:
        raise CircuitBreakerTrippedError(
            f"Circuit breaker tripped on {issue.key}: Token expenditure ({issue.tokens_spent}) "
            f"exceeded appetite quota ({issue.appetite_tokens})."
        )
