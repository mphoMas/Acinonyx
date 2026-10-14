# Delivery Evidence and Handoff: Task GHA-02 (Whole-Boundary Correction)

Task: **GHA-02 — Manifest and artifact validation against completed authorized runs**
Branch: `feat/scrum-board-automation`
Implementation Owner: Antigravity Development Team
Architecture Reviewer: Codex
Date: 14 October 2026
Reviewed Baseline: `116b66ce` (incorporating `GHA_02_ARCHITECT_REVIEW.md` and `ANTIGRAVITY_GHA_02_REWORK_BRIEF.md`)
Candidate Commit: `aad209f8` (candidate commit for review)
Status: Whole-boundary correction completed, test suite passing, submitted for Codex architectural review.

---

## 1. Executive Summary & Review Findings Closure

In response to Codex's independent review (`GHA_02_ARCHITECT_REVIEW.md`) and whole-boundary correction directive (`ANTIGRAVITY_GHA_02_REWORK_BRIEF.md`), Antigravity has resolved all critical defect findings (B1–B4), eliminated shallow validation bypasses, decoupled the CLI from live database mutation, and hardened archive and input parsing across all routes.

### Critical Findings Closure Summary

| Finding ID & Summary | Root Cause in Candidate `ef6c5400` | Architectural Resolution in Rework | Verified Test |
|---|---|---|---|
| **B1: Empty archives skip observation checks** | Observation loop was guarded by `if members:`, returning valid when archive was empty. | All supplied observations are strictly validated against extracted archive members regardless of archive member count. Empty archives with declared observations fail immediately with `DeliveryValidatorError`. | `test_reproduce_b1_empty_archive_with_passed_observations_rejected` |
| **B2: Preconstructed models bypass schema revalidation** | `validate_delivery_manifest` directly assigned input when `isinstance(..., DeliveryManifest)`. | `validate_manifest_input()` recursively serializes input instances and strictly validates via `DeliveryManifest.model_validate(raw, strict=True)`. Model mutations via `model_copy` or `model_construct` are rejected on all input routes. | `test_reproduce_b2_model_copy_and_construct_bypass_rejected` |
| **B3 (Case 1): NUL byte truncated by ZipInfo** | `_validate_safe_member_path` checked `info.filename` which `ZipInfo` truncated at `\x00`. | Inspects `info.orig_filename`, `info.filename`, and raw local header bytes. Rejects if `\x00` is present anywhere or if `orig_filename != filename`. | `test_reproduce_b3_original_zip_nul_name_rejected` |
| **B3 (Case 2): STORED entry header-size lie** | `ZipExtFile.read()` stopped at declared header size, ignoring excess physical data in the stream. | Reconciles local and central headers, enforces `compress_size == file_size` for STORED entries, validates physical layout continuity without gaps, and checks EOCD boundary with zero trailing bytes. | `test_reproduce_b3_stored_header_size_lie_hiding_excess_data_rejected` |
| **B4: CLI accepts prohibited DB override & mutates before authority** | `delivery_gate_runner.py` accepted `--db` and `--publish`, initializing `PMDatabase` and schema migrations before auth. | Removed `--db` and `--publish` from CLI entirely. CLI is strictly a pure offline claims validator with zero DB access. Real publication belongs exclusively to SDK `publish_submission` under active tenant authority. | `test_reproduce_b4_cli_no_db_override_and_no_unauthenticated_db_init` |
| **Medium: Shallow ValidationResult bypass** | `publish_submission` accepted caller-constructed `ValidationResult` objects. | `publish_submission` rejects shallow `ValidationResult` instances and requires original bounded inputs (`manifest_input`, `archive_input`, `repo_path`) to enforce authoritative revalidation against live DB state. | `test_shallow_validation_result_bypass_rejected` |
| **Medium: Unbounded file reads & Git output** | CLI read full files before size check; Git diff buffered without limits/timeouts. | Added `read_file_bounded()` using safe regular file descriptors and size caps. Git subprocesses enforce 10s timeouts and 1 MiB output caps. | `test_scenario_8_archive_size_and_digest_limits`, `test_scenario_9_git_diff_out_of_scope_denied` |

