"""
mas.pm.plans: Plan Publication Service for the MAS Project Management Engine (MAS-PM).
Implements the SBA-03 planning publication contract defined in BOARD_CONTRACT_V1.md.

Enforces:
1. Stable planning identities (task_id, planning_reference) mapped to local issue keys.
2. Complete graph and payload pre-validation before any mutations.
3. Dependency cycle detection and hierarchy loop prevention.
4. Unsafe path traversal rejection (relative normalized paths only).
5. Scoped idempotency with hash mismatch detection (409 Conflict).
6. Optimistic concurrency with expected_previous_revision check (409 Conflict).
7. Active work preservation (never overwrites runtime status, assignments, evidence, or verdicts).
8. Explicit change reconciliation tracking for active tasks.
9. Atomic transactions (all changes succeed or none do).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import PurePosixPath
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from mas.pm.db import PMDatabase
from mas.pm.models import (
    Issue,
    IssueState,
    PlanMapping,
    PlanPublicationRequest,
    PlanPublicationResponse,
    PlanRecord,
    PlanTaskDefinition,
    ReconciliationItem,
    TaskMapping,
)


class PlanError(Exception):
    """Base exception for plan publication errors."""
    def __init__(self, message: str, code: str = "plan_error", retryable: bool = False, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retryable = retryable
        self.details = details or {}


class PlanValidationError(PlanError):
    """Raised when plan payload or task definitions fail validation (HTTP 400)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="validation_failed", retryable=False, details=details)


class CycleDetectedError(PlanValidationError):
    """Raised when dependency or hierarchy cycle is detected (HTTP 400)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)
        self.code = "cycle_detected"


class UnsafePathError(PlanValidationError):
    """Raised when path traversal or absolute path is found in path_whitelist (HTTP 400)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)
        self.code = "unsafe_path"


class ContradictoryIdentityError(PlanValidationError):
    """Raised when task identities contradict existing mappings (HTTP 400)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details=details)
        self.code = "contradictory_identity"


class IdempotencyConflictError(PlanError):
    """Raised when an idempotency key is reused with a different request payload (HTTP 409)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="idempotency_conflict", retryable=False, details=details)


class StaleRevisionError(PlanError):
    """Raised when expected_previous_revision does not match current plan revision (HTTP 409)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="stale_revision", retryable=False, details=details)


class RevisionMismatchError(PlanError):
    """Raised when revision does not equal current revision + 1 (HTTP 409)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="revision_mismatch", retryable=False, details=details)


class ProjectNotFoundError(PlanError):
    """Raised when the target project is not found in the tenant database (HTTP 404)."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code="not_found", retryable=False, details=details)


def compute_request_hash(data: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash of the canonical request payload."""
    canonical_json = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def validate_path_scope(path: str) -> str:
    """
    Validates that a path is safe:
    - Relative (not starting with '/' or drive letter)
    - No '..' directory traversal components
    - Returns normalized posix path
    """
    cleaned = path.strip()
    if not cleaned:
        raise UnsafePathError("Empty path specification in path_whitelist")

    if cleaned.startswith("/") or cleaned.startswith("\\") or (len(cleaned) >= 2 and cleaned[1] == ":"):
        raise UnsafePathError(f"Unsafe absolute path '{path}': paths must be relative to repository root")

    pure = PurePosixPath(cleaned)
    for part in pure.parts:
        if part == "..":
            raise UnsafePathError(f"Unsafe path '{path}': directory traversal ('..') is strictly forbidden")

    return str(pure)


