# Antigravity: GHA-03 design correction instructions

Read `GHA_03_DESIGN_REVIEW.md`. This is a design-only return; do not implement the gateway yet. GHA-02 approval is preserved and its compatibility/metadata follow-ups pass 77 targeted tests.

## Concrete solution path

1. Keep one reusable-workflow, witness-only profile. Remove direct admin workflow support. Bind approved workflow repository/path/SHA and explicit event/ref/environment conditions. Separate GitHub run IDs from MAS execution IDs. Candidate identity and current PR head are not proven by a pinned workflow.
2. Choose the first slice explicitly:
   - Simplest: offline validator returning VALIDATED_UNTRUSTED_OBSERVATION, no persistent receipt/session or durable replay promise. Define ingestion as deferred rather than claim it is implemented.
   - If retaining local ingestion: propose a separately scoped durable security receipt store/migration, with unique token identity and atomic token-consumption/receipt insertion. Define concurrent replay, restart, response loss and fresh-token retry. Preserve logical source-action idempotency for GHA-04. No schema work until design agreement.
3. Map a preconfigured tenant/principal/connector registry to actual IAM verification APIs. Check active tenant/principal/connector and current registry generation at the ingestion commit. Prefer per-request witness context; do not invent existing project-revocation APIs or mint privileged sessions.
4. Define strict RS256 token parsing with bounded JWT length, duplicate/extra-header handling, fixed JWKS endpoint and redirect restrictions, valid RSA parameters, fresh/expired caches, single-flight refresh, unknown-kid cooldown and outage refusal. Define positive lifetime, actual token age and clock tolerance separately.
5. Choose one request format initially. Provide exact schema and size limits for manifest/archive and response; forbid role/tenant/actor overrides. Bind full GHA-02 manifest coordinates through trusted tenant/repository configuration. Store candidate uploads only as untrusted claims; no delivery phase, acceptance, budget or verifier-evidence mutation.
6. Make failure invariants precise: no business-state mutation on validation failure; private security/audit records may be distinct. A committed receipt followed by network response loss cannot truthfully promise zero writes on every 5xx.
7. Update executable acceptance scenarios for the selected slice: real signed JWTs, absent/wrong workflow path, caller ref/environment, old and negative-lifetime tokens, cache expiry/rotation/outage, concurrent/restarted replay where supported, spoofed extras rejected, cross-tenant/task/run binding, revocation races and response loss where ingestion is retained.

Return a revised mechanism document, matrix and scope statement. Do not claim prose scenarios are tests already executed. No changes to delivery core, live workflows, external credentials, production enrollment or provider execution.
