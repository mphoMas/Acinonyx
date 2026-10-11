# CC-02 Capable Coordinator Contract Specification

**Document Version:** 1.0.0-draft  
**Delivery Owner:** Antigravity (Backend, Engine, Runtime Integration)  
**Reviewer:** Codex (Frontend, UI/UX, Interface Requirements) / Independent Reviewer  
**Status:** DRAFT (Submitted for independent review before downstream implementation)  
**Workstream:** Capable Coordinator (Priority 1)  

---

## 1. Scope and Architectural Objectives

The Capable Coordinator provides autonomous, resilient, and policy-governed dispatch and tracking of agent work across the Software Development Lifecycle (SDLC). It bridges high-level project management plans in **MAS-PM** with heterogeneous AI execution engines:
- **Developer Runtime:** Google Antigravity CLI (`agy` headless process-group execution)
- **Reviewer Runtime:** OpenAI Codex CLI (`codex exec` headless batch review)

This specification defines the formal identity models, execution lifecycle, lease and outbox mechanisms, uncertain execution semantics, authority boundaries, candidate verification, and staged reconciliation protocols required to implement **CC-03** through **CC-15**.

---

## 2. Core Identity Model

The coordinator enforces strict separation between session continuity, intent, execution attempts, and candidate artifacts.

```
+-------------------------------------------------------------------------------+
| Tenant (tenant_id)                                                            |
|   +-------------------------------------------------------------------------+ |
|   | Project (project_id, project_key)                                       | |
|   |   +-------------------------------------------------------------------+ | |
|   |   | Task (task_id [UUID], planning_reference [e.g. SBA-01])            | | |
|   |   |   |                                                               | | |
|   |   |   +---> Attempt (attempt_id [UUID], attempt_seq: 1, 2, ...)       | | |
|   |   |           |                                                       | | |
|   |   |           +---> Run (run_id, runtime_session_id)                  | | |
|   |   |           |                                                       | | |
|   |   |           +---> Candidate (candidate_id, commit_sha, tree_sha)    | | |
|   |   |           |                                                       | | |
|   |   |           +---> Evidence Link (evidence_id, content_hash, sig)     | | |
|   |   |           |                                                       | | |
|   |   |           +---> Review Verdict (verdict_id, reviewer_id, sig)     | | |
|   +---+---+---------------------------------------------------------------+ | |
+-------+-----------------------------------------------------------------------+
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

4. **Run Identity (`run_id` [UUID])**:
   - A single physical OS process spawn or CLI dispatch execution.
   - Associated with a runtime-emitted identifier:
     - Antigravity: `conversation_id` (UUID).
     - Codex: `thread_id` (UUID).
   - **Crucial Separation:** `runtime_session_id` identifies conversation history; `run_id` identifies a specific in-flight OS execution process.

5. **Candidate Identity (`candidate_id` [UUID], `commit_sha` [hex-40/64])**:
   - Immutable pointer to a Git commit in the local object database.
   - Captures exact changes produced by an implementation attempt.
   - Must be committed and resolvable via `git rev-parse` before transition to verification.

6. **Evidence Identity (`evidence_id` [UUID], `content_hash` [SHA-256])**:
   - Cryptographically anchored record linking a Git commit SHA, test execution log, or benchmark receipt.
   - Signed with HMAC-SHA256 (`provenance_signature`) preventing client tampering.

---

## 3. Runtime Adapter Operations & Capability Boundaries

Based on empirical discovery from **CC-01** (`CC_01_CAPABILITY_MATRIX.md`), adapters must adhere to the following contracts:

### 3.1 Developer Adapter (Antigravity `agy`)
- **Invocation Command:** `agy -p "<prompt>" --output-format stream-json --add-dir <workspace_dir>`
- **Early Identification:** Adapter MUST parse the initial stream event (`{"event": "init", "conversation_id": "..."}`) and persist `conversation_id` before awaiting tool execution.
- **Process Group Scoping:** MUST spawn with `preexec_fn=os.setsid` to guarantee process tree signaling.
- **Capability Limits:**
  - Standard conversation resumption (`--conversation <id>`) starts a subsequent prompt turn (`turn 2`).
  - Does NOT provide in-flight resumption of broken tool chains.
  - Exactly-once tool execution across process crash is **UNSUPPORTED**.

### 3.2 Reviewer Adapter (Codex `codex`)
- **Invocation Command:** `codex exec --skip-git-repo-check -m codex-auto-review --json "<instructions>"`
- **Early Identification:** First stream event emitted within seconds: `{"type": "thread.started", "thread_id": "..."}`.
- **Process Group Scoping:** MUST spawn with `preexec_fn=os.setsid`.
- **Capability Limits:**
  - Interactive Codex TUI/chat is NOT programmatic; headless batch `codex exec` is mandatory.
  - Semantic review verdicts MUST be parsed from `item.completed` agent messages and validated for pass/reject criteria.

---

## 4. Durable Dispatch, Leases, and Outbox State Machine

Network calls and process spawns MUST NOT occur within relational database transactions.

### 4.1 Dispatch Outbox Architecture

```
[PM State Engine]
       |
       v (Atomic Transaction)
