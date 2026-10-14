# Antigravity — GHA-04 Design Checkpoint Delivery (Revised)

**Task:** GHA-04 — Durable Ingestion, Replay Protection & Source-Event Synchronization (Design Checkpoint Rework)  
**Branch:** `feat/scrum-board-automation`  
**Implementation Owner:** Antigravity Development Team  
**Architecture Reviewer:** Codex  
**Date:** 14 October 2026  
**Status:** **SUBMITTED FOR INDEPENDENT CODEX REVIEW**  
**Design Specification:** [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_SPEC.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_SPEC.md)  
**Review Documents Addressed:**
- [`projects/scrum-board-automation/planning/GHA_04_DESIGN_REVIEW.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_DESIGN_REVIEW.md) (`6099b8ae`)
- [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_REWORK_BRIEF.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_04_DESIGN_REWORK_BRIEF.md) (`a193e1af`)
- [`projects/scrum-board-automation/planning/GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md) (`a629ba4b`)
- [`projects/scrum-board-automation/planning/GHA_04_REVIEW_READINESS_CHECKLIST.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_REVIEW_READINESS_CHECKLIST.md) (`a629ba4b`)
**Accepted GHA-03 Baseline:** Commit `82407210f97eb41500f2a4d671d71d38175b685e` (Approved in `3ca8fc4d`, Recorded in `GHA_03_ACCEPTANCE_RECORD.md`)

---

## 1. Executive Summary & Review Response

Antigravity has revised the GHA-04 architectural design specification in direct response to Codex's design review (`GHA_04_DESIGN_REVIEW.md`), explicit rework instructions (`ANTIGRAVITY_GHA_04_DESIGN_REWORK_BRIEF.md`), and shared acceptance scenarios (`GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md`).

All six critical review findings (B1 through B6) have been resolved within a bounded, mathematically consistent, and operationally realistic architecture:
1. **Quarantined Witness Authority:** Witness ingestion functions strictly as an untrusted, unverified observation recorder (`admission_status = 'ADMITTED_OBSERVATION'`, `authority_verified = False`). Direct SQL updates to `pm_delivery_tasks.phase`, submissions, verdicts, and budgets are completely eliminated (§ 1, § 2.2, § 3.1).
2. **Composite Identity & Idempotency Keying:** Defined generation-specific `action_key` incorporating source generation and suite digest. Scoped receipts to `(tenant_id, issue_id, action_key, github_run_id, github_run_attempt)`, natively supporting multiple checks per workflow run while enforcing strict composite foreign key integrity on `(tenant_id, project_id, issue_id)` (§ 2.1, § 3.1).
3. **Tripartite Retry & Retrieval Protocol:** Deterministic three-way resolution ensures:
   - Same token, same payload: `200 OK` (cached receipt).
   - Same token, altered payload: `409 IDEMPOTENCY_CONFLICT`.
   - Fresh token, same action: `200 OK` (cached receipt, token unconsumed).
   - Fresh token, altered payload: `409 CONFLICTING_ACTION_PAYLOAD`.
   - Read-only historical receipt query: permits authenticated inspection of past receipts without re-admission, token replay, or current-head claims (§ 5.1, § 5.2).
4. **Authoritative Source Freshness:** Single-row CAS projection (`pm_source_current_heads`) coupled with append-only notification logs (`pm_source_notifications`). Monotonic `source_generation` advances on authenticated refresh tickets, cleanly decoupling authority from git commit ancestry/timestamps during force pushes or rebases, and failing closed (`503 SOURCE_FRESHNESS_UNKNOWN`) on network degradation (§ 3.1, § 4.3).
5. **Authority Linearization Across Independent Stores:** Two-phase filesystem staging (quota check, temp file write, fsync, atomic rename promotion, dir fsync) precedes database locking. Followed by `BEGIN IMMEDIATE` lock with double-checked verification of IAM tenant active status, connector snapshot generation/digest, and PR head generation before commit (§ 4.1, § 4.2).
6. **Clean Local Durability & Retention:** Eliminated the redundant external side-effect journal (`pm_delivery_intents`) from this local slice. Local transaction rollback leaves zero committed rows; token retention is bounded by `expires_at + clock_skew`; receipts and observation records are permanently immutable (§ 1, § 2.2, § 3.1).

**Strict Governance Guarantees:**
- **Zero implementation code, database migrations, or live endpoints have been created.**
- All proposed models, interfaces, and schemas are explicitly labeled as **PROPOSED**.
- GHA-04 implementation remains strictly gated pending Codex design agreement.

---

## 2. Review Finding Closure Matrix (B1–B6)

| Review Finding | Issue Identified in Review | Architectural Correction in Revised Design | Location in Revised Spec |
|---|---|---|---|
| **B1: Witness ingestion takes builder submission authority** | Proposed design directly updated `pm_delivery_tasks.phase` to `IN_REVIEW`/`READINESS_RETURNED` on witness observation outcome, bypassing `DeliveryService.submit`. | Direct phase mutation removed. Ingestion strictly quarantines untrusted observations and receipts (`admission_status = 'ADMITTED_OBSERVATION'`). Delivery tasks remain in existing phases. Submissions must occur via separate authenticated builder services (`DeliveryService.submit`). | § 1, § 2.2 (INV-01), § 3.1 |
| **B2: Identity/idempotency schema cannot express contract** | Omitted generation from logical identity, lacked action digest, prohibited multiple checks per GitHub run, omitted composite ownership constraints. | Defined generation-specific `action_key` and `semantic_action_digest`. Scoped receipts to permit multiple checks per run `(tenant_id, issue_id, action_key, github_run_id, github_run_attempt)`. Added composite foreign keys on `(tenant_id, project_id, issue_id)`. Scoped token replay to `(tenant_id, iss, jti)`. | § 2.1, § 3.1 |
| **B3: Contradictory retry semantics & lost recovery after expiry** | Claimed tokens single-use but permitted replays; fresh-token retries returned 409; cached lookups blocked if head advanced; expired tokens unrecoverable. | Formalized tripartite retry protocol: at-most-once mutation per token; same-token identical replay returns historical receipt (`200 OK`); fresh-token identical action returns existing receipt (`200 OK`); conflicting payloads return `409`; authenticated read query allows inspecting historical receipts even after token expiration or head advancement. | § 5.1, § 5.2 |
| **B4: Non-authoritative freshness ordering** | Relied on ambiguous commit ancestry / timestamps; lacked force-push / base update handling; permitted multiple current rows. | Established append-only notification history (`pm_source_notifications`) and single-row current projection (`pm_source_current_heads`). Monotonic `source_generation` advances on accepted refresh tickets. Force-pushes increment generation and invalidate prior submissions. Fails closed on unknown freshness. | § 3.1, § 4.3 |
| **B5: SQLite lock does not serialize IAM/connector/filesystem** | `BEGIN IMMEDIATE` cannot lock independent IAM DB, connector registry, or filesystem; staging inside lock causes lock contention; chmod 0440 is not immutability. | Out-of-transaction filesystem staging: verify caps (12MB comp, 2MB/member, 10MB uncomp), fsync temp file, atomic promotion via rename, fsync directory. Followed by `BEGIN IMMEDIATE` lock with double-checked verification of IAM active status, connector generation, and PR head generation before commit. | § 4.1, § 4.2 |
| **B6: Contradictory recovery & retention records** | Side-effect journal contradicted local rollback; token deletion conflicted with audit immutability triggers. | Eliminated redundant `pm_delivery_intents` journal from this local slice. Rollback leaves zero rows. Response loss handled by action/token store. Token purge permitted only after `expires_at + clock_skew`; receipts and audit records strictly immutable with abort triggers. | § 1, § 2.2 (INV-10), § 3.1 |

---

## 3. Review Readiness Checklist Compliance

In accordance with [`GHA_04_REVIEW_READINESS_CHECKLIST.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_REVIEW_READINESS_CHECKLIST.md), each checklist item is verified below:

