# Antigravity — GHA-03 design checkpoint

Next increment: authentication gateway and observation ingestion. Antigravity owns backend implementation; Codex independently reviews. GHA-02 approval is bounded offline approval and does not itself authorize live gateway activation.

## First action

Submit the gateway mechanism and acceptance matrix before implementation of any state-changing endpoint. Resolve the existing conditions in `GHA_01_REVISED_ACCEPTANCE_REVIEW.md`. Define:

1. The actual GitHub OIDC profile: reusable or direct workflow, available claims, issuer/audience, exact approved workflow commit SHA, numeric repository/owner IDs, event/ref/environment and permitted job/action. A mutable branch ref is not a pinned workflow.
2. JWT verification: allowed algorithms, signature and bounded JWKS retrieval/cache/rotation, exp/nbf/iat and clock tolerance, maximum token age, replay handling and unavailable-key failure behavior. Request fields must never choose a principal or tenant.
3. Server-owned mapping to a narrowly scoped, short-lived platform session. Verifier observation transport must not impersonate builder submission, reviewer approval or coordinator dispatch. Define who may perform each action and how revocation is checked.
4. Strict bounded request/response schemas, artifact/repository sources chosen by trusted configuration, error redaction and no state mutation on failed authentication/admission.
5. Transactional handoff and recovery: which writes this increment owns, which source freshness/idempotency rules are deferred to GHA-04, and how retries/unknown outcomes fail closed. No premature claim of exactly-once remote execution or current PR-head authority.

Share executable acceptance cases before coding: wrong issuer/audience/algorithm/key, expired/future/old tokens, wrong repository/owner/workflow/job/event, replay, cache rotation/failure, request-role spoofing, cross-tenant attempts, revocation, malformed/oversized requests and no-mutation failure checks.

Record design agreement and explicit exclusions. After agreement, implement the bounded library/local test integration first; public deployment, production credentials, GitHub workflow activation and check publication remain separate steps. Never place credentials in chat or commit them.

## Existing GHA-02 nonblocking follow-ups

- Replace global ZIP64 signature scanning with structural record checks so ordinary artifact bytes containing those sequences are not falsely refused. Add a valid STORED payload regression. This is compatibility correction, not evidence that failed artifacts were accepted.
- Correct stale candidate metadata in `GHA_02_DELIVERY.md`; use the externally recorded immutable commit identity, avoiding a self-referential amend loop.

No delivery-core/schema changes, provider dispatch, operational enrollment or branch protection edits are implied by this design handoff.
