# Full delivery lifecycle — execution control

Owner request recorded 9 October 2026: action delivery across all nine epics and the indicative 14–20-week implementation window. Codex coordinates the lifecycle and its assigned frontend/design work; the owner explicitly confirmed that Antigravity retains backend/engine implementation. This document references the existing PLG backlog, not a replacement board.

## Current evidence and next gate

Shared Git: Antigravity acknowledgement, board-sync evidence and backend discovery at 5e96bf95; Codex frontend/specification/measurement/training candidate at 836c2721. All G0–G6 gates remain unpassed. Local cloud MAS-PM read through its public API shows 55 BACKLOG records with no runtime assignees; that is not proof of the desktop database's current state. Reconcile through authenticated workflows, preserving existing evidence/state. No authenticated execution identity or reviewer has been provisioned by this document.

Country Mozambique and Excel baseline are confirmed. Multi-property release-one scope remains. Owner confirmed Platinum Hotel as the sole initial Mozambique pilot and no existing payment provider. Operational policies, room count, qualified local fiscal/privacy review, eligible merchant/provider, budget/capacity and actual staff measurements remain unresolved. Week 1 means agreed execution commencement after capacity/prerequisites are established, not a retrospectively assumed calendar date. The range is conditional and must be reforecast.

## Epic delivery sequence

| Epic | Indicative weeks | Exit outcome |
|---|---|---|
| D Discovery | 1–2 | G0: confirmed scope, policy/provider feasibility, baseline, capacity and ownership |
| F Foundations | 3–5 | G1: reviewed tenancy/auth, migrations/staging and agreed versioned contracts |
| U Frontend system | 3–5 | G1: property-safe shell, component/design system and integrated client |
| R Reservations | 6–9 | G2: atomic reservation/check-in/out lifecycle with actual browser/concurrency evidence |
| B Finance | 6–12 | G3: authoritative ledger, fiscal documents, provider and reconciliation |
| H Housekeeping | 8–13 | G4: assignment/inspection/readiness/maintenance and safe front-desk propagation |
| M Management | 8–13 | G4: defined metrics, actionable exceptions and measured staff improvement |
| Q Qualification | 13–16 or later | G5: independently reviewed security, performance, recovery and frontend qualification |
| L Operational rollout | 13–20 | G6: reconciled migration, training, authorized rollout and 14 days at Platinum Hotel plus multi-property technical qualification |

Windows overlap only where task blockers permit. A static preview does not satisfy an integrated gate. No production rollout or funds movement is authorized by an implementation schedule alone. The owner makes the final release decision on a concrete qualification packet.

## All 45 work packages

Read acceptance/reviewer/path scope in BACKLOG.json and runtime blockers/state in MAS-PM before staging. Split packages into reviewable changes there using the authenticated workflow; do not duplicate all records into the MAS coordination queue.

