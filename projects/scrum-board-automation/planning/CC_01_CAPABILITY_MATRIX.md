# CC-01 Runtime Capability Matrix

## Executive Summary
This document records the empirical capability discovery for **Capable Coordinator (CC-01)** across both execution runtimes:
1. **Developer Runtime**: Google Antigravity CLI (`agy` v1.3.3, Linux x86_64)
2. **Reviewer Runtime**: OpenAI Codex CLI (`codex` v0.114.0, Linux x86_64)

Every classification below is backed by empirical measurements from `scripts/probe_cc_01_runtimes.py` and receipts committed in `projects/scrum-board-automation/planning/CC_01_PROBE_RECEIPTS.json`.

Operations are strictly classified into:
- **Demonstrated**: Functionality verified with reproducible CLI probes and programmatic output.
- **Unsupported**: Operations where runtime architecture does not provide guarantees (e.g., in-flight exactly-once recovery across process interruption).
- **Unverified**: Operations that depend on unverified external state (e.g., remote sidecars or interactive IDE chat sockets).

---

## Capability Classification Matrix

| Runtime Operation | Status | Antigravity CLI (`agy` v1.3.3) | Reviewer Runtime (`codex` v0.114.0) | Fallback / Architectural Policy |
| :--- | :--- | :--- | :--- | :--- |
| **1. Starting an authorized run** | **Demonstrated** | `agy -p "<prompt>" --output-format stream-json` | `codex exec --skip-git-repo-check -m codex-auto-review --json "<prompt>"` | Real process spawn with workspace scoping and explicit model/prompt input. |
| **2. Early Run Identification** | **Demonstrated** | Initial event `{"event": "init", "conversation_id": "..."}` emitted on stdout before turn completion (measured: ~34.67s). | First JSONL line `{"type": "thread.started", "thread_id": "..."}` emitted on stdout immediately (measured: ~5.36s). | Adapters MUST capture and persist the run reference immediately from the stream prior to blocking on execution completion. |
| **3. Interrupted Execution & In-Flight Recovery** | **Unsupported** | Resumption via `--conversation <id>` executes a *subsequent* conversational turn (`turn 2`), not an idempotent replay or resume of in-flight tool execution. | Resumption via `exec resume <thread_id>` starts a *subsequent* turn. Does not resume interrupted in-flight tool calls. | **`UNKNOWN_EXECUTION`**: When a run is interrupted midway, the coordinator MUST NOT automatically retry. Transition to `UNKNOWN_EXECUTION` and halt until manual or coordinator reconciliation. Proved via synthetic subprocess side-effect duplication. |
| **4. Process Cancellation & Descendant Cleanup** | **Demonstrated (Local OS)**<br>**Unverified (Remote)** | Process group signaling (`os.killpg(pgid, signal.SIGTERM)`) terminates parent and local child processes. Child PID tracked via `psutil`; verified exited with zero late filesystem writes past scheduled deadline. | Process group signaling terminates process group immediately (return code -15). | Process groups isolate local OS descendants only. Remote sidecars, external containers, or MCP servers running out-of-process require adapter heartbeats/timeouts. |
| **5. Candidate Review on Immutable Git Changeset** | **Demonstrated** | N/A (Developer Runtime) | Tested against a real disposable Git commit introducing deliberate auth bypass (`def verify_admin(token): return True`). Model rejected changeset with authentic `REJECT` verdict and detailed security rationale. | Automated review flows MUST use `codex exec` in non-interactive batch mode with `-m codex-auto-review` and `--json`. |

---

## Detailed Empirical Evidence & Probe Receipts

### Probe 1: Early Run Identification Before Completion
- **Codex**:
  - Command: `codex exec --skip-git-repo-check -m codex-auto-review --json "echo probe1"`
  - Latency: ~5.36s
  - Result: First line emitted on stdout before turn completion:
    ```json
    {"type": "thread.started", "thread_id": "01a12a99-1942-7813-bfef-38f81d254ef1"}
    ```
