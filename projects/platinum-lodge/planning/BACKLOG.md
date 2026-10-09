# Initiated MAS-PM backlog

Project **PLG**: 55 records — one initiative, 9 epics and 45 implementation/discovery work packages.

Canonical planning state: local MAS-PM (`mas_pm.db`) accessed through existing Python APIs, not raw SQL. This is a static export. All records are BACKLOG, with zero execution-token appetite, no runtime assignee and no active sprint. Zero is a deliberate planning-only allowance, not a cost estimate. Owner labels do not provision credentials. Check shared-instance synchronization before execution.

Work packages require sizing and splitting into short, reviewable tasks before staging. Task-level scopes, acceptance and blockers are recorded in MAS-PM and [BACKLOG.json](BACKLOG.json). CSV: [BACKLOG.csv](BACKLOG.csv). No task below is reported complete.

Initiative: **PLG-1**.

| Epic | MAS-PM key | Delivery owner | Gate |
| --- | --- | --- | --- |
| D: Discovery, feasibility and operating policies | PLG-2 | Codex | G0 |
| F: Multi-property backend foundations | PLG-3 | Antigravity development team | G1 |
| U: Frontend system and property-aware navigation | PLG-4 | Codex | G1 |
| R: Reservations and front desk | PLG-5 | Antigravity development team | G2 |
| B: Billing, payments and business-day close | PLG-6 | Antigravity development team | G3 |
| H: Housekeeping and room readiness | PLG-7 | Antigravity development team | G4 |
| M: Management visibility and productivity | PLG-8 | Codex | G4 |
| Q: Production qualification and recovery | PLG-9 | Antigravity development team | G5 |
| L: Migration, training and operational acceptance | PLG-10 | Antigravity development team | G6 |

