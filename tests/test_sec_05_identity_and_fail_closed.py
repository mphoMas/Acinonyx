"""
Regression tests for SEC-05:
- Close identity and fail-open verification defects
- Rejects unverified principals and unauthenticated caller-supplied identities
- Rejects invalid or unreadable Git changesets in commit scope verification
"""
import subprocess
from pathlib import Path
import pytest

from mas.security import ExecutionContext, validate_reviewer_authorization
from mas.pm.db import PMDatabase
from mas.pm.fsm import FSMEngine
from mas.pm.guards import ScopeJailViolationError, validate_commit_scope
from mas.pm.models import Issue, IssueState, Project


def test_sec_05_unverified_principal_rejected():
    """Verify that calling resolve_authenticated_principal outside ExecutionContext raises PermissionError."""
    # Ensure no context is active
    ExecutionContext.set_current_principal(None)

    # Calling with no claimed principal must fail closed
    with pytest.raises(PermissionError) as exc_info:
        ExecutionContext.resolve_authenticated_principal()
    assert "Unauthenticated operation" in str(exc_info.value)

    # Calling with a claimed principal when unauthenticated MUST ALSO fail closed (no spoofing)
    with pytest.raises(PermissionError) as exc_info:
        ExecutionContext.resolve_authenticated_principal(claimed_principal="chief_architect")
    assert "Unauthenticated operation" in str(exc_info.value)


def test_sec_05_fsm_rejects_unauthenticated_transitions(tmp_path):
    """Verify that FSM transition rejects unauthenticated callers even if caller_principal is passed."""
    db = PMDatabase(tmp_path / "pm_sec05.db")
    proj = db.create_project(Project(id="p1", key="SEC", name="Security Project"))
    db.create_issue(
        Issue(
            id="i1",
            project_id=proj.id,
            key="SEC-100",
            title="Unauthenticated Transition Test",
            current_state=IssueState.BACKLOG,
            appetite_tokens=20000,
            appetite_timeout_s=600,
        )
    )
    fsm = FSMEngine(db)

    # Ensure no context
    ExecutionContext.set_current_principal(None)

    # Attempt transition without active execution context must raise PermissionError
    with pytest.raises(PermissionError) as exc_info:
        fsm.transition("SEC-100", IssueState.REFINED, caller_principal="product_lead")
    assert "Unauthenticated operation" in str(exc_info.value)


def test_sec_05_impersonation_within_authenticated_context():
    """Verify that caller cannot claim identity different from authenticated principal."""
    with ExecutionContext.scope("security_sre"):
        # Matches authenticated principal
        assert ExecutionContext.resolve_authenticated_principal("security_sre") == "security_sre"
        assert ExecutionContext.resolve_authenticated_principal() == "security_sre"

        # Mismatch raises ImpersonationAttemptError
        with pytest.raises(PermissionError) as exc_info:
            ExecutionContext.resolve_authenticated_principal("adversarial_red_team")
        assert "ImpersonationAttemptError" in str(exc_info.value)


def test_sec_05_reviewer_authorization_verification():
    """Verify validate_reviewer_authorization checks separation of duties and reviewer identity."""
    # Author cannot review
    with pytest.raises(PermissionError) as exc_info:
        validate_reviewer_authorization("SEC-100", "security_sre", "security_sre")
    assert "Separation of duties violation" in str(exc_info.value)

    # Missing reviewer
    with pytest.raises(PermissionError) as exc_info:
        validate_reviewer_authorization("SEC-100", "security_sre", "")
    assert "missing reviewer principal" in str(exc_info.value)

    # Authenticated principal mismatch
    with pytest.raises(PermissionError) as exc_info:
        validate_reviewer_authorization(
            "SEC-100",
            author_principal="security_sre",
            reviewer_principal="adversarial_red_team",
            authenticated_principal="backend_engineer",
        )
    assert "UnauthorizedReviewerError" in str(exc_info.value)

    # Valid authorization
    validate_reviewer_authorization(
        "SEC-100",
        author_principal="security_sre",
        reviewer_principal="adversarial_red_team",
        authenticated_principal="adversarial_red_team",
    )


def test_sec_05_validate_commit_scope_rejects_invalid_commit():
    """Verify that validate_commit_scope fails closed on non-existent or malformed commit SHAs."""
    issue = Issue(
        id="i1",
        project_id="p1",
        key="SEC-100",
        title="Commit Scope Test",
        current_state=IssueState.IN_PROGRESS,
        path_whitelist=["mas/security.py"],
        forbidden_paths=[".env", "**/secrets/**"],
    )

    # Non-existent commit SHA
    with pytest.raises(ScopeJailViolationError) as exc_info:
        validate_commit_scope(issue, "0000000000000000000000000000000000000000")
    assert "failed to inspect commit" in str(exc_info.value)

    # Empty commit SHA
    with pytest.raises(ScopeJailViolationError) as exc_info:
        validate_commit_scope(issue, "")
    assert "missing or empty commit SHA" in str(exc_info.value)

    # Malformed / unreadable commit SHA
    with pytest.raises(ScopeJailViolationError) as exc_info:
        validate_commit_scope(issue, "not-a-valid-sha")
    assert "failed to inspect commit" in str(exc_info.value)


def test_sec_05_validate_commit_scope_with_real_commit():
    """Verify that validate_commit_scope permits legitimate in-scope commits and blocks forbidden paths."""
    head_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()

    # Issue with broad whitelist covering everything
    valid_issue = Issue(
        id="i1",
        project_id="p1",
        key="SEC-100",
        title="Valid Commit Test",
        current_state=IssueState.IN_PROGRESS,
        path_whitelist=["*"],
        forbidden_paths=[".env", "**/secrets/**"],
    )
    # Should not raise
    validate_commit_scope(valid_issue, head_sha)

    # Issue with restrictive whitelist that doesn't match HEAD commit changes
    restrictive_issue = Issue(
        id="i2",
        project_id="p1",
        key="SEC-101",
        title="Restrictive Whitelist Test",
        current_state=IssueState.IN_PROGRESS,
        path_whitelist=["nonexistent/dir/*"],
        forbidden_paths=[],
    )
    # If HEAD changed files, restrictive whitelist must catch it
    res = subprocess.run(
        ["git", "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", head_sha],
        capture_output=True,
        text=True,
    )
    if res.stdout.strip():
        with pytest.raises(ScopeJailViolationError):
            validate_commit_scope(restrictive_issue, head_sha)
