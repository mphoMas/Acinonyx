# Acinonyx Git Work Queue — Agent Operating Contract

## Platinum Lodge project pickup

The [Platinum Lodge pickup instructions](PLATINUM_LODGE.md) define four queued coordination tickets, delivery ownership and synchronization of the separate 55-record PLG project. Antigravity starts with `PLG-BOARD-01`; Codex retains frontend/design ownership. All entries remain BACKLOG and require actual identity binding and normal review.

The source of truth for **planned allocations** is [`work_queue/tasks.json`](tasks.json). The MAS-PM SQLite database is the source of truth for **runtime state**, evidence, and review verdicts. The dashboard reads the database; do not write directly to SQLite from an agent.

## Fully repeatable pipeline

1. The Chief Architect publishes or revises task allocations by committing `work_queue/tasks.json` to `Acinonyx_frontier`.
2. Antigravity synchronizes its checkout using Git (normal `git pull` or its built-in repository sync).
3. When `python3 main.py --mode dashboard --port 8080` runs, MAS-PM automatically imports any missing tasks. The dashboard watches for changes to the checked-out manifest every 30 seconds. Set `MAS_GIT_QUEUE_AUTOSYNC=false` to disable the watcher.
4. An agent discovers **its own** dependency-ready work using `PYTHONPATH=. python3 -m mas.pm.git_queue --agent <principal>`.
5. The agent follows the existing MAS-PM FSM and evidence requirements. It must not automatically move tasks to IN_PROGRESS, DONE, or bypass judicial review. A proposed reviewer must not be the builder.

The queue is **not** an autonomous dispatcher. Antigravity must initiate the agent, and Git must update the local checkout. Neither a remote Git commit nor a new manifest revision by itself reaches an offline workstation.

## Antigravity master instruction

> Read `work_queue/README.md` and `work_queue/tasks.json`. Identify your authenticated MAS agent principal and run `PYTHONPATH=. python3 -m mas.pm.git_queue --agent <principal>`. Choose the highest-priority returned task. If the list is empty, report that no dependencies-cleared work is available; do not invent tasks or bypass dependencies. Read the task's scope, forbidden paths, acceptance criteria, and reviewer. Verify that the board record exists (the dashboard auto-imports on startup; use `PYTHONPATH=. python3 -m mas.pm.git_queue --sync` for a one-time recovery if the server is not running). Follow the FSM's permitted transitions and request authorized human/agent approval when required. Implement only in the allowed paths, run tests, attach verifiable evidence, and submit for independent review. Never claim DONE without the actual MAS-PM state transition and required critic verdicts. Do not reveal or commit secrets.

## Agent allocations

| Principal | Planning IDs |
|---|---|
| `security_sre` | SEC-01, SEC-03 |
| `backend_engineer` | SEC-02, SEC-04, PM-06 |
| `platform_sre` | OPS-01, OPS-03 |
| `qa_critic` | GOV-01, CU-03 |
| `frontend_engineer` | PM-01, UX-02, UX-03 |
| `product_lead` | PM-02, PM-05 |
| `chief_architect` | PM-03, CU-01, OPS-04 |
| `agent_workflow_engineer` | PM-04, CU-02 |
| `adversarial_red_team` | CU-04 |
| `market_researcher` | CU-05 |
| `design_lead` | UX-01, UX-04 |
| `finops_governor` | OPS-02 |

These principals are proposed execution roles; the running MAS deployment must authenticate them and may require mapping to its actual registered agents. Reviewer principals are independently specified in the JSON.

## Troubleshooting

- Board shows no issues: verify the integrated server is running, the current checkout includes `work_queue/tasks.json`, and check the startup log for `MAS-PM Git queue`. Use `PYTHONPATH=. python3 -m mas.pm.git_queue --sync` for a diagnostic manual recovery.
- Task is not ready: dependencies must be in actual MAS-PM `DONE` state, not merely committed or described as complete.
- Existing issue is not updated: import deliberately never rewrites existing issues, their assignees, or workflow state. A separate audited reconciliation/assignment workflow is needed for safe changes.
- Dependency links are currently checked in the Git queue's pickup logic; they are **not** relational `pm_dependencies` edges. A future task should integrate this with MAS-PM's native dependency model.
- Remote Git updates require a Git pull or automated checkout synchronization; this process does not fetch from GitHub itself.
