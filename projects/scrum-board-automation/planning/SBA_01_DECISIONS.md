# SBA-01 decisions and acknowledgement register

Draft decisions: use explicit stable project registration; publish structured plans with optimistic concurrency; keep MAS-PM runtime authority; authenticate agent events server-side; persist attributable activity and verified evidence separately; preserve the FSM; use incremental polling first; require actual Antigravity runtime proof.

Implementation owners: Antigravity owns proposed v1 backend, migrations, adapter and recovery. Codex owns board integration and UX. Codex coordinates the interface. Individual runtime principals and separate reviewers remain to be appointed through authenticated deployment administration.

## Antigravity Technical Realization & Entry Points (Revised Proposal)

### 1. Actual runtime hooks, log sources, protocol limitations, and proposed components

All new backend and test files are explicitly marked **[PROPOSED]** and are not implemented at this revision:
- `mas/pm/adapter.py` [PROPOSED]: Core `AntigravityEventAdapter` for monotonic event construction, schema validation, and server event ingestion.
- `scripts/antigravity_bridge.py` [PROPOSED]: Runtime process bridge monitoring execution activity and publishing lifecycle events to MAS-PM.
- `projects/registry.json` [PROPOSED]: Explicit repository project manifest.
- `tests/test_sba_01_contract.py` [PROPOSED] & `tests/test_sba_02_discovery.py` [PROPOSED]: Contract and discovery verification test suites.

**Real Antigravity Runtime Mechanisms & Confirmed Limitations:**
- **Disk Log Source:** Active agent sessions record append-only JSONL execution steps to `<appDataDir>/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`. Each entry records `step_index`, `source`, `type` (`USER_INPUT`, `MODEL_TURN`, `TOOL_CALL`, `TOOL_RESULT`), `status`, and tool invocation payloads/results. This is an authoritative, immutable record of actual agent actions, commands executed, and file modifications.
- **Customization Roots & Extension Hooks:** Customizations load from `/home/acinonyx/.gemini/config` (global) and `.agents/` (workspace-relative), including `skills/`, `rules/`, `plugins/`, `mcp_config.json`, and `hooks.json`.
- **Tool Dispatch & Protocol:** Real Antigravity tool invocations communicate via Model Context Protocol (MCP) using JSON-RPC/stdio. MAS-PM lifecycle tools (`pm_post_event`, `pm_submit_evidence`, `pm_add_comment`) will be registered as MCP tools.
- **Confirmed Runtime Limitations:** Antigravity does not support arbitrary asynchronous outbound HTTP push webhooks injected into model reasoning turns. Consequently, runtime lifecycle events cannot be pushed into the agent unsolicited. Events must originate from:
  1. Active agent MCP tool calls during task execution (for milestone transitions such as `candidate.submitted` and `evidence.submitted`).
  2. Out-of-process transcript log watchers (`transcript.jsonl`) tailing tool activity (`work.started`, `work.progress`).
  3. Git repository branch and commit monitoring (`candidate` commit creation).
- **Runtime Capture for SBA-04:** Rather than using a standalone mock simulator, Antigravity will supply an actual runtime capture (transcript log excerpts and real executed test-runner outputs) to prove genuine integration before requesting SBA-04 acceptance.
- **Durable Outbox Store [PROPOSED]:** Backed by SQLite at `.mas/outbox.db` (or tenant-scoped storage root). Buffers outgoing events with UUID event IDs and attempt-scoped monotonic sequence numbers; retries with exponential backoff on network failure and reconciles 409 version/sequence conflicts without fabricating progress.

### 2. Project registry, source branch configuration, and deployment-specific task ID reconciliation