- [x] **Revised design addresses B1–B6 in `GHA_04_DESIGN_REVIEW.md`:**  
  Fully resolved in § 1, § 2.1, § 2.2, § 3.1, § 4.1–4.3, § 5.1–5.2, and mapped in the closure matrix above.
- [x] **Witness cannot mutate delivery phase, budgets, dispatch or trusted evidence:**  
  Formalized in INV-01, INV-02, and INV-08. Observation records are quarantined (`authority_verified = False`). Phase changes remain exclusive to `DeliveryService.submit`. Zero task mutations occur during witness ingestion.
- [x] **Token/action/attempt/source/MAS identities and relational constraints are explicit:**  
  Formalized in § 2.1 and § 3.1. Token identity is `(tenant_id, iss, jti)`. Logical action identity is `action_key`. Execution attempt is `github_run_attempt`. Source state is tracked via `(tenant_id, project_id, pr_number)` with monotonic `source_generation`. Composite FKs enforce cross-tenant separation on `(tenant_id, project_id, issue_id)`.
- [x] **Same/fresh/expired-token retry and historical receipt retrieval outcomes are unambiguous:**  
  Formalized in § 5.1 (tripartite retry resolution table) and § 5.2 (`DeliveryReceiptService` query contract). Same-token retry returns `200 OK (CACHED_RECEIPT)`; fresh-token retry returns `200 OK (CACHED_RECEIPT)`; expired tokens can be queried read-only with `is_current_head` flag.