def detect_dependency_cycles(tasks: List[PlanTaskDefinition], existing_refs: Set[str]) -> None:
    """
    Detects cycles in the plan's dependency graph using depth-first search cycle detection.
    Raises CycleDetectedError if a cycle is found.
    """
    # Graph maps each task reference to the list of task references it depends on (blockers)
    # A -> B means A depends on B (B must complete before A can start)
    graph: Dict[str, List[str]] = {}
    known_nodes: Set[str] = set()

    for task in tasks:
        known_nodes.add(task.task_id)
        known_nodes.add(task.planning_reference)

    for task in tasks:
        node_id = task.task_id
        graph[node_id] = []
        for dep in task.dependencies:
            dep_clean = dep.strip()
            if dep_clean == task.task_id or dep_clean == task.planning_reference:
                raise CycleDetectedError(f"Task '{task.planning_reference}' cannot depend on itself")
            graph[node_id].append(dep_clean)

    # 0 = unvisited, 1 = visiting (in recursion stack), 2 = visited
    state: Dict[str, int] = {}

    def dfs(node: str, path: List[str]) -> None:
        state[node] = 1
        path.append(node)

        # Resolve node if it's a planning_reference alias
        deps = graph.get(node, [])
        for neighbor in deps:
            # If neighbor is outside current plan (i.e. existing DB task), it's a leaf for this cycle check
            if neighbor not in graph:
                # Could be a planning_reference mapping to a task_id in graph
                found_task = next((t.task_id for t in tasks if t.planning_reference == neighbor), None)
                if found_task:
                    neighbor = found_task
                else:
                    continue

            n_state = state.get(neighbor, 0)
            if n_state == 1:
                cycle_str = " -> ".join(path + [neighbor])
                raise CycleDetectedError(f"Cyclic dependency detected: {cycle_str}")
            elif n_state == 0:
                dfs(neighbor, path)

        path.pop()
        state[node] = 2

    for node in graph:
        if state.get(node, 0) == 0:
            dfs(node, [])


def detect_hierarchy_cycles(tasks: List[PlanTaskDefinition]) -> None:
    """
    Detects parent-child cycles among tasks in the plan.
    Raises CycleDetectedError if a cycle is found.
    """
    task_by_id = {t.task_id: t for t in tasks}
    task_by_ref = {t.planning_reference: t for t in tasks}

    for task in tasks:
        if not task.parent_task_id:
            continue
        visited = {task.task_id, task.planning_reference}
        curr_parent_id = task.parent_task_id.strip()

        while curr_parent_id:
            if curr_parent_id in visited:
                raise CycleDetectedError(f"Hierarchy cycle detected involving task '{task.planning_reference}' and parent '{curr_parent_id}'")
            visited.add(curr_parent_id)

            parent_task = task_by_id.get(curr_parent_id) or task_by_ref.get(curr_parent_id)
            if parent_task:
                curr_parent_id = (parent_task.parent_task_id or "").strip()
            else:
                break


