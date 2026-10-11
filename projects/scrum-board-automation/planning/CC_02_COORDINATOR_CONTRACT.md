# CC-02 Capable Coordinator Contract Specification

**Document Version:** 1.3.0-correction
**Delivery Owner:** Antigravity (Backend, Engine, Runtime Integration)  
**Reviewer:** Codex (Frontend, UI/UX, Interface Requirements) / Independent Reviewer  
**Status:** REVISED SPECIFICATION (Addressing Independent Review 3 Findings)  
**Workstream:** Capable Coordinator (Priority 1)  

---

## 1. Scope and Architectural Objectives

The Capable Coordinator provides autonomous, resilient, and policy-governed dispatch and tracking of agent work across the Software Development Lifecycle (SDLC). It bridges high-level project management plans in **MAS-PM** with heterogeneous AI execution engines:
- **Developer Runtime:** Google Antigravity CLI (`agy` headless process-group execution)
- **Reviewer Runtime:** OpenAI Codex CLI (`codex exec` headless batch review)

This specification defines the formal identity models, relational persistence schemas, monotonic fencing tokens, CAS dispatch claims, stale worker rejection, crash recovery boundaries, conservative budget settlement, execution containment limits, full versioned versioned HMAC evidence envelopes, adapter contracts, event cursor tracking, and staged reconciliation protocols required to govern **CC-03** through **CC-15**.

---

## 2. Core Identity Model & Hierarchical Relationships

The coordinator enforces strict separation between session continuity, intent, execution attempts, physical runs, deployment issues, and candidate artifacts.

```
+---------------------------------------------------------------------------------------------------+
| Tenant (tenant_id)                                                                                |
|   +---------------------------------------------------------------------------------------------+ |
|   | Project (project_id, project_key)                                                           | |
|   |   +---------------------------------------------------------------------------------------+ | |
|   |   | Planning Task (task_id [UUID], planning_reference [e.g. SBA-01])                      | | |
|   |   |   |                                                                                   | | |
|   |   |   +---> Deployment Issue (issue_id [UUID] -> pm_issues.id)                            | | |
|   |   |           |                                                                           | | |
|   |   |           +---> Attempt (attempt_id [UUID], attempt_seq: 1, 2, ...)                   | | |
|   |   |                   |                                                                   | | |
|   |   |                   +---> Outbox Intent (intent_id, fencing_token, status)              | | |
|   |   |                   |                                                                   | | |
|   |   |                   +---> Physical Run (run_id, runtime_session_id, pid, pgid)          | | |
|   |   |                   |       |                                                           | | |
|   |   |                   |       +---> Event Cursors (cursor_seq: 0, 1, 2, ...)              | | |
|   |   |                   |                                                                   | | |
|   |   |                   +---> Candidate Commit (candidate_id, commit_sha, tree_sha)         | | |
|   |   |                   |                                                                   | | |
|   |   |                   +---> Signed Evidence Envelope (evidence_id, nonce, hmac_signature) | | |
|   |   |                   |                                                                   | | |
|   |   |                   +---> Signed Verdict Envelope (verdict_id, nonce, hmac_signature)  | | |
|   |   +---+---+-----------+-------------------------------------------------------------------+ | |
+-------+-------------------------------------------------------------------------------------------+
```

### 2.1 Identity Definitions & Separation of Concerns

1. **Planning Task Identity (`task_id` [UUID])**:
   - Immutable, globally unique UUID originating from `BACKLOG.json` or plan specifications.
   - Retains identity across plan revisions, board migrations, and cross-deployment syncs.
   - Used for portfolio-level roadmaps, dependency DAGs, and multi-tenant tracking.

2. **Deployment Issue Identity (`issue_id` [UUID])**:
   - Primary key of `pm_issues(id)` in the deployment-local SQLite database.
   - Represents the local operational ticket hosting live FSM state, assignee, policy version, and evidence links.
   - Distinct from `task_id`; mapped 1:1 via `pm_task_mappings`.

3. **Planning Reference (`planning_reference`)**:
   - Human-readable canonical reference (e.g., `SBA-01`, `CC-02`).
   - Unique within a project. Mapped to `(task_id, issue_id)` in `pm_task_mappings`.

4. **Attempt Identity (`attempt_id` [UUID], `attempt_seq` [int])**:
   - Uniquely identifies a single execution loop iteration for a deployment issue.
   - Sequence increments monotonically (`1`, `2`, `3`, ...).
   - Bounded by maximum reflexion / rework appetite (default: max 3 cycles).

