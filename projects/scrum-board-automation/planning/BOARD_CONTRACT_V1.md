# SBA end-to-end contract v1 — proposed for joint agreement

Status: DRAFT, implementation-ready proposal; Antigravity acknowledgement and independent review pending. This document proposes interfaces; it does not claim they exist. Scope: SBA-01, local board task SBA-1. Codex owns this contract draft and frontend requirements; Antigravity owns backend realization. CEO is product/release authority.

## 1. Authority and sources of truth

Git holds project registration and approved plan snapshots. MAS-PM holds runtime tasks, assignment, transitions, comments, evidence and review. GitHub supplies repository revisions, not task completion. Conversation produces a draft; an authenticated architect publishes it under the CEO's approved project scope. Ordinary task refinements within that scope do not require repeated CEO confirmation. Scope, cost or release expansion is returned to the CEO.

Client-supplied caller, reviewer and tenant claims never confer authority. Resolve identity from platform IAM and server-bound tenant context; recheck revocation for writes and every live-feed reconnect. Authentication failure cannot fall back to a shared founder identity. Existing storage permissions are necessary but must be supplemented with per-project and per-task action authorization. Proposed action labels below describe requirements, not currently provisioned IAM roles.

Architect: register projects and publish plans. Coordinator: allocate scoped work and request permitted readiness transitions. Assigned agent: publish activity and submit its own candidate. Verifier: attach independently measured results. Separate reviewer: review the candidate; cannot be its builder. CEO/authorized release approver: rollout decision. Neither this document nor a planning owner field grants these permissions.

## 2. Project registration and discovery

Proposed repository registry: `projects/registry.json`, schema_version 1, containing project_id (stable UUID), project_key, name, root_path and planning_path. Repository identity is configured using GitHub's immutable repository ID plus owner/name for display. Existing folders become discovery candidates until explicitly registered. Import SBA and PLG as a reviewed migration, preserving existing PM IDs and keys. Never create a second copy from a title match alone.

Discovery watches the configured branch and reconciles on startup and at least every 30 seconds, with authenticated webhook acceleration optional. Record observed commit, last successful synchronization and latest error. Rename preserves project_id; missing registration marks source inactive, retaining runtime records. Invalid registry/revision leaves the last good snapshot active and visibly stale. No arbitrary repository fetches or branch changes based on agent payloads. GitHub credentials stay server-side.

## 3. Planning publication

Proposed `POST /api/pm/v1/projects/{project_id}/plans` accepts schema_version, plan_id, revision, expected_previous_revision, source_commit, scope_reference and tasks. Each task has stable task_id, planning_reference, title, description, type, priority, parent_task_id, dependencies, acceptance criteria, proposed delivery owner, reviewer requirement, path scope and proposed budget. Server allocates local issue keys and returns the identity mapping.

Use `Idempotency-Key` scoped to authenticated tenant/action. Repeated key with identical canonical payload returns the original outcome; different payload returns 409. Compare expected_previous_revision atomically; apply the validated plan and dependency graph in one transaction, or make no changes. Reject duplicate IDs, unknown parents/dependencies, cycles, unsafe scopes and cross-project references unless explicitly admitted. Enforce request and task count limits.

New tasks enter BACKLOG. Planning ownership is distinct from authenticated assignment. Proposed budget is not an execution grant. Existing status, evidence and review cannot be overwritten by a plan. Editing acceptance/scope of active work requires an explicit change record and revalidation; deleting a plan item archives planning intent, not runtime history. Response includes applied revision, mappings, changes requiring reconciliation and board cursor. No natural-language interpretation inside this deterministic API: the architect converts conversation into a reviewable structured plan.

## 4. Agent event envelope and ingestion

Proposed `POST /api/pm/v1/projects/{project_id}/events` accepts one event:

```json
{
  "schema_version": 1,
  "event_id": "stable UUID reused for retries",
  "task_id": "stable UUID",
  "attempt_id": "server-issued attempt UUID",
  "sequence": 1,
  "kind": "work.started",
  "occurred_at": "2026-10-10T12:00:00Z",
  "expected_task_version": 3,
  "payload": {"message": "Starting the assigned work"}
}
```

Tenant, actor and receipt time are stamped by the server. Validate task/project/attempt membership, current assignment and permissions before consuming deduplication keys. Agent event_id is a UUID, sequence a positive integer, message <=8 KiB, request <=64 KiB. Activity strings are plain text and rendered escaped. Reject unknown fields and kinds. Timestamps are informational; ordering uses server cursors and attempt sequence.

Kinds: work.started, work.progress, work.blocked, work.resumed, comment.added, note.added, evidence.submitted and candidate.submitted. Notes and comments are attributable append-only activity; corrections are new linked events. Progress has a message and optional bounded reported percentage, which does not determine workflow state. Blocked includes reason and category. Resume requests a permitted transition; it does not force one. Candidate submission includes full commit SHA and artifact digest.

The server atomically records the event, any permitted FSM transition and the outgoing activity record. Duplicate event with identical payload returns original receipt; changed payload returns 409. Sequence gap or stale task version returns 409 with expected sequence/version; adapter reconciles rather than skipping. Rejected events cause no partial mutation. A stored event receipt means persisted activity, not accepted verification or completion.

## 5. State mapping and completion

