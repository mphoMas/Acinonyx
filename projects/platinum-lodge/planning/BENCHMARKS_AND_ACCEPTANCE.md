# Benchmarks and production acceptance

Research accessed 9 October 2026. Published vendor capabilities establish reference expectations. Vendor statistics are self-reported and do not establish independently measured superiority. All project targets below are proposed and currently unverified.

## Reference systems and standards

| Reference | Supported observation | How we use it |
| --- | --- | --- |
| [Oracle OPERA Cloud](https://www.oracle.com/hospitality/hotel-property-management/hotel-pms-software/) | Chain/property/user configuration, multi-property guest and availability workflows, multiple folios and mobile housekeeping | Capability floor for property context, front-desk operations, folio handling and group management; no assumed access to Oracle services |
| [Cloudbeds API](https://www.cloudbeds.com/api/) | Property-scoped and group-level access, reservations/folios/housekeeping, events, staging and versioned integration support; page advertises 99.95%+ uptime | Tenant-safe integration contract and test-environment reference; uptime is a vendor-published claim, not our measured result or contractual entitlement |
| [Cloudbeds housekeeping](https://myfrontdesk.cloudbeds.com/hc/en-us/articles/25695101078427-Housekeeping-Everything-you-need-to-know) | Assignment and housekeeping operational controls | Baseline for assigned work, room readiness, bulk actions and role boundaries |
| [Mews PMS](https://www.mews.com/en-gb/property-management-system) | Unified reservations/payments/housekeeping workspace; advertises 24% front-desk efficiency improvement | Productivity motivation. Its cohort/method is not established here; our 30% target uses our own matched-task baseline and cannot be described as outperforming Mews |
| [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Accessibility success criteria | Target AA for in-scope journeys; automatic checks alone do not prove conformance |
| [OWASP ASVS 5.0](https://github.com/OWASP/ASVS/tree/v5.0.0) | Versioned application security requirements | Security reviewer maps applicable Level 2 requirements, exceptions and evidence; no automatic certification claim |
| [PCI SSC outsourced-payment eligibility](https://www.pcisecuritystandards.org/faqs/if-a-merchant-s-e-commerce-implementation-meets-the-criteria-that-all-elements-of-payment-pages-originate-from-a-pci-dss-compliant-service-provider-is-the-merchant-eligible-to-complete-saq-a-or-saq-a-ep/) | Hosted capture alone does not establish SAQ eligibility; other criteria apply | Use hosted/tokenized capture and have acquirer/qualified advisor determine actual merchant obligations |

Use these references to evaluate our original workflows and measured outcomes. Preserve licensed asset and implementation boundaries.

## Measurement protocol

Before implementation, record current hotel task baselines using the same role, data complexity and hardware/connectivity as candidate tests. Aim for at least five representative staff per core role and 20 matched repetitions per task distributed across at least two properties; report actual sample, failures, learning effects, median and p95. This is a practical initial study, not a statistically universal industry comparison. Increase sample if outcomes are uncertain. Separate routine tasks from exceptions; do not hide errors by excluding failed attempts. Use synthetic guests for recorded tests, consented staff participation and anonymized timing data.

Baseline task set: make/amend a reservation, check in a ready prepaid guest, resolve an unready room, settle/checkout a guest, record/refund/reconcile payment, assign cleaning, update/inspect a room and investigate a management exception. External ID checks and provider waits are timed separately and reported. Measure full end-to-end time as well as interface-only time.

## Proposed metrics, evidence and ownership

| ID | Target | Protocol / evidence | Delivery owner; reviewer |
| --- | --- | --- | --- |
| M01 | At least 30% lower median time for matched core tasks, without lower completion/safety | Before/after matched study; publish every task result, not only blended average | Codex; hotel operations reviewer |
| M02 | At least 95% unassisted task success; usability SUS target at least 80 | Scripted real-staff study and survey; disclose sample size | Codex; separate UX reviewer |
| M03 | Routine existing-reservation check-in median ≤90s; routine settlement/checkout ≤120s | Twenty matched repetitions/task; exclusions reported, full elapsed time also recorded | Codex; hotel supervisor |
| M04 | Housekeeping state update median ≤15s; committed readiness changes visible p95 ≤5s | Mobile task recordings plus server/browser timestamps under agreed network | Codex UI / Antigravity propagation as separate tasks; supervisor |
| M05 | Zero unintended cross-org/property disclosures or writes in adversarial suite | Two organizations, two properties each, every scoped API/file/export/job/cache path; privilege escalation and guessed-ID tests | Antigravity; separate security reviewer |
| M06 | Zero conflicting room allocations under tested concurrency | At least 100 simultaneous attempts at one room/date; amend/move/block races and process faults; invariants checked | Antigravity; separate backend reviewer |
| M07 | Exactly one monetary effect per accepted operation; zero unexplained reconciliation difference | ≥100 client/webhook replays, out-of-order events, lost responses, crash boundaries, provider settlement and cash close fixtures | Antigravity; finance + separate technical reviewer |
| M08 | p95 core read ≤500ms and durable write ≤1s; <0.5% unexpected error rate | Server-side timings, excluding external provider duration; 50 concurrent staff, 5 properties, 1,000 rooms, 100k reservations, 1m journal rows; 8h soak | Antigravity; performance reviewer |
| M09 | Core frontend LCP ≤2.5s at p75 on agreed representative device/network; reliable 360/768/1440px and 200% zoom | Browser traces and production field telemetry where available; lab results clearly labelled | Codex; separate frontend reviewer |
| M10 | Monthly critical-workflow availability objective 99.9% | Authenticated synthetic checks at 1min cadence plus incidents; 30-day month budget 43.2min, planned outages counted; provider dependency failures separately attributed and still shown in end-to-end availability | Antigravity; operations reviewer |
| M11 | RPO ≤15min; RTO ≤60min | Two witnessed timed restore drills to isolated environment, including files/keys/jobs; verify bookings, money and tenant scope | Antigravity; operations reviewer |
| M12 | WCAG 2.2 AA for scoped journeys; no unresolved critical/high security findings | Automated plus keyboard/screen-reader/zoom checks; ASVS mapping, dependency/config review and separate security assessment; scoped exceptions documented | Codex accessibility / Antigravity security; separate reviewers |
| M13 | Staff can complete ≥95% scripted core tasks after ≤60min role-specific training | Training trial with actual hotel staff; disclose previous familiarity | Codex training UX + hotel supervisor; operations reviewer |
| M14 | 100% of priority exceptions show source, owner, age, next action; acknowledgement ≤5min during staffed shifts | Replay late cleaning, unpaid departure, room failure, uncertain payment; staffed rota and audit metrics | Codex workspace / Antigravity event logic; manager |
| M15 | 14 consecutive staffed operational days across ≥2 real properties without unresolved critical safety defects | Daily inventory, cash/provider and business-day reconciliations; staff issue log; signed exit review | Antigravity rollout integration; owner + independent operational review |

These are bounded test claims, not promises of zero possible future defects. Performance and reliability targets are deliberate initial service objectives, not values inferred from marketing. The 99.9% objective is below Cloudbeds' advertised figure; improve only with evidence and viable operating cost. A short soak or pilot cannot prove a monthly production availability result.

Management reporting must define and reconcile occupancy, ADR and RevPAR with finance: proposed occupancy = occupied eligible room nights / sellable available room nights; ADR = earned room revenue / eligible occupied room nights; RevPAR = earned room revenue / sellable available room nights. Confirm treatment of complimentary stays, tax, cancellations, out-of-service inventory, business dates and currency before use. Booked value, collections and earned revenue stay separate. No forecasted revenue uplift is claimed.

## Gates and required evidence

| Gate | Exit requirement | Decision authority |
| --- | --- | --- |
| G0 Scope/feasibility | Launch-property/jurisdiction list; provider feasibility; approved financial policies; measured workflow baseline; owner-reviewed scope, capacity/cost estimate and architecture options | Project owner, informed by both teams and finance |
| G1 Foundations | Tenant/auth model and migrations; property-safe API contracts; 2-org fixtures; deployment/staging skeleton; property-switch UX; negative authorization tests; reviewed candidate | Separate technical/security review; owner accepts residual risks |
| G2 Reservations/front desk | Core lifecycle/room readiness/exception browser journeys; M06 concurrency; regression contracts and audit evidence | Separate backend/frontend review plus hotel supervisor |
| G3 Finance/payments | Golden ledger/invoice/night-close fixtures; M07; provider sandbox and authorized live smoke/settlement proof; accountant policy review; unknown-state/runbook behavior | Finance reviewer and separate technical review; owner approves live activation |
| G4 Housekeeping/management | Assignment/inspection/maintenance relocation; scoped reports/alerts; M04/M14; property-aware mobile and keyboard evidence | Hotel housekeeping/management reviewers and separate integration review |
| G5 Production qualification | M05–M12; migration rehearsal, independent assessment, backup drills, operational staffing, training and cutover/rollback review; no unresolved critical/high defects | Separate security/operations review; project owner final release decision |
| G6 Operational acceptance | M01–M04/M13/M15; completed reconciliations, known-issue disposition, support handover and expansion decision | Hotel operators/finance and project owner |

Each evidence packet records candidate commit, deployment/environment, fixture/suite version, actual commands/results, timestamps, artifacts, reviewer identity and decision. A builder cannot solely certify its own work. Proposed tests, mocks, model assertions, screenshots alone and a six-test prototype pass do not satisfy these gates. Real merchant tests require the applicable authorization and cannot be simulated into a live acceptance claim.
