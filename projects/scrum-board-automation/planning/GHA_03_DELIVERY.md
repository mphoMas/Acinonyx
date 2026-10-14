# Delivery Evidence and Handoff: Task GHA-03 (Local Gateway & Witness Validator Rework 1)

Task: **GHA-03 — Authentication Gateway, Witness Token Verification, and Observation Validator**
Branch: `feat/scrum-board-automation`
Implementation Owner: Antigravity Development Team
Architecture Reviewer: Codex
Date: 14 October 2026
Baseline Design Review: `f84225e1` (`GHA_03_IMPLEMENTATION_REVIEW.md` and `ANTIGRAVITY_GHA_03_IMPLEMENTATION_REWORK_BRIEF.md`)
Status: Implemented and locally verified for offline witness observation scope following independent implementation review. Submitted for independent architectural review and verification by Codex.

---

## 1. Executive Summary & Review Findings Closure

Following Codex's independent implementation review of candidate `025bede6` (`GHA_03_IMPLEMENTATION_REVIEW.md`) and the rework directive (`ANTIGRAVITY_GHA_03_IMPLEMENTATION_REWORK_BRIEF.md`), Antigravity has resolved all four findings (B1, B2, B3, and B4) without expanding beyond the approved boundary.

### Architectural Boundary & Guarantees
- **Local & Offline**: Zero network listeners, zero exposed HTTP ports, and zero outbound network calls during test suites.
- **Witness-Only Observation**: The gateway produces strictly `status="VALIDATED_UNTRUSTED_OBSERVATION"` with `authority_verified=False`. It cannot transition tasks to `IN_REVIEW`, cannot submit formal verifier/reviewer evidence, cannot challenge findings, cannot resolve disputes, and cannot self-approve work.
- **Stateless & Immutable**: Zero database mutations (`DeliveryService`, `CoordinatorStore`, and SQLite schema remain untouched). Persistent receipts, token exchange, and durable replay caches are explicitly deferred to GHA-04.
- **Ephemeral Security Context**: Operates inside an ephemeral `TenantContext` bounded to `delivery:witness_observe`. Constructed `TenantContext` is an internal ephemeral data structure, not an IAM bearer or session token, and provides no bypass of delivery gates.

---

### Implementation Review Findings Closure Summary

