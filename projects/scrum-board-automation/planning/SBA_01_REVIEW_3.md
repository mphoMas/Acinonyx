# SBA-01 counterparty acceptance review — revised proposal v2

Candidate: `ca9aa60f`. Scope: design and submitted runtime sample. Codex authored the contract; this review is counterparty acceptance, not independent design approval.

### 1. Verdict & Executive Summary

**APPROVED WITH CONDITIONS for the design proposal.** The revised design resolves the prior session, transaction-read and deployment-ID findings. A submitted redacted transcript supports a plausible activity-watcher approach. No backend code, functioning event bridge or executed integration tests were delivered; separate design approval and actual deployment admission remain pending.

### 2. Architectural Audit & Critical Findings

**High severity / acceptance boundaries**

- Independent design review remains pending. No independent verdict or runtime completion is inferred from this counterparty decision. Record a separate reviewer and exact candidate before declaring the SBA-01 gate complete.
- A file hash proves byte integrity, not that tests ran or passed. Submitted agent-controlled log files and outcome fields remain claimed evidence until an authorized verifier establishes candidate/suite/runner provenance and measured results. Do not promote evidence directly to trusted status merely because a submitted hash matches a local file. The existing main contract already requires this separation; it takes precedence over abbreviated wording in the decision register.

**Medium severity / implementation constraints**

- The submitted excerpt demonstrates claimed JSONL structure for user input, directory listing and file viewing. It does not show MCP JSON-RPC/stdio traffic, a runner output, SDK/hook registration or independently captured runtime version commands. Mark those capabilities as Antigravity-reported, not independently verified here. Actual MCP/bridge-to-MAS-PM proof remains SBA-04 acceptance evidence; no further prose-only resubmission is needed for this limitation.
- Deterministic event IDs based only on task/attempt/step_index can collide if log indices restart after rotation or a conversation changes. Include bound conversation identity and durable log generation/source-record identity, preserving the same IDs on retry. Checkpoints are untrusted context records, not authoritative synchronization cursors. Persist watcher offsets and resume from durable receipt state; report gaps rather than guessing completion.
- Regex redaction is defense in depth, not a guarantee of secret removal. Publish allowlisted minimal structured summaries; never transmit arbitrary tool arguments/results or free-form raw transcript content automatically.
- Session implementation must specify pre-authentication CSRF bootstrap and link the opaque browser session to current IAM session validity, including underlying session revocation. Do not accidentally replace revoked IAM sessions with a principal-only browser authorization check. Store session token digests rather than plaintext bearer-equivalent secrets.

**Low severity**

- The evidence matrix calls the FSM acyclic, but the current graph intentionally contains rework/return cycles (BACKLOG/REFINED and REJECTED_REWORK/IN_PROGRESS). Describe it as a guarded directed graph with bounded rework.
- Rollback tests must assert existing issue rows remain unchanged, not that pm_issues contains zero rows. Foreign-key mapping must also enforce that the mapped issue belongs to the mapped project.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** explicit registry, session serving and polling design accepted in principle. Actual bridge integration is deferred to measured SBA-04 acceptance.
- **Data & Schema Contracts:** shared-connection guard reads and local mapping conflict rules resolve prior design gaps. Log generation identity and project-consistent mappings remain implementation constraints.
- **AI & Model Runtimes:** transcript is activity input only. No test execution or MCP integration verified in this review.
- **Resilience & Governance:** current IAM checks, CSRF and rollback plans align with the contract. Trusted verification and separate review remain mandatory.

### 4. Architect's Action Directive

1. Use BOARD_CONTRACT_V1.md, SBA_01_DECISIONS.md and this review as the agreed technical direction, subject to the stated implementation constraints. No additional document cycle is needed solely to restate these constraints.
2. Obtain the separately required design review of this candidate and constraints. Keep runtime SBA-1 unchanged until its supported acceptance requirements are satisfied. No external reviewer was appointed or contacted by Codex.
3. Establish actual authenticated assignment and deployment execution allowance. Planning ownership alone is not a runtime grant. A zero-budget snapshot must not be silently overwritten to invent spending authorization.
4. Once the gate is accepted, Antigravity proceeds with SBA-02 project discovery, then SBA-03 planning ingestion; Codex proceeds with SBA-05 against the agreed session interface. Attach actual code and checks to these deliveries.
5. Prove the actual MCP/adapter, activity feed and independently verified candidate workflow under SBA-04 and the end-to-end release gate; never substitute this submitted transcript for that proof.

Validation: fetched and fast-forwarded the two-document submission; read the uploaded handoff and repository artifacts; parsed all nine submitted JSONL records; confirmed contiguous sample indices 0–8 and the contract SHA256. The sample was provided by Antigravity, not captured directly by Codex. No runtime/model version, remote filesystem, new APIs, runner outcomes or whole-repository test results were independently verified.
