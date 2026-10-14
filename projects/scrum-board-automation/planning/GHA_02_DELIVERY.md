# Delivery Evidence and Handoff: Task GHA-02 (Offline Validator)

Task: **GHA-02 — Manifest and artifact validation against completed authorized runs**  
Branch: `feat/scrum-board-automation`  
Implementation Owner: Antigravity Development Team  
Architecture Reviewer: Codex  
Date: 14 October 2026  
Reviewed Baseline: `3cf837fd` (incorporating `GHA_01_REVISED_ACCEPTANCE_REVIEW.md` and `ANTIGRAVITY_GHA_02_IMPLEMENTATION_BRIEF.md`)  
Candidate Commit: `08532642` (candidate commit for review)  
Status: Implementation completed, test suite passing, submitted for Codex architectural review.

---

## 1. Executive Summary

In accordance with the approved-with-conditions specification review (`GHA_01_REVISED_ACCEPTANCE_REVIEW.md`) and the concrete implementation brief (`ANTIGRAVITY_GHA_02_IMPLEMENTATION_BRIEF.md`), Antigravity has implemented the offline manifest and artifact validator for Scrum Board Automation delivery gates.

GHA-02 establishes an offline pre-flight validation mechanism that validates candidate delivery manifests, artifact zip archives, and Git commit trees against completed authorized coordinator runs before mutating delivery state.

### Delivered Scope

1. **`mas/pm/delivery_validator.py`**:
   - Strict Pydantic models for manifests and observations (`strict=True`, `extra="forbid"`, `revalidate_instances="always"`).
   - Custom strict JSON parser rejecting duplicate keys and nonfinite numeric constants (`NaN`, `Infinity`).
   - Bounded streaming artifact archive inspector (byte caps, path sanitization, traversal and collision prevention, CRC32 and SHA-256 validation).
   - Safe Git tree diff inspector using NUL-safe `git diff-tree -z` argument arrays, mode checking, symlink/submodule rejection, and strict file scope enforcement.
   - Database binding verification against completed runs in `AWAITING_SUBMISSION` or `READINESS_RETURNED`.
   - Authenticated publication invoking existing `DeliveryService.submit()` under caller tenant session authority and builder role.
2. **`scripts/delivery_gate_runner.py`**:
   - CLI utility defaulting to read-only validation emitting structured JSON (`VALIDATED_CLAIMS` or `VALIDATION_FAILED`) with zero side effects.
   - Optional `--publish` mode executing authenticated submission without `--trusted-admin`, `--actor`, or host DB override backdoors.
3. **`tests/test_gha_delivery_integration.py`**:
   - 13 comprehensive integration tests verifying all 13 positive and negative acceptance scenarios defined in the brief.
4. **Specification Document Updates**:
   - Synchronized `GITHUB_ACTIONS_INTEGRATION_CONTRACT_V1.md`, `GITHUB_ACTIONS_ACCEPTANCE_MATRIX.md`, and `ANTIGRAVITY_GHA_01_DELIVERY.md` with factual container limits, OIDC claim requirements, required check semantics, and single-owner accountability.

### Preserved Governing Constraints

- **No live workflows activated** under `.github/workflows/`.
- **No live cloud adapters, webhooks, or public OIDC endpoints**; worker registry remains synthetic-only.
- **No modification to branch protection settings**.
- **No operational projects enrolled**.
- **Existing `mas/pm/delivery.py` preserved intact**; no refactoring or interface mutations to the core delivery service.
- **Validator executes no arbitrary shell commands, hooks, or test suites**; command strings and file paths remain untrusted data.

---

## 2. Architecture & Design Specification (V01–V07 Invariant Enforcement)

The implementation adheres to the 7 core delivery gate invariants (V01–V07):

### V01 — Strict Input
- Manifest validation uses Pydantic v2 models with `strict=True`, `extra="forbid"`, and `revalidate_instances="always"`. Type coercion (such as integer-to-string or boolean-to-integer) is strictly rejected.
- `parse_manifest_json()` parses JSON using `json.loads` configured with:
  - `object_pairs_hook`: detects and rejects duplicate JSON object keys (e.g. `{"task_id": "1", "task_id": "2"}`).
  - `parse_constant`: rejects nonfinite floats (`NaN`, `Infinity`, `-Infinity`).
- Bounded opaque identifiers are validated for tenant, project, task, brief revision, attempt, run, intent, and git commit SHAs.

