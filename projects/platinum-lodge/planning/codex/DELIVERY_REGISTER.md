# Codex delivery candidates — 9 October 2026

These are review artifacts against existing PLG tickets, not a second Scrum board or a declaration of completion. Runtime MAS-PM remains authoritative. No assignments, dependencies or execution states were bypassed. Independent review and the listed integrations/inputs remain required.

User decisions: launch country Mozambique; current operations use Excel, with no established daily workflow measurement. Multi-property capability remains a release-one requirement. Owner selected Platinum Hotel as the sole initial live pilot and no existing payment provider. Multi-property technical qualification remains required; live second-property acceptance is deferred to expansion. See ../SCOPE_AMENDMENT_2026_10_09.md.

| Ticket | Work delivered in this branch | Remaining acceptance input |
|---|---|---|
| PLG-11 D1 | Launch-country and scope intake in DISCOVERY_AND_MEASUREMENT.md | Room/role inventory, legal entity, owner-approved integrations/exclusions |
| PLG-12 D2 | Excel workflow observation protocol and blank measurement CSV | Staff participation and observed baseline; none fabricated |
| PLG-22 U1 | Role journeys, gap and state inventory in FRONTEND_SPEC.md | Staff validation and backend feasibility |
| PLG-23 U2 | Implemented tokens, responsive preview and art direction specification | Brand approval, independent contrast/accessibility review and image rights |
| PLG-24 U3 | Role/property shell, draft switch warning and context-version primitive | Real property memberships, authorization and API integration |
| PLG-25 U4 | Native dialogs/forms, resilient-state preview and stable operation-key primitive, unit tests | Joint contract, durable production retry lifecycle and server idempotency |
| PLG-29 R4 | Front desk queue and validated reservation draft preview | Inventory calendar, atomic availability, bookings/check-in/out APIs; implementation incomplete |
| PLG-36 B6 | Folio presentation and pending/unknown payment states | Real ledger, taxes, checkout, provider callbacks and reconciliation; no payment actions implemented |
| PLG-40 H3 | Mobile room queue and inspection request preview, without guest/financial fields | Real assignments, authorized inspection, audit and conflict APIs |
| PLG-43 M2 | Today attention queue and property overview | Canonical KPI definitions, service freshness, real tasks and portfolio data |
| PLG-44 M3 | Matched-task measurement and refinement protocol | Baseline and production candidate trials; no productivity claim |
| PLG-49 Q5 | Selected browser checks, unit tests and qualification checklist | Portuguese translation review, manual screen reader/zoom, integrated performance and full WCAG review |
| PLG-52 L2 | Role training and manual continuity draft | Accountant/operations/backend review and real recovery rehearsal |

## Review/run

From the repository root:

```sh
python3 -m http.server 8090 --bind 127.0.0.1 --directory projects/platinum-lodge/public/design-preview
```

Open http://127.0.0.1:8090. This is a static design preview, separate from the Scrum dashboard. No hotel API, credentials, guest data or payment provider is used. Records and drafts exist in browser memory only. Closing/reloading loses drafts. Do not use it for actual operations.

```sh
node --test projects/platinum-lodge/test/browser/model.test.mjs
python3 projects/platinum-lodge/test/browser/preview_checks.py
```

Browser checks require Python Playwright and Chromium. Evidence and limits are in VALIDATION.md. The earlier prototype accessibility foundation remains on `feat/platinum-lodge-frontend-foundations` at `920641f`; this branch does not merge its older backend/runtime.

## Antigravity pickup

Fetch `feat/platinum-lodge-codex-delivery`; review this register, FRONTEND_SPEC.md and existing NEXT_PHASE_KICKOFF.md. The Antigravity development team should resolve PLG-BOARD-01 / PLG-BE-01 and jointly agree PLG-CONTRACT-01. Codex owns frontend integration; Antigravity owns backend/engine/data/security/services. The supervised coding swarm does not inherit the development team's authority. Do not set these PLG packages DONE based on the preview or import alone.
