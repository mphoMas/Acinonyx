"""
mas.pm: Internal Agentic Project Management Engine (MAS-PM).
"""

from mas.pm.db import PMDatabase
from mas.pm.fsm import FSMEngine, InvalidStateTransitionError
from mas.pm.guards import (
    CircuitBreakerTrippedError,
    PMGuardError,
    ScopeJailViolationError,
    SeparationOfDutiesError,
    UnshapedTaskError,
    UnverifiedWorkError,
    WIPLimitExceededError,
)
from mas.pm.metrics import FlowMetricsEngine
from mas.pm.models import (
    BoardState,
    CFDSnapshot,
    CriticVerdict,
    CriticVerdictType,
    EvidenceLink,
    EvidenceType,
    Issue,
    IssueState,
    IssueType,
    Project,
    ShapedTask,
)
from mas.pm.tools import (
    get_pm_db,
    pm_attach_evidence,
    pm_cast_verdict,
    pm_create_issue,
    pm_create_project,
    pm_get_board_state,
    pm_get_issue,
    pm_list_issues,
    pm_transition_issue,
    register_pm_tools,
)

__all__ = [
    "BoardState",
    "CFDSnapshot",
    "CircuitBreakerTrippedError",
    "CriticVerdict",
    "CriticVerdictType",
    "EvidenceLink",
    "EvidenceType",
    "FSMEngine",
    "FlowMetricsEngine",
    "InvalidStateTransitionError",
    "Issue",
    "IssueState",
    "IssueType",
    "PMDatabase",
    "PMGuardError",
    "Project",
    "ScopeJailViolationError",
    "SeparationOfDutiesError",
    "ShapedTask",
    "UnshapedTaskError",
    "UnverifiedWorkError",
    "WIPLimitExceededError",
    "get_pm_db",
    "pm_attach_evidence",
    "pm_cast_verdict",
    "pm_create_issue",
    "pm_create_project",
    "pm_get_board_state",
    "pm_get_issue",
    "pm_list_issues",
    "pm_transition_issue",
    "register_pm_tools",
]
