# CC-02 Capable Coordinator Contract Specification

**Document Version:** 1.1.0-revised  
**Delivery Owner:** Antigravity (Backend, Engine, Runtime Integration)  
**Reviewer:** Codex (Frontend, UI/UX, Interface Requirements) / Independent Reviewer  
**Status:** REVISED DRAFT (Governing Implementation Contract for CC-03 through CC-15)  
**Workstream:** Capable Coordinator (Priority 1)  

---

## 1. Scope and Architectural Objectives

The Capable Coordinator provides autonomous, resilient, and policy-governed dispatch and tracking of agent work across the Software Development Lifecycle (SDLC). It bridges high-level project management plans in **MAS-PM** with heterogeneous AI execution engines:
- **Developer Runtime:** Google Antigravity CLI (`agy` headless process-group execution)
- **Reviewer Runtime:** OpenAI Codex CLI (`codex exec` headless batch review)

This specification defines the formal identity models, relational persistence schemas, monotonic fencing tokens, CAS dispatch claims, stale worker rejection, crash recovery boundaries, budget settlement, execution containment limits, signed evidence structures, and staged reconciliation protocols required to implement **CC-03** through **CC-15**.

---

## 2. Core Identity Model & Hierarchical Relationships

The coordinator enforces strict separation between session continuity, intent, execution attempts, physical runs, and candidate artifacts.

```
+---------------------------------------------------------------------------------------+
| Tenant (tenant_id)                                                                    |
|   +---------------------------------------------------------------------------------+ |
|   | Project (project_id, project_key)                                               | |
|   |   +---------------------------------------------------------------------------+ | |
|   |   | Task (task_id [UUID], planning_reference [e.g. SBA-01])                   | | |
|   |   |   |                                                                       | | |
|   |   |   +---> Attempt (attempt_id [UUID], attempt_seq: 1, 2, ...)               | | |
|   |   |           |                                                               | | |
|   |   |           +---> Outbox Intent (intent_id, fencing_token, status)          | | |
|   |   |           |                                                               | | |
|   |   |           +---> Run (run_id, runtime_session_id, process_pid)             | | |
|   |   |           |                                                               | | |
|   |   |           +---> Candidate (candidate_id, commit_sha, tree_sha)            | | |
|   |   |           |                                                               | | |
|   |   |           +---> Signed Evidence (evidence_id, content_hash, signature)     | | |
|   |   |           |                                                               | | |
|   |   |           +---> Signed Verdict (verdict_id, reviewer_principal, signature)| | |
|   |   +---+---+-------------------------------------------------------------------+ | |
+-------+-------------------------------------------------------------------------------+
```

### 2.1 Identity Definitions

1. **Task Identity (`task_id` [UUID])**:
   - Immutable, globally unique UUID assigned in `BACKLOG.json` or plan definition.
   - Distinct from deployment-specific display keys (e.g., `SBA-1`, `SBA-10`).
   - Retains identity across plan revisions, re-organizations, and migrations.

2. **Planning Reference (`planning_reference`)**:
   - Human-readable canonical reference (e.g., `SBA-01`, `CC-02`).
   - Unique within a project. Mapped 1:1 with `task_id` in `pm_task_mappings`.

3. **Attempt Identity (`attempt_id` [UUID], `attempt_seq` [int])**:
   - Uniquely identifies a single execution loop iteration for a task.
   - Sequence increments monotonically (`1`, `2`, `3`, ...).
   - Bounded by maximum reflexion / rework appetite (default: max 3 cycles).

4. **Outbox Intent Identity (`intent_id` [UUID], `fencing_token` [int])**:
   - Durable dispatch intent in SQLite.
   - Guarded by a strictly monotonic generation counter (`fencing_token`).

5. **Run Identity (`run_id` [UUID])**:
   - A single physical OS process spawn or CLI dispatch execution.
   - Associated with a runtime-emitted identifier:
     - Antigravity: `conversation_id` (UUID).
     - Codex: `thread_id` (UUID).
   - **Crucial Separation:** `runtime_session_id` identifies conversational context history; `run_id` identifies a specific in-flight OS execution process. Resuming a conversation starts turn 2 of a session, which is a new run attempt, NOT in-flight recovery of run 1.

