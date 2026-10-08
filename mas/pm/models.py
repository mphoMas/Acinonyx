"""
mas.pm.models: Data models for the MAS Project Management Engine (MAS-PM).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IssueState(str, Enum):
    BACKLOG = "BACKLOG"
    REFINED = "REFINED"
    STAGED = "STAGED"
    IN_PROGRESS = "IN_PROGRESS"
    VERIFICATION = "VERIFICATION"
    JUDICIAL_REVIEW = "JUDICIAL_REVIEW"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    REJECTED_REWORK = "REJECTED_REWORK"


class IssueType(str, Enum):
    INITIATIVE = "INITIATIVE"
    EPIC = "EPIC"
    TASK = "TASK"
    SUBTASK = "SUBTASK"
    DEFECT = "DEFECT"


class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SprintState(str, Enum):
    FUTURE = "FUTURE"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class CriticVerdictType(str, Enum):
    PASS = "PASS"
    REJECT_REWORK = "REJECT_REWORK"
    HARD_FAIL = "HARD_FAIL"


class EvidenceType(str, Enum):
    GIT_COMMIT = "GIT_COMMIT"
    TEST_RUN_LOG = "TEST_RUN_LOG"
    AST_SCAN_REPORT = "AST_SCAN_REPORT"
    SECURITY_AUDIT = "SECURITY_AUDIT"
    COVERAGE_REPORT = "COVERAGE_REPORT"
    MERKLE_ROOT = "MERKLE_ROOT"


class Project(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    key: str
    name: str
    description: str = ""
    token_budget: int = 5_000_000
    tokens_consumed: int = 0
    created_at: str = ""
    updated_at: str = ""


class ShapedTask(BaseModel):
    title: str
    problem_statement: str = ""
    appetite_tokens: int = 50_000
    appetite_timeout_s: int = 1800
    path_whitelist: List[str] = Field(default_factory=list)
    forbidden_paths: List[str] = Field(default_factory=list)
    no_gos: List[str] = Field(default_factory=list)


class Sprint(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    project_id: str
    name: str
    goal: str = ""
    state: SprintState = SprintState.FUTURE
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: str = ""


class Issue(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str
    project_id: str
    key: str
    title: str
    description: str = ""
    issue_type: IssueType = IssueType.TASK
    current_state: IssueState = IssueState.BACKLOG
    priority: PriorityLevel = PriorityLevel.MEDIUM
    sprint_id: Optional[str] = None
    parent_id: Optional[str] = None
    assignee_principal: Optional[str] = None
    appetite_tokens: int = 50_000
    appetite_timeout_s: int = 1800
    tokens_spent: int = 0
    reflexion_attempts: int = 0
    rework_cycle: int = 0
    blocker_reason: Optional[str] = None
    path_whitelist: List[str] = Field(default_factory=list)
    forbidden_paths: List[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class TransitionHistory(BaseModel):
    id: Optional[int] = None
    issue_id: str
    from_state: str
    to_state: str
    triggered_by: str
    reason: str = ""
    timestamp: str = ""


class EvidenceLink(BaseModel):
    id: str
    issue_id: str
    evidence_type: EvidenceType
    content_hash: str
    uri: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    linked_at: str = ""


class CriticVerdict(BaseModel):
    id: str
    issue_id: str
    reviewer_principal: str
    verdict: CriticVerdictType
    findings: Dict[str, Any] = Field(default_factory=dict)
    signature: str = ""
    rework_cycle: int = 0
    commit_sha: Optional[str] = None
    timestamp: str = ""


class ColumnInfo(BaseModel):
    name: str
    count: int
    wip_limit: Optional[int] = None
    is_saturated: bool = False


class BoardState(BaseModel):
    project_key: str
    columns: Dict[str, ColumnInfo]
    total_active_wip: int
    flow_health: str
    wip_saturation_pct: float
    issues_by_column: Dict[str, List[Issue]] = Field(default_factory=dict)
    sprints: List[Sprint] = Field(default_factory=list)
    active_sprint_id: Optional[str] = None


class CFDSnapshot(BaseModel):
    timestamp: str
    project_id: str
    backlog_count: int
    refined_count: int
    staged_count: int
    in_progress_count: int
    verification_count: int
    judicial_review_count: int
    done_count: int
