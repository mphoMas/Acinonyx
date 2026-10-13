# Delivery process enforcement contract v1

Owner authorization: embed the research remedies into the process, 13 October 2026. Implementation owner: Codex under this explicit assignment. Separate implementation acceptance remains required.

## Supported boundary

A durable, project-enrolled delivery gate protects supported CoordinatorStore intent creation, pre-spawn, completion linkage, evidence-review admission and PM completion writes. Enrollment is explicit and irreversible through supported service methods; it refuses unresolved existing execution. Legacy un-enrolled projects retain their separately accepted scope. This is not universal historical migration, live provider activation or automatic conversational handoff.

Authenticated callers need storage write plus `delivery:coordinate`, `delivery:submit` or `delivery:review` as appropriate, refreshed by current tenant authority on every operation. Only the coordinator principal assigned in the brief can coordinate it; builder/verifier/reviewer are distinct. Explicit trusted host administration may configure records under a declared actor; this is not an exposed identity fallback.

## Required rules and failure checks

- G01: versioned brief includes exact base SHA, issue policy, bounded requirements/checks, permitted scope and named actors; reviewer attests the mechanism and builder acknowledges before dispatch.
- G02: additive checks cover every requirement and include a negative case; a critical task requires an enforcement-design explanation. Metadata is not proof that design is correct.
- G03: admitted intent is linked to the current brief version and exact task; stale/missing/changed/paused/disputed briefs fail at creation and pre-spawn. Checks participate in existing SQLite transactions.
- G04: successful execution is distinct from process acceptance. Submission references the actual completed run/candidate and all check observations. Missing/nonpassing observations become durable readiness returns; no self-acceptance.
- G05: blocking findings cite existing requirement, reproduction or essential missing evidence, impact and closure paths. New scope is recorded separately. Optional improvements cannot silently become blockers.
- G06: closure covers each open finding; repeat rejection of a claimed-closed requirement triggers durable recurrence pause. A coordinator design decision is required before correction resumes.
- G07: builder may challenge a finding; coordinator disposition is recorded, cannot create acceptance, and does not erase past return/rejection records.
- G08: acceptance requires independent current verifier/reviewer receipts checked by the existing service-owned cryptographic trust implementation, matching the enrolled roles, current candidate, policy and suite. Scoped acceptance does not grant release authority.
- G09: readiness returns, design changes, scope changes, challenges, rejections and recurrence are append-only observations. Retries cannot overwrite evidence or disappear across reopen. CAS revisions prevent competing stale decisions.
- G10: uncertainty retains existing funding holds and execution quarantine. Gate decisions never release money, terminate guests, authorize retries or register adapters on their own.

## Readiness evidence and limits

Run targeted authority/CAS/recurrence/admission tests, existing coordinator/evidence/board regressions, historical migration/reopen checks and the full actual repository quality gate. Test cross-tenant/unbound/revoked/wrong-role denial, malformed input, direct low-level dispatch bypass, changed policy, fabricated success, reopened pauses and duplicate decisions. No production enrollment, active ticket migration or live dispatch is implied by tests.
