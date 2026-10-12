# Independent CC-05 / CC-06 implementation review

Date: 12 October 2026. CC-05 `961acefa`; CC-06 `52c53756`. Reviewer: Codex. Existing CC-03 and controlled-only CC-04 acceptance refer to their reviewed baseline; neither qualifies these newly added live adapters/admission changes.

## 1. Verdict & Executive Summary

**CC-05: REJECTED (REQUIRES RE-WORK). CC-06: REJECTED (REQUIRES RE-WORK).** The submission provides CLI wrappers and HMAC plumbing, but does not enforce isolated candidate execution, trusted verification provenance or complete descendant termination. Existing tests mainly qualify simulated transport and currently promote simulated evidence as trusted admission. No live dispatch or new evidence admission is approved.

Workspace startup initially blocked downloads; once ready, the default command network sandbox could not reach the configured proxy. Authorized commands outside that restricted sandbox successfully fetched the candidates through the existing session proxy. Environment access was resolved; the findings below are repository defects.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Developer execution is not contained and receives verifier secrets.** antigravity.py sets cwd/--add-dir and --dangerously-skip-permissions, then passes dict(os.environ) without actually stripping governance credentials. No filesystem/process/network isolation or path whitelist enforcement exists. Independent simulated child reports MAS_EVIDENCE_SECRET present using an ephemeral random test key (value never printed). **Impact:** builder can access signing authority and host resources, defeating separation from verification. **Fix:** execute in an enforceable restricted boundary; allowlist only required provider/proxy/CA/runtime environment and deny verifier/reviewer/administrative/Git signing credentials. Preserve TLS/proxy configuration without copying all secrets. Scope tools/files/network and prove forbidden writes/secret access reject.

2. **Process-tree cleanup reports success while a descendant survives.** _terminate_process_group returns true when parent exits; it never confirms descendant disappearance. Independent bounded child ignores SIGTERM, parent exits on SIGTERM, cleanup reports cleaned=true, and child writes a file after adapter return. Natural parent exit has the same missing-descendant reconciliation risk. **Fix:** supervise the whole managed execution boundary and escalate/reconcile descendants even after parent death. Observe termination and pipes within cleanup deadline. Unknown remote/escaped effects remain uncertain; do not assert guarantee from parent poll alone.

3. **Verification is independent of the named Git candidate.** VerifierAdapter accepts strings of length >=7 but never resolves candidate/base, checks out a candidate workspace, binds a trusted test contract or selects cwd. subprocess.run executes in the current process directory. Independent probe names a nonexistent 40-character commit and runs a trivial command; receipt passed=true and test_count=1. **Fix:** resolve exact immutable objects in the authorized repository, verify ancestry/scope and test-contract hash, execute candidate in isolated workspace with trusted checks, collect actual runner counts/results and bind policy/fence/run/image/runner. No tests or missing provenance must fail closed. Bound resource/output/process cleanup.

4. **Simulation and public default keys create “trusted” evidence.** Both signer constructors fall back to mas-default-development-secret; neither requires a private minimum-length key. simulate_result and simulate_verdict use the same signed/admitted path as real execution. Independent simulated passing receipt verifies with the public literal default key. Current CC06 test explicitly admits canned passing evidence for nonexistent commits. **Fix:** remove public fallback; require configured trusted issuer key and role, separate test-only signing domain/key from production admission, and prohibit simulated evidence promotion. Restore fail-closed admission until the trusted verifier implementation qualifies. Do not invent test counts or evidence to pass integration.

5. **Admission trust/binding is incomplete.** admit_evidence_receipt takes trusted_keys per call, uses generic mutation authority, compares only selected receipt fields, and does not bind tenant/project/issue/policy/attempt sequence/generation/base/test contract/issuer role to current persisted ownership. Builder identity checks elsewhere are optional caller-supplied strings, not verified runtime principals. **Fix:** bind a service-owned issuer/key registry and dedicated admission capability, derive builder/verifier/reviewer from authenticated ownership, validate the complete strict envelope and current policy/candidate/fencing, then promote atomically with replay controls. Caller parameters cannot establish key trust or separation of duties. This is an internal API defect, not a demonstrated remote exploit.

6. **Reviewer accepts substring approval and wrong repository context.** CodexReviewerAdapter runs without cwd/candidate workspace verification and treats any stdout containing APPROVED as approval, including “NOT APPROVED” or quoted prompt content. **Fix:** schema-validated terminal review result bound to actual immutable candidate and empirical verifier receipt; nonconclusive/malformed/contradictory output remains a claim. Use measured subprocess cleanup and configured explicit model validation. A model verdict cannot authorize production release.

### Medium Severity

- Model availability is a hardcoded list: query_available_models ignores binary_path, discovery/version validation is not called by adapter initialization, and allowed_models can replace the set. Query actual supported discovery interface and validate requested model against measured target runtime; fail without silent substitution.
- stdout/stderr lines accumulate without byte/event bounds and raw payloads are emitted. Bound memory/output/context, sanitize secrets and quarantine malformed streams rather than forwarding arbitrary tool transcripts.
- canonical_json is Python sorted JSON with ASCII escaping, not RFC 8785. Independent example x=1.0 serializes as 1.0 rather than JCS 1. Choose a correctly implemented versioned serialization contract; do not claim JCS compliance without conformance vectors.
- Early session capture stays only in local variables/callbacks; persistent authoritative session/turn/run binding and crash recovery need integration proof. Return statuses do not themselves prove measured billing or actual candidate existence.
- Full gate labels in the handoff do not match scripts/run_quality_gate.sh. Correct labels and distinguish skipped from executed tests.

### Low Severity

- Use measured capabilities and exact environment/version references rather than “strict isolation” and “guaranteed termination” until qualified.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Process groups/cwd are insufficient for containment; subprocess wrappers need owned isolated execution boundaries and whole-tree recovery.
- **Data:** HMAC can protect bytes but cannot make nonexistent candidate/test execution true. Complete ownership and semantic contracts are missing.
- **AI:** Live Antigravity/Codex workflows are not qualified; simulation and free-text approval cannot become trusted evidence.
- **Resilience/Governance:** Builder secret inheritance, known signing key, caller-controlled authority and incomplete cleanup are deployment blockers.

## 4. Architect’s Action Directive

1. Antigravity disables new evidence promotion/simulation-to-trust and removes public signing defaults before any live activation. Preserve accepted foundations and registry gating.
2. Implement restricted developer environment and real managed termination; add the inherited-signing-key and surviving-descendant regressions.
3. Implement exact-candidate trusted test execution with genuine failing/zero-test scenarios, then authenticated full-envelope admission. No simulated receipts in production key domain.
4. Make reviewer output strict and candidate-bound, runtime/model discovery real, stream budgets bounded and serialization honestly specified.
5. Run negative acceptance cases plus repository quality gate, submit separate corrected CC-05/CC-06 hashes and measured limitations. Same branch/board; no self-certification or live registry activation.

## Independent verification

Reported targeted command independently rerun: `python -m pytest tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_cc04_scheduler_worker.py tests/test_cc05_antigravity_adapter.py tests/test_cc06_verifier_reviewer.py -q`: **71 passed in 3.32 seconds**, no failures/skips.

Independent disposable probes confirmed nonexistent candidate passed=true/test_count=1; developer child inherited a random ephemeral verifier secret; simulated receipt signed with public default key; claimed process-group cleanup true followed by a late descendant file write; and non-JCS float serialization. No live models, production secrets or deployed board were used. No backend implementation changed. Full repository gate was not independently rerun after these blockers were reproduced; reported skipped checks remain unexecuted.
