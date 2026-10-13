# Delivery gate v1: operator and integration guide

## What is implemented

`mas.pm.delivery.DeliveryService` stores a project-enrolled, durable delivery process in the existing PM database. It validates shared briefs, role agreement, readiness, justified findings, related-path closure, challenges, scope disposition and recurrence. Admission/pre-spawn and PM DONE writes enforce the gate. This Python service is an integration boundary; it is not a new public HTTP endpoint or a live agent bridge.

Existing projects are NOT automatically enrolled. Existing accepted controlled-synthetic and evidence scopes remain separate. Enrollment blocks new dispatch for every issue in that project until a brief is agreed, refuses existing unresolved execution/funding and cannot be disabled through the service. A supported gate does not broaden the qualified adapter registry, authorize provider calls, grant release rights or imply production acceptance.

## Authority

Use the existing `tenant_scope(iam, session, tenant, root)` around calls, with the PM database resolved from that binding. Roles are assigned in the brief; they are not taken from display names or request metadata.

- Every service user needs `storage:read` and `delivery:read`.
- Coordinator additionally needs `storage:write` and `delivery:coordinate`.
- Builder additionally needs `storage:write` and `delivery:submit`.
- Reviewer additionally needs `storage:write` and `delivery:review`.
- Dispatch service additionally needs current coordinator storage authority and `delivery:dispatch`.
- Cryptographic verifier/reviewer/admitter authorities remain the existing dedicated coordinator evidence permissions, not replaced by delivery roles.

Four distinct assigned principals are required in this bounded version: coordinator, builder, verifier and reviewer. They may use the same provider with different roles, but the builder cannot approve its own work. Every request rechecks current IAM authority. No credentials are provisioned by this feature.

The existing explicit trusted-host coordinator scope plus `delivery_admin_actor` is permitted only for trusted local administration/tests. Never expose it as a caller-selected identity fallback or grant it to untrusted agent tools. Raw database/socket access remains privileged; this gate does not contain host administrators.

## Normal sequence

1. Trusted coordinator calls `enroll(project_id, tenant_id)` on an idle project.
2. Coordinator calls `establish(issue_id, brief)` with exact base SHA, immutable suite digest, current policy version, scope, named principals, mechanism, requirements and positive/adverse checks for each requirement.
3. Reviewer calls `agree(..., role='reviewer', rationale=...)`; builder calls `agree(..., role='builder', rationale=...)`. Both use the current integer CAS `revision` returned by `get`.
4. Existing admission creates a funded intent. Direct CoordinatorStore admission cannot bypass the brief. Pre-spawn checks the same current version in its transaction and links the physical run.
5. Successful execution records AWAITING_SUBMISSION, not acceptance. Builder calls `submit` with actual completed run/candidate and bounded check observations plus all finding-closure paths. Observations are claims for readiness, not trusted execution proof.
6. Incomplete/nonpassing observations produce append-only READINESS_RETURNED records. Complete observations produce IN_REVIEW. Neither permits DONE.
7. Existing operator-owned verification and independent reviewer issue the qualified signed receipts. Service startup configures `db.coordinator` with service-owned EvidenceTrust; no per-call trust keys.
8. Reviewer calls `accept` with verification/review IDs. Both receipts are validated again in the same transaction, against current execution, roles, candidate/base/policy, suite digest and agreed case IDs. The implementation remains limited by the existing qualified verifier contract; arbitrary repository/browser evidence is not newly qualified here.
9. Normal FSM/critic/release controls still apply. Direct PM DONE writes also require current delivery acceptance; issuer revocation invalidates that check. Scoped process acceptance is not release approval.

## Rejection and recurrence

`reject` requires an existing requirement ID, reproduction or essential missing-evidence explanation, impact and closure paths. Unknown requirements must use `request_scope_change`; they cannot become an original-defect rejection. A coordinator may establish an updated version (with new agreements) or explicitly decline the scope proposal. Ordinary `resume` cannot skip a pending scope decision.

For existing defects, coordinator `resume` records a correction plan. A subsequent submission must cover every open finding and its related paths. A new rejection of the same previously claimed-closed requirement causes RECURRENCE_PAUSED even if its finding ID changed. Only assigned coordinator reassessment can resume; it cannot erase prior events or authorize additional spending.

Builder `challenge` records an objection and pauses correction. Coordinator `resolve_challenge` records upheld/overturned disposition; it does not accept work. If all blockers are withdrawn, `resume_review` permits re-reviewing the same candidate, avoiding unnecessary implementation retries. Overturned findings are not automatically assigned to a provider or classified as reviewer error; the reason remains in the audit trail.

## Uncertainty, recovery and migrations

Cancellation, lease expiry and interruption record UNCERTAIN. Existing funded holds and physical containment/recovery remain authoritative. `reconcile_execution` only resumes when intents are authoritatively terminal and holds resolved by existing authorized accounting; the gate never performs settlement itself.

Migration `2026101301` is additive/content-checksummed and does not edit old coordinator migration identities. Reopen verifies all new table/trigger definitions against that migration; an existing ledger is insufficient if required enforcement objects are missing. Events and submissions are append-only. CAS decisions and dispatch/run updates use the existing BEGIN IMMEDIATE transaction.

Readiness metadata is not semantic correctness. The database records role attestation and closure claims; independent technical review is still required. No existing production project, live board, task status or credentials are changed by this guide or the code tests.

## Measurement and readiness scope

`metrics` counts readiness returns, formal submissions/rejections, recurrence pauses, scope requests, design reassessments, challenges, overturned findings and acceptances. No hours or automated provider ranking is inferred. New observations cannot hide repeats by overwriting submissions.

Before live deployment, obtain separate implementation review, configure IAM and EvidenceTrust in the actual trusted service, select an idle project for deliberate enrollment, and connect real producer/reviewer clients and activity presentation. The full no-owner-relay loop remains a distinct integration milestone.
