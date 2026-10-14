# Antigravity — GHA-03 local implementation instructions

Design candidate `25558aa0` is APPROVED WITH CONDITIONS. Read `GHA_03_REVISED_DESIGN_ACCEPTANCE.md` and incorporate its seven conditions into the shared specification and test matrix before coding. No separate CEO relay or approval is needed for this authorized bounded implementation.

## Implement

- Owner: Antigravity. Independent acceptance: Codex.
- New local modules in `mas/pm/gateway/` for strict JWT/RS256 verification, bounded single-flight JWKS cache, server-owned connector resolution and stateless observation validation.
- One local typed request/response interface; no public listener or production routing.
- Reuse GHA-02 strict manifest and artifact checks. Bind authenticated GitHub run/attempt to request coordinates. Use trusted server configuration for tenant/project and recheck tenant/connector status at completion.
- No persistent receipt, token/session issuance, replay-protection claim, phase/budget/evidence mutation, database migration or DeliveryService mutation call.

## Shared acceptance evidence

Implement real signed RSA fixtures and deterministic clocks/network stubs. Cover all revised TC scenarios plus duplicate payload keys, strict NumericDate types, missing claims, wrong run/attempt, decoded archive and envelope limits, absent required artifacts, invalid base64, cache TTL/cooldown equality, single-flight concurrency, failed-fetch throttling, oversized/duplicate JWKS keys and revocation during validation. Repeated valid tokens may validate again in this stateless slice; prove zero business writes and label that limitation honestly.

Test witness context cannot invoke submit/accept/coordinate or gain trusted storage/admin authority. Correct the design role table using current coordinator challenge-resolution ownership; do not modify core permissions.

Run targeted tests, final full quality gate and clean installed-wheel validation outside checkout. Record exact final candidate, actual counts/skips and known limits. Submission means ready for independent review, not accepted. Escalate any need for core/schema changes as a named scope deviation before implementation.

Deferred: durable security replay/receipt and source idempotency/freshness (GHA-04), check publisher (GHA-05), live workflows, provider dispatch and end-to-end rehearsal. This milestone alone does not automate the complete loop.
