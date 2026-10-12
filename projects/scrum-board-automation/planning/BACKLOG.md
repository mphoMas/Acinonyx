# SBA unified backlog — Capable Coordinator Priority 1

One SBA project, one board, one delivery branch: `feat/scrum-board-automation`. Planning references below map to deployment-local issue keys; runtime state remains authoritative in MAS-PM. New coordinator records are BACKLOG, unassigned and zero execution appetite.

| Reference | Priority | Delivery owner | Dependencies | Outcome |
|---|---|---|---|---|
| SBA-01 | CRITICAL | Codex | None | Define the end-to-end board contract |
| SBA-02 | CRITICAL | Antigravity | SBA-01 | Discover and reconcile repository projects |
| SBA-03 | CRITICAL | Antigravity | SBA-01, SBA-02 | Publish conversation-derived plans into MAS-PM |
| SBA-04 | CRITICAL | Antigravity | SBA-01, SBA-03 | Integrate Antigravity agent progress and evidence |
| SBA-05 | CRITICAL | Codex | SBA-01 | Repair authenticated board actions |
| SBA-06 / CC-10 | HIGH | Codex | SBA-02, SBA-03, SBA-04, SBA-05, CC-07 | Deliver live project, task and activity views |
| SBA-07 / CC-13 | HIGH | Antigravity | SBA-04, CC-08, CC-09, CC-11, CC-12 | Qualify recovery, isolation and adversarial events |
| SBA-08 / CC-14 | HIGH | Codex | SBA-06, SBA-07 | Prove the CEO-to-agent-to-board workflow |
| SBA-09 / CC-15 | HIGH | Antigravity | SBA-01, SBA-04, SBA-07, SBA-08 | Automate Antigravity branch synchronization and task kickoff |
| CC-01 | CRITICAL | Antigravity | None | Prove developer and reviewer runtime capabilities |
| CC-02 | CRITICAL | Antigravity | CC-01 | Define coordinator contracts and authority |
| CC-03 | CRITICAL | Antigravity | CC-02 | Build durable coordinator state and outbox |
| CC-04 | CRITICAL | Antigravity | CC-03, SBA-03 | Implement authorized scheduling and task admission |
| CC-05 | CRITICAL | Antigravity | CC-01, CC-03 | Implement Antigravity development runtime adapter |
| CC-06 | CRITICAL | Antigravity | CC-01, CC-03 | Implement verifier and reviewer runtime adapters |
| CC-07 | CRITICAL | Antigravity | CC-04, CC-05, CC-06, SBA-04 | Automate rejection correction and resubmission |
| CC-08 | HIGH | Antigravity | CC-04, CC-07 | Handle plan changes and stale approvals |
| CC-09 | CRITICAL | Antigravity | CC-05, CC-06 | Manage isolated workspaces and integrated candidates |
| CC-11 | CRITICAL | Antigravity | CC-03, CC-05 | Implement pause cancellation and uncertainty controls |
| CC-12 | HIGH | Antigravity | CC-03, CC-11 | Provide coordinator operations and recovery runbook |


## Live integration packages

The [live-loop implementation plan](CC_LIVE_LOOP_IMPLEMENTATION_PLAN.md) maps proposed provider, candidate, verification, activity and correction packages to existing SBA/CC task identities. CC-09 is CRITICAL because export/integration is on the live delivery path. Existing runtime status, assignee, budgets and history are unchanged.

The four proposed contracts require Antigravity technical acknowledgement before backend implementation. Independent actual-container acceptance remains outstanding. Repository planning updates are not a claim of authenticated board publication, accepted runtime dependencies or live dispatch.
