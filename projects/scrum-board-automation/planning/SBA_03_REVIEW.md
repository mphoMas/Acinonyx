# SBA-03 planning publication review

Candidate: `04eb5810`. Scope: deterministic plan publication and architect integration. Reviewer: Codex reviewing Antigravity implementation.

### 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK).** The planning API, clients and transactional persistence are implemented, and 59 selected planning/discovery/session tests pass independently. Disposable reproductions show that plan publication applies active scope changes before reconciliation, allocates execution appetite from proposed budgets and admits cycles involving existing dependencies. These violate core planning authority and integrity requirements.

### 2. Architectural Audit & Critical Findings

**High severity (blockers)**

- Active scope/acceptance changes are applied immediately by update_issue_from_plan after returning a reconciliation notice. Reproduced an IN_PROGRESS task changing from portal/ to mas/ while the response merely reports a pending notice. Impact: the effective execution/review contract changes before approval. Fix: persist proposed changes separately; preserve effective scope/acceptance/reviewer requirements until an authenticated reconciliation decision. Gate readiness/completion when relevant changes are pending. Test active and previously reviewed candidates.
- New issues get appetite_tokens from proposed_budget_tokens or an implicit 50,000 default. Reproduced publication without any explicit budget creating execution appetite 50,000. Fix: keep proposed budget metadata separate and initialize actual appetite to zero unless an independently authorized allocation exists; preserve existing execution allocations. Test that publication cannot manufacture readiness/spending authority.
- Dependency/hierarchy validation only traverses incoming tasks; existing nodes are treated as leaves. Reproduced existing B->A followed by revision containing A->B accepted as a combined cycle. Parent references are not fully validated; unknown parents are silently ignored, dependency removal is not reconciled and existing parent clearing is not handled. Fix: validate the complete effective graph inside the transaction, reject unknown/ambiguous targets and define safe graph replacement/reconciliation semantics. Test partial revisions and persisted graph cycles.
- Authenticated publishing role/project authority is not enforced by the service or MCP tool. pm_publish_plan falls back to an unbound 'architect'; HTTP uses generic write/tool guards rather than an explicit planning action. A direct unbound call succeeds in reproduction; this does not prove a remote unauthorized HTTP exploit. Fix: public publisher paths require authenticated architect/planning authority, explicit project access and fresh revocation checks. Keep any trusted local helper explicitly separate and unavailable to agent tools. Add MCP and tenant HTTP tests for ordinary operator, reader, cross-tenant, revoked and planning-authorized identities.

**Medium severity (fragility)**

- Existing mapping validation is outside the transaction and not rechecked after locking. Concurrent different plan IDs share mappings but have independent revision locks; revalidate all identities/graph against the locked snapshot.
- validate_path_scope accepts Windows backslash traversal and NUL-containing strings, while the delivery claims both are rejected. Normalize/reject unsafe cross-platform separators, NULs and unrestricted wildcard scopes according to the admitted scope policy. Models currently permit unknown fields and non-UUID IDs; define strict versioned schema and validate canonical identities and finite nonnegative budgets.
- Omitted items preserve rows but have no explicit archived-plan membership record. Persist actionable lifecycle/reconciliation decisions rather than only response notices.
- board_cursor is not demonstrated as the durable consistent change-feed cursor required by the shared contract. Label compatibility limitations and agree the cursor implementation with SBA-04.

**Low severity**

The handoff's DONE/IN_PROGRESS labels are not independently confirmed runtime PM states. Previous SBA-02/SBA-05 acceptance remains scoped development acceptance, not production qualification or automatic completion transitions. Correct claims accordingly.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** API/SDK/CLI/MCP paths exist; authenticated planning admission needs an explicit authority boundary.
- **Data & Schema Contracts:** persistence uses an explicit transaction, but effective graph validation and staged changes are incomplete.
- **AI & Model Runtimes:** natural-language interpretation is correctly outside the deterministic service. Proposed ownership/budget must not become agent execution authority.
- **Resilience & Governance:** supplied rollback/retry tests pass; untested concurrent identity conflicts and active-contract mutation remain blockers.

### 4. Architect's Action Directive

1. Stage active planning changes, separate execution appetite from proposed budget and enforce planning/project authorization across HTTP and MCP.
2. Validate/reconcile the complete effective graph and mappings in the shared transaction; add reproductions as regression tests before changing implementation.
3. Add strict schema/path and real tenant authorization/revocation tests; demonstrate actual architect publication and browser-visible records using disposable fixtures.
4. Submit the corrected candidate with lint and executed results. Do not advance SBA-04 on assumed SBA-03 completion.
5. Keep the Capable Coordinator Priority 1 workstream on this existing branch/board. SBA-03 is a supporting prerequisite for its scheduling; do not create a second delivery board or duplicate the existing dependency tickets. Coordinator runtime capability discovery can proceed independently of this rejection.

Verification: independently ran tests/test_sba_03_plan_publication.py, tests/test_sba_02_discovery.py and tests/test_sba_05_session_integration.py: **59 passed in 19.73s**. Disposable reproduction confirmed 50,000 actual appetite without allocation, accepted persisted dependency cycle and active scope mutation before reconciliation. Evidence: /workspace/review-evidence/sba-backend/sba03-tests.log and sba03-reproductions.json. No canonical runtime tickets transitioned; no full-repository gate or live architect-to-board acceptance claimed on this revision.
