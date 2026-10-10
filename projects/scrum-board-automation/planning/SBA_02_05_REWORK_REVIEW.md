# SBA-02/SBA-05 rework review

Candidate: `d19b0924a67edbd0e82d54f385e01031a89a5a43`. Reviewer: Codex. Scope: revised backend and submitted browser evidence.

### 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK).** The earlier caller-selected identity and missing tenant cookie context were corrected, and 87 selected tests plus lint pass independently. However, discovery/session services and tenant PM routes use different database paths, reconciliation still is not transactional, durable suspension fails, and the browser evidence falsely asserts populated tickets without checking them.

### 2. Architectural Audit & Critical Findings

**High severity (blockers)**

1. **Two incompatible tenant database paths.** DashboardServer binds its session/discovery DB to `tenant_root/pm.db`; tenant_scope binds PM requests to `tenant_root/state/<isolated tenant path>/pm.db`. These paths are different. Server-bound discovery inside tenant scope may consequently fail PMDatabase's binding check, while legacy project reads see another database. Independent rerun of record_browser_evidence.py signs in successfully but screenshot shows No project / 0 issues, not the seeded SBA-1/SBA-2. Fix: resolve one tenant state database using the existing trusted tenant path resolver and use it consistently for server services, request bindings, fixtures and discovery. Test v1 project reads plus legacy board reads against the same seeded data, with two tenant servers sharing a root and no leakage.

2. **Atomic reconciliation remains false.** `_reconcile_unlocked` opens `with conn:` but PMDatabase connections use isolation_level=None, and create_project/update_project/upsert_project_source each open another connection. This does not begin a shared transaction. Injecting an exception in source insertion after project creation leaves the project persisted. Fix: use one explicit BEGIN IMMEDIATE transaction and pass that connection through every reconciliation read/write; move conflict checks into its snapshot. Test failures after each mutation and concurrent writers, asserting unchanged original rows and no newly committed partial records.

3. **Durable suspension API fails.** MultiTenantIAM.suspend_principal calls IdentityStore.revoke_principal_sessions with two arguments; the actual method requires actor, user_id and permission_check. Disposable durable IAM reproduction raises TypeError. Fix: use an authenticated, authorized public operation with an audit-consistent principal suspension/removal policy and session revocation. Do not bypass the durable store's permission callback or silently treat session revocation as durable suspension. Test persistence after restart and suspended principal cannot issue/use sessions.

4. **Browser acceptance evidence does not assert the claimed records.** record_browser_evidence.py appends “Board rendered live issues SBA-1 and SBA-2” without checking cards or project content. It also seeds DONE/IN_PROGRESS directly as display fixtures, not independently verified workflow states. Independent rerun printed success although the screenshot showed no projects. Fix: explicitly assert expected project, card keys and count; label fixtures synthetic and never use seeded DONE as workflow proof. Add actual create/transition/revocation interaction tests through the same tenant-bound browser. Correct BROWSER_EVIDENCE_REPORT.md and delivery claims around the failing candidate.

**Medium severity (implementation constraints)**

- Browser validate_session creates context from current principal roles/scopes without the original token's role/scope ceiling. Under an in-memory current-authority change without replacing the session, reproduced cookie validation returning tenant_admin/storage:write while verification of the original bearer retains no admin role/storage:read only. This is an authority-semantics inconsistency, not a demonstrated external exploit. Preserve the original issued claims and intersect them with current authority, or explicitly require a freshly issued credential for expanded rights; use durable authority rather than client/PM-controlled claims.
- Remote registry path checks prefer existing local directories even when inspecting a remote revision; planning_path is not checked for presence/type in the target revision. A deleted remote project may remain active because the old local directory exists. Validate root/planning tree entries solely against the selected revision in remote mode, reject symlink/blob-as-directory entries, and test deletion while old local folders remain.
- safe_git_fetch chooses a hard-coded default delivery branch rather than resolving configured_branch first and may prefer stale origin/<branch> over FETCH_HEAD when refspecs differ. Fetch an explicit configured branch to a dedicated ref, verify its commit and fail on source disagreement. Do not silently substitute HEAD when remote synchronization is required.
- Registry identity still uses owner/name rather than immutable GitHub repository ID. Stable remote project UUID-to-local UUID binding is not persisted independently of the mutable project key/path; strengthen mapping constraints before subsequent plan/event integration.

**Low severity**

Backend delivery added portal/login.html despite the recorded frontend ownership. Codex will review/adopt it as a functional candidate, but shared UI edits need coordination. Request timeout, structured login errors and keyboard/error focus need frontend follow-up. No new lint failures identified in the executed check.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** real login/cookie plumbing improved; mismatched tenant state paths prevent the claimed integrated board/discovery flow.
- **Data & Schema Contracts:** legacy project retention improved. Atomicity and revision-consistent source validation still fail the required guarantees.
- **AI & Model Runtimes:** no activity bridge is claimed here; seeded status is test display data, not agent execution or verified completion.
- **Resilience & Governance:** fixed identity claim rejection is retained. Durable suspension, issued-credential ceilings and honest browser assertions require correction.

### 4. Architect's Action Directive

1. Fix the tenant state path and shared reconciliation transaction. Add regression cases reproducing both failures before changing tests to pass.
2. Repair authenticated durable suspension and preserve original IAM credential claims during cookie validation; prove expiry/revocation/suspension and authority-outage behavior.
3. Make configured remote branch/path validation consistent with the selected commit, including remote removal with local directories still present.
4. Correct the browser fixture/database setup, assert actual cards, label seeded data, and add real mutation/denial/revocation checks. Remove unsupported success claims from the committed report.
5. Run lint, selected regressions and the full gate with skipped tests explained. Push candidate and measured evidence for re-review. SBA-02/SBA-05 remain unaccepted; do not progress SBA-03 on assumed DONE.

## Independent verification

- pytest selected discovery/session/frontend/tenant/durable identity suites: **87 passed in 31.48s**.
- `ruff check mas/ tests/ scripts/record_browser_evidence.py`: **All checks passed**.
- Reran submitted browser script outside checkout with disposable fixtures and installed Chromium: login, cookie inspection, session GET and logout succeed. Inspected screenshot: No project, 0 of 0 issues. The runner lacks ticket assertions and therefore reports success incorrectly.
- Injected source-insert failure: project remains committed after exception.
- Durable suspend_principal: TypeError, missing permission_check argument.
- Credential-ceiling check uses an explicit in-memory authority mutation; records differing cookie/bearer roles/scopes. No remote exploitation claim.

Evidence at /workspace/review-evidence/sba-backend/rework-tests.log, rework_reproductions.json, rework-browser.log and rework-browser/. No submitted secrets reused; no production data or backend code changed. Full gate not rerun independently because confirmed blockers already prevent acceptance; Antigravity reported 536 passed/20 skipped, which is not independently verified here.
