"""
mas.orchestration.supervisor: Hierarchical Supervisor for task decomposition, dispatch, and aggregation.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from mas.core.agent import BaseAgent
from mas.core.message import ContentType, Message, MessageMetadata, Role
from mas.observability import METRICS, LOGGER


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FailurePolicy(str, Enum):
    FAIL_FAST = "fail_fast"
    CONTINUE = "continue"


@dataclass
class SubTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = ""
    assigned_worker: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    attempts: int = 0
    dependencies: List[str] = field(default_factory=list)


class SupervisorAgent(BaseAgent):
    """
    Hierarchical Orchestrator that decomposes a high-level goal,
    dispatches work items to specialist agents, and aggregates results.
    """

    def __init__(
        self,
        name: str = "supervisor",
        system_prompt: str = "You are the Hierarchical Supervisor managing specialist agents.",
        failure_policy: FailurePolicy = FailurePolicy.FAIL_FAST,
        default_timeout_sec: float = 30.0,
        default_retries: int = 1,
        **kwargs,
    ) -> None:
        super().__init__(name=name, role=Role.SUPERVISOR, system_prompt=system_prompt, **kwargs)
        self.workers: Dict[str, BaseAgent] = {}
        self.subtasks: Dict[str, SubTask] = {}
        self.failure_policy = failure_policy
        self.default_timeout_sec = default_timeout_sec
        self.default_retries = default_retries

    def register_worker(self, agent: BaseAgent) -> None:
        """Register a subordinate specialist agent."""
        self.workers[agent.name] = agent

    def plan_subtasks(self, goal: str, task_specs: List[Dict[str, Any]]) -> List[SubTask]:
        """Decompose a goal into structured subtasks."""
        created_tasks = []
        for spec in task_specs:
            worker_name = spec.get("worker")
            if worker_name not in self.workers:
                raise ValueError(f"Worker '{worker_name}' is not registered with supervisor.")

            task = SubTask(
                id=spec.get("id", str(uuid.uuid4())[:8]),
                description=spec.get("description", ""),
                assigned_worker=worker_name,
                dependencies=spec.get("dependencies", []),
            )
            self.subtasks[task.id] = task
            created_tasks.append(task)
        return created_tasks

    def _deadlock_dump(self) -> str:
        lines = ["DEADLOCK DIAGNOSTIC:"]
        completed = {t.id for t in self.subtasks.values() if t.status == TaskStatus.COMPLETED}
        for task in self.subtasks.values():
            unmet = [d for d in task.dependencies if d not in completed]
            lines.append(
                f"  task={task.id} status={task.status.value} worker={task.assigned_worker} "
                f"unmet_deps={unmet} error={task.error}"
            )
        return "\n".join(lines)

    async def execute_subtasks(self, timeout_sec: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute subtasks respecting dependency graph.
        Independent tasks run concurrently; dependent tasks wait for upstream outputs.
        Supports per-task timeout, retries, and fail-fast vs continue policies.
        """
        completed_results: Dict[str, str] = {}
        effective_timeout = timeout_sec if timeout_sec is not None else self.default_timeout_sec

        while True:
            ready_tasks = [
                task for task in self.subtasks.values()
                if task.status == TaskStatus.PENDING
                and all(dep in completed_results for dep in task.dependencies)
            ]

            if not ready_tasks:
                pending = [t for t in self.subtasks.values() if t.status == TaskStatus.PENDING]
                running = [t for t in self.subtasks.values() if t.status == TaskStatus.RUNNING]
                if not pending and not running:
                    break
                if pending and not ready_tasks:
                    dump = self._deadlock_dump()
                    LOGGER.error(dump)
                    raise RuntimeError(f"Deadlock or unmet dependencies detected in subtasks.\n{dump}")
                break

            async def _run_single(task: SubTask):
                task.status = TaskStatus.RUNNING
                worker = self.workers[task.assigned_worker]
                max_attempts = self.default_retries + 1
                last_error: Optional[Exception] = None

                dep_context = ""
                if task.dependencies:
                    dep_context = "\nPreceding Artifacts:\n" + "\n".join(
                        f"- Task [{dep_id}]: {completed_results[dep_id]}"
                        for dep_id in task.dependencies
                        if dep_id in completed_results
                    )

                instruction = f"Task: {task.description}{dep_context}"
                msg = Message(
                    sender=self.name,
                    recipient=task.assigned_worker,
                    role=Role.SUPERVISOR,
                    content=instruction,
                    metadata=MessageMetadata(topic="orchestration"),
                )

                for attempt in range(1, max_attempts + 1):
                    task.attempts = attempt
                    try:
                        response = await asyncio.wait_for(
                            worker.step(msg),
                            timeout=effective_timeout,
                        )
                        task.result = response.content
                        task.status = TaskStatus.COMPLETED
                        completed_results[task.id] = response.content
                        METRICS.incr("supervisor.subtasks.completed")
                        return
                    except Exception as exc:
                        last_error = exc
                        METRICS.incr("supervisor.subtasks.retries")
                        LOGGER.warning(
                            "subtask %s attempt %s failed: %s", task.id, attempt, exc
                        )

                task.status = TaskStatus.FAILED
                task.error = str(last_error)
                METRICS.incr("supervisor.subtasks.failed")
                if self.failure_policy == FailurePolicy.FAIL_FAST:
                    raise RuntimeError(
                        f"Subtask '{task.id}' failed after {max_attempts} attempts: {last_error}"
                    )
                # CONTINUE: leave failed, do not add to completed_results

            await asyncio.gather(*[_run_single(t) for t in ready_tasks])

            if self.failure_policy == FailurePolicy.CONTINUE:
                # Mark impossible downstream of failed tasks as failed to avoid deadlock wait
                failed_ids = {t.id for t in self.subtasks.values() if t.status == TaskStatus.FAILED}
                progress = True
                while progress:
                    progress = False
                    for task in self.subtasks.values():
                        if task.status == TaskStatus.PENDING and any(
                            d in failed_ids for d in task.dependencies
                        ):
                            task.status = TaskStatus.FAILED
                            task.error = "Upstream dependency failed"
                            failed_ids.add(task.id)
                            progress = True

        return completed_results

    async def run_mission(self, goal: str, task_specs: List[Dict[str, Any]]) -> str:
        """End-to-end plan, execute, and aggregate a macro mission."""
        self.subtasks.clear()
        self.plan_subtasks(goal, task_specs)
        await self.execute_subtasks()

        summary_lines = [f"=== MISSION SUMMARY: {goal} ==="]
        for task_id, task in self.subtasks.items():
            if task.status == TaskStatus.COMPLETED:
                summary_lines.append(
                    f"[{task.assigned_worker}] Task '{task.description}': {task.result}"
                )
            else:
                summary_lines.append(
                    f"[{task.assigned_worker}] Task '{task.description}': FAILED ({task.error})"
                )

        final_artifact = "\n".join(summary_lines)
        await self.act(
            thought_or_action=final_artifact,
            recipient="broadcast",
            content_type=ContentType.ARTIFACT,
            topic="mission_complete",
        )
        return final_artifact