| Finding ID & Summary | Root Cause in Candidate `025bede6` | Architectural Resolution in Rework 1 | Verified Tests |
|---|---|---|---|
| **B1: Connector revocation recheck uses stale object** | Completion check tested the locally retained frozen object `connector_config.status` looked up at step 4, rather than re-resolving the current registry entry. Removal, replacement, generation increment, or authority configuration mutations were completely ignored. | Introduced `ConnectorRegistry` synchronized via `threading.RLock`. Validator snapshots initial coordinates, generation, and authority fields (`tenant_id`, `project_id`, `approved_workflow_sha`, `approved_workflow_path`, `approved_workflow_repo`, `required_runner_env`). At validation completion (Step 10), re-resolves current connector entry from registry: rejects removal (`CONNECTOR_REMOVED`, 403), revocation (`CONNECTOR_REVOKED`, 403), generation change (`CONNECTOR_GENERATION_CHANGED`, 403), and authority field mutation (`CONNECTOR_AUTHORITY_CHANGED`, 403). Added `on_validation_stage` hook for deterministic mid-validation concurrency testing. | `test_rework_b1_connector_replacement_during_artifact_validation_rejected`, `test_rework_b1_connector_removal_during_artifact_validation_rejected`, `test_rework_b1_connector_generation_change_during_validation_rejected`, `test_rework_b1_connector_authority_change_during_validation_rejected`, `test_connector_registry_thread_safe_operations` |
| **B2: Manifest and dictionary request bounds are not enforced** | `_parse_request_input` returned `dict` directly without envelope bounds; `WitnessObservationSubmissionRequest` did not enforce the 1 MiB `MAX_MANIFEST_JSON_SIZE` limit on the nested manifest, allowing a 2 MiB closure path (2,097,866 bytes) to bypass admission. | Enforced 18 MiB envelope limit across bytes, str, and dict representations using bounded streaming accounting (`json.JSONEncoder().iterencode(data)`). Enforced 1 MiB nested manifest limit on all inputs before and during schema parsing via `@field_validator("manifest", mode="before")` on `WitnessObservationSubmissionRequest` and pre-validation bounded scan. Retained separate 16 MiB base64 and 12 MiB decoded caps. Tested reproduced 2 MiB closure path on dict and JSON routes, exact boundaries (1,048,576 bytes passes, 1,048,577 bytes fails with 413 `PAYLOAD_TOO_LARGE`), oversized envelopes, and valid 12 MiB archive envelope preservation. | `test_rework_b2_two_mib_closure_nested_manifest_dict_and_json_rejected`, `test_rework_b2_manifest_size_exact_boundaries`, `test_rework_b2_oversized_dict_and_json_envelopes_rejected`, `test_rework_b2_valid_12_mib_archive_envelope_accepted` |
| **B3: Public errors expose internal exception details** | `GatewayError` directly interpolated `str(exc)` into public error messages across catch-all and subroutines, leaking internal dependency messages and injected sentinels (e.g. `/private/host/keys SECRET_SENTINEL`) via `to_envelope()`. | Centralized static mapping `PUBLIC_ERROR_MESSAGES` for all error codes. `GatewayError.message` is strictly retrieved from the central static mapping; raw exception strings and sentinels are retained exclusively in the private `diagnostic` attribute and NEVER leaked into `to_envelope()`. Envelopes are strictly bounded with correlation IDs (`request_id`). Tested injected secret/path sentinels across JWKS, JSON parsing, schema validation, archive validation, and generic handlers. Logging redaction thoroughly sanitizes bearer tokens, JWTs, and sensitive fields. | `test_rework_b3_public_errors_and_envelope_never_leak_sentinel_or_exceptions`, `test_rework_b3_sentinels_across_jwks_parsing_schema_archive_handlers`, `test_security_audit_logging_redacts_tokens_and_bodies` |
| **B4: Delivery evidence documentation accurately matches actual APIs** | Previous delivery report named non-existent APIs (`temporary_tenant_context`, `tenant.is_active`, `config.enabled`). | Corrected documentation: Clarified that `MultiTenantIAM.get_tenant(tenant_id).status == TenantStatus.ACTIVE` is checked. Clarified that `GitHubConnectorConfig.status == "ACTIVE"` is checked. Accurately documented that the constructed `TenantContext` is an internal ephemeral data structure, not an IAM credential or bearer session, and does not prove runtime permission enforcement by itself. | Documentation corrected throughout `GHA_03_DELIVERY.md` and `GHA_03_GATEWAY_DESIGN_V1.md` |

---

## 2. Test Matrix Results (TC-01 through TC-22 and Rework Regressions)

All 22 test scenarios from the specification, 12 binding condition tests, and 11 dedicated rework regressions pass cleanly in `tests/test_gha_gateway_integration.py` (**45 items total**).

