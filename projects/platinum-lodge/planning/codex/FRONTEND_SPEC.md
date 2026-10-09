# Frontend, design and art direction candidate

## Experience and design system (U1/U2)

Make the active property visible on every operational screen. Prioritize the next safe action, the responsible person and freshness over decorative metrics. Use calm warm-white surfaces, deep green navigation, clear dark text, 16px body/14px supporting text, 44px controls, visible focus and reduced-motion support. Tokens live in public/design-preview/tokens.css; the preview uses system fonts and a typographic monogram. No third-party photography, logos or stock assets are included. Any future images need a rights register with source, license, permission and intended placement; benchmark screenshots are references, not reusable assets.

Role journeys: reception moves from arrivals through readiness verification and allocation to check-in; finance verifies authoritative folios, payment state and reconciliation before checkout/refund; housekeeping moves from assigned room to cleaning then inspection request, with supervisor approval separate; manager triages exceptions and supervises property operations. Never conflate occupancy, cleaning, inspection, booking, payment and reconciliation statuses. Housekeeping should receive the minimum guest information required, with no financial information by default.

Current gap inventory: prototype is single-property and payment recording is not payment processing. Missing production contracts include tenant/property membership; stable identifiers and timezone/business-day semantics; atomic inventory; reservation revisions; role-bound audit; ledger/fiscal documents; payment lifecycle; housekeeping assignment/inspection; KPI definitions and freshness. Preview covers layout and interaction examples, not all these capabilities. A production availability calendar, full checkout/refund flows and complete Portuguese localization remain frontend work after contracts.

## Shell and component behavior (U3/U4)

Changing property must warn about unsaved drafts, clear rendered old-property records, invalidate outstanding responses, and obtain new server-authorized context. The preview demonstrates discard/keep; createContextGuard rejects even a response from before switching away and back. UI role selection is not authentication. Cache, requests, offline data and persistent storage must be scoped by authenticated tenant/property/user; privacy boundaries must be enforced server-side.

Components need initial loading, empty, retryable error, permission denial, stale/offline, conflict, pending and outcome-unknown states. Do not render yesterday's data as current or silently replay financial writes. Preserve draft on conflict; retrieve latest version, show meaningful differences and let the authorized user resolve. Native dialogs have named titles and focus containment; validation must identify fields, preserve entries and announce feedback. Production client must cancel/invalidate obsolete requests, redact logs and handle session expiry with safe draft recovery.

createOperationKeys is an in-memory frontend demonstration: repeat attempts retain a reference until acknowledged, separate by property. It supplies neither durable retry storage nor server idempotency. Agreement is needed on operation lifetime, persistence/privacy, terminal states, reconciliation, expiration and retry rules. Do not generate a new monetary-operation key after a timeout; do not acknowledge an unknown outcome.

## Workflow acceptance details (R4/B6/H3/M2)

Reservations: date validation, inclusive/exclusive nights, live availability, modification/cancellation consequences, late arrivals/no-shows, room moves and overbooking policy need explicit tests. Check-in confirms identity, reservation, room readiness and authorized payment/deposit policy; checkout confirms ledger state and fiscal obligations. Production reservation calendar must support keyboard alternatives, responsive list view, conflict refresh and property-local dates.

Billing: show charges, tax, adjustments, deposits, allocations and balances separately; display currency and source timestamps. Pending/unknown is not paid. Provider status and signed callbacks are backend responsibilities. Refunds require explicit authorization, original payment reference and audit; corrections preserve historical documents. Reconciliation presents mismatch ownership and next action, never invents a zero difference. Cross-property transfers/legal entities require explicit policy.

Housekeeping: separate cleaning and occupancy; show assignment, priority and last confirmed update. Starting/completing a task needs conflict handling and server confirmation. Inspection approval is a distinct authorized action. No offline status is treated as room-ready until synchronized and accepted. Test reassignment, occupied-room access, service refusal, maintenance blocks and shift handovers.

Today/portfolio: expose overdue work, owner, freshness and next action, with counts based on agreed definitions. Keep property and business day explicit. Do not equate bookings with revenue or cash. Portfolio currency conversion needs disclosed rates/time/source; no synthetic aggregate is presented as financial truth. This launch preview uses two fictional Mozambique properties with MZN.

## Joint contract agenda — proposals, not adopted endpoints

For each workflow agree authenticated context, resource identifier, request/response shape, permission, revision/concurrency token, idempotency reference, structured field errors, status lifecycle, pagination/filtering, timestamps/freshness, audit, retries and observability. Supply representative success/denied/conflict/pending/unknown fixtures and a test environment. Antigravity publishes backend feasibility/contracts; Codex reviews UX/data requirements and integrates only after agreement. No shared API definition is changed in this candidate.

## Qualification (Q5)

Review WCAG 2.2 AA with keyboard-only use, visible/retained focus, screen readers, names/roles/status announcements, contrast, 200% zoom and 320 CSS-pixel reflow, reduced motion and accessible tables/calendar alternatives. Test English and Portuguese with reviewed translations, names and MZN formatting, date/business-day boundaries and long strings. The preview is English; it does not claim localization acceptance. Lab checks are regression aids, not a WCAG certificate. Measure the integrated frontend on representative low-end devices/connectivity and real data; do not treat localhost timings as production p75 or service SLO evidence.
