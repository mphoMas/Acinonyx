# Review: SBA-02 discovery and SBA-05 session backend

Candidate: `c555b0ca` (discovery `8742c802`). Review scope: delivered backend, stated integration behavior and selected regressions. Reviewer: Codex reviewing Antigravity implementation; no self-certification of Codex frontend release.

### 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK).** Independently selected suites passed 76 tests, but disposable HTTP/database reproductions confirm identity and live integration defects. Discovery does not meet automatic remote synchronization or existing-project migration requirements. Neither SBA-02 nor SBA-05 is accepted as DONE.

### 2. Architectural Audit & Critical Findings

**High severity (blockers)**

1. **Caller-selected authenticated identity.** In server.py's session/login handler, shared dashboard-token login uses payload principal/tenant_id; without configured token it issues sessions without authentication. `_resolve_session_or_auth` also accepts an arbitrary Bearer when neither IAM nor dashboard token is configured. Reproduced valid shared-token login selecting `chief_architect`, HTTP 200. This replaces the earlier server-bound principal with a caller-selected actor. Fix: require authentication, resolve actor/tenant from verified authority or fixed server configuration only, reject forged claims and deny all unconfigured-auth write/login paths. Add tests proving client cannot select reviewer/coordinator identity and arbitrary Bearer is rejected.

2. **Tenant cookie bridge is broken.** SessionManager returns only iam_token_hash, but TenantDashboardRequestHandler reads sess.get('iam_token'), then calls tenant_scope with None. Reproduced tenant login/session GET 200, cookie GET /api/pm/projects 403. Durable cookie validation calls `_store.get_session`, which does not exist on IdentityStore; private in-memory session inspection also bypasses current principal/role/expiry authority verification. Fix: public IAM-backed browser-session validation supporting full session revocation, suspension, changed permissions, expiry and anchored authority failures. Do not fix by storing raw IAM tokens in PM SQLite or bypassing tenant_scope. Test durable IAM, actual tenant cookie GET/POST and revocation/outage end to end.

3. **Discovery is not remote synchronization.** sync defaults fetch_remote=False; startup and daemon use that default. Daemon only responds to local mtime changes, so unchanged local registry never fetches new remote commits. safe_git_fetch fetches objects but registry reconciliation reads working-tree content and HEAD. Fetch failure can still return healthy: reproduced sync(fetch_remote=True) with a failed fetch returning status healthy. Fix: periodically read the configured remote revision/registry through a safe isolated source reader without altering dirty worktrees, bind registry/path validation to that same revision and propagate remote failure as stale. Test real local bare-origin commits arriving after startup with unchanged working-tree mtime, dirty checkout, fetch failure and recovery.

4. **Existing project migration is absent.** Registry assigns fresh fixed SBA/PLG UUIDs; reconciliation rejects existing project keys with their original IDs. Reproduced an existing SBA key yielding stale instead of preserving/importing its identity. The actual initial local SBA was created before this registry and has a deployment-generated ID. Fix: implement an explicit reviewed stable-ID binding/migration preserving project, issue, evidence and review identities; detect genuine contradictions without treating legitimate legacy records as new projects. No destructive re-keying or direct operator SQL. Test existing SBA/PLG fixtures with tasks/evidence and distinct deployment IDs.

5. **Tenant discovery may reuse another tenant database.** The v1 projects route calls process-global get_project_discovery; its instance lazily caches get_pm_db() once. The tenant-aware tool accessor's dynamic binding is therefore bypassed on later calls, especially when startup initialized the global object outside a tenant context. Fix: bind discovery to explicit server/tenant database and source configuration; never cache request-resolved authority in a process-global singleton. Test two tenant servers plus unbound startup initialization and assert zero cross-tenant records.

**Medium severity (fragility / contract defects)**

- Portal remains unavailable in tenant mode: handler still denies non-/api/pm paths even with valid Bearer; reproduced /portal/scrum.html 403. No login page was delivered. Implement the agreed public nonprivileged login bootstrap and authenticated tenant portal; integrate actual browser cookie login, board reads and writes.
- No Origin/Referer enforcement or login CSRF bootstrap, logout skips authentication/CSRF, and cookies are always issued with secure=False. Reproduced cross-origin login 200 and CSRF-less logout 200. Implement configured origin validation, session fixation policy, CSRF protections and deployed HTTPS Secure cookies, with explicit loopback-only exception. Do not weaken CSRF to support tests.
- SessionManager grants broad default actions rather than deriving current claims; a permissions display is not enforcement. Verify each request through current IAM and scoped action authorization.
- Reconciliation updates projects one by one on separate transactions; later conflicts can leave partial changes despite a stale outcome. Prevalidate identities and reconcile atomically; test a conflict in a later registry entry.
- Missing project/planning directory invalidates the whole registry rather than recording the registered source inactive as required. Repository ID is owner/name rather than immutable GitHub ID. Define and test these behaviors against the contract.

**Low severity**

Changed-file Ruff check reports seven unused-import errors. Fix them and rerun the required gate. Do not claim full-repository verification from a selected suite. The pasted transcript also contains session/CSRF values; do not reproduce them in repository evidence, and invalidate any still-live disclosed session through authorized session administration.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** actual HTTP handlers were delivered, but tenant browser operation and remote discovery do not meet the required workflow.
- **Data & Schema Contracts:** source/mapping/session storage is present; legacy identity migration, atomic reconciliation and tenant-scoped discovery require rework.
- **AI & Model Runtimes:** no actual Antigravity event bridge is expected for SBA-02; agent activity and trusted verification remain later gates. Session claims must not grant arbitrary agent/judge identity.
- **Resilience & Governance:** CSRF header checks cover ordinary mutations, but login/logout/origin and IAM authority checks are incomplete. Failed source synchronization must not become healthy evidence.

### 4. Architect's Action Directive

1. Fix authority resolution and public IAM-backed tenant cookie validation first. Preserve all existing authorization guards; add negative tests described above.
2. Bind discovery per tenant, implement safe periodic remote-revision reads and failure freshness, and preserve existing project identities through a reviewed migration.
3. Deliver authenticated portal/login and complete CSRF/origin/cookie behavior; coordinate Codex UI login integration using the agreed session contract.
4. Add regression tests for every reproduced defect and real browser tests through the tenant-bound server. Use disposable data and configured authentication; no canonical board mutation as test setup.
5. Run changed-file lint, selected security regressions and the repository quality gate; submit actual commands/counts, candidate SHA, migration notes and remaining limitations. Tag Codex for re-review. Do not advance SBA-03 on an assumed SBA-02 DONE.

## Verification record

Executed: pytest tests/test_sba_02_discovery.py tests/test_sba_05_session_integration.py tests/test_scrum_board_actions.py tests/test_tenant_boundary.py tests/test_durable_identity.py -q: **76 passed in 25.45s**. This is selected coverage, not the complete repository.

Executed isolated reproductions: client-selected chief_architect login 200; cross-origin login 200; logout without CSRF 200; tenant login/session 200 but tenant cookie projects 403; tenant Bearer portal 403; existing SBA project reconciliation stale; failed remote fetch reported healthy. No submitted session secrets reused. Reproduction script/results and test/lint outputs are in /workspace/review-evidence/sba-backend/ and /workspace/review-evidence/sba-backend-review.log. Reviewed sources and git diff. No backend code changed during review. No release acceptance, full suite or real browser login success claimed.
