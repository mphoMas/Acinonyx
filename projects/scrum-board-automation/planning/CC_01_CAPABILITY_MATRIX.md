# CC-01 Runtime Capability Matrix

## Executive Summary
This document records the empirical capability discovery for **Capable Coordinator (CC-01)** across both execution runtimes:
1. **Developer Runtime**: Google Antigravity CLI (`agy` v1.2.14)
2. **Reviewer Runtime**: OpenAI Codex CLI (`codex` v0.114.0)

Every operation below was executed against live CLI instances in disposable, bounded environments. No operations were simulated, mocked, or extrapolated from web documentation.

---

## Capability Matrix

| Runtime Operation | Antigravity CLI (`agy` v1.2.14) | Reviewer Runtime (`codex` v0.114.0) | Supported / Fallback Mechanism |
| :--- | :--- | :--- | :--- |
| **1. Starting an authorized run** | **Supported**<br>`agy -p "<prompt>" --output-format json` (or `--input-format text`) | **Supported**<br>`codex exec --skip-git-repo-check -m codex-auto-review --json "<prompt>"` | Real process spawn with workspace scoping and explicit model/prompt input. |
| **2. Retrieving run reference & status** | **Supported**<br>Returns `conversation_id` (UUID) and status (`SUCCESS`/`FAILED`) in JSON stdout. | **Supported**<br>Streams JSONL event `thread.started` with `thread_id` (UUID), followed by `turn.completed`. | Both runtimes provide deterministic session UUID references for persistent state tracking. |
| **3. Receiving results & candidate references** | **Supported**<br>Captures final assistant text in `response` field; workspace edits/files written to disk. | **Supported**<br>Streams `item.completed` events with `agent_message` payload; structured review verdict & git refs captured. | Full stdout JSON/JSONL structured capture and local disk artifact inspection. |
| **4. Requesting cancellation & verification** | **Supported via OS process group**<br>Sends `SIGTERM` to process group (`os.killpg`), escalating to `SIGKILL` on timeout; verified process exit. | **Supported via OS process group**<br>Immediate clean shutdown on `SIGTERM` to process group (`returncode = -15`). | OS process group signaling guarantees halting without orphaned sub-processes. |
| **5. Handling interrupted connection without duplicates** | **Supported via session resumption**<br>`agy --conversation <conversation_id> -p "<prompt>" --output-format json` preserves state without duplicate kickoff. | **Supported via session resumption**<br>`codex exec resume <thread_id> --skip-git-repo-check -m codex-auto-review --json "<prompt>"` reconnects without re-executing. | In the event of an outbox timeout, crash, or disconnect, the coordinator reconnects to the existing session ID rather than spawning duplicate runs. |

---

## Detailed Runtime Empirical Evidence

### 1. Developer Runtime: Google Antigravity (`agy`)
- **CLI Binary**: `agy` (v1.2.14, Linux x86_64)
- **Invocation Interface**: Headless CLI with `--output-format json` or `--output-format stream-json`.
- **Permissions & Auth**: Uses local user session / Google Antigravity environment auth. Requires read/write access to target workspace directory.
- **Evidence Commands & Redacted Outputs**:
  ```bash
  # Start run and retrieve run ref / status:
  agy -p "Respond with exactly the word PROVEN and nothing else." --output-format json
  ```
  Output:
  ```json
  {
    "conversation_id": "31e21ec4-05fa-45c2-90f6-2ab843f8b0a3",
    "status": "SUCCESS",
    "response": "PROVEN\n",
    "duration_seconds": 26.9,
    "num_turns": 1,
    "usage": {
      "input_tokens": 27795,
      "output_tokens": 638,
      "thinking_tokens": 636,
      "cache_read_tokens": 0,
      "total_tokens": 28433
    }
  }
  ```

  ```bash
  # Session Resumption (No Duplicate Run Kickoff):
  agy --conversation 98f595b0-a93d-40aa-ac22-e8fd6420a1dc -p "What token did you respond with in the previous turn? Answer with just that token." --output-format json
  ```
  Output:
  ```json
  {
    "conversation_id": "98f595b0-a93d-40aa-ac22-e8fd6420a1dc",
    "status": "SUCCESS",
    "response": "AGY_RESUME_ALPHA\n",
    "num_turns": 2
  }
  ```

  ```bash
  # Process Cancellation:
  # Launched bounded task with preexec_fn=os.setsid, sent os.killpg(pgid, signal.SIGTERM) -> escalated to SIGKILL.
  # Result: Process terminated cleanly, exit code 1.
  ```

---

### 2. Reviewer Runtime: OpenAI Codex (`codex`)
- **CLI Binary**: `codex` (v0.114.0, Linux x86_64)
- **Invocation Interface**: Headless CLI using `codex exec --skip-git-repo-check -m codex-auto-review --json "<prompt>"`.
- **Permissions & Auth**: Uses local OpenAI Codex CLI configuration. Model flag `-m codex-auto-review` selects the reviewer model.
- **Evidence Commands & Redacted Outputs**:
  ```bash
  # Start run and stream structured JSONL events:
  codex exec --skip-git-repo-check -m codex-auto-review --json "Respond with exactly the word PROVEN and nothing else."
  ```
  Output events:
  ```json
  {"type":"thread.started","thread_id":"01a129a8-1698-74b1-b1e1-c90bcfec9cdf"}
  {"type":"turn.started"}
  {"type":"item.completed","item":{"id":"item_1","type":"agent_message","text":"PROVEN"}}
  {"type":"turn.completed","usage":{"input_tokens":10515,"cached_input_tokens":3712,"output_tokens":6}}
  ```

  ```bash
  # Session Resumption by thread_id:
  codex exec resume 01a129a9-8969-7462-84b9-e2d600dd0d21 --skip-git-repo-check -m codex-auto-review --json "What token did you respond with in the previous turn? Answer with just that token."
  ```
  Output:
  ```json
  {"type":"thread.started","thread_id":"01a129a9-8969-7462-84b9-e2d600dd0d21"}
  {"type":"item.completed","item":{"id":"item_1","type":"agent_message","text":"CODEX_RESUME_BETA"}}
  ```

  ```bash
  # Cancellation:
  # Sent os.killpg(pgid, signal.SIGTERM).
  # Result: Process immediately terminated, returncode = -15 (SIGTERM).
  ```

---

## Limitations and Architectural Concrete Fallbacks

1. **Interactive Codex Chat Not Invokable via IPC**:
   - As mandated by the protocol, the interactive Codex TUI/chat interface cannot be assumed to possess an programmatic socket or IPC hook.
   - **Supported Fallback**: All automated reviewer dispatch flows MUST invoke `codex exec` in non-interactive batch mode with `--json` streaming and `-m codex-auto-review`.
2. **Process Cancellation Boundary**:
   - Because both runtimes spawn sub-processes (Python/Rust runtimes, node sidecars, sandboxes), standard single-PID `kill(pid)` risks leaking child processes.
   - **Requirement**: The Coordinator adapter MUST spawn worker processes in new process groups (`preexec_fn=os.setsid` or `creationflags=CREATE_NEW_PROCESS_GROUP`) and issue cancellation signals to the entire process group (`os.killpg`).
3. **Session Reconnection on Network / Polling Interruption**:
   - To adhere to idempotency and prevent duplicate work or unbudgeted token consumption, the coordinator MUST persist the initial `conversation_id` / `thread_id` to its durable state before awaiting completion.
   - If a connection drops, the outbox processor reconnects using `--conversation <id>` (`agy`) or `exec resume <thread_id>` (`codex`).
