# SBA-06 activity and evidence interface — frontend specification

Status: prepared for implementation against real backend responses. No simulated feed is presented as live work. Codex owns this frontend; Antigravity implements the versioned read/event contracts.

## Project and board states

Project selector shows registered project name/key, active/inactive source, source revision and latest successful synchronization. A fetch failure preserves source context visibly as stale, rather than suggesting an empty repository. No projects is distinct from unauthenticated, forbidden, source unavailable and malformed responses. Loading uses aria-busy and readable status; requests have a bounded deadline and retry control.

Cards show server-authoritative state, assigned authenticated actor, blocker and most recent activity time. Reported progress is labelled agent-reported; it never implies verification. Cards cannot move optimistically to DONE. The board refreshes within five seconds on healthy connectivity using the agreed incremental polling contract; cursor gaps trigger a consistent snapshot reload. Failed polls show freshness/error and reconnect backoff, never fabricated updates.

## Task drawer

Show three sections: overview/workflow, activity, evidence/review.

Activity lists receipt order, actor, timestamp, type and escaped plain-text summary. Distinguish comments, notes, progress and blockers. Show older pages through bounded cursor pagination; preserve reading position when new entries arrive. Do not render raw transcript, HTML, executable attachments or full tool arguments. Missing activity is an empty state; failed activity fetch is an error with retry.

Evidence lists candidate commit, artifact hash, runner/suite/run identity, recorded outcome and evidence trust status: claimed, validated or rejected. Reviewer decision identifies reviewer, exact candidate and rework cycle. A submitted PASS field displays as a claim until verification. Changed candidates show stale prior approval. Links are permitted only for backend-admitted origins; opening an artifact never executes it.

Comments/notes submit through authenticated session/CSRF writes once the backend supplies them. Keep drafts on transient failure in page memory; do not persist potentially sensitive drafts in browser storage. Show errors in the modal, focus the error summary and permit retry without duplicate entries. Server decisions remain authoritative; UI availability is not an authorization grant.

## Backend fields needed before integration

Session: principal, tenant_id, permitted_actions, csrf_token. Project: stable id, key, name, source status/revision/sync timestamp/error. Task: stable id, local key, version, state, assignment, blocker, latest activity and current candidate. Activity: stable event identity, cursor, kind, actor, occurred_at, received_at, sanitized summary and optional evidence reference. Evidence: trust status plus candidate/suite/runner/run identifiers, hash, outcome and rejection reason. Board snapshot: matching consistent cursor. Changes response: changes, next_cursor, has_more; expired cursor returns 410/resync_required.

Exact JSON fixture agreement belongs to the shared contract; missing fields must be surfaced rather than silently invented. Unit/controlled browser fixtures stay labelled test-only. Live feed integration and real Antigravity execution are pending.

## Acceptance checks

At desktop and narrow viewport: project selection, keyboard navigation, drawer focus, readable loading/error/empty states, comments pagination, candidate-specific evidence and denied mutation. Exercise new activity during reading, out-of-order/repeated changes, cursor expiry, reconnect, revoked session and no unsupported privileged controls. Capture real browser screenshots and measured refresh time with the backend. Independent end-to-end acceptance remains SBA-08.

## Prepared drawer candidate

The issue drawer now offers an explicit Load task activity action. It requires the task's persisted id and reads `/api/pm/v1/tasks/{id}/activity?limit=100`. Proposed response is `{events:[{kind,actor,summary,received_at,evidence?:{status,candidate_commit}}]}`. This shape must be agreed with Antigravity before live acceptance. Only claimed/validated/rejected evidence status is recognized; PASS alone is displayed as unverified. Strings are rendered with textContent, not HTML, and no artifact URL is opened. Missing task identity, missing/unsupported endpoint and empty activity are distinct visible states. Stale responses cannot replace a newly opened task's drawer.

This is read-only preparation, not live polling or completed SBA-06. Comment submission, pagination, cursor recovery and real agent integration remain dependent on backend delivery. No generated activity is shown as real.

## Attempt and review preparation (11 October 2026)

Codex implemented read-only sections on the existing activity request. This is a **proposed frontend contract extension**, not an accepted backend contract or live runtime integration. The endpoint remains `/api/pm/v1/tasks/{id}/activity?limit=100`; events are required, while missing attempt/review arrays display interface-unavailable states rather than implying no runs.

Proposed additional fields:

```json
{
  "events": [],
  "current_candidate_commit": "immutable candidate commit",
  "attempts": [
    {"attempt_id": "uuid", "run_id": "uuid", "state": "UNKNOWN_EXECUTION"}
  ],
  "reviews": [
    {"review_id": "uuid", "candidate_commit": "immutable candidate commit", "reviewer_principal": "tenant:reviewer", "trust_status": "validated", "decision": "REJECTED"}
  ]
}
```

Attempt display states: QUEUED, RUNNING, SUCCEEDED, FAILED, UNKNOWN_EXECUTION, CANCEL_REQUESTED, CANCELLED. These are proposed presentation values; Antigravity must agree mappings from the actual attempt lifecycle before integration. Unknown values remain visible as unrecognized. SUCCEEDED means execution completed, with verification still required. CANCEL_REQUESTED explicitly does not confirm stopping.

A review displays as validated only when the server marks trust validated, provides a reviewer, and binds it to the supplied current candidate. A different candidate is stale; missing binding or trust remains an unverified claim. This display does not independently verify signatures, attest tenant ownership or authorize release. Server admission must enforce those requirements.

All fields use plain text; no artifact links, dispatch, approval, cancellation or reconciliation mutations are added. No polling, pagination or automatic task movement is claimed. The existing load button also serves retry. Opening another drawer invalidates old responses. Controlled browser tests cover empty/error/malformed data, uncertain attempts, stale/claimed/validated reviews, narrow screens, text injection and delayed drawer responses. Live integration and independent end-to-end acceptance remain pending backend delivery.