5. **Outbox Intent Identity (`intent_id` [UUID], `fencing_token` [int])**:
   - Durable dispatch intent in the SQLite outbox.
   - Guarded by a strictly monotonic generation counter (`fencing_token`).

6. **Physical Run Identity (`run_id` [UUID])**:
   - A single physical OS process spawn or CLI dispatch execution.
   - Associated with a runtime-emitted identifier:
     - Antigravity: `conversation_id` (UUID).
     - Codex: `thread_id` (UUID).
   - **Crucial Separation:** `runtime_session_id` identifies conversational context history; `run_id` identifies a specific in-flight OS execution process. Resuming a conversation starts turn 2 of a session, which is a new run attempt, NOT in-flight recovery of run 1.

7. **Event Cursor (`cursor_seq` [int])**:
   - Monotonically increasing event sequence number within a physical run stream.
   - Ensures lossless event ordering, idempotent event consumption, and resume cursors.

8. **Candidate Identity (`candidate_id` [UUID], `commit_sha` [hex-40/64])**:
   - Immutable pointer to a Git commit in the local object database.
   - Must be committed and resolvable via `git rev-parse` before transition to verification.

9. **Signed Evidence Identity (`evidence_id` [UUID], `content_hash` [SHA-256])**:
   - Cryptographically anchored record linking a Git commit SHA, test execution log, or benchmark receipt.
   - Signed with HMAC-SHA256 (`provenance_signature`) across all security-relevant identity and outcome fields.

### 2.2 Historical Identity Preservation & Collision-Checked Migration

To avoid silent identity reassignment or overwriting historical ticket keys (such as `sba-uuid-sba-01` from initial prototypes):
- Historical database records in `pm_issues` retain their existing primary key `pm_issues.id`.
- The mapping table `pm_task_mappings` records:
  - `planning_task_id`: Canonical planning UUID.
  - `issue_id`: Deployment-local issue UUID.
  - `legacy_task_id`: Historical prototype string identifier (e.g., `sba-uuid-sba-01`).
  - `planning_reference`: Canonical human key (e.g., `SBA-01`).
- **Collision-Checked Invariant:** Before inserting or updating mappings, the migration routine checks:
  1. `planning_reference` is unique within `project_id`.
  2. `issue_id` exists in `pm_issues` and is not mapped to a different `planning_task_id`.
  3. `legacy_task_id` is preserved for historical audit trails and backward-compatible lookups.

---

## 3. Relational Persistence Schemas & Uniqueness Constraints

The coordinator persistence model expands `mas.pm.db` with durable outbox, attempt, run, and event tracking tables. All tables enforce relational integrity, foreign keys, and transactional boundaries.