+------------------------------------+
| 1. Create Attempt Record           |
| 2. Enqueue Outbox Intent (PENDING) |
| 3. Set Execution Lease (leased_at) |
+------------------------------------+
       |
       v
[Outbox Dispatch Worker]
       |
       +---> 1. Lock Intent (PROCESSING, worker_id, lease_timeout)
       |
       +---> 2. Spawn CLI Process (outside DB transaction)
       |
       +---> 3. Read early stream line -> Update Run ID in DB
       |
       +---> 4. Await process exit / Stream results
       |
       +---> 5. Record Result & Complete Outbox Record (COMPLETED)
```

### 4.2 Lease and Idempotency Protocol

- **Lease Duration:** Default 1,800 seconds (governed by `issue.appetite_timeout_s`).
- **Heartbeat:** Outbox worker updates `lease_heartbeat_at` every 30 seconds.
- **Lease Expiration:** If a worker crashes, the lease expires after `lease_timeout_s`. Expired leases enter reconciliation before re-dispatch.
- **Process Idempotency:** If an outbox intent is dispatched, the `idempotency_key` format is:
  `coordinator:attempt:{tenant_id}:{task_id}:{attempt_seq}`

---

## 5. Lifecycle States & Uncertain Execution Handling

### 5.1 Formal Task Lifecycle

```
[BACKLOG] (tokens=0, unallocated)
    |
    v (Refinement & Appetite Allocation)
[STAGED] (scope-jailed, whitelist verified)
    |
    v (Outbox Dispatch: Attempt Spawned)
[IN_PROGRESS] (execution lease active)
    |
    +--------------------------------+
    |                                |
    v (Interrupted / Crash)          v (Normal Exit)
[UNKNOWN_EXECUTION]          [VERIFICATION] (evidence validated)
    |                                |
    +---> (Manual / Recon)           v (Critic Verdict)
                                 [JUDICIAL_REVIEW]
                                     |
                           +---------+---------+
                           |                   |
                           v (PASS)            v (REJECT)
                        [DONE]            [REWORK / BACKLOG]
