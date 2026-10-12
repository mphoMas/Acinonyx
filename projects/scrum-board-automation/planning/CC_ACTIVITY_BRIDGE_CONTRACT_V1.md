# Runtime activity and board projection contract — proposed v1

Contract ID: `mas-runtime-activity-v1`. Backend owner: Antigravity under SBA-04. Frontend owner: Codex under SBA-06 / CC-10. Design owner: Codex; joint interface acknowledgement pending Antigravity. This refines [BOARD_CONTRACT_V1.md](BOARD_CONTRACT_V1.md) and preserves its v1 event/read paths. It is not a claim that those routes are already implemented.

## Authoritative data and event classes

MAS-PM is the durable source of board state. Every runtime channel is bound by the supervisor to one authenticated tenant/task/attempt/run/generation. Agent messages are observations; trusted supervisor, broker, exporter, verifier, reviewer and merger events have distinct service-owned provenance. The server stamps actor and receipt time; guest input cannot promote its own authority class.

Guest observations retain existing kinds: work.started, work.progress, work.blocked, work.resumed, comment.added, note.added, evidence.submitted and candidate.submitted. Evidence/candidate submissions are untrusted until their respective services validate them. Agent percentages/messages cannot certify a transition, test pass, review or completion.

Service-only events record session.bound, provider.requested, provider.usage_confirmed, candidate.exported, verification.recorded, review.recorded, integration.confirmed, execution.uncertain and escalation.created. A guest using one of these kinds is rejected. Do not invent new FSM states from event names; route eligible changes through existing authenticated guards.

## Ingestion, acknowledgements and recovery

Preserve proposed POST `/api/pm/v1/projects/{project_id}/events` and its fields: schema_version=1, event_id, task_id, attempt_id, sequence, kind, occurred_at, expected_task_version, payload. For a runtime channel, resolve physical run and generation from the authenticated channel; any later external producer extension needs an explicit versioned contract, not loosely accepted extra fields.

Validate tenant/project/task/assignment/current generation/permissions before deduplication. Enforce existing 64 KiB request, 8 KiB message, exact field/type/kind bounds; markup and artifacts are data, never instructions. Per-producer/attempt sequences prevent duplicates and gaps. Store canonical digest and return the original receipt for exact duplicate IDs; conflicting payload under an ID returns 409. Authentication failures stop replay; stale generations cannot insert late authoritative results.

Persist event, eligible guarded state mutation, outgoing board change cursor and durable handoff intent in one transaction. No network call occurs inside that transaction. Acknowledgement means committed storage only. Respond with receipt_id, event_id, task_id, accepted_sequence, task_version and board_cursor; it never means verification passed.

The supervisor writes early session identity before acknowledging startup and before treating the runtime as resumable. Raw model conversation IDs are not replay/authority keys. If the actual CLI cannot expose/resume a session, report capability unavailable and reconcile the run; do not manufacture a session or redispatch uncertain work.

A bounded credential-free spool retains unacknowledged events. Replay stable IDs/digests in sequence. Apply backpressure rather than dropping terminal/candidate/evidence events; coalesce progress only before assigning durable IDs/sequences. Spool exhaustion pauses output admission and records a visible blocker. Never synthesize progress, completion or elapsed usage during an outage.

## Reads and compatibility with the prepared UI

GET `/api/pm/v1/tasks/{issue_id}/activity?after={opaque_cursor}&limit=100` uses deployment-local issue identity in the URL, mapped to stable task identity server-side. Authorization happens before returning records or resolving a cursor. A cursor is scoped to tenant/project/filter; it is not a globally reusable row ID.

Version-1 response fields:

| Field | Meaning |
| --- | --- |
| schema_version | 1 |
| task_id / issue_id | Stable planning identity and deployment-local issue identity |
| events | Required ordered array; empty means genuinely no recorded events |
| attempts | Ordered attempt summaries; absent means interface unavailable, not zero attempts |
| reviews | Review summaries; absent means interface unavailable, not approval |
| current_candidate_commit | Exact current candidate, or null |
| next_cursor / has_more | Bounded pagination/replay continuation |
| snapshot_cursor / observed_at | Consistent read cursor and server snapshot timestamp |

Event summaries retain fields consumed by `portal/scrum.html`: event identity, kind, `summary`, `actor` and `received_at` and optional evidence with status `claimed`, `validated` or `rejected` and candidate_commit. Attempt summaries supply `attempt_id`, `state` and `run_id` plus attributable runtime details. Preserve the prepared UI states QUEUED, RUNNING, SUCCEEDED, FAILED, UNKNOWN_EXECUTION, CANCEL_REQUESTED and CANCELLED; map persisted PENDING to QUEUED and CANCELED to CANCELLED in the read projection only. A pending cancellation is never confirmed cancellation. Reviews supply `review_id`, `candidate_commit`, `reviewer_principal`, `decision` (APPROVED / REJECTED / CHANGES_REQUESTED) and `trust_status`. Internal verdict/status field names are projected to these existing UI names rather than changing the frontend contract silently. `validated` requires server-side current evidence/authority checks; historical ADMITTED labels are not enough. Changed candidate/policy/issuer authority appears stale or unverified. No secret values, raw prompts, local paths or arbitrary clickable artifact URLs are returned.

Project board snapshot and GET `/api/pm/v1/projects/{id}/changes?after={cursor}&limit=100` share a consistent snapshot/change boundary. Missing/inaccessible resources do not expose other tenants. A retained-feed gap returns 410 with resync_required; reload a consistent snapshot, never interpret a gap as an empty board.

First live release uses two-second incremental polling while visible, following the existing board contract. Drain bounded pages in order. Reconnect with jittered exponential backoff capped at 30 seconds; stop unauthorized polling and report denial. SSE/WebSockets are not prerequisites. The five-second healthy-connection update target is tested from committed server event to rendered card.

## Frontend delivery acceptance

Codex integrates only after the acknowledged API contract and fixtures are available. Preserve current readable activity/attempt/review states, escaped text and response-generation race guard. Add incremental polling, cursor recovery and last-successful-update/stale/disconnected states without optimistic DONE.

Browser acceptance must exercise: real authenticated event → persisted board/card update; empty board vs unavailable response; attempts unavailable vs empty; stale review; cursor gap; pagination; 401/403/503; rapid project/task switching; restart/replay and malicious strings. Mock transport tests qualify rendering only; at least one actual backend+runtime browser run is required for SBA-08.

## Backend acceptance

- Real supported runtime starts, early session/progress/blocker/comments/evidence persist and appear automatically without CEO scripts.
- Duplicates, conflicting IDs, gaps, reordered frames, wrong tenants, revoked actors and stale generations cannot bypass authority or duplicate transitions.
- Crash before/after acknowledgement and spool replay lose no acknowledged activity or pending handoff.
- Guest attempts to emit service-only success/review events fail. Missing audit/storage authority and exhausted buffers produce visible failure.
- Tests explicitly distinguish observed runtime status from validated verification, review, integration and completion.