- **Registry specification:** `projects/registry.json` [PROPOSED], schema_version 1, containing `project_id` (stable UUID), `project_key`, `name`, `root_path`, and `planning_path`.
- **Source branch:** `feat/scrum-board-automation` (base `Acinonyx_frontier`).
- **Stable Planning IDs vs Deployment-Specific Local Task IDs:**
  - `LOCAL_BOARD_REGISTRATION.json` in Git is an illustrative snapshot of cloud-workspace mappings, not an immutable desktop or cross-deployment constraint.
  - Stable planning references (`SBA-01`..`SBA-09`) and plan task UUIDs (`task_id`) remain globally invariant across Git plans.
  - Local issue keys (`SBA-1`, `SBA-2`, etc.) are allocated dynamically by each deployment's local database (`mas_pm.db`) and autoincrement sequence.
  - Proposed local mapping table in `mas/pm/db.py`: `pm_task_mappings` [PROPOSED] with schema `(project_id TEXT, planning_reference TEXT, task_id TEXT, local_issue_key TEXT, local_issue_id TEXT, created_at TIMESTAMP, updated_at TIMESTAMP, PRIMARY KEY(project_id, planning_reference))`.
  - Idempotent plan reconciliation: Look up existing mapping by `(project_id, planning_reference)` or `task_id`. If mapped in the target deployment, preserve the existing local issue key and runtime history; if unmapped, allocate the next available local key in that deployment. No hardcoded assumption of `SBA-1..SBA-9` is made across separate environments.
- **Idempotent discovery:** Reconciles projects from `projects/registry.json` [PROPOSED] without scanning or creating projects from unregistered folders. Missing or renamed directories mark sources inactive without dropping runtime history.

### 3. Selected browser authentication approach, session transport, and CSRF enforcement

- **First-Release Transport Selection:** **Same-Origin HttpOnly Session Cookie + Header CSRF Token**, complemented by `Authorization: Bearer <service_token>` for non-browser agent/bridge processes.
- **Browser Bootstrap & Login Flow:**
  1. **Login / Bootstrap Endpoint:** `POST /api/pm/v1/auth/login` [PROPOSED] accepts authorized credentials/bootstrap token and issues:
     - `Set-Cookie: mas_session=<session_id>; HttpOnly; SameSite=Lax; Path=/` (and `Secure` on TLS).
     - Response body: `{"csrf_token": "<csrf_token>", "principal": "<principal>", "tenant_id": "<tenant_id>"}`.
  2. **Portal & Page Delivery:** `GET /portal/*` and `GET /scrum.html` in `DashboardServer` / `TenantDashboardRequestHandler` validate `mas_session`. If missing or expired, the request is redirected to `/portal/login.html` (or returns 401). No unauthenticated portal is served on tenant-bound paths.
  3. **Session API:** `GET /api/pm/v1/session` [PROPOSED] validates the session cookie and returns `{principal, tenant_id, permitted_actions}`; never exposes secrets or raw tokens.
  4. **State-Changing Browser Mutations (POST/PUT/DELETE):**
     - Browser `fetch` requests include `credentials: 'same-origin'`.
     - Browser attaches `X-CSRF-Token: <csrf_token>` on all state-mutating requests.
     - Server middleware verifies that `X-CSRF-Token` matches the session's active CSRF secret before processing the request.
  5. **Token Expiry & Revocation:**
     - Session state is cached server-side with an 8-hour TTL and idle timeout.
     - Explicit tenant/principal revocation check runs on every mutation and incremental poll.
     - `POST /api/pm/v1/auth/logout` [PROPOSED] terminates the session and expires the cookie (`Max-Age=0`).
  6. **Automated Bridge / Script Transport:**
     - Background CLI bridges (`scripts/antigravity_bridge.py` [PROPOSED]) authenticate via `Authorization: Bearer <service_token>`.
     - Server checks `Authorization: Bearer` first; if valid, authenticates directly without requiring a CSRF token (since custom Bearer headers cannot be forged via ambient browser cross-origin requests).
- **Critic & Identity Mapping:** Reviewers are tenant-qualified principals (`tenant:principal_id`). Enforces strict separation of duties: `reviewer_principal != assignee_principal`.

### 4. Shared-connection transactional persistence and atomic FSM composition

- **Diagnosis of Existing Connection-Per-Call Behavior:**
  - In `mas/pm/db.py`, `PMDatabase.atomic_transaction()` creates a new SQLite connection per invocation and calls `BEGIN IMMEDIATE;`.
  - In `mas/pm/fsm.py`, `FSMEngine.transition()` invokes `with self.db.atomic_transaction() as conn:`.
  - Wrapping an existing call inside an outer `atomic_transaction` creates a second connection, resulting in SQLite write contention (`database is locked`) or broken atomicity where inner commits cannot be rolled back by outer failures.
