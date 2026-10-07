# COMPUTER-USE INTEGRATION IMPLEMENTATION PLAN
**Target:** MAS-Core (`/home/acinonyx/Desktop/MAS/`)  
**Architecture:** Two-Tier Decoupled Automation Fabric  
**Revision:** v2.0 (Post-PR Review Update)  
**Date:** October 7, 2026  
**Status:** DRAFT / PROPOSED FOR MERGE  

---

## 1. Integration Scope & Boundaries

This implementation plan details the integration of verified browser and native desktop automation into MAS-Core, incorporating the corrections required during the initial PR review:
- **Defined Trust Boundary:** The candidate artifact hash is computed at the source file level, bound to an ephemeral loopback server, and cryptographically reconciled.
- **Passing Baseline Control:** CI verification must validate that a known compliant baseline passes (`RELEASE_PERMITTED`) before asserting defect rejections.
- **Dedicated Virtual Display:** Native desktop operations remain confined to dedicated virtual X11 displays (`Xvfb :99`), acknowledging that Xvfb is a display isolation tool, not a full security sandbox.
- **Zero Production Mutations During Research:** All research and proof-of-concept trials executed in isolated directories (`workspace/computer_use_research/`).

---

## 2. Dependencies & Prerequisites

### 2.1 Already Available & Verified in Environment (Zero Action Required)
- Python 3.14.6 (`/home/acinonyx/anaconda3/bin/python3`)
- Playwright Python 1.63.0 (`/home/acinonyx/Desktop/MAS/bin/packages/playwright`)
- Playwright Headless Chromium Shell (`/home/acinonyx/Desktop/MAS/bin/browsers/chromium_headless_shell-1243`)
- System Google Chrome 154 (`/usr/bin/google-chrome`)
- Node.js v22.14.0 & npm 10.9.2 (`/home/acinonyx/Desktop/MAS/bin/node`)
- Virtual Display Server (`/usr/bin/Xvfb` and `/usr/bin/fluxbox`)
- Image Processing Library (`Pillow` 11.x)
- GUI Framework (`tkinter` verified functional in Python 3.14)
- Deterministic Policy Engine (`mas.release_policy`)

### 2.2 Prerequisites to Address During Implementation
1. **Local Vendoring of axe-core:** Copy `workspace/computer_use_research/2026-10-07/EVIDENCE/axe.min.js` to `mas/tools/vendor/axe.min.js` so accessibility testing does not depend on external CDN egress during air-gapped CI/CD.
2. **Portal Accessibility Remediation:** Repair `#search-trigger-btn` contrast and `.table-wrapper` keyboard focusability in `portal/index.html` to establish a passing production baseline.

---

## 3. Incremental Implementation Roadmap

### Step 1: Vendor axe-core & Create the Verification Harness
- **Path:** `mas/tools/vendor/axe.min.js`
- **New Module:** [`mas/tools/browser_verifier.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/)
- **Core Function:** `verify_candidate_artifact(candidate_dir: Path, policy: PolicySpec) -> PolicyEvaluationResult`
  - **Trust Boundary Enforcement:**
    1. Read all files in `candidate_dir` and compute composite SHA-256 hash `candidate_hash`.
    2. Start an ephemeral loopback server (`http://127.0.0.1:<ephemeral_port>/`) serving `candidate_dir`.
    3. Launch headless Playwright Chromium, navigate to the loopback URL.
    4. Inject local `mas/tools/vendor/axe.min.js` and execute `axe.run()`.
    5. Exercise interactive user journeys (e.g. click `#star-btn`, assert DOM change).
    6. Construct canonical `audit` and `findings_reports` bound to `candidate_hash`.
    7. Invoke `mas.release_policy.evaluate_release_policy()`.
    8. Tear down loopback server and browser.

### Step 2: In-Browser Canvas Interaction Support
- Ensure [`mas/tools/browser_tool.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/browser_tool.py) utilizes `page.mouse.click(x, y)` and `page.mouse.move(x, y)` for HTML5 `<canvas>` elements, avoiding unnecessary redirection to Xvfb desktop tools.

### Step 3: Register Playwright MCP for Exploratory Agent Loops
- Add configuration to `mas/mcp/` to enable autonomous agents to query accessibility trees via `@playwright/mcp`:
  ```json
  {
    "mcpServers": {
      "playwright": {
        "command": "/home/acinonyx/Desktop/MAS/bin/node",
        "args": [
          "/home/acinonyx/Desktop/MAS/bin/node-dist/bin/npx",
          "@playwright/mcp@latest",
          "--allowed-hosts=localhost,127.0.0.1",
          "--allowed-origins=http://localhost:*;http://127.0.0.1:*"
        ]
      }
    }
  }
  ```

### Step 4: Outcome-Verified Desktop Tooling ([`mas/tools/computer_use.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/computer_use.py))
- Document explicitly that `VirtualDisplayManager` provides virtual display separation, not OS security sandboxing.
- Add an integrated test fixture (`tests/test_desktop_effect.py`) that uses the verified Tkinter pattern to assert that synthetic mouse clicks produce measurable state changes.

### Step 5: Update CI Pipeline & Quality Gates ([`scripts/run_quality_gate.sh`](file:///home/acinonyx/Desktop/MAS/scripts/run_quality_gate.sh))
- Add automated verification execution:
  ```bash
  python3 -m unittest tests/test_portal_web.py
  python3 -m unittest tests/test_computer_use_xvfb.py
  python3 -m unittest tests/test_deliberately_broken_candidate.py
  ```

---

## 4. Acceptance Criteria & Definition of Done

A pull request promoting this integration will be accepted only if:
1. **Passing Control Validated:** The baseline control fixture passes all gates with `decision == "RELEASE_PERMITTED"` and zero blocking findings.
2. **Defect Mutations Blocked:** Injected title, contrast, alt text, and broken interaction defects are each independently detected and result in `decision == "RELEASE_BLOCKED"`.
3. **Tamper Rejection:** A modified candidate hash or missing evidence artifact immediately triggers `RELEASE_BLOCKED`.
4. **Outcome-Verified Desktop Test:** Native desktop tests assert resulting application state changes (counter increment and text input), not just attempted action logs.
5. **Hermetic & Air-Gapped:** Zero external network calls during test execution; all scripts and browsers load from local repository paths.

---

## 5. Rollback Strategy

1. **Feature Branch Isolation:** All implementation work proceeds on `feat/two-tier-computer-use`.
2. **Instant Reversion:** Reverting the branch restores previous mock-capable fallbacks without lingering Xvfb subprocesses or display sockets.
