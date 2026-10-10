# Scrum Board Automation backlog

Runtime status is authoritative in MAS-PM. This snapshot defines planned work, not completion. All newly created tickets are BACKLOG, unassigned and have zero execution appetite. Delivery ownership is a responsibility, not a runtime permission.

| Reference | Priority | Delivery owner | Dependencies | Outcome |
|---|---|---|---|---|
| SBA-01 | CRITICAL | Codex | None | Define the end-to-end board contract |
| SBA-02 | CRITICAL | Antigravity | SBA-01 | Discover and reconcile repository projects |
| SBA-03 | CRITICAL | Antigravity | SBA-01, SBA-02 | Publish conversation-derived plans into MAS-PM |
| SBA-04 | CRITICAL | Antigravity | SBA-01, SBA-03 | Integrate Antigravity agent progress and evidence |
| SBA-05 | CRITICAL | Codex | SBA-01 | Repair authenticated board actions |
| SBA-06 | HIGH | Codex | SBA-02, SBA-03, SBA-04, SBA-05 | Deliver live project, task and activity views |
| SBA-07 | HIGH | Antigravity | SBA-04 | Qualify recovery, isolation and adversarial events |
| SBA-08 | HIGH | Codex | SBA-06, SBA-07 | Prove the CEO-to-agent-to-board workflow |
| SBA-09 | HIGH | Antigravity | SBA-01, SBA-04, SBA-07, SBA-08 | Automate branch synchronization and Antigravity task kickoff |
