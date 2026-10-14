# Independent GHA-03 design review

Reviewed design candidate: **54cc7916**. Review date: 14 October 2026.

## 1. Verdict & executive summary

**REJECTED (REQUIRES RE-WORK)** for gateway implementation agreement. The witness-only separation and offline rollout direction are retained. The proposed mechanism leaves replay, ingestion persistence, workflow authorization and revocation insufficiently specified to implement consistently.

This is a pre-implementation design return, not a new failed implementation submission. Count it separately in rework measurement. GHA-02 remains conditionally approved; its two nonblocking follow-ups are corrected in this candidate, with **77 targeted tests passed in 3.24 seconds**. No full-suite result is claimed for this new candidate.

## 2. Architectural findings

### High — Replay/receipt transaction is undefined

Sections 2/3 require rejecting reused `jti`, section 5 promises no database writes on any failure, TC-22 creates an ingestion record, and section 8 forbids schema changes. No replay store, receipt store, atomic claim protocol, crash state, expiry cleanup, or restart/multi-worker behavior is selected. Deferring semantic idempotency to GHA-04 does not supply authentication replay protection now. A memory set cannot establish durable replay protection after restart, and marking a token used before an unsuccessful request conflicts with the stated no-write rule.

Required design: choose an explicit offline validation-only first slice (no persistent INGESTED receipt/session/replay claim), or define the bounded durable replay/receipt store owned by GHA-03, with separately agreed additive migration scope. For ingestion, specify atomic token consumption plus receipt insertion, concurrent winner behavior, crash-after-commit response loss, retry with a fresh token, and revocation recheck at commit. Preserve GHA-04 logical source-action idempotency as distinct future work. State which failed requests leave business state untouched, which security/audit writes are allowed, and avoid universal zero-write promises inconsistent with logging or committed response-loss recovery.

### High — Workflow and action authorization profile is incomplete

Section 2.2 allows a direct admin workflow and assumes `job_workflow_sha` matches `workflow_sha`; reusable-workflow claims must not be assumed present in direct workflows. This expands the witness-only profile unnecessarily. The checks table matches SHA but does not bind exact approved workflow repository/path, caller event/ref/environment, or the GitHub run/attempt to the uploaded coordinator run. A pinned template alone does not prove candidate identity or independent verification. `workflow_dispatch` and PR merge SHA also need explicit treatment, not an assumption that token `sha` equals candidate head.

Required design: keep GHA-03 reusable-workflow/witness-only; defer direct admin maintenance. Pin exact workflow repository/path and SHA, require actual relevant claims, and define allowlisted event/ref/environment combinations. Distinguish GitHub `run_id`/`run_attempt` from MAS run coordinates. Either provide a trusted association for observation attachment or store uploads as untrusted quarantined observations only, with no trusted completion effect. Never let a payload select an authoritative repository root or assert freshness. Document that a compromised runner can submit claims and cannot create verifier evidence or acceptance.

### Medium — Token age and JWKS lifecycle leave gaps

`exp - iat <= 900` is lifetime, not maximum age. No positive lifetime or `now - iat` bound is specified; required claim types, duplicate JWT keys, maximum JWT/header size, RSA key parameters, fixed endpoint/redirect policy and expired-cache behavior are missing. The diagram accepts known cached keys without checking TTL; throttling and cold-cache/rotation behavior are not unambiguous.

Required design: define numeric strict temporal relationships and an actual maximum age with clock tolerance. Require bounded strict token/claim parsing and trusted RS256 key selection. Specify fresh known-key use, expired cache, unknown-kid refresh, single-flight and outage behavior. Never fetch token-controlled URLs or accept stale keys indefinitely. Add actual RSA-signature test cases, not only monkeypatched verification.

### Medium — IAM and request contracts are not mapped to existing APIs

The design asks `MultiTenantIAM` for project archival and connector revocation, but it currently models tenant/principal/session status; a project/connector registry and ownership are not defined here. Creating an ephemeral principal/session also conflicts with the pure read/no-write language. Section 4's permission labels do not consistently match existing delivery actions (for example challenge ownership must follow the actual delivery service). TC-18 ignores a role field although StrictModel forbids extra fields. The request schema omits archive representation, base/suite/brief/policy/fence coordinates and response storage identity; JSON and multipart are both allowed without a parsing profile.

Required design: name exact existing IAM verification/revocation operations and the proposed server-owned registry fields; distinguish future additions from existing capabilities. Prefer a per-request restricted witness context initially unless persistent session issuance is separately scoped. Use one initial request format and a complete bounded schema; reject role/tenant/actor extras rather than filtering them. Resolve full manifest/archive binding through GHA-02 without granting builder submission. Specify response authority labels precisely: authenticated transport can be true while result verification remains false.

## 3. Pillars

- Platform: offline-first and bounded JWKS are appropriate; durable ingestion and cache failure mechanisms need concrete definitions.
- Data: receipt/replay ownership and GitHub-to-MAS association are not yet authoritative contracts.
- AI: witness uploads remain untrusted observations; they cannot replace verifier/reviewer evidence.
- Governance: current authorization APIs and requested new registry/session functionality must be distinguished, with revocation checked at the action boundary.

## 4. Action directive

1. Amend the design and acceptance matrix before gateway implementation. Preserve witness-only separation and existing GHA-02 boundaries.
2. Select validation-only versus durable local ingestion explicitly, with named storage/transaction ownership and exclusions.
3. Resolve the workflow/claim and IAM mapping contracts, temporal/cache lifecycle, and request/response formats.
4. Add concurrency, restart, expired-cache, fresh-token retry, role-extra rejection, cross-task/run mismatch, revocation-after-validation and response-loss scenarios to the shared matrix. These are previously requested replay/recovery/authority guarantees, not new live functionality.
5. Resubmit the design for agreement. No public endpoint, live workflow, production enrollment, provider dispatch or database schema change is approved by this review.