| Ticket | Outcome | Implementation owner | Window | Blockers |
|---|---|---|---|---|
| PLG-11 (D1) | Confirm launch properties, countries and scope | Codex | 1–2 | — |
| PLG-12 (D2) | Measure current staff workflow baseline | Codex | 1–2 | D1 |
| PLG-13 (D3) | Validate financial, guest-registration and privacy policies | Antigravity development team | 1–2 | D1 |
| PLG-14 (D4) | Validate regional payment provider and merchant readiness | Antigravity development team | 1–2 | D1 |
| PLG-15 (D5) | Agree backend architecture, capacity and cost model | Antigravity development team | 1–2 | D3, D4 |
| PLG-16 (D6) | Acknowledge ownership and synchronize execution planning | Antigravity development team | 1–2 | D1 |
| PLG-17 (F1) | Plan selective prototype/frontier integration | Antigravity development team | 3–5 | D5, D6 |
| PLG-18 (F2) | Implement organization/property data model and migrations | Antigravity development team | 3–5 | F1 |
| PLG-19 (F3) | Implement production authentication and scoped authorization | Antigravity development team | 3–5 | F2 |
| PLG-20 (F4) | Publish versioned API and operation contract | Antigravity development team | 3–5 | F2, F3 |
| PLG-21 (F5) | Provision staging, CI and deployment/migration skeleton | Antigravity development team | 3–5 | D5, F1 |
| PLG-22 (U1) | Inventory frontend gaps and specify role journeys | Codex | 3–5 | D1, D2 |
| PLG-23 (U2) | Define design system and approved art direction | Codex | 3–5 | U1 |
| PLG-24 (U3) | Implement property/role-aware shell and safe switching | Codex | 3–5 | U2, F4 |
| PLG-25 (U4) | Implement accessible components and resilient API client | Codex | 3–5 | U2, F4 |
| PLG-26 (R1) | Implement inventory, rates and reservation policy snapshots | Antigravity development team | 6–9 | F4, D3 |
| PLG-27 (R2) | Implement concurrent-safe reservation lifecycle and room moves | Antigravity development team | 6–9 | R1 |
| PLG-28 (R3) | Implement check-in/out eligibility and exception APIs | Antigravity development team | 6–9 | R2, D3 |
| PLG-29 (R4) | Build reservations/calendar and front-desk workspaces | Codex | 6–9 | U3, U4, R2, R3 |
| PLG-30 (R5) | Verify reservation/front-desk integration and regression | Antigravity development team | 6–9 | R4 |
| PLG-31 (B1) | Implement immutable property/legal-entity journal and folios | Antigravity development team | 6–12 | F4, D3 |
| PLG-32 (B2) | Implement taxes, invoice/receipt rules and financial exports | Antigravity development team | 6–12 | B1 |
| PLG-33 (B3) | Implement nightly posting and resumable business-day close | Antigravity development team | 6–12 | B1, R2 |
| PLG-34 (B4) | Integrate provider capture/refunds and verified webhooks | Antigravity development team | 6–12 | B1, D4, F5 |
| PLG-35 (B5) | Implement tender, shift and provider settlement reconciliation | Antigravity development team | 6–12 | B2, B3, B4 |
| PLG-36 (B6) | Build billing, checkout and reconciliation frontend | Codex | 6–12 | U4, B2, B3, B4, B5, R4 |
| PLG-37 (B7) | Qualify finance and payment acceptance | Antigravity development team | 6–12 | B6 |
| PLG-38 (H1) | Implement housekeeping assignment and inspection workflow | Antigravity development team | 8–13 | F4, R3 |
| PLG-39 (H2) | Implement emergency maintenance and inventory relocation | Antigravity development team | 8–13 | H1, R2 |
| PLG-40 (H3) | Build mobile housekeeping and supervisor workspace | Codex | 8–13 | U4, H1, H2 |
| PLG-41 (H4) | Verify readiness propagation and handover | Antigravity development team | 8–13 | H3 |
| PLG-42 (M1) | Implement property/group metrics and actionable exception APIs | Antigravity development team | 8–13 | B5, H2, R3 |
| PLG-43 (M2) | Build Today workspace and portfolio management views | Codex | 8–13 | U3, M1, B6, H3 |
| PLG-44 (M3) | Measure and refine staff productivity | Codex | 8–13 | M2, D2 |
| PLG-45 (Q1) | Implement monitoring, audit retention and incident runbooks | Antigravity development team | 13–16+ | F5, B5, H4 |
| PLG-46 (Q2) | Implement off-site recovery and conduct two restore drills | Antigravity development team | 13–16+ | Q1 |
| PLG-47 (Q3) | Run independent security and tenant isolation qualification | Antigravity development team | 13–16+ | B7, H4, M1 |
| PLG-48 (Q4) | Run backend load, soak and fault qualification | Antigravity development team | 13–16+ | B7, H4, M1 |
| PLG-49 (Q5) | Qualify accessibility, frontend performance and localization | Codex | 13–16+ | M3 |
| PLG-50 (Q6) | Prepare qualification packet and release recommendation | Antigravity development team | 13–16+ | Q2, Q3, Q4, Q5 |
| PLG-51 (L1) | Develop and rehearse migration with opening-balance reconciliation | Antigravity development team | 13–20 | B7, H4, M1 |
| PLG-52 (L2) | Prepare role training and safe manual continuity guides | Codex | 13–20 | M3, B7, H4 |
| PLG-53 (L3) | Approve cutover, rollback and support coverage | Antigravity development team | 13–20 | L1, L2, Q6 |
| PLG-54 (L4) | Execute authorized staged multi-property rollout | Antigravity development team | 13–20 | L3 |
| PLG-55 (L5) | Complete operational acceptance and support handover | Antigravity development team | 13–20 | L4 |

