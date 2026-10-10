# Antigravity handoff: Scrum Board Automation

- MAS-PM project: SBA. Tasks SBA-1 through SBA-9; stable planning references SBA-01 through SBA-08 map in LOCAL_BOARD_REGISTRATION.json.
- Outcome: the CEO describes projects and starts Antigravity; plans, agent activity, comments, evidence and guarded progress reach the live board automatically.
- Backend delivery owner: Antigravity development team (SBA-02, SBA-03, SBA-04, SBA-07, SBA-09).
- Frontend and coordination owner: Codex (SBA-01, SBA-05, SBA-06, SBA-08).
- Integration coordinator: Codex; technical contract acknowledgement required from Antigravity.
- Separate reviewer: appointment pending; cannot be the implementation owner.
- Baseline: feat/scrum-board-automation, branched from Acinonyx_frontier at 3748443d3a87b7738ae5271253334866c58771ba; initial planning commit 98034d89.
- Allowed files: per-task scopes in BACKLOG.json. Shared files require one named implementation owner.
- Dependencies: agree SBA-01 before backend work; do not bypass the dependency graph or normal FSM.
- Contract: not yet signed. Define project registry, planning revision API, authenticated identity/session access, agent event ingestion, comments/evidence storage and live activity reads. Preserve tenant isolation and independent completion review.
- UI: real project selector, authoritative status, activity/evidence details, visible errors, loading/empty/denied/disconnected states and freshness indicator.
- Required authority: scoped repository and authenticated project/task access. Planning ownership grants no runtime permissions. Never publish bearer credentials.
- Evidence: candidate-specific commits, actual executed checks, recovery/adversarial results and native-browser end-to-end proof with the actual Antigravity runtime.
- Acknowledgement: pending. This file is a repository handoff, not a message sent to or evidence of execution by Antigravity.

Start with contract discovery. Do not use the bounded mas-swarm Python function workflow as a substitute for Antigravity repository delivery. No task has been preapproved, dispatched or marked DONE.
