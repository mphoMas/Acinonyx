# Independent review — fourth coordinator resubmission

Date: 11 October 2026. Candidates: `70f2d2d0` (SBA-03), `e238f7d6` (CC-01), `6d8ac613` (CC-02).

## 1. Verdict & Executive Summary

**SBA-03: REJECTED (REQUIRES RE-WORK) for completion acceptance.** Name-based unbound authorization is removed, proposal bindings are required, and policy changes invalidate review cycles independently of evidence count. Remaining evidence binding and strict HTTP validation gaps prevent acceptance of the claimed corrections.

**CC-01: APPROVED WITH CONDITIONS for discovery and bounded adapter design.** Nonblocking reads and truthful synthetic classifications address the main prior findings. Live runtime cancellation and interrupted execution recovery remain unverified; no automatic retry permission follows.

**CC-02: REJECTED as the governing dispatch implementation contract.** PENDING-only claims and full-envelope signing are substantial corrections. Pre-spawn and completion transitions still need state/lease fencing to prevent stale workers changing reaped state. Existing database migration constraints must be made explicit before CC-03 relies on the supplied schemas.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Evidence policy is unsigned and optional.** `validate_evidence` accepts links with missing policy_version and accepts matching versions without including that field in the current provenance signature. Candidate test binding is also optional. Independent disposable reproduction: sign evidence under policy 1, advance issue to policy 2, change only the evidence payload policy_version to 2, and validate using original signatures. Validation succeeds. Git-object resolution was disabled solely to isolate policy binding; log hash and signature checks ran. This demonstrates evidence admission weakness, not a remote storage-tampering exploit. **Fix:** require immutable policy/candidate bindings and protect them cryptographically at trusted admission; quarantine legacy unbound evidence or explicitly restrict compatibility to a reviewed local mode. Do not stamp current policy onto an arbitrary historical submission as proof it was measured under that policy. Test missing binding, relabeled payload and cross-candidate evidence.

2. **Pre-spawn gate permits stale worker resurrection.** Contract section 4.2 updates PROCESSING by intent ID/worker/fencing only, without requiring CLAIMED or an unexpired lease. The CLAIMED reaper can mark FAILED without specified fencing advancement; a delayed worker can then set PROCESSING and launch. Section 4.4 similarly allows COMPLETED after state cancellation/reconciliation if generation is unchanged. **Fix:** require expected state, worker, generation and live lease for spawn authorization; require exactly one successful row update before spawn; atomically advance/retire generations on reaping/cancellation and enforce state predicates for late results. Define all related attempt/run updates in one transaction. Add pause/reaper races to CC-03 acceptance criteria.

3. **Supplied schema is not an existing-database migration.** Contract redefines existing `pm_task_mappings` with different columns; CREATE TABLE IF NOT EXISTS cannot transform the current table. Intents still have no attempt foreign key and tenant/project/task consistency is asserted without enforceable schema or transactional validation. **Fix:** specify versioned additive migration, retain existing APIs/mappings and history, define composite ownership checks and intent-attempt linkage. Prove reopen/migration and cross-tenant mismatch rejection. Do not create a competing identity map implicitly.

### Medium Severity

- HTTP reconciliation model still coerces wrong types: independent evaluation of `expected_proposal_rev=True` and `expected_base_policy_version='1'` produces integer 1 values. The direct service is stricter, but HTTP conversion bypasses those checks. Use strict integers, forbid unknown fields and test HTTP bool/string/float inputs. The handoff's claim that wrong-type fields return 400 is not true for these inputs.
- Choose exactly one canonical signing representation; RFC 8785 and Python sorted JSON are not interchangeable generally. Specify key ID/domain separation and the complete verdict identity envelope, with tamper tests, before signature implementation.
- Adapter result schema requires known session ID, integer exit code and measured tokens for interrupted executions where these may be unavailable. Model uncertainty explicitly; preserve reservation/settlement holds. Tenant quotas and lease timeout are not mechanisms that stop remote jobs or provider billing.
- Keep human release approval separate from DONE/reviewer signature; the revised lifecycle table must not silently supersede existing release governance.

### Low Severity

- “15-field” envelope descriptions disagree with the larger example; use named/versioned schema rather than a stale field count.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Initial claim safety improves; stale transition fencing remains incomplete. No coordinator implementation has been certified.
- **Data:** Identity separation is clearer; real migration and ownership constraints must preserve the existing board.
- **AI:** Discovery supports adapter design, not proven in-flight recovery or autonomous delivery.
- **Resilience/Governance:** Explicit authorization and mandatory versioning improve planning; evidence provenance must bind the policy it claims to verify.

## 4. Architect’s Action Directive

1. Antigravity requires and protects policy/candidate evidence binding; adds relabel/missing-binding regressions without treating attachment-time stamping as trusted verification.
2. Make HTTP reconciliation strict and test wrong-type inputs at the actual endpoint.
3. Correct CC-02 state/lease/generation transition predicates and specify additive identity migration and relational consistency. CC-03 remains gated against the current draft.
4. Submit targeted and repository-quality-gate evidence for corrected code. Keep untested capabilities explicitly unverified and preserve frontend `77ba7083`.

Independent checks: `python -m pytest tests/test_sba_03_plan_publication.py tests/test_sba_02_discovery.py tests/test_sba_05_session_integration.py tests/test_scrum_board_actions.py -q`: **92 passed in 52.26 seconds**. No full quality gate or live provider probe was rerun. Evidence reproduction initially lacked a configured signing key; after supplying an ephemeral random key, it completed as described. No production credential was used or printed. No backend implementation or deployed board state was changed.