- [x] **Source freshness protocol handles force push, base changes and delayed responses:**  
  Formalized in § 4.3 and § 3.1. Single-row projection `pm_source_current_heads` increments `source_generation` on refresh tickets. Force pushes advance generation and invalidate prior submissions without relying on commit graph ancestry. Degraded/stale refresh windows fail closed with `503 SOURCE_FRESHNESS_UNKNOWN`.
- [x] **Authorization linearization covers IAM and connector update boundaries:**  
  Formalized in § 4.2. Pre-flight reads connector generation snapshot $G_{conn}$. Double-checked locking under `BEGIN IMMEDIATE` re-validates `iam.get_tenant()` is active and connector generation equals $G_{conn}$ immediately prior to commit.
- [x] **Artifact durability/quota/orphan cleanup and local rollback versus remote uncertainty are distinguished:**  
  Formalized in § 4.1. Staging occurs outside transaction; promotion via atomic rename and directory fsync; DB commit follows. Local transaction aborts roll back 100% of rows (no uncertain state for local writes). Unreferenced CAS artifacts are reaped after 24 hours.
- [x] **Immutable history, mutable projections, retention and migration compatibility are specified:**  
  Formalized in § 3.1, § 3.2, and § 9. `pm_delivery_receipts`, `pm_delivery_observation_records`, and `pm_source_notifications` are append-only with SQLite `ABORT` triggers. `pm_source_current_heads` is a mutable projection without delete triggers. Migration `2026101401` is additive and idempotent.
- [x] **Shared scenarios in `GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md` are mapped to proposed mechanisms before coding:**  
  All 33 scenarios (A01–A07, R01–R09, S01–S06, C01–C06, D01–D05) are explicitly mapped in § 8.
- [x] **Codex design agreement recorded before implementation/schema changes:**  
  Strictly observed. Implementation is 100% gated on Codex's written approval of this revised design specification.

---

## 4. Shared Acceptance Scenario Mapping Summary (33 Scenarios)

