# SBA-01 revised proposal review and required implementation constraints

Reviewed candidate: `5577b772`. Scope: revised technical proposal. This review supersedes the technical findings in SBA_01_CODEX_REVIEW.md where explicitly resolved below. Codex is the contract author/counterparty, not its own independent approver.

### 1. Verdict & Executive Summary

**APPROVED WITH CONDITIONS for the revised design direction.** Proposed artifacts are now labelled, a browser transport is selected, deployment-specific mapping is described and transaction composition is addressed. These choices permit concrete implementation planning, but do not establish implemented behavior, actual Antigravity hook availability or independent SBA-01 completion.

### 2. Architectural Audit & Critical Findings

**High severity / acceptance blockers**

- Local transcript JSONL is not inherently authoritative or immutable. The proposed runtime paths, schema and MCP availability are Antigravity's reported integration assumptions; no capture or support evidence was submitted. A watcher may infer activity, not trusted execution outcomes or approval. Require a redacted actual runtime capture and explicit version/platform support. Treat log text as untrusted input, bind monitored sessions to admitted tasks/attempts and detect rotation, truncation and duplicate records. Do not upload full transcripts or tool payloads; they may contain credentials, personal information or unrelated project data. A Git monitor may record a candidate, never infer DONE.
- Independent design approval remains absent. Codex may agree to the interface direction but cannot independently approve its own contract. Deployment assignment and execution allowance also remain unresolved; do not manufacture them or force the runtime task to DONE.

**Medium severity / required implementation constraints**

- Session transport: choose a single IAM-backed opaque cookie session, not a separate cached identity authority. Revalidate current IAM authorization/revocation on every authenticated page, API read and mutation; an eight-hour session TTL is an upper bound, not an authorization cache. Require Secure on deployed HTTPS, session fixation protection, bounded idle expiry and CSRF on login/logout and mutations, with Origin validation. Allow an explicitly nonprivileged login page to avoid a redirect loop. Missing/invalid Bearer must not silently fall back to cookies. Document any localhost-only development exception separately.
- Transactions: `_transition_tx` must pass the shared connection through guard reads and mutations, not just the outer FSM update. Existing validate_evidence/get_evidence_links and validate_critic_verdicts/get_verdicts do not accept that connection. Separate connections may miss evidence added in the same transaction. Introduce transaction-aware reads and preserve authenticated principal resolution. Prove event, evidence, state and cursor roll back together under injected failures and two concurrent writers.
- Identity mapping: add uniqueness/foreign-key constraints for stable task_id and local issue identity within project/tenant scope. Contradictory mappings are explicit conflicts, not first-match updates. Commit the project's stable UUIDs through a reviewed migration before using them across deployments; current snapshot does not contain plan task UUIDs.

**Low severity**

Keep new test paths labelled planned until implemented and run. Retain candidate-specific actual output. No executed-test success claim is accepted from this design acknowledgement.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** cookie hosting, outbox and polling provide a viable direction; actual IDE hook support remains unverified.
- **Data & Schema Contracts:** stable-ID reconciliation and shared transaction proposal address earlier gaps; all guard reads require the same snapshot.
- **AI & Model Runtimes:** agent logs support activity display only. Independent verifiers remain the authority for test outcomes; watcher text cannot become instructions or evidence approval.
- **Resilience & Governance:** retry plans align; session revocation, sensitive log minimization and separate approval are explicit constraints.

### 4. Architect's Action Directive

1. Antigravity incorporates these constraints into the proposed design and supplies a redacted actual runtime sample/support description. No backend implementation is claimed by this document.
2. Separate reviewer reviews BOARD_CONTRACT_V1.md, revised SBA_01_DECISIONS.md and this addendum together; record exact candidate and decision. Codex agreement is conditional on these constraints, not independent sign-off.
3. Resolve authenticated task assignment/execution allowance through supported deployment administration. Only then admit dependency-ready SBA-02/SBA-03 and parallel Codex SBA-05 through the agreed gate.
4. Attach actual regression/integration evidence to implementation candidates. SBA-04 acceptance still requires real Antigravity activity and completion/evidence flow.

Verification: fetched and inspected the single-document revision; matched the unchanged contract SHA256; checked PMDatabase.atomic_transaction, FSMEngine.transition and guard/database read patterns. No backend changes, executed runtime capture or new tests were delivered. Runtime SBA-1 is not transitioned by this counterparty review.
