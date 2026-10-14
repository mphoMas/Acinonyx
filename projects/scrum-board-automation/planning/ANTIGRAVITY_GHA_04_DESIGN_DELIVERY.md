# Antigravity — GHA-04 Design Checkpoint Delivery (Revised Checkpoint 2)

**Task:** GHA-04 — Durable Ingestion, Replay Protection & Source-Event Synchronization (Design Checkpoint Rework 2)
**Branch:** `feat/scrum-board-automation`
**Implementation Owner:** Antigravity Development Team
**Architecture Reviewer:** Codex
**Date:** 14 October 2026
**Status:** **SUBMITTED FOR INDEPENDENT CODEX REVIEW** (Design agreement pending)
**Design Specification:** [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_SPEC.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_SPEC.md)
**Review Documents Addressed:**
- [`projects/scrum-board-automation/planning/GHA_04_DESIGN_REVIEW.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_DESIGN_REVIEW.md) (`a193e1af`)
- [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_REWORK_BRIEF.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_REWORK_BRIEF.md) (`a193e1af`)
- [`projects/scrum-board-automation/planning/GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md) (`a629ba4b`)
- [`projects/scrum-board-automation/planning/GHA_04_REVIEW_READINESS_CHECKLIST.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_REVIEW_READINESS_CHECKLIST.md) (`a629ba4b`)
- [`projects/scrum-board-automation/planning/GHA_04_REVISED_DESIGN_REVIEW.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_REVISED_DESIGN_REVIEW.md) (`fe0e9899`)
- [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_REVISED_DESIGN_REWORK.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_REVISED_DESIGN_REWORK.md) (`fe0e9899`)
**Accepted GHA-03 Baseline:** Commit `82407210f97eb41500f2a4d671d71d38175b685e` (Approved in `3ca8fc4d`, Recorded in `GHA_03_ACCEPTANCE_RECORD.md`)

---

## 1. Executive Summary & Review Rework Alignment

In response to Codex's second design review (`GHA_04_REVISED_DESIGN_REVIEW.md`) and action directive (`ANTIGRAVITY_GHA_04_REVISED_DESIGN_REWORK.md`), Antigravity has revised the architectural design specification (`ANTIGRAVITY_GHA_04_DESIGN_SPEC.md`).

All four blocking corrections have been resolved with concrete relational DDL, linearization epochs, lookup decision trees, and filesystem protocols:
1. **Executable Relational Proposal:**
   - Explicit parent unique indexes added on `pm_delivery_projects(tenant_id, project_id)` and `pm_delivery_tasks(tenant_id, project_id, issue_id)`.
   - Complete separation of entities: `pm_delivery_logical_actions` (immutable semantic action digest), `pm_delivery_receipts` (attempt receipt with full 256-bit ID `rec_` + 64 hex characters), and `pm_delivery_observation_records` (individual checks).
   - Separation of expiring anti-replay table (`pm_token_replay_cache`) from permanent receipt token provenance, allowing clean cleanup under `PRAGMA foreign_keys = ON;`.
   - Structured canonical action hashing using deterministic $\text{JSON}_{\text{canonical}}$ serialization.
2. **Cross-Store Authority Linearization & Source Protocol:**
   - Established `pm_tenant_authority_epochs` in `PMDatabase` as the single serialization point for IAM tenant status and connector updates. Mutators and admission synchronize on the identical `BEGIN IMMEDIATE` lock.
   - Durable refresh tickets (`pm_source_refresh_tickets`) with CAS acquisition, lease timeouts, and failed/stalled status.
   - Source generation advances on any change to `head_sha`, `base_sha`, or `state` (`OPEN` $\leftrightarrow$ `CLOSED` / `MERGED`). Ancestry ordering is 100% eliminated. Stalled freshness fails closed (`503 SOURCE_FRESHNESS_UNKNOWN`).
3. **Lookup Decision Protocol & Historical Recovery:**
   - Authenticates caller context first.
   - Evaluates historical receipt lookup (token replay cache or logical action attempt) **before** evaluating current PR head freshness.
   - Legitimate replays after PR head advance or closure return historical cached receipts (`200 OK`, `historical=True`) without re-admission or phase transition.