| Test Scenario | Condition / Threat Vector | Expected Status & Code | Outcome |
|---|---|---|---|
| **TC-01** | Valid Witness Observation Submission | 200 OK (`VALIDATED_UNTRUSTED_OBSERVATION`) | **PASSED** |
| **TC-02** | Invalid JWT Signature (tampered payload/header) | 401 Unauthorized (`INVALID_TOKEN_SIGNATURE`) | **PASSED** |
| **TC-03** | Untrusted JWT Issuer (`evil-issuer.com`) | 401 Unauthorized (`UNTRUSTED_ISSUER`) | **PASSED** |
| **TC-04** | Invalid Audience (expected `mas-coordinator-witness`) | 401 Unauthorized (`INVALID_AUDIENCE`) | **PASSED** |
| **TC-05** | Expired Token (`exp < now`) | 401 Unauthorized (`TOKEN_EXPIRED`) | **PASSED** |
| **TC-06** | Clock Skew Tolerance ($\le 30$s permitted, $> 30$s rejected) | 200 OK / 401 Unauthorized | **PASSED** |
| **TC-07** | Future Token (`nbf > now + 30s`) | 401 Unauthorized (`TOKEN_FUTURE`) | **PASSED** |
| **TC-08** | Token Issued in Future (`iat > now + 30s`) | 401 Unauthorized (`TOKEN_ISSUED_IN_FUTURE`) | **PASSED** |
| **TC-09** | Negative or Excessive Lifetime (`exp <= iat` or `exp - iat > 900s`) | 401 Unauthorized (`INVALID_TOKEN_LIFETIME`) | **PASSED** |
| **TC-10** | Token Age Exceeded (`now - iat > 900s` with valid future exp) | 401 Unauthorized (`TOKEN_AGE_EXCEEDED`) | **PASSED** |
| **TC-11** | JWKS Unknown `kid` Throttling ($\ge 5$ min cool-down) | 401 Unauthorized (`UNKNOWN_KEY_THROTTLED`) | **PASSED** |
| **TC-12** | JWKS Endpoint Outage / Refusal (timeout / redirect / 500) | 503 Service Unavailable (`JWKS_UNAVAILABLE`) | **PASSED** |
| **TC-13** | Unenrolled Repository ID (`repository_id` mismatch) | 403 Forbidden (`REPOSITORY_NOT_ENROLLED`) | **PASSED** |
| **TC-14** | Unapproved Reusable Workflow SHA (unpinned / wrong SHA) | 403 Forbidden (`UNAPPROVED_WORKFLOW_SHA`) | **PASSED** |
| **TC-15** | Unapproved Branch / Tag Ref (`ref` outside permitted pattern) | 403 Forbidden (`REF_NOT_PERMITTED`) | **PASSED** |
| **TC-16** | Fencing Token Mismatch (request vs manifest mismatch) | 409 Conflict (`FENCING_TOKEN_MISMATCH`) | **PASSED** |
| **TC-17** | Coordinate Mismatch (`run_id` or `run_attempt` mismatch) | 403 Forbidden (`COORDINATE_MISMATCH`) | **PASSED** |
| **TC-18** | Structural Manifest Violation (blank IDs / invalid JSON) | 422 Unprocessable (`INVALID_MANIFEST_STRUCTURE`) | **PASSED** |
| **TC-19** | Client Privilege Spoofing (`role: builder` in body) | 422 Unprocessable (`EXTRA_FIELDS_FORBIDDEN`) | **PASSED** |
| **TC-20** | Revoked Tenant Status (inactive tenant in `MultiTenantIAM`) | 403 Forbidden (`TENANT_REVOKED`) | **PASSED** |
| **TC-21** | Disabled Connector (`status="REVOKED"`) | 403 Forbidden (`CONNECTOR_REVOKED`) | **PASSED** |
| **TC-22** | Structured JSON Logging (sanitized, zero raw secrets) | 200 OK (Audited without secret leakage) | **PASSED** |
| **Edge 1** | Ref Pattern Matching on Valid Pattern | 200 OK | **PASSED** |
| **Edge 2** | Base64 Archive Exceeding 16 MiB Limit | 413 Payload Too Large (`PAYLOAD_TOO_LARGE`) | **PASSED** |
| **Edge 3** | Decoded Archive Exceeding 12 MiB Limit | 413 Payload Too Large (`PAYLOAD_TOO_LARGE`) | **PASSED** |
| **Edge 4** | Invalid / Non-canonical Base64 String | 400 Bad Request (`INVALID_BASE64_PAYLOAD`) | **PASSED** |
| **Edge 5** | Missing Archive When Observations Declare Artifacts | 400 Bad Request (`ARTIFACTS_REQUIRED`) | **PASSED** |
| **Edge 6** | Artifact Archive Validation Failure (digest mismatch) | 400 Bad Request (`INVALID_ARTIFACT_ARCHIVE`) | **PASSED** |
| **Edge 7** | Corrupt ZIP Archive | 400 Bad Request (`INVALID_ARTIFACT_ARCHIVE`) | **PASSED** |
| **Edge 8** | In-flight Tenant Revocation During Validation | 403 Forbidden (`TENANT_REVOKED`) | **PASSED** |
| **Edge 9** | In-flight Connector Revocation During Validation | 403 Forbidden (`CONNECTOR_REVOKED`) | **PASSED** |
| **Edge 10** | Ephemeral Witness Context Non-persistence | Verified: zero leakage of witness context | **PASSED** |
| **Edge 11** | Clean Import in Subprocess (`sys.executable`) | Clean zero exit code | **PASSED** |
| **Edge 12** | JWKS Single-Flight Concurrency (10 threads, 1 fetch) | Verified: exactly 1 fetch executed | **PASSED** |
| **Edge 13** | Repeated Valid Token Stateless Success (zero DB mutation) | Verified: zero DB rows added across calls | **PASSED** |
| **Rework B1-1** | Connector Replacement During Artifact Validation (`REVOKED`, gen 2) | 403 Forbidden (`CONNECTOR_REVOKED`) | **PASSED** |
| **Rework B1-2** | Connector Removal During Artifact Validation | 403 Forbidden (`CONNECTOR_REMOVED`) | **PASSED** |
| **Rework B1-3** | Connector Generation Changed During Validation | 403 Forbidden (`CONNECTOR_GENERATION_CHANGED`) | **PASSED** |
| **Rework B1-4** | Connector Authority Changed During Validation | 403 Forbidden (`CONNECTOR_AUTHORITY_CHANGED`) | **PASSED** |
| **Rework B1-5** | `ConnectorRegistry` Thread-Safe Operations & Snapshot Isolation | Verified: mapping and snapshot isolation | **PASSED** |
| **Rework B2-1** | Reproduced 2 MiB Closure Path on Dict, JSON, and Model Routes | 413 Payload Too Large (`PAYLOAD_TOO_LARGE`) | **PASSED** |
| **Rework B2-2** | Manifest Size Exact Boundaries (1,048,576 B passes, 1,048,577 B fails) | 200 OK / 413 Payload Too Large | **PASSED** |
| **Rework B2-3** | Oversized Envelopes (> 18 MiB) on Dict and JSON Routes | 413 Payload Too Large (`PAYLOAD_TOO_LARGE`) | **PASSED** |
| **Rework B2-4** | Valid 12 MiB Archive Fits Within 18 MiB Envelope | 200 OK (`VALIDATED_UNTRUSTED_OBSERVATION`) | **PASSED** |
| **Rework B3-1** | Public Error Envelope & Message Never Leak Internal Sentinel | 500 Internal Error (`INTERNAL_ERROR`, zero sentinel) | **PASSED** |
| **Rework B3-2** | Sentinel Redaction Across JWKS, JSON, Schema, & Archive Errors | Verified: zero sentinel in envelopes | **PASSED** |

