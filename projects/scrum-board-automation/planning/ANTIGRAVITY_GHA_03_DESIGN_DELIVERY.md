# Antigravity — GHA-03 Design Checkpoint Delivery (Revised)

**Task**: GHA-03 — Authentication Gateway & Observation Ingestion Specification
**Branch**: `feat/scrum-board-automation`
**Implementation Owner**: Antigravity Development Team
**Architecture Reviewer**: Codex
**Date**: 14 October 2026
**Status**: Revised design checkpoint submitted for Codex independent architectural review.
**Reviewed Candidate**: `54cc7916`
**Review Documents**:
- [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_REWORK_BRIEF.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_REWORK_BRIEF.md)
- [`projects/scrum-board-automation/planning/GHA_03_DESIGN_REVIEW.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_03_DESIGN_REVIEW.md)
**Baseline Commit**: `334a1227`

---

## 1. Executive Summary & Review Rework Summary

In response to Codex's design review (`GHA_03_DESIGN_REVIEW.md`) and explicit rework instructions (`ANTIGRAVITY_GHA_03_DESIGN_REWORK_BRIEF.md`), Antigravity has revised the GHA-03 Gateway and Observation Ingestion design specification:

1. **Selected the Offline Observation Validator Slice**:
   - The gateway operates strictly as an offline validator returning a typed `WitnessObservationValidationResponse` with `status: "VALIDATED_UNTRUSTED_OBSERVATION"`, `transport_authenticated: true`, and `authority_verified: false`.
   - Generates **zero database writes** to `pm_delivery_tasks`, `pm_delivery_submissions`, or coordinator state tables.
   - Persistent ingestion, durable receipt store (`pm_security_tokens`), and PR-head freshness tracking are formally deferred to GHA-04 alongside the transactional idempotency ledger (`pm_source_events`).
2. **Enforced Reusable-Workflow, Witness-Only Profile**:
   - Completely removed direct admin workflow execution.
   - Pinned exact approved workflow repository, path, and 40-character commit SHA (`job_workflow_sha` and `job_workflow_ref`).
   - Bound allowlisted execution conditions (`event_name`, `ref`, and `runner_environment`).
   - Separated GitHub transport coordinates (`run_id`, `run_attempt`) from coordinator execution coordinates (`run_id`, `intent_id`, `attempt_id`).
   - Documented that workflow pinning does not prove candidate identity or PR head freshness; all CI uploads remain untrusted observations only.
3. **Hardened Cryptographic Verification & JWKS Lifecycle**:
   - Bounded JWT length to 8192 bytes.
   - Header inspection permits strictly `alg: "RS256"` and non-empty `kid` $\le 128$ chars; rejects duplicate header keys and extraneous parameters (e.g. `jku`, `x5u`).
   - Strictly positive lifetime (`exp > iat`), maximum lifetime $\le 900$s, maximum token age (`now - iat <= 900`s), and bounded clock skew ($\le 30$s).
   - Fixed JWKS endpoint (`https://token.actions.githubusercontent.com/.well-known/jwks`) with zero redirects followed (`max_redirects = 0`), 64 KiB buffer cap, RSA modulus $\ge 2048$ bits, 24h cache TTL, single-flight refresh, $\ge 5$ min unknown-`kid` cool-down, and fail-closed (503) on outage.
4. **Mapped Identity to Real `MultiTenantIAM` APIs**:
   - Server-owned `GitHubConnectorConfig` resolves `(repository_id, repository_owner_id)` to tenant and project.
   - Calls real `iam.get_tenant(config.tenant_id)` to verify active status (`TenantStatus.ACTIVE`); rejects suspended or missing tenants with 403 `TENANT_REVOKED`. No fictitious project-revocation APIs are invented.
   - Ephemeral per-request `witness` context (`delivery:witness_observe`); no persistent sessions or bearer tokens are minted.
   - Delivery action ownership aligned with `mas/pm/delivery.py`: `builder` challenges findings, `reviewer` resolves challenges.
5. **Standardized Request/Response & Strict Field Validation**:
   - Single request format: `application/json`.
   - Bounded request model binds `DeliveryManifest`, inline base64 artifact archive (passing GHA-02 zip validation), and fencing token.
   - Extraneous fields (e.g. client-supplied `role`, `tenant_id`, `actor`) trigger immediate validation error (422/400 `EXTRA_FIELDS_FORBIDDEN`) via `StrictModel(extra="forbid")`, never silent filtering.
6. **Formulated Pre-Implementation Test Specification**:
   - Clarified that the 22 acceptance scenarios (TC-01 to TC-22) constitute the formal specification plan for GHA-03, not claimed as already executed runtime tests.

---

## 2. Review Finding Closure Table

| Review Finding / Directive | Revised Design Section | Accountable Component | Negative Test Scenario & Expected Outcome |
|---|---|---|---|
| **Finding 1 (High): Undefined replay/receipt transaction** | `GHA_03_GATEWAY_DESIGN_V1.md` § 1.2, § 6.1, § 6.2 | `GatewayAdmissionEngine`<br>`GHA03Validator` | Offline validator slice selected; zero DB mutation; durable security receipt store and idempotency ledger deferred to GHA-04. (TC-22: 200 OK with zero DB writes). |
| **Finding 2 (High): Incomplete workflow & authorization profile** | `GHA_03_GATEWAY_DESIGN_V1.md` § 2.1, § 2.2, § 2.3 | `OIDCClaimValidator`<br>`ServerIdentityResolver` | Direct admin workflow removed; reusable-workflow witness-only profile; repo/path/SHA pinning; event/ref/env allowlists; GitHub coordinates separated from MAS runs; CI claims are untrusted observations. (TC-15, TC-16, TC-17: 403 Forbidden). |
| **Finding 3 (Medium): Token age & JWKS lifecycle gaps** | `GHA_03_GATEWAY_DESIGN_V1.md` § 3.1, § 3.2, § 3.3 | `JWKSClient`<br>`TokenParser` | Max JWT 8192 bytes; duplicate/extra headers forbidden; strictly `RS256`; `exp > iat`; lifetime $\le 900$s; token age $\le 900$s; clock skew $\le 30$s; fixed JWKS URL with 0 redirects; 64 KiB cap; RSA modulus $\ge 2048$ bits; 24h TTL; single-flight refresh; $\ge 5$ min cool-down; fail-closed 503. (TC-03 through TC-12). |
| **Finding 4 (Medium): IAM & request contracts mapping** | `GHA_03_GATEWAY_DESIGN_V1.md` § 4.1, § 4.2, § 5.1, § 5.2 | `ServerIdentityResolver`<br>`ObservationSubmissionSchema` | Server-owned `GitHubConnectorConfig`; real `iam.get_tenant()` active status check; ephemeral witness context; delivery action alignment (builder challenges); single JSON format with `DeliveryManifest` coordinates; extra fields rejected. (TC-13, TC-14, TC-18, TC-19, TC-20). |

---

## 3. Revised Document Deliverables

The revised design package consists of:
1. [`projects/scrum-board-automation/planning/GHA_03_GATEWAY_DESIGN_V1.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_03_GATEWAY_DESIGN_V1.md) — Comprehensive technical design specification.
2. [`projects/scrum-board-automation/planning/GITHUB_ACTIONS_ACCEPTANCE_MATRIX.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GITHUB_ACTIONS_ACCEPTANCE_MATRIX.md) — Updated Authentication Gateway control row reflecting the offline validator mechanism.
3. [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_DELIVERY.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_DELIVERY.md) — This revised delivery handoff document.

---

## 4. Verification & Scope Commitments

1. **Design-Only Checkpoint**: No gateway implementation code, public HTTP endpoints, or live workflow activations have been added. No coordinator database schema migrations have been performed.
2. **GHA-02 Verification Intact**: All 77 targeted GHA-02 process and integration tests pass cleanly:
   - `tests/test_gha_delivery_integration.py` (30 passed)
   - `tests/test_delivery_process_gates.py` (47 passed)
3. **Execution Plan**: Upon Codex architectural review approval of this revised design, Antigravity will proceed with Step 2 (implementing the offline OIDC/JWKS gateway engine and the 22 acceptance tests in `tests/test_gha_gateway_integration.py`).
