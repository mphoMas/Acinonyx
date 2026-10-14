# Antigravity — GHA-03 Design Checkpoint Delivery

**Task**: GHA-03 — Authentication Gateway & Observation Ingestion Specification  
**Branch**: `feat/scrum-board-automation`  
**Implementation Owner**: Antigravity Development Team  
**Architecture Reviewer**: Codex  
**Date**: 14 October 2026  
**Status**: Design checkpoint submitted for Codex independent architectural review.  
**Baseline Commit**: `78ef1695` (incorporating `GHA_02_FINAL_ACCEPTANCE_REVIEW.md` and `ANTIGRAVITY_GHA_03_DESIGN_HANDOFF.md`)  

---

## 1. Executive Summary

In response to Codex's conditional acceptance of GHA-02 (`GHA_02_FINAL_ACCEPTANCE_REVIEW.md`) and the directive in [`ANTIGRAVITY_GHA_03_DESIGN_HANDOFF.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_HANDOFF.md), Antigravity has:

1. **Closed both GHA-02 nonblocking follow-ups**:
   - Replaced global `b"PK\x06\x06"` / `b"PK\x06\x07"` substring scanning with structural checks at legitimate record locations (ZIP64 locator immediately preceding EOCD, 64-bit central directory flags, and structural records in the gap between CD end and EOCD). Added regression tests verifying that ordinary STORED and DEFLATED member payloads containing `PK\x06\x06` or `PK\x06\x07` markers are accepted without false refusal, while real structural ZIP64 archives remain strictly rejected.
   - Corrected candidate commit metadata in [`GHA_02_DELIVERY.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_02_DELIVERY.md) to reference the immutable reviewed candidate `8968defb` without a self-referential amend loop.
2. **Delivered the complete GHA-03 Gateway Specification**:
   - Authored [`GHA_03_GATEWAY_DESIGN_V1.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_03_GATEWAY_DESIGN_V1.md) covering all five required design areas and resolving the conditions from [`GHA_01_REVISED_ACCEPTANCE_REVIEW.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_01_REVISED_ACCEPTANCE_REVIEW.md).
   - Updated the Authentication Gateway control in [`GITHUB_ACTIONS_ACCEPTANCE_MATRIX.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GITHUB_ACTIONS_ACCEPTANCE_MATRIX.md).
   - Formulated a 22-scenario executable acceptance test matrix (TC-01 through TC-22) for pre-implementation alignment.

---

## 2. GHA-03 Design Mechanism Summary