Preserve the existing directed graph in mas/pm/fsm.py:
BACKLOG -> REFINED -> STAGED -> IN_PROGRESS -> VERIFICATION -> JUDICIAL_REVIEW -> DONE.
Existing BLOCKED and REJECTED_REWORK edges remain subject to the same guards. No new shortcut edge is introduced.

Coordinator readiness evaluates scope, dependency completion, budget authorization and WIP before staging. work.started can request STAGED -> IN_PROGRESS only for an authorized assigned attempt. candidate.submitted can request IN_PROGRESS -> VERIFICATION only when existing evidence requirements are met; otherwise retain state and return explicit guard failure. Independent verification and review move subsequent stages through authenticated guarded operations. Existing critic requirements must be mapped to tenant-qualified identities and explicitly configured; never weaken them to fit unqualified role strings. DONE remains terminal under the current graph.

Evidence submissions are unverified until trusted checks establish validity. Require task, attempt, candidate digest/full commit, test-suite digest, runner identity, run ID, execution times, outcome and content hash for measured test evidence. Distinguish claimed, validated and rejected evidence. Verify allowed artifact origins and hash; never fetch arbitrary agent URLs or execute attached content. Reviewer verdict binds the exact candidate and current rework cycle. Changed candidate invalidates prior approval. Comments, screenshots and commits alone cannot certify test success.

## 6. Frontend identity, reads and live activity

Proposed GET `/api/pm/v1/session` returns principal display, tenant display and permitted actions, never tokens. Authenticated page delivery must be agreed: use same-origin authenticated portal hosting with secure session/Bearer adapter, not a file:// page or credentials in query strings/localStorage. If cookies are chosen, implement HttpOnly, Secure, SameSite and CSRF protection. Browser cannot invent founder_lead. Legacy compatibility routes retain server identity enforcement until retired through a tested cutover.

Proposed GET `/api/pm/v1/projects` returns projects plus source freshness. GET `/api/pm/v1/projects/{id}/board` returns tasks, versions and snapshot cursor. GET `/api/pm/v1/tasks/{id}/activity?after={cursor}&limit=100` returns ordered comments, notes, events and evidence status. Use opaque tenant-scoped cursor, bounded pagination and permission checks. Forbidden access reveals no other tenant/project records.

First release uses authenticated incremental polling every two seconds while visible; this meets the five-second healthy-connection target without requiring a new streaming broker. GET `/api/pm/v1/projects/{id}/changes?after={cursor}&limit=100` returns ordered persisted changes, next_cursor and has_more. Snapshot and its cursor must represent the same consistent read. Retained-feed gap returns 410/resync_required; frontend reloads a consistent snapshot. Reconnect uses exponential backoff with jitter capped at 30 seconds. Show last successful update, stale state and access-denied state; do not show an optimistic transition as committed. SSE can be a later compatible transport.

Error envelope: error.code, message, retryable, request_id and safe details. 400 malformed, 401 unauthenticated, 403 unauthorized, 404 inaccessible/nonexistent resource, 409 duplicate mismatch/version/sequence conflict, 410 cursor expired, 413 oversized, 422 contract/guard rejection, 429 throttled, 503 authority/storage/source unavailable. Preserve legacy HTTP behavior during versioned migration. Avoid leaking secrets or internal paths in errors; display failures above open drawers.

## 7. Antigravity adapter and recovery

Antigravity must acknowledge the actual runtime hook and credential transport before claiming integration. Adapter discovers assigned admitted work, publishes startup/progress/blocker/comment/evidence events, durably buffers retryable events with stable IDs and sequence, and reconciles task versions. Local queue stores no bearer credentials; use configured scoped authentication. Failed auth stops writes and surfaces the issue. Network outage does not mark work completed or fabricate progress. Explicit cancellation stops the attempt and records uncertainty; heartbeat/lease expiry marks stale activity without inventing a terminal verdict.

Agent writes, workflow transition and outgoing change cursor share a transaction. Process restart cannot lose an acknowledged event. Recovery replays durable receipts, never grants execution from old approval. Database backup restores require identity/audit recovery checks already applicable to deployment. CEO startup remains one manual operation; ongoing scripts and ticket dragging cannot be acceptance prerequisites.

## 8. Acceptance and contract sign-off

| Gate | Required evidence | Delivery owner |
|---|---|---|
| C1 | Stable registered project rename, invalid/missing source, idempotent discovery | Antigravity |
| C2 | Conversation-derived plan revision, dependencies, conflict and active-work preservation | Antigravity |
| C3 | Actual Antigravity events, restart/replay, ordering and persisted comments/notes | Antigravity |
| C4 | Cross-tenant and forged-actor denial, revocation, invalid transition, fake evidence rejection | Antigravity |
| C5 | Real authenticated browser, visible errors, five-second refresh and gap recovery | Codex |
| C6 | One real project from CEO request to independently reviewed completion; no CEO maintenance scripts | Codex coordinates; independent reviewer accepts |

Draft verified against current code: dashboard has legacy project/board reads, create/transition/verdict handlers; tenant server binds principal but denies non-PM page paths. PM models contain evidence and verdicts but no general activity/comment record. Git queue reads one local manifest, no remote discovery. These proposed v1 endpoints, registry, attempt adapter and durable activity feed are new backend work.

SBA-01 completion requires Antigravity's recorded technical acknowledgement and separate review of this exact draft. Until then this is a completed proposal, not an agreed contract or permission to bypass the dependency gate.
