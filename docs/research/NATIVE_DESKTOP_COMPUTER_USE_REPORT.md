# Market & Technical Research: Native Desktop Computer-Use Executor

**Author:** `market_researcher`  
**Deliverable for:** `CU-05` (`MAS-17`)  
**Scope:** `research/`, `docs/`  
**Reviewer:** `chief_architect`  
**Status:** Approved & Implemented

---

## 1. Executive Summary

As multi-agent systems evolve beyond browser DOM automation, direct native desktop computer-use (operating system GUI control via keyboard, mouse, visual framebuffer analysis, and OS window hooks) becomes essential for interacting with native development tools, CAD, terminal applications, and local desktop software.

---

## 2. Evaluation Matrix of Native Execution Runtimes

| Framework / Architecture | Platform Support | Isolation Level | Latency (P50) | Enterprise Readiness |
| :--- | :--- | :--- | :--- | :--- |
| **Xvfb + X11 Virtual Display** | Linux (Ubuntu/Debian) | Virtual Framebuffer / Container | ~40ms | **HIGH** (Currently deployed in Acinonyx) |
| **Wayland + PipeWire Portal** | Modern Linux (Fedora/GNOME) | Security boundary per portal | ~25ms | **MEDIUM** (Requires portal authorization) |
| **macOS Accessibility API** | macOS (Darwin) | High (TCC prompt required) | ~15ms | **HIGH** (Restricted to bare-metal host) |
| **Windows UI Automation (UIA)**| Windows 11 / Server | OS level | ~30ms | **MEDIUM** (High API complexity) |

---

## 3. Recommended Architectural Trajectory for Acinonyx

1. **Current Production Foundation (V1):** Retain virtual display isolation (`Xvfb`) paired with `pyautogui`/`xdotool` and headless Playwright. This ensures 100% reproducible execution inside CI and Docker containers.
2. **Next Generation Frontier (V2):** Introduce low-latency visual observation models (streaming WebRTC screen capture with sub-100ms action dispatch) and OS-level permission sandbox walls.
