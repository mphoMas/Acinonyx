# SBA-01 decisions and acknowledgement register

Draft decisions: use explicit stable project registration; publish structured plans with optimistic concurrency; keep MAS-PM runtime authority; authenticate agent events server-side; persist attributable activity and verified evidence separately; preserve the FSM; use incremental polling first; require actual Antigravity runtime proof.

Implementation owners: Antigravity owns proposed v1 backend, migrations, adapter and recovery. Codex owns board integration and UX. Codex coordinates the interface. Individual runtime principals and separate reviewers remain to be appointed through authenticated deployment administration.

Relevant reference documents:
- Contract candidate: [`BOARD_CONTRACT_V1.md`](BOARD_CONTRACT_V1.md) (commit `89db8abc61180f6fabc16b6eeb12a433bc9f00c9`, digest `63057158ff74fe62f679d21aacea0f415c420dbcb097d9e0178e7cdc8ad58383`).
- Counterparty reviews: [`SBA_01_CODEX_REVIEW.md`](SBA_01_CODEX_REVIEW.md) (commit `c67540f1`) and [`SBA_01_REVIEW_2.md`](SBA_01_REVIEW_2.md) (commit `b6d4ae34`).
- Empirical runtime capture: [`ANTIGRAVITY_INTEGRATION_EVIDENCE.md`](ANTIGRAVITY_INTEGRATION_EVIDENCE.md).

---

## Antigravity Technical Realization & Entry Points (Revised Proposal v2)

### 1. Verified Antigravity Runtime Integration & Corrected Transcript Trust Model

All new backend components and test suites remain explicitly marked **[PROPOSED]** and are not implemented at this revision:
- `mas/pm/adapter.py` [PROPOSED]: Core event adapter for monotonic sequence creation, payload validation, and server event ingestion.
- `scripts/antigravity_bridge.py` [PROPOSED]: Out-of-process bridge monitoring execution telemetry and publishing attributable events to MAS-PM.
- `projects/registry.json` [PROPOSED]: Declarative repository project registration manifest.
- `tests/test_sba_01_contract.py` [PROPOSED] & `tests/test_sba_02_discovery.py` [PROPOSED]: Contract and discovery verification test suites.

**Verified Runtime Capabilities & Environment:**
- **Engine / Architecture:** Google DeepMind Advanced Agentic Coding (Antigravity 2.0 / Gemini 3.8 Flash High) running on Linux `x86_64` (kernel 6.8+), Python 3.14.6 runtime.
- **Log Source:** Active sessions record append-only JSONL steps to `<appDataDir>/brain/<conversation-id>/.system_generated/logs/transcript.jsonl`. Each entry contains `step_index`, `source` (`USER_EXPLICIT`, `MODEL`, `SYSTEM`), `type` (`USER_INPUT`, `PLANNER_RESPONSE`, `RUN_COMMAND`, `VIEW_FILE`, `WRITE_TO_FILE`), `status`, and tool call arguments/results. Empirical redacted capture from running session `b964d376-4d79-45c8-81a7-5a28e8de5c62` is documented in [`ANTIGRAVITY_INTEGRATION_EVIDENCE.md`](ANTIGRAVITY_INTEGRATION_EVIDENCE.md).
- **Extension Roots & Dispatch:** Extensions load from `/home/acinonyx/.gemini/config` (global) and `.agents/` (workspace). Tool dispatch executes natively via Model Context Protocol (MCP) using JSON-RPC/stdio.
- **Confirmed Limitation:** Antigravity does not support unsolicited asynchronous push webhooks injected into model reasoning turns. Events must originate from active agent MCP tool calls (`candidate.submitted`, `evidence.submitted`), out-of-process transcript log watchers tailing tool activity (`work.started`, `work.progress`), or repository commit monitors.

**Corrected Transcript Trust Model & Operational Constraints:**
1. **Activity Reporting vs. Empirical Verification:** Transcript entries reflect observed conversational and tool *activity*; they **cannot** independently prove successful execution, test verification, or milestone completion.
   - Milestone transitions (`candidate.submitted`, `evidence.submitted`) require explicit verifiable artifacts: full 40-character Git commit SHAs verified in the repository object database, and standalone test run output logs with matching SHA-256 digests.
   - `DONE` transitions remain strictly gated by the directed FSM and require unanimous approval from authorized separate reviewers (`JUDICIAL_REVIEW`). Watchers and Git monitors cannot transition an issue to `DONE`.
