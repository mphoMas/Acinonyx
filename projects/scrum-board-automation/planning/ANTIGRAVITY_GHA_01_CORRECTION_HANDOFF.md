# Antigravity: correct GHA-01 before implementation

Base candidate `6f620549`, shared branch `feat/scrum-board-automation`. Read `GHA_01_ARCHITECT_REVIEW.md` first. This is an early design correction intended to prevent implementation rework. Do not change application code, workflows, branch protection, production enrollment or the existing research denominators.

## Required bounded solution

1. **Split control plane and guest.** Trusted workflow/publisher/gateway validate event identity, fetch pinned source and collect bounded observations. The untrusted guest gets no GitHub/OIDC/MAS/provider/signing credentials or DB/socket access. GitHub check publisher is separate with minimal Checks write authority; candidate runner is not permitted to publish acceptance.
2. **Describe one exact lifecycle.** For the first increment, an already completed private coordinator run is the input. Offline validation binds observations to that run/candidate/brief. submit may produce READINESS_RETURNED or IN_REVIEW. It never implies signed acceptance. Re-reporting corrected metadata for the same completed candidate differs from producing new code: new code needs a separately authorized attempt and qualified execution path. Identify the missing readiness-correction transition as proposed; do not invent it or manually set READY/SUCCEEDED.
3. **Keep the qualified verifier.** Existing suite digest is canonical source_path/cases; add separate proposed oracle/harness/image provenance fields rather than changing its meaning. No general pytest/browser stdout signing. Candidate edits to tests are evaluated as data/code changes by an independently fixed oracle, not used to modify that oracle.
4. **Define proposed source/event ledger.** Immutable repository ID, PR/source identity, current head/base generation; logical action ID and immutable payload digest; atomic head/version checks and duplicate replay result. Store before side effects. Same action/digest returns original outcome; changed digest rejects; uncertain launch cannot be repeated automatically. New workflow attempts are observations of a logical dispatch, not automatic new paid dispatches.
5. **Define proposed authentication gateway.** Explicit GitHub OIDC/JWKS issuer/audience/expiry/workflow/ref/environment validation, server-owned tenant/action mapping and replay/TTL limits. Never pass a GitHub JWT directly to MultiTenantIAM as though it were a MAS session. Never map verifier transport to caller-selected builder identity. State that this gateway/endpoint and authorized ingestion interface are missing today.
6. **Make GitHub semantics valid.** Specify actual triggers and run_attempt rerun behavior, exact trusted workflow SHA and immutable oracle SHA, pinned action commits, Checks status/conclusion enum, expected check publisher and merge/head/base rules. Quarantine malformed/unknown job results; acceptance status remains non-success during outage, dispute, recurrence or stale head.
7. **Make runtime/artifacts bounded.** Reuse the existing ContainerBoundary/journal rather than a bare docker command. Define image/user/resource/deadline/output policies. Artifact manifest includes candidate/action/check identity and bounded safe paths/digests; reject traversal, symlinks, duplicates, missing bytes and partial uploads. Artifacts are observations, not proof merely because a hash matches.
8. **Correct the matrix.** Separate existing behavior from proposed checks, privileged SQL from supported API guards, nonpassing checks from omitted checks, and readiness from formal rejection. Include closure/check limits and explicit design review/reviewer challenge controls. Avoid exact exception messages not produced by the cited API.

## Resubmission deliverables

Revise:
- `GITHUB_ACTIONS_INTEGRATION_CONTRACT_V1.md`
- `GITHUB_ACTIONS_ACCEPTANCE_MATRIX.md`
- `ANTIGRAVITY_GHA_01_DELIVERY.md`

Add a closure section inside the delivery note: review finding -> revised section -> existing/proposed component -> negative acceptance scenario. Include an ordered implementation backlog: offline validator, authenticated gateway/ingestion, source-event ledger, trusted publication, qualified execution, recovery/pilot. One owner per package; keep the existing SBA stream.

## Proposed GHA-02 scope after contract review

An offline, non-activating validator/collector with strict versioned input, exact candidate/base/brief and completed-run binding, safe bounded artifact verification, scope inspection and structured readiness output. Test with private fixtures and supported authenticated Python calls. No arbitrary shell command execution, production DB path overrides, trusted actor flags, workflow deployment, general-repository trusted receipts or automatic paid dispatch. This narrow increment validates the transport/readiness contract first.

Push only the revised documents and report candidate SHA, actual checks and unresolved dependencies. Do not mark GHA-01 accepted, GHA-02 ready or the live loop complete yourself. Existing process tests passing do not verify the new workflow design.