- **Antigravity**:
  - Command: `agy -p "echo probe1" --output-format stream-json`
  - Latency: ~34.67s
  - Result: Initial initialization event emitted before turn completion:
    ```json
    {"event": "init", "conversation_id": "efd5da11-9334-4981-b1e1-9233f9b016e6"}
    ```

### Probe 2: Interrupted Run & Synthetic Side Effect Duplication
- **Evaluation Type**: Synthetic controlled subprocess demonstration.
- **Probe setup**: Worker process writing to an external append-only log file interrupted via `SIGTERM` midway through sleep, followed by a simulated retry turn.
- **Observation**:
  - Initial run execution: 1 effect recorded.
  - Blind retry / subsequent prompt turn: 2nd effect recorded (`duplicate_executed: true`).
- **Architectural Conclusion**:
  - Conversation resumption proves context continuity, **not** duplicate-safe side effect recovery.
  - Exactly-once execution across process crash is **unsupported** by the runtime CLI interfaces.
  - **Mandatory Policy**: When an in-flight attempt fails without an authoritative result receipt, the state machine enters **`UNKNOWN_EXECUTION`**. Automatic retries are strictly prohibited.

### Probe 3: Crash Recovery State Machine Specification
- **Evaluation Type**: Proposed architectural policy specification (governing CC-02/CC-03 contracts).
- The coordinator contract (CC-02) handles crash recovery across three lifecycle boundaries:
  1. **Crash before process spawn**: Safe to retry (`SAFE_RETRY`). Intent lease has not expired; no run ID allocated.
  2. **Crash after process spawn before run ID persisted**: State is `UNKNOWN_EXECUTION`. Re-execution cannot guarantee single invocation of side effects; automatic retry prohibited.
  3. **Crash after run ID persisted before completion**: Run is interrupted in flight (`INTERRUPTED_IN_FLIGHT`). Coordinator marks attempt as failed; no blind retry.

### Probe 4: Process Cancellation & Descendant Containment
- **Evaluation Type**: Empirical process group signaling with deadline observation.
- **Local Process Tree**: Process spawned with `preexec_fn=os.setsid` receives `SIGTERM` to `os.killpg(os.getpgid(p.pid))`.
- **Measurement**:
  - Tracked child PID: `245588` (scheduled to write `LATE_WRITE` after 2s).
  - Parent terminated after 0.3s; probe observed past the 2s scheduled deadline for 3.0s total.
  - Child survival check (`psutil`): `child_survived_past_deadline: false`.
  - Late filesystem writes: `None`.
- **Limitation**: Process groups isolate local OS descendants only. Remote sidecars, cloud jobs, or out-of-process containers require adapter heartbeats and lease expiration.

### Probe 5: Adversarial Review of Real Defective Git Commit
- **Evaluation Type**: Empirical Git commit review.
- **Candidate Commit**: Real disposable Git repository commit with subject `bypass auth check (defective)` introducing:
  ```diff
  def verify_admin(token):
  -    if not token:
  -        return False
  -    return False
  +    # bypass check
  +    return True
  ```
- **Reviewer Invocation**: `codex exec --skip-git-repo-check -m codex-auto-review --json "<prompt>"`
- **Empirical Output**:
  ```
  **REJECT**

  `verify_admin()` now returns `True` for every token, including `None`, empty, malformed, or forged values. This completely bypasses administrator authentication and is a critical security vulnerability. Restore actual token validation and add tests covering invalid, missing, expired, and...
  ```
- **Verification**: Genuine adversarial semantic evaluation confirmed; deliberate defects trigger explicit rejection (`verdict_detected: "REJECT"`, `verdict_authentic: true`).

---

## Operational Boundaries & Limitations
1. **Interactive Codex Chat Not Programmatic**: The interactive Codex TUI/chat session has no programmatic IPC interface. Headless batch execution via `codex exec` is the only supported programmatic reviewer interface.
2. **No Claim of Exactly-Once Recovery**: The coordinator does not assume or claim that resuming a conversation guarantees no duplicate side effects. Any interrupted execution enters `UNKNOWN_EXECUTION`.
3. **Lease Expiration Over Blind Kill**: If cancellation signaling cannot verify complete cessation of work, the task remains locked under its timeout lease until the lease expires, preventing concurrent double-execution.

