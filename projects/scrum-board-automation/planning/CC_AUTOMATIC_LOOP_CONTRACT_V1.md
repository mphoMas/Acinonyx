# Bounded automatic correction loop — proposed v1

Contract ID: `mas-automatic-loop-v1`. Design owner: Codex; backend/integration owner: Antigravity under CC-07. Separate design acknowledgement pending Antigravity. Dependencies are phased in [CC_LIVE_LOOP_IMPLEMENTATION_PLAN.md](CC_LIVE_LOOP_IMPLEMENTATION_PLAN.md). Status: proposed contract, not live runtime approval.

## Outcome and profiles

An authorized task is developed, exported, verified, independently reviewed and, if rejected, corrected without the CEO carrying messages. The CEO remains involved in scope/business decisions and required separate human release/integration approval. This loop does not bypass that approval.

Profiles must be explicit:

1. **Bounded solve profile:** current operator-owned solve(payload) verification with trusted host expectations, exact source/base commits and pinned worker image. This is the implemented verification foundation, not proof that live provider/adapter/export integration exists.
2. **Repository profile:** initially unsupported. Before enabling it, qualify an owner-controlled external test driver/oracle and candidate isolation, including how actual application outputs are measured without importing candidate code into the verifier. Guest pytest summaries, exit 0 or candidate-written JUnit/coverage files are operational signals only. Do not promote them to completion evidence. Candidate-modified tests cannot redefine the owner's oracle. Runtime/container data channels may expose application outputs; verdict construction and expectations stay outside candidate control.

Each task admission declares a supported profile, exact scope, acceptance suite, dependency evidence, identities, policy and approved limits. An unsupported project/profile is a visible blocker, not a silent downgrade to solve or a fabricated QA pass.

## Durable stages and handoffs

These are coordinator job stages, not new PM issue states:

| Stage | Required behavior / exit evidence |
| --- | --- |
| ADMITTED | Current authenticated task assignment, scope, dependency/WIP/budget authority and durable intent |
| DEVELOPING | Qualified supervised runtime, broker channel, early session record and bounded observations |
| EXPORTING | Trusted exporter creates an immutable authorized candidate or rejects proposal |
| VERIFYING | Independent verifier measures the owner suite against exact candidate/base/image |
| REVIEWING | Separate reviewer receives immutable diff, current measured evidence and policy binding |
| REWORK_PENDING | A deterministic rejected-outcome receipt creates one next-attempt intent |
| AWAITING_REQUIRED_APPROVAL | Exact candidate ready for the separately authorized human/policy gate |
| INTEGRATING | Authorized merger reconciles expected target ref and confirms exact integrated candidate |
| COMPLETION_PENDING | Existing PM completion guards evaluate current required evidence/approvals |
| COMPLETE / ESCALATED | Guarded completion, or durable actionable reason and held liabilities |

Issue states continue through the existing FSM; do not equate job stages with permitted ticket transitions. All handoffs are durable outbox records with a stable handoff ID, canonical digest, originating receipt, task/attempt/run/policy/generation, destination role and next-stage expectation. External dispatch happens after commit, never while holding a write transaction. Acknowledged receipt commits the next handoff exactly once logically; transport remains at-least-once with idempotent reconciliation.

Default pilot bounds: at most three development attempts (initial plus two corrections), at most twelve provider calls across the loop, task deadline at most 600 seconds, per-provider call at most 45 seconds and per-candidate execution at most 30 seconds, all clipped to remaining authorization/deadline. Operator policy may lower these. Token/currency allocations remain zero until separately authorized. Deadline, consumed retries and reservations are durable and cannot reset on restart. Required cleanup may extend observation beyond work deadline; uncertainty blocks retries and retains funding.

## Rejection and correction

Verifier failures and reviewer REJECTED results become normalized bounded findings: finding_id, severity, affected_path (within scope), evidence_reference and corrective_requirement. Separate operator/verified findings from untrusted runtime commentary. Feedback artifacts are data; strip active content and never execute embedded commands or follow arbitrary links.

One rejection receipt plus its current generation creates at most one correction intent. Repeated delivery returns the same intent; conflicting receipt content is a conflict. The next attempt uses the same stable task identity with a new attempt sequence/run/generation and candidate; historic evidence remains immutable. Old approvals cannot transfer to new candidates.

Before correcting, re-evaluate authority, scope, dependencies, profile, active policy, target base, remaining time/funding, cleanup confirmation and retry ceiling. Out-of-scope recommendations request a policy/scope decision rather than expanding rights. If corrective requirements conflict or imply unrelated work, escalate a concise decision instead of repeated speculative edits.

A builder may resume a real session only when the runtime proves that capability and the old execution is confirmed stopped. It may not reuse old execution authority. Unknown provider/runtime/integration state, orphan uncertainty or held liabilities prevent automatic retry until reconciled.

## Approval, completion and escalation

Reviewer APPROVED must be a strict current candidate-bound result from a separate currently authorized issuer. Review cannot substitute for verification or authorize a different integrated commit. APPROVED WITH CONDITIONS is not unconditional completion; deterministic policy must explicitly classify each condition and require its evidence. Unknown conditions block.

Apply only authenticated existing PM transition/verdict operations. Separate human approval remains required where configured; a builder, model, coordinator or conversational CEO intent cannot impersonate the approver. If integration changes the candidate, return to verification/review and obtain the required approval for the new exact candidate.

Escalation categories: unsupported runtime/model/profile, conflicting scope, exhausted attempts/time/budget, unresolved execution/provider/integration, authentication revocation, unreconciled policy change, immutable evidence mismatch, infrastructure unavailable and protected-ref conflict. Persist category, concise decision needed, exact candidate/run, available evidence and liabilities. Ordinary retries and progress do not create repeated CEO notifications. Suppress duplicate escalation IDs; route only through an authorized notification channel. No Slack/email transport is implicitly authorized by this contract.

Pause stops new admissions/handoffs/provider calls; cancellation revokes generation/channel then confirms whole-boundary cleanup. Shutdown/restart resumes only durable eligible handoffs after authority checks; it cannot treat silence as successful execution. Log/audit failure is visible and blocks mandatory-audit transitions.

## Acceptance and zero-relay demonstration

- Run a real authorized task with deliberately rejected candidate, real measured failing case, separate reviewer feedback, automatic correction and resubmission to a newly verified exact candidate.
- The board reflects events, comments, candidates, attempts, findings and reviews automatically. No CEO SQL, import commands, ticket moves or copied agent messages are used during normal delivery.
- Inject crashes before/after handoff commit, duplicate transport, revoked sessions, out-of-order events, changed policy/base, exhausted budgets, cancellation and uncertain execution. Prove no lost acknowledged handoff, duplicate effective dispatch, blind retry or stale completion.
- Demonstrate the required final human/policy approval clearly and separately from routine coordination. Do not claim zero human decisions or automatic production deployment.
- Record real provider/runtime/image/repository/test identities, actual independent verdict and browser evidence. Mocked components and skipped checks remain separate from this live acceptance.
