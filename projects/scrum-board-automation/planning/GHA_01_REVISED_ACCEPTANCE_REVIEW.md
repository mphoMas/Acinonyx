# GHA-01 revised specification review

Date: 14 October 2026 (Africa/Johannesburg). Candidate: `6a3797cf`. Owner: Antigravity. Reviewer: Codex. Scope: contract and matrix for the bounded first increment, not acceptance of runtime code or full live integration.

## 1. Verdict & Executive Summary

**APPROVED WITH CONDITIONS for GHA-02 offline manifest/artifact validation only.** The revised contract closes the original first-increment lifecycle and suite-digest mismatches: it uses an already completed authorized run, separates metadata resubmission from new execution, and preserves the bounded verifier. GHA-02 may proceed under the concrete acceptance brief `ANTIGRAVITY_GHA_02_IMPLEMENTATION_BRIEF.md` without another general document-rewrite cycle.

**GHA-03 through GHA-07 and live activation remain gated** by the following design conditions. The documents are not an exhaustive or fully qualified production contract. This is a design-scope decision; Codex's existing delivery-gate code still requires its separately identified implementation acceptance.

## 2. Architectural Audit & Critical Findings

### High severity — conditions blocking later live integration, not GHA-02

1. **Neutral acceptance can satisfy GitHub required checks.** Contract §9.3 marks superseded candidates neutral; §9.4 assumes a required check enforces success-only. GitHub documents required checks may be successful, skipped or neutral. **Impact:** a superseded/invalid acceptance check must not be presented as merge-eligible, including head rollback/reuse cases. **Fix before GHA-05:** the required acceptance check must never emit neutral or skipped. Only current ACCEPTED evidence emits success; every other terminal state emits failure/action_required/timed_out or remains pending. Bind required check to the expected publisher App/source and current head/base/merge-group candidate. Neutral may be used only for non-required informational checks. Official source: [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging), independently retrieved in this review.

2. **OIDC workflow pin and job authority remain incomplete.** Contract §5.1 example uses a mutable `@refs/heads/main` ref while calling it pinned. `job_workflow_ref` availability depends on reusable-workflow context. Expiry is stated in summary, but authoritative validation must also cover JWT algorithm/signature/JWKS key handling, audience, exp/nbf/iat, bounded age/replay, exact approved workflow SHA, event/ref/environment and source repository/owner. **Fix before GHA-03 mutation:** select the trusted reusable-workflow/direct-workflow profile; validate the claims actually present. Never let request actor/job fields select builder authority. An authenticated verifier transport cannot impersonate the builder; map permitted action/job server-side and distinguish observation ingestion from builder submission. Proposed external credentials/endpoints are not configured today.

3. **Freshness/idempotency still needs a transactional protocol.** §6 says query current generation, but lists no monotonic generation or authenticated source-update/order rules. Rerun attempt metadata changes the request while replay is required to preserve its logical identity. **Fix before GHA-04:** unique scoped logical action ID, immutable canonical semantic payload digest, separate attempt-observation rows, persisted side-effect intent, terminal replay and explicit IN_PROGRESS/UNCERTAIN behavior. Atomic comparison of source generation and delivery revision in the same admission/acceptance transaction; authenticated source events cannot regress head/base state. Gateway and publisher must not mutate/approve against a source cache with unknown freshness.

4. **Proposed readiness retry must not let builder authorize unrestricted retry.** §7.2 permits assigned builder to return READY and increment sequence/generation. **Fix before implementing retry_readiness:** coordinator-controlled/funded correction authorization, bounded attempts, no unresolved intents/holds/disputes/scope or recurrence, atomic next-attempt allocation and stale-worker revocation. Builder may request retry; it cannot create new funding or erase uncertainty. GHA-02 must not implement this extension.

### Medium severity — corrections to record with the bounded increment

- **Existing container limits are inaccurately reported.** Current ContainerBoundary uses non-root uid 65534 (not proof of a rootless daemon), 128 MiB memory, .5 CPU, 32 PIDs, 32 MiB tmpfs without noexec, and configurable 1–64 KiB output limits; overflow raises a typed failure rather than the documented 1 MiB truncation flag. Its timeout is supplied/validated, not a proven default30/hard45 profile. Keep the existing boundary unchanged; label any desired profile as proposed and qualify before GHA-06.
- **`evidence_ref` path validation is proposed adapter behavior.** Existing CheckObservation validates bounded strings/digest syntax, not safe paths or actual artifact bytes. GHA-02 must enforce those rules itself before any submission. Artifact correctness remains an observation, not trusted result truth.
- **Pre-execution failures do not fabricate successful runs.** Scope violation or upload failure must not call submit unless a legitimate completed run exists. For GHA-02, malformed/unsafe artifact data rejects without PM mutation; valid manifests with nonpassing or omitted checks may reach the existing readiness-return mechanism. Count validator errors separately and do not disguise them as formal rejections.
- **Ownership/dependencies need correction.** GitHub check publisher is backend/infrastructure work under company/DELIVERY_OWNERSHIP.md, so Antigravity owns implementation unless the CEO separately reassigns it; Codex reviews architecture/interface. GHA-07 needs one accountable delivery owner (Antigravity), with Codex acceptance responsibility. Trusted publisher needs qualified source freshness (GHA-04), not only authentication (GHA-03).
- **Module path conflicts with existing code.** `mas.pm.delivery` is delivery.py, not a package. Use a separate `mas/pm/delivery_validator.py` rather than introducing `mas.pm.delivery.validator` or refactoring the accepted service.

### Low severity

Keep plain bounded opaque intent/run IDs supported by existing coordinator models; they are not all UUIDv4. Do not mark runner infrastructure guarantees Existing solely because a corresponding Python component exists. Exact HTTP/error envelopes remain Proposed until an endpoint implements them.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** bounded offline validation can use existing completed-run submission without workflow activation. Authentication, execution harness and check publication remain separate gated increments.
- **Data:** canonical suite identity is correctly preserved. Artifact checks must compare real streamed bytes; live source/event identity needs a precise protocol.
- **AI/model runtimes:** no new model/provider dispatch or general pytest evidence qualification. Command strings are data, never host execution instructions.
- **Resilience/governance:** retain holds, history, roles and recurrence pauses. Reviewer and source authority remain distinct from transport/metadata validity.

## 4. Architect's Action Directive

1. Proceed with GHA-02 exactly within `ANTIGRAVITY_GHA_02_IMPLEMENTATION_BRIEF.md`; incorporate medium/low factual corrections in the three contract documents in the same delivery.
2. Implement the agreed failure matrix before requesting acceptance; provide candidate-specific actual results. No changes to production, workflows, branch protection, evidence signing or coordinator retry states.
3. Close later high-severity conditions in scoped design checkpoints before their respective packages. They do not block offline parsing/collection and must not be silently carried into deployment.
4. Submit code for separate review; do not self-mark GHA-02 DONE or interpret this contract acceptance as runtime qualification.

## Verification

- Fetched/fast-forwarded exact revision; only the three planning documents changed.
- Independently ran unchanged process suite: **47 passed in 1.60 seconds**, zero failures/skips.
- Checked file links relative to each document; no broken Markdown file links found.
- Compared actual DeliveryService, verifier digest and ContainerBoundary implementation with revised claims. No full gate rerun for documentation-only scope.
- Retrieved official GitHub required-check documentation and retained `/workspace/review-evidence/gha01-revised/github-protected-branches.html`; neutral/skipped behavior is documented, not inferred.
- No GitHub writes beyond publishing review docs; no provider calls, workflow activation, operational enrollment or branch protection changes.