class PlanPublisherService:
    """
    Service coordinating conversation-derived plan validation, idempotency,
    optimistic concurrency, and atomic persistence into MAS-PM.
    """

    def __init__(self, db: PMDatabase):
        self.db = db

    def publish_plan(
        self,
        project_id_or_key: str,
        request: PlanPublicationRequest,
        actor: str,
        tenant_id: str,
        idempotency_key: Optional[str] = None,
        test_injected_failure_stage: Optional[str] = None,
    ) -> Tuple[int, PlanPublicationResponse]:
        """
        Publishes a plan into MAS-PM.
        Returns (http_status_code, response_model).
        """
        # 1. Resolve project
        project = self.db.get_project(project_id_or_key) or self.db.get_project_by_key(project_id_or_key)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id_or_key}' not found in current tenant")

        # 2. Check limits
        if len(request.tasks) > 500:
            raise PlanValidationError(f"Plan contains {len(request.tasks)} tasks, exceeding the maximum limit of 500")

        # 3. Validate unique identities within the request
        seen_task_ids: Set[str] = set()
        seen_planning_refs: Set[str] = set()

        for task in request.tasks:
            t_id = task.task_id.strip()
            p_ref = task.planning_reference.strip()

            if not t_id:
                raise PlanValidationError("Each task must have a non-empty 'task_id'")
            if not p_ref:
                raise PlanValidationError(f"Task '{t_id}' must have a non-empty 'planning_reference'")
            if not task.title.strip():
                raise PlanValidationError(f"Task '{p_ref}' must have a non-empty 'title'")
            if len(task.title) > 256:
                raise PlanValidationError(f"Task '{p_ref}' title exceeds maximum length of 256 characters")

            if t_id in seen_task_ids:
                raise PlanValidationError(f"Duplicate task_id '{t_id}' in plan request")
            if p_ref in seen_planning_refs:
                raise PlanValidationError(f"Duplicate planning_reference '{p_ref}' in plan request")

            seen_task_ids.add(t_id)
            seen_planning_refs.add(p_ref)

            # Validate path scope
            for p in task.path_whitelist:
                validate_path_scope(p)

        # 4. Check contradictory mappings against existing database
        existing_mappings = self.db.list_task_mappings(project.id)
        mapping_by_task_id = {m.task_id: m for m in existing_mappings}
        mapping_by_ref = {m.planning_reference: m for m in existing_mappings}

        for task in request.tasks:
            t_id = task.task_id.strip()
            p_ref = task.planning_reference.strip()

            m1 = mapping_by_task_id.get(t_id)
            if m1 and m1.planning_reference != p_ref:
                raise ContradictoryIdentityError(
                    f"Task ID '{t_id}' is already mapped to planning reference '{m1.planning_reference}' on issue {m1.local_issue_key}; "
                    f"cannot contradict existing mapping with '{p_ref}'"
                )

            m2 = mapping_by_ref.get(p_ref)
            if m2 and m2.task_id != t_id:
                raise ContradictoryIdentityError(
                    f"Planning reference '{p_ref}' is already mapped to task ID '{m2.task_id}' on issue {m2.local_issue_key}; "
                    f"cannot contradict existing mapping with '{t_id}'"
                )

        # 5. Check hierarchy cycles and dependency cycles
        all_known_refs = set(mapping_by_ref.keys()) | set(mapping_by_task_id.keys())
        detect_hierarchy_cycles(request.tasks)
        detect_dependency_cycles(request.tasks, all_known_refs)

        # 6. Verify dependencies reference known tasks (either in plan or existing in project)
        valid_targets = seen_task_ids | seen_planning_refs | all_known_refs
        for task in request.tasks:
            for dep in task.dependencies:
                dep_clean = dep.strip()
                if dep_clean not in valid_targets:
                    raise PlanValidationError(
                        f"Task '{task.planning_reference}' depends on unknown task '{dep_clean}'. "
                        "Dependencies must resolve within the same project plan or existing project issues."
                    )

        # 7. Compute canonical request hash for idempotency
        request_dict = request.model_dump()
        req_hash = compute_request_hash(request_dict)
        idempotency_action = f"publish_plan:{project.id}"

        # Check existing idempotency key before opening transaction
        if idempotency_key:
            existing_idem = self.db.get_idempotency_record(tenant_id, idempotency_action, idempotency_key)
            if existing_idem:
                if existing_idem["request_hash"] == req_hash:
                    # Identical replay: return stored response!
                    cached_data = json.loads(existing_idem["response_body"])
                    return existing_idem["response_code"], PlanPublicationResponse(**cached_data)
                else:
                    # Same key, different body -> 409 Conflict
                    raise IdempotencyConflictError(
                        f"Idempotency key '{idempotency_key}' was previously used with a different request payload."
                    )

        # 8. Check optimistic revision
        latest_plan = self.db.get_latest_plan_revision(project.id, request.plan_id)
        current_rev = latest_plan.revision if latest_plan else 0

        if request.expected_previous_revision is not None:
            if request.expected_previous_revision != current_rev:
                raise StaleRevisionError(
                    f"Expected previous revision {request.expected_previous_revision} does not match current plan revision {current_rev}."
                )

        if request.revision != current_rev + 1:
            raise RevisionMismatchError(
                f"Published plan revision must be {current_rev + 1}, got {request.revision}."
            )

        # Failure injection point: before_transaction
        if test_injected_failure_stage == "before_transaction":
            raise RuntimeError("Injected failure before transaction")

        # 9. Atomic Transaction
        with self.db.atomic_transaction() as conn:
            # Recheck idempotency inside lock
            if idempotency_key:
                locked_idem = self.db.get_idempotency_record(tenant_id, idempotency_action, idempotency_key, conn=conn)
                if locked_idem:
                    if locked_idem["request_hash"] == req_hash:
                        cached_data = json.loads(locked_idem["response_body"])
                        return locked_idem["response_code"], PlanPublicationResponse(**cached_data)
                    else:
                        raise IdempotencyConflictError(
                            f"Idempotency key '{idempotency_key}' was previously used with a different request payload."
                        )

            # Recheck revision inside lock to prevent concurrent races
            locked_latest = self.db.get_latest_plan_revision(project.id, request.plan_id, conn=conn)
            locked_rev = locked_latest.revision if locked_latest else 0
            if locked_rev != current_rev:
                raise StaleRevisionError(
                    f"Concurrent publication detected: current plan revision advanced to {locked_rev}."
                )

            # Failure injection point: during_validation
            if test_injected_failure_stage == "during_validation":
                raise RuntimeError("Injected failure during validation")

            # In-transaction lookup dictionaries for parent and dependency resolution
            ref_to_issue_id: Dict[str, str] = {}
            for m in existing_mappings:
                ref_to_issue_id[m.planning_reference] = m.local_issue_id
                ref_to_issue_id[m.task_id] = m.local_issue_id

            created_count = 0
            updated_count = 0
            reconciliations: List[ReconciliationItem] = []
            final_mappings: List[PlanMapping] = []

            # First pass: Create or Update issues & mappings
            for task in request.tasks:
                t_id = task.task_id.strip()
                p_ref = task.planning_reference.strip()

                existing_map = self.db.get_task_mapping_by_task_id(project.id, t_id, conn=conn) or \
                               self.db.get_task_mapping(project.id, p_ref, conn=conn)

                budget_tokens = (
                    task.proposed_budget_tokens
                    if task.proposed_budget_tokens is not None
                    else (task.proposed_budget.get("tokens") if isinstance(task.proposed_budget, dict) and "tokens" in task.proposed_budget else 50000)
                )

                # Format description: ensure delivery owner and allocation tag are structured
                desc_text = task.description.strip()
                if task.proposed_delivery_owner:
                    owner_line = f"Delivery/integration owner: {task.proposed_delivery_owner.strip()}"
                    if "Delivery/integration owner:" not in desc_text:
                        desc_text = f"{desc_text}\n\n{owner_line}" if desc_text else owner_line
                alloc_tag = f"[ALLOCATION_ID:{p_ref}]"
                if alloc_tag not in desc_text:
                    desc_text = f"{desc_text}\n{alloc_tag}" if desc_text else alloc_tag

                if existing_map:
                    # Update existing issue
                    issue = self.db.get_issue(existing_map.local_issue_id, conn=conn)
                    if not issue:
                        raise PlanValidationError(f"Mapped issue '{existing_map.local_issue_key}' not found in database")

                    # Check active work reconciliation requirements
                    if issue.current_state != IssueState.BACKLOG:
                        # 1. Did acceptance criteria change?
                        if sorted(issue.acceptance_criteria) != sorted(task.acceptance_criteria):
                            reconciliations.append(ReconciliationItem(
                                task_id=t_id,
                                planning_reference=p_ref,
                                issue_key=issue.key,
                                current_state=issue.current_state.value,
                                change_type="acceptance_criteria_modified",
                                description=(
                                    f"Active issue {issue.key} in state {issue.current_state.value} has modified acceptance criteria "
                                    "requiring explicit coordinator/reviewer reconciliation."
                                ),
                            ))

                        # 2. Did path whitelist change?
                        if sorted(issue.path_whitelist) != sorted(task.path_whitelist):
                            reconciliations.append(ReconciliationItem(
                                task_id=t_id,
                                planning_reference=p_ref,
                                issue_key=issue.key,
                                current_state=issue.current_state.value,
                                change_type="path_whitelist_modified",
                                description=(
                                    f"Active issue {issue.key} in state {issue.current_state.value} has modified path scope "
                                    "requiring explicit coordinator/reviewer reconciliation."
                                ),
                            ))

                    # Update plan-defined fields preserving runtime status, tokens, assignee, evidence
                    self.db.update_issue_from_plan(
                        issue_id=issue.id,
                        title=task.title.strip(),
                        description=desc_text,
                        issue_type=task.type,
                        priority=task.priority,
                        parent_id=issue.parent_id,  # Resolved in second pass
                        path_whitelist=task.path_whitelist,
                        acceptance_criteria=task.acceptance_criteria,
                        proposed_delivery_owner=task.proposed_delivery_owner,
                        reviewer_requirement=task.reviewer_requirement,
                        proposed_budget_tokens=budget_tokens,
                        conn=conn,
                    )

                    ref_to_issue_id[t_id] = issue.id
                    ref_to_issue_id[p_ref] = issue.id

                    final_mappings.append(PlanMapping(
                        task_id=t_id,
                        planning_reference=p_ref,
                        local_issue_id=issue.id,
                        local_issue_key=issue.key,
                    ))
                    updated_count += 1

                else:
                    # Allocate new issue key and create new task
                    new_key = self.db.next_issue_key(project.key, conn=conn)
                    new_id = str(uuid.uuid4())

                    new_issue = Issue(
                        id=new_id,
                        project_id=project.id,
                        key=new_key,
                        title=task.title.strip(),
                        description=desc_text,
                        issue_type=task.type,
                        current_state=IssueState.BACKLOG,  # New tasks ALWAYS enter BACKLOG
                        priority=task.priority,
                        parent_id=None,  # Resolved in second pass
                        assignee_principal=None,  # Proposed delivery owner DOES NOT grant runtime permissions!
                        appetite_tokens=budget_tokens,
                        tokens_spent=0,
                        reflexion_attempts=0,
                        rework_cycle=0,
                        path_whitelist=task.path_whitelist,
                        task_id=t_id,
                        planning_reference=p_ref,
                        acceptance_criteria=task.acceptance_criteria,
                        proposed_delivery_owner=task.proposed_delivery_owner,
                        reviewer_requirement=task.reviewer_requirement,
                        proposed_budget_tokens=budget_tokens,
                    )

                    self.db.create_issue(new_issue, conn=conn)

                    new_mapping = TaskMapping(
                        project_id=project.id,
                        planning_reference=p_ref,
                        task_id=t_id,
                        local_issue_id=new_id,
                        local_issue_key=new_key,
                    )
                    self.db.upsert_task_mapping(new_mapping, conn=conn)

                    ref_to_issue_id[t_id] = new_id
                    ref_to_issue_id[p_ref] = new_id

                    final_mappings.append(PlanMapping(
                        task_id=t_id,
                        planning_reference=p_ref,
                        local_issue_id=new_id,
                        local_issue_key=new_key,
                    ))
                    created_count += 1

            # Failure injection point: during_issues_write
            if test_injected_failure_stage == "during_issues_write":
                raise RuntimeError("Injected failure during issues write")

            # Second pass: Wire hierarchy (parent_id) and dependencies
            for task in request.tasks:
                t_id = task.task_id.strip()
                p_ref = task.planning_reference.strip()
                my_issue_id = ref_to_issue_id[t_id]

                # Update parent if specified
                if task.parent_task_id:
                    parent_ref = task.parent_task_id.strip()
                    parent_issue_id = ref_to_issue_id.get(parent_ref)
                    if parent_issue_id and parent_issue_id != my_issue_id:
                        conn.execute(
                            "UPDATE pm_issues SET parent_id = ? WHERE id = ?",
                            (parent_issue_id, my_issue_id),
                        )

                # Add dependencies
                for dep in task.dependencies:
                    dep_ref = dep.strip()
                    blocker_issue_id = ref_to_issue_id.get(dep_ref)
                    if blocker_issue_id and blocker_issue_id != my_issue_id:
                        conn.execute(
                            """
                            INSERT INTO pm_dependencies (blocker_id, blocked_id)
                            VALUES (?, ?)
                            ON CONFLICT(blocker_id, blocked_id) DO NOTHING
                            """,
                            (blocker_issue_id, my_issue_id),
                        )

            # Failure injection point: during_dependencies_write
            if test_injected_failure_stage == "during_dependencies_write":
                raise RuntimeError("Injected failure during dependencies write")

            # 10. Record plan publication
            now_iso = datetime.now(timezone.utc).isoformat()
            plan_record = PlanRecord(
                project_id=project.id,
                plan_id=request.plan_id,
                revision=request.revision,
                source_commit=request.source_commit,
                scope_reference=request.scope_reference,
                published_by=actor,
                tasks_count=len(request.tasks),
                created_at=now_iso,
            )
            self.db.create_plan_record(plan_record, conn=conn)

            # 11. Generate board cursor
            board_cursor = f"c_{project.id}_{request.revision}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

            response_data = PlanPublicationResponse(
                success=True,
                project_id=project.id,
                project_key=project.key,
                plan_id=request.plan_id,
                revision=request.revision,
                source_commit=request.source_commit,
                scope_reference=request.scope_reference,
                mappings=final_mappings,
                tasks_created=created_count,
                tasks_updated=updated_count,
                changes_requiring_reconciliation=reconciliations,
                board_cursor=board_cursor,
            )

            status_code = 201 if current_rev == 0 else 200

            # 12. Persist idempotency record
            if idempotency_key:
                resp_json = json.dumps(response_data.model_dump())
                self.db.save_idempotency_record(
                    tenant_id=tenant_id,
                    action=idempotency_action,
                    idempotency_key=idempotency_key,
                    request_hash=req_hash,
                    response_code=status_code,
                    response_body=resp_json,
                    conn=conn,
                )

            # Failure injection point: before_commit
            if test_injected_failure_stage == "before_commit":
                raise RuntimeError("Injected failure before commit")

            return status_code, response_data
