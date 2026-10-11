# Codex takeover: coordinator review corrections

Date: 11 October 2026. Owner explicitly authorized Codex to implement these backend fixes because Antigravity was struggling. This is a scoped exception to the normal delivery ownership agreement, not a permanent ownership change. Baseline: `efa5315e` (implementation candidate `6d8ac613`). Frontend `77ba7083` remains included and unchanged.

## What changed

- PM evidence provenance version 2 signs the full JSON payload, immutable evidence metadata and a domain/version marker. Altering policy, candidate, runner or result invalidates the original signature. Existing legacy signing remains available only for historical integrity inspection; completion guards require the bound v2 format.
- Evidence attachment requires an explicit positive policy version; test logs require an explicit candidate. Neither the tool nor database invents current-policy measurement claims. Git candidate binding derives from its immutable supplied reference and cannot contradict it. Supplied signatures are verified before insertion.
- Verification rejects legacy/unbound evidence, stale policies and missing/mismatched test candidate bindings. Historical records are retained; policy changes do not rewrite them or silently re-sign them.
- Reconciliation HTTP models reject boolean/string/float version coercion and unknown fields.
- CC-02 contract now requires expected state, active lease, worker and generation before pre-spawn and completion; reaping/cancellation retires generations. Related attempt/run changes must be atomic and spawn requires exactly one successful row update.
- CC-02 retains the actual existing identity mapping table, defines additive versioned migration with collision checks, and adds composite attempt/intent ownership constraints. Coordinator storage/dispatch is still a proposal for CC-03; it has not been implemented here.
- Corrected inherited Ruff failures (missing sqlite3 annotation import, misplaced imports, unused imports).

## Compatibility and limitations

Old operational evidence producers that omit policy/candidate bindings now fail closed. Update those producers to include the policy and candidate actually measured before using them. Do not fill in today's values merely to make a legacy ratification script pass. Historical evidence can be inspected, but requires fresh candidate-specific trusted verification before qualifying under current policy.

Database signatures attest the integrity of an admitted claim. They do not themselves prove tests executed. The trusted verifier and full coordinator evidence envelope remain separate implementation gates. No real agent dispatch, remote cancellation, production deployment or identity migration was performed.

## Validation

Affected PM/security suites: **83 passed in 9.15 seconds**, including 19 new evidence-binding and strict-model regressions.

Actual proposed SQL exercised against the existing SQLite PM schema: claim competition, expired lease, reaper resurrection, cancellation/late completion and ownership mismatch. The claim test uses two independent SQLite connections concurrently. These are contract design checks, not an implemented coordinator runtime.

Latest targeted run including the concurrent contract tests and actual HTTP strict-input checks: **37 passed in 13.13 seconds**.

Initial negative results were diagnosed and corrected: two legacy provenance fixtures used the former signature interface; the first SQL race fixture omitted required issue fields and was corrected to use supported issue creation. No assertions were disabled or tests skipped to obtain these results.

Independent review remains required: Codex authored these fixes and does not certify its own work as independent acceptance. Antigravity should review the exact candidate, inspect the new attack regressions and contract predicates, and run candidate-specific checks before treating CC-03 as admitted. Keep the existing SBA branch and board; do not overwrite frontend work or self-mark tasks DONE.


Full five-stage repository quality gate: **625 passed in 253.74 seconds; zero failures or skips**, including actual Docker containment/recovery checks. Log: `/workspace/review-evidence/coordinator-takeover/quality-gate.log`. The five SQL contract tests and eight strict HTTP cases were added after that run collected its tests; all passed in the later 37-test targeted run (which also repeats existing planning checks). These counts must not be summed as independent tests. Final Ruff and patch checks passed.