## Immediate execution and handoff

1. Owner confirmed Codex coordinates delivery and the existing implementation split remains. Codex progresses frontend/design work and contract review; Antigravity progresses backend/engine work within authenticated scopes.
2. Antigravity reviews CODEX_CONTRACT_REVIEW.md, resolves the proposal issues and supplies the complete contract packet; jointly agree PLG-20 / PLG-CONTRACT-01. Its Git acknowledgement is now recorded; actual principal/allowance/assignment and independent review still need verification.
3. Codex evolves the frontend candidate into API-integrated workflows once the agreed contracts and staging exist, preserving draft/context/retry safeguards. Reservations calendar, checkout/refunds, real housekeeping updates, management APIs and Portuguese localization remain implementation work.
4. Collect anonymous Excel baseline observations using the prepared sheet, then run matched trials on the integrated candidate. Do not manufacture staff measurements or announce productivity gains from fixtures.
5. At every gate publish candidate commit, contract/schema versions, actual commands/results, relevant screenshots, independent review, unresolved defects/risks and owner decision. Failed or missing evidence keeps the gate open.

## Cadence and completion

During actual active work: record evidence, next integration point and blockers in MAS-PM; weekly product/operations review assesses demonstrated behavior, decisions, costs and forecast. A chat turn cannot autonomously schedule future weeks, contact staff or operate an unavailable desktop. Resume against current Git/board evidence each session; no unattended execution is claimed.

Production acceptance requires real infrastructure, merchant/provider and fiscal readiness, controlled customer-data migration, staff training, support coverage, witnessed restore rehearsals, independent qualification and authorized pilot. The 14-day Platinum Hotel pilot is elapsed operational evidence, not something a synthetic test can substitute. Live second-property acceptance is deferred until expansion; synthetic isolation tests must still qualify the release-one multi-property architecture.

## Read-only readiness command

Run with the configured project Python environment from the repository root:

```sh
python projects/platinum-lodge/planning/lifecycle_status.py
```

If the dashboard uses another database, pass its actual configured path with `--database`. Existing tenancy checks remain enforced. The report lists live state, actual assignee, execution allowance and unresolved blockers for every work package across all nine epics. `CLEAR` means no unresolved dependency in that instance; it does not authorize staging or execution. Missing databases are rejected without creating one. Results are printed rather than written into another planning store. Do not commit private runtime identities or customer data from production reports.

Verified in the cloud planning instance: nine epics, 45 work packages, 55 total records, all BACKLOG, only PLG-11 dependency-clear. The database SHA-256 remained unchanged across the reporting command. A missing database path was rejected and no file created. These results describe this instance only; Antigravity must run the command against its configured dashboard to reconcile desktop state.


See [owner scope amendment](SCOPE_AMENDMENT_2026_10_09.md): initial pilot is Platinum Hotel only; backend assesses eligible Mozambique providers from scratch. The published frontend candidate is `feat/platinum-lodge-codex-delivery` at `b239cb93`, with six unit tests and 36 browser checks plus mobile/desktop screenshots. These are frontend-specific results, not an integrated gate pass.

## Bind published references to the existing board

`DELIVERY_EVIDENCE_LINKS.json` holds 26 pinned references for initiative/epic coordination, 13 Codex candidates, the owner scope amendment (D1/L5), and contract review. They are explicitly partial/planning evidence, not approvals or verified test-run links.

```sh
python projects/platinum-lodge/planning/link_delivery_evidence.py
python projects/platinum-lodge/planning/link_delivery_evidence.py --apply
```

Use `--database` only with the actual configured dashboard path if needed. Default is preview; apply uses public MAS-PM evidence APIs, maps stable planning references/titles rather than assuming numeric keys, deduplicates references, and does not transition, assign, approve or alter allowances. Errors stop processing; retry safely skips previously attached references.

Cloud preview resolved all 26 references. Apply stopped before the first attachment because the configured governance signing key is absent. No links, task states, assignments or allowances were changed. Do not paste keys into chat or introduce a development signing key to simulate approval. Antigravity/authorized runtime administration must use the normal configured governance environment. Git publication is available even while signed board binding remains blocked.
