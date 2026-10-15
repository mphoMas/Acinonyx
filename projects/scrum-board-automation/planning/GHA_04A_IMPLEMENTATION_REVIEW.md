# Independent GHA-04A implementation review

Candidate **4e050879**. **REJECTED (REQUIRES RE-WORK)** for runtime acceptance. The small receipt slice remains the agreed scope; no return to the rejected broad GHA-04 design is requested.

## 1. Executive assessment

The supported receipt service, composite ownership, replacement guards, idempotency and crash tests are implemented. **156 targeted tests passed in 8.94 seconds**. Independent probes nonetheless violate existing current-access and strict-input requirements. Correct those mechanisms without adding PR freshness, artifact storage or durable token replay.

## 2. Reproduced blockers

### B1 — Connector authority depends on optional client claims (high)

Set configured connector `(100,200)` to REVOKED generation2. Submit through `DeliveryReceiptService(db, registry)`, removing `repository_owner_id` from payload transport claims. The service returns CREATED. The check executes only when a registry, transport_claims, repository_id AND repository_owner_id are present. Omitting one field selects a path without connector checks. `get_receipt` receives no registry at all, so it also cannot enforce the promised connector revocation for reads.

Required: configure the receipt service's connector identity server-side and bind its tenant/project. Client metadata remains claims and must not enable/disable authorization. If local nonconnector callers are allowed, make that a separate explicit trusted service profile; never silently select it from missing input. Check current configured connector for both read/write under the guard. Add omitted/changed claims, wrong tenant/project connector, revoked/removed connector and historical-read denial cases.

### B2 — Credentials can expire between preflight and guarded operation (high)

Using a controlled clock, advance time beyond the verified identity's expires_at when entering the authority guard. `record_observation` returns CREATED. The guarded block checks tenant/principal status and session revoked flag but does not repeat expiration or complete authorization. The read path repeats this partial manual logic.

Required: perform the supported full fresh authorization check INSIDE the authority guard for each read/write, including credential/session expiry, principal/current roles/scopes and storage binding. Avoid two separately maintained partial lifecycle checks. Wire every supported authority-changing API (including principal re-registration/permission changes) into the declared lock profile. Test guard-wait expiry and permission changes at actual guarded boundaries. Do not weaken existing IAM verification or accept constructed contexts.

### B3 — Contract/payload validation is permissive rather than frozen schema (high)

Contract `{schema_version: true, claims: {}, check_ids:[...] , unapproved_field:...}` and payload with boolean version, missing transport/MAS claims and unknown item fields return CREATED. `True == 1` passes version checks. Required claim shapes, SHA/digest formats, identifier/limitations limits and extra-field rejection are not enforced.

Required: exact strict versioned contract/payload models consistent with the reference contract, including required claim coordinates, optional explicitly nullable source_generation and artifact digest-claim shape. Forbid unknown fields recursively, booleans for integers, malformed hashes and invalid types. Preserve sorted unique check subset INCLUDING equality and combined1MiB/128items/64artifact limits. Test each entry through supported record interface, no rows on refusal. They are untrusted claims, not schema-free data.

## 3. Evidence correction

Submission claims quality-gate stages Xenon/Radon, Pyright, coverage and Bandit. The actual unchanged `scripts/run_quality_gate.sh` stages are Ruff, doctor/capabilities, research assets/links, compilation and full pytest. Correct the delivery evidence; separately executed tools must have their own receipts. This mismatch does not prove reported tests false.

Private probes: `/workspace/review-evidence/gha04a/probe.py`, `probes.json`, `targeted.log`; sentinel-free disposable data. No full gate/wheel independently repeated after blockers were established. Author reports remain separate evidence. Receipt labels correctly stay authority_verified=false; probes did not mutate delivery phases or prove verified work acceptance.

## 4. Pillars and directive

Platform: real local persistence/recovery exists. Data: core ownership/idempotency mechanisms are retained, strict schemas need closure. AI: observations remain untrusted. Governance: server-owned connector authorization and fresh guarded credential checks are mandatory.

1. Fix B1–B3 across read/write and input routes, retaining existing recovery/immutability tests.
2. Correct evidence descriptions; add closure matrix and new negative checks before submission.
3. Run final targeted/full gate and isolated installed-wheel checks on final candidate.
4. Submit for independent acceptance. No live listener/workflow/provider activation, receipt-based approval, business phase/budget changes, artifact file lifecycle or PR freshness work.