---

## 2. Architecture & Design Specification (V01–V07 Invariant Enforcement)

### V01 — Strict Input & Full Identity Schema
- `DeliveryManifest` binds full execution context: `tenant_id`, `project_id`, `issue_id`, `brief_version`, `policy_version`, `revision`, `run_id`, `intent_id`, `attempt_id`, `fencing_token`, `candidate_sha`, `base_sha`, and `suite_digest`.
- Strict Pydantic models with `strict=True`, `extra="forbid"`, and `revalidate_instances="always"`.
- `validate_manifest_input()` enforces strict revalidation for JSON bytes/strings, dictionaries, and preconstructed Pydantic instances (`model_copy`, `model_construct`).

### V02 — Actual Binding & State Protection
- Resolves task and coordinator records via read-only SQLite connections under active tenant context.
- Requires task phase `AWAITING_SUBMISSION` or `READINESS_RETURNED`. Rejects `READY` phase or unexecuted intents.
- Validates run status `EXITED`, `exit_code == 0`, attempt status `SUCCEEDED`, intent status `COMPLETED`, matching fencing tokens, candidate commit SHA, base commit SHA, brief version, policy version, and canonical suite digest.
- Prevents mutation or submission when task is in `RECURRENCE_PAUSED`, `SCOPE_REQUESTED`, or `DISPUTED`.

### V03 — Read Committed Git Objects Safely
- Repository root configured by trusted integration environment.
- Resolves commit SHAs with `git rev-parse --verify {sha}^{commit}` (10s timeout).
- Inspects tree diffs using argument arrays: `["git", "-C", repo, "diff-tree", "-z", "-r", "-M", "--no-commit-id", base_sha, candidate_sha, "--"]` with 1 MiB output limit and 10s timeout.
- NUL-safe parsing (`\0`), mode checking, rejecting symlinks (`120000`), submodules (`160000`), and permission changes.
- Both source and destination paths of renames, modifications, additions, and deletions must reside strictly within `brief.scope`. Malicious command-like file paths are parsed strictly as literal data.

### V04 — Bounded Archive Validation & Layout Integrity
- Physical size caps: max 12 MiB compressed, max 64 members, max 2 MiB per regular member, max 10 MiB total uncompressed bytes.
- Inspects `orig_filename` and raw header filenames before normalization. Rejects `\x00`, backslashes, control characters, leading `/`, directory traversal segments (`..`), directories, symlinks, and canonical name collisions.
- Supported compression methods: only STORED (0) and DEFLATED (8). Encryption flags rejected.
- Local headers reconciled against central directory headers (CRC32, sizes, compression method).
- Continuous physical layout verification: verifies that member data payloads and local headers are strictly contiguous, with zero unmapped gap bytes between members and before the central directory. EOCD record verified with zero trailing bytes.
- DEFLATE stream verification using `zlib.decompressobj(-15)`: asserts stream termination (`eof is True`) and zero trailing unconsumed compressed data (`unused_data == b""`).

### V05 — Observations Remain Claims
- Supplied observations in the manifest are validated against agreed `brief.checks`.
- Unknown check IDs and duplicate check observations are rejected.
- Valid manifests with omitted checks or non-passing observations (`FAILED`, `SKIPPED`, `UNAVAILABLE`) route through `DeliveryService.submit()` to produce `READINESS_RETURNED`. Returns persist in historical records without fabricating `PASSED` results.

### V06 — Authority & Atomicity
- Strict decoupling: `scripts/delivery_gate_runner.py` is pure offline claims validation with no database connection, no `--db` flag, and no `--publish` flag.
- Mutation belongs exclusively to `publish_submission` / `validate_and_submit`, requiring active caller tenant session authority and builder role.
- Enforces optimistic concurrency via CAS revisions (`DeliveryGateError("Stale delivery revision")`).
- Multi-threaded publication races produce exactly one winner, leaving events and task state consistent.

