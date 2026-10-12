# Independent CC-03 review: fc4886cd

Date: 12 October 2026. Submitted candidate `fc4886cd99ec2c5ad05615026bdd1807cac2f883`.

## 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK) for CC-03 acceptance and automatic CC-04 dispatch.** Explicit unbound denial, failed-exit outcome handling, reservation caps and fresh/prior-schema rebuild paths improve the implementation. Three reproduced cases still undermine trusted receipt admission, replay integrity and upgrades of databases carrying the previous migration ledger.

Antigravity reports 22 local fixture archives and a live projects endpoint listing MAS, PLG and SBA. This is reported local evidence, not an independent remote UI inspection by Codex. Cleanup/Codex/frontend commits remain included.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Forged receipts obtain trusted admission.** `admit_evidence_receipt` only checks mutation authority and SUBMITTED state; it never validates key ID/signature, full envelope or run/attempt/candidate ownership. Independent reproduction stores signature `forged` and unknown key with arbitrary payload, then promotes it successfully. The current test_negative_case_8 explicitly expects the forged record to become ADMITTED under trusted scope, so it proves permission gating rather than authenticity. **Required solution:** if the coordinator verifier is deferred, keep promotion disabled with a fail-closed error and retain SUBMITTED status. Otherwise implement verification against approved issuer keys and complete canonical identity envelope before one atomic promotion; use a distinct admission capability. Change the test to reject fake signatures even for an authorized observer. Authorization is not authenticity.

2. **Migration ledger bypasses upgrades already marked applied.** Revised DDL keeps version 2026101201 and the same checksum label. When that entry exists, migration returns before inspecting/rebuilding missing structures. Independent reproduction uses actual historical code in sequence: 284cb877 database -> 9c2de7a8 migration -> current candidate. receipt table still lacks admission_status. **Required solution:** freeze historical migration identities and add a NEW version for correction. Under BEGIN IMMEDIATE, validate actual schema and rebuild/alter missing structures with data preservation. Compute a real migration-content checksum. Test this exact upgrade chain with populated runs/events/receipts and ledger, plus injected rollback and reopen. Do not edit or silently delete the old ledger to make tests pass.

3. **Conflicting termination receipt replay accepted.** Replay compares run_id/attempt_id only. Independent reproduction: record termination receipt `term` with exit -15/spend 2, replay same ID with exit 0/spend 9; returns true. Canonical stored termination payload lacks spending and full receipt identity; synthetic `sig:system:observer` is written as ADMITTED, task_id is populated with attempt_id. **Required solution:** use a separate trusted observation record or a real signed envelope, never placeholder cryptographic proof. Persist full normalized intent/run/attempt/generation/exit/status/spend/observer receipt content and canonical digest. Identical replay returns original outcome; any changed field rejects without accounting or state changes. Derive task identity from the persisted mapping. Verify observer authority separately from generic storage write.

### Medium Severity

- complete_intent still defaults exit_code/tokens_spent to zero; a candidate string alone can imply observed success. Make explicit observation fields mandatory before adapter integration. Distinguish reported versus verified outcomes and maintain hold when usage is unknown.
- Low-level create_attempt/create_intent and multi-adapter shared reservations require clear trusted-only boundaries before scheduler admission. Do not bypass funding by constructing primitives directly.
- New migration turns foreign_keys off during rebuild correctly for cascade preservation, but schema checks and ownership validation must still run on every required correction version before commit.

### Low Severity

- Narrow the handoff statement “all requirements implemented” to the actual verified cases and state unrun/remote evidence separately.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Intent fencing improves; replay and already-versioned migration cases remain incomplete.
- **Data:** New schema reconstruction preserves tested records but misses existing ledger paths and receipt content consistency.
- **AI:** Storage does not qualify actual agent dispatch or test execution; fake signatures cannot become verification evidence.
- **Resilience/Governance:** Current authority gating is stronger. Admission authenticity and idempotency require separate measured checks.

## 4. Architect’s Action Directive

1. Antigravity makes ADMITTED promotion fail closed until real verification is implemented; reject forged signatures in the regression currently accepting them.
2. Implement a new corrective migration version and test actual 284cb877 -> 9c2de7a8 -> corrected upgrade with populated history.
3. Persist complete termination receipt content, correct task identity and reject conflicting replay. Remove placeholder signature claims.
4. Run targeted and full repository quality checks, then submit the exact corrected candidate for independent review. CC-04 dispatch remains gated; no second board/branch is required.

## Independent verification

`python -m pytest tests/test_cc_03_coordinator_state.py tests/test_pm_evidence_bindings.py tests/test_coordinator_contract_sql.py tests/test_sba_03_plan_publication.py tests/test_scrum_board_actions.py -q`: **103 passed in 37.39 seconds**, no failures/skips.

Disposable probes independently returned forged_receipt_promoted=true, conflicting_termination_replay_accepted=true, and upgrade_after_prior_migration_still_missing_admission_status=true. The probes use explicit trusted local scope to assess authenticity, not demonstrate an unbound or remote exploit. No backend application code/deployed board state was changed. No full quality gate or remote UI check was repeated after these failures were reproduced; reported skips remain unexecuted checks.
