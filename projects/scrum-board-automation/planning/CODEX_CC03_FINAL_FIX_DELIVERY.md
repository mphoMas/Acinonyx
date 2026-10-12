# Codex CC-03 correction delivery

Date: 12 October 2026. Baseline: fc4886cd / independent review c64828d0. The owner explicitly asked Codex to implement the remaining fixes. This is a scoped ownership exception. Existing frontend, fixture cleanup and evidence-binding work is preserved.

## Implemented corrections

1. **Evidence admission fails closed.** admit_evidence_receipt denies promotion even for a trusted administrator until coordinator envelope/key verification is implemented. Raw receipts remain SUBMITTED. The old test accepting a forged signature as ADMITTED now explicitly rejects it. This is deliberate fail-closed deferral, not implementation of the future verifier.

2. **Exact termination observations.** Accounting observations now live in pm_coordinator_termination_observations, separate from cryptographic evidence. They contain canonical tenant/project/issue/task/intent/attempt/run/generation, observer, status, exit and measured-spend fields plus a SHA-256 digest. These are trusted observations, not fabricated signatures. Exact replay returns the prior outcome; any changed field fails without rebilling or state updates, both with explicit receipt IDs and the stable per-run default identity. Real task identity is recorded. Generic tenant storage write is insufficient for observation: a bound observer needs coordinator:observe in addition to existing mutation authority, while explicit trusted local administration remains supported.

3. **New migration version.** Corrective version 2026101202 runs independently of the historical 2026101201 ledger. Old entries remain unchanged. The actual migration source is SHA-256 checksummed, checked on reopen; future modifications to this migration require a new version. The existing rebuild/foreign-key/integrity checks now run for databases the prior migration incorrectly marked applied. The correction adds the observation table and quarantines old unverified ADMITTED receipt labels as SUBMITTED without rewriting receipt payload/signature bytes.

## Regression evidence

Affected coordinator checks: **33 passed in 0.70 seconds**.

The historical SQL fixture was generated from actual repository schema code in the sequence 284cb877 -> 9c2de7a8, with populated project, issue, mapping, attempt, intent, run, event, receipt and migration ledger. The committed fixture is disposable synthetic data; tests require no historical Git objects or production credentials. Upgrade/reopen preserves history and ledger, installs the missing column/composite foreign key, and verifies database integrity. An injected mid-migration failure leaves the old ledger/schema/history intact and can be retried successfully.

Replay checks cover changed exit, status and spend with/without receipt IDs. No placeholder candidate, key or signature is inserted as admitted evidence during termination accounting.

## Independent handoff

Codex authored this implementation; it is not an independent acceptance verdict. Antigravity should review the exact candidate, rerun candidate-specific negative checks and record storage-only acceptance or concrete findings. Do not rewrite passing code without evidence of a defect. CC-04 dispatch remains gated until that review accepts the storage foundation. No live agent runtime, production activation or remote observation was exercised here. Future cryptographic admission belongs to its verifier milestone and must not be bypassed to move work to DONE.

Suggested review checks:

```bash
python3 -m pytest tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_pm_evidence_bindings.py tests/test_coordinator_contract_sql.py tests/test_sba_03_plan_publication.py tests/test_scrum_board_actions.py -q
bash scripts/run_quality_gate.sh
```

Keep the existing SBA board and branch. Do not self-mark runtime tickets DONE or claim this correction has automated Codex/Antigravity communication.

## Final repository verification

All five stages of `scripts/run_quality_gate.sh` passed. Full suite: **672 passed in 207.07 seconds**, zero failures/skips. This includes the nine new correction regressions, migration preservation/rollback, frontend checks and actual container containment/recovery checks. Log: `/workspace/review-evidence/cc03-codex-fixes/quality-gate.log`. Ruff and `git diff --check` passed. The 33-test affected run overlaps the full suite and is not an additional unique-test count.