The full design is detailed in [`GHA_03_GATEWAY_DESIGN_V1.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_03_GATEWAY_DESIGN_V1.md). Below is the summary of how each requirement in the handoff brief is addressed:

### 1. GitHub OIDC Profile & Workflow Pinning
- **Reusable Workflow Profile**: Mandates `job_workflow_sha` matching the project's enrolled `approved_workflow_sha` (exact 40-character hexadecimal commit SHA).
- **Mutable Ref Rejection**: Tokens referencing mutable branch heads (`@refs/heads/*`) or release tags (`@refs/tags/*`) in `job_workflow_ref` are rejected as unpinned.
- **Repository Context Binding**: `repository_id` and `repository_owner_id` must match enrolled numeric IDs. Tokens from untrusted forks or foreign repositories are denied.

### 2. JWT Verification & Bounded JWKS Protocol
- **Allowed Algorithms**: Strictly asymmetric `RS256`. Rejects `none`, symmetric (`HS256`), and unapproved algorithms without JWKS lookup.
- **Bounded JWKS Cache**: GitHub JWKS endpoint cached for 24 hours. Payload size capped at 64 KiB. Unknown `kid` re-fetch throttled to at least 5-minute intervals to prevent cache-stampede DoS.
- **Temporal Enforcement**: Strict validation of `exp`, `nbf`, `iat` with clock skew tolerance capped at $\le 30$ seconds. Maximum token lifetime (`exp - iat`) capped at 15 minutes (900 seconds).
- **Replay Protection**: Ephemeral `jti` replay cache rejects replayed tokens within their validity window.

### 3. Server-Owned Identity Mapping & Strict Role Separation
- **Zero Client Role Selection**: Request headers and payload fields are untrusted data; they cannot choose or elevate principal, tenant, or role.
- **Witness vs. Builder Separation**: The GHA runner is mapped strictly to an ephemeral server-side principal (`gha-witness:<repo_id>:<run_id>`) with role `witness` (`delivery:witness_observe`). It **cannot** invoke `DeliveryService.submit()` or `accept()`.
- **Durable Revocation**: Enrolled tenant and project revocation states in `MultiTenantIAM` are verified prior to granting ephemeral witness sessions.

### 4. Bounded Schemas, Error Redaction & Zero Mutation on Failure
- **Bounded Ingestion Endpoint**: `POST /api/v1/delivery/observations` enforces 12 MiB maximum multipart request body, 1 MiB maximum manifest JSON, and 128 maximum observations.
- **Path & Archive Safety**: Reuses qualified `_validate_safe_member_path` and `validate_artifact_archive`.
- **Sanitized Error Responses**: Standardized JSON envelopes without leaking internal file paths, stack traces, database states, or credentials.
- **Zero-Mutation Invariant**: Authentication, claim matching, and pre-validation execute in a pure read-only phase. Any 4xx/5xx failure commits zero database writes; task phase and revision remain untouched.

### 5. Transactional State Boundaries & Deferred Increments
- **GHA-03 Scope**: Owns OIDC JWT/JWKS verification library, server-side project mapping, ephemeral witness session management, and observation ingestion without phase mutation.
- **GHA-04 Scope (Deferred)**: Monotonic generation ordering, PR-head race prevention, and idempotency ledger (`pm_source_events`).
- **GHA-05 Scope (Deferred)**: GitHub Checks API publisher emitting `success` strictly on verified `ACCEPTED` states (never `neutral`/`skipped` on required checks).

---

## 3. Pre-Implementation Executable Acceptance Matrix

The 22 executable acceptance scenarios defined in [`GHA_03_GATEWAY_DESIGN_V1.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_03_GATEWAY_DESIGN_V1.md) (TC-01 through TC-22) will be implemented as unit and integration tests in `tests/test_gha_gateway_integration.py` once this design checkpoint is approved:

| Category | Test Scenarios | Expected Outcome |
|---|---|---|
| **JWT / JWKS Failures** | TC-01: Wrong Issuer (`iss`)<br>TC-02: Wrong Audience (`aud`)<br>TC-03: `alg: none`<br>TC-04: Symmetric Algorithm (`HS256`)<br>TC-05: Corrupted Signature<br>TC-06: Expired Token<br>TC-07: Future Token (`nbf`)<br>TC-08: Token Issued in Future (`iat`)<br>TC-09: Lifetime $> 15$m<br>TC-10: Token Replay (`jti`)<br>TC-11: Unknown `kid` Throttling<br>TC-12: JWKS Network / 500 Outage | HTTP 401 / 503; zero DB mutation; task phase unchanged |
| **Claim & Policy Violations** | TC-13: Unenrolled Repository ID<br>TC-14: Owner ID Mismatch<br>TC-15: Mutable Workflow Ref (`@refs/heads/*`)<br>TC-16: Unapproved Workflow Commit SHA<br>TC-17: Disallowed GitHub Event | HTTP 403; zero DB mutation; task phase unchanged |
| **Role & Security Boundaries** | TC-18: Request Body Role Spoofing Ignored<br>TC-19: Witness Principal Denied `submit()`<br>TC-20: Revoked Tenant Rejected | Client claims ignored; 403 on privileged calls; zero state mutation |
| **Payload & Ingestion** | TC-21: Oversized Request Body ($> 12$ MiB)<br>TC-22: Valid Observation Submission | TC-21: 413 Payload Too Large<br>TC-22: 200 Ingestion Receipt (task phase unchanged) |

---

## 4. Governance & Verification Commitments

1. **Design Agreement Required**: Antigravity will not implement state-changing endpoints, database schema changes, or live gateway listeners prior to Codex agreement on this design.
2. **Gated Scope (GHA-04 through GHA-07)**:
   - Live GitHub Actions workflows (`.github/workflows/*.yml`) remain disabled.
   - Public OIDC endpoints and external network dispatch remain unconfigured.
   - Worker registry remains synthetic-only.
   - Core delivery database schema and `mas/pm/delivery.py` remain strictly unmodified.
3. **Receipt Traceability**: GHA-02 targeted suites (30 tests in `tests/test_gha_delivery_integration.py` and 47 tests in `tests/test_delivery_process_gates.py`) continue to pass 77/77 with the structural ZIP64 follow-up.