The revised specification (§ 8) maps every shared scenario from [`GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_04_INDEPENDENT_ACCEPTANCE_SCENARIOS.md) to an accountable component, database constraint, and verified outcome:

1. **Admission and Authority (A01 – A07):**
   - **A01 (Valid observation):** Records untrusted observation; leaves delivery phase and budgets unchanged.
   - **A02 (Authority boundary):** Rejects builder fields; preserves `authority_verified = False`.
   - **A03 (Cross-tenant separation):** Composite FK on `(tenant_id, project_id, issue_id)` blocks foreign tenant insertion.
   - **A04 (Multi-check per run):** Composite receipt key allows distinct checks/tasks in same workflow run attempt.
   - **A05 (Revision change):** Changed generation/suite creates new `action_key`; rejects conflicting rerun.
   - **A06 (Authority race):** Double-checked lock verifies IAM and connector generation immediately before commit.
   - **A07 (Binding mismatch):** Coordinates matching token claims enforced before transaction.
2. **Replay, Idempotency, and Retrieval (R01 – R09):**
   - **R01 (Concurrent same-token):** Serialized `BEGIN IMMEDIATE` commits one row; second request returns `200 OK (Cached)`.
   - **R02 (Fresh-token retry):** Resolves existing receipt without consuming token; zero duplicate execution.
   - **R03 (Altered payload conflict):** Semantic digest mismatch returns `409 CONFLICTING_ACTION_PAYLOAD`.
   - **R04 (Formatting invariance):** Canonical JSON serialization prevents false conflicts on dictionary ordering.
   - **R05 (Workflow rerun):** Distinct `github_run_attempt` creates separate observation receipt.
   - **R06 (Expired token recovery):** Authenticated historical query recovers receipt after token expiry.
   - **R07 (Historical read on advanced PR):** Returns past receipt with explicit `is_current_head = False`.
   - **R08 (Tenant isolation on query):** Tenant context derived from authentication; foreign receipt query returns 404.
   - **R09 (Token purge vs immutable receipt):** Token purged only after `expires_at + skew`; receipts permanently retained.
3. **Source Currentness and Ordering (S01 – S06):**
   - **S01 (Delayed notification):** Out-of-order notification logged without regressing current head.
   - **S02 (Force-push / rebase):** Authoritative refresh ticket increments `source_generation`, invalidating stale commits.
   - **S03 (Base change / closed PR):** Mismatched candidate SHA returns 409; closed PR returns 409.
   - **S04 (Webhook authenticity):** HMAC-SHA256 signature verified before processing; delivery ID logged.
   - **S05 (GitHub outage / stale window):** Stale refresh window fails closed with `503 SOURCE_FRESHNESS_UNKNOWN`.
   - **S06 (Concurrent source updates):** Serialized projection updates prevent split-brain or duplicate current rows.
4. **Artifact and Crash Durability (C01 – C06):**
   - **C01 (Crash recovery lifecycle):** Two-phase promotion ensures atomic promotion; orphan temp files reaped safely.
   - **C02 (Storage failure / disk full):** Unlinks staging file; rolls back 100% of SQLite rows; returns `500 INTERNAL_ERROR`.
   - **C03 (CAS integrity & collision):** Verifies byte SHA-256 before promotion; rejects symlinks and corrupt overwrite.
   - **C04 (Caps & quota enforcement):** Enforces 12MB/2MB/10MB limits; quota overflow returns `413 QUOTA_EXCEEDED`.
   - **C05 (Clean restart & WAL recovery):** SQLite WAL guarantees zero phantom rows and zero lost committed receipts.
   - **C06 (External side-effect separation):** Outbox/intents journal excluded from local ingestion slice.
5. **Schema, Evidence, and Operability (D01 – D05):**
   - **D01 (Additive migration):** Migration `2026101401` runs atomically under ledger check without data corruption.
   - **D02 (Schema integrity check):** Startup executes `PRAGMA foreign_key_check` and `PRAGMA integrity_check`.
   - **D03 (Immutable triggers):** Triggers prevent `UPDATE` or `DELETE` on receipts and audit logs.
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
