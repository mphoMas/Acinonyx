# Antigravity instructions: CC-03 recovery and board fixture cleanup

Owner: Antigravity implementation; Codex independent review. Date: 12 October 2026. Same SBA board and feat/scrum-board-automation branch. CC-04 dispatch remains gated.

## Synchronize without losing work

Commit or safely stash local changes, then fetch and integrate the latest shared branch. No force-push. Read CC_03_REWORK_REVIEW.md (review 5b83fde1) and these instructions. Preserve 03da60da and 77ba7083. Do not treat passing existing tests as proof that reproduced negative cases are fixed.

## Clean the CEO's local project selector

The repeated Dashboard Project (DP<number>) entries match tests/test_dashboard.py fixtures. Codex added private test database isolation, reversible archive markers, project-list filtering and a cleanup utility. Nothing is deleted. Confirm the exact database used by the running dashboard; an environment default is not proof if its launcher overrides it.

From /home/acinonyx/Desktop/MAS with the project Python environment activated:

```bash
python3 scripts/cleanup_dashboard_projects.py --db "${MAS_PM_DB_PATH:-mas_pm.db}"
```

Read the preview. It selects only exact Dashboard Project/DP numeric fixtures with at most one untouched BACKLOG Board Test Issue, no assignment/spend, no project source/plans/mappings/sprints/coordinator attempts, evidence/verdicts or dependencies. Real projects and used fixtures are preserved. Do not merge projects by name.

After confirming this is the server's database, run:

```bash
python3 scripts/cleanup_dashboard_projects.py --db "${MAS_PM_DB_PATH:-mas_pm.db}" --apply
```

The owner has authorized cleanup; no repeat owner permission is needed. A private SQLite backup is created. Restart the dashboard to load the updated list filter, then refresh the board. Verify real project IDs, keys and issue counts remain unchanged through the authenticated projects/board endpoints; capture the selector. Codex archived 8 matching fixtures only in the cloud database; this does NOT clean the CEO's separate local database. Do not claim local cleanup until the actual served selector is checked. Archive markers can be removed to restore visibility; preserve the backup.

## Fix authority once, at every mutation boundary

Solution: centralize a store mutation authorization helper. If trusted_coordinator_admin_scope is active, allow the explicitly trusted internal operation. Otherwise require an active tenant binding; raise PermissionError when absent. Compare its tenant to the tenant derived from persisted intent/attempt/run ownership. Require the agreed coordinator write capability and database-path ownership; recheck revocation at mutation time.

Call this helper from creation, claim, pre-spawn, heartbeat, completion, reaping, cancellation, termination observation, events and receipt writes. Supplied worker/fencing IDs are concurrency tokens, not credentials. Add tests for unbound, read-only, revoked and conflicting-tenant callers for each mutation family. Reads retain separate access rules.

## Make completion and termination receipt-driven

Remove default successful exit and default zero spend. Require an explicit trusted receipt identity, exact run/intent/attempt/generation, validated exit status and measured usage. Exit 42 must become failed execution, never SUCCEEDED. A caller-provided candidate string is not measured success.

For termination: accept only eligible cancellation/unknown states; find and validate the exact owned run before any state write. A nonexistent run must fail with no mutation. Require one matching row update and atomic state/accounting updates. A completed intent cannot be rewritten as canceled. Use receipt identity uniqueness for identical idempotent replay; conflicting replay must reject. Preserve uncertain holds when billing or remote termination remains unconfirmed.

Raw evidence receipts must always enter SUBMITTED. Remove caller-controlled ADMITTED promotion; separate trusted verification/signature/ownership admission before promotion.

## Conserve budget across every path

Validate amounts as strict nonnegative integers. Settlement cannot silently exceed its funded reservation. If an actual provider receipt exceeds the cap, retain an explicit overrun/uncertainty liability and require authorized reconciliation; never discard real cost or represent it as funded success.

In a single transaction: validate receipt and reservation state, post measured spend exactly once to project accounting, record reservation settlement/release, update owned outcome records. Termination costs must enter project consumption just like normal completion. Unconfirmed usage keeps holds. Separate developer/reviewer reservations or define one aggregate attempt settlement so two adapter completions cannot double-charge/release a shared reservation.

Low-level create_attempt/create_intent must be explicitly trusted persistence primitives, or enforce funded admission themselves. A zero reservation must not create scheduler-admissible unbudgeted work. Bind authorization_ref to actual durable authorization rather than an arbitrary string.

## Upgrade the actual previously shipped database

Test both pre-coordinator databases and databases created by 284cb877. CREATE TABLE IF NOT EXISTS alone does not upgrade old CC-03 columns or foreign keys.

Solution: explicit schema version migration with computed checksum. Acquire BEGIN IMMEDIATE, then recheck ledger/schema under that lock. Add admission_status with existing receipts defaulting SUBMITTED. Rebuild runs and dependent constrained tables using validated temporary tables and an explicit preservation map where SQLite cannot add the required composite foreign key. Keep IDs, history and evidence unchanged; reject contradictory old ownership rather than guessing. Perform foreign_key_check and integrity_check, record version/checksum and commit together. Check existing checksum on reopen. Backup and prove rollback with a mid-migration injected failure. Do not suppress unexpected OperationalError.

## Required negative acceptance cases

1. No binding/admin scope -> every mutation denied.
2. Exit 42 -> failed outcome, not success.
3. Reserve 10, report 20 -> no silent funded settlement/overdraft.
4. Termination with missing or foreign run -> zero mutations.
5. Termination of COMPLETED intent -> rejected; exact receipt replay -> idempotent.
6. Cancellation spend -> project accounting updated once; unknown spend -> hold retained.
7. Actual old CC-03 DB upgrade -> new column and composite constraint present; all historical rows preserved.
8. Caller ADMITTED status or fake receipt -> cannot obtain trusted admission.

Run targeted suites and bash scripts/run_quality_gate.sh. Actual gates are Ruff, CLI doctor/capabilities, research links, compilation and pytest. Report skips separately. Commit reviewable implementation/test/docs changes, push normally, and submit exact candidate hashes. Do not self-certify CC-03 or begin CC-04 dispatch before independent acceptance.