```sql
-- Existing pm_task_mappings remains authoritative; do not recreate or rename it.
-- The redundant identity index enables composite ownership foreign keys.
CREATE UNIQUE INDEX IF NOT EXISTS uq_coord_mapping_identity
ON pm_task_mappings(project_id, task_id, local_issue_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_coord_issue_project
ON pm_issues(project_id, id);

-- CC-02 / CC-03: Durable Coordinator Outbox Intents Table
CREATE TABLE IF NOT EXISTS pm_coordinator_intents (
    intent_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,               -- References deployment-local issue
    task_id TEXT NOT NULL,                -- Preserves stable planning UUID
    attempt_id TEXT NOT NULL,
    adapter_type TEXT NOT NULL CHECK(adapter_type IN ('antigravity', 'codex', 'synthetic')),
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'CLAIMED', 'PROCESSING', 'COMPLETED', 'FAILED', 'UNKNOWN_EXECUTION', 'CANCELED', 'CANCEL_REQUESTED')),
    fencing_token INTEGER NOT NULL DEFAULT 1,
    worker_id TEXT,
    lease_expires_at REAL,
    lease_heartbeat_at REAL,
    payload JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
    FOREIGN KEY(attempt_id, issue_id, task_id, project_id, tenant_id)
        REFERENCES pm_coordinator_attempts(attempt_id, issue_id, task_id, project_id, tenant_id),
    CONSTRAINT uq_intent_issue_attempt UNIQUE (issue_id, attempt_id, adapter_type)
);
CREATE INDEX IF NOT EXISTS idx_coord_intents_status ON pm_coordinator_intents(status, lease_expires_at);
CREATE INDEX IF NOT EXISTS idx_coord_intents_task ON pm_coordinator_intents(task_id);

-- CC-02 / CC-03: Execution Attempts Table
CREATE TABLE IF NOT EXISTS pm_coordinator_attempts (
    attempt_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_seq INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN_EXECUTION', 'CANCELED')),
    fencing_token INTEGER NOT NULL DEFAULT 1,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    budget_tokens_allocated INTEGER NOT NULL DEFAULT 0,
    budget_tokens_spent INTEGER NOT NULL DEFAULT 0,
    candidate_commit_sha TEXT,
    failure_reason TEXT,
    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
FOREIGN KEY(project_id, task_id, issue_id)
        REFERENCES pm_task_mappings(project_id, task_id, local_issue_id),
    FOREIGN KEY(project_id, issue_id) REFERENCES pm_issues(project_id, id),
    CONSTRAINT uq_attempt_identity UNIQUE (attempt_id, issue_id, task_id, project_id, tenant_id),
    CONSTRAINT uq_issue_attempt_seq UNIQUE (issue_id, attempt_seq)
);
CREATE INDEX IF NOT EXISTS idx_coord_attempts_issue ON pm_coordinator_attempts(issue_id);

-- CC-02 / CC-03: Physical Process Runs Table
CREATE TABLE IF NOT EXISTS pm_coordinator_runs (
    run_id TEXT PRIMARY KEY,
    intent_id TEXT NOT NULL REFERENCES pm_coordinator_intents(intent_id),
    attempt_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    runtime_session_id TEXT,              -- conversation_id or thread_id
    process_pid INTEGER,
    process_pgid INTEGER,
    status TEXT NOT NULL CHECK(status IN ('SPAWNING', 'STREAMING', 'EXITED', 'INTERRUPTED', 'KILLED')),
    exit_code INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY(attempt_id) REFERENCES pm_coordinator_attempts(attempt_id) ON DELETE CASCADE,
    CONSTRAINT uq_physical_dispatch UNIQUE (intent_id, fencing_token)
);
CREATE INDEX IF NOT EXISTS idx_coord_runs_attempt ON pm_coordinator_runs(attempt_id);

-- CC-02 / CC-03: Monotonic Event Cursors Table
CREATE TABLE IF NOT EXISTS pm_coordinator_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    cursor_seq INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_payload JSON NOT NULL,
    emitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES pm_coordinator_runs(run_id) ON DELETE CASCADE,
    CONSTRAINT uq_run_cursor UNIQUE (run_id, cursor_seq)
);
CREATE INDEX IF NOT EXISTS idx_coord_events_run ON pm_coordinator_events(run_id, cursor_seq);

-- CC-02 / CC-03: Signed Evidence Receipts Table
CREATE TABLE IF NOT EXISTS pm_coordinator_evidence_receipts (
    evidence_id TEXT PRIMARY KEY,
    issue_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    candidate_commit_sha TEXT NOT NULL,
    nonce TEXT NOT NULL UNIQUE,           -- Replay prevention
    key_id TEXT NOT NULL,                 -- Key rotation identifier
    signature TEXT NOT NULL,              -- Hex-encoded HMAC-SHA256 signature
    canonical_payload JSON NOT NULL,      -- Canonical RFC-8785 serialized payload
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
    FOREIGN KEY(attempt_id) REFERENCES pm_coordinator_attempts(attempt_id) ON DELETE CASCADE,
    FOREIGN KEY(run_id) REFERENCES pm_coordinator_runs(run_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_evidence_issue ON pm_coordinator_evidence_receipts(issue_id);
```

---

## 4. Durable Dispatch, Leases, and Monotonic Fencing

Network calls and process spawns MUST NOT occur within relational database transactions.

### 4.1 Compare-And-Swap (CAS) Claim Protocol (Unlaunched Work Only)

A worker claiming work executes an atomic CAS update. **The claim query strictly matches `status = 'PENDING'`. Expired `PROCESSING` work is NEVER claimed via this path to eliminate redispatch hazards:**

```sql
UPDATE pm_coordinator_intents
SET status = 'CLAIMED',
    worker_id = :worker_id,
    fencing_token = fencing_token + 1,
    lease_expires_at = :now_epoch + :lease_timeout_s,
    lease_heartbeat_at = :now_epoch,
    updated_at = :now_iso
WHERE intent_id = :intent_id
  AND status = 'PENDING'
  AND fencing_token = :expected_fencing_token;
```

If zero rows are updated, the claim fails (lost race or state changed). The worker aborts dispatch without spawning any process.

### 4.2 Pre-Spawn Persistence (`SPAWN_INTENT`)