4. **Local Artifact Durability & CAS Protocol:**
   - Scoped server-owned paths (`/var/mas/pm/cas/<tenant_id>/` and `/var/mas/pm/staging/<tenant_id>/`).
   - Atomic no-replace promotion using POSIX `link(staging_tmp, cas_dest)`. If destination exists, byte-for-byte SHA-256 verification is performed; corrupt destinations raise `CAS_INTEGRITY_VIOLATION`.
   - Quota reservation lifecycle managed in `pm_tenant_artifact_quotas`.
   - Safe orphan cleanup with 24-hour grace window and committed reference recheck.

---

## 2. Review Finding Closure Matrix (Revised Review)

| Review Finding | Issue Identified | Concrete Architectural Correction | Spec Location |
|---|---|---|---|
| **1. DDL does not enforce claimed ownership or token retention** | FKs referenced only `issue_id`; no parent unique indexes; token cleanup broke FKs; logical actions lacked separate record to enforce immutable semantic digest. | Added parent unique indexes `uq_idx_delivery_projects_tenant` and `uq_idx_delivery_tasks_tenant_issue`. Added composite FKs referencing `(tenant_id, project_id, issue_id)`. Created `pm_delivery_logical_actions` table. Separated expiring `pm_token_replay_cache` from permanent receipt token provenance. Replaced truncated ID with full 256-bit `rec_` ID. Used deterministic $\text{JSON}_{\text{canonical}}$ action serialization. | § 2.1, § 2.2, § 3.1, § 3.2 |
| **2. Authority and freshness ordering still lack enforcement** | Separate stores acknowledged but no cross-store linearization mechanism; refresh tickets had no schema/protocol; ancestry ordering contradicted force-push; open/closed transitions omitted generation bump. | Established `pm_tenant_authority_epochs` in `PMDatabase` locked under `BEGIN IMMEDIATE`. Created `pm_source_refresh_tickets` with atomic CAS and lease timeouts. Monotonic generation advances on any change to `head_sha`, `base_sha`, or `state` (`OPEN`/`CLOSED`). Removed ancestry ordering. Stalled freshness fails closed with `503`. | § 4.2, § 4.3 |
| **3. Logical action vs attempt and historical recovery conflict** | Admission validated current source before token/receipt lookup, blocking historical cached responses after PR head advance or closure; new-attempt/new-token contradicted action cache. | Structured lookup decision order: Step 1 Authenticate context $\to$ Step 2 Check token replay cache $\to$ Step 3 Check logical action attempt cache (returns `200 OK`, `historical=True`) $\to$ Step 4 Validate current source freshness only for new admissions. | § 5.1, § 5.2 |
| **4. Artifact durability remains a promise rather than a safe protocol** | Rename overwrote existing files; orphan cleanup raced paused admissions; quota reservation had no lifecycle; chmod did not prove immutability. | Specified server-owned scoped paths. Atomic no-replace promotion via POSIX `link()`; existing file verified by SHA-256 (corrupt raises `CAS_INTEGRITY_VIOLATION`). Quota lifecycle tracked in `pm_tenant_artifact_quotas`. Orphan cleanup enforces 24h grace window and queries committed receipts under read transaction before unlinking. | § 4.1 |

---

## 3. Review Readiness Checklist Compliance

