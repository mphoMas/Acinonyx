# Acinonyx Frontier Workstream

**Branch:** `Acinonyx_frontier`  
**Base:** `main` (commit `c5408636`)  
**Maintained by:** MAS Principal Engineering & Evaluation Pods  

---

## Overview

The `Acinonyx_frontier` branch serves as the advanced development track for cutting-edge agentic capabilities, rigorous adversarial verification, and enterprise-grade autonomous workflows within **Project ACINONYX (MAS-Core)**.

---

## Active Frontier Workstreams

### 1. Computer-Use & Desktop OS Automation
* **Two-Tier Execution:** Tier 1 DOM/CDP (Playwright/Chrome) + Tier 2 Native Desktop (X11/Wayland coordinates via `xdotool` / `pyautogui` / `xvfb`).
* **Deterministic Gating:** State dumps, verification matrix runners, and screenshot assertions before release.
* **Reference Artifacts:**
  * [`workspace/computer_use_research/2026-10-07/RESEARCH_REPORT.md`](../../workspace/computer_use_research/2026-10-07/RESEARCH_REPORT.md)
  * [`workspace/computer_use_research/2026-10-07/run_rigorous_verification_matrix.py`](../../workspace/computer_use_research/2026-10-07/run_rigorous_verification_matrix.py)
  * [`workspace/computer_use_research/2026-10-07/run_native_desktop_verification.py`](../../workspace/computer_use_research/2026-10-07/run_native_desktop_verification.py)

### 2. Anti-Sycophancy & Release Policy Engine
* **Adversarial Evaluator Pod:** Automated detection of sycophantic consensus in multi-agent debates.
* **Cryptographic & Integrity Binding:** Verification bundles required for all candidate production promotions.
* **Reference Implementation:** [`mas/release_policy.py`](../../mas/release_policy.py)

### 3. Living AI Research Portal & Anti-Slop Web Engine
* **Aesthetic Guardrails:** Elimination of generic AI-generated monoculture ("AI slop") through strict token-based CSS hierarchies, semantic HTML, and accessibility audits.
* **Neural Copilot & Interactive Readers:** Real-time topology visualization and verified benchmark explorer.
* **Reference Implementation:** [`portal/index.html`](../../portal/index.html), [`templates/anti_slop_web/`](../../templates/anti_slop_web)
