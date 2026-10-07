# COMPUTER-USE RESEARCH REPORT & ADVERSARIAL INTEGRATION EVALUATION
**Target Repository:** Project ACINONYX (`/home/acinonyx/Desktop/MAS/`)  
**Host Machine:** Dell PowerEdge T340 | Linux Kernel `7.0.0-38-generic x86_64`  
**Revision:** v2.0 (Addressing PR Review Findings: Baseline Controls, Outcome Verification, Defined Trust Boundaries)  
**Date:** October 7, 2026  
**Evaluator:** Technical Research Team & Adversarial Evaluator for MAS-Core  
**Status:** PROPOSED & VERIFIED VIA PASSING CONTROLS  

---

## 1. Executive Summary & Recommended Architecture

MAS requires reliable, verifiable automation to:
1. Operate and inspect browser interfaces (such as the [Living Research Portal](file:///home/acinonyx/Desktop/MAS/portal/index.html)).
2. Perform native desktop tasks where non-browser GUI applications or window management are required.
3. Capture cryptographically bound screenshots and execution traces.
4. Test frontend behavior, responsive viewports, and accessibility compliance (WCAG 2.1 AA).
5. Feed independently verified evidence into the deterministic [release-policy evaluator](file:///home/acinonyx/Desktop/MAS/mas/release_policy.py).

### Core Architectural Recommendation: The Two-Tier Decoupled Automation Fabric
We recommend decoupling browser and desktop automation into two distinct execution tiers, with an independent verifier enforcing release gating:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              MAS ORCHESTRATION LAYER                                   │
│            (Strike Pods • Supervisor Agents • Anti-Sycophancy Reviewers)               │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
       ┌───────────────────────────┐                ┌───────────────────────────┐
       │   TIER 1: BROWSER SUITE   │                │   TIER 2: DESKTOP SUITE   │
       │ (Primary: Web Applications│                │ (Secondary: Native OS /   │
       │    & Living Portals)      │                │    Window Management)     │
       ├───────────────────────────┤                ├───────────────────────────┤
       │ • Playwright Python API   │                │ • mas.tools.display       │
       │ • Headless Chromium/Chrome│                │   (Dedicated Xvfb :99)    │
       │ • In-DOM axe-core 4.10.2  │                │ • mas.tools.computer_use  │
       │ • Responsive Viewports    │                │   (xdotool in Xvfb)       │
       │ • In-Browser Canvas Mouse │                │ • fluxbox Window Manager  │
       │ • Direct Console Captures │                │ • Tkinter / GUI Harness   │
       └─────────────┬─────────────┘                └─────────────┬─────────────┘
                     │                                            │
                     └──────────────────────┬─────────────────────┘
                                            ▼
                    ┌───────────────────────────────────────────┐
                    │       INDEPENDENT VERIFICATION GATE       │
                    │         (mas.release_policy Engine)       │
                    ├───────────────────────────────────────────┤
                    │ • Cryptographic Candidate Hash (SHA-256)  │
                    │ • Mandatory Suite Reconciliations         │
                    │ • Automated Defect Classification         │
                    │ • Hard Release Gate: Permitted vs Blocked │
                    └───────────────────────────────────────────┘
```

1. **Tier 1 (Browser Automation — Primary Web Workload): Playwright Python Engine**
   - **Engine:** Playwright Python API (`1.63.0`) driving headless Chromium / Google Chrome (`154.0.8037.97`).
   - **Interactive Agent Option:** Microsoft Playwright MCP (`@playwright/mcp`) for conversational exploratory browsing.
   - **Rationale:** Operates over Chrome DevTools Protocol (CDP), completely bypassing host display server restrictions. Interacts directly via DOM accessibility trees (`browser_snapshot`) and in-browser coordinate mouse input (`page.mouse`), eliminating token-heavy pixel coordinate hallucination.
2. **Tier 2 (Native Desktop Automation — Secondary OS Workload): Dedicated Virtual Display (Xvfb)**
   - **Engine:** [`mas.tools.display.VirtualDisplayManager`](file:///home/acinonyx/Desktop/MAS/mas/tools/display.py) launching a dedicated virtual X11 framebuffer (`:99`) with `fluxbox` and [`mas.tools.computer_use.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/computer_use.py) (`xdotool`).
   - **Crucial Architectural Definition:** Xvfb is a **dedicated virtual display**, NOT a security boundary. It provides display server isolation to prevent visual disruption of the host's Wayland desktop (`:0`). Process, filesystem, and network isolation must be enforced separately (via OS user accounts, containers, or MAS scope jails).
3. **Deterministic Release Gate Integration:**
   - Raw scanner outputs (`axe_scan.json`), browser test logs, and screenshot hashes are emitted by the executor and written to durable storage under `workspace/evidence/`.
   - The verifier computes the SHA-256 hash of the frozen candidate artifact at the source file level, reconciles mandatory execution records, and invokes `mas.release_policy.evaluate_release_policy()`.
   - **Validated via Passing Baseline:** In our verified test matrix, a clean baseline candidate passed cleanly (`RELEASE_PERMITTED`), while four isolated defect mutations (missing title, contrast defect, missing alt, and broken interactive handler) were each blocked (`RELEASE_BLOCKED`) with exact finding IDs.

---

## 2. Phase 1: Environment Audit & Verification Taxonomy

### 2.1 Verification State Definitions
To ensure absolute evidentiary precision, every component is classified using strict operational labels:
- **`INSTALLED`**: Binary, library, or package exists on disk.
- **`LAUNCHED`**: Process spawned and running in memory.
- **`EXERCISED`**: Command, action, or synthetic event dispatched to the process.
- **`OUTCOME-VERIFIED`**: An independent state assertion confirmed the intended functional or visual effect occurred.
- **`UNAVAILABLE`**: Binary missing, service inactive, or hardware incompatible.

### 2.2 Host Telemetry & Hardware Profile
- **Host Model:** Dell PowerEdge T340. `[OUTCOME-VERIFIED]`
- **CPU:** Intel(R) Xeon(R) E-2246G CPU @ 3.60GHz (1 socket, 6 physical cores, 12 logical execution threads). `[OUTCOME-VERIFIED]`
- **Memory (RAM):** 61 GiB total physical memory (~64 GB nominal), 45 GiB free, 8.0 GiB swap (0% swap utilized). `[OUTCOME-VERIFIED]`
- **Storage Subsystem:** `/dev/sda2` 915 GB root filesystem, 59 GB used (7%), 811 GB free space. `[OUTCOME-VERIFIED]`
- **GPU Subsystem (Hardware Reality & Reconciliation):**
  - **PCI Telemetry (`lspci -v -s 01:00.0`):**
    ```
    01:00.0 VGA compatible controller: NVIDIA Corporation GK208B [GeForce GT 710] (rev a1)
    Kernel driver in use: nouveau
    Kernel modules: nvidiafb, nouveau
    ```
  - **Secondary VGA:** Matrox Electronics Systems Ltd. Integrated Matrox G200eW3 Controller (rev 04).
  - **`nvidia-smi` binary:** **Not Found / Inactive**. `[OUTCOME-VERIFIED]`
  - **Reconciliation with "4 GB GPU" Spec:** OEM board partners (e.g., Asus GT710-4H-SL-2GD5 / MSI GT 710 4GD3) manufacture 4 GB DDR3 variants of the GeForce GT 710. However, the GPU is based on the legacy NVIDIA **Kepler** microarchitecture (Compute Capability 3.5). The system is running the open-source `nouveau` driver without proprietary NVIDIA CUDA drivers.
  - **Technical Finding:** Modern deep learning frameworks (PyTorch 2.x, TensorRT, vLLM) require Compute Capability 5.0+ (Maxwell) or higher and proprietary CUDA drivers. **Local execution of multi-billion parameter Vision-Language Models (e.g., Qwen2-VL, CogAgent, ShowUI) is strictly UNAVAILABLE on this host without upgraded hardware and drivers.** Any computer-use vision reasoning must utilize hosted APIs (Gemini, Claude, OpenAI) or lightweight CPU heuristic grounding. `[OUTCOME-VERIFIED]`

### 2.3 Display Server & Session Architecture
- **Host Session:** `XDG_SESSION_TYPE=wayland`, `WAYLAND_DISPLAY=wayland-0`, `DISPLAY=:0`. `[OUTCOME-VERIFIED]`
- **Host Display Injection Test:** Direct execution of `xdotool mousemove 120 80` against `DISPLAY=:0` **failed with exit status 1** due to Wayland client isolation. `[OUTCOME-VERIFIED]`
- **Dedicated Virtual Display:** `/usr/bin/Xvfb` and `/usr/bin/fluxbox` are installed. Spawning an isolated virtual display (`:98`) with `fluxbox` started cleanly (`is_mock=False`). `[OUTCOME-VERIFIED]`

### 2.4 Software Runtimes & Tooling Status
- **Python:** Python `3.14.6` (Anaconda at `/home/acinonyx/anaconda3/bin/python3`). `[OUTCOME-VERIFIED]`
- **Node.js:** Node `v22.14.0`, npm `10.9.2` installed at `/home/acinonyx/Desktop/MAS/bin/node`. `[OUTCOME-VERIFIED]`
- **Installed Browsers:**
  - Google Chrome `154.0.8037.97` (`/usr/bin/google-chrome`). `[OUTCOME-VERIFIED]`
  - Mozilla Firefox `154.0` (`/usr/bin/firefox`). `[OUTCOME-VERIFIED]`
  - Chromium Headless Shell 1243 (`bin/browsers/chromium_headless_shell-1243`). `[OUTCOME-VERIFIED]`
- **Playwright Packages:**
  - Python: `playwright 1.63.0` in Anaconda and `bin/packages`. `[OUTCOME-VERIFIED]`
  - Node: `playwright 1.49.1` and `playwright-core 1.49.1` in `node_modules`. `[INSTALLED]`
  - `@playwright/mcp`: Package schema inspected; interactive stdio session remains proposed for integration. `[INSTALLED]`
- **Docker Subsystem:**
  - Docker binary `27.5.1` is installed. `[INSTALLED]`
  - Docker daemon is **INACTIVE** (`systemctl is-active docker` returns `inactive`, `/var/run/docker.sock` does not exist). Container-based desktop agents (Bytebot) are `[UNAVAILABLE]`. `[OUTCOME-VERIFIED]`

---

## 3. Technology Comparison & Primary-Source Evaluation

| Candidate Technology | Primary Classification | Release / Version & Pinned Date | License | Linux Display Architecture | Model Provider & Inference Location | Input Paradigm | Maintenance Status | Dell T340 Fit |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Playwright Python API** | Browser Automation Library | `1.63.0` (Python) / `1.49.1` (Node) | Apache 2.0 | Native Linux (Headless via CDP, X11, Wayland) | Zero model inference needed (code-driven) | DOM & Accessibility tree + in-browser Canvas mouse | Very Active (Daily commits by Microsoft) | **Tier 1 Recommended** |
| **Microsoft Playwright MCP** (`@playwright/mcp`) | MCP Browser Adapter / Automation Driver | `@playwright/mcp@latest` ([repo](https://github.com/microsoft/playwright-mcp)) | Apache 2.0 | Linux compatible (Node stdio / SSE transport) | Hosted API or local model generates tool calls | Structured Accessibility snapshots (`browser_snapshot`) | Very Active (Official Microsoft repo) | **Tier 1 Recommended** (For agent browsing) |
| **Open Computer Use** (`open-codex-computer-use`) | MCP Native Desktop Automation Adapter | `v0.1.x` ([repo](https://github.com/iFurySt/open-codex-computer-use)) | MIT | Linux supported (falls back to coordinates / xdotool) | Requires external model for coordinate selection | Accessibility on macOS; coordinate clicks on Linux | Active (Community-driven, inspired by Codex) | **Conditional** (If MCP protocol mandated for desktop) |
| **OpenAI Computer Use** (API & Reference Pattern) | Model Decision API & Reference Harness | API Guide ([docs](https://developers.openai.com/api/docs/guides/tools-computer-use)) | Proprietary API / MIT Harness | Host-independent (API emits actions; client executes) | Hosted OpenAI API (GPT-4o, GPT-6 Astra) | Code execution (Playwright) OR discrete `computer` tool | Active (Core OpenAI platform feature) | **Recommended Integration Pattern** |
| **Bytebot** (`bytebot-ai/bytebot`) | Full Desktop Environment & Container Agent | `v0.2.x` ([repo](https://github.com/bytebot-ai/bytebot)) | Apache 2.0 | Linux container (Docker + X11 + noVNC) | Hosted VLM APIs (Claude, OpenAI) | Coordinate & screenshot-based desktop | Active (Fast-growing open-source project) | **Rejected** (Docker daemon inactive; heavy container bloat) |
| **Cua** (`trycua/cua`) | Desktop Automation & VM Infrastructure | `v0.1.x` ([repo](https://github.com/trycua/cua)) | AGPL-3.0 / Commercial | Linux Spaces supported, but Lume VM is macOS-only | Hosted APIs or CUA-S1 specialized models | OS Accessibility tree (Cua Driver) & coordinates | Active (Commercial startup) | **Rejected** (Apple Silicon VM bias; licensing overhead) |
| **Agent-S / S3** (`simular-ai/Agent-S`) | Academic Agent Framework & GUI Benchmark | `gui-agents 0.3.x` ([repo](https://github.com/simular-ai/Agent-S)) | Apache 2.0 | Linux supported (PyAutoGUI, single monitor) | Hosted VLM (Claude 3.5 Sonnet, GPT-5) | Set-of-Marks coordinate grounding | Active (Simular AI, OSWorld 2.0 benchmark leader) | **Rejected for Core** (Research framework; token-heavy) |
| **macOS Agent** (`computer-use-agents.github.io`) | Research Benchmark Project | Academic project ([site](https://computer-use-agents.github.io/macos/)) | Academic | **Incompatible** (macOS Cocoa / AX APIs only) | Multimodal VLM | Native macOS Accessibility APIs | Academic snapshot | **Inapplicable** (macOS only) |

### Analysis of Technical Findings & Nuance

1. **In-Browser Canvas Coordinate Interaction (Correction to Canvas Fallback):**
   - *Initial Assumption:* Web applications rendering inside `<canvas>` elements require falling back to native desktop automation (Xvfb + `xdotool`).
   - *Verified Reality:* **Incorrect.** Playwright provides a native `page.mouse` API supporting coordinate-based mouse movement, clicking, and dragging directly inside the browser viewport. We created an isolated Canvas fixture (`canvas_fixture.html`) and executed `page.mouse.click(box.x + 150, box.y + 100)`. The canvas listener fired, painted a circle, and updated state (`Clicks: 1 (Last at: 150,100)`) without ever touching Xvfb. Visual grounding (Set-of-Marks / VLM) can remain entirely within Playwright.
2. **Workload Distribution Context:**
   - The operational distinction between Tier 1 (Browser) and Tier 2 (Desktop) is an **architectural allocation based on Acinonyx Consulting Group's business focus** (SaaS portals, BigQuery pipelines, web applications), where web testing represents ~90–95% of client deliverables. Reserving Xvfb for non-browser GUI tasks keeps high-frequency web testing fast and lightweight.
3. **Automated Accessibility Testing Scope:**
   - Empirical studies by **Deque Systems** and the **UK Government Digital Service (GDS)** demonstrate that automated accessibility scanners (like `axe-core`) detect **30% to 40%** of total WCAG barriers. Automated scans catch missing alt attributes, color contrast ratios, duplicate IDs, and invalid ARIA roles, but cannot verify cognitive workflow clarity, meaningful screen-reader announcement order, or complex keyboard navigation logic. Scanner passage is a **necessary baseline gate**, not exhaustive compliance.
4. **Latency Measurement Definition:**
   - The reported latency figure of **55.4 ms** specifically measures **navigation load time**: the elapsed time between issuing `page.goto("http://localhost:8080/portal/")` and the browser firing the `load` event over loopback in headless Google Chrome.

---

## 4. Phase 4: Bounded Proof-of-Concept & Verification Matrix

### 4.1 The 8-Case Verification Matrix ([`run_rigorous_verification_matrix.py`](file:///home/acinonyx/Desktop/MAS/workspace/computer_use_research/2026-10-07/run_rigorous_verification_matrix.py))
To establish that the release gatekeeper reliably distinguishes compliant from defective candidates, we executed an 8-case verification matrix against [`mas.release_policy.evaluate_release_policy()`](file:///home/acinonyx/Desktop/MAS/mas/release_policy.py):

| Case ID | Fixture / Scenario | Injected Condition | Expected Evaluation Decision | Actual Evaluation Result | Blocking Finding IDs |
|:---|:---|:---|:---|:---|:---|
| **CASE-01** | `candidate_01_baseline.html` | Clean, fully accessible WCAG AA markup + working star bookmark click listener | `RELEASE_PERMITTED` | **`RELEASE_PERMITTED`** `[OUTCOME-VERIFIED]` | `[]` (Zero blocking findings; 25 passes) |
| **CASE-02** | `candidate_02_defect_title.html` | Empty `<title>` tag | `RELEASE_BLOCKED` | **`RELEASE_BLOCKED`** `[OUTCOME-VERIFIED]` | `['FIND-A11Y-document-title']` |
| **CASE-03** | `candidate_03_defect_contrast.html` | `#star-btn` text #24292e on #238636 (1.4:1 contrast ratio) | `RELEASE_BLOCKED` | **`RELEASE_BLOCKED`** `[OUTCOME-VERIFIED]` | `['FIND-A11Y-color-contrast']` |
| **CASE-04** | `candidate_04_defect_alt.html` | Image lacking `alt` attribute | `RELEASE_BLOCKED` | **`RELEASE_BLOCKED`** `[OUTCOME-VERIFIED]` | `['FIND-A11Y-image-alt']` |
| **CASE-05** | `candidate_05_defect_broken_script.html` | Click listener on `#star-btn` removed; interaction fails | `RELEASE_BLOCKED` | **`RELEASE_BLOCKED`** `[OUTCOME-VERIFIED]` | `['FIND-FUNC-STAR-ACTION']` |
| **CASE-06** | `candidate_01_baseline.html` | Candidate SHA-256 hash tampered in audit payload | `RELEASE_BLOCKED` | **`RELEASE_BLOCKED`** `[OUTCOME-VERIFIED]` | Reason: `Audit candidate_hash mismatch` |
| **CASE-07** | `candidate_01_baseline.html` | Finding references non-existent evidence artifact path | `RELEASE_BLOCKED` | **`RELEASE_BLOCKED`** `[OUTCOME-VERIFIED]` | Reason: `references non-existent evidence artifact` |
| **CASE-08** | `candidate_01_baseline.html` | Audit marked `execution_complete: False` | `RELEASE_BLOCKED` | **`RELEASE_BLOCKED`** `[OUTCOME-VERIFIED]` | Reason: `Verification audit is marked incomplete` |

### 4.2 Outcome-Verified Native Desktop Interaction ([`run_native_desktop_verification.py`](file:///home/acinonyx/Desktop/MAS/workspace/computer_use_research/2026-10-07/run_native_desktop_verification.py))
To satisfy the requirement that native desktop automation must verify resulting application state:
1. Spawned an isolated virtual display `:98` via `VirtualDisplayManager` (`Xvfb` + `fluxbox`).
2. Launched a real Tkinter desktop application ([`sample_desktop_app.py`](file:///home/acinonyx/Desktop/MAS/workspace/computer_use_research/2026-10-07/EVIDENCE/sample_desktop_app.py)) with an initial state of `counter=0` and empty text.
3. Activated window `4194352` via `xdotool`.
4. Dispatched `mouse_move(250, 155)` and `mouse_click(1)` to click the increment button.
   - **Verified State:** App wrote `{"counter": 1, "action": "button_clicked"}` to [`tkinter_app_state.json`](file:///home/acinonyx/Desktop/MAS/workspace/computer_use_research/2026-10-07/EVIDENCE/tkinter_app_state.json).
5. Dispatched `mouse_move(250, 210)` and `mouse_click(1)` into text entry, executed `type_text("Hello MAS")`, and clicked the Submit button at `(250, 260)`.
   - **Verified State:** App wrote `{"text_content": "Hello MAS", "action": "text_submitted"}` to state JSON.
6. Captured a framebuffer screenshot ([`native_tkinter_outcome_verified.png`](file:///home/acinonyx/Desktop/MAS/workspace/computer_use_research/2026-10-07/EVIDENCE/native_tkinter_outcome_verified.png)), proving that synthetic input produced actual application state changes. Status: **`OUTCOME-VERIFIED`**.

### 4.3 Baseline Portal Telemetry (Pre-Existing Violations)
Evaluating the unmutated [Living Research Portal](file:///home/acinonyx/Desktop/MAS/portal/index.html) running at `http://localhost:8080/portal/` revealed that it currently fails WCAG AA on two specific rules:
- `color-contrast`: `#search-trigger-btn > span:nth-child(1)` fails contrast thresholds.
- `scrollable-region-focusable`: `.table-wrapper` elements have scrollable overflow without keyboard focusability.
These pre-existing violations correctly trigger `RELEASE_BLOCKED` when evaluated against `POLICY-PORTAL-STRICT-01`, confirming that the release policy blocks dirty candidates.

---

## 5. Candidate Binding & Defined Trust Boundary

To prevent caller spoofing where an executor tests a compliant site but claims a hash from a defective candidate, the verification trust boundary must follow a deterministic protocol:

```
┌─────────────────────────┐
│ Frozen Source Candidate │
│   (Immutable Directory) │
└────────────┬────────────┘
             │
             ├──▶ [1. Canonical Hash Engine] ──▶ Computes candidate_hash = SHA256(index.html + assets)
             │
             ├──▶ [2. Ephemeral Loopback Server] ──▶ Serves candidate files on http://127.0.0.1:<ephemeral_port>/
             │
             ▼
┌─────────────────────────┐
│ Browser Test Executor   │ ──▶ Fetches loopback URL, asserts HTTP Content-Length & SHA256 match
└────────────┬────────────┘
             │
             ├──▶ [3. Emits axe_scan.json + test_run.json] ──▶ Written to workspace/evidence/<run_id>/
             │
             ▼
┌─────────────────────────┐
│ Independent Verifier    │ ──▶ Reads disk artifacts, reconciles candidate_hash, enforces PolicySpec
└─────────────────────────┘
```

1. **Source Immutability:** The candidate directory is frozen in a clean workspace location before testing begins.
2. **Hash Computation:** The test harness calculates the SHA-256 hash directly from the frozen source files, NOT from a caller argument.
3. **Loopback Serving:** The harness spins up an ephemeral loopback HTTP server bound to `127.0.0.1` serving only that frozen directory.
4. **Reconciliation:** The browser fetches the content from the loopback server, verifies that the delivered bytes match the source hash, and binds `candidate_hash` to the audit log and all findings reports.
5. **Tamper Detection:** If an audit record supplies a hash differing from the evaluated artifact, Gate 1 of `evaluate_release_policy()` rejects the release immediately (`Audit candidate_hash mismatch`).
