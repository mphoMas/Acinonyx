# Antigravity Runtime Integration Evidence & Telemetry Specification

**Document Version:** 1.0.0  
**Scope:** SBA-01 Runtime Verification and Trust Boundary Definition  
**Date:** 2026-10-10  
**Status:** EVIDENCE SUBMISSION — Empirical runtime capture for counterparty review  

---

## 1. Runtime Environment Telemetry

The Antigravity agentic runtime executing this session operates under the following verified configuration:

| Property | Value | Verification Source |
|---|---|---|
| **Engine / Architecture** | Google DeepMind Advanced Agentic Coding (Antigravity 2.0 / Gemini 3.8 Flash High) | Runtime model configuration & metadata |
| **Operating System** | Linux (Ubuntu/Debian derivative, kernel 6.8+) | `uname -srm`, platform metadata |
| **Python Runtime** | Python 3.14.6 (Virtualenv `.venv` & system `/usr/bin/python3`) | `python3 --version`, `./.venv/bin/python --version` |
| **Active Session UUID** | `b964d376-4d79-45c8-81a7-5a28e8de5c62` | Session AppData context & directory structure |
| **Workspace Root** | `/home/acinonyx/Desktop/MAS` (`mphoMas/Acinonyx`) | Active workspace configuration |
| **Customization Roots** | `/home/acinonyx/.gemini/config` (Global) & `.agents/` (Workspace) | Customization discovery engine |
| **Log Storage Root** | `<appDataDir>/brain/<conversation-id>/.system_generated/logs/` | Active session filesystem |

---

## 2. Verified Capabilities vs. Proposed Components

To preserve strict architectural clarity, the following matrix distinguishes verified, running runtime facilities from proposed, uncommitted software components:

| Component / Facility | Status | Implementation State | Trust & Authority Role |
|---|---|---|---|
| **JSONL Session Transcripts** | **VERIFIED** | Active on disk at `logs/transcript.jsonl` | Append-only execution record of conversational and tool turns. Reports activity only; not proof of verification. |
| **MCP Tool Invocation Protocol** | **VERIFIED** | Active via JSON-RPC / stdio | Agent tool dispatch mechanism. Authorized tools can be exposed to agents via MCP registry. |
| **SQLite WAL Persistence** | **VERIFIED** | Implemented in `mas/pm/db.py` | Embedded persistence layer with WAL mode and `BEGIN IMMEDIATE` transaction locking. |
| **Directed FSM Engine** | **VERIFIED** | Implemented in `mas/pm/fsm.py` | Enforces acyclic workflow state transitions with programmatic guard evaluation. |
| **`mas/pm/adapter.py`** | **PROPOSED** | Planned for SBA-04 | Monotonic event construction, client-side sequence enforcement, outbox buffering. |
| **`scripts/antigravity_bridge.py`** | **PROPOSED** | Planned for SBA-04 | Background daemon monitoring transcript deltas and publishing attributable events. |
| **`projects/registry.json`** | **PROPOSED** | Planned for SBA-02 | Declarative repository project registration manifest. |
| **`pm_events`, `pm_comments`, `pm_changes`** | **PROPOSED** | Planned schema migration | Relational storage for immutable audit log, attributable comments, and monotonic polling feed. |
| **`pm_task_mappings`** | **PROPOSED** | Planned schema migration | Relational mapping decoupling global planning IDs (`SBA-01`) from local deployment issue keys (`SBA-1`). |

---

## 3. Redacted Actual Session Transcript Telemetry

Below is a redacted, verbatim excerpt from the active Antigravity session transcript (`b964d376-4d79-45c8-81a7-5a28e8de5c62/.system_generated/logs/transcript.jsonl`). Sensitive environment variables, internal paths, and token tokens have been redacted per security guidelines:

```jsonl
{"step_index":0,"source":"USER_EXPLICIT","type":"USER_INPUT","status":"DONE","created_at":"2026-10-10T19:26:17Z","content":"<USER_REQUEST>\nrun and open the scrum board\n</USER_REQUEST>\n<ADDITIONAL_METADATA>\nActive Document: [REDACTED_REPO_ROOT]/company/DELIVERY_OWNERSHIP.md\n</ADDITIONAL_METADATA>"}
{"step_index":1,"source":"SYSTEM","type":"CONVERSATION_HISTORY","status":"DONE","created_at":"2026-10-10T19:26:22Z"}
{"step_index":2,"source":"SYSTEM","type":"KNOWLEDGE_ARTIFACTS","status":"DONE","created_at":"2026-10-10T19:26:22Z"}
{"step_index":3,"source":"MODEL","type":"PLANNER_RESPONSE","status":"DONE","created_at":"2026-10-10T19:26:22Z","tool_calls":[{"name":"list_dir","args":{"DirectoryPath":"\"[REDACTED_REPO_ROOT]\"","toolAction":"\"Listing directory\"","toolSummary":"\"List workspace root\""}}]}
{"step_index":4,"source":"MODEL","type":"LIST_DIRECTORY","status":"DONE","created_at":"2026-10-10T19:26:26Z","content":"[DIRECTORY_LISTING_METADATA: 27 subdirectories, 25 files]"}
{"step_index":5,"source":"SYSTEM","type":"CHECKPOINT","status":"DONE","created_at":"2026-10-10T19:26:26Z","content":"# Resuming from a compaction\n[TASK_SUMMARY_RECORDED]"}
{"step_index":6,"source":"MODEL","type":"PLANNER_RESPONSE","status":"DONE","created_at":"2026-10-10T19:26:27Z","tool_calls":[{"name":"view_file","args":{"AbsolutePath":"\"[REDACTED_REPO_ROOT]/package.json\"","StartLine":"1","toolAction":"\"Viewing file\"","toolSummary":"\"View package.json\""}}]}
{"step_index":7,"source":"MODEL","type":"VIEW_FILE","status":"DONE","created_at":"2026-10-10T19:26:32Z","content":"[FILE_CONTENT_TRUNCATED]"}
{"step_index":8,"source":"MODEL","type":"PLANNER_RESPONSE","status":"DONE","created_at":"2026-10-10T19:26:32Z","tool_calls":[{"name":"view_file","args":{"AbsolutePath":"\"[REDACTED_REPO_ROOT]/projects/scrum-board-automation/planning/SBA_01_DECISIONS.md\"","EndLine":"100","StartLine":"1","toolAction":"\"Viewing file\"","toolSummary":"\"View SBA_01_DECISIONS.md\""}}]}
```

### Transcript Structure & Parsing Invariants:
1. **Linear Monotonic Sequencing:** Every entry contains an incremental integer `step_index` scoped to the conversation.
2. **Actor Attribution:** `source` explicitly denotes the producing actor: `USER_EXPLICIT` (human instruction), `MODEL` (agent thoughts and tool calls), or `SYSTEM` (context injection and checkpoints).
3. **Structured Tool Telemetry:** Every tool invocation records tool name, arguments, execution status (`DONE` / `ERROR`), timestamp (`created_at`), and tool return content.

---

## 4. Transcript Trust Model & Operational Constraints

In accordance with Codex Review 2 ([SBA_01_REVIEW_2.md](SBA_01_REVIEW_2.md)), local transcript logs are governed by the following strict operational trust boundaries:

1. **Activity Reporting vs. Empirical Verification:**
   - Transcripts report observed agent activity; they **do not** prove successful execution, test verification, or milestone completion.
   - A watcher reading `transcript.jsonl` may emit `work.started` or `work.progress` events to reflect active development.
   - Milestone transitions (`candidate.submitted`, `evidence.submitted`) require explicit, verifiable external artifacts: Git commit SHAs resolvable in the repository object database and standalone test runner output logs with matching SHA-256 hashes.
   - `DONE` transitions remain strictly gated by the directed FSM and require unanimous approval from authorized separate reviewers (`JUDICIAL_REVIEW`). Watcher logs can never transition an issue to `DONE`.

2. **Session, Task, and Attempt Binding:**
   - Any bridge daemon reading session logs must bind the active `conversation-id` to an explicitly admitted `(tenant_id, project_id, task_id, attempt_id)` tuple provisioned by the coordinator.
   - Unbound conversations or activities referencing unauthorized project keys are discarded and logged as security warnings.

3. **Log Sanitization & Sensitive Data Filtering:**
   - Log text extracted from `transcript.jsonl` is treated as untrusted input.
   - The proposed bridge daemon (`scripts/antigravity_bridge.py` [PROPOSED]) implements strict redaction before transmitting event payloads to MAS-PM:
     - API keys, bearer tokens, passwords, and private key blocks are stripped via regex.
     - Paths outside the admitted `path_whitelist` are blocked.
     - Full conversational transcripts or raw prompt dumps are **never** committed to Git or pushed to public endpoints.

4. **Rotation, Truncation, and Duplicate Handling:**
   - The bridge daemon tracks file identity using `(device_id, inode)` and byte offset.
   - If file size drops below the tracked offset or the inode changes (indicating log rotation or compaction), the bridge detects the discontinuity, emits an operational warning, and resynchronizes state from the latest `CHECKPOINT` entry.
   - Duplicate log parsing is eliminated using deterministic UUID generation based on `(task_id, attempt_id, step_index)`, allowing MAS-PM's idempotent event ingestion to detect and acknowledge replays without mutating state.