6. **Candidate Identity (`candidate_id` [UUID], `commit_sha` [hex-40/64])**:
   - Immutable pointer to a Git commit in the local object database.
   - Captures exact changes produced by an implementation attempt.
   - Must be committed and resolvable via `git rev-parse` before transition to verification.

7. **Signed Evidence Identity (`evidence_id` [UUID], `content_hash` [SHA-256])**:
   - Cryptographically anchored record linking a Git commit SHA, test execution log, or benchmark receipt.
   - Signed with HMAC-SHA256 (`provenance_signature`) preventing client tampering.

---

## 3. Relational Persistence Schemas & Uniqueness Constraints

The coordinator persistence model expands `mas.pm.db` with durable outbox and dispatch tracking tables. All tables enforce foreign keys and transactional boundaries.

```sql
-- CC-02 / CC-03: Durable Coordinator Outbox Intents
CREATE TABLE IF NOT EXISTS pm_coordinator_intents (
    intent_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    adapter_type TEXT NOT NULL CHECK(adapter_type IN ('antigravity', 'codex', 'synthetic')),
    status TEXT NOT NULL CHECK(status IN ('PENDING', 'CLAIMED', 'PROCESSING', 'COMPLETED', 'FAILED', 'UNKNOWN_EXECUTION', 'CANCELED')),
    fencing_token INTEGER NOT NULL DEFAULT 1,
    worker_id TEXT,
    lease_expires_at REAL,
    lease_heartbeat_at REAL,
    payload JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(task_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
    CONSTRAINT uq_intent_attempt UNIQUE (task_id, attempt_id)
);
CREATE INDEX IF NOT EXISTS idx_coord_intents_status ON pm_coordinator_intents(status, lease_expires_at);

-- CC-02 / CC-03: Execution Attempts Table
CREATE TABLE IF NOT EXISTS pm_coordinator_attempts (
    attempt_id TEXT PRIMARY KEY,
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
    FOREIGN KEY(task_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
    CONSTRAINT uq_task_attempt_seq UNIQUE (task_id, attempt_seq)
);

-- CC-02 / CC-03: Physical Process Runs Table
CREATE TABLE IF NOT EXISTS pm_coordinator_runs (
    run_id TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    runtime_session_id TEXT, -- conversation_id or thread_id
    process_pid INTEGER,
    process_pgid INTEGER,
    status TEXT NOT NULL CHECK(status IN ('SPAWNING', 'STREAMING', 'EXITED', 'INTERRUPTED', 'KILLED')),
    exit_code INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    FOREIGN KEY(attempt_id) REFERENCES pm_coordinator_attempts(attempt_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_coord_runs_attempt ON pm_coordinator_runs(attempt_id);
```

---

## 4. Durable Dispatch, Leases, and Monotonic Fencing

Network calls and process spawns MUST NOT occur within relational database transactions.

### 4.1 Compare-And-Swap (CAS) Claim Protocol

A worker claiming a `PENDING` outbox intent or reclaiming an expired lease executes an atomic CAS update:

```sql
UPDATE pm_coordinator_intents
SET status = 'CLAIMED',
    worker_id = :worker_id,
    fencing_token = fencing_token + 1,
    lease_expires_at = :now_epoch + :lease_timeout_s,
    lease_heartbeat_at = :now_epoch,
    updated_at = :now_iso
WHERE intent_id = :intent_id
  AND (status = 'PENDING' OR (status = 'PROCESSING' AND lease_expires_at < :now_epoch))
  AND fencing_token = :expected_fencing_token;
```

If zero rows are updated, the claim fails (lost race). The worker aborts dispatch without spawning any process.

### 4.2 Stale Worker & Late Result Rejection

When a worker completes execution and attempts to write completion state, candidate commits, or spend tokens, it MUST present its assigned `fencing_token`:

```sql
UPDATE pm_coordinator_intents
SET status = 'COMPLETED',
    updated_at = :now_iso
WHERE intent_id = :intent_id
  AND worker_id = :worker_id
  AND fencing_token = :assigned_fencing_token;
```