---

## 3. Verification Evidence & Test Receipts

### 1. Targeted Gateway Suite (`tests/test_gha_gateway_integration.py`)
```text
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0
collected 45 items

tests/test_gha_gateway_integration.py ............................................. [100%]
============================== 45 passed in 2.69s ==============================
```

### 2. Combined Targeted Delivery Suite (Gateway + GHA-02 + Delivery Gates)
Command: `pytest tests/test_gha_gateway_integration.py tests/test_gha_delivery_integration.py tests/test_delivery_process_gates.py -q`
```text
........................................................................ [ 59%]
..................................................                       [100%]
122 passed in 9.51s
```

### 3. CC Execution & Coordinator Suites
Command: `pytest tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_cc04_scheduler_worker.py tests/test_cc05_antigravity_adapter.py tests/test_cc06_verifier_reviewer.py -q`
```text
........................................................................ [ 50%]
......................................................................   [100%]
142 passed in 31.59s
```

### 4. Full Quality Gate (`bash scripts/run_quality_gate.sh`)
```text
[GATE 1/5]: Checking Code Style & Lints (ruff)...
All checks passed!

[GATE 2/5]: Checking Runtime Health & Capabilities Matrix...
MAS doctor — v0.2.0

[GATE 3/5]: Checking Local Research Assets and Links...
{
  "total_files": 112,
  "md_files_count": 89,
  "pdf_files_count": 8,
  "png_files_count": 15,
  "total_md_lines": 25121,
  "total_links": 197,
  "broken_links_count": 0,
  "broken_links": []
}

[GATE 4/5]: Checking Python Source Compilation...
python3 -m compileall -q mas scripts (Clean exit code 0)

[GATE 5/5]: Executing Full Unit & Integration Test Suite...
================= 894 passed, 20 skipped in 324.94s (0:05:24) ==================

=================================================================
   ✅ ALL QUALITY GATES PASSED (5/5)
=================================================================
```

