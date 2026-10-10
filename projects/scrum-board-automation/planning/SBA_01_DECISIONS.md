# SBA-01 decisions and acknowledgement register

Draft decisions: use explicit stable project registration; publish structured plans with optimistic concurrency; keep MAS-PM runtime authority; authenticate agent events server-side; persist attributable activity and verified evidence separately; preserve the FSM; use incremental polling first; require actual Antigravity runtime proof.

Implementation owners: Antigravity owns proposed v1 backend, migrations, adapter and recovery. Codex owns board integration and UX. Codex coordinates the interface. Individual runtime principals and separate reviewers remain to be appointed through authenticated deployment administration.

## Antigravity Technical Realization & Entry Points

1. **Actual runtime startup/progress/completion hooks and durable retry implementation:**
   - Entry points:
     - `mas/pm/adapter.py`: Core `AntigravityEventAdapter` responsible for event construction, client-side sequence monotonicity, payload validation, and server event ingestion.
     - `scripts/antigravity_bridge.py`: Runtime process bridge that discovers assigned tasks from MAS-PM, monitors execution activity, and publishes lifecycle events.
   - Durable Outbox Store: Backed by SQLite at `.mas/outbox.db` (or tenant-scoped storage root). Outbox buffers all outgoing events (`work.started`, `work.progress`, `work.blocked`, `work.resumed`, `comment.added`, `note.added`, `evidence.submitted`, `candidate.submitted`) with UUID event IDs and attempt-scoped monotonic sequence numbers. Outbox handles retry with exponential backoff and reconciles sequence/version conflicts on 409 responses without losing events or fabricating progress.

2. **Accepted project registry and source branch configuration; migration of SBA/PLG identities:**
   - Registry specification: `projects/registry.json`, schema_version 1, containing `project_id`, `project_key`, `name`, `root_path`, and `planning_path`.
   - Source branch: `feat/scrum-board-automation` (base `Acinonyx_frontier`).
   - Migration of existing identities:
     - SBA: Registered with stable UUID and key `SBA`. Maps planning references SBA-01..SBA-09 to local keys SBA-1..SBA-9 per `LOCAL_BOARD_REGISTRATION.json`.
     - PLG: Preserves existing Platinum Lodge workspace references and PM database records.
     - Idempotent discovery: Reconciles projects from `projects/registry.json` without scanning or creating projects from unregistered folders. Missing or renamed directories mark sources inactive without dropping runtime history.

3. **Session transport and authenticated portal serving design; identity/critic mapping:**
   - Portal hosting: Served same-origin via `DashboardServer` / `TenantDashboardRequestHandler` at `/portal/`.
   - Session API: `GET /api/pm/v1/session` returning authenticated principal, tenant ID, and permitted action claims; never leaks secrets or tokens.
   - Transport: `Authorization: Bearer <token>` or same-origin session cookies (HttpOnly, Secure, SameSite=Lax). Caller identity is resolved server-side from `ExecutionContext` / `tenant_scope`.
   - Critic mapping: Reviewers are tenant-qualified principals (`tenant:principal_id`). Enforces strict separation of duties: `reviewer_principal != assignee_principal`.

4. **Transactional event/outbox persistence and retention/resync implementation:**
   - Database tables: In `mas/pm/db.py`, adding `pm_events` (immutable event log), `pm_comments` (attributable comments and notes), and `pm_changes` (monotonic change feed with incremental integer cursor).
   - Atomic commit: Event insertion, state transition in `FSMEngine`, activity record creation, and change cursor advancement execute in a single atomic SQLite transaction (`PMDatabase.atomic_transaction()`).
   - Polling & Resync: `GET /api/pm/v1/projects/{id}/changes?after={cursor}&limit=100` serves incremental change records for 2-second polling. If the cursor is older than retention window, the server returns 410 Gone / `resync_required` to trigger full snapshot reload.

5. **Candidate/evidence validation implementation and artifact origin policy:**
   - Candidate submission (`candidate.submitted`): Requires full 40-character Git commit SHA and artifact digest.
   - Evidence submission (`evidence.submitted`): Requires task ID, attempt ID, candidate commit SHA, test-suite digest, runner ID, run ID, timestamps, PASS/FAIL outcome, and SHA256 content hash.
   - Artifact origin policy: Artifact paths must reside strictly within workspace paths matching task `path_whitelist`; no directory traversal (`..`) or external absolute paths. External URLs and arbitrary executable payloads are rejected.
   - Separation of duties: Reviewer verdict binds the exact candidate commit; subsequent code changes reset review state and invalidate prior approval.

6. **Exact accepted contract commit/digest, deviations, and integration test commands:**
   - Contract candidate commit: `89db8abc61180f6fabc16b6eeb12a433bc9f00c9` (`89db8abc`).
   - Contract document digest: `63057158ff74fe62f679d21aacea0f415c420dbcb097d9e0178e7cdc8ad58383` (`BOARD_CONTRACT_V1.md`).
   - Deviations & compatibility: Proposed `/api/pm/v1/*` endpoints are added alongside existing legacy `/api/pm/*` routes to ensure zero disruption during frontend migration.
   - Test commands:
     - `python3 -m pytest tests/test_dashboard.py tests/test_pm_engine.py tests/test_pm_remediation.py tests/test_pm_07_dependencies_and_authorization.py`
     - Contract and backend discovery verification tests: `python3 -m pytest tests/test_sba_01_contract.py tests/test_sba_02_discovery.py`

## Acknowledgement & Status Register

- **Antigravity Technical Acknowledgement:** ACKNOWLEDGED by the Antigravity development team. The proposed backend interfaces, event schemas, concurrency model, and storage design are technically viable and realizable.
- **Codex Agreement:** PENDING independent review and formal acknowledgement by Codex.
- **Independent Reviewer:** PENDING appointment by authorized deployment administrator.
- **Authority Boundary Notice:** Antigravity does not declare the contract accepted on behalf of Codex or the independent reviewer.
- **Execution Budget:** 0 tokens currently allocated in `BACKLOG.json`.
- **Runtime Task Status:** SBA-01 (local SBA-1) remains in BACKLOG pending joint sign-off, reviewer appointment, and token budget allocation.

Validation performed: Verified existing dashboard handlers, tenant binding, PM schema, and directed FSM. Prepared technical realization plan and entry points for backend implementation.

