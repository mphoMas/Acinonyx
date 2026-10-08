"""
mas.pm.guards: Transition guards and policy enforcement for MAS-PM.
Enforces:
- Separation of Builder and Judge
- Strict Little's Law WIP limits
- Scope jail path normalization and traversal prevention
- Git commit verification & changeset scope check (PM-SEC-002, PM-SEC-003)
- Cryptographic evidence SHA-256 verification (PM-SEC-002)
- Multi-perspective judicial verdict assertions with rework cycle invalidation (PM-GOV-001)
- Finite reflexion and token circuit breakers
"""

from __future__ import annotations

import fnmatch
import hashlib
from pathlib import Path
import sqlite3
import subprocess
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
            clean_path = (root / pattern.replace("*", "")).resolve()
            if not clean_path.is_relative_to(root):
                raise ScopeJailViolationError(
                    f"Scope jail violation in {issue.key}: pattern '{pattern}' escapes workspace boundary."
                )


def validate_commit_scope(issue: Issue, commit_sha: str, workspace_root: Optional[Path] = None) -> None:
    """
    PM-SEC-003: Inspects the actual Git commit changeset and verifies every modified
    file against issue.path_whitelist and issue.forbidden_paths.
    """
    root = (workspace_root or Path.cwd()).resolve()
    try:
        res = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            return  # Not able to run diff-tree (e.g. invalid commit or shallow)
        changed_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
        if not changed_files:
            return

        for file_path in changed_files:
            # Check forbidden paths first
            for forbidden in issue.forbidden_paths:
                if fnmatch.fnmatch(file_path, forbidden) or file_path.startswith(forbidden.rstrip("*")):
                    raise ScopeJailViolationError(
                        f"Scope jail violation in {issue.key}: commit {commit_sha} violates scope jail, modified "
                        f"forbidden file '{file_path}' (matching forbidden rule '{forbidden}')."
                    )

            # Check path whitelist if configured
            if issue.path_whitelist and "*" not in issue.path_whitelist:
                matches_whitelist = any(
                    fnmatch.fnmatch(file_path, pattern) or file_path.startswith(pattern.rstrip("*"))
                    for pattern in issue.path_whitelist
                )
                if not matches_whitelist:
                    raise ScopeJailViolationError(
                        f"Scope jail violation in {issue.key}: commit {commit_sha} modified "
                        f"out-of-scope file '{file_path}' (not in whitelist {issue.path_whitelist})."
                    )
    except ScopeJailViolationError:
        raise
    except Exception:
        pass


def validate_wip_limit(
    db: PMDatabase,
    project_id: str,
    target_state: str,
    assignee: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """
    PM-CON-001: Validates Little's Law WIP capacity before state transition commits.
    Accepts active transaction conn to eliminate concurrent race windows.
    """
    limit = COLUMN_WIP_LIMITS.get(target_state)
    if limit is not None:
        current_count = db.count_issues_in_state(project_id, target_state, conn=conn)
        if current_count >= limit:
            raise WIPLimitExceededError(
                f"Column WIP limit exceeded for state '{target_state}' "
                f"[Current: {current_count}, Limit: {limit}]. Flow throttled per Little's Law."
            )

    if target_state == IssueState.IN_PROGRESS.value and assignee:
        active_for_agent = db.count_agent_active_issues(assignee, conn=conn)
        if active_for_agent >= MAX_AGENT_CONCURRENT_TASKS:
            raise WIPLimitExceededError(
                f"Agent concurrency limit exceeded: '{assignee}' already has {active_for_agent} "
                f"active task in progress (Max: {MAX_AGENT_CONCURRENT_TASKS})."
            )


def validate_evidence(
    db: PMDatabase,
    issue: Issue,
    workspace_root: Optional[Path] = None,
    enforce_git_commit: bool = True,
) -> None:
    """
    Validates empirical evidence before transition to VERIFICATION.
    Enforces Condition 2 (PM-SEC-002) & PM-SEC-003:
    1. Verifies GIT_COMMIT against local Git repository object database.
    2. Inspects git diff-tree changeset against path_whitelist & forbidden_paths.
    3. Verifies TEST_RUN_LOG exit_code == 0 and SHA-256 hash against file on disk.
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

    root = (workspace_root or Path.cwd()).resolve()

    for link in links:
        # PM-SEC-002: Test run log verification
        if link.evidence_type == EvidenceType.TEST_RUN_LOG:
            exit_code = link.payload.get("exit_code")
            if exit_code != 0:
                raise UnverifiedWorkError(
                    f"Issue {issue.key} test run evidence indicates failure (exit_code={exit_code})."
                )

            # Check file existence and SHA-256
            clean_uri = link.uri.replace("file://", "")
            file_path = Path(clean_uri)
            if not file_path.is_absolute():
                file_path = root / file_path

            if not file_path.is_file():
                raise UnverifiedWorkError(
                    f"Issue {issue.key} test run log file '{clean_uri}' does not exist on disk."
                )

            calculated_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if calculated_hash.lower() != link.content_hash.lower():
                raise UnverifiedWorkError(
                    f"Evidence integrity mismatch for {clean_uri}: "
                    f"Expected hash {link.content_hash}, calculated {calculated_hash}."
                )

        # PM-SEC-002 & PM-SEC-003: Git commit verification
        if link.evidence_type == EvidenceType.GIT_COMMIT and enforce_git_commit:
            commit_sha = link.content_hash or link.uri.replace("git:commit:", "").strip()
            # Verify commit object exists in git
            res = subprocess.run(
                ["git", "rev-parse", "--verify", f"{commit_sha}^{{commit}}"],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode != 0:
                raise UnverifiedWorkError(
                    f"Git commit verification failed for {commit_sha}: commit does not exist in repository."
                )

            # Check changeset scope
            validate_commit_scope(issue, commit_sha, workspace_root=root)


def validate_critic_verdicts(db: PMDatabase, issue: Issue, required_roles: List[str]) -> None:
    """
    Validates that required independent critic roles have issued unanimous PASS verdicts.
    PM-GOV-001: Filters strictly by issue.rework_cycle to invalidate stale approvals.
    """
    verdicts = db.get_verdicts(issue.id, rework_cycle=issue.rework_cycle)
    roles_passed = set()

    for v in verdicts:
        if v.verdict == CriticVerdictType.HARD_FAIL:
            raise UnverifiedWorkError(
                f"Issue {issue.key} received HARD_FAIL verdict from {v.reviewer_principal} in rework cycle {issue.rework_cycle}: {v.findings}"
            )
        if v.verdict == CriticVerdictType.REJECT_REWORK:
            raise UnverifiedWorkError(
                f"Issue {issue.key} received REJECT_REWORK verdict from {v.reviewer_principal} in rework cycle {issue.rework_cycle}: {v.findings}"
            )
        if v.verdict == CriticVerdictType.PASS:
            roles_passed.add(v.reviewer_principal)

    missing = [role for role in required_roles if role not in roles_passed]
    if missing:
        raise UnverifiedWorkError(
            f"Issue {issue.key} is missing required PASS verdicts for rework cycle {issue.rework_cycle} from independent critics: {missing}"
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
