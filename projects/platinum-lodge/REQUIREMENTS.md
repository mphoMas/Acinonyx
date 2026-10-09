# Platinum Lodge system requirements and delivery status

**Baseline note — 9 October 2026:** the delivered requirements below describe the prototype. The [multi-property first-release plan](planning/PROJECT_PLAN.md) supersedes the previous release scope. Production status is determined by the new [acceptance gates](planning/BENCHMARKS_AND_ACCEPTANCE.md), not by this historical delivery table.

## Context

Platinum Lodge is in Tchumene II, Matola, Mozambique. A UN workshop information note confirms the property as an event venue and provides its address and telephone numbers:

https://sdgs.un.org/sites/default/files/2026-02/Information%20Note%20for%20Participants_25-27%20February%202026%20Mozambique%20Workshop_EN_0.pdf

A March 2026 promotional update reproduced on FindGlocal advertises 100 rooms, three pools, two restaurants and bars, a gym, and seven conference rooms with advertised capacity of up to 1,000 guests:

https://www.findglocal.com/MZ/Matola/102391995206065/Platinum-Lodge

These promotional counts are context, not a confirmed inventory. Real rooms, rates, venues, and capacity must be entered by hotel management. The temporary demonstration workspace uses 24 fictional rooms, illustrative venues, guest names, and prices. No real guest data is bundled.

## Objectives

Provide a shared application for reservations, reception, guest accounts, room readiness, dining, events, maintenance, and management reporting. Keep accommodation and venue availability accurate, prevent conflicts, protect sensitive records by staff role, and preserve financial corrections and an audit trail.

## Delivered requirements

| Area | Behavior |
| --- | --- |
| Property configuration | Unique room numbers, categories, capacity, rates, venue names, venue capacity, and hotel contact details. |
| Reservations | Guest and company contact details, stay dates, booking sources, occupancy limits, overlap checks, confirmed stays, cancellation, and no-show statuses. |
| Amendments | Move rooms and extend or shorten stays, preserve the agreed nightly rate, adjust charges, and validate availability. |
| Reception | Check in during the booked dates only into a clean, unblocked, unoccupied room; require a settled balance before check-out. |
| Guest accounts | Stay charges, additional departmental charges, partial payments, manager refunds, printable statements, and CSV exports. |
| Financial integrity | Integer-cent amounts, transactional guest account updates, idempotent financial/booking POST requests, and traceable reversals. |
| Housekeeping | Dirty, cleaning, awaiting-inspection, and clean states; reception or manager inspection approval; checkout makes a room dirty. |
| Dining | Restaurant, bar, and poolside sale recording; immediate-payment records or charges to an active in-house guest account. |
| Events | Provisional and confirmed bookings, venue/time/capacity conflict checks, organiser information, setup/cleanup periods, deposits, cancellation, and printable instructions. |
| Maintenance | Requests by room or general facility, priorities, open/in-progress/resolved statuses, and room blocks. Active/future booked rooms cannot be blocked. |
| Reporting | Occupancy, arrivals/departures, booking charges, recorded receipts, guest balances, booking sources, and exports. Future booking charges are not presented as earned revenue. |
| Access | Individual staff accounts; manager, reception, finance, housekeeping, dining, events, and maintenance roles; server-side access enforcement; account deactivation and password changes. |
| Privacy | Housekeeping/maintenance cannot fetch guest identity or financial records. Dining receives only in-house guest details needed for room charges. |
| Images | Ten source-labelled hotel image references, administrator upload/removal, title/category/alternative text, and permission-status tracking. |
| Localisation | Portuguese/English navigation and primary labels, MZN monetary formatting, and Africa/Maputo dates. Some explanatory copy is English. |
| Persistence | SQLite hotel records survive restarts; demos use separate temporary databases. |
| Continuity | Consistent SQLite backup plus uploaded images, backup integrity check, and documented restoration. |

## Deferred requirements

Production MFA and account-recovery services; granular discount/refund approval limits; statutory guest-registration requirements and tax invoices; automatic night audit and earned-revenue accounting; cashier shifts and company credit billing; group room allocations; cancellation fees and deposit policies; scheduled housekeeping assignments; inventory, purchasing, and kitchen tickets; accounting, payment processing, booking-channel, and messaging integrations; event refunds within the system; complete Portuguese copy; scheduled backups and high-availability hosting.

Payments record funds already received/refunded and do not process transactions. Event deposits are tracked separately from guest payments. HTTPS and appropriate data-retention and security policies are needed for a real deployment.

## Acceptance evidence

Automated tests cover account setup and authentication, role restrictions, room overlaps and capacity, cleaning checks, dining transfers, payment balances, event conflicts/capacity, transaction replay protection, stay amendments, refunds, atomic validation, demo isolation, process restarts, and backup restoration.

Browser checks passed for department navigation, a complete reservation-to-checkout workflow, housekeeping inspection, dining entry, local image upload, Portuguese navigation, and mobile layout. External hotel reference images could not be downloaded or rendered under the workspace network restrictions; approved originals can be uploaded.

## Information still required from the hotel

Confirmed room inventory and rates; reception/deposit/cancellation policies; venue layouts and capacities; payment/accounting providers; tax and guest-registration rules; credit/approval limits; retention rules; hosting and connectivity requirements; image reuse permission; migration inputs and launch priorities.
