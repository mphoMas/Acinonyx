# Platinum Lodge: Backend Discovery, Architecture Assessment & Contract Proposal

**Author:** Antigravity Development Team  
**Date:** 9 October 2026  
**Status:** Discovery Complete; Proposed Foundations Package Staged for Review  
**Context:** Release 1 — Production Multi-Property Hotel Management System  
**Related Allocations:** PLG-BOARD-01, PLG-BE-01, PLG-FE-01, PLG-CONTRACT-01  

---

## 1. Ownership & Authority Formal Acknowledgement

The Antigravity development team formally acknowledges the Delivery Ownership Agreement ([company/DELIVERY_OWNERSHIP.md](file:///home/acinonyx/Desktop/MAS/company/DELIVERY_OWNERSHIP.md)) and its operating boundaries:

1. **Frontend Ownership:** Codex owns frontend implementation, UX/UI, navigation, responsive layouts, design systems, visual identity, typography, imagery, and art direction.
2. **Backend & Engineering Ownership:** The Antigravity development team owns backend architecture, domain logic, APIs, persistence/data migrations, tenancy enforcement, concurrency safety, financial journal, payment integrations, infrastructure, CI/CD, and operational observability/recovery.
3. **Supervised Coding Swarm Boundary:** The supervised coding swarm (`mas-swarm`) is a distinct, strictly bounded Python `solve(payload)` workflow. It has no general application engineering, deployment, or hotel administrative authority.
4. **Shared Contracts:** Shared API and data contracts require joint agreement between Codex and Antigravity, with exactly one accountable delivery/integration owner per task.
5. **Release & Credential Authority:** Ownership does not grant runtime credentials, production administrator permissions, or self-release authority. All gate transitions (G0–G6) require independent review and project owner authorization.

### Execution Principal & Authenticated Identity
- **Local Runtime Principal:** The authenticated environment user is `acinonyx` (UID 1000, `ANTIGRAVITY_AGENT=1`).
- **Proposed Template Role:** The role `backend_engineer` in `work_queue/tasks.json` is an unverified planning role; Antigravity operates under its actual authenticated identity and does not impersonate `backend_engineer`, `admin`, or any independent reviewer (`qa_critic`, `chief_architect`).
- **Review Requirement:** PLG-BOARD-01 is submitted for independent review by `qa_critic`. No task is self-certified or transitioned to `DONE` via scripts.

---

## 2. Multi-Property Tenancy & Security Boundaries

### Findings on Baseline Prototype
The prototype (`feat/platinum-lodge-management`) assumes a single property with global room numbers, monolithic session cookies, and flat SQLite storage.

### Target Architecture & Invariants
1. **Hierarchical Multi-Tenancy:**
   - Hierarchy: `Organization` (Legal entity / Portfolio) → `Property` (Physical hotel / Currency / Timezone / Business Date) → `Inventory / Stays / Folios`.
   - All database tables, foreign keys, and indexes must partition by `organization_id` and `property_id`.
2. **Server-Enforced Access Control:**
   - Client-provided headers (`X-Property-ID`) represent *context intent*, never authority.
   - The server resolves the authenticated user session, checks explicit membership in the requested `(organization_id, property_id)`, and verifies granular capabilities (e.g., `folio:read`, `payment:capture`, `room:inspect`).
   - Group managers receive explicit multi-property portfolio view capabilities; cross-property write operations are strictly forbidden without property-specific delegation.
3. **Adversarial Tenant Isolation Testing (Target M05):**
   - Negative authorization fixtures must include at least two independent organizations, each with at least two properties.
   - Automated tests will verify that URL tampering, guessed UUIDs, IDOR attempts, and cross-tenant exports fail closed with 403 Forbidden and audit alarms.

---

## 3. Concurrent Inventory Correctness & Overbooking Prevention

### Findings on Baseline Prototype
The prototype performs read-then-write checks in memory/SQLite without transactional row locks or optimistic version checks. Concurrent reservation requests for the same room category can produce double allocations.

### Target Architecture & Invariants (Target M06)
1. **Transactional Invariant:**
   - For any date $D$ and room $R$ (or room type $T$), total assigned active reservations + confirmed out-of-service maintenance blocks must not exceed physical capacity:
     $$\text{Occupied}(R, D) + \text{Maintenance}(R, D) \le 1$$
2. **Concurrency Control Strategy:**
   - PostgreSQL row-level locking (`SELECT ... FOR UPDATE`) during room allocation transactions, scoped to `(property_id, stay_date_range)`.
   - Optimistic concurrency control (`version` column with atomic `WHERE id = :id AND version = :expected_version`) for all reservation amendments, date shifts, and room relocations.
   - Concurrency stress suite: 100 simultaneous requests competing for the last available room must accept exactly 1 and reject 99 with clear `409 Conflict` (HTTP status code, preserved client state, and alternative recommendations).

---

## 4. Accounting, Double-Entry Folio Journal & Night Close

### Findings on Baseline Prototype
The prototype stores integer-cent balances directly on booking records, modifying balances in place when charges or refunds occur. This creates audit loss, makes partial refund reconciliation fragile, and lacks business-day boundary enforcement.

### Target Architecture & Invariants (Target M07)
1. **Immutable Double-Entry Ledger:**
   - All monetary mutations append immutable journal lines (`debit` and `credit` entries with balanced zero sum per transaction).
   - Columns: `id`, `organization_id`, `property_id`, `folio_id`, `account_code`, `business_date`, `currency`, `amount_minor_units`, `entry_type`, `created_at`, `created_by`, `correlation_id`.
   - Destructive row edits or deletes are strictly forbidden; corrections occur exclusively via compensating reversal entries.
2. **Business-Date vs Wall-Clock Time:**
   - Every property maintains a formal `current_business_date`.
   - Postings belong to the active property business date regardless of server UTC time or local DST transitions.
3. **Night Audit / Daily Close Workflow:**
   - The night audit is an idempotent, resumable multi-stage batch process:
     1. Pre-close validation (unassigned arrivals, pending departures, open shift cash balances).
     2. Automatic room & tax charges posting.
     3. Financial balancing check (total debits == total credits).
     4. Business date increment ($D \to D+1$).
     5. Immutable snapshot generation for property financial archives.
   - Replay protection: Running night audit twice for the same business date produces a safe no-op.

---

## 5. Jurisdiction, Statutory & Tax Requirements

### Regulatory Blockers (DEC03)
Different operating jurisdictions impose non-negotiable statutory requirements:
1. **Tax Calculations:** Inclusive vs exclusive VAT/sales tax, municipal tourist city taxes (per-person per-night vs flat percentage), and mandatory tax invoice sequencing (gap-free legal invoice numbers).
2. **Guest Registration / Police Reporting:** Statutory guest identification data (passport numbers, nationality, home address) required in jurisdictions like South Africa, Portugal, and the EU.
3. **Data Retention & Privacy (GDPR / POPIA):** Guest PII minimization, role-restricted visibility, separate PII encryption, and compliant audit trail retention.
4. **Mandate:** Antigravity will not invent national tax rates or invoice formatting rules. Formal sign-off on country-specific finance policies from the project owner and qualified accountant is a required blocker before Phase 3 (G3).

---

## 6. Payment Provider Eligibility, Webhooks & PCI Boundaries

### Payment Processing Blockers (DEC04)
1. **Hosted Capture Only:**
   - Full hosted/tokenized capture (Stripe Elements / Adyen Drop-in / regional payment gateway redirect).
   - Zero PAN/CVV transmission through or persistence within the application server, qualifying the hotel merchant for PCI DSS SAQ A eligibility.
2. **Webhook Intake & Idempotency:**
   - Every payment mutation requires a client-generated durable idempotency key scoped to `(property_id, operation_id)`.
   - Webhook intake enforces cryptographic signature verification (HMAC-SHA256).
   - Deduplication store prevents duplicate payment credits from replayed webhooks.
   - Status machine explicitly tracks: `PENDING` $\to$ `AUTHORIZED` $\to$ `CAPTURED` | `FAILED` | `REFUNDED` | `UNCERTAIN`.
3. **Settlement Reconciliation:**
   - Independent daily batch reconciliation between provider payout reports and internal ledger balances to detect processing discrepancies.

---

## 7. Housekeeping, Room Readiness & Emergency Relocations

### Target Architecture & Mobile Workflow
1. **Distinct Physical vs Operational States:**
   - *Occupancy State:* `VACANT`, `OCCUPIED`.
   - *Cleaning State:* `DIRTY`, `CLEANING_IN_PROGRESS`, `CLEAN`, `INSPECTED`.
   - *Readiness State:* `READY_FOR_CHECKIN`, `BLOCKED`, `OUT_OF_SERVICE`, `MAINTENANCE_REQUIRED`.
   - A room that is `CLEAN` is not `READY_FOR_CHECKIN` if supervisor inspection is required or if it is marked `OUT_OF_SERVICE`.
2. **Freshness & Mobile Tasking:**
   - Lightweight, responsive housekeeping mobile endpoint with low-bandwidth payload size (<15KB).
   - Event-driven state updates propagate to front desk workspaces within target p95 $\le 5$s (Target M04).
3. **Emergency Out-of-Service Handling:**
   - When a room suffers a physical failure (e.g., plumbing defect), an emergency workflow flags the room `OUT_OF_SERVICE` and presents front desk staff with an automated, safe guest relocation command.

---

## 8. Backup, High Availability & Disaster Recovery

### Recovery Architecture (Target M11)
1. **Recovery Objectives:**
   - **RPO (Recovery Point Objective):** $\le 15$ minutes (enforced via continuous WAL archiving and transaction log streaming).
   - **RTO (Recovery Time Objective):** $\le 60$ minutes (automated recovery drill to isolated testing VPC).
2. **Dual-Object Backup Cohesion:**
   - Database snapshots must coordinate with Cloud Storage / file asset backups (guest documents, invoices, signed receipts).
   - Restoration procedures must verify database references against actual restored object storage buckets.
3. **Verification Drills:**
   - Two witnessed, timed restore drills on synthetic data before G5 qualification.

---

## 9. Technology Stack & Architecture Decision Records (ADRs)

| Component | Prototype Baseline | Recommended Production Architecture | Rationale & Tradeoffs |
|---|---|---|---|
| **Runtime** | Node 24 (Vanilla HTTP) | Node 24 LTS (Fastify / Express modular framework) | Retains Node performance and team alignment; Fastify provides built-in JSON schema validation, high throughput, and robust OpenAPI plugin ecosystem. |
| **Language** | Vanilla JavaScript (ESM) | TypeScript (strict mode) | Eliminates runtime type errors across complex multi-property financial and reservation domains. |
| **Database** | SQLite file | Managed PostgreSQL 16 (Cloud SQL / Amazon RDS) | Row-level locking, ACID transactions, robust connection pooling (PgBouncer), native JSONB, schemas, and point-in-time recovery. |
| **Migrations** | None (ad-hoc SQL script) | Versioned migration tool (e.g., node-pg-migrate / Prisma) | Forward/backward migrations with automated rollback testing in CI. |
| **Asynchronous Jobs** | None | Transactional Outbox pattern with PgBoss / BullMQ | Guarantees reliable webhook delivery, async night audit processing, and email dispatch without distributed dual-write inconsistencies. |
| **Observability** | Console stdout | Structured JSON logging (Pino), OpenTelemetry tracing, Prometheus metrics | Correlation IDs, audit trail protection, and latency telemetry (Target M08). |

---

## 10. Staffing, Capacity & Monthly Cost Model

### Indicative Capacity Plan
- **Backend Stream (Antigravity):** 2 senior backend engineers + 1 cloud/DevOps SRE (part-time).
- **Frontend Stream (Codex):** 1 lead design/frontend engineer + 1 UI/UX specialist.
- **Review & Quality Assurance:** 1 independent security/compliance reviewer (`qa_critic`) + project owner product lead.
- **Timeline:** 14–20 elapsed weeks across 7 gates (G0 to G6).

### Monthly Infrastructure Cost Model (Pilot: 2 Properties, 100 Rooms)
- Managed PostgreSQL (Cloud SQL 2 vCPU, 8GB RAM, 100GB SSD with HA replica): ~$180 / month
- Application Runtime (Google Cloud Run / AWS ECS Fargate, auto-scaled 2–6 instances): ~$60 / month
- Object Storage (GCS / S3 with Multi-Region redundancy & backup archiving): ~$25 / month
- Monitoring, Logging & Telemetry (Cloud Logging / Datadog / Grafana Cloud): ~$45 / month
- Payment Sandbox & Provider Fees: Transaction-based (0% fixed during discovery; standard 2.9% + 30¢ live)
- **Total Estimated Pilot Infrastructure Cost:** **~$310 / month** (excluding developer toolchains).

---

## 11. Discovery Decision Register Status (Blockers for G0)

All items from `DECISION_REGISTER.md` remain actively tracked:
- **DEC01 (Launch Properties & Jurisdictions):** **BLOCKER.** Project owner must confirm the first 2 pilot properties and country of incorporation.
- **DEC02 (Incumbent Systems & Channels):** **BLOCKER.** Hotel manager must confirm existing reservation data sources and whether OTA channel managers are required for day 1.
- **DEC03 (Tax, Invoice & Regulatory Policies):** **BLOCKER.** Local legal/accounting guidelines required for VAT and guest registration.
- **DEC04 (Payment Provider & Merchant Accounts):** **BLOCKER.** Project owner must select regional gateway (Stripe vs local provider) and initiate merchant underwriting.
- **DEC05 (Deposit & Cancellation Rules):** **BLOCKER.** Hotel operational policy required.
- **DEC06 (Backend Architecture ADR):** **PROPOSED.** Node 24 + TypeScript + Managed PostgreSQL recommended by Antigravity (staged in this document).
- **DEC07 (Capacity & Budget Approval):** **PENDING.** Requires owner review of the 14–20 week window and infrastructure cost model.

---

## 12. Versioned API Contract Proposal (Coordination with Codex)

To unblock Codex frontend development (PLG-FE-01 and PLG-CONTRACT-01) without waiting for database migration implementation, Antigravity proposes **API Version 1 (`/api/v1`)** with the following foundational contract shapes:

### Contract Principles
1. Every URL includes the active property context: `/api/v1/properties/{property_id}/...`.
2. All financial amounts are integer minor units (e.g., cents: `15000` = $150.00) accompanied by an explicit ISO 4217 currency code (`ZAR`, `USD`, `EUR`).
3. All mutable operations accept an `Idempotency-Key` header.
4. All responses include a `version` field for optimistic concurrency checks.
5. Standard error envelopes format:
   ```json
   {
     "error": {
       "code": "CONCURRENT_MODIFICATION_CONFLICT",
       "message": "The reservation was amended by another user. Please refresh and review.",
       "correlation_id": "req-9a8b7c6d",
       "details": {}
     }
   }
   ```

### Core Endpoint Contract Summary
- `GET /api/v1/user/memberships`: Returns authorized organizations, properties, and role capabilities for the logged-in user.
- `GET /api/v1/properties/{property_id}/inventory/availability`: Scoped room inventory availability by date range.
- `POST /api/v1/properties/{property_id}/reservations`: Creates a reservation with policy snapshots and returns `version: 1`.
- `PATCH /api/v1/properties/{property_id}/reservations/{id}`: Amends reservation dates/room with optimistic version check (`If-Match: "1"`).
- `POST /api/v1/properties/{property_id}/reservations/{id}/check-in`: Validates eligibility, room readiness, deposit payment status, and performs atomic check-in.
- `GET /api/v1/properties/{property_id}/folios/{id}`: Returns itemized charges, payments, and balanced ledger lines.
- `POST /api/v1/properties/{property_id}/folios/{id}/charges`: Appends an immutable charge line.
- `POST /api/v1/properties/{property_id}/folios/{id}/payments`: Initiates or records a tokenized payment/refund.
- `GET /api/v1/properties/{property_id}/housekeeping/tasks`: Mobile-optimized room cleaning list with priority flags.
- `PATCH /api/v1/properties/{property_id}/rooms/{room_id}/state`: Updates cleaning/inspection state with immediate event propagation.

---

## 13. Proposed Next Scoped Task: Foundation Staging (F1 / F2)

Following independent review and completion of PLG-BOARD-01 blockers, Antigravity proposes the next bounded work package:
- **Allocation:** PLG-BE-01 / F1 & F2 Foundations.
- **Allowed Scope:** `projects/platinum-lodge/` (specifically `data/`, `migrations/`, `server/`, `contracts/`).
- **Forbidden Paths:** `projects/platinum-lodge/public/`, `portal/`, `.env*`, `**/secrets/**`.
- **Deliverables:**
  1. Complete OpenAPI 3.1 specification for `/api/v1`.
  2. JSON schema fixtures covering two properties across two independent organizations.
  3. Relational database schema migrations (PostgreSQL DDL) establishing tenant boundaries and inventory locks.
  4. Contract test suite validating schema adherence and negative cross-tenant isolation.
