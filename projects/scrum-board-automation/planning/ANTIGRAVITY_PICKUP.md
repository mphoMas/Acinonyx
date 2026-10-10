# Antigravity pickup — Scrum Board Automation

Delivery branch: `feat/scrum-board-automation`. Merge target: `Acinonyx_frontier`.

## Start here

After loading this branch in Antigravity, give the team this instruction:

> Read AGENTS.md, company/DELIVERY_OWNERSHIP.md and projects/scrum-board-automation/planning/ANTIGRAVITY_PICKUP.md. Review BACKLOG.json, BOARD_CONTRACT_V1.md, SBA_01_DECISIONS.md and ANTIGRAVITY_HANDOFF.md in this directory. First acknowledge the proposed SBA-01 contract, document any required changes and identify your actual runtime hooks and authenticated MAS-PM integration. Do not declare the contract accepted on behalf of Codex or the independent reviewer. Once agreement, review, authenticated assignment and execution budget are recorded, begin dependency-ready backend tasks in priority order. Publish actual task activity, comments, blockers and candidate-specific evidence through the supported MAS-PM integration. Where that integration is not yet available, explicitly record the gap and repository delivery evidence; do not claim live board updates. Preserve server-side authorization, tenant isolation and independent completion review. Codex owns frontend work. Never mark a task DONE from a commit or your own success claim alone.

## Backend sequence

1. Contract acknowledgement/discovery for SBA-01. Record the accepted candidate commit, deviations and actual runtime integration entry points in SBA_01_DECISIONS.md.
2. SBA-02: repository project discovery and reconciliation.
3. SBA-03: architect planning publication.
4. SBA-04: actual Antigravity activity/evidence adapter.
5. SBA-07: recovery and adversarial qualification.
6. Support Codex integration/acceptance in SBA-06 and SBA-08.
7. SBA-09: automate the manual branch synchronization and kickoff process after the first workflow is qualified.

SBA-05 and SBA-06 frontend implementation remains Codex-owned. Dependencies are completion gates, not merely document references. Use task-level scopes and named independent reviewers; no unlimited execution budget is granted by this handoff.

## Board reconciliation

The committed BACKLOG.json is the portable planning snapshot. LOCAL_BOARD_REGISTRATION.json records cloud-local issue mappings, not proof of desktop board registration. The legacy work_queue/tasks.json importer currently imports MAS allocations, not this SBA snapshot. Do not assume it will populate SBA on IDE startup. Antigravity must reconcile the SBA snapshot through supported PM APIs in the configured deployment, preserve stable planning references and existing runtime state, and record that deployment's local key mapping. No direct SQL writes or copy of the cloud SQLite database.

This initial setup gap is part of SBA-02/SBA-03; the finished CEO workflow must not depend on these manual import steps.

## Delivery evidence

For each task record planning/local issue reference, authenticated delivery identity, candidate commit, changed paths, actual commands/results, unresolved issues and separate review. Keep credentials out of Git. Preserve dirty worktrees; do not force-reset the CEO's checkout. Merge conflicts and unavailable authentication are blockers to report, not reasons to skip controls.

Pickup publication is not acknowledgement or execution. Only the actual Antigravity run establishes those facts.