If the lease was stolen or incremented by a reconciliation reaper during a long network pause, the fencing generation has advanced. The database update fails with zero rows updated.
**The coordinator strictly rejects the stale worker's output and drops late results.**

---

## 5. Lifecycle State Mapping & Crash Recovery Boundaries

### 5.1 FSM State Mapping Across SDLC

The existing MAS-PM board FSM states (`BACKLOG`, `REFINED`, `STAGED`, `IN_PROGRESS`, `VERIFICATION`, `JUDICIAL_REVIEW`, `DONE`) govern board progression. Coordinator attempt and run states map cleanly into this FSM:

| PM Board State | Coordinator Attempt State | Outbox Intent State | Description / Invariants |
| :--- | :--- | :--- | :--- |
| `BACKLOG` | (None) | (None) | Task unrefined; budget tokens = 0; no runtime execution. |
| `REFINED` | (None) | (None) | Scope and acceptance criteria reviewed; financial budget proposed. |
| `STAGED` | `PENDING` | `PENDING` | Execution appetite granted; intent enqueued; ready for worker poll. |
| `IN_PROGRESS` | `RUNNING` | `CLAIMED` / `PROCESSING` | Worker spawned CLI process; run ID tracked; lease active. |
| `VERIFICATION` | `SUCCEEDED` | `COMPLETED` | Process exited code 0; candidate commit created; automated test log attached. |
| `JUDICIAL_REVIEW` | `SUCCEEDED` | `COMPLETED` | Independent reviewer evaluating signed evidence. Separation of builder and judge enforced. |
| `DONE` | `SUCCEEDED` | `COMPLETED` | Approved with cryptographic reviewer signature; closed. |
| `UNKNOWN_EXECUTION` | `UNKNOWN_EXECUTION` | `UNKNOWN_EXECUTION` | Process crashed or lease expired with untracked side effects. Automatic dispatch halted. |

### 5.2 Crash Recovery Boundaries

```
[Crash Point A: Before Spawn]
   --> Lease expired; process never launched.
   --> SAFE_RETRY: Next worker claims with fencing_token + 1.

[Crash Point B: After Spawn, Before Run ID / Fencing Persisted]
   --> Process was spawned into OS; side effects may have started.
   --> UNKNOWN_EXECUTION: Worker dies before storing early conversation_id/thread_id.
   --> AUTOMATIC RETRY FORBIDDEN.

[Crash Point C: Run ID Persisted, Mid-Execution Disconnection]
   --> Run ID recorded, but connection lost or process SIGKILLed.
   --> UNKNOWN_EXECUTION / INTERRUPTED:
   --> Tool executions cannot be assumed idempotent.
```

### 5.3 Recovery Safety & External Side Effect Realities
- **Git Rollback Limitation:** `git checkout` or `git reset` rolls back working tree files on disk. **It cannot undo external side effects** (database migrations, API calls, external service writes, tokens billed).
- **Settlement Protocol:** `DISCARD_ATTEMPT` requires:
  1. Process group verification (`os.killpg`) ensuring zero surviving local descendants.
  2. Bounded token settlement: spend is tallied up to the crash point.
  3. Git working tree cleaned to base commit.
  4. Manual or architect reconciliation approval before the task may re-enter `STAGED`.

---

## 6. Signed Evidence & Provenance Schema

To prevent client tampering or forgery of test execution results, evidence attached to an issue must adhere to a strict HMAC-SHA256 canonical structure.

### 6.1 Canonical Evidence Payload

```json
{
  "evidence_id": "ev-7a91c0b3",
  "issue_id": "c5d9f5dc-d645-4a62-af11-dd9e064e9d55",
  "tenant_id": "tenant-alpha",
  "task_id": "uuid-task-active",
  "attempt_id": "att-1",
  "attempt_seq": 1,
  "fencing_token": 3,
  "candidate_commit_sha": "a971cf7b1091868613eaac6839001034d7dd5d2b",
  "base_commit_sha": "09b9a4e6cbbe96926bdfa1c25607bee8aa98b1df",
  "evidence_type": "TEST_RUN_LOG",
  "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "test_suite": "tests/test_sba_03_plan_publication.py",
  "exit_code": 0,
  "policy_version": 2,
  "runner_principal": "coordinator-worker-1",
  "timestamp": "2026-10-11T12:00:00Z"
}
```

