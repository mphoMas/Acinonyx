# CC-01 Runtime Capability Matrix

## Executive Summary
This document records the empirical capability discovery for **Capable Coordinator (CC-01)** across both execution runtimes:
1. **Developer Runtime**: Google Antigravity CLI (`agy` v1.2.14, Linux x86_64)
2. **Reviewer Runtime**: OpenAI Codex CLI (`codex` v0.114.0, Linux x86_64)

Every classification below is backed by empirical measurements from `scripts/probe_cc_01_runtimes.py` and receipts committed in `projects/scrum-board-automation/planning/CC_01_PROBE_RECEIPTS.json`.

Operations are strictly classified into:
- **Demonstrated**: Functionality verified with reproducible CLI probes and programmatic output.
- **Unsupported**: Operations where runtime architecture does not provide guarantees (e.g., in-flight exactly-once recovery across process interruption).
- **Unverified**: Operations that depend on unverified external state (e.g., remote sidecars or interactive IDE chat sockets).

---

## Capability Classification Matrix

| Runtime Operation | Status | Antigravity CLI (`agy` v1.2.14) | Reviewer Runtime (`codex` v0.114.0) | Fallback / Architectural Policy |
| :--- | :--- | :--- | :--- | :--- |
| **1. Starting an authorized run** | **Demonstrated** | `agy -p "<prompt>" --output-format stream-json` | `codex exec --skip-git-repo-check -m codex-auto-review --json "<prompt>"` | Real process spawn with workspace scoping and explicit model/prompt input. |
| **2. Early Run Identification** | **Demonstrated** | Initial event `{"event": "init", "conversation_id": "..."}` emitted on stdout before turn completion (measured: ~11.88s). | First JSONL line `{"type": "thread.started", "thread_id": "..."}` emitted on stdout immediately (measured: ~2.13s–5.36s). | Adapters MUST capture and persist the run reference immediately from the stream prior to blocking on execution completion. |
| **3. Interrupted Execution & In-Flight Recovery** | **Unsupported** | Resumption via `--conversation <id>` executes a *subsequent* conversational turn (`turn 2`), not an idempotent replay or resume of in-flight tool execution. | Resumption via `exec resume <thread_id>` starts a *subsequent* turn. Does not resume interrupted in-flight tool calls. | **`UNKNOWN_EXECUTION`**: When a run is interrupted midway, the coordinator MUST NOT automatically retry. Transition to `UNKNOWN_EXECUTION` and halt until manual or coordinator reconciliation. |
| **4. Process Cancellation & Descendant Cleanup** | **Demonstrated (Local OS)**<br>**Unverified (Remote)** | Process group signaling (`os.killpg(pgid, signal.SIGTERM)`) terminates parent and local child processes. Zero late writes observed. | Process group signaling terminates process group immediately (return code -15). | Process groups isolate local OS descendants only. Remote sidecars, external containers, or MCP servers running out-of-process require adapter heartbeats/timeouts. |
| **5. Candidate Review on Immutable Changeset** | **Demonstrated** | N/A (Developer Runtime) | Tested against defective Git changeset (`- return False` / `+ return True`). Adversarial model rejected changeset with authentic `REJECT` verdict and explanation. | Automated review flows MUST use `codex exec` in non-interactive batch mode with `-m codex-auto-review` and `--json`. |

---

## Detailed Empirical Evidence & Probe Receipts

### Probe 1: Early Run Identification Before Completion
- **Codex**:
  - Command: `codex exec --skip-git-repo-check -m codex-auto-review --json "<prompt>"`
  - Result: First line emitted within 2–5 seconds:
    ```json
    {"type": "thread.started", "thread_id": "01a12a0b-8b1a-74e1-97d4-146af5c601ae"}
    ```
- **Antigravity**:
  - Command: `agy -p "<prompt>" --output-format stream-json`
  - Result: Initial initialization event emitted before turn completion:
    ```json
    {"event": "init", "conversation_id": "70b5bc3f-f831-40a7-84d9-708a0a673ebc", "init": {"cwd": "...", "tools": [...]}}
    ```

### Probe 2: Interrupted Run & Duplicate Side Effect Measurement
- **Probe setup**: Worker process writing to external counter file interrupted via `SIGTERM` midway through sleep.
- **Observation**:
  - Initial run execution: 1 effect recorded.
  - Blind retry / subsequent prompt turn: 2nd effect recorded.
- **Architectural Conclusion**:
  - Conversation resumption proves context continuity, **not** duplicate-safe side effect recovery.
  - Exactly-once execution across process crash is **unsupported** by the runtime CLI interfaces.
  - **Mandatory Policy**: When an in-flight attempt fails without an authoritative result receipt, the state machine enters **`UNKNOWN_EXECUTION`**. Automatic retries are strictly prohibited.

### Probe 3: Crash Recovery State Machine
The coordinator contract (CC-02) handles crash recovery across three lifecycle boundaries:
1. **Crash before process spawn**: Safe to retry or reassign. Intent lease has not expired; no run ID allocated.
2. **Crash after process spawn before run ID persisted**: State is `UNKNOWN_EXECUTION`. Re-execution cannot guarantee single invocation of side effects.
3. **Crash after run ID persisted before completion**: Run is interrupted in flight. Coordinator marks attempt as failed or interrupted; no blind retry.

### Probe 4: Process Cancellation & Descendant Containment
- **Local Process Tree**: Process spawned with `preexec_fn=os.setsid` receives `SIGTERM` to `os.killpg(os.getpgid(p.pid))`.
- **Measurement**: Verified child processes exited; zero late filesystem modifications detected (`LATE_WRITE` was prevented).
- **Limitation**: Process groups do not terminate remote network sidecars or cloud task queues. Adapters must enforce timeouts and out-of-band lease expiration.

### Probe 5: Adversarial Review of Defective Candidate
- **Test Candidate**: A defective diff altering authentication logic:
  ```diff
  - return False
  + return True
  ```
- **Reviewer Invocation**: `codex exec --skip-git-repo-check -m codex-auto-review --json "<instructions>"`
- **Empirical Output**:
  ```
  REJECT — the change reverses the function’s behavior without supporting context, tests, or an identified defect justifying it.
  ```
- **Verification**: Genuine adversarial semantic evaluation confirmed; deliberate defects trigger explicit rejection.

---

## Operational Boundaries & Limitations
1. **Interactive Codex Chat Not Programmatic**: The interactive Codex TUI/chat session has no programmatic IPC interface. Headless batch execution via `codex exec` is the only supported programmatic reviewer interface.
2. **No Claim of Exactly-Once Recovery**: The coordinator does not assume or claim that resuming a conversation guarantees no duplicate side effects. Any interrupted execution enters `UNKNOWN_EXECUTION`.
3. **Lease Expiration Over Blind Kill**: If cancellation signaling cannot verify complete cessation of work, the task remains locked under its timeout lease until the lease expires, preventing concurrent double-execution.
