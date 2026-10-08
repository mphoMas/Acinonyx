"""
mas.pm.tools: MCP Tool registrations for the MAS Project Management Engine (MAS-PM).
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from mas.pm.db import DEFAULT_DB_PATH, PMDatabase
from mas.pm.fsm import FSMEngine
from mas.pm.metrics import FlowMetricsEngine
from mas.pm.models import (
    CriticVerdict,
    CriticVerdictType,
    EvidenceLink,
    EvidenceType,
    Issue,
    IssueState,
    IssueType,
    PriorityLevel,
    Project,
)


_GLOBAL_DB: Optional[PMDatabase] = None


def get_pm_db(db_path: Optional[str] = None) -> PMDatabase:
    """Singleton/accessor for PM database."""
    global _GLOBAL_DB
    if _GLOBAL_DB is None or db_path:
        _GLOBAL_DB = PMDatabase(db_path or DEFAULT_DB_PATH)
    return _GLOBAL_DB


def pm_create_project(
    key: str,
    name: str,
    description: str = "",
    token_budget: int = 5_000_000,
    db: Optional[PMDatabase] = None,
) -> Dict[str, Any]:
    """Creates a new project container with financial token quotas."""
    database = db or get_pm_db()
    existing = database.get_project_by_key(key)
    if existing:
        return {"status": "EXISTS", "project_key": existing.key, "project_id": existing.id}

    proj = Project(
        id=str(uuid.uuid4()),
        key=key.upper(),
        name=name,
        description=description,
        token_budget=token_budget,
    )
    saved = database.create_project(proj)
    return {"status": "CREATED", "project_key": saved.key, "project_id": saved.id}


def pm_create_issue(
    project_key: str,
    title: str,
    description: str = "",
    issue_type: str = "TASK",
    priority: str = "MEDIUM",
    sprint_id: Optional[str] = None,
    parent_key: Optional[str] = None,
    assignee_principal: Optional[str] = None,
    appetite_tokens: int = 50_000,
    appetite_timeout_s: int = 1800,
    path_whitelist: Optional[List[str]] = None,
    forbidden_paths: Optional[List[str]] = None,
    db: Optional[PMDatabase] = None,
) -> Dict[str, Any]:
    """Registers a new issue in the BACKLOG."""
    database = db or get_pm_db()
    project = database.get_project_by_key(project_key)
    if not project:
        raise ValueError(f"Project '{project_key}' does not exist.")

    parent_id = None
    if parent_key:
        parent = database.get_issue(parent_key)
        if parent:
            parent_id = parent.id

    issue_key = database.next_issue_key(project.key)
    issue = Issue(
        id=str(uuid.uuid4()),
        project_id=project.id,
        key=issue_key,
        title=title,
        description=description,
        issue_type=IssueType(issue_type.upper()),
        current_state=IssueState.BACKLOG,
        priority=PriorityLevel(priority.upper()) if priority else PriorityLevel.MEDIUM,
        sprint_id=sprint_id,
        parent_id=parent_id,
        assignee_principal=assignee_principal,
        appetite_tokens=appetite_tokens,
        appetite_timeout_s=appetite_timeout_s,
        path_whitelist=path_whitelist or [],
        forbidden_paths=forbidden_paths or [],
    )
    saved = database.create_issue(issue)
    return {
        "status": "CREATED",
        "issue_key": saved.key,
        "issue_id": saved.id,
        "state": saved.current_state.value,
        "priority": saved.priority.value,
        "sprint_id": saved.sprint_id,
    }


def pm_transition_issue(
    issue_key: str,
    target_state: str,
    caller_principal: str,
    reason: str = "",
    db: Optional[PMDatabase] = None,
) -> Dict[str, Any]:
    """Transitions an issue through the FSM with transition guard validation."""
    database = db or get_pm_db()
    fsm = FSMEngine(database)
    updated = fsm.transition(
        issue_id_or_key=issue_key,
        target_state=target_state,
        caller_principal=caller_principal,
        reason=reason,
    )
    return {
        "status": "TRANSITIONED",
        "issue_key": updated.key,
        "current_state": updated.current_state.value,
        "reflexion_attempts": updated.reflexion_attempts,
    }


def pm_attach_evidence(
    issue_key: str,
    evidence_type: str,
    content_hash: str,
    uri: str,
    payload: Optional[Dict[str, Any]] = None,
    db: Optional[PMDatabase] = None,
) -> Dict[str, Any]:
    """Binds empirical evidence (git commit, test logs, AST reports) to an issue."""
    database = db or get_pm_db()
    issue = database.get_issue(issue_key)
    if not issue:
        raise ValueError(f"Issue '{issue_key}' does not exist.")

    evidence = EvidenceLink(
        id=str(uuid.uuid4()),
        issue_id=issue.id,
        evidence_type=EvidenceType(evidence_type.upper()),
        content_hash=content_hash,
        uri=uri,
        payload=payload or {},
    )
    saved = database.attach_evidence(evidence)
    return {
        "status": "ATTACHED",
        "evidence_id": saved.id,
        "issue_key": issue.key,
        "evidence_type": saved.evidence_type.value,
    }


def pm_cast_verdict(
    issue_key: str,
    reviewer_principal: str,
    verdict: str,
    findings: Optional[Dict[str, Any]] = None,
    signature: str = "",
    db: Optional[PMDatabase] = None,
) -> Dict[str, Any]:
    """Casts an independent critic verdict on an issue under review."""
    database = db or get_pm_db()
    issue = database.get_issue(issue_key)
    if not issue:
        raise ValueError(f"Issue '{issue_key}' does not exist.")

    critic_verdict = CriticVerdict(
        id=str(uuid.uuid4()),
        issue_id=issue.id,
        reviewer_principal=reviewer_principal,
        verdict=CriticVerdictType(verdict.upper()),
        findings=findings or {},
        signature=signature or f"sig_{reviewer_principal}_{issue.key}",
    )
    saved = database.record_verdict(critic_verdict)
    return {
        "status": "RECORDED",
        "verdict_id": saved.id,
        "issue_key": issue.key,
        "verdict": saved.verdict.value,
        "reviewer": saved.reviewer_principal,
    }


def pm_get_board_state(project_key: str, db: Optional[PMDatabase] = None) -> Dict[str, Any]:
    """Returns the visual board state, column counts, and Little's Law WIP saturation."""
    database = db or get_pm_db()
    metrics = FlowMetricsEngine(database)
    state = metrics.get_board_state(project_key)
    return state.model_dump()