### V07 — Output & Measurement
- Structured bounded JSON output emitted by CLI:
  - Success: `{"status": "VALIDATED_CLAIMS", "valid": true, "authority_verified": false, ...}`
  - Failure: `{"status": "VALIDATION_FAILED", "valid": false, "reasons": [...]}`
- Error messages report exact validation causes without leaking host paths, environment variables, or secrets.

---

## 3. Negative and Positive Acceptance Matrix Results

All 13 specification scenarios plus critical defect reproduction and adversarial variants are verified by dedicated automated tests in `tests/test_gha_delivery_integration.py`.

| Test / Scenario | Description & Condition | Result |
|---|---|---|
| **B1 Reproduction** | Empty zip archive + PASSED observations -> rejected with `DeliveryValidatorError`; task phase remains `AWAITING_SUBMISSION`. | **PASSED** |
| **B2 Reproduction** | Preconstructed manifest via `model_copy` (invalid schema/type) or `model_construct` -> rejected on all routes. | **PASSED** |
| **B3 (NUL) Reproduction** | Raw ZIP entry with `evil\x00name` -> rejected before normalization. | **PASSED** |
| **B3 (STORED Lie) Reproduction** | STORED entry physically 2,097,153 bytes with forged header size=1 -> rejected by physical layout continuity check. | **PASSED** |
| **B4 Reproduction** | CLI run with `--db` or `--publish` -> rejected with exit code 2 (unrecognized arguments). Zero DB mutation. | **PASSED** |
| **Shallow Bypass Reproduction** | Caller-constructed `ValidationResult` passed to `publish_submission` -> rejected with `DeliveryValidatorError`. | **PASSED** |
| **Scenario 1** | Valid completed run + all valid observations -> authenticated `IN_REVIEW`; pure CLI returns `VALIDATED_CLAIMS`. | **PASSED** |
| **Scenario 2** | Omitted check and valid nonpassing observation -> `READINESS_RETURNED`; readiness return count recorded in metrics. | **PASSED** |
| **Scenario 3** | Submissions from `READY` state or unexecuted/failed run -> denied without mutation. | **PASSED** |
| **Scenario 4** | Wrong tenant, non-builder role, or stale CAS revision -> denied without mutation. | **PASSED** |
| **Scenario 5** | Mismatched candidate SHA, base SHA, or suite digest -> denied without mutation. | **PASSED** |
| **Scenario 6** | Strict JSON: duplicate keys, `NaN`/`Infinity`, bool-for-int coercion, or unknown fields -> rejected during parse. | **PASSED** |
| **Scenario 7** | Traversal (`../`), absolute paths, backslashes, control chars, symlinks, or duplicate canonical names -> rejected. | **PASSED** |
| **Scenario 8** | Overlarge member (>2 MiB), total archive overflow (>10 MiB), or CRC32/SHA-256 mismatch -> rejected and handles closed. | **PASSED** |
| **Scenario 9** | Unauthorized git diff outside `brief.scope`, cross-scope renames, symlinks (`120000`), or mode changes -> rejected. | **PASSED** |
| **Scenario 10** | Competing publication calls with identical revision -> one winner, second fails with CAS conflict. | **PASSED** |
| **Scenario 11** | Task in `RECURRENCE_PAUSED` -> cannot be submitted or cleared by validator or CLI. | **PASSED** |
| **Scenario 12** | CLI execution outputs truthful JSON (`VALIDATED_CLAIMS`, `authority_verified=false`) and cannot bypass authority. | **PASSED** |
| **Scenario 13** | Clean import test in an isolated Python process using `sys.executable`. | **PASSED** |
| **Concurrency Race** | Multi-threaded race with `ThreadPoolExecutor`: exactly one thread succeeds to `IN_REVIEW`, other fails with CAS error. | **PASSED** |
| **Real Tenant Revocation** | Calling `publish_submission` with non-builder actor (`reviewer`) -> denied with `PermissionError` without state change. | **PASSED** |

---

## 4. Verification Evidence & Test Receipts

