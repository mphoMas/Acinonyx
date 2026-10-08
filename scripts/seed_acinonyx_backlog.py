#!/usr/bin/env python3
"""Idempotently seed the conversation-approved Acinonyx master backlog into MAS-PM.

Run from the repository root:
    python3 scripts/seed_acinonyx_backlog.py --dry-run
    python3 scripts/seed_acinonyx_backlog.py --apply

The SQLite database is local runtime state and is NOT populated by git pull alone.
Only BACKLOG issues are created. Existing issues are never modified or transitioned.
"""
import argparse
import json
from mas.pm.tools import get_pm_db, pm_create_issue, pm_create_project

TASKS = json.loads(r'''[
  {
    "id": "SEC-01",
    "title": "Audit exposed credentials and rotate affected secrets",
    "priority": "CRITICAL",
    "owner": "Security SRE",
    "dependencies": [],
    "scope": [
      "mas/",
      "scripts/",
      ".github/"
    ]
  },
  {
    "id": "SEC-02",
    "title": "Secure authenticated identities and reviewer authorization",
    "priority": "CRITICAL",
    "owner": "Backend Engineer + Security SRE",
    "dependencies": [
      "SEC-01"
    ],
    "scope": [
      "mas/dashboard/",
      "mas/pm/",
      "mas/security.py"
    ]
  },
  {
    "id": "SEC-03",
    "title": "Fail-closed evidence and commit-scope verification",
    "priority": "CRITICAL",
    "owner": "Security SRE + QA Critic",
    "dependencies": [
      "SEC-02"
    ],
    "scope": [
      "mas/pm/",
      "tests/"
    ]
  },
  {
    "id": "SEC-04",
    "title": "Prove atomic WIP, unique issue keys, and FSM safety",
    "priority": "CRITICAL",
    "owner": "Backend Engineer",
    "dependencies": [
      "SEC-02"
    ],
    "scope": [
      "mas/pm/",
      "tests/"
    ]
  },
  {
    "id": "OPS-01",
    "title": "Repair failing GitHub CI and verify Docker pipeline",
    "priority": "CRITICAL",
    "owner": "Platform/SRE",
    "dependencies": [],
    "scope": [
      ".github/",
      "Dockerfile",
      "docker-compose.yml",
      "scripts/"
    ]
  },
  {
    "id": "GOV-01",
    "title": "Eliminate self-certified releases and evaluator bypasses",
    "priority": "CRITICAL",
    "owner": "QA Critic + Red Team",
    "dependencies": [
      "SEC-03"
    ],
    "scope": [
      "mas/pm/",
      "tests/"
    ]
  },
  {
    "id": "PM-01",
    "title": "Validate Scrum board end-to-end against live MAS-PM",
    "priority": "CRITICAL",
    "owner": "Frontend Engineer + QA Critic",
    "dependencies": [
      "SEC-02",
      "SEC-04"
    ],
    "scope": [
      "portal/scrum.html",
      "mas/dashboard/",
      "tests/"
    ]
  },
  {
    "id": "PM-02",
    "title": "Make board the canonical intake and assignment workflow",
    "priority": "HIGH",
    "owner": "Product Lead + Backend Engineer",
    "dependencies": [
      "PM-01"
    ],
    "scope": [
      "portal/",
      "mas/pm/",
      "mas/dashboard/"
    ]
  },
  {
    "id": "PM-03",
    "title": "Define issue contracts, dependencies, and acceptance gates",
    "priority": "HIGH",
    "owner": "Chief Architect + Product Lead",
    "dependencies": [
      "SEC-04"
    ],
    "scope": [
      "mas/pm/",
      "docs/",
      "templates/"
    ]
  },
  {
    "id": "PM-04",
    "title": "Build agent claim, dispatch, and heartbeat lifecycle",
    "priority": "HIGH",
    "owner": "Agent Workflow Engineer",
    "dependencies": [
      "PM-02",
      "PM-03"
    ],
    "scope": [
      "mas/pm/",
      "mas/orchestration/",
      "tests/"
    ]
  },
  {
    "id": "PM-05",
    "title": "Integrate sprint planning, capacity, and flow analytics",
    "priority": "MEDIUM",
    "owner": "Product Lead + Backend Engineer",
    "dependencies": [
      "PM-02"
    ],
    "scope": [
      "mas/pm/",
      "portal/"
    ]
  },
  {
    "id": "PM-06",
    "title": "Implement immutable issue audit trail and rework history",
    "priority": "HIGH",
    "owner": "Backend Engineer",
    "dependencies": [
      "SEC-03"
    ],
    "scope": [
      "mas/pm/",
      "tests/"
    ]
  },
  {
    "id": "CU-01",
    "title": "Finalize computer-use threat model and permission boundaries",
    "priority": "HIGH",
    "owner": "Chief Architect + Security SRE",
    "dependencies": [
      "SEC-02"
    ],
    "scope": [
      "docs/",
      "mas/tools/"
    ]
  },
  {
    "id": "CU-02",
    "title": "Build isolated Playwright browser execution worker",
    "priority": "HIGH",
    "owner": "Agent Workflow Engineer",
    "dependencies": [
      "CU-01"
    ],
    "scope": [
      "mas/tools/",
      "tests/"
    ]
  },
  {
    "id": "CU-03",
    "title": "Implement independent browser, visual, and a11y verifier",
    "priority": "HIGH",
    "owner": "QA Critic + Frontend Engineer",
    "dependencies": [
      "CU-02"
    ],
    "scope": [
      "mas/tools/",
      "tests/"
    ]
  },
  {
    "id": "CU-04",
    "title": "Run defect-injection and forged-evidence regression suite",
    "priority": "HIGH",
    "owner": "Red Team",
    "dependencies": [
      "CU-03",
      "GOV-01"
    ],
    "scope": [
      "tests/",
      "mas/eval/"
    ]
  },
  {
    "id": "CU-05",
    "title": "Research native desktop computer-use executor",
    "priority": "MEDIUM",
    "owner": "Research Lead + Architect",
    "dependencies": [
      "CU-01"
    ],
    "scope": [
      "research/",
      "docs/"
    ]
  },
  {
    "id": "UX-01",
    "title": "Create Acinonyx design system and visual identity",
    "priority": "HIGH",
    "owner": "Design Lead",
    "dependencies": [],
    "scope": [
      "portal/css/",
      "docs/"
    ]
  },
  {
    "id": "UX-02",
    "title": "Refine board accessibility, keyboard use, and responsive UX",
    "priority": "HIGH",
    "owner": "Design Lead + Frontend Engineer",
    "dependencies": [
      "PM-01",
      "UX-01"
    ],
    "scope": [
      "portal/scrum.html",
      "portal/css/"
    ]
  },
  {
    "id": "UX-03",
    "title": "Repair research portal navigation and accessibility",
    "priority": "MEDIUM",
    "owner": "Frontend Engineer + QA Critic",
    "dependencies": [
      "CU-03"
    ],
    "scope": [
      "portal/"
    ]
  },
  {
    "id": "UX-04",
    "title": "Integrate anti-slop design linting and visual regression",
    "priority": "MEDIUM",
    "owner": "Design Lead + QA Critic",
    "dependencies": [
      "CU-03",
      "UX-01"
    ],
    "scope": [
      "scripts/",
      "tests/",
      "portal/"
    ]
  },
  {
    "id": "OPS-02",
    "title": "Define observability, token budgets, and circuit-breaker alerts",
    "priority": "HIGH",
    "owner": "Platform/SRE + FinOps",
    "dependencies": [
      "SEC-04"
    ],
    "scope": [
      "mas/observability.py",
      "mas/pm/",
      "docs/"
    ]
  },
  {
    "id": "OPS-03",
    "title": "Test database backup, recovery, and migration strategy",
    "priority": "HIGH",
    "owner": "Platform/SRE",
    "dependencies": [
      "PM-06"
    ],
    "scope": [
      "mas/pm/",
      "scripts/",
      "tests/"
    ]
  },
  {
    "id": "OPS-04",
    "title": "Publish release readiness checklist and pilot report",
    "priority": "MEDIUM",
    "owner": "Chief Architect + QA Critic",
    "dependencies": [
      "GOV-01",
      "OPS-01",
      "OPS-03"
    ],
    "scope": [
      "docs/"
    ]
  }
]''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write missing tasks to the MAS-PM SQLite database")
    parser.add_argument("--dry-run", action="store_true", help="Preview missing tasks (default)")
    parser.add_argument("--project", default="MAS", help="MAS-PM project key (default: MAS)")
    args = parser.parse_args()
    if args.apply and args.dry_run:
        parser.error("Choose --apply or --dry-run, not both")
    project_key = args.project.upper()
    db = get_pm_db()
    project = db.get_project_by_key(project_key)
    if not project and args.apply:
        pm_create_project(project_key, "Acinonyx MAS-Core", "Canonical Acinonyx engineering delivery backlog", db=db)
        project = db.get_project_by_key(project_key)
    existing = db.list_issues(project_id=project.id) if project else []
    # Exact source ID in description provides stable deduplication independent of generated issue keys.
    existing_ids = set()
    existing_titles = set()
    for issue in existing:
        existing_titles.add(issue.title.casefold())
        for task in TASKS:
            if f"[ALLOCATION_ID:{task['id']}]" in issue.description:
                existing_ids.add(task["id"])
    created = skipped = 0
    for task in TASKS:
        if task["id"] in existing_ids or task["title"].casefold() in existing_titles:
            print(f"SKIP   {task['id']}: {task['title']}")
            skipped += 1
            continue
        print(f"{'CREATE' if args.apply else 'PLAN  '} {task['id']}: {task['title']}")
        if args.apply:
            description = (
                f"[ALLOCATION_ID:{task['id']}]\\n"
                f"Proposed owner/role: {task['owner']}\\n"
                f"Dependencies (planning IDs): {', '.join(task['dependencies']) or 'None'}\\n"
                "Scope: " + ", ".join(task["scope"]) + "\\n"
                "Acceptance: independently verifiable implementation or documented research; "
                "passing relevant tests; attached empirical evidence; independent reviewer approval.\\n"
                "Initial state: BACKLOG. Do not auto-dispatch or claim DONE."
            )
            result = pm_create_issue(
                project_key=project_key, title=task["title"], description=description,
                issue_type="TASK", priority=task["priority"], assignee_principal=None,
                appetite_tokens=50000, path_whitelist=task["scope"], db=db,
            )
            print(f"       -> {result['issue_key']}")
            existing_titles.add(task["title"].casefold())
        created += 1
    print(f"\\n{'Applied' if args.apply else 'Preview'}: {created} new, {skipped} existing; {len(TASKS)} planned.")
    if not args.apply:
        print("Run with --apply to create issues. Git does not sync local MAS-PM database contents.")


if __name__ == "__main__":
    main()
