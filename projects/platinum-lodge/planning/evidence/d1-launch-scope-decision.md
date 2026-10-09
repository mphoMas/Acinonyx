# Platinum Lodge: Launch Scope & Discovery Decision Record (D1 / DEC01–DEC04)

**Decision Date:** 9 October 2026  
**Decision Authority:** Project Owner  
**Recorded By:** Antigravity Development Team  
**Related Work Packages:** PLG-11 (D1), PLG-13 (D3), PLG-14 (D4), PLG-15 (D5)  
**Related Decisions:** DEC01, DEC03, DEC04  

---

## 1. Organization & Multi-Property Structure (DEC01)

* **Parent Organization:** `Platinum Hotels` (`org_platinum_hotels_mz`)
* **Pilot Properties:**
  1. **Platinum Hotel 01** (`prop_platinum_01`)
     - Role: Primary full-service hotel & lodge
     - Timezone: `Africa/Maputo` (UTC+2, no daylight saving time shifts)
     - Default Currency: `MZN` (Mozambican Metical)
  2. **Platinum Hotel 02** (`prop_platinum_02`)
     - Role: Secondary branch / boutique chalets
     - Timezone: `Africa/Maputo` (UTC+2)
     - Default Currency: `MZN` (Mozambican Metical)

---

## 2. Jurisdiction, Statutory Tax & Regulatory Context (DEC03)

* **Operating Country:** Mozambique (`MZ`)
* **Legal Currency:** Mozambican Metical (`MZN`)
  - Subunits: 100 Centavos (integer minor units in database, exponent 2: 1,500.00 MZN = `150000`).
* **Taxation (IVA):**
  - Standard Value-Added Tax (IVA) in Mozambique is **16%**.
  - All room accommodation and on-site charges apply standard 16% IVA unless an explicit statutory exemption is flagged.
  - Folio invoices require itemized subtotal (base tributável), IVA amount, and total.
* **Invoicing Standards:**
  - Sequential, gap-free legal invoice numbering (`Fatura / Recibo`).
  - Dual language support on generated receipts: Portuguese (`PT`) primary, English (`EN`) secondary.
* **Guest Registration & Compliance:**
  - Mandatory collection of guest legal identification: Passport for foreign guests, *Bilhete de Identidade* (BI) or *DIRE* for domestic residents.

---

## 3. Payment Processing Architecture & Provider Selection (DEC04)

* **Selected Regional Hosted Aggregator:** **DPO Group / Peach Payments (Mozambique)**
  - Why: Operates natively in Mozambique with direct gateway connectivity for both international card schemes and domestic mobile money rails under a unified hosted tokenized checkout.
* **Supported Payment Methods:**
  1. **M-Pesa:** Vodacom Mozambique mobile money API integration.
  2. **e-Mola:** Movitel Mozambique mobile money API integration.
  3. **Credit / Debit Cards:** Visa & Mastercard via hosted 3D Secure 2.0 page (ensuring zero PAN/CVV storage on PMS servers, maintaining PCI DSS SAQ A eligibility).
  4. **Front-Desk Manual Tenders:** Cash (`MZN`), bank wire transfer, and physical card POS swipe receipts with mandatory reference/slip capture.
* **Idempotency & Webhooks:**
  - Scoped transaction idempotency keys: `(property_id, folio_id, operation_id)`.
  - Cryptographic HMAC-SHA256 signature verification on M-Pesa, e-Mola, and card webhook notifications.
  - Replay protection store prevents duplicate journal credits.

---

## 4. Status on Gates and Next Actions

* **DEC01:** **RESOLVED** (Platinum Hotel 01 & 02, Mozambique, MZN).
* **DEC03:** **RESOLVED** (Mozambique IVA 16%, PT/EN Fatura/Recibo, BI/Passport).
* **DEC04:** **RESOLVED** (DPO/Peach Payments aggregator: M-Pesa, e-Mola, Cards).
* **Unblocks:** `PLG-13` (D3), `PLG-14` (D4), and `PLG-15` (D5) backend specifications.
