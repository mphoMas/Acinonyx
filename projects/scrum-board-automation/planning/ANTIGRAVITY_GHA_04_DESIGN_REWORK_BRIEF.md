# Antigravity — GHA-04 design solution instructions

Design `6099b8ae` requires revision. Read `GHA_04_DESIGN_REVIEW.md`. Do not code or migrate yet; GHA-03 stays accepted.

Use this smaller concrete architecture:

1. A witness validates and durably stores untrusted observations plus immutable receipts. It cannot change delivery phase, submit as builder, approve, refund funds or dispatch work. Keep actual delivery transitions through separately authenticated existing services.
2. Separate token consumption, generation-specific logical action, attempt observation and historical receipt. Include complete tenant/project/source/MAS binding, suite/policy and artifact identity. Add scoped action key/digest storage and composite ownership constraints. Permit multiple checks/tasks per GitHub run; do not make run/attempt the only receipt key.
3. Specify retries precisely: current valid authentication plus same logical action/digest resolves existing outcome, conflicts409; same token never mutates twice. Fresh tokens support response-loss recovery, including after old token expiry. Historical receipt reads do not re-admit stale work.
4. Append-only source notification/history plus one uniquely constrained current projection. Choose a server-authoritative serialized refresh/CAS protocol that handles force pushes, delayed/out-of-order responses, base changes and closed/reopened PRs. No ancestry/timestamp-only ordering and no arbitrary caller source authority.
5. Define authority linearization across PM/IAM/connector stores. A SQLite PM lock alone does not protect IAM revocation. Define coordination/generation fences and exact recheck/commit ordering in local tests.
6. Stage artifacts safely outside the business DB transaction, verify/hash/fsync and atomically promote without overwrite before creating committed references. Define quota reservations, existing-blob revalidation and orphan cleanup. Read-only permission bits are not an immutability guarantee.
7. Avoid a new generic external-effect journal for local ingestion. Rollback leaves no receipt, response loss uses durable action replay. Defer remote effect recovery unless a full separately scoped outbox/fencing/reconciliation protocol is proposed. Keep budgets unchanged.
8. Define explicit expiry/retention and immutable history versus mutable projections. Give authenticated read contracts and migration/reopen/rollback rules. Correct cap/signature/ownership claims.

Return revised numbered invariants, DDL/keys/FKs, state graph and acceptance scenarios with concrete expected outcomes. Keep proposed APIs labeled proposed. No live listener/workflow/provider activation, production credentials or core/schema implementation before design agreement.
