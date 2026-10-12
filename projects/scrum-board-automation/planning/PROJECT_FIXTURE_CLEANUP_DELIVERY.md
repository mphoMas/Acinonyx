# Project selector fixture cleanup

Delivered by Codex, 12 October 2026, under the owner's request to clean repeated project names.

Repeated Dashboard Project / DP numeric keys match tests/test_dashboard.py. That unittest class now owns a private temporary PM database, including when executed outside pytest. Existing test isolation in pytest alone did not cover standalone unittest execution.

scripts/cleanup_dashboard_projects.py previews narrowly selected unused fixtures and, with --apply, makes a private SQLite backup and archives project IDs. It deletes no projects or issues. Normal PM project lists exclude archive markers; explicit include_archived=True exposes historical records. Genuine work, assignments, spend, source registrations, plans, mappings, sprints, coordinator attempts, evidence, verdicts and dependencies protect a candidate from this cleanup. No name-based merging occurs.

Accessible cloud database: eight eligible fixtures archived; their records/tickets remain. Backup recorded in /workspace/review-evidence/project-cleanup-receipt.json. After standalone tests, a new preview found zero eligible fixtures. This does not establish cleanup of /home/acinonyx/Desktop/MAS on the CEO's separate machine. Antigravity's local application and authenticated API verification instructions are in ANTIGRAVITY_CC03_RECOVERY_INSTRUCTIONS.md.

Validation: cleanup, dashboard, discovery and browser suites: **58 passed in 37.98 seconds**. Standalone dashboard unittest invocation: **12 passed in 1.762 seconds**; operational fixture count did not increase. Ruff and git diff --check passed. No full repository gate was repeated for this scoped cleanup. CC-03/CC-04 acceptance gates remain unchanged.