Before the worker executes `subprocess.Popen` or begins any CLI runtime dispatch:
1. The worker commits a durable `SPAWN_INTENT` transition:
   ```sql
   UPDATE pm_coordinator_intents
   SET status = 'PROCESSING',
       lease_heartbeat_at = :now_epoch,
       updated_at = :now_iso
   WHERE intent_id = :intent_id
     AND status = 'CLAIMED'
     AND worker_id = :worker_id
     AND fencing_token = :assigned_fencing_token
     AND lease_expires_at > :now_epoch;
   ```
2. Check exactly one affected row. In the SAME transaction, update the already-created attempt and insert the unique physical run record in SPAWNING state. On any failure roll back every update and do not spawn. Do not insert a second attempt at launch.
3. After transaction commit, only this successful claimant may spawn once. Never retry Popen after an ambiguous outcome; reconcile PROCESSING as UNKNOWN_EXECUTION. The small commit-to-spawn interval is intentionally conservative: a crash may mark unlaunched work unknown, never duplicate it.
3. If the worker host crashes during or immediately following process spawn, the persisted state in SQLite is already `PROCESSING`. Because `PROCESSING` intents are excluded from the CAS claim query, **no second worker can claim or redispatch the task**.

### 4.3 Expired Lease Reaper & Reconciliation Engine

A background reaper periodically inspects active leases where `lease_expires_at < :now_epoch`:
- **Case 1: Expired in `CLAIMED` State:**
  - The worker claimed the intent but died before committing `SPAWN_INTENT` / launching the process.
  - The reaper verifies against `pm_coordinator_runs` that zero process records exist.
  - The intent is transitioned to `FAILED` with reason `CLAIM_TIMEOUT_PRE_SPAWN`, or flagged for operator review.
- **Case 2: Expired in `PROCESSING` State:**
  - The worker spawned or attempted to spawn an OS process. External side effects may be in flight.
  - The reaper marks the intent as **`UNKNOWN_EXECUTION`**.
  - **Automatic re-claim and re-dispatch are strictly prohibited.**
  - The intent requires explicit coordinator reconciliation (`RECONCILE_UNKNOWN_EXECUTION`), verifying local process termination, settling token spend up to the point of lease loss, cleaning Git working tree state, and obtaining architect approval before a new attempt may be staged.

### 4.3.1 Atomic lease retirement

The reaper performs the following retirement and updates related run/attempt status in ONE transaction. It never creates a dispatch. The CLAIMED outcome is known-unlaunched only because every permitted spawn requires the guarded PROCESSING transition and run insertion above. Unexpected run records require UNKNOWN_EXECUTION instead of automatic recovery.

```sql
UPDATE pm_coordinator_intents
SET status = CASE WHEN status = 'CLAIMED' THEN 'FAILED' ELSE 'UNKNOWN_EXECUTION' END,
    fencing_token = fencing_token + 1,
    worker_id = NULL,
    updated_at = :now_iso
WHERE intent_id = :intent_id
  AND status IN ('CLAIMED', 'PROCESSING')
  AND fencing_token = :expected_fencing_token
  AND lease_expires_at <= :now_epoch;
```

Cancel/pause decisions similarly advance generation atomically, remove live worker authority and place potentially launched work in reconciliation. Late receipts are retained as quarantined observations for billing/recovery, not promoted to completion. Heartbeats require matching active state/worker/generation and a lease which has not expired; they cannot resurrect retired work.

### 4.4 Stale Worker Rejection via Monotonic Fencing

When a worker completes execution and attempts to write completion state, candidate commits, or spend tokens, it MUST present its assigned `fencing_token`:

```sql
UPDATE pm_coordinator_intents
SET status = 'COMPLETED',
    updated_at = :now_iso
WHERE intent_id = :intent_id
  AND status = 'PROCESSING'
  AND worker_id = :worker_id
  AND fencing_token = :assigned_fencing_token
  AND lease_expires_at > :now_epoch;
```

If the lease was reclaimed or advanced by a reconciliation reaper during a long network pause, the fencing generation has advanced. The database update fails with zero rows updated.
**The coordinator strictly rejects the stale worker's output and drops late results.**

---

## 5. Lifecycle State Mapping & Crash Recovery Boundaries

### 5.1 FSM State Mapping Across SDLC

The existing MAS-PM board FSM states (`BACKLOG`, `REFINED`, `STAGED`, `IN_PROGRESS`, `VERIFICATION`, `JUDICIAL_REVIEW`, `DONE`) govern board progression. Coordinator attempt and run states map into this FSM:

