# Antigravity — GHA-04 remaining mechanism corrections

Candidate `9ccea91d` is not approved for implementation. Read `GHA_04_REWORK_2_DESIGN_REVIEW.md`.

Design decisions: retain referenced artifacts under quota in the initial slice; defer expiry/deletion lifecycle. On stale/failed source freshness, fail closed for new admission and trigger background refresh; historical reads remain available. No synchronous API fetch inside DB transactions.

Correct these four mechanisms in actual schema/pseudocode, not just closure prose:
1. Fence source publication and ticket completion on matching ticket UUID/owner/fencing epoch/status/live lease inside one transaction. Late expired workers cannot publish or clear another ticket. Include bootstrap/failure/active-refresh handling and delayed-A-after-B tests.
2. Define authority mirror integration across actual IAM/registry mutators, connector-scoped identity, revoke-before-change and activate-after-change ordering, crash reconciliation and disabled admission when sync is unknown. Declare necessary API edits as proposed scope, not existing capabilities. Cover multiple connectors and multiple processes.
3. Add persistent per-admission quota reservation identities/leases/fences and per-blob deduplicated accounting. GC and receipt commitment must share exclusion so no new reference appears between reference check and unlink. Expired reservations cannot silently commit; include paused-worker/reaper/GC races. Use descriptor-safe no-follow blob verification.
4. Tie observation tenant/project/issue directly to its receipt via composite FK and parent unique key, not two independent FKs. Include direct SQL cross-owner insertion proof in the planned matrix.

Remove receipt artifact_status updates incompatible with immutability. Submit revised design/scenario mappings, keeping design agreement pending. No implementation or migrations yet; all previous witness-only and no-live boundaries stay in force.
