# Independent CC-03 rework review

Date: 12 October 2026. Candidate code `49ce36db`, submitted head `9c2de7a8`.

## 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK) for CC-03 acceptance and CC-04 dispatch.** Wrong-attempt rejection and cancellation request states improve the previous implementation. Tests pass, but fail-closed authority, outcome settlement and upgrades from the already-shipped CC-03 schema still have reproduced defects.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Unbound authority still falls through.** `_validate_tenant_authority` returns for trusted admin, validates a present binding, but does not raise when neither exists. Lifecycle methods do not consistently call it. **Reproduction:** outside any binding/admin scope, create_attempt_with_intent succeeds. **Fix:** explicit denial when unbound; authorize all mutations, not just creation. Resolve persisted tenant for ID-only methods and require current authority. Internal/local trusted scope must be deliberate, not implicit. Add unbound, read-only, revoked and mismatched-tenant tests for every mutation family.

2. **Failed execution is recorded as success and settlement can exceed reservation.** `complete_intent` has exit_code=0 by default, then unconditionally writes attempt SUCCEEDED. It accepts spend beyond allocation without authorization. **Reproduction:** reserve 10 against project budget 10, complete with exit_code=42/tokens_spent=20; attempt is SUCCEEDED and project consumed=20. **Fix:** require explicit validated outcome/receipt and measured usage; distinguish failed execution from successful candidate admission. Enforce funded limits or record excess as quarantined overrun requiring authorized settlement; do not silently overdraw capacity. Validate strict nonnegative integers and exactly-once settlement across all completion paths.

3. **“Authoritative termination” accepts no matching run and rewrites final state.** Method does not constrain starting intent state or require a matched run update. **Reproduction:** call record_authoritative_termination on a COMPLETED intent with nonexistent run ID; method returns true and intent becomes CANCELED. It settles reservation without adding measured termination spend to project consumption. **Fix:** authorize observer, bind run/intent/attempt/generation and receipt identity, require eligible cancellation/unknown state, check exactly one matching run, and atomically reconcile project spend/hold. Identical receipt replay must be idempotent; conflicting receipts and terminal-state rewrite must fail without mutation. Supplied exit_code alone is not an authoritative receipt.

4. **Migration does not upgrade existing CC-03 tables.** CREATE TABLE IF NOT EXISTS leaves the previously shipped schema untouched, then records migration success. **Reproduction:** create DB using actual `284cb877:mas/pm/db.py`, reopen with candidate: receipt table still lacks admission_status and run table still lacks composite intent/attempt FK. **Fix:** versioned migration must inspect actual schema, add compatible columns and rebuild constrained tables transactionally when necessary. Preserve rows/IDs/evidence and validate foreign_key_check. Reject ambiguous ownership rather than inventing it. Test both pre-coordinator DB and populated prior CC-03 DB. Use a real computed checksum, verify existing ledger checksum, and recheck after acquiring the database migration lock.

### Medium Severity

- Public create_attempt/create_intent primitives can bypass funded reservation admission; zero reservation with arbitrary authorization_ref does not prove execution authorization. Distinguish trusted low-level persistence from scheduler-admissible funded intents.
- Evidence receipt caller can supply admission_status=ADMITTED with unchecked signature and ownership. Always store raw submissions as SUBMITTED; expose trusted promotion separately with verified authority and signature/identity checks.
- Multiple adapter intents share an attempt/reservation; define aggregation and prevent independent completions billing or settling the same attempt twice.
- Delivery gate labels do not match scripts/run_quality_gate.sh: actual gates are Ruff, CLI doctor/capabilities, research links, compilation, pytest. Correct the recorded labels; skipped tests did not execute.

### Low Severity

- Replace “all blockers resolved” with measured scope until negative acceptance cases pass.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Intent CAS is useful; safe lifecycle transitions and upgraded constraints are required before a daemon uses it.
- **Data:** Prior-schema migration fails to establish declared structure; receipt and ownership consistency need enforcement.
- **AI:** No live runtime qualification is inferred. Storage must not fabricate authoritative success or termination.
- **Resilience/Governance:** Reservation holds exist, but authorization and conservation across settlement paths are incomplete.

## 4. Architect’s Action Directive

1. Antigravity fixes explicit unbound denial and authorization across all mutation families.
2. Require validated outcomes/termination receipts and enforce state, identity, generation and idempotent budget conservation.
3. Implement and test upgrade from the actual previous CC-03 schema, preserving populated history and rejecting contradictory records.
4. Add the reproduced negative cases before rerunning targeted and full quality checks. Submit exact candidate hashes for independent review; CC-04 remains gated. Keep the same SBA board/branch and preserve frontend and Codex fix commits.

## Independent evidence

Targeted command: `python -m pytest tests/test_cc_03_coordinator_state.py tests/test_pm_evidence_bindings.py tests/test_coordinator_contract_sql.py tests/test_sba_03_plan_publication.py tests/test_scrum_board_actions.py -q`: **95 passed in 50.10 seconds**, no skips/failures.

Disposable reproductions confirmed unbound admission, failed exit marked SUCCEEDED, consumed budget 20 against reservation/project 10, missing-run receipt rewriting COMPLETED to CANCELED, and missing schema changes after upgrade from actual prior commit. No agent processes, production credentials or deployed board were used. No backend application code was changed. The reported full gate with 20 skips was not independently rerun after these blockers were reproduced.