| Task | Outcome | Delivery/integration owner | Gate | Blocking tasks |
| --- | --- | --- | --- | --- |
| PLG-11 (D1) | Confirm launch properties, countries and scope | Codex | G0 | — |
| PLG-12 (D2) | Measure current staff workflow baseline | Codex | G0 | PLG-11 |
| PLG-13 (D3) | Validate financial, guest-registration and privacy policies | Antigravity development team | G0 | PLG-11 |
| PLG-14 (D4) | Validate regional payment provider and merchant readiness | Antigravity development team | G0 | PLG-11 |
| PLG-15 (D5) | Agree backend architecture, capacity and cost model | Antigravity development team | G0 | PLG-13, PLG-14 |
| PLG-16 (D6) | Acknowledge ownership and synchronize execution planning | Antigravity development team | G0 | PLG-11 |
| PLG-17 (F1) | Plan selective prototype/frontier integration | Antigravity development team | G1 | PLG-15, PLG-16 |
| PLG-18 (F2) | Implement organization/property data model and migrations | Antigravity development team | G1 | PLG-17 |
| PLG-19 (F3) | Implement production authentication and scoped authorization | Antigravity development team | G1 | PLG-18 |
| PLG-20 (F4) | Publish versioned API and operation contract | Antigravity development team | G1 | PLG-18, PLG-19 |
| PLG-21 (F5) | Provision staging, CI and deployment/migration skeleton | Antigravity development team | G1 | PLG-15, PLG-17 |
| PLG-22 (U1) | Inventory frontend gaps and specify role journeys | Codex | G1 | PLG-11, PLG-12 |
| PLG-23 (U2) | Define design system and approved art direction | Codex | G1 | PLG-22 |
| PLG-24 (U3) | Implement property/role-aware shell and safe switching | Codex | G1 | PLG-23, PLG-20 |
| PLG-25 (U4) | Implement accessible components and resilient API client | Codex | G1 | PLG-23, PLG-20 |
| PLG-26 (R1) | Implement inventory, rates and reservation policy snapshots | Antigravity development team | G2 | PLG-20, PLG-13 |
| PLG-27 (R2) | Implement concurrent-safe reservation lifecycle and room moves | Antigravity development team | G2 | PLG-26 |
| PLG-28 (R3) | Implement check-in/out eligibility and exception APIs | Antigravity development team | G2 | PLG-27, PLG-13 |
| PLG-29 (R4) | Build reservations/calendar and front-desk workspaces | Codex | G2 | PLG-24, PLG-25, PLG-27, PLG-28 |
| PLG-30 (R5) | Verify reservation/front-desk integration and regression | Antigravity development team | G2 | PLG-29 |
| PLG-31 (B1) | Implement immutable property/legal-entity journal and folios | Antigravity development team | G3 | PLG-20, PLG-13 |
| PLG-32 (B2) | Implement taxes, invoice/receipt rules and financial exports | Antigravity development team | G3 | PLG-31 |
| PLG-33 (B3) | Implement nightly posting and resumable business-day close | Antigravity development team | G3 | PLG-31, PLG-27 |
| PLG-34 (B4) | Integrate provider capture/refunds and verified webhooks | Antigravity development team | G3 | PLG-31, PLG-14, PLG-21 |
| PLG-35 (B5) | Implement tender, shift and provider settlement reconciliation | Antigravity development team | G3 | PLG-32, PLG-33, PLG-34 |
| PLG-36 (B6) | Build billing, checkout and reconciliation frontend | Codex | G3 | PLG-25, PLG-32, PLG-33, PLG-34, PLG-35, PLG-29 |
| PLG-37 (B7) | Qualify finance and payment acceptance | Antigravity development team | G3 | PLG-36 |
| PLG-38 (H1) | Implement housekeeping assignment and inspection workflow | Antigravity development team | G4 | PLG-20, PLG-28 |
| PLG-39 (H2) | Implement emergency maintenance and inventory relocation | Antigravity development team | G4 | PLG-38, PLG-27 |
| PLG-40 (H3) | Build mobile housekeeping and supervisor workspace | Codex | G4 | PLG-25, PLG-38, PLG-39 |
| PLG-41 (H4) | Verify readiness propagation and handover | Antigravity development team | G4 | PLG-40 |
| PLG-42 (M1) | Implement property/group metrics and actionable exception APIs | Antigravity development team | G4 | PLG-35, PLG-39, PLG-28 |
| PLG-43 (M2) | Build Today workspace and portfolio management views | Codex | G4 | PLG-24, PLG-42, PLG-36, PLG-40 |
| PLG-44 (M3) | Measure and refine staff productivity | Codex | G4 | PLG-43, PLG-12 |
| PLG-45 (Q1) | Implement monitoring, audit retention and incident runbooks | Antigravity development team | G5 | PLG-21, PLG-35, PLG-41 |
| PLG-46 (Q2) | Implement off-site recovery and conduct two restore drills | Antigravity development team | G5 | PLG-45 |
| PLG-47 (Q3) | Run independent security and tenant isolation qualification | Antigravity development team | G5 | PLG-37, PLG-41, PLG-42 |
| PLG-48 (Q4) | Run backend load, soak and fault qualification | Antigravity development team | G5 | PLG-37, PLG-41, PLG-42 |
| PLG-49 (Q5) | Qualify accessibility, frontend performance and localization | Codex | G5 | PLG-44 |
| PLG-50 (Q6) | Prepare qualification packet and release recommendation | Antigravity development team | G5 | PLG-46, PLG-47, PLG-48, PLG-49 |
| PLG-51 (L1) | Develop and rehearse migration with opening-balance reconciliation | Antigravity development team | G5 | PLG-37, PLG-41, PLG-42 |
| PLG-52 (L2) | Prepare role training and safe manual continuity guides | Codex | G5 | PLG-44, PLG-37, PLG-41 |
| PLG-53 (L3) | Approve cutover, rollback and support coverage | Antigravity development team | G5 | PLG-51, PLG-52, PLG-50 |
| PLG-54 (L4) | Execute authorized staged multi-property rollout | Antigravity development team | G6 | PLG-53 |
| PLG-55 (L5) | Complete operational acceptance and support handover | Antigravity development team | G6 | PLG-54 |

## Task acceptance and review

### PLG-11: Confirm launch properties, countries and scope

Owner-reviewed Platinum Hotel Mozambique pilot scope, room/role inventory, required integrations and exclusions; multi-property technical qualification remains required; no implied legal/provider eligibility.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/planning/. Forbidden: projects/platinum-lodge/public/, projects/platinum-lodge/server.js. Refine actual file allowlist before staging.

### PLG-12: Measure current staff workflow baseline

M01/M02 protocol, role journey inventory and consented/anonymized matched task timings at participating hotels.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/planning/. Forbidden: projects/platinum-lodge/public/, projects/platinum-lodge/server.js. Refine actual file allowlist before staging.

### PLG-13: Validate financial, guest-registration and privacy policies

