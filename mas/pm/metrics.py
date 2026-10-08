"""
mas.pm.metrics: Telemetry, Little's Law, and Cumulative Flow Diagram (CFD) engine for MAS-PM.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from mas.pm.db import PMDatabase
from mas.pm.guards import COLUMN_WIP_LIMITS
from mas.pm.models import (
    BoardState,
    CFDSnapshot,
    ColumnInfo,
    Issue,
    IssueState,
    SprintState,
)


class FlowMetricsEngine:
    """Computes Little's Law flow metrics, CFD snapshots, and bottleneck alerts."""

    def __init__(self, db: PMDatabase) -> None:
        self.db = db

    def get_board_state(self, project_key: str) -> BoardState:
        """Constructs the real-time board state for visualization and WIP monitoring."""
        project = self.db.get_project_by_key(project_key)
        if not project:
            raise ValueError(f"Project '{project_key}' not found.")

        issues = self.db.list_issues(project_id=project.id)
        issues_by_column: Dict[str, List[Issue]] = {state.value: [] for state in IssueState}

        for issue in issues:
            state_val = issue.current_state.value if hasattr(issue.current_state, "value") else str(issue.current_state)
            if state_val in issues_by_column:
                issues_by_column[state_val].append(issue)

        columns: Dict[str, ColumnInfo] = {}
        total_active_wip = 0

        for state in IssueState:
            val = state.value
            count = len(issues_by_column[val])
            wip_limit = COLUMN_WIP_LIMITS.get(val)
            is_saturated = (wip_limit is not None) and (count >= wip_limit)
            columns[val] = ColumnInfo(
                name=val,
                count=count,
                wip_limit=wip_limit,
                is_saturated=is_saturated,
            )
            if val in (IssueState.IN_PROGRESS.value, IssueState.VERIFICATION.value, IssueState.JUDICIAL_REVIEW.value):
                total_active_wip += count

        # Overall WIP saturation relative to max active capacity (4 + 2 + 2 = 8)
        max_active_capacity = sum(COLUMN_WIP_LIMITS.values())
        saturation_pct = round((total_active_wip / max_active_capacity) * 100.0, 1) if max_active_capacity > 0 else 0.0

        if saturation_pct >= 100.0:
            flow_health = "SATURATED"
        elif saturation_pct >= 75.0:
            flow_health = "APPROACHING_CAPACITY"
        else:
            flow_health = "OPTIMAL"

        sprints = self.db.list_sprints(project.id)
        active_sprint = next((s for s in sprints if s.state == SprintState.ACTIVE), None)
        active_sprint_id = active_sprint.id if active_sprint else None

        return BoardState(
            project_key=project.key,
            columns=columns,
            total_active_wip=total_active_wip,
            flow_health=flow_health,
            wip_saturation_pct=saturation_pct,
            issues_by_column=issues_by_column,
            sprints=sprints,
            active_sprint_id=active_sprint_id,
        )

    def capture_cfd_snapshot(self, project_id: str) -> CFDSnapshot:
        """Records a point-in-time state count snapshot to SQLite."""
        counts: Dict[str, int] = {}
        for state in IssueState:
            counts[state.value] = self.db.count_issues_in_state(project_id, state.value)

        now = datetime.now(timezone.utc).isoformat()
        conn = self.db._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO pm_cfd_snapshots (
                        timestamp, project_id, backlog_count, refined_count, staged_count,
                        in_progress_count, verification_count, judicial_review_count, done_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        now,
                        project_id,
                        counts[IssueState.BACKLOG.value],
                        counts[IssueState.REFINED.value],
                        counts[IssueState.STAGED.value],
                        counts[IssueState.IN_PROGRESS.value],
                        counts[IssueState.VERIFICATION.value],
                        counts[IssueState.JUDICIAL_REVIEW.value],
                        counts[IssueState.DONE.value],
                    ),
                )
            return CFDSnapshot(
                timestamp=now,
                project_id=project_id,
                backlog_count=counts[IssueState.BACKLOG.value],
                refined_count=counts[IssueState.REFINED.value],
                staged_count=counts[IssueState.STAGED.value],
                in_progress_count=counts[IssueState.IN_PROGRESS.value],
                verification_count=counts[IssueState.VERIFICATION.value],
                judicial_review_count=counts[IssueState.JUDICIAL_REVIEW.value],
                done_count=counts[IssueState.DONE.value],
            )
        finally:
            conn.close()

    def compute_cycle_time_metrics(self, project_id: str) -> Dict[str, Any]:
        """
        Calculates average Lead Time, Cycle Time, and Flow Efficiency from transition history.
        """
        conn = self.db._get_connection()
        try:
            # Get issues that reached DONE
            cur = conn.execute(
                """
                SELECT i.id, i.created_at,
                       min(t_start.timestamp) as in_progress_at,
                       max(t_done.timestamp) as done_at
                FROM pm_issues i
                JOIN pm_transitions t_start ON i.id = t_start.issue_id AND t_start.to_state = 'IN_PROGRESS'
                JOIN pm_transitions t_done ON i.id = t_done.issue_id AND t_done.to_state = 'DONE'
                WHERE i.project_id = ?
                GROUP BY i.id
                """,
                (project_id,),
            )
            rows = cur.fetchall()
            if not rows:
                return {
                    "completed_count": 0,
                    "avg_cycle_time_seconds": 0.0,
                    "avg_lead_time_seconds": 0.0,
                    "flow_efficiency_pct": 100.0,
                }

            cycle_times = []
            lead_times = []

            for r in rows:
                try:
                    t_create = datetime.fromisoformat(str(r["created_at"]))
                    t_start = datetime.fromisoformat(str(r["in_progress_at"]))
                    t_done = datetime.fromisoformat(str(r["done_at"]))

                    cycle_seconds = max(0.0, (t_done - t_start).total_seconds())
                    lead_seconds = max(cycle_seconds, (t_done - t_create).total_seconds())

                    cycle_times.append(cycle_seconds)
                    lead_times.append(lead_seconds)
                except Exception:
                    continue

            avg_cycle = sum(cycle_times) / len(cycle_times) if cycle_times else 0.0
            avg_lead = sum(lead_times) / len(lead_times) if lead_times else 0.0
            efficiency = round((avg_cycle / avg_lead) * 100.0, 1) if avg_lead > 0 else 100.0

            return {
                "completed_count": len(rows),
                "avg_cycle_time_seconds": round(avg_cycle, 2),
                "avg_lead_time_seconds": round(avg_lead, 2),
                "flow_efficiency_pct": efficiency,
            }
        finally:
            conn.close()