### 5. Clean Installed-Wheel Check Outside Repository
Command sequence:
```bash
python3 -m build --wheel --outdir /tmp/test_wheel_isolated
python3 -m venv /tmp/test_venv_isolated
/tmp/test_venv_isolated/bin/pip install /tmp/test_wheel_isolated/mas_core-0.2.0-py3-none-any.whl pytest
mkdir -p /tmp/isolated_tests && cp tests/test_gha_gateway_integration.py /tmp/isolated_tests/
cd /tmp/isolated_tests
/tmp/test_venv_isolated/bin/python -c "import mas.pm.gateway; print('RESOLVED_GATEWAY_FILE:', mas.pm.gateway.__file__)"
/tmp/test_venv_isolated/bin/pytest test_gha_gateway_integration.py -q
```
Receipt:
```text
Successfully built mas_core-0.2.0-py3-none-any.whl
Successfully installed Pillow-12.3.0 PyYAML-6.0.3 annotated-types-0.8.0 cffi-2.1.1 cryptography-50.0.2 iniconfig-2.3.1 mas-core-0.2.0 packaging-26.3 pluggy-1.6.0 pycparser-3.11 pydantic-2.14.1 pydantic-core-2.50.1 pygments-2.21.0 pytest-9.1.1 typing-extensions-4.16.0 typing-inspection-0.4.4
RESOLVED_GATEWAY_FILE: /tmp/test_venv_isolated/lib/python3.14/site-packages/mas/pm/gateway/__init__.py
.............................................                            [100%]
45 passed in 2.93s
```

---

## 4. Notes for Codex Architectural Reviewer & Unresolved Guarantees

1. **Submission Readiness**: This rework candidate is submitted for independent architectural review and verification by Codex. Acceptance is not self-conferred.
2. **Evidence Boundary**: The test receipts represent author-provided execution evidence. Independent semantic verification by Codex is required under the delivery agreement before release.
3. **Gated Scope (GHA-04 Checkpoint)**:
   - Live GitHub Actions workflows (`.github/workflows/*.yml`) remain disabled.
   - Public OIDC endpoints, token issuance/exchange, and external provider dispatch remain unconfigured.
   - Persistent witness receipt storage and replay deduplication are deferred to GHA-04.
   - No branch protection settings or production project enrollments were modified.
   - Core delivery database schema and `mas/pm/delivery.py` remain strictly unmodified.
4. **Traceability**: All 45 gateway tests, 30 GHA-02 validator tests, 47 delivery process tests, 142 CC regression tests, and full 5-stage quality gates pass on this exact candidate.