def pm_get_issue(issue_key: str, db: Optional[PMDatabase] = None) -> Dict[str, Any]:
    """Retrieves full details, evidence, and verdicts for an issue."""
    database = db or get_pm_db()
    issue = database.get_issue(issue_key)
    if not issue:
        return {"error": f"Issue '{issue_key}' not found"}

    evidence = database.get_evidence_links(issue.id)
    verdicts = database.get_verdicts(issue.id)
    return {
        "issue": issue.model_dump(),
        "evidence": [e.model_dump() for e in evidence],
        "verdicts": [v.model_dump() for v in verdicts],
    }


def pm_list_issues(
    project_key: str,
    state: Optional[str] = None,
    db: Optional[PMDatabase] = None,
) -> List[Dict[str, Any]]:
    """Lists issues in a project optionally filtered by state."""
    database = db or get_pm_db()
    project = database.get_project_by_key(project_key)
    if not project:
        raise ValueError(f"Project '{project_key}' not found.")

    issues = database.list_issues(project_id=project.id, state=state)
    return [i.model_dump() for i in issues]


def register_pm_tools(registry: Any, db: Optional[PMDatabase] = None) -> None:
    """Registers the complete MAS-PM tool suite into the MCP tool registry."""
    # 1. pm_create_project
    registry.register_tool(
        name="pm_create_project",
        description="Creates a top-level project container with financial token quotas.",
        input_schema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "3-5 letter project key (e.g. CORE)"},
                "name": {"type": "string", "description": "Full project name"},
                "description": {"type": "string", "description": "Project overview", "default": ""},
                "token_budget": {"type": "integer", "description": "Total token budget", "default": 5000000},
            },
            "required": ["key", "name"],
        },
        handler=lambda key, name, description="", token_budget=5000000: pm_create_project(
            key, name, description, token_budget, db=db
        ),
    )

    # 2. pm_create_issue
    registry.register_tool(
        name="pm_create_issue",
        description="Registers a new issue in the BACKLOG.",
        input_schema={
            "type": "object",
            "properties": {
                "project_key": {"type": "string", "description": "Project key (e.g. CORE)"},
                "title": {"type": "string", "description": "Issue title"},
                "description": {"type": "string", "description": "Detailed description", "default": ""},
                "issue_type": {"type": "string", "description": "INITIATIVE, EPIC, TASK, SUBTASK, DEFECT", "default": "TASK"},
                "parent_key": {"type": "string", "description": "Optional parent issue key", "default": None},
                "assignee_principal": {"type": "string", "description": "Assigned agent principal name", "default": None},
                "appetite_tokens": {"type": "integer", "description": "Token budget appetite", "default": 50000},
                "appetite_timeout_s": {"type": "integer", "description": "Timeout seconds appetite", "default": 1800},
                "path_whitelist": {"type": "array", "items": {"type": "string"}, "description": "Permitted file globs", "default": []},
                "forbidden_paths": {"type": "array", "items": {"type": "string"}, "description": "Forbidden file globs", "default": []},
            },
            "required": ["project_key", "title"],
        },
        handler=lambda project_key, title, description="", issue_type="TASK", parent_key=None, assignee_principal=None, appetite_tokens=50000, appetite_timeout_s=1800, path_whitelist=None, forbidden_paths=None: pm_create_issue(
            project_key=project_key,
            title=title,
            description=description,
            issue_type=issue_type,
            parent_key=parent_key,
            assignee_principal=assignee_principal,
            appetite_tokens=appetite_tokens,
            appetite_timeout_s=appetite_timeout_s,
            path_whitelist=path_whitelist,
            forbidden_paths=forbidden_paths,
            db=db,
        ),
    )

    # 3. pm_transition_issue
    registry.register_tool(
        name="pm_transition_issue",
        description="Transitions an issue through the FSM with transition guard validation.",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Issue key (e.g. CORE-1)"},
                "target_state": {"type": "string", "description": "Target FSM state"},
                "caller_principal": {"type": "string", "description": "Principal name of calling agent"},
                "reason": {"type": "string", "description": "Operational justification", "default": ""},
            },
            "required": ["issue_key", "target_state", "caller_principal"],
        },
        handler=lambda issue_key, target_state, caller_principal, reason="": pm_transition_issue(
            issue_key, target_state, caller_principal, reason, db=db
        ),
    )

    # 4. pm_attach_evidence
    registry.register_tool(
        name="pm_attach_evidence",
        description="Binds empirical evidence (git commit, test logs, AST reports) to an issue.",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Issue key"},
                "evidence_type": {"type": "string", "description": "GIT_COMMIT, TEST_RUN_LOG, AST_SCAN_REPORT, etc."},
                "content_hash": {"type": "string", "description": "SHA-256 hash of artifact"},
                "uri": {"type": "string", "description": "File path or Git commit SHA"},
                "payload": {"type": "object", "description": "Structured details (e.g. exit_code)", "default": {}},
            },
            "required": ["issue_key", "evidence_type", "content_hash", "uri"],
        },
        handler=lambda issue_key, evidence_type, content_hash, uri, payload=None: pm_attach_evidence(
            issue_key, evidence_type, content_hash, uri, payload, db=db
        ),
    )

    # 5. pm_cast_verdict
    registry.register_tool(
        name="pm_cast_verdict",
        description="Casts an independent critic verdict on an issue under review.",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Issue key"},
                "reviewer_principal": {"type": "string", "description": "Critic principal name"},
                "verdict": {"type": "string", "description": "PASS, REJECT_REWORK, HARD_FAIL"},
                "findings": {"type": "object", "description": "Findings JSON", "default": {}},
                "signature": {"type": "string", "description": "Cryptographic signature", "default": ""},
            },
            "required": ["issue_key", "reviewer_principal", "verdict"],
        },
        handler=lambda issue_key, reviewer_principal, verdict, findings=None, signature="": pm_cast_verdict(
            issue_key, reviewer_principal, verdict, findings, signature, db=db
        ),
    )

    # 6. pm_get_board_state
    registry.register_tool(
        name="pm_get_board_state",
        description="Returns the visual board state, column counts, and Little's Law WIP saturation.",
        input_schema={
            "type": "object",
            "properties": {
                "project_key": {"type": "string", "description": "Project key"},
            },
            "required": ["project_key"],
        },
        handler=lambda project_key: pm_get_board_state(project_key, db=db),
    )

    # 7. pm_get_issue
    registry.register_tool(
        name="pm_get_issue",
        description="Retrieves full details, evidence, and verdicts for an issue.",
        input_schema={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string", "description": "Issue key"},
            },
            "required": ["issue_key"],
        },
        handler=lambda issue_key: pm_get_issue(issue_key, db=db),
    )

    # 8. pm_list_issues
    registry.register_tool(
        name="pm_list_issues",
        description="Lists issues in a project optionally filtered by state.",
        input_schema={
            "type": "object",
            "properties": {
                "project_key": {"type": "string", "description": "Project key"},
                "state": {"type": "string", "description": "Optional filter state", "default": None},
            },
            "required": ["project_key"],
        },
        handler=lambda project_key, state=None: pm_list_issues(project_key, state=state, db=db),
    )