Accountant/legal-reviewed taxes, invoice numbering, deposits, cancellation/no-show, refunds, credit balance, guest reporting and retention per jurisdiction.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/planning/. Forbidden: projects/platinum-lodge/public/, projects/platinum-lodge/server.js. Refine actual file allowlist before staging.

### PLG-14: Validate regional payment provider and merchant readiness

Country/currency/payout/refund/terminal eligibility, sandbox access, hosted capture and merchant obligations documented; owner procurement decision.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/planning/. Forbidden: projects/platinum-lodge/public/, projects/platinum-lodge/server.js. Refine actual file allowlist before staging.

### PLG-15: Agree backend architecture, capacity and cost model

ADRs for database/identity/hosting/job boundaries; capacity estimate and engineering/operating cost categories reviewed, no invented approvals.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/planning/. Forbidden: projects/platinum-lodge/public/, projects/platinum-lodge/server.js. Refine actual file allowlist before staging.

### PLG-16: Acknowledge ownership and synchronize execution planning

Antigravity acknowledges agreement; shared MAS-PM synchronization/principals validated; precise scopes and task splits proposed without granting permissions.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/planning/. Forbidden: projects/platinum-lodge/public/, projects/platinum-lodge/server.js. Refine actual file allowlist before staging.

### PLG-17: Plan selective prototype/frontier integration

Reviewed branch divergence and selective integration plan preserves frontier security/ownership; legacy modules inventoried and disabled unless qualified.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/planning/. Forbidden: projects/platinum-lodge/public/, projects/platinum-lodge/server.js. Refine actual file allowlist before staging.

### PLG-18: Implement organization/property data model and migrations

Versioned reversible-or-recoverable migrations, membership model and two-org/two-property fixtures; property-local config, room numbering and timezone/currency.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-19: Implement production authentication and scoped authorization

Privileged MFA, revocation/recovery, secure session behavior and server checks for every resource/file/export/job; negative tests M05.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-20: Publish versioned API and operation contract

Jointly reviewed OpenAPI, pagination, capabilities, record versions, errors, correlation IDs, durable retry semantics and fixtures.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-21: Provision staging, CI and deployment/migration skeleton

Separated environments/secrets, candidate-bound CI, smoke checks and reviewed migration rollout; no production activation.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-22: Inventory frontend gaps and specify role journeys

Core journeys with all loading/error/stale/conflict/permission states and role/property navigation mapped to required APIs.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-23: Define design system and approved art direction

Accessible component/token specifications, readable typography, semantic status design, EN/PT guidance and image-rights register.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-24: Implement property/role-aware shell and safe switching

Property identity visible, stale responses rejected, scoped caches cleared, unsaved input handled; group actions require explicit property.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-25: Implement accessible components and resilient API client

Keyboard/dialog/form states, input preservation, retained operation keys, pagination and version-conflict handling; browser checks at target sizes/zoom.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-26: Implement inventory, rates and reservation policy snapshots

Room types/sellable inventory, rate/capacity/deposit/cancellation snapshots and business-date semantics tested.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-27: Implement concurrent-safe reservation lifecycle and room moves

Creation/amend/cancel/no-show/move invariants; M06 races, version conflicts and idempotent commands verified.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-28: Implement check-in/out eligibility and exception APIs

Clean/unblocked/available room enforcement, dates/occupancy, settlement/credit policy and audited overrides; no client-only policy.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-29: Build reservations/calendar and front-desk workspaces

Scoped availability/create/amend/arrivals/departures/in-house flows integrate real APIs with retained input and clear property context.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-30: Verify reservation/front-desk integration and regression

Actual candidate-bound lifecycle/browser/concurrency evidence; hotel supervisor signs scenarios, Codex reviews UI contract.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-31: Implement immutable property/legal-entity journal and folios

Balanced currency-aware journal, deposits/receivables/earned revenue separation, split folios/routing, reversals and audit golden fixtures.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-32: Implement taxes, invoice/receipt rules and financial exports

Accountant-approved rounding/numbering/tax examples reconcile; permission-safe/formula-safe exports and no destructive financial edits.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-33: Implement nightly posting and resumable business-day close

Timezone/DST/late posting fixtures; idempotent nightly close, restart-safe checkpoints and explicit failed/partial close status.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-34: Integrate provider capture/refunds and verified webhooks