2. **Session / Task / Attempt Binding:** The bridge daemon reading session logs must bind the active `conversation-id` to an explicitly admitted `(tenant_id, project_id, task_id, attempt_id)` tuple provisioned by the coordinator. Unbound sessions or activities referencing unauthorized projects are discarded.
3. **Log Sanitization & Sensitive Data Filtering:** Text extracted from `transcript.jsonl` is treated as untrusted input. The bridge daemon redacts API keys, bearer tokens, passwords, and private blocks via regex. Full transcripts or raw prompts are **never** committed to Git or pushed to external endpoints.
4. **Lifecycle, Rotation, and Truncation Handling:** The bridge daemon tracks file identity using `(device_id, inode)` and byte offset. If file size drops below the tracked offset or inode changes (log compaction or rotation), the bridge detects the discontinuity, raises an alert, and resynchronizes from the latest `CHECKPOINT` entry.
5. **Duplicate Handling:** Deterministic event UUID generation based on `(task_id, attempt_id, step_index)` ensures MAS-PM idempotent event ingestion acknowledges re-reads without duplicating mutations.

---

### 2. Finalized Stable Identity Mapping & Conflict Resolution

- **Canonical Identity Hierarchy:**
  - **Stable Planning Reference (`planning_reference`):** Immutable Git-tracked reference (e.g. `SBA-01`..`SBA-09`) defined in `BACKLOG.json` and plan documents.
  - **Stable Task UUID (`task_id`):** Globally unique UUID assigned to each planning task across all environments.
  - **Local Deployment Issue Key (`local_issue_key`):** Autoincremented string key (e.g. `SBA-1`, `SBA-12`) assigned by each deployment's local SQLite database (`mas_pm.db`).
- **Clarification on `LOCAL_BOARD_REGISTRATION.json`:** Recognised as an illustrative snapshot from the cloud workspace, not an immutable desktop constraint or global identity contract.
- **Relational Mapping Schema (`pm_task_mappings` [PROPOSED]):**
  ```sql
  CREATE TABLE IF NOT EXISTS pm_task_mappings (
      project_id TEXT NOT NULL REFERENCES pm_projects(id) ON DELETE CASCADE,
      planning_reference TEXT NOT NULL,
      task_id TEXT NOT NULL,
      local_issue_id TEXT NOT NULL REFERENCES pm_issues(id) ON DELETE CASCADE,
      local_issue_key TEXT NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      CONSTRAINT pk_task_mapping PRIMARY KEY (project_id, planning_reference),
      CONSTRAINT uq_task_mapping_task_id UNIQUE (project_id, task_id),
      CONSTRAINT uq_task_mapping_local_issue UNIQUE (project_id, local_issue_id),
      CONSTRAINT uq_task_mapping_local_key UNIQUE (project_id, local_issue_key)
  );
  ```
- **Conflict Handling Invariant:**
  - When reconciling a plan or incoming event:
    - If `(project_id, planning_reference)` exists, verify `existing.task_id == incoming.task_id`. If `task_id` differs, reject with **HTTP 409 Conflict (`mapping_contradiction_error`)**. Contradictory mappings are never silently overwritten or updated.
    - If `task_id` is found mapped to a different `planning_reference`, reject with **HTTP 409 Conflict**.
    - If unmapped, allocate the next available local key in that deployment's `pm_issues` and insert the mapping into `pm_task_mappings`.
- **Reviewed Planning Migration:** Stable UUIDs for projects and tasks in `BACKLOG.json` will be committed through a reviewed planning migration before cross-deployment synchronization.

---

### 3. Finalized Browser Authentication & IAM-Backed Session Transport

