# GHA-03 revised design acceptance

Candidate: **25558aa0**. Status: **APPROVED WITH CONDITIONS** for implementing a local, stateless, witness-only authentication and observation validator. This is design agreement, not acceptance of gateway code, durable ingestion or live deployment.

## Executive assessment

The revised slice removes the unresolved receipt/replay transaction from GHA-03, specifies reusable-workflow pinning and untrusted-result labels, and defines token lifetime/age and cache expiry. These resolve the prior design blockers for this smaller scope. Durable replay/ingestion remain GHA-04 obligations; repeated valid tokens may validate repeatedly in GHA-03 and must never be advertised as replay-protected.

## Binding implementation conditions

Treat these as shared acceptance requirements before coding, not requirements first introduced during final code review:

1. **Token parsing and identity:** Require strict types and required claims, rejecting duplicate payload keys as well as header keys, nonfinite numbers and booleans for NumericDates. Exactly three bounded base64url JWT segments; real RS256 signature verification. Compare request `github_run_id` and `github_run_attempt` to authenticated token claims, with explicit canonical conversion of GitHub's digit-string attempt to an integer. Preserve the distinction from MAS coordinates. Test mismatches and missing claims.
2. **Request limits:** Define maximum encoded request bytes and decoded archive bytes independently. Sixteen MiB of base64 alone plus manifest/envelope exceeds a sixteen-MiB total request allowance. Choose a documented total bound (for example 18 MiB), retaining 1 MiB manifest, 16 MiB base64 and 12 MiB decoded archive caps; reject during bounded collection. Strict base64 decoding. If observations reference artifact bytes, the archive is required and every reference/digest must match via actual `validate_artifact_archive(..., observations=...)`. Without bytes, do not return the same fully artifact-validated success label. Call the existing function, not nonexistent `validate_artifact_zip`.
3. **Witness context:** A constructed TenantContext is an internal restricted validation context only, not a valid IAM bearer/session or authority to enter privileged tenant storage. Never expose it as a token or mint grants. No DeliveryService mutation calls, trusted-admin scope, database initialization or migration. Current tenant and connector status/generation must be rechecked at validation completion to detect revocation during slow JWKS/artifact processing; repeated validation is still not durable revocation assurance or commit authorization.
4. **JWKS:** Explicit equality boundaries for TTL/cooldown; cold-cache fetch behavior; one shared refresh; failed fetch cooldown to prevent repeated outage requests. Bound streamed response before JSON parse, key count and RSA parameter size (minimum strength and finite maximum size), duplicate key IDs and inappropriate key metadata. Use a fixed TLS-verified endpoint without redirects/token-controlled URLs. Inject a clock/fetcher for deterministic tests, but exercise actual crypto. The optional network client may fetch JWKS only; offline tests must not call GitHub.
5. **Scope and output:** Manifest tenant/project equality is binding, but MAS run completion, candidate freshness and trusted verification are not proven by this structural-only slice. Report `transport_authenticated=true`, `authority_verified=false`, explicit structural/artifact-validation coverage, and no receipt or admission/acceptance claim. Security logs must redact bearer tokens, secrets and raw bodies; any configured audit failure policy is explicit.
6. **Correct action ownership:** Current `DeliveryService.resolve_challenge` uses coordinator role and `delivery:coordinate`; `challenge` uses builder and `delivery:submit`. The design's reviewer-resolution table is inaccurate. My previous guidance also incorrectly suggested reviewer resolution; this review corrects that guidance. Do not change core roles to make documentation pass. The gateway needs no challenge authority.
7. **Specification consistency:** Correct TC-10: a token older than 900 seconds cannot simultaneously satisfy a lifetime <=900 seconds and unexpired future exp. Test age in isolation or define deterministic failure precedence. Align event-specific ref allowlists with the actual config model; a single default PR regex does not represent both PR and workflow_dispatch policies.

## Evidence and pillars

Only three documentation files changed from `334a1227`; no gateway implementation exists. Reviewed the revised mechanism against current `TenantContext`, `DeliveryService` action ownership and GHA-02 APIs. Author-reported 77 targeted tests cover existing delivery code, not the proposed gateway; no new runtime test result is claimed by this design review.

- Platform: bounded local engine is feasible; public networking and service operations are excluded.
- Data: transport coordinates and structural claims must remain distinguishable from authoritative completed execution.
- AI: no witness upload can manufacture verifier/reviewer evidence or approval.
- Governance: witness-only restrictions, independent code review and no durable replay claim remain mandatory.

## Action directive

Antigravity may implement this bounded slice after incorporating the conditions into the mechanism/matrix. Keep tests shared and name any deviation before implementing it. Submit actual failure evidence, full gate and isolated-wheel checks on the final candidate. No public endpoint, production credentials, live Actions workflow, operational enrollment, provider dispatch or schema/core-delivery change is released by this agreement.