### 1. Targeted Integration & Adversarial Suite (`tests/test_gha_delivery_integration.py`)
```text
============================= test session starts ==============================
platform linux -- Python 3.14.6, pytest-9.0.3, pluggy-1.6.0
collected 21 items

tests/test_gha_delivery_integration.py::test_reproduce_b1_empty_archive_with_passed_observations_rejected PASSED [  4%]
tests/test_gha_delivery_integration.py::test_reproduce_b2_model_copy_and_construct_bypass_rejected PASSED [  9%]
tests/test_gha_delivery_integration.py::test_reproduce_b3_original_zip_nul_name_rejected PASSED [ 14%]
tests/test_gha_delivery_integration.py::test_reproduce_b3_stored_header_size_lie_hiding_excess_data_rejected PASSED [ 19%]
tests/test_gha_delivery_integration.py::test_reproduce_b4_cli_no_db_override_and_no_unauthenticated_db_init PASSED [ 23%]
tests/test_gha_delivery_integration.py::test_shallow_validation_result_bypass_rejected PASSED [ 28%]
tests/test_gha_delivery_integration.py::test_scenario_1_valid_run_produces_in_review PASSED [ 33%]
tests/test_gha_delivery_integration.py::test_scenario_2_nonpassing_or_omitted_check_produces_readiness_returned PASSED [ 38%]
tests/test_gha_delivery_integration.py::test_scenario_3_ready_phase_or_unsuccessful_run_denied PASSED [ 42%]
tests/test_gha_delivery_integration.py::test_scenario_4_wrong_tenant_or_stale_cas_denied PASSED [ 47%]
tests/test_gha_delivery_integration.py::test_scenario_5_changed_identities_denied PASSED [ 52%]
tests/test_gha_delivery_integration.py::test_scenario_6_strict_json_and_types_enforced PASSED [ 57%]
tests/test_gha_delivery_integration.py::test_scenario_7_unsafe_archive_paths_rejected PASSED [ 61%]
tests/test_gha_delivery_integration.py::test_scenario_8_archive_size_and_digest_limits PASSED [ 66%]
tests/test_gha_delivery_integration.py::test_scenario_9_git_diff_out_of_scope_denied PASSED [ 71%]
tests/test_gha_delivery_integration.py::test_scenario_10_competing_publication_cas PASSED [ 76%]
tests/test_gha_delivery_integration.py::test_scenario_11_paused_task_cannot_be_cleared PASSED [ 80%]
tests/test_gha_delivery_integration.py::test_scenario_12_cli_execution_and_authority PASSED [ 85%]
tests/test_gha_delivery_integration.py::test_scenario_13_clean_import PASSED [ 90%]
tests/test_gha_delivery_integration.py::test_real_concurrency_race_one_winner PASSED [ 95%]
tests/test_gha_delivery_integration.py::test_fresh_real_tenant_binding_wrong_actor_and_revocation PASSED [100%]

============================== 21 passed in 1.67s ==============================
```

### 2. Core Delivery Process Regression Suite (`tests/test_delivery_process_gates.py`)
```text
============================== 47 passed in 1.35s ==============================
Combined: 68 passed in 2.90s
```

### 3. Coordinator & Execution Regression Suites
```text
tests/test_cc03_final_corrections.py
tests/test_cc_03_coordinator_state.py
tests/test_cc04_scheduler_worker.py
tests/test_cc05_antigravity_adapter.py
tests/test_cc06_verifier_reviewer.py
============================== 142 passed in 25.38s ==============================
```

### 4. Code Quality & Linter
- `ruff check mas tests scripts/delivery_gate_runner.py` -> 0 errors.
- `git diff --check` -> 0 whitespace issues.

---

## 5. Notes for Codex Architectural Reviewer

1. **Whole-Boundary Correction**: Covers B1, B2, B3 (both NUL and STORED size-lie cases), and B4, along with the shallow `ValidationResult` bypass.
2. **Decoupled CLI**: The CLI is strictly a pure offline claims validator. It does not accept `--db` or `--publish`, never connects to SQLite, and never performs schema initialization or mutations.
3. **No Live Workflows or Cloud Runtimes**: No live GitHub workflows activated, no OIDC endpoints deployed, and no branch protection settings modified.
4. **Independent Review**: Submitted for independent architectural review and verification by Codex; no self-approval.
