# Antigravity — GHA-04 durable ingestion design checkpoint

GHA-03 local stateless witness validation baseline `82407210` is independently accepted by review `3ca8fc4d`. Antigravity owns GHA-04 design and backend implementation; Codex reviews. First deliver design, schema proposal and executable acceptance specification. Do not implement code or migrations yet.

## Required mechanism

1. Separate GitHub token identity (issuer/jti), GitHub run/attempt transport identity, MAS execution identity, and scoped logical source-action identity. Define canonical semantic payload digest and immutable artifact references. A token replay rule must not pretend an action executes exactly once remotely.
2. Propose additive durable security/receipt and source-event storage: exact columns, ownership constraints, uniqueness, expiry/retention, migration/reopen/backfill and rollback behavior. Existing evidence, task mappings and budgets must remain intact.
3. Define the atomic admission protocol: fresh tenant/connector authorization and source generation, token consumption, immutable receipt and durable side-effect intent committed together where applicable. No successful receipt before durable commit. Specify concurrent duplicates, payload conflicts and reruns as separate observations of a logical action.
4. Define authenticated source registration/update. PR number, head/base SHA, repository and monotonically ordered generation must be server-authoritative, not caller-selected. State GitHub API/webhook trust, signature and event ordering, out-of-order/duplicate delivery and unavailable/unknown-freshness behavior. Recheck freshness at later submission/acceptance; do not certify currentness from an old cache.
5. Define crash/restart and response-loss transitions. Show exactly what retries with the same token, fresh token or same logical action return. Preserve IN_PROGRESS/UNCERTAIN and held reservations; never blindly redispatch or release funds when execution is unknown. Clearly distinguish receipt validation from candidate verification and human approval.
6. Define read-only receipt/query and future activity interface contracts, bounded storage/artifact quotas, redacted audit categories and key boundaries. Witness uploads still cannot impersonate builder/verifier/reviewer or create trusted evidence.

## Shared failure matrix

Before coding specify: concurrent same-token requests; fresh-token same-action retry; identical versus conflicting payloads; separate rerun attempts; restart after token/receipt/intent commit; dropped response; stale/out-of-order head update; head changing during admission; tenant/connector revocation race; missing/expired artifacts; storage failure; migration/reopen; cross-tenant/run references; UNCERTAIN recovery without duplicate work or budget release.

Provide numbered invariants, component ownership, transaction boundaries, state graph, schema proposal and concrete test inputs/expected outcomes. Mark proposed APIs/schema as proposed, not existing. Name all exclusions and resolve the mechanism with Codex before implementation.

No public endpoint, workflow activation, provider dispatch, check publisher, production credentials, branch protection changes or operational enrollment is implied. Start with a local deterministic integration profile. This design is the next step toward durable handoffs, not proof of the full loop.
