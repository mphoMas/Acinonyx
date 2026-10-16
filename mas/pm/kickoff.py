"""Project startup automation and kickoff orchestration service (SBA-09, CC-15).

Coordinates project registration, plan publication, delivery gate readiness,
and automatic admission into the bounded AutomaticCorrectionLoop.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mas.pm.db import PMDatabase
from mas.pm.discovery import ProjectRegistryDiscovery
from mas.pm.fsm import FSMEngine
from mas.pm.loop import AutomaticCorrectionLoop
from mas.pm.models import Issue, IssueState, IssueType, PriorityLevel, Project
from mas.security import ExecutionContext


@dataclass(frozen=True)
class KickoffResult:
    project_id: str
    project_key: str
    published_tasks_count: int
    admitted_jobs: list[dict[str, Any]]
    status: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_key": self.project_key,
            "published_tasks_count": self.published_tasks_count,
            "admitted_jobs": self.admitted_jobs,
            "status": self.status,
            "created_at": self.created_at,
        }


class ProjectKickoffService:
    """Orchestrates initial project registration, plan publication, and loop admission."""

    def __init__(
        self,
        db: PMDatabase,
        *,
        loop: AutomaticCorrectionLoop | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self.db = db
        self.workspace_root = Path(workspace_root) if workspace_root else None
        self.loop = loop or AutomaticCorrectionLoop(db, workspace_root=self.workspace_root)
        self.fsm = FSMEngine(db, workspace_root=self.workspace_root)
        self.discovery = ProjectRegistryDiscovery(registry_file=self.workspace_root / "projects" / "registry.json", db=self.db) if self.workspace_root else None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def kickoff_project(
        self,
        *,
        tenant_id: str,
        project_key: str,
        project_name: str,
        token_budget: int = 100000,
        base_commit_sha: str,
        task_definitions: list[dict[str, Any]],
        default_profile: str = "coding.solve.v1",
        actor_principal: str | None = None,
        auto_admit_first_ready: bool = True,
    ) -> KickoffResult:
        """Atomically initializes a project, publishes tasks, and admits eligible tasks to the loop."""
        actor = actor_principal or f"{tenant_id}:coordinator_admin"
        now_iso = self._now_iso()
        project_id = f"proj-{secrets.token_hex(8)}"

        with ExecutionContext.scope(actor):
            # 1. Register project
            proj = Project(
                id=project_id,
                key=project_key,
                name=project_name,
                token_budget=token_budget,
                tokens_consumed=0,
            )
            self.db.create_project(proj)

            published_issues: list[Issue] = []
            # 2. Publish versioned tasks
            for idx, td in enumerate(task_definitions):
                task_ref = str(td.get("task_id") or td.get("planning_reference") or f"T-{idx + 1}")
                issue_key = f"{project_key}-{idx + 1}"
                issue_id = f"iss-{secrets.token_hex(8)}"
                title = str(td.get("title") or f"Task {task_ref}")
                appetite = int(td.get("appetite_tokens", 20000))
                whitelist = td.get("path_whitelist", ["*"])
                forbidden = td.get("forbidden_paths", [])
                assignee = str(td.get("assignee_principal") or f"{tenant_id}:builder-1")

                issue = Issue(
                    id=issue_id,
                    project_id=project_id,
                    key=issue_key,
                    task_id=task_ref,
                    title=title,
                    description=str(td.get("description") or ""),
                    issue_type=IssueType.TASK,
                    priority=PriorityLevel.HIGH,
                    current_state=IssueState.BACKLOG,
                    assignee_principal=assignee,
                    appetite_tokens=appetite,
                    path_whitelist=whitelist,
                    forbidden_paths=forbidden,
                    staged_acceptance_criteria=td.get("acceptance_criteria", ["Requirement satisfied", "Independently verified"]),
                )
                self.db.create_issue(issue)
                published_issues.append(issue)

                with self.db.atomic_transaction() as conn:
                    conn.execute(
                        """
                        INSERT INTO pm_task_mappings (project_id, planning_reference, task_id, local_issue_id, local_issue_key)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (project_id, task_ref, task_ref, issue_id, issue_key),
                    )

            # 3. Admit eligible ready tasks into automatic loop
            admitted_jobs: list[dict[str, Any]] = []
            if auto_admit_first_ready and published_issues:
                first_issue = published_issues[0]
                job_id = f"job-{secrets.token_hex(8)}"
                adm = self.loop.admit_task(
                    job_id=job_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    issue_id=first_issue.id,
                    task_id=first_issue.task_id or first_issue.key,
                    profile=default_profile,
                    base_commit_sha=base_commit_sha,
                )
                adm_entry = dict(adm)
                adm_entry["issue_id"] = first_issue.id
                adm_entry["task_id"] = first_issue.task_id or first_issue.key
                admitted_jobs.append(adm_entry)

        return KickoffResult(
            project_id=project_id,
            project_key=project_key,
            published_tasks_count=len(published_issues),
            admitted_jobs=admitted_jobs,
            status="INITIALIZED",
            created_at=now_iso,
        )


__all__ = ["KickoffResult", "ProjectKickoffService"]
