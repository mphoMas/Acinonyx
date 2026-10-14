# Antigravity — GHA-04 Design Checkpoint Delivery

**Task:** GHA-04 — Durable Ingestion, Replay Protection & Source-Event Synchronization (Design Checkpoint)  
**Branch:** `feat/scrum-board-automation`  
**Implementation Owner:** Antigravity Development Team  
**Architecture Reviewer:** Codex  
**Date:** 14 October 2026  
**Status:** **SUBMITTED FOR INDEPENDENT CODEX REVIEW**  
**Design Specification:** [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_SPEC.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_SPEC.md)  
**Handoff Brief Reference:** [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_HANDOFF.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_HANDOFF.md)  
**Accepted GHA-03 Baseline:** Commit `82407210f97eb41500f2a4d671d71d38175b685e` (Approved in `3ca8fc4d`)  

---

## 1. Executive Summary

In response to the GHA-04 design handoff directive, Antigravity has developed the complete architectural design specification, additive database schema proposal, and executable acceptance test plan for GHA-04.

In strict compliance with delivery governance rules:
- **Zero implementation code or database migrations have been executed.**
- All proposed models, tables, and services are explicitly documented as **PROPOSED**.
- The design strictly preserves the agreed witness-only scope: witness observations cannot approve deliveries, bypass critic reviews, or trigger unauthorized coordinator side-effects.

---

## 2. Requirement Coverage Summary

| Section | Required Mechanism from Brief | Specification Section in `ANTIGRAVITY_GHA_04_DESIGN_SPEC.md` | Key Architectural Guarantees |
|---|---|---|---|
| **1** | **Identity Separation & Digesting** | § 1.1, § 1.2, § 1.3 | Strict decoupling of Token Identity `(iss, jti)`, Transport Coordinates `(run_id, attempt)`, MAS Execution Identity, and Logical Source-Action Identity. Distinguishes token replay from rerun attempts. Canonical semantic payload hashing and immutable CAS storage. |
| **2** | **Additive Storage Proposal** | § 2.1, § 2.2 | Additive schema migration `2026101401` proposing `pm_security_tokens`, `pm_delivery_receipts`, `pm_source_events`, and `pm_delivery_intents`. Immutability triggers abort direct SQL updates/deletes. Zero impact on legacy tables. |
| **3** | **Atomic Admission Protocol** | § 3.1 | Single `BEGIN IMMEDIATE` database transaction binding fresh IAM tenant status, connector snapshot authority, server-authoritative PR head freshness, token consumption, and receipt generation. |
| **4** | **Authenticated Source Registration** | § 4.1 | Server-authoritative PR head and base tracking via HMAC-SHA256 authenticated webhooks. Out-of-order webhook rejection via generation ordering. Re-check of PR head freshness at subsequent review acceptance. |
| **5** | **Crash Recovery & UNCERTAIN Graph** | § 5.1, § 5.2 | Dropped HTTP responses return cached receipts upon client retry with identical token (HTTP 200). Crash prior to commit rolls back cleanly. Crash during side effects marks intent `UNCERTAIN` and preserves reservations. |
| **6** | **Query Contracts & Quotas** | § 7.1, § 7.2 | Read-only tenant-scoped receipt query service. Strict per-tenant quotas. Bounded archive storage. Witness uploads strictly forbidden from assuming builder or reviewer roles. |
| **7** | **Shared Failure Matrix** | § 6 (Table) | Exhaustive specifications for all 14 required failure/concurrency scenarios with trigger conditions, invariant preservation rules, and expected HTTP codes. |
| **8** | **Executable Test Plan** | § 8 | 20 concrete acceptance test scenarios (TC-01 through TC-20) mapped to system invariants. |

---

## 3. Submission & Review Hand-off

Antigravity requests Codex's independent review of [`ANTIGRAVITY_GHA_04_DESIGN_SPEC.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_SPEC.md). Upon mutual sign-off and review approval, Antigravity will proceed to backend implementation under the agreed boundaries.
