"""
mas.pm.models: Data models for the MAS Project Management Engine (MAS-PM).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class StagedReviewerAction(str, Enum):
    NONE = "NONE"
    REPLACE = "REPLACE"
    REMOVE = "REMOVE"


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
    task_id: Optional[str] = None
    planning_reference: Optional[str] = None
    acceptance_criteria: List[str] = Field(default_factory=list)
    proposed_delivery_owner: Optional[str] = None
    reviewer_requirement: Optional[str] = None
    proposed_budget_tokens: Optional[int] = None
    staged_acceptance_criteria: Optional[List[str]] = None
    staged_path_whitelist: Optional[List[str]] = None
    staged_reviewer_requirement: Optional[str] = None
    staged_reviewer_action: Optional[str] = None  # None | "NONE" | "REPLACE" | "REMOVE"
    policy_version: int = 1
    staged_proposal_id: Optional[str] = None
    staged_proposal_rev: Optional[int] = None
    has_pending_reconciliation: bool = False
    created_at: str = ""
    updated_at: str = ""


class ReconciliationAuditRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: Optional[int] = None
    tenant_id: str
    project_id: str
    issue_id: str
    issue_key: str
    decision: str  # "apply" | "reject"
    actor: str
    proposal_id: Optional[str] = None
    proposal_rev: Optional[int] = None
    base_policy_version: int
    resulting_policy_version: int
    before_policy: Dict[str, Any]
    after_policy: Dict[str, Any]
    evidence_invalidated_count: int = 0
    created_at: str = ""


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


class ProjectSource(BaseModel):
    model_config = ConfigDict(frozen=False)

    project_id: str
    repository_id: str
    repository_owner: str
    repository_name: str
    configured_branch: str
    root_path: str
    planning_path: str
    status: str = "active"  # "active" or "inactive"
    source_revision: Optional[str] = None
    last_successful_sync: Optional[str] = None
    last_error: Optional[str] = None
    is_stale: bool = False
    remote_project_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class TaskMapping(BaseModel):
    model_config = ConfigDict(frozen=False)

    project_id: str
    planning_reference: str
    task_id: str
    local_issue_id: str
    local_issue_key: str
    legacy_task_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class PlanTaskDefinition(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid")

    task_id: str
    planning_reference: str
    title: str
    description: str = ""
    type: IssueType = IssueType.TASK
    priority: PriorityLevel = PriorityLevel.MEDIUM
    parent_task_id: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    acceptance_criteria: List[str] = Field(default_factory=list)
    proposed_delivery_owner: Optional[str] = None
    reviewer_requirement: Optional[str] = None
    path_whitelist: List[str] = Field(default_factory=list)
    proposed_budget: Optional[Dict[str, Any]] = None
    proposed_budget_tokens: Optional[int] = Field(default=None, ge=0)

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("task_id cannot be empty")
        return clean

    @field_validator("planning_reference")
    @classmethod
    def validate_planning_ref(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("planning_reference cannot be empty")
        return clean

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("title cannot be empty")
        if len(clean) > 256:
            raise ValueError("title exceeds maximum length of 256 characters")
        return clean

    @field_validator("proposed_budget")
    @classmethod
    def validate_proposed_budget(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is not None and "tokens" in v:
            tokens_val = v["tokens"]
            if not isinstance(tokens_val, int) or tokens_val < 0:
                raise ValueError("proposed_budget['tokens'] must be a non-negative finite integer")
        return v


class PlanPublicationRequest(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid")

    schema_version: int = 1
    plan_id: str
    revision: int
    expected_previous_revision: Optional[int] = None
    source_commit: Optional[str] = None
    scope_reference: Optional[str] = None
    tasks: List[PlanTaskDefinition] = Field(default_factory=list)

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("plan_id cannot be empty")
        return clean

    @field_validator("revision")
    @classmethod
    def validate_revision(cls, v: int) -> int:
        if v < 1:
            raise ValueError("revision must be >= 1")
        return v


class PlanMapping(BaseModel):
    model_config = ConfigDict(frozen=False)

    task_id: str
    planning_reference: str
    local_issue_id: str
    local_issue_key: str


class ReconciliationItem(BaseModel):
    model_config = ConfigDict(frozen=False)

    task_id: str
    planning_reference: str
    issue_key: str
    current_state: str
    change_type: str
    description: str
    proposal_id: Optional[str] = None
    proposal_rev: Optional[int] = None
    base_policy_version: int = 1


class PlanPublicationResponse(BaseModel):
    model_config = ConfigDict(frozen=False)

    success: bool = True
    project_id: str
    project_key: str
    plan_id: str
    revision: int
    source_commit: Optional[str] = None
    scope_reference: Optional[str] = None
    mappings: List[PlanMapping] = Field(default_factory=list)
    tasks_created: int = 0
    tasks_updated: int = 0
    changes_requiring_reconciliation: List[ReconciliationItem] = Field(default_factory=list)
    board_cursor: str = ""


class PlanRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    project_id: str
    plan_id: str
    revision: int
    source_commit: Optional[str] = None
    scope_reference: Optional[str] = None
    published_by: str = ""
    tasks_count: int = 0
    created_at: str = ""


class PlanReconciliationRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    decision: str = Field(..., description="Reconciliation decision: 'apply' or 'reject'")
    expected_proposal_id: str = Field(..., min_length=1, description="Immutable proposal identity")
    expected_proposal_rev: int = Field(..., ge=1, description="Immutable proposal revision")
    expected_base_policy_version: int = Field(..., ge=1, description="Expected base policy version of the issue")

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("decision must be a string")
        clean = v.strip().lower()
        if clean not in ("apply", "reject"):
            raise ValueError(f"decision must be 'apply' or 'reject', got '{v}'")
        return clean


class CoordinatorAttempt(BaseModel):
    model_config = ConfigDict(frozen=False)

    attempt_id: str
    tenant_id: str
    project_id: str
    issue_id: str
    task_id: str
    attempt_seq: int
    status: str
    fencing_token: int = 1
    started_at: str = ""
    finished_at: Optional[str] = None
    budget_tokens_allocated: int = 0
    budget_tokens_spent: int = 0
    candidate_commit_sha: Optional[str] = None
    failure_reason: Optional[str] = None


class CoordinatorIntent(BaseModel):
    model_config = ConfigDict(frozen=False)

    intent_id: str
    tenant_id: str
    project_id: str
    issue_id: str
    task_id: str
    attempt_id: str
    adapter_type: str
    status: str
    fencing_token: int = 1
    worker_id: Optional[str] = None
    lease_expires_at: Optional[float] = None
    lease_heartbeat_at: Optional[float] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class CoordinatorRun(BaseModel):
    model_config = ConfigDict(frozen=False)

    run_id: str
    intent_id: str
    attempt_id: str
    fencing_token: int
    runtime_session_id: Optional[str] = None
    process_pid: Optional[int] = None
    process_pgid: Optional[int] = None
    status: str
    exit_code: Optional[int] = None
    started_at: str = ""
    ended_at: Optional[str] = None


class CoordinatorEvent(BaseModel):
    model_config = ConfigDict(frozen=False)

    event_id: Optional[int] = None
    run_id: str
    cursor_seq: int
    event_type: str
    event_payload: Dict[str, Any] = Field(default_factory=dict)
    emitted_at: str = ""


class CoordinatorEvidenceReceipt(BaseModel):
    model_config = ConfigDict(frozen=False)

    evidence_id: str
    issue_id: str
    task_id: str
    attempt_id: str
    run_id: str
    candidate_commit_sha: str
    nonce: str
    key_id: str
    signature: str
    canonical_payload: Dict[str, Any] = Field(default_factory=dict)
    admission_status: str = "SUBMITTED"  # "SUBMITTED" | "ADMITTED" | "REJECTED"
    created_at: str = ""


class CoordinatorReservation(BaseModel):
    model_config = ConfigDict(frozen=False)

    reservation_id: str
    tenant_id: str
    project_id: str
    issue_id: str
    attempt_id: str
    authorization_ref: str
    amount: int
    settled_amount: int = 0
    status: str = "HELD"  # "HELD" | "SETTLED" | "RELEASED"
    created_at: str = ""
    settled_at: Optional[str] = None