Hosted/tokenized flows, signed/deduplicated/out-of-order events, lost acknowledgement and unknown states; no PAN/CVV storage.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-35: Implement tender, shift and provider settlement reconciliation

Cash/bank/manual/provider tenders, refund limits and discrepancy workflow; M07 replay/fault fixtures and settlement totals reconcile.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-36: Build billing, checkout and reconciliation frontend

Folios/invoices/tenders/refunds/shift close/uncertain payments integrate actual APIs; high-risk confirmations and role-safe details.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-37: Qualify finance and payment acceptance

Finance independent review, M07, sandbox proof and separately authorized live smoke/settlement evidence; operational runbooks accepted.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-38: Implement housekeeping assignment and inspection workflow

Distinct occupancy/cleaning/readiness, assignments/priorities and supervisor inspection with audit/version conflicts.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-39: Implement emergency maintenance and inventory relocation

Out-of-service with current/future stays creates accountable relocation workflow; availability and guest communication states remain safe.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-40: Build mobile housekeeping and supervisor workspace

Assigned rooms/priorities, safe bulk actions, quick updates and inspection; stale/offline state explicit; M04 task checks.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-41: Verify readiness propagation and handover

M04 server propagation and browser integration; back-to-back arrivals, room failure and staff handover scenarios reviewed.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-42: Implement property/group metrics and actionable exception APIs

Reviewed occupancy/ADR/RevPAR definitions, separate currencies, safe drill-down and source/owner/age/next action for every priority exception.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-43: Build Today workspace and portfolio management views

Role-focused tasks, arrival/payment/cleaning exceptions, scoped portfolio and drill-down with freshness and action accountability.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-44: Measure and refine staff productivity

Matched M01–M04/M14 study; disclose sample and failures, record improvements and remeasure changed candidate.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-45: Implement monitoring, audit retention and incident runbooks

Redacted logs, critical synthetic checks, correlation IDs, protected audit retention, alert routing and staffed escalation proposal.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-46: Implement off-site recovery and conduct two restore drills

Coordinated DB/files/jobs/keys recovery, independent encrypted backups, witnessed M11 and transaction/provider reconciliation.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-47: Run independent security and tenant isolation qualification

ASVS 5.0 applicable Level 2 mapping, M05, upload/CSRF/session/dependency/config checks; no unresolved critical/high findings.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-48: Run backend load, soak and fault qualification

M06–M08 scenario dataset, 8h soak, restart/provider faults and correctness/performance results tied to candidate.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-49: Qualify accessibility, frontend performance and localization

M09/M12 manual keyboard/screen-reader/zoom checks plus browser traces; EN/PT and property currency/timezone examples reviewed.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-50: Prepare qualification packet and release recommendation

Candidate-specific evidence, independent reviews, known risks, monitoring/support and gate decisions; owner decides production release.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-51: Develop and rehearse migration with opening-balance reconciliation

Two-property mapping/dedup/import rehearsals; inventory, deposits, balances and guest provenance reconcile; no blind password/session copies.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-52: Prepare role training and safe manual continuity guides

Role guides, emergency property-safe procedures and training trial M13; hotel staff and Antigravity review correctness.

Reviewer: Antigravity integration review + independent hotel/UX reviewer. Planning file bounds: projects/platinum-lodge/public/, projects/platinum-lodge/planning/, projects/platinum-lodge/test/browser/. Forbidden: projects/platinum-lodge/server.js, projects/platinum-lodge/migrations/. Refine actual file allowlist before staging.

### PLG-53: Approve cutover, rollback and support coverage

Write fence, backup verification, forward recovery/payment limits and escalation rehearsed; owner-approved staffing and cutover decision.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-54: Execute authorized staged multi-property rollout

Only after release authorization: candidate deployment, opening totals verified, monitored cohort and documented stop/rollback conditions.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

### PLG-55: Complete operational acceptance and support handover

M15 14-day evidence at Platinum Hotel Mozambique, daily inventory/finance close, M01–M04/M13 reports, multi-property synthetic qualification, known issues and owner expansion decision; live second-property acceptance deferred.

Reviewer: Codex contract review + separate technical/domain reviewer. Planning file bounds: projects/platinum-lodge/server.js, projects/platinum-lodge/server/, projects/platinum-lodge/migrations/, projects/platinum-lodge/scripts/, projects/platinum-lodge/test/, .github/workflows/platinum-lodge.yml. Forbidden: projects/platinum-lodge/public/. Refine actual file allowlist before staging.