| PM Board State | Coordinator Attempt State | Outbox Intent State | Description / Invariants |
| :--- | :--- | :--- | :--- |
| `BACKLOG` | (None) | (None) | Task unrefined; budget tokens = 0; no runtime execution. |
| `REFINED` | (None) | (None) | Scope and acceptance criteria reviewed; financial budget proposed. |
| `STAGED` | `PENDING` | `PENDING` | Execution appetite granted; intent enqueued; ready for worker poll. |
| `IN_PROGRESS` | `RUNNING` | `CLAIMED` / `PROCESSING` | Worker spawned CLI process; run ID tracked; lease active. |
| `VERIFICATION` | `SUCCEEDED` | `COMPLETED` | Process exited code 0; candidate commit created; automated test log attached. |
| `JUDICIAL_REVIEW` | `SUCCEEDED` | `COMPLETED` | Independent reviewer evaluating signed evidence. Separation of builder and judge enforced. |
| `DONE` | `SUCCEEDED` | `COMPLETED` | Verified task acceptance only; human production release authorization remains separate. |
| `UNKNOWN_EXECUTION` | `UNKNOWN_EXECUTION` | `UNKNOWN_EXECUTION` | Process crashed or lease expired with untracked side effects. Automatic dispatch halted. |

### 5.2 Crash Recovery Boundaries

```
[Crash Point A: Before Spawn]
   --> Intent is CLAIMED; process was never spawned.
   --> SAFE_RECOVERY: Verified no process runs exist. Can reset to STAGED or FAILED.

[Crash Point B: After Spawn, Before Run ID Persisted]
   --> Process was spawned into OS; side effects may have started.
   --> UNKNOWN_EXECUTION: Worker died before storing early conversation_id / thread_id.
   --> AUTOMATIC RETRY PROHIBITED. Requires reconciliation.

[Crash Point C: Run ID Persisted, Mid-Execution Disconnection]
   --> Run ID recorded, but stream disconnected or process SIGKILLed.
   --> UNKNOWN_EXECUTION / INTERRUPTED_IN_FLIGHT:
   --> Tool executions cannot be assumed idempotent. Resumption turn is turn 2, not turn 1 replay.
```

### 5.3 Recovery Safety & External Side Effect Realities
- **Git Rollback Limitation:** `git checkout` or `git reset` rolls back working tree files on disk. **It cannot undo external side effects** (database migrations, API calls, external service writes, tokens billed).
- **Settlement Protocol:** `DISCARD_ATTEMPT` requires:
  1. Process group verification (`os.killpg`) ensuring zero surviving local descendants.
  2. Bounded token settlement: spend is tallied conservatively up to the crash point.
  3. Git working tree cleaned to base commit.
  4. Manual or architect reconciliation approval before the task may re-enter `STAGED`.

---

## 6. Versioned Canonical Evidence Signing Envelope

To prevent client tampering or substitution of test execution results, evidence attached to an issue must adhere to a strict HMAC-SHA256 canonical structure binding all security-relevant identity and outcome fields.

### 6.1 Canonical Evidence Payload Specification

The payload contains the complete execution envelope:

```json
{
  "schema_version": 1,
  "evidence_id": "ev-7a91c0b3-0001-4000-8000-000000000001",
  "tenant_id": "tenant-alpha",
  "project_id": "project-sba",
  "issue_id": "c5d9f5dc-d645-4a62-af11-dd9e064e9d55",
  "task_id": "4a1b0001-0000-4000-8000-000000000001",
  "attempt_id": "att-4a1b0001-01",
  "attempt_seq": 1,
  "run_id": "run-0dc6de08-5f2b-4eb6-8d6e-1fa07fd4d832",
  "fencing_token": 3,
  "candidate_commit_sha": "a971cf7b1091868613eaac6839001034d7dd5d2b",
  "base_commit_sha": "09b9a4e6cbbe96926bdfa1c25607bee8aa98b1df",
  "policy_version": 2,
  "test_suite": "tests/test_sba_03_plan_publication.py",
  "exit_code": 0,
  "runner_principal": "coordinator:worker:1",
  "timestamp": "2026-10-11T12:00:00Z",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "nonce": "9f8e7d6c5b4a39281701f0e1d2c3b4a5"
}
```

### 6.2 Canonical Serialization & Signature Formula (future coordinator envelope)

1. **Serialization Standard:** The payload object is canonically serialized according to RFC 8785 (JSON Canonicalization Scheme - JCS) :
   $$\text{canonical\_bytes} = \text{JCS}(\text{payload})$$