In accordance with [`GHA_04_REVIEW_READINESS_CHECKLIST.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_REVIEW_READINESS_CHECKLIST.md):

- [x] **Revised design addresses B1–B6 in `GHA_04_DESIGN_REVIEW.md` and findings 1–4 in `GHA_04_REVISED_DESIGN_REVIEW.md`:**
  Fully resolved in § 1, § 2.1–2.3, § 3.1–3.2, § 4.1–4.3, § 5.1–5.2, and mapped in the closure matrix above.
- [x] **Witness cannot mutate delivery phase, budgets, dispatch or trusted evidence:**
  Formalized in INV-01, INV-02, and INV-08. Observation records are quarantined (`authority_verified = False`). Phase changes remain exclusive to `DeliveryService.submit`. Zero task mutations occur during witness ingestion.
- [x] **Token/action/attempt/source/MAS identities and relational constraints are explicit:**
  Formalized in § 2.1 and § 3.1. Parent unique indexes added; composite FKs on `(tenant_id, project_id, issue_id)` enforced; separate `pm_delivery_logical_actions` and `pm_delivery_receipts` tables defined.
- [x] **Same/fresh/expired-token retry and historical receipt retrieval outcomes are unambiguous:**
  Formalized in § 5.1 (lookup decision table) and § 5.2 (`DeliveryReceiptService` query contract). Historical lookups execute *before* source freshness checks, allowing retrieval after PR head advances or closes.
- [x] **Source freshness protocol handles force push, base changes and delayed responses:**
  Formalized in § 4.3 and § 3.1. Durable refresh tickets with CAS; generation increments on any change to head, base, or open/closed state; ancestry ordering 100% eliminated; fails closed with `503` on stale refresh.
- [x] **Authorization linearization covers IAM and connector update boundaries:**
  Formalized in § 4.2. Cross-store mutators update `pm_tenant_authority_epochs` under `BEGIN IMMEDIATE` lock in `PMDatabase`, establishing a single, provable linearization point.
- [x] **Artifact durability/quota/orphan cleanup and local rollback versus remote uncertainty are distinguished:**
  Formalized in § 4.1. Server-owned paths; POSIX `link()` atomic no-replace promotion; byte verification on collision; quota reservation lifecycle; orphan cleanup with 24h grace window and committed reference recheck.
- [x] **Immutable history, mutable projections, retention and migration compatibility are specified:**
  Formalized in § 3.1, § 3.2, and § 9. `pm_delivery_receipts`, `pm_delivery_observation_records`, `pm_delivery_logical_actions`, and `pm_source_notifications` have abort triggers. `pm_source_current_heads` is a mutable projection. Additive migration `2026101401`.
- [x] **Shared scenarios in `GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md` are mapped to proposed mechanisms before coding:**
  All 33 scenarios (A01–A07, R01–R09, S01–S06, C01–C06, D01–D05) mapped with all 5 required dimensions in § 8.
- [ ] **Codex design agreement recorded before implementation/schema changes:**
  **Status: PENDING CODEX REVIEW.** Strict gate preserved; zero implementation code written.

---

## 4. Shared Acceptance Scenario Mapping Summary (33 Scenarios)

The revised specification (§ 8) maps every shared scenario from [`GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md) with all five required dimensions (Invariant Checked, Component & Boundary, Input/Fault, Response & State, Evidence Needed):

1. **Admission and Authority (A01 – A07):**
   - **A01 (Valid observation):** Records untrusted observation; leaves delivery phase and budgets unchanged.
   - **A02 (Authority boundary):** Rejects builder fields; preserves `authority_verified = False`.
   - **A03 (Cross-tenant separation):** Composite FK on `(tenant_id, project_id, issue_id)` blocks foreign tenant insertion.
   - **A04 (Multi-check per run):** Composite receipt key allows distinct checks/tasks in same workflow run attempt.
   - **A05 (Revision change):** Changed generation/suite creates new `action_key`; rejects conflicting rerun.
   - **A06 (Authority race):** Double-checked lock verifies `pm_tenant_authority_epochs` immediately before commit.
   - **A07 (Binding mismatch):** Coordinates matching token claims enforced before transaction.
2. **Replay, Idempotency, and Retrieval (R01 – R09):**
   - **R01 (Concurrent same-token):** Serialized `BEGIN IMMEDIATE` commits one row; second request returns `200 OK (Cached)`.
   - **R02 (Fresh-token retry):** Resolves existing receipt without consuming token; zero duplicate execution.
   - **R03 (Altered payload conflict):** Semantic digest mismatch returns `409 CONFLICTING_ACTION_PAYLOAD`.
   - **R04 (Formatting invariance):** Canonical JSON serialization prevents false conflicts on dictionary ordering.
   - **R05 (Workflow rerun):** Distinct `github_run_attempt` creates separate observation receipt.
   - **R06 (Expired token recovery):** Authenticated historical query recovers receipt after token expiry.
   - **R07 (Historical read on advanced PR):** Returns past receipt with explicit `is_current_head = False`, `historical = True`.
   - **R08 (Tenant isolation on query):** Tenant context derived from authentication; foreign receipt query returns 404.
   - **R09 (Token purge vs immutable receipt):** Ephemeral replay cache cleaned safely without breaking foreign keys.
