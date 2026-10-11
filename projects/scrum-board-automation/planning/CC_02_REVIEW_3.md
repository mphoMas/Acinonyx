# Independent review — third coordinator resubmission

Reviewed 11 October 2026. Candidates: `7bcdd079` planning, `1359248d` probes, `5daa01b5` contract.

## 1. Verdict & Executive Summary

**SBA-03: REJECTED (REQUIRES RE-WORK).** Explicit administrative-token configuration and transactional audit improve the implementation, but name-based authorization and optional proposal binding remain confirmed blockers.

**CC-01: APPROVED WITH CONDITIONS for discovery only.** Synthetic probes are now labeled, descendant observation is improved, and a disposable Git candidate replaces the earlier bare diff. Deadline handling remains incorrect and live runtime cancellation/recovery is not qualified.

**CC-02: REJECTED as the governing implementation contract.** The new schemas and fencing discussion help, but the dispatch SQL contradicts the safe-stop policy and evidence signing does not bind the full stated identity envelope. CC-03 remains gated against this draft.

The new candidate includes frontend commit `77ba7083`; `portal/scrum.html` and `tests/test_scrum_board_actions.py` are unchanged from that commit. Frontend work was not overwritten.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

1. **Name-based unbound planning permission persists.** `mas/pm/tools.py` admits a whitelist of principal names and suffixes `:architect` or `:tenant_admin` without verified role/scopes. Disposable reproduction: `ExecutionContext.scope('unprivileged:tenant_admin')` successfully publishes through `pm_publish_plan` with no tenant binding. This is a local entry-point reproduction, not a demonstrated remote exploit. **Fix:** deny unbound exposed publication or validate explicit trusted authority independently of the name; test both allowed-looking names and suffixes.

2. **Proposal version binding is optional.** `reconcile_staged_changes` compares expected fields only when non-null; HTTP extracts optional values and passes them through. Disposable reproduction applies staged criteria without any expected proposal/version fields. **Fix:** require all binding fields in a strict request and service contract, reject missing/null/wrong-typed bindings, and reject stale decisions. Do not default a missing decision to apply. Preserve transactional decision audit.

3. **Evidence invalidation is incomplete.** Apply increments rework cycle only when evidence count is positive. With a changed policy and zero evidence, independent reproduction keeps the same cycle. Existing evidence guards do not check the new policy version, so counting links is not evidence invalidation. **Fix:** invalidate approvals on any relevant policy change independently of link count; bind admitted evidence to exact policy/candidate and reject stale evidence. Test verdict-only and existing-evidence cases.

4. **Contract redispatch hazard.** Section 4.1 CAS SQL makes expired PROCESSING intents claimable again. Fencing protects database writes, not external effects from an old worker. Section 5 describes unknown execution but the executable claim condition permits duplicate launch. **Fix:** claim only provably unlaunched intents; persist SPAWN_INTENT/launch uncertainty before spawning; send ambiguous expired work to reconciliation. Specify CLAIMED crash recovery, worker fencing and authorized settlement before retry.

5. **Signed envelope is under-bound.** Section 6 lists tenant/task/attempt/fencing/base/test/runner fields, then the HMAC formula signs only evidence ID, issue ID, candidate, content hash and policy. Unsigned identity fields can be substituted. **Fix:** sign a versioned canonical serialization of every security-relevant field, including run identity; define key ID/rotation, replay uniqueness, issuer admission and verdict envelope. Mark future guard enforcement as proposed rather than implemented.

6. **Persistence identity mismatch.** Contract task_id means stable planning UUID, but schema task_id references `pm_issues(id)`, the deployment-local issue UUID. **Fix:** introduce explicit issue_id and planning task_id mapping, tenant/project ownership consistency, intent-to-attempt foreign keys and uniqueness for admitted physical runs. Define which identity each constraint protects.

### Medium Severity

- Probe 1 remains blocking: checking elapsed time around `stdout.readline()` does not bound the read; `p.wait()` is also unbounded. Receipts record Antigravity at 34.67 seconds against a stated 15-second deadline. Use selectors/nonblocking or independently timed readers, bounded process-group cleanup and nonzero probe exit on unmet required criteria.
- Process cleanup measurement is still a controlled subprocess test; do not equate it with cancellation of each actual runtime or remote jobs. UNKNOWN_EXECUTION remains appropriate for unproven cases.
- Contract still lacks complete adapter requests/results/error schemas, event cursors, pause/cancel lifecycle and conservative budget reservation/uncertain spend settlement. Specify these before downstream runtime work; their persistence requirements must inform CC-03.
- Handoff lists old SBA task IDs such as `sba-uuid-sba-01`, which are not UUIDs and differ from Git backlog IDs. Preserve historical identity and provide a collision-checked mapping/migration proposal, not silent reassignment. The API smoke test lacks before/after preservation receipts.

### Low Severity

- `pytest tests/` is a test-suite invocation, not the five-stage repository quality gate. The reported 20 skipped tests did not execute; do not call all 604 tests executed. No new full-quality-gate acceptance is inferred.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Frontend preserved; schemas/fencing improve the draft but expired execution cannot safely be redispatched.
- **Data:** Transactional audits help; mandatory proposal bindings and stable versus local identities need correction.
- **AI:** Real disposable candidate review is better evidence; synthetic demonstrations do not qualify live interruption recovery.
- **Resilience/Governance:** Unbound authority, incomplete signatures and unbounded reads remain concrete weaknesses. No production approval is issued.

## 4. Architect’s Action Directive

1. Antigravity removes name-based planning authorization and makes proposal binding/decision mandatory; adds negative regressions.
2. Correct policy-based evidence/approval invalidation independently of evidence count.
3. Amend CC-02 claim/recovery SQL, schemas and full-envelope signing before CC-03 starts.
4. Bound probe I/O and process cleanup correctly; keep unmeasured capabilities unverified. Submit authenticated identity-preservation receipts.
5. Resubmit exact candidates and measured tests. Keep the existing branch and board. Frontend milestone `77ba7083` must remain included.

No backend application code or deployed board state was changed by this review. Live provider probes were not rerun. Independent disposable reproductions confirmed the authorization and optional-binding findings.

Independent validation: `python -m pytest tests/test_sba_03_plan_publication.py tests/test_sba_02_discovery.py tests/test_sba_05_session_integration.py tests/test_scrum_board_actions.py -q` in the existing project environment: **90 passed in 74.93 seconds**, including preserved frontend browser checks. No full repository gate was run on this rejected candidate.
