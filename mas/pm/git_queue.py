"""Git-defined MAS-PM queue -> local board synchronization and agent task discovery.

No remote network calls; the checked-out Git work_queue/tasks.json is authoritative.
Sync creates missing BACKLOG records and assigns only newly created issues.
It never modifies existing issues, transitions workflow state, or executes code.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mas.pm.tools import get_pm_db, pm_create_issue, pm_create_project

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "work_queue" / "tasks.json"


def load_manifest():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported work queue schema")
    tasks = data["tasks"]
    ids = [task["id"] for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate task IDs in work queue")
    for task in tasks:
        if task["assignee_principal"] == task["reviewer_principal"]:
            raise ValueError(f"Builder and reviewer must differ: {task['id']}")
        if task["status"] != "BACKLOG":
            raise ValueError(f"Manifest cannot preapprove work: {task['id']}")
        if task["priority"] not in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            raise ValueError(f"Invalid priority: {task['id']}")
        if not task["scope"]:
            raise ValueError(f"Missing scope: {task['id']}")
        if any(p.startswith("/") or ".." in Path(p).parts for p in task["scope"]):
            raise ValueError(f"Unsafe scope: {task['id']}")
        if task["id"] in task["dependencies"]:
            raise ValueError(f"Self-dependency: {task['id']}")
        if not task["acceptance"]:
            raise ValueError(f"Missing acceptance: {task['id']}")
    for task in tasks:
        if set(task["dependencies"]) - set(ids):
            raise ValueError(f"Unknown dependencies: {task['id']}")
    return data


def sync(*, dry_run=False, db=None):
    data = load_manifest()
    database = db or get_pm_db()
    project_key = data["project_key"].upper()
    project = database.get_project_by_key(project_key)
    if project is None and not dry_run:
        pm_create_project(project_key, "Acinonyx MAS-Core",
                          "Git-defined agent work queue", db=database)
        project = database.get_project_by_key(project_key)
    issues = database.list_issues(project_id=project.id) if project else []
    known_ids = {task["id"] for task in data["tasks"]
                 if any(f"[ALLOCATION_ID:{task['id']}]" in issue.description
                        for issue in issues)}
    known_titles = {issue.title.casefold() for issue in issues}
    created = []
    skipped = []
    for task in data["tasks"]:
        if task["id"] in known_ids or task["title"].casefold() in known_titles:
            skipped.append(task["id"])
            continue
        if dry_run:
            created.append(task["id"])
            continue
        description = "\n".join([
            f"[ALLOCATION_ID:{task['id']}]",
            f"Source: work_queue/tasks.json",
            f"Assigned builder: {task['assignee_principal']}",
            f"Independent reviewer: {task['reviewer_principal']}",
            f"Dependencies (allocation IDs): {', '.join(task['dependencies']) or 'None'}",
            f"Acceptance: {'; '.join(task['acceptance'])}",
            "Scope: " + ", ".join(task["scope"]),
            "Status: BACKLOG. Dependency checks and workflow approvals are not bypassed.",
        ])
        result = pm_create_issue(
            project_key=project_key, title=task["title"], description=description,
            issue_type="TASK", priority=task["priority"],
            assignee_principal=task["assignee_principal"],
            appetite_tokens=task["appetite_tokens"],
            appetite_timeout_s=task["appetite_timeout_s"],
            path_whitelist=task["scope"],
            forbidden_paths=task["forbidden_paths"],
            db=database,
        )
        created.append(f"{task['id']} -> {result['issue_key']}")
        known_titles.add(task["title"].casefold())
    return {"created": created, "skipped": skipped, "total": len(data["tasks"])}


def next_tasks(agent, *, db=None):
    data = load_manifest()
    database = db or get_pm_db()
    project = database.get_project_by_key(data["project_key"])
    issues = database.list_issues(project_id=project.id) if project else []
    by_id = {}
    for task in data["tasks"]:
        for issue in issues:
            if f"[ALLOCATION_ID:{task['id']}]" in issue.description:
                by_id[task["id"]] = issue
                break
    available = []
    for task in data["tasks"]:
        if task["assignee_principal"] != agent:
            continue
        issue = by_id.get(task["id"])
        if issue and issue.current_state.value not in ("BACKLOG", "REFINED", "STAGED"):
            continue
        if any(dep not in by_id or by_id[dep].current_state.value != "DONE"
               for dep in task["dependencies"]):
            continue
        available.append({**task, "board_issue_key": issue.key if issue else None})
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    return sorted(available, key=lambda task: (priority_order[task["priority"]], task["id"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="Import missing tasks to MAS-PM")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    parser.add_argument("--agent", help="List dependency-ready tasks for this agent principal")
    args = parser.parse_args()
    if args.agent:
        print(json.dumps(next_tasks(args.agent), indent=2))
    else:
        print(json.dumps(sync(dry_run=not args.sync or args.dry_run), indent=2))


if __name__ == "__main__":
    main()
