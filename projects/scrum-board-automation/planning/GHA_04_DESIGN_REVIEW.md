# GHA-04 independent design review

Candidate: **6099b8ae**. Verdict: **REJECTED (REQUIRES RE-WORK)** for implementation agreement. This is a design return, not a failed implementation. GHA-03 acceptance remains unchanged.

## 1. Executive assessment

The identity separation and additive-ledger direction are useful, but the proposed admission protocol bypasses existing delivery submission authority and contains contradictory replay/recovery semantics. The schema cannot enforce the stated ownership, logical-action idempotency or current-source guarantees. Fix these mechanisms before code or migrations.

## 2. Critical findings and required solutions

### B1 — Witness ingestion takes builder submission authority (high)

INV-05, admission Phase 5 and TC-11/12 directly UPDATE delivery tasks to IN_REVIEW/READINESS_RETURNED from witness PASSED/FAILED claims. GHA-03 deliberately denies witness `DeliveryService.submit`; the existing service independently checks builder identity, current brief/revision, complete observations and actual completed run. Avoiding ACCEPTED alone does not preserve that boundary.

**Fix:** GHA-04 persists quarantined untrusted observations/receipts only, without delivery phase or submission mutation. A later distinct authenticated builder submission may reference a receipt after fresh existing checks. Keep `authority_verified=false`, use admission status rather than an authoritative verdict, and explicitly prohibit mutations of delivery phases, trusted evidence and budgets from witness ingestion. No direct SQL phase changes.

### B2 — Identity/idempotency schema cannot express the contract (high)

Logical identity `(repository, pr_number, check_id)` omits source generation/candidate/suite and can collide across revisions. The schema contains neither the scoped idempotency key nor canonical action payload digest required by INV-07. Run/attempt uniqueness prohibits multiple checks or MAS tasks in one GitHub run. Receipts omit source generation/PR association, MAS intent/attempt/fence/brief/suite/policy coordinates and issuer from token linkage. Independent scalar FKs permit inconsistent tenant/project/issue ownership.

**Fix:** define a server-mapped source subject and generation-specific logical action, separately from GitHub run/attempt observations and token consumption. Persist scoped action key and semantic digest; record attempt-specific observations without executing again. Include canonical artifact digests and suite/policy/binding fields in semantic identity. Use composite tenant/project/issue/run ownership constraints and exact token-to-receipt foreign keys. One project database cannot enforce platform-global `(iss,jti)` uniqueness without a specified shared store; scope the guarantee or choose its owner explicitly.

### B3 — Retry semantics contradict single-use rules and lose recovery after expiry (high)

The text says consumed tokens are refused, but later permits identical-token cached responses. Fresh-token exact retries return409 instead of resolving the same logical action. Cached lookup occurs after current-head validation, so head advancement prevents receipt recovery; JWT expiry also makes old-token recovery unavailable. Define these outcomes rather than letting implementation guess.

**Fix:** at-most-once mutation per token; authenticated identical replays may return a historical immutable receipt without re-admission. Fresh valid token plus identical logical-action/digest returns that receipt; conflicts refuse. Authenticate and check current access for reads; mark historical/stale status and never claim current acceptance. Define expired-token recovery via fresh authentication or scoped query, and whether token consumption is recorded for cached responses. Distinguish token, action and attempt uniqueness.

### B4 — Freshness ordering is not authoritative (high)

Commit ancestry, delivery timestamp or unspecified monotonic webhook counter cannot order legitimate force pushes/rebases reliably. Signature authenticates delivery, not ordering or currentness. Schema permits multiple `is_current=1` rows; generation uniqueness omits repository. Changes mutate prior events despite INV-10's append-only claim. Base branch advancement/PR closure/reopen and unknown freshness are unspecified.

**Fix:** append-only authenticated event ledger plus one constrained current-source projection with CAS generation. Treat webhooks as notifications; choose a concrete authoritative refresh protocol with serialized refresh tickets/CAS and bounded freshness policy. Delayed responses cannot regress current state. Define force-push, base update and closed/reopened PR behavior and fail closed for unknown freshness. Local generation counts accepted refreshes, not GitHub event order. No live webhook activation is needed for deterministic local tests.

### B5 — SQLite lock does not serialize IAM, connector or filesystem state (high)

BEGIN IMMEDIATE locks the PM database, not the independent IAM database/registry. Authorization may change after recheck. Artifact CAS writes are outside SQLite atomicity; chmod0440 alone does not prevent overwrite/deletion by the owner. File staging inside a long DB lock is not a complete durability protocol.

**Fix:** define authority linearization and supported update coordination or a durable generation/fence protocol with revocation ordering. Artifact stage/validate/hash/fsync/atomic no-overwrite promotion must precede receipt commitment; fsync directories and recheck existing content. DB references require durably stored bytes. Use safe server-owned paths, quota reservation and orphan reclamation; crashed staging may leave unreferenced blobs but not receipts pointing to missing data. Do not claim one atomic transaction spans all independent stores.

### B6 — Recovery and retention contradict proposed records (high)

SC-11 says rollback all rows and mark an intent UNCERTAIN; no durable intent survives that rollback. Admission diagram never inserts the promised intent, while the journal lacks action identity, CAS revision, leasing/fences or recovery evidence. A pure local rolled-back receipt write is not uncertain remote execution. WAL existence alone cannot settle an external effect. INV-10 freezes transitions while intents/current source are updated, and token purge/receipt archive rules conflict with deletion bans.

**Fix:** keep this slice local receipt persistence and avoid a redundant remote side-effect journal. Rollback means no committed receipt; response loss is resolved by persisted action/receipt. If a future external effect is retained, give it a separate durable outbox with explicit claim/fence/UNKNOWN_EXECUTION reconciliation and existing funding holds. Specify immutable history versus mutable projections and retention cleanup separately. Token cleanup only after all replay-validity windows, historical receipt query behavior and artifact-expiry states must be explicit.

## 3. Scope and documentation corrections

- Correct archive caps: 12 MiB compressed, 2 MiB/member, 10 MiB total uncompressed.
- A signed receipt is not a trusted verifier signature. Prefer immutable receipt digest initially; any signing adds explicit issuer/key/rotation/verifier semantics.
- Read APIs must derive tenant from authenticated context, not trust a caller's tenant string.
- CLI/backend ownership belongs to Antigravity unless CEO reassigns; Codex owns board UI/review.
- Migration2026101401 is proposed, not allocated until collision/checksum/current migration inventory is checked. Include missing/mutated-table/trigger reopen tests, data preservation and rollback compatibility.
- No new code/tests were run: this candidate changes only two design documents. Prose test specifications are not executed evidence.

## 4. Pillars and action directive

Platform: choose one durable local ingestion slice and explicit storage boundaries. Data: define complete relational identity and source projection constraints. AI: witness claims must remain quarantined. Governance/recovery: authenticate receipt access, specify token retry policy and avoid false atomicity/uncertainty claims.

1. Resubmit a narrower local immutable observation/receipt design with no delivery-phase changes.
2. Include corrected DDL, transaction/authority/artifact protocols and explicit failure outcomes, addressing B1–B6.
3. Share tests for cross-tenant ownership, multiple checks/tasks per run, identical fresh-token recovery, expired-token query, head changes/force pushes, revocation races, file/DB crash boundaries, retention and migration reopening.
4. Wait for design agreement before GHA-04 implementation or schema changes. No public endpoints, live workflows, production credentials/enrollment or provider dispatch.