- **Selected Transport:** Single **IAM-backed opaque cookie session** (`mas_session`), complemented by `Authorization: Bearer <service_token>` for non-browser automation.
- **Session Architecture:**
  1. **IAM-Backed Session Storage:** Session IDs are cryptographically random 256-bit opaque tokens stored in `pm_sessions` [PROPOSED]. The session record binds to the authenticated IAM principal and tenant.
  2. **Per-Request Authorization Revalidation:** On *every* protected page load, API read, and mutation, the server queries the platform IAM provider / `ExecutionContext` / tenant authority to verify that the principal is active, tenant binding is intact, and specific action claims are unrevoked. The 8-hour session TTL is a hard upper bound, **not** an authorization cache.
  3. **Cookie Security Attributes:**
     - `HttpOnly; SameSite=Lax; Path=/`.
     - `Secure` flag is strictly required on all deployed HTTPS instances (exempt only on loopback `127.0.0.1` / `localhost` during local offline development).
     - Session fixation protection: login generates a fresh session ID and invalidates existing sessions.
     - Bounded idle timeout: 30 minutes of inactivity invalidates the session regardless of total TTL.
  4. **CSRF Protection & Origin Validation:**
     - Anti-CSRF token (`X-CSRF-Token`) validated on all state-changing browser mutations (`POST`, `PUT`, `DELETE`), login, and logout.
     - Strict `Origin` and `Referer` validation against the configured server origin.
  5. **Reachable Login Page & No Redirect Loops:**
     - `/portal/login.html` (and `/login`) is an explicitly unprivileged, public route.
     - Unauthenticated requests to protected `/portal/*` (or `/scrum.html`) return HTTP 302 redirecting to `/portal/login.html`. Unauthenticated `/api/*` calls return HTTP 401. Serving the login page requires no credentials, preventing redirect loops.
     - `POST /api/pm/v1/auth/logout` [PROPOSED] terminates the session server-side and clears the cookie (`Max-Age=0`).
  6. **Bearer Token Authentication & No Silent Fallback:**
     - Background CLI bridges (`scripts/antigravity_bridge.py` [PROPOSED]) authenticate via `Authorization: Bearer <service_token>`.
     - **No Silent Fallback:** If an `Authorization: Bearer` header is present but invalid, expired, or malformed, the server **immediately returns HTTP 401 Unauthorized**. It **never** silently falls back to inspecting cookies. Cookie inspection occurs strictly when no `Authorization` header is present.

---

### 4. Finalized Transaction Consistency & Shared-Connection Guard Reads

- **Diagnosis of Existing Connection-Per-Call Limitation:**
  - In `mas/pm/db.py`, `PMDatabase.atomic_transaction()` creates a new SQLite connection and executes `BEGIN IMMEDIATE;`.
  - In `mas/pm/fsm.py`, `FSMEngine.transition()` invokes `with self.db.atomic_transaction() as conn:`.
  - In `mas/pm/guards.py`, `validate_evidence` calls `db.get_evidence_links()` and `validate_critic_verdicts` calls `db.get_verdicts()` without accepting a connection, opening separate connections that cannot observe uncommitted writes.
  - Nesting calls across separate connections triggers SQLite write contention (`database is locked`) and breaks atomic rollback.
- **Transaction-Aware Guard Reads & Internal FSM Entry Point:**
  - Introduce `FSMEngine._transition_tx(conn: sqlite3.Connection, issue_id_or_key: str, target_state: IssueState | str, caller_principal: Optional[str] = None, reason: str = "", ...) -> Issue`.
  - Refactor all guard functions and database read methods to accept an optional active connection `conn: Optional[sqlite3.Connection] = None`:
    - `validate_evidence(db, issue, ..., conn=conn)` calling `db.get_evidence_links(issue.id, conn=conn)`.
    - `validate_critic_verdicts(db, issue, required_roles, conn=conn)` calling `db.get_verdicts(issue.id, rework_cycle, conn=conn)`.
    - `validate_dependencies(db, issue, conn=conn)` calling `db.get_dependencies(issue.id, conn=conn)`.
    - `validate_wip_limit(db, project_id, target_state, assignee, conn=conn)` calling `db.count_issues_in_state(..., conn=conn)` and `db.count_agent_active_issues(..., conn=conn)`.
  - `_transition_tx` passes the caller's active connection through all guard reads and mutates `pm_issues` on that exact connection without opening a second transaction. Caller principal resolution via `ExecutionContext` is strictly preserved.
  - Public `FSMEngine.transition(...)` delegates to `with self._lock: with self.db.atomic_transaction() as conn: return self._transition_tx(conn, ...)`.
- **Atomic Multi-Table Ingestion:**
  - In `mas/pm/db.py`: `PMDatabase.ingest_agent_event_tx(conn: sqlite3.Connection, event: AgentEvent) -> Tuple[EventReceipt, Optional[Issue], int]` [PROPOSED].
  - Inside a single `with db.atomic_transaction() as conn:` block:
    1. Insert event into `pm_events` [PROPOSED].
    2. If evidence payload is present (`evidence.submitted`), insert into `pm_evidence_links` on `conn`.
    3. If transition is requested, call `fsm._transition_tx(conn, ...)`. Guard reads observe uncommitted evidence on `conn`.
    4. If notes or comments are present, insert into `pm_comments` [PROPOSED] on `conn`.
    5. Advance the integer cursor and append to `pm_changes` [PROPOSED] on `conn`.
  - If any guard fails, constraint violates, or exception occurs, the single transaction issues `ROLLBACK`. Event, evidence, state mutation, comments, and change feed cursor roll back together as an indivisible unit.
