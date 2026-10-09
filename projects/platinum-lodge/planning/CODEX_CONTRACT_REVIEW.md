# Codex review of Antigravity backend discovery

9 October 2026. Reviewed BACKEND_DISCOVERY.md at Antigravity commit 5e96bf95. This is frontend/architecture review, not independent backend qualification or joint contract approval. Implementation remains governed by DELIVERY_OWNERSHIP.md with the owner-confirmed implementation split.

## Outcome

The modular Node/TypeScript/PostgreSQL direction is a reasonable candidate. Do not treat the endpoint summary as an implementable contract yet. Resolve the following before PLG-20 / PLG-CONTRACT-01 can be accepted.

| Issue | Required clarification / correction | Owner |
|---|---|---|
| Launch assumptions | Mozambique confirmed; Excel baseline confirmed. Remove reliance on unconfirmed jurisdictions/providers. Owner selected Platinum Hotel as the sole initial pilot; room inventory and required integrations remain unresolved. Multi-property technical qualification remains required. | Owner + both teams |
| PCI claim | Hosted/tokenized collection alone does not establish SAQ A eligibility. Embedded forms and provider integration affect scope; merchant/acquirer must determine eligibility. Stripe Elements and hosted redirect must not be treated as interchangeable compliance evidence. | Antigravity + merchant/acquirer |
| Provider feasibility/fees | Stripe/Adyen examples and 2.9% + 30 cents are not verified Mozambique eligibility, settlement support or a cost quote. Confirm local merchant eligibility, currencies, refunds and payout reports. | Antigravity + owner |
| Payment lifecycle | Define partial capture/refund, reversal, failure, expired authorization and unknown outcomes. Separate recorded cash/bank tender from provider initiation and refund commands; generic payments endpoint currently conflates them. Expose operation lookup/reconciliation by original reference. | Antigravity; Codex reviews UI |
| Webhook signatures | Verification is provider-specific, not universally HMAC-SHA256. Specify raw-body handling, timestamp/replay policy, event identity, ordering and reconciliation after missing callbacks. | Antigravity |
| Mutable operation contract | Specify If-Match/ETag semantics, missing/stale preconditions, conflict error fields, idempotency scope/lifetime/body mismatch and recovery after lost acknowledgements. Do not require an idempotency key on a read request. | Antigravity + Codex |
| Schema and errors | Publish full request/response schemas, capabilities, pagination, nullability, safe field errors and correlation IDs. Membership response must represent identity expiry/revocation and permitted property contexts. No credentials or PII in client errors. | Antigravity |
| Tenant model | Legal entity and portfolio/organization are not necessarily the same thing. Clarify ownership relationships, scoped foreign keys, global reference tables and organization-only resources. 'Every table has both IDs' is too broad without a schema. | Antigravity + finance/privacy |
| Inventory locks | Name actual rows/ranges locked and transaction boundary; a date range cannot itself be row-locked. Cover unallocated room-type bookings, maintenance, cancellation, amendments and lock ordering. The 100-last-room race is necessary but not sufficient. | Antigravity |
| Business day/ledger | Distinguish ledger account debits/credits from guest folio presentation. Specify currency precision, tax rounding, invariant checks, closing permissions, late postings and restart checkpoints. Verify actual Mozambique invoice requirements rather than assuming gap-free numbering. | Antigravity + accountant |
| Room state | Separate cleaning, inspection and availability, with explicit permissions/transitions. Generic PATCH state must not let cleaners approve their own inspection or force readiness through maintenance blocks. | Antigravity + operations; Codex reviews UX |
| Management data | Define Today exceptions, assigned owner, source timestamp, staleness, next action and portfolio KPIs. The proposed endpoint list currently omits these contracts and reservation list/calendar, checkout, cancellations and shift reconciliation. | Antigravity + Codex |
| Estimate confidence | Staffing, 100 rooms, cloud choice, ~$310/month and timeline remain assumptions, not funded capacity or a validated quote. Include HA, backups, egress, support, security, provider and staging costs; reforecast at gates. | Both teams + owner |

## Required next contract packet

Supply versioned OpenAPI with representative authorized, denied, empty, stale/conflict, pending/unknown fixtures; explicit server-enforced permissions; operation status lookup; property business-date/timezone semantics; and staging access. Agree a compatibility policy and frontend integration owner. Codex will implement frontend adapters/workflows against that agreed packet and report actual candidate-bound checks. No API, ledger or migration implementation is changed by this review.