### 6.2 Provenance Signing & Key Ownership
- **Key Ownership:** Signing keys (`MAS_EVIDENCE_SECRET`, `MAS_VERDICT_SECRET`) are owned strictly by the trusted coordinator runtime environment (minimum 32 bytes). Worker agents do not possess signing keys.
- **Canonical Payload Digest:** The payload fields are sorted canonically and hashed via HMAC-SHA256:
  $$\text{signature} = \text{HMAC-SHA256}(K, \text{evidence\_id} \parallel \text{issue\_id} \parallel \text{candidate\_sha} \parallel \text{content\_hash} \parallel \text{policy\_version})$$
- **Verification on Transition:** `mas/pm/guards.py` verifies both the cryptographic signature and that `content_hash` matches the raw log on disk before allowing transition into `JUDICIAL_REVIEW`.

---

## 7. Execution Containment Boundaries & Realistic Limits

1. **Local Process Tree Containment:**
   - Adapters spawn worker processes with `preexec_fn=os.setsid` into dedicated POSIX process groups.
   - On cancellation or timeout, `os.killpg(pgid, signal.SIGTERM)` is issued, followed by deadline observation and `SIGKILL` if processes survive.
2. **Boundary Realities (What Process Groups DO NOT Contain):**
   - **Remote Microservices / Containers:** Out-of-process Docker containers or cloud tasks are unaffected by local OS `killpg`.
   - **Network Operations in Flight:** Sockets opened to external LLM providers or remote APIs may complete or incur billing even after local process death.
   - **Mitigation:** The coordinator relies on lease timeouts, token quota fencing, and out-of-band adapter timeouts rather than assuming OS signals provide total containment.

---

## 8. Authority & Trust Boundaries

The system enforces five distinct authority boundaries:

| Role / Authority | Boundary Enforcement | Permitted Operations |
| :--- | :--- | :--- |
| **Tenant Administrator** | HTTP / JWT Scope `admin:*` | Tenant lifecycle, session revocation, global quota management. |
| **Planner / Architect** | Roles `architect`, `data_architect`, `chief_architect`<br>or Scope `pm:plan:publish` | Plan publication, DAG authoring, version-bound reconciliation decision (`apply`/`reject`). |
| **Coordinator (Engine)** | Service Context `coordinator` | Outbox polling, CAS claim, process dispatch, attempt sequencing, lease renewals. |
| **Developer Agent** | Task Assignee Principal | Implementation file writes within `path_whitelist`, Git commits. **DENIED:** State transitions to verification or completion. |
| **Reviewer Agent** | Independent Reviewer Principal | Critic review evaluations, verdict signing. **DENIED:** Code modifications, plan publishing. |

### 8.1 Separation of Builder and Judge
As formalized in `mas/pm/guards.py`:
- `assert_separation_of_builder_and_judge(issue, caller_principal)`
- The principal who generated the candidate commit or held developer assignment CANNOT evaluate, sign, or transition the issue through `JUDICIAL_REVIEW` or `DONE`.

---

## 9. Version-Bound Staged Reconciliation Specification

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
   - On `apply`: increments `policy_version += 1`, invalidates prior approvals, increments `rework_cycle`, and commits an immutable record to `pm_reconciliation_audits`.
   - On `reject`: discards staged fields, retaining current policy version.

---

## 10. Downstream Implementation Dependencies (CC-03 through CC-15)

With this specification revised:
- **CC-03 (Durable State & Outbox):** Build `pm_coordinator_intents`, `pm_coordinator_attempts`, `pm_coordinator_runs` and CAS claim engine.
- **CC-04 (Outbox Worker & Lease Reaper):** Implement background polling, monotonic fencing verification, and expired lease reconciliation.
- **CC-05 (Antigravity Developer Adapter):** Implement early `conversation_id` extraction and process group isolation.
- **CC-06 (Codex Reviewer Adapter):** Implement early `thread_id` extraction and automated Git commit semantic reviews.
- **CC-07 / CC-08 (Candidate Verification & FSM Dispatch):** Wire automated verification evidence, cryptographic provenance checks, and separation of duties.