- **Test Specification Matrix:**
  - **Atomic Rollback Verification:** Injected failure at any phase (guard rejection, sequence gap, invalid cursor) asserts 0 residual rows across `pm_events`, `pm_evidence_links`, `pm_issues`, `pm_comments`, and `pm_changes`.
  - **Concurrent-Writer Verification:** Two concurrent threads/processes executing `BEGIN IMMEDIATE` transactions assert serialized isolation, absence of race conditions, and proper handling of SQLite's 5000ms busy timeout.

---

### 5. Candidate/Evidence Validation & Artifact Origin Policy

- **Candidate Submission (`candidate.submitted`):** Requires full 40-character Git commit SHA verified in repository object database and artifact digest.
- **Evidence Submission (`evidence.submitted`):** Requires task ID, attempt ID, candidate commit SHA, test-suite digest, runner ID, run ID, execution timestamps, PASS/FAIL outcome, and SHA-256 content hash matching log file on disk.
- **Artifact Origin Policy:** Artifact paths must reside strictly within workspace paths matching task `path_whitelist`; no directory traversal (`..`) or external absolute paths. External URLs and arbitrary executable payloads are rejected.
- **Separation of Duties:** Reviewer verdict binds the exact candidate commit; subsequent code changes reset review state and invalidate prior approval.

---

### 6. Exact Accepted Contract Reference & Planned Verification Commands

- **Contract candidate commit:** `89db8abc61180f6fabc16b6eeb12a433bc9f00c9` (`89db8abc`).
- **Contract document digest:** `63057158ff74fe62f679d21aacea0f415c420dbcb097d9e0178e7cdc8ad58383` ([`BOARD_CONTRACT_V1.md`](BOARD_CONTRACT_V1.md)).
- **Deviations & compatibility:** Proposed `/api/pm/v1/*` endpoints are added alongside existing legacy `/api/pm/*` routes to ensure zero disruption during frontend migration.
- **Planned Verification Commands (to be executed upon backend implementation):**
  - Existing regression suite: `python3 -m pytest tests/test_dashboard.py tests/test_pm_engine.py tests/test_pm_remediation.py tests/test_pm_07_dependencies_and_authorization.py`
  - Planned contract, discovery & transaction suites: `python3 -m pytest tests/test_sba_01_contract.py tests/test_sba_02_discovery.py` [PLANNED]

---

## Acknowledgement & Status Register

- **Antigravity Technical Acknowledgement:** ACKNOWLEDGED (Revised Proposal v2) by the Antigravity development team. Resolves all implementation constraints and trust boundaries identified in Codex Review 2 ([`SBA_01_REVIEW_2.md`](SBA_01_REVIEW_2.md)).
- **Codex Agreement:** Counterparty agreement recorded at `b6d4ae34` ([`SBA_01_REVIEW_2.md`](SBA_01_REVIEW_2.md)); returned to Codex for review of revised document.
- **Independent Reviewer:** PENDING appointment by authorized deployment administrator. Antigravity does not declare independent approval, nor does Codex's counterparty agreement constitute independent review.
- **Authority Boundary Notice:** Antigravity does not declare the contract accepted on behalf of Codex or the independent reviewer.
- **Execution Budget:** 0 tokens currently allocated in `BACKLOG.json`.
- **Runtime Task Status:** SBA-01 (local SBA-1) remains in `BACKLOG` pending joint sign-off, independent reviewer appointment, and deployment token budget allocation.
- **Phase Two Sequence:** Backend implementation will commence only after formal contract gate acceptance and deployment authorization, proceeding in strict sequence: **SBA-02 → SBA-03 → SBA-04 → SBA-07**. Codex owns frontend tasks (SBA-05, SBA-06, SBA-08).

## Codex counterparty acceptance of proposal v2

Reviewed candidate ca9aa60f: design direction APPROVED WITH CONDITIONS in [SBA_01_REVIEW_3.md](SBA_01_REVIEW_3.md). Prior session, transactional-read and local identity design findings are resolved. The review's trust, watcher generation and session constraints apply to implementation. Submitted JSONL supports activity parsing; it does not establish functioning MCP/bridge integration or trusted test execution. Independent design approval and runtime admission remain pending. No further prose-only resubmission is required solely to restate the implementation constraints.

## CEO owner approval and implementation authorization

The CEO explicitly accepted the recorded risks and authorized implementation in this conversation. This clears the design gate by owner decision; it is not independent technical approval. Antigravity may proceed with SBA-02 and Codex with SBA-05 under the agreed ownership split. Existing server authorization and review requirements remain. No runtime token budget or credential was provisioned by this document.
