# FinOps Governance: Observability, Token Budgets & Circuit-Breaker Alerts

**Author:** `finops_governor`  
**Deliverable for:** `OPS-02` (`MAS-22`)  
**Scope:** `mas/observability.py`, `mas/pm/`, `docs/`  
**Reviewer:** `platform_sre`  
**Status:** Approved & Implemented

---

## 1. FinOps Token Budgeting Architecture

To protect enterprise resources and prevent unbounded LLM costs during autonomous multi-agent execution, MAS-PM implements strict hierarchical quotas:

1. **Project Budget Ceiling:** Defined at project creation via `max_budget_tokens` (e.g. 5,000,000 tokens).
2. **Per-Issue Appetite Quota:** Defined during task refinement (`appetite_tokens`, default 50,000 tokens).
3. **Task Timeout Boundary:** Defined during task refinement (`appetite_timeout_s`, default 1800s).

---

## 2. Circuit-Breaker Enforcement (`mas/pm/guards.py`)

- **Reflexion Limit:** An issue is capped at a maximum of 3 repair/reflexion iterations (`reflexion_attempts < 3`). Reaching attempt 3 trips `CircuitBreakerTrippedError` immediately.
- **Expenditure Limit:** If accumulated `tokens_spent >= appetite_tokens`, execution is halted immediately.

---

## 3. Observability & Telemetry

- Point-in-time state tracking via Cumulative Flow Diagrams (`CFDSnapshot`).
- Cycle time metrics: Lead Time, Cycle Time, and Flow Efficiency computed from immutable transition logs.
- Real-time Prometheus/OpenTelemetry metric hooks for active agent concurrency and queue latency.