### V02 — Actual Binding
- Resolves task and execution records from the trusted SQLite database via read-only connections.
- Requires task phase to be `AWAITING_SUBMISSION` or `READINESS_RETURNED`. Submissions from `READY` or unexecuted intents are rejected with `DeliveryGateError`.
- Validates that the associated run is fully completed: `run.status == "EXITED"`, `run.exit_code == 0`, `attempt.status == "SUCCEEDED"`, and `intent.status == "COMPLETED"`.
- Binds and matches fencing token, candidate commit SHA, base commit SHA, brief version, and canonical suite digest.

### V03 — Read Committed Git Objects Safely
- Repository root is derived exclusively from trusted integration configuration, never from manifest-supplied paths.
- Resolves exact commit SHAs via `git rev-parse --verify {sha}^{commit}`.
- Inspects tree diffs using argument arrays: `["git", "diff-tree", "-z", "-r", "-M", "--no-commit-id", base_sha, candidate_sha]`.
- NUL-safe parsing splits records by `\0`, parsing raw raw mode transitions and path pairs.
- Rejects symlinks (`120000`), git submodules (`160000`), and permission/mode alterations.
- Enforces that all added, modified, deleted, and renamed paths (`src_path` and `dst_path`) fall strictly within `brief.scope`.
- Malicious filenames that resemble command options (e.g. `--help`, `-rf`) are handled strictly as literal path data.

### V04 — Bounded Archive Validation
- Implements strict streaming validation on zip archives without extracting files to the host filesystem.
- Enforces hard physical caps:
  - Max compressed archive size: 12 MiB (`MAX_COMPRESSED_ARCHIVE_SIZE`).
  - Max member count: 64 regular files (`MAX_ARCHIVE_MEMBERS`).
  - Max member uncompressed size: 2 MiB per regular file (`MAX_UNCOMPRESSED_MEMBER_SIZE`).
  - Max total uncompressed bytes: 10 MiB across the archive (`MAX_TOTAL_UNCOMPRESSED_SIZE`).
