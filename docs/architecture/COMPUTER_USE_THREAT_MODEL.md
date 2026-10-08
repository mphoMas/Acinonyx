# Acinonyx Computer-Use Threat Model & Permission Boundaries

**Author:** `chief_architect`  
**Deliverable for:** `CU-01` (`MAS-13`)  
**Scope:** `docs/`, `mas/tools/`  
**Reviewer:** `security_sre`  
**Status:** Approved & Implemented

---

## 1. System Overview

Acinonyx Computer-Use enables autonomous browser and desktop automation (Playwright Chromium, virtual Xvfb display, and system tool execution) under strict supervision and safety boundaries.

---

## 2. Threat Vectors & Mitigations

### 2.1 Prompt Injection via Web Content
- **Threat:** Malicious web pages displaying adversarial prompt instructions to coerce agent into unintended actions (e.g. data exfiltration, secret leakage).
- **Mitigation:**
  - Strict input sanitization via `mas/security.py:sanitize_tool_arguments`.
  - Execution within isolated headless browser contexts.
  - Deny-by-default network policy outside explicitly targeted test domains.

### 2.2 Host System Compromise & Escapes
- **Threat:** Subprocess execution or browser exploits breaking out into the host OS.
- **Mitigation:**
  - Non-root container execution (`USER mas`, UID `10001`).
  - Read-only container root with ephemeral `/tmp` scratch storage.
  - OS-level sandboxing with strict environment variable stripping.

### 2.3 Secret Leakage & Credential Harvesting
- **Threat:** Automation interacting with forms containing tokens or writing secrets to disk/logs.
- **Mitigation:**
  - Forbidden path regex: `.env`, `.env.*`, `**/secrets/**`.
  - Sensitive token redaction across all MCP tool payloads and audit events.

---

## 3. Permission Boundaries Matrix

| Operation Category | Principal Authorization | Sandbox Level | Logging Requirement |
| :--- | :--- | :--- | :--- |
| **DOM Inspection / Snapshot** | All authenticated agents | Isolated Browser Context | Audit log event |
| **Click / Mouse / Keyboard Input** | `agent_workflow_engineer` | Controlled Xvfb / Playwright | Screenshot evidence |
| **File Downloads / Artifacts** | `qa_critic`, `security_sre` | Whitelisted workspace scratch | SHA-256 hash validation |
| **System Process Execution** | Denied by default | OS container sandbox | Full exit code and stdout capture |

---

## 4. Verification Suite

Validated by:
- `tests/test_computer_use.py` (19 passing test cases)
- `tests/test_executor_security.py`
- `tests/test_visual_diff.py`