```

### 5.2 UNKNOWN_EXECUTION State Specification

When a run is interrupted by process crash, network severance, SIGKILL, or ungraceful shutdown:
1. **Automatic Retry Strictly Prohibited:** Because runtimes cannot guarantee exactly-once side effects, the coordinator MUST NOT automatically launch a retry attempt.
2. **State Tagging:** The task and attempt transition to `UNKNOWN_EXECUTION`.
3. **Reconciliation Procedure:**
   - The coordinator inspects the workspace Git repository status.
   - If clean commits exist matching the task scope, the coordinator checks test execution logs.
   - If side effects are partial or unknown, human or coordinator reconciliation is required to either:
     - `DISCARD_ATTEMPT`: Revert working tree to parent commit and reschedule.
     - `ADMIT_CANDIDATE`: Advance to verification if empirical evidence exists.

---

## 6. Authority & Trust Boundaries

The system enforces four distinct authority boundaries:

| Role / Authority | Boundary Enforcement | Permitted Operations |
| :--- | :--- | :--- |
| **Tenant Administrator** | HTTP / JWT Scope `admin:*` | Tenant lifecycle, session revocation, global quota management. |
| **Planner / Architect** | Roles `architect`, `data_architect`, `chief_architect`<br>or Scope `pm:plan:publish` | Plan publication, DAG dependency authoring, staged reconciliation decision (`apply`/`reject`). |
| **Coordinator (Engine)** | Service Token / Context `coordinator` | Outbox polling, process dispatch, attempt sequencing, lease renewals. |
| **Developer Agent** | Task Assignee Principal | Implementation file writes within `path_whitelist`, Git commits. **DENIED:** State transitions to verification or completion. |
| **Reviewer Agent** | Independent Reviewer Principal | Critic review evaluations, verdict signing. **DENIED:** Code modifications, plan publishing. |

### 6.1 Separation of Builder and Judge
As formalized in `mas/pm/guards.py`:
- `assert_separation_of_builder_and_judge(issue, caller_principal)`
- The principal who generated the candidate commit or held developer assignment CANNOT evaluate, sign, or transition the issue through `JUDICIAL_REVIEW` or `DONE`.

---

## 7. Candidate Verification & Adversarial Review Protocol

1. **Commit changesets MUST be checked against path whitelist:**
   - Git changeset is inspected using `git diff-tree -m --root --no-commit-id --name-only -r <commit_sha>`.
   - Every touched file must fall within `issue.path_whitelist` and outside `issue.forbidden_paths`. Traversal patterns (`..`) fail closed.
2. **Empirical Evidence Required:**
   - Mandatory `GIT_COMMIT` pointing to immutable object in Git database.
   - Mandatory `TEST_RUN_LOG` with zero exit code and matching SHA-256 hash.
   - Provenance cryptographic signature verified via HMAC-SHA256.
3. **Adversarial Review:**
   - Reviewer runtime evaluates candidate commit.
   - Genuine rejection triggers increment of `rework_cycle`.
   - Rejection reasons recorded in `pm_critic_verdicts` with cryptographic signature.

---

## 8. Staged Reconciliation & Stale Approval Invalidation

When an active task (`IN_PROGRESS`, `VERIFICATION`, `JUDICIAL_REVIEW`) is modified in a revised plan:
1. **Live Scope Preservation:**
   - Live `path_whitelist`, `acceptance_criteria`, and `reviewer_requirement` remain active and unchanged.
   - Proposed plan revisions are stored in `staged_*` fields.
   - `staged_reviewer_action` explicitly records `REPLACE` vs `REMOVE`.
2. **Advancement Gating:**
   - `has_pending_reconciliation` is set to `1`.
   - All FSM transitions to `VERIFICATION`, `JUDICIAL_REVIEW`, or `DONE` fail closed until authorized reconciliation.
3. **Authorized Reconciliation:**
   - Handled via `POST /api/pm/v1/projects/{key}/issues/{issue_key}/reconcile`.
   - `apply`: Updates live policy to staged changes and clears staging fields.
   - `reject`: Drops staged changes, keeping original live policy.
   - If an approved candidate is modified after approval, prior approvals are invalidated.

---

## 9. Next Steps & Downstream Implementations

This specification provides the governing contracts for:
- **CC-03:** Building durable coordinator state and SQLite outbox.
- **CC-04:** Outbox worker implementation and lease reaper.
- **CC-05:** Antigravity developer adapter.
- **CC-06:** Codex reviewer adapter.
- **CC-07 / CC-08:** Candidate verification, rework loops, and automated dispatch.