2. **Signature Formula:**
   $$\text{signature} = \text{hex}(\text{HMAC-SHA256}(K_{\text{evidence}}, \text{canonical\_bytes}))$$
3. **Key Ownership & Rotation:**
   - Keys (`MAS_EVIDENCE_SECRET`) are owned strictly by the trusted coordinator runtime environment (minimum 32 bytes). Worker agents do not possess signing keys.
   - The envelope carries `key_id` (e.g. `mas-evidence-v1`). Active keys are rotated periodically; previous keys are retained in a verification keyring.
4. **Replay Prevention:**
   - Every signed envelope includes a cryptographically random 128-bit hex `nonce`.
   - The coordinator verifies uniqueness against `pm_coordinator_evidence_receipts(nonce)` before admitting evidence. Duplicate nonces are rejected.
5. **Signed Verdict Envelope (Reviewer):**
   - The trusted reviewer admission service signs a domain-separated `mas.coordinator.verdict.v1` envelope. It binds schema/key ID, tenant/project/issue/task/attempt/run/generation, candidate/base/policy, reviewer principal, verdict, rationale hash, timestamp and nonce. Agent processes never receive signing keys. Signatures attest admitted observations, not correctness of model reasoning.
6. **Implementation Status:**
   - *Current PM implementation:* evidence provenance version 2 signs the complete PM evidence payload using precisely Python JSON with sorted keys, compact separators, ASCII escapes, no NaN/Infinity and domain `mas.pm.evidence.v2`. Explicit positive policy binding is required; TEST_RUN_LOG must name a candidate matching Git evidence. Legacy records remain historical and cannot qualify verification. This PM representation is separate from the future RFC 8785 coordinator envelope; the two are not interchangeable.
   - *Proposed CC-07/CC-08 Enforcement:* Cryptographic signature verification via HMAC and nonce uniqueness is formalized in this contract and will be enforced upstream during CC-07/CC-08 transition gates.

---

## 7. Complete Adapter Schemas, Event Cursors, and Cancellation Lifecycle

### 7.1 Adapter Request & Result Schemas

#### Adapter Execution Request (`AdapterExecutionRequest`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AdapterExecutionRequest",
  "type": "object",
  "required": [
    "tenant_id", "project_id", "issue_id", "task_id", "attempt_id",
    "attempt_seq", "fencing_token", "runtime_type", "prompt",
    "workspace_path", "path_whitelist", "budget_token_limit", "timeout_seconds"
  ],
  "properties": {
    "tenant_id": { "type": "string" },
    "project_id": { "type": "string" },
    "issue_id": { "type": "string", "format": "uuid" },
    "task_id": { "type": "string", "format": "uuid" },
    "attempt_id": { "type": "string" },
    "attempt_seq": { "type": "integer", "minimum": 1 },
    "fencing_token": { "type": "integer", "minimum": 1 },
    "runtime_type": { "type": "string", "enum": ["antigravity", "codex", "synthetic"] },
    "prompt": { "type": "string" },
    "workspace_path": { "type": "string" },
    "path_whitelist": { "type": "array", "items": { "type": "string" } },
    "budget_token_limit": { "type": "integer", "minimum": 1 },
    "timeout_seconds": { "type": "number", "minimum": 1.0 },
    "early_id_deadline_seconds": { "type": "number", "default": 15.0 }
  }
}
```

#### Adapter Execution Result (`AdapterExecutionResult`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AdapterExecutionResult",
  "type": "object",
  "required": [
    "attempt_id", "run_id", "runtime_session_id", "status",
    "exit_code", "tokens_billed", "duration_seconds"
  ],
  "properties": {
    "attempt_id": { "type": "string" },
    "run_id": { "type": "string" },
    "runtime_session_id": { "type": ["string", "null"] },
    "status": { "type": "string", "enum": ["SUCCEEDED", "FAILED", "INTERRUPTED", "TIMEOUT", "CANCELED"] },
    "exit_code": { "type": ["integer", "null"] },
    "candidate_commit_sha": { "type": ["string", "null"] },
    "tokens_billed": { "type": ["integer", "null"], "minimum": 0 },
    "duration_seconds": { "type": "number", "minimum": 0.0 },
    "artifacts": { "type": "array", "items": { "type": "object" } },
    "error_details": { "type": ["object", "null"] }
  }
}
```