- **Transaction-Aware Internal FSM Entry Point:**
  - Introduce `FSMEngine._transition_tx(conn: sqlite3.Connection, issue_id_or_key: str, target_state: IssueState | str, caller_principal: Optional[str] = None, reason: str = "", ...) -> Issue`.
  - `_transition_tx` executes all guard evaluations (`validate_dependencies`, `validate_evidence`, `validate_critic_verdicts`, `validate_wip_limit`) and mutates `pm_issues` directly on the provided active connection without opening a second transaction.
  - The public `FSMEngine.transition(...)` delegates to `with self._lock: with self.db.atomic_transaction() as conn: return self._transition_tx(conn, ...)`.
- **Atomic Multi-Table Ingestion:**
  - Implement `PMDatabase.ingest_agent_event_tx(conn: sqlite3.Connection, event: AgentEvent) -> Tuple[EventReceipt, Optional[Issue], int]` [PROPOSED].
  - Inside a single `with db.atomic_transaction() as conn:` block:
    1. Insert event into `pm_events` [PROPOSED] (immutable event log).
    2. If a state transition is requested, execute `fsm._transition_tx(conn, ...)`.
    3. If notes or comments are present, insert into `pm_comments` [PROPOSED].
    4. Advance the monotonic integer cursor and append to `pm_changes` [PROPOSED].
  - If any guard fails, sequence conflicts, or constraint check fails, the single SQLite transaction issues `ROLLBACK`. Event ingestion, state mutation, and change cursor roll back together as an indivisible atomic unit.
- **Polling & Resync:** `GET /api/pm/v1/projects/{id}/changes?after={cursor}&limit=100` [PROPOSED] serves incremental change records for 2-second polling. If the cursor is older than the retention window, returns 410 Gone / `resync_required` to trigger full snapshot reload.

### 5. Candidate/evidence validation implementation and artifact origin policy

- **Candidate submission (`candidate.submitted`):** Requires full 40-character Git commit SHA and artifact digest.
- **Evidence submission (`evidence.submitted`):** Requires task ID, attempt ID, candidate commit SHA, test-suite digest, runner ID, run ID, execution timestamps, PASS/FAIL outcome, and SHA256 content hash.
- **Artifact origin policy:** Artifact paths must reside strictly within workspace paths matching task `path_whitelist`; no directory traversal (`..`) or external absolute paths. External URLs and arbitrary executable payloads are rejected.
- **Separation of duties:** Reviewer verdict binds the exact candidate commit; subsequent code changes reset review state and invalidate prior approval.

### 6. Exact accepted contract commit/digest, deviations, and planned test suites

- **Contract candidate commit:** `89db8abc61180f6fabc16b6eeb12a433bc9f00c9` (`89db8abc`).
- **Contract document digest:** `63057158ff74fe62f679d21aacea0f415c420dbcb097d9e0178e7cdc8ad58383` (`BOARD_CONTRACT_V1.md`).
- **Deviations & compatibility:** Proposed `/api/pm/v1/*` endpoints are added alongside existing legacy `/api/pm/*` routes to ensure zero disruption during frontend migration.
- **Planned Verification Commands (to be executed upon backend implementation):**
  - Existing regression suite: `python3 -m pytest tests/test_dashboard.py tests/test_pm_engine.py tests/test_pm_remediation.py tests/test_pm_07_dependencies_and_authorization.py`
  - Planned contract & discovery suites: `python3 -m pytest tests/test_sba_01_contract.py tests/test_sba_02_discovery.py` [PLANNED]

## Acknowledgement & Status Register

- **Antigravity Technical Acknowledgement:** ACKNOWLEDGED (Revised Proposal) by the Antigravity development team. Incorporates all four action directives from Codex counterparty review `c67540f1` ([SBA_01_CODEX_REVIEW.md](SBA_01_CODEX_REVIEW.md)).
- **Codex Agreement:** ACKNOWLEDGED at revision `c67540f1`. Pending re-review of this revised proposal.
- **Independent Reviewer:** PENDING appointment by authorized deployment administrator.
- **Authority Boundary Notice:** Antigravity does not declare the contract accepted on behalf of Codex or the independent reviewer.
- **Execution Budget:** 0 tokens currently allocated in `BACKLOG.json`.
- **Runtime Task Status:** SBA-01 (local SBA-1) remains in BACKLOG pending joint sign-off, reviewer appointment, and token budget allocation.
- **Implementation Gate:** Backend implementation of SBA-02/SBA-03 will commence only after formal contract sign-off, independent reviewer appointment, and deployment budget allocation.