3. **Source Currentness and Ordering (S01 – S06):**
   - **S01 (Delayed notification):** Out-of-order notification logged without regressing current head.
   - **S02 (Force-push / rebase):** Authoritative refresh ticket increments `source_generation`, invalidating stale commits.
   - **S03 (Base change / closed PR):** Mismatched candidate SHA returns 409; closed PR returns 409.
   - **S04 (Webhook authenticity):** HMAC-SHA256 signature verified before processing; delivery ID logged.
   - **S05 (GitHub outage / stale window):** Stale refresh window fails closed with `503 SOURCE_FRESHNESS_UNKNOWN`.
   - **S06 (Concurrent source updates):** Serialized refresh tickets prevent split-brain or duplicate current rows.
4. **Artifact and Crash Durability (C01 – C06):**
   - **C01 (Crash recovery lifecycle):** Two-phase promotion ensures atomic promotion; orphan temp files reaped safely.
   - **C02 (Storage failure / disk full):** Unlinks staging file; rolls back 100% of SQLite rows; returns `500 INTERNAL_ERROR`.
   - **C03 (CAS integrity & collision):** POSIX `link()` atomic no-replace; verified existing bytes; corrupt file raises 500.
   - **C04 (Caps & quota enforcement):** Enforces 12MB/2MB/10MB limits; quota overflow returns `413 QUOTA_EXCEEDED`.
   - **C05 (Clean restart & WAL recovery):** SQLite WAL guarantees zero phantom rows and zero lost committed receipts.
   - **C06 (External side-effect separation):** Outbox/intents journal excluded from local ingestion slice (deferred).
5. **Schema, Evidence, and Operability (D01 – D05):**
   - **D01 (Additive migration):** Migration `2026101401` runs atomically under ledger check with parent unique indexes.
   - **D02 (Schema integrity check):** Startup executes `PRAGMA foreign_key_check` and `PRAGMA integrity_check`.
   - **D03 (Immutable triggers):** Triggers prevent `UPDATE` or `DELETE` on receipts, observations, and actions.
   - **D04 (Error redaction):** Static category diagnostics prevent sentinel or secret leakage in responses and logs.
   - **D05 (Isolated wheel verification):** Test suite passes against wheel installed outside repository checkout.

---

## 5. Explicit Exclusions & Unresolved Decisions

### 5.1. Explicit Exclusions from Milestone Scope
In accordance with bounded delivery gates, the following capabilities are explicitly excluded from this milestone:
1. **No Delivery Phase Mutation:** Witness observations do not approve work, transition task phases to `IN_REVIEW`/`ACCEPTED`, or create builder delivery submissions. Delivery tasks remain in their pre-existing phases.
2. **No External Side-Effect Coordination:** Distributed outbox journals (`pm_delivery_intents`), asynchronous PR commenting, external webhook relays, and coordinator dispatch are excluded from this local witness ingestion slice.
3. **No Live Workflow Execution / Provider Dispatch:** Witness ingestion only admits completed, authenticated runs; it does not trigger GitHub workflow runs or dispatch external agents.
4. **No Production Credentials or Repository Enrollment:** All testing and verification remain confined to disposable databases, mock filesystems, and signed JWT test fixtures without production credentials.

### 5.2. Unresolved Decisions & Open Questions for Codex
1. **Historical Artifact Retention Horizon:**
   The proposed design permanently retains historical observation receipts while reaping unreferenced staging blobs after 24 hours. Does Codex prefer retaining referenced CAS artifacts indefinitely (governed strictly by tenant quota), or should a tenant-configurable retention horizon (e.g., 90 days) be introduced for raw zip archives?
2. **Synchronous Fallback on Stale Source Refresh:**
   The proposed freshness protocol fails closed with `503 SOURCE_FRESHNESS_UNKNOWN` if the local projection is older than `MAX_FRESHNESS_TTL` (15 minutes). Does Codex recommend attempting a synchronous GitHub API pull during pre-flight if the window is expired, or strictly enforcing fail-closed behavior to prevent webhook queue blocking?

---

## 6. Review Hand-off Request

Antigravity formally marks this delivery **SUBMITTED FOR INDEPENDENT CODEX REVIEW** and requests Codex's architecture agreement on [`ANTIGRAVITY_GHA_04_DESIGN_SPEC.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_SPEC.md).

All implementation code, database migrations, and live endpoints remain strictly gated pending Codex's formal sign-off.
