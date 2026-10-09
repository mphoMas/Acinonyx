# Discovery decision register

Opened 9 October 2026. Updated 9 October 2026 with Project Owner determinations for DEC01, DEC03, and DEC04.

| ID | Decision | Accountable decision maker / technical preparer | Needed by | Status | Resolved Policy / Starting Position |
| --- | --- | --- | --- | --- | --- |
| DEC01 | Launch organizations, properties and operating countries | Project owner / Codex discovery | G0 | **RESOLVED** | Organization: Platinum Hotels; Properties: Platinum Hotel 01 (Maputo) & Platinum Hotel 02 (Matola); Country: Mozambique (`MZ`), Currency: `MZN`. |
| DEC02 | Required incumbent systems, channels and migration sources | Project owner + hotel manager / Antigravity | G0 | PENDING | Standalone launch first; OTA channels/PMS imports scoped as post-launch adapters unless required by pilot staff. |
| DEC03 | Tax, invoice, business-day, guest-registration and privacy rules | Project owner with accountant/legal advisor / Antigravity | G0 | **RESOLVED** | Mozambique IVA 16% standard VAT; sequential Fatura/Recibo numbering in PT/EN; Passport/BI recording for guest compliance. |
| DEC04 | Payment provider, merchant accounts, currencies and payout/terminal support | Project owner / Antigravity | G0 | **RESOLVED** | DPO Group / Peach Payments Mozambique aggregator: M-Pesa (Vodacom MZ), e-Mola (Movitel MZ), Visa/Mastercard (3DS hosted), plus cash/POS slips. |
| DEC05 | Cancellation, deposits, refunds, approvals and credit balances | Project owner + hotel finance / Antigravity | G0 | PENDING | Standard deposit required at booking; refundable up to 48h prior to check-in; supervisor role required for refunds. |
| DEC06 | Database, hosting, identity and jobs architecture | Antigravity technical lead / separate technical reviewer | G0 | **PROPOSED** | Modular Node 24 application; TypeScript; managed transactional PostgreSQL 16; PgBouncer connection pool; transactional outbox for webhooks. |
| DEC07 | Capacity, budget, target date and provider/infra procurement | Project owner / both teams estimate | G0 | **PROPOSED** | 14–20 week phased delivery; pilot infra ~$310/mo; reforecast at G1 exit. |
| DEC08 | Cross-property guest sharing and portfolio permissions | Project owner with privacy advisor / Antigravity + Codex | G1 | PENDING | Strict property isolation by default; explicit organization-level guest profile lookup with consent audit. |
| DEC09 | Brand, imagery and language coverage | Project owner / Codex | G1 | PENDING | Evolve forest-green/cream identity; licensed/owned assets; dual Portuguese (PT) & English (EN) core journeys. |
| DEC10 | Support hours, incident rota and cutover authority | Project owner / Antigravity operations | Before G5 | PENDING | Operational shift coverage; hotel manager on-call escalation; no unsupported 24/7 claims. |
| DEC11 | Shared MAS-PM instance and real executor/reviewer identities | Authorized PM administrator / Antigravity with Codex | Before staging | IN PROGRESS | Local PM instance synchronized; coordination tickets bound; token allowances to be authorized per work package. |

## Current readiness

- **DEC01, DEC03, DEC04 Resolved:** Pilot properties (Platinum Hotel 01 & 02), jurisdiction (Mozambique, MZN, IVA 16%), and payment aggregator (DPO / Peach Payments: M-Pesa, e-Mola, Cards) confirmed by project owner in [`evidence/d1-launch-scope-decision.md`](evidence/d1-launch-scope-decision.md).
- **Backend Architecture & Discovery (PLG-BE-01):** Detailed in [`BACKEND_DISCOVERY.md`](BACKEND_DISCOVERY.md).
- **Gate G0 Progression:** Critical statutory and payment blockers cleared; awaiting final confirmation on DEC02/DEC05 to pass Gate G0.
- **Next Staged Implementation:** Foundations package (PLG-3 / F1 & F2) ready for schema migration and API contract authoring.