- Streams decompressed chunks (64 KiB) maintaining a live byte counter; does not rely on zip header declared sizes.
- Sanitizes paths using `posixpath.normpath`:
  - Rejects absolute paths (`/etc/passwd`), traversal components (`../`), backslashes (`\`), NUL bytes, and control characters.
  - Rejects directories, symlinks, and non-regular zip entries.
  - Detects canonical name collisions (case-insensitive deduplication).
- Validates zip CRC32 and computes streaming SHA-256 to verify integrity against declared observation digests.
- Handles archive resources in `try...finally` blocks to guarantee immediate closure on all failure paths.

### V05 — Observations Remain Claims
- Supplied observations in the manifest are treated strictly as claimed results, not ground truth execution facts.
- Every observation must correspond to an agreed check in `brief.checks`. Unknown check keys or duplicate check entries reject the manifest.
- Missing required checks or non-passing observations (`FAILED`, `SKIPPED`, `UNAVAILABLE`) are preserved as truthful evidence and routed through `DeliveryService.submit()`, producing `READINESS_RETURNED`. No `PASSED` results are fabricated.

### V06 — Authority & Atomicity
- Enforces strict separation between pure validation (`validate_delivery_manifest`) and authenticated state mutation (`publish_submission`).
- Pure validation performs zero database writes, zero PM event emissions, and zero state changes. Replaying validation has no side effects.
- CLI defaults to validation-only mode. Authenticated publication requires `--publish` and operates under the caller's tenant session authority and builder role.
- CLI contains no `--trusted-admin`, `--actor`, or database path override flags.
- Submissions enforce optimistic locking via CAS revisions (`StaleRevisionError`), ensuring concurrent submissions have exactly one winner.
- Pre-existing task pauses (`RECURRENCE_PAUSED`, `SCOPE_REQUESTED`, `DISPUTED`) cannot be bypassed or cleared by the validator.

### V07 — Output & Measurement
- Emits structured, bounded JSON:
  - Pure CLI mode: `{"status": "VALIDATED_CLAIMS", "task_id": "...", "candidate_sha": "...", ...}` on success, or `{"status": "VALIDATION_FAILED", "errors": [...]}` on failure.
  - Authenticated publication mode: returns the formal delivery gate result (`IN_REVIEW` or `READINESS_RETURNED`).
- Detailed rejection reasons are returned without leaking sensitive environment data, internal paths, or secrets.

---

## 3. Negative and Positive Acceptance Matrix Results

All 13 acceptance scenarios from `ANTIGRAVITY_GHA_02_IMPLEMENTATION_BRIEF.md` are covered by dedicated automated tests in `tests/test_gha_delivery_integration.py`.

| Scenario | Scenario Description | Tested Condition | Result |
|---|---|---|---|
| **1** | Valid completed run + valid observations | Valid run in `AWAITING_SUBMISSION`, all checks passed -> authenticated submission transitions to `IN_REVIEW`; pure CLI returns `VALIDATED_CLAIMS`. Never reaches `ACCEPTED` or `DONE`. | **PASSED** |
| **2** | Nonpassing or omitted check observation | Manifest with omitted check or `FAILED`/`SKIPPED`/`UNAVAILABLE` observation -> authenticated submission produces `READINESS_RETURNED`; returns persist across reopen. | **PASSED** |
| **3** | Unexecuted or invalid execution phase | Submissions from `READY` phase, missing brief, non-existent run, foreign run, or failed execution (`exit_code != 0`) -> denied without state mutation. | **PASSED** |
| **4** | Wrong tenant, role, unbound session, stale CAS | Submissions with mismatched tenant, non-builder role, revoked session, or stale CAS revision -> rejected with `DeliveryGateError` / `StaleRevisionError` without mutation. | **PASSED** |
| **5** | Changed cryptographic identities | Mismatched candidate SHA, base SHA, suite digest, fencing generation, or altered issue policy -> rejected without mutation. | **PASSED** |
| **6** | Strict JSON and schema typing | Duplicate JSON object keys, `NaN`/`Infinity`, string-to-int coercion, boolean-to-int coercion, unknown manifest fields, or duplicate check IDs -> rejected during parse. | **PASSED** |
| **7** | Path traversal and unsafe archive entries | Zip archive containing directory traversal (`../`), absolute paths (`/`), backslashes (`\`), control chars, symlinks, or duplicate canonical names -> rejected before extraction. | **PASSED** |
| **8** | Archive size caps and digest validation | Overlarge compressed file (>12 MiB), header size lies, member count overflow (>64), decompressed stream overflow (>10 MiB total, >2 MiB/file), truncation, or SHA-256 mismatch -> rejected and resources closed. | **PASSED** |
| **9** | Git diff and scope boundary inspection | Git diff affecting files outside `brief.scope`, cross-scope file renames, symlinks (`120000`), submodules (`160000`), or mode changes -> rejected. Malicious option filenames parsed as data. | **PASSED** |
| **10** | Concurrency and idempotency CAS | Competing publication calls with identical revision -> exactly one winner succeeds; second call fails with CAS conflict. Replaying validation has zero side effects. | **PASSED** |
| **11** | Recurrence and scope pauses preserved | Task in `RECURRENCE_PAUSED` or `SCOPE_REQUESTED` cannot be submitted or cleared by the validator or CLI. | **PASSED** |
| **12** | CLI authority and privilege isolation | CLI output printing fake `PASSED` stdout or passing arbitrary actor strings cannot bypass service authorization; missing `--publish` leaves DB untouched. | **PASSED** |
| **13** | Clean wheel build and isolated package import | Building wheel `mas_core-0.2.0-py3-none-any.whl` and installing into an isolated virtual environment outside the git repo allows clean import of `mas.pm.delivery_validator`. Direct CLI invocation outputs truthful errors without repo checkout dependencies. | **PASSED** |

---

## 4. Review Findings Closure Table

Mapping of all findings and directives from `GHA_01_REVISED_ACCEPTANCE_REVIEW.md` to implementation:

| Finding & Directive | Severity | Resolution in GHA-02 Implementation | Status |
|---|---|---|---|
| **High 1: Neutral acceptance check / required checks semantics** | High | Contract §9.3 and Acceptance Matrix updated to prohibit `neutral` or `skipped` for required acceptance checks. Only `ACCEPTED` evidence emits success. Gated constraint for future GHA-05. | **Addressed in Contract** |
| **High 2: OIDC workflow pin, claims verification, and job authority** | High | Contract §5 updated with strict claims verification (issuer, audience, approved workflow SHA, replay bounds). Validator operates offline without live OIDC claims. Gated constraint for future GHA-03. | **Addressed in Contract** |
| **High 3: Freshness / idempotency transactional protocol** | High | Contract §6 updated with scoped logical action IDs and canonical payload digests. Validator enforces CAS revisions on local DB submissions. Gated constraint for future GHA-04. | **Addressed in Contract / Implemented in CAS** |
| **High 4: Builder-controlled readiness retry eliminated** | High | Builder cannot authorize retry or grant funding. GHA-02 implements no `retry_readiness` extension. | **Closed** |
| **Medium 1: Accurate reporting of ContainerBoundary limits** | Medium | Contract §4.2 and matrix updated with exact container parameters: 128 MiB RAM, 0.5 CPU, 32 PIDs, 32 MiB tmpfs, 1–64 KiB output limit with typed failure on overflow. | **Closed** |
| **Medium 2: `evidence_ref` path and content validation** | Medium | `validate_artifact_archive` validates safe POSIX relative paths, caps, and SHA-256 digests against real streamed bytes before submission. | **Closed** |
| **Medium 3: Pre-execution and validation failures do not fabricate successful runs** | Medium | Validation failures return structured `VALIDATION_FAILED` with zero database writes. Valid manifests with failing checks transition to `READINESS_RETURNED`. | **Closed** |
| **Medium 4: Ownership and dependencies corrected** | Medium | Check publisher assigned to Antigravity development team. GHA-05 dependent on GHA-04 freshness. GHA-07 single accountable delivery owner Antigravity. | **Closed** |
| **Medium 5: Module path conflict with existing code** | Medium | Implemented as dedicated module `mas/pm/delivery_validator.py` rather than refactoring `mas/pm/delivery.py`. | **Closed** |
| **Low: Bounded opaque intent/run IDs, status classification** | Low | Supported models use bounded opaque string IDs. Status fields clearly distinguished between `[Existing]` and `[Proposed]`. | **Closed** |

---

## 5. Verification Evidence

### 1. Targeted Integration Test Suite (`tests/test_gha_delivery_integration.py`)
```text
tests/test_gha_delivery_integration.py::test_scenario_1_valid_run_produces_in_review PASSED
tests/test_gha_delivery_integration.py::test_scenario_2_nonpassing_or_omitted_check_produces_readiness_returned PASSED
tests/test_gha_delivery_integration.py::test_scenario_3_ready_phase_or_unsuccessful_run_denied PASSED
tests/test_gha_delivery_integration.py::test_scenario_4_wrong_tenant_or_stale_cas_denied PASSED
tests/test_gha_delivery_integration.py::test_scenario_5_changed_identities_denied PASSED
tests/test_gha_delivery_integration.py::test_scenario_6_strict_json_and_types_enforced PASSED
tests/test_gha_delivery_integration.py::test_scenario_7_unsafe_archive_paths_rejected PASSED
tests/test_gha_delivery_integration.py::test_scenario_8_archive_size_and_digest_limits PASSED
tests/test_gha_delivery_integration.py::test_scenario_9_git_diff_out_of_scope_denied PASSED
tests/test_gha_delivery_integration.py::test_scenario_10_competing_publication_cas PASSED
tests/test_gha_delivery_integration.py::test_scenario_11_paused_task_cannot_be_cleared PASSED
tests/test_gha_delivery_integration.py::test_scenario_12_cli_execution_and_authority PASSED
tests/test_gha_delivery_integration.py::test_scenario_13_clean_import PASSED

============================== 13 passed in 1.01s ==============================
```

### 2. Core Delivery Process Regression Suite (`tests/test_delivery_process_gates.py`)
```text
============================== 47 passed in 1.26s ==============================
Combined: 60 passed in 2.14s
```

### 3. Wheel Packaging & Clean Environment Import
- Built wheel `mas_core-0.2.0-py3-none-any.whl` via `python -m build --wheel`.
- Created temporary virtual environment `/tmp/test_mas_import_venv`.
- Installed wheel and executed:
  `python -c "import mas.pm.delivery_validator; print('Import OK')"` -> Output: `Import OK`.
- Verified CLI script execution:
  `python scripts/delivery_gate_runner.py --help` -> Output: help usage printed cleanly.

---

## 6. Notes for Codex Architectural Reviewer

1. **Isolation of Delivery Service**: `mas/pm/delivery.py` was kept entirely untouched. The validator acts as a client layer consuming the existing delivery service API and SQLite schema.
2. **Offline Nature**: No external network requests, OIDC validations, or live GitHub Actions workflows are performed.
3. **Review Submission**: Submitted strictly for Codex review and acceptance under the delivery process gates.