#### Adapter Error Schema (`AdapterError`)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AdapterError",
  "type": "object",
  "required": ["error_code", "message", "recoverable"],
  "properties": {
    "error_code": {
      "type": "string",
      "enum": [
        "SPAWN_FAILED", "EARLY_ID_TIMEOUT", "PROCESS_CRASH",
        "BUDGET_EXCEEDED", "SIGNAL_TIMEOUT", "UNKNOWN_EXECUTION"
      ]
    },
    "message": { "type": "string" },
    "recoverable": { "type": "boolean" },
    "diagnostic_context": { "type": "object" }
  }
}
```

### 7.2 Event Cursors & Stream Ingestion

Adapters stream JSON / JSONL output from runtime processes. For each event emitted:
1. The adapter assigns a strictly monotonic `cursor_seq` starting at `0`.
2. The event is persisted to `pm_coordinator_events` with `run_id`, `cursor_seq`, `event_type`, and `event_payload`.
3. If an IPC pipe or network connection disconnects midway, the coordinator resumes or reconciles knowing the exact last-acknowledged cursor sequence.

### 7.3 Pause & Cancellation Lifecycle

1. **Cancellation Request:**
   - Operator or coordinator sets intent status to `CANCEL_REQUESTED`.
2. **Pre-Emptive Process Group Cleanup:**
   - Adapter locates `process_pgid` for the running process.
   - Issues `SIGTERM` to the process group (`os.killpg(pgid, signal.SIGTERM)`).
   - Observes process group exit over a bounded 3.0s deadline.
   - If processes survive the deadline, escalates to `os.killpg(pgid, signal.SIGKILL)`.
3. **Outcome Recording:**
   - If process exited cleanly before candidate commit creation: intent transitions to `CANCELED`.
   - If process was killed while filesystem writes or tool calls were in flight: intent transitions to `UNKNOWN_EXECUTION`.
4. **Containment Reality:**
   - Process group signaling cleanly terminates local OS subprocesses.
   - **Remote sidecars, out-of-process containers, or external network requests are NOT terminated by OS signals.** Lease expiry revokes local admission authority; it does not stop remote work or billing. A provider-enforced spending cap or verified remote cancellation is required for bounded remote execution. Otherwise retain uncertainty and reservation holds, and escalate instead of asserting containment.

---

## 8. Conservative Budget Reservation & Uncertain Spend Settlement

To protect project financial boundaries against uncoordinated overrun:

1. **Upfront Reservation:**
   - Before dispatching an attempt, the coordinator reserves the task's maximum execution appetite (`budget_tokens_allocated`) from the project pool:
     $$\text{reserved\_tokens} = \text{task.execution\_appetite}$$
2. **Clean Settlement on Completion:**
   - When an attempt completes cleanly with an authoritative adapter receipt, actual spend is settled:
     $$\text{budget\_tokens\_spent} = \text{result.tokens\_billed}$$
   - Unspent tokens ($\text{reserved\_tokens} - \text{budget\_tokens\_spent}$) are released back to the project pool.
3. **Uncertain Spend Settlement (Crash / `UNKNOWN_EXECUTION`):**
   - If a worker crashes, disconnects, or enters `UNKNOWN_EXECUTION`, actual spend cannot be confirmed from the local process.
   - **Pessimistic Settlement Rule:** The coordinator treats 100% of the reserved amount as spent:
     $$\text{budget\_tokens\_spent} = \text{budget\_tokens\_allocated}$$
   - Reserved tokens CANNOT be recycled or re-allocated until an authoritative billing log reconciliation is performed.

---

## 9. Authority & Trust Boundaries

The system enforces five distinct authority boundaries:

| Role / Authority | Boundary Enforcement | Permitted Operations |
| :--- | :--- | :--- |
| **Tenant Administrator** | HTTP / JWT Scope `admin:*` | Tenant lifecycle, session revocation, global quota management. |
| **Planner / Architect** | Roles `architect`, `data_architect`, `chief_architect`<br>or Scope `pm:plan:publish` | Plan publication, DAG authoring, version-bound reconciliation decisions (`apply`/`reject`). |
| **Coordinator (Engine)** | Service Context `coordinator` | Outbox polling, CAS claims, process dispatch, attempt sequencing, lease renewals. |
| **Developer Agent** | Task Assignee Principal | Implementation file writes within `path_whitelist`, Git commits. **DENIED:** State transitions to verification or completion. |
| **Reviewer Agent** | Independent Reviewer Principal | Critic review evaluations, verdict signing. **DENIED:** Code modifications, plan publishing. |

### 9.1 Separation of Builder and Judge
As formalized in `mas/pm/guards.py`:
- `assert_separation_of_builder_and_judge(issue, caller_principal)`
- The principal who generated the candidate commit or held developer assignment CANNOT evaluate, sign, or transition the issue through `JUDICIAL_REVIEW` or `DONE`.

---

## 10. Version-Bound Staged Reconciliation Specification

When an active task (`IN_PROGRESS`, `VERIFICATION`, `JUDICIAL_REVIEW`) is modified in a revised plan:
1. **Live Scope Preservation:**
   - Live `path_whitelist`, `acceptance_criteria`, and `reviewer_requirement` remain active and unchanged.
   - Proposed plan revisions are stored in `staged_*` fields.
   - `staged_proposal_id` (e.g. `prop_<proj>_<plan>_<rev>`) and `staged_proposal_rev` attach immutable version tags.
2. **Advancement Gating:**
   - `has_pending_reconciliation` is set to `1`.
   - All FSM transitions to `VERIFICATION`, `JUDICIAL_REVIEW`, or `DONE` fail closed until authorized reconciliation.
3. **Atomic Version-Bound Reconciliation:**
   - Reconcile request must submit: `expected_proposal_id`, `expected_proposal_rev`, and `expected_base_policy_version`.
   - If superseded or stale, the request is rejected with **HTTP 409 Conflict (`StaleProposalError`)**.
   - On `apply`: increments `policy_version += 1`, invalidates prior approvals, increments `rework_cycle` (even if evidence count is zero), and commits an immutable record to `pm_reconciliation_audits`.
   - On `reject`: discards staged fields, retaining current policy version.

---

## 11. Downstream Implementation Dependencies (CC-03 through CC-15)

With this specification revised:
- **CC-03 (Durable State & Outbox):** Build `pm_task_mappings`, `pm_coordinator_intents`, `pm_coordinator_attempts`, `pm_coordinator_runs`, `pm_coordinator_events`, and `pm_coordinator_evidence_receipts` schemas with CAS claim engine.
- **CC-04 (Outbox Worker & Lease Reaper):** Implement background polling, monotonic fencing verification, pre-spawn `SPAWN_INTENT` persistence, and expired lease reaper (`UNKNOWN_EXECUTION` transitions).
- **CC-05 (Antigravity Developer Adapter):** Implement early `conversation_id` extraction with non-blocking bounded reads and process group isolation.
- **CC-06 (Codex Reviewer Adapter):** Implement early `thread_id` extraction and automated Git commit semantic reviews.
- **CC-07 / CC-08 (Candidate Verification & FSM Dispatch):** Wire automated verification evidence, cryptographic HMAC provenance checks, and separation of duties.


## 12. Versioned additive migration and CC-03 acceptance gate

This document is a corrected design proposal; coordinator tables/dispatch are not implemented by this change. CC-03 must use a transactional schema migration ledger (version, checksum, applied_at), integrity-checked backup and reopen tests. Inspect existing schema with PRAGMA before adding fields/indexes. Never reinterpret CREATE TABLE IF NOT EXISTS as migration. Existing pm_task_mappings columns remain project_id, planning_reference, task_id, local_issue_id, local_issue_key, created_at, updated_at.

Preserve issue IDs, display keys, assignments, runtime history and evidence bytes. Canonicalizing historical non-UUID task IDs requires an approved one-to-one identity mapping, immutable legacy alias receipts and collision checks; pending active attempts prohibit identity cutover. Abort atomically on ambiguity. Do not silently rewrite the board during normal startup.

Admission creates attempts and intents in one BEGIN IMMEDIATE transaction. Verified tenant binding chooses the private database. Cross-check tenant ownership, project, issue and mapping before insertion; never trust supplied tenant_id. Composite foreign keys above bind intent ownership to its attempt and attempts to the existing mapping. Enable foreign_keys for every connection. Evidence receipts must verify run->intent->attempt ownership and complete signed envelope before insertion. Enforce one physical spawn per intent/generation, one verdict/evidence nonce per domain/tenant/key, and retain independent developer/reviewer intent roles.

Required recovery evidence before CC-03 acceptance: populated legacy database migration and reopen; unchanged history/identities; mismatched project/task/tenant rejection; concurrent claims; reaper versus pre-spawn CAS; cancel versus late result; expired heartbeat; crash before and after PROCESSING commit; duplicate physical-run insertion; unknown usage reservation hold. No automatic launch or production activation belongs to a storage migration.

Signed evidence attachment remains a claim unless a trusted verifier actually executes and admits the candidate-specific checks. Automatic DONE requires that verifier, independent review and all current server gates. These contract corrections do not grant runtime authority or self-certify their author's implementation.
