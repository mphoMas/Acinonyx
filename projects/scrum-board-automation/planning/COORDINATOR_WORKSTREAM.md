# Unified SBA / Capable Coordinator workstream

Owner directive: Capable Coordinator is Priority 1 and must use the current SBA board and branch. No second board or delivery branch is created.

Delivery branch: feat/scrum-board-automation. Unified portable backlog: BACKLOG.json. Existing SBA ticket IDs, history and review evidence remain intact. Eleven new coordinator records are registered in the cloud-local SBA database; four overlapping coordinator packages reuse existing records:

| Coordinator package | Existing SBA planning reference |
|---|---|
| CC-10 board activity | SBA-06 |
| CC-13 recovery/adversarial qualification | SBA-07 |
| CC-14 supervised end-to-end pilot | SBA-08 |
| CC-15 automatic startup | SBA-09 |

CC-01 through CC-09, CC-11 and CC-12 are additional records. They map locally to SBA-10 through SBA-20; LOCAL_BOARD_REGISTRATION.json contains the exact mapping. Other deployments allocate their own keys. Stable planning task UUIDs are now included in the portable backlog; these do not silently rebind existing runtime records.

## Pickup and ownership

Antigravity starts CC-01 runtime capability discovery now. Demonstrate supported start/status/result/cancel for both development and reviewer runtimes; notifications and log watchers alone cannot satisfy dispatch acceptance. Then CC-02 defines the shared coordinator contracts and CC-03 builds durable control state. All coordinator backend implementation belongs to Antigravity. Codex supplies frontend/interface requirements and reviews backend delivery; a separate reviewer is needed for designs/components Codex authored.

SBA-03 remediation remains a scheduling prerequisite, not a reason to block CC-01. SBA-04 supplies the actual agent event/submission foundation. Keep bounded verification and production approval distinct from the coordinator's message carrying. No executor credentials, budgets or runtime assignments are provisioned by this planning update.

The strengthened SBA-08 now requires actual automatic reviewer invocation, deliberate rejection/correction/resubmission, restart recovery and zero routine CEO message relays or ticket repairs. SBA-09 removes manual synchronization/startup only after that loop passes.

## Registration and visibility limits

New tasks exist in the cloud-local mas_pm.db, unassigned/BACKLOG with zero appetite. Existing runtime states, assignments and evidence are not changed. New dependency edges are registered locally. Expanded existing acceptance criteria are saved as planning proposals in Git; applying them to active runtime work requires authorized reconciliation.

Git publication does not update a separate Antigravity desktop database. Use the corrected authenticated planning publication path to reconcile this snapshot on that deployment after SBA-03 is accepted. Do not use its rejected implementation to change live scope or allocate execution allowance. No direct SQL, destructive key migration or copy of the cloud database is required from the CEO. Antigravity owns resolving deployment pickup and reporting actual board visibility.
