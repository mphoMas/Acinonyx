# GHA-02 independent implementation review

Date: 14 October 2026 (Africa/Johannesburg). Candidate: `ef6c5400`. Implementation owner: Antigravity. Reviewer: Codex. Scope: offline validator, CLI, tests and amended specifications against `ANTIGRAVITY_GHA_02_IMPLEMENTATION_BRIEF.md` V01–V07. No new acceptance of the author's underlying delivery-gate implementation is inferred.

## 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK) for GHA-02 acceptance.** The submitted 13 validator groups and 47 process tests pass, and the implementation uses literal Git arguments and retains independent evidence admission. Independent probes nevertheless reproduced artifact-validation bypasses, preconstructed-model input bypass and CLI schema writes before authentication denial. These violate the existing V01/V04/V06 requirements rather than introducing new product scope. GHA-03 remains dependency-gated.

No live workflow, provider, branch setting or operational project was changed. All probes used disposable private fixtures; reaching IN_REVIEW is not reaching ACCEPTED or trusted completion.

## 2. Architectural Audit & Critical Findings

### High severity — acceptance blockers

**B1. Empty archives skip observation membership and digest checks.** In `mas/pm/delivery_validator.py`, the observation loop is guarded by `if members:`. A well-formed empty ZIP returns `{}` with no error; nonempty PASSED observations naming absent artifacts therefore remain valid. **Reproduction:** completed private run + two PASSED observations + empty archive -> `valid=True`; ordinary authorized fixture publication -> IN_REVIEW. **Impact:** readiness can claim validated evidence that has no bytes. **Fix:** validate every supplied reference regardless of member count; missing artifacts must fail without publication. Define zero-observation handling separately: incomplete claims may be readiness returns, but cannot be considered all-passing. Verify no premature acceptance and no successful-phase advance on failed validation.

**B2. Typed instances explicitly bypass schema revalidation.** `validate_delivery_manifest` directly assigns input when `isinstance(..., DeliveryManifest)` instead of invoking model validation. `revalidate_instances='always'` does nothing when validation is never called. **Reproduction:** parsed valid manifest `.model_copy(update={'schema_version':'wrong-schema','brief_version':True})` -> `valid=True`. **Impact:** version/type guarantees differ by input route, recurring the exact preconstructed-input failure family already addressed in the core gate. **Fix:** normalize/revalidate and defensively copy every supported route; JSON/bytes/dict/model paths must have the same strict contract and bounds. Add model_construct/model_copy and nested-instance probes, not only JSON examples.

**B3. ZIP validation trusts normalized names and header-capped reads.** Two independent cases reproduced:

- A raw ZIP member `evil\x00name` is accepted as `evil` because ZipInfo truncates filename before `_validate_safe_member_path`; original filename still carries the NUL.
- A STORED member physically contains 2,097,153 bytes, but forged local/central uncompressed size=1 and matching prefix CRC make ZipExtFile return one byte. Validator accepts `size=1`, because its reader stops at the declared size rather than checking the full stored payload.

**Impact:** required name rejection and actual byte completeness/size guarantees are false. **Fix:** inspect original names before normalization/truncation; validate supported regular-entry metadata. STORED compressed/uncompressed sizes must agree. DEFLATE validation must account for actual bounded output and complete stream termination, reject trailing/hidden data and reconcile local/central metadata and CRC, without unbounded decompression. Do not treat a header-limited read as proof all member bytes were checked. Add forged-header, original-NUL and compression-stream tests across the entire ingestion boundary.

**B4. CLI accepts prohibited DB override and mutates before authority denial.** `scripts/delivery_gate_runner.py` accepts required `--db`; publication constructs PMDatabase(args.db), which initializes/migrates schema before DeliveryService checks identity. Standalone CLI provides no authenticated tenant configuration. **Reproduction:** disposable completed fixture with ancillary `pm_idempotency_keys` table removed -> `--publish` recreates the table, then reports PUBLICATION_FAILED for unbound authority. The task remains AWAITING_SUBMISSION, but the database is not unchanged. **Impact:** explicit V06 no-path-override/no-mutation-before-authority requirement is violated. This is a privileged-local-path defect, not a demonstrated remote unauthorized exploit. **Fix:** keep CLI pure offline claims validation; remove publication and arbitrary live DB selection. Use a trusted configured snapshot/input for pure mode, explicitly unverified for authority. Real publication belongs in the existing authenticated SDK/service path with tenant-owned database/repository resolved by trusted configuration before writes. Never initialize a caller-selected PMDatabase to authenticate later.

### Medium severity — complete related-boundary correction

- `publish_submission` treats caller-constructible, shallow-frozen ValidationResult and its mutable submission_payload as proof validation happened. Bind publication to actual source material/trusted context and repeat required validation against the current snapshot; an invented valid flag or post-validation mutation must not bypass collection checks. Existing DeliveryService still enforces roles/run ownership, but that does not verify archive bytes or Git scope.
- CLI reads the entire manifest via read_bytes before enforcing the1 MiB limit. File inputs use separate stat/open and can be symlinks/changing files. Bound reads on a single verified regular-file descriptor and limit actual compressed source bytes, not just a pre-open stat. Add explicit time/output bounds and deterministic failure to Git subprocess collection; diff output is currently buffered without limits/timeouts.
- Manifest lacks explicit policy/intent/fence identity fields requested by V01/V02; DB current checks help but do not bind the full submitted observation context. Use the agreed full identity schema and validate it on all routes.
- Duplicate/unknown references and closure path bounds must be normalized consistently. Empty archive/member mapping, invalid UTF8, original path bytes and undeclared archive entries need explicit policy; do not expose raw uncontrolled exception content as unbounded output.

### Low severity — evidence and coverage corrections

- `GHA_02_DELIVERY.md` still names `08532642`, not submitted `ef6c5400`, and describes posixpath.normpath even though code does not use it. Correct actual code/results, not just intended features.
- Thirteen named groups do not establish every variant of thirteen matrix rows. Current tests do not exercise real revocation/wrong assigned role, all omitted checks, original NUL names, symlink archives, forged ZIP sizes, real concurrency, or a clean installed-package execution. The concurrency group performs sequential calls; import group imports the working tree. State these limits and implement the actual agreed variants.
- The initial local test invocation used the host child python3 and failed CLI imports; configured venv PATH resolved it. Prefer sys.executable in subprocess tests and verify clean installed script behavior with isolated Python. Do not classify that environment mismatch as an implementation security defect.
- No final full-gate completion result is included in the submitted delivery. Selected stages/suites and a launched gate are not equivalent to the required five-stage receipt.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** literal Git command arguments and offline boundary direction are retained. CLI identity/database selection and collection resource bounds remain incomplete.
- **Data:** artifact-to-observation correspondence and full-member bytes are not reliably validated. Typed inputs and validation/publication context need consistent binding.
- **AI/model runtimes:** no live agents or trusted general-test signing activated. The validator must not promote fake completeness to readiness; independent verification remains necessary.
- **Resilience/governance:** core CAS, role and signed acceptance controls remain intact. Validator failure must not mutate schema, erase returns or bypass pause states.

## 4. Architect's Action Directive

1. Reproduce B1–B4 as regression tests before fixing them; retain actual expectation of failure/no mutation, not permissive fixtures.
2. Use `ANTIGRAVITY_GHA_02_REWORK_BRIEF.md` for the whole input/artifact/publication boundary correction. This is the existing requirement set; no OIDC, workflows or new business functionality.
3. Close related routes, source handles and stream cases in one closure matrix. If the same invariant survives correction, follow the recurrence/design-pause rule rather than another symptom patch.
4. Reproduce configured targeted tests, real adversarial variants, clean installed package and final full gate after code freeze. Record actual skips and failures. Submit exact candidate for independent acceptance; keep GHA-03 gated.

## Independent evidence

- Configured targeted command: `PATH=/workspace/venvs/acinonyx/bin:$PATH python -m pytest tests/test_gha_delivery_integration.py tests/test_delivery_process_gates.py -q`: **60 passed in 2.94 seconds**, no failures/skips. Ruff passed for mas/tests/script.
- Private probe results: empty_archive_validated=true; empty_archive_publication_phase=IN_REVIEW; invalid_preconstructed_model_validated=true; nul_member_accepted_as=['evil']; oversized stored payload2,097,153 validated size1; schema_recreated_before_authority_denial=true.
- Evidence: `/workspace/review-evidence/gha02/adversarial-probes.json`, `cli-side-effect-probe.json`, `targeted-configured.log`. No full gate repeated after confirmed blockers; no application code changed by reviewer.
