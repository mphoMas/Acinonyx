# GHA-04 shared independent acceptance scenarios

Owner: Codex (acceptance definition/review). Implementation: Antigravity.
Baseline: GHA-03 accepted implementation `82407210`; GHA-04 design review `a193e1af`.
Status: **PRE-IMPLEMENTATION SPECIFICATION — NOT EXECUTED TEST EVIDENCE**.

These scenarios operationalize the existing GHA-04 handoff/review. They do not approve the rejected design or authorize implementation. Antigravity must map each scenario to the revised design's exact APIs, constraints and transaction boundaries before coding. Changes to requirements must be recorded as scope changes.

## Common fixture

Two tenants A/B, separate projects/issues, one enrolled repository and trusted reusable workflow; active tenant/connector with immutable policy generation; real signed short-lived JWT fixtures and controlled time. One source subject PR42 at generation7, headH7/baseB1, and two MAS tasks T1/T2. Artifacts contain actual bounded bytes/digests. Use disposable databases/filesystems and no production credentials, GitHub writes or provider calls.

Capture full persisted state before/after: business phase/revision, submissions, trusted evidence/verdicts, reservations/budget, receipts, tokens, logical actions, attempt observations, source projection/history and artifact references. Token/action/receipt counts are not interchangeable. Fixture setup uses supported services; malformed direct SQL is reserved for relational integrity probes.

## Admission and authority

| ID | Input/fault | Required outcome and observable evidence |
|---|---|---|
| A01 | Valid authenticated witness observation bound to current source | One durable untrusted observation/receipt, exact canonical payload/artifact identity; zero delivery phase/submission/trusted-evidence/budget changes |
| A02 | Witness claims all checks PASSED or supplies approval-looking fields | Receipt remains untrusted; forbidden extras rejected; no IN_REVIEW, ACCEPTED or trusted verifier signature |
| A03 | TenantA request links TenantB project/issue/run; inconsistent ownership inserted directly | Service refuses with no cross-tenant disclosure; proposed composite database constraints independently refuse inconsistent links |
| A04 | Two distinct checks/tasks in the same GitHub run and attempt | Both can be represented by distinct scoped logical actions; no collision caused by run/attempt-only uniqueness |
| A05 | Same action changes candidate/source generation/suite/policy/artifact identity | Updated revision is a separately bound action or explicit conflict; cannot silently overwrite prior receipt or inherit its evidence |
| A06 | Connector removed/revoked/changed or tenant suspended between validation and commit | Defined authorization linearization refuses or proves permitted-before-revocation ordering; actual barrier tests against IAM/registry update API, not merely PM lock assertions |
| A07 | Requested run/attempt, MAS execution/fence or brief binding mismatches | Refusal with no successful receipt or business mutation; distinguish authenticated transport coordinates from untrusted MAS claims |

## Replay, idempotency and retrieval

| ID | Input/fault | Required outcome and observable evidence |
|---|---|---|
| R01 | Two processes concurrently use same token/action/digest | Exactly one mutation; second authenticated result follows agreed cached-or-refusal rule; no duplicate receipt/effect; real separate connections/processes |
| R02 | Fresh valid token repeats committed logical action and identical semantic payload | Same historical logical outcome/receipt according to agreed response contract; no duplicate execution, budget change or authoritative re-admission |
| R03 | Same scoped action key with different semantic digest | Conflict; immutable prior payload/receipt; no partial token/action/receipt writes inconsistent with agreed failure policy |
| R04 | Formatting/dictionary order changes only | Same canonical semantic digest; no false conflict; attempt-only fields excluded from logical identity where specified |
| R05 | New GitHub rerun attempt | Distinct attempt observation, preserved previous history; no inference that new tokens pay for/authorize new MAS execution |
| R06 | Old token expired after dropped response; client uses fresh authentication | Authorized historical receipt recovery works; expired token alone denied; current tenant/connector access required |
| R07 | PR head advances after original receipt; client retrieves it | Historical receipt can be read with explicit stale/historical status; no current-success claim or phase transition |
| R08 | Other tenant queries known receipt ID or supplies another tenant string | No data returned; authorization derives from authenticated context rather than request tenant selector |
| R09 | Token/receipt cleanup and token-expiry clock boundary | No replay-valid token becomes usable again; cleanup respects documented clock tolerance/retention; history/expired artifact semantics explicit |

## Source currentness and ordering

| ID | Input/fault | Required outcome and observable evidence |
|---|---|---|
| S01 | Authenticated notification triggers authoritative refresh H8, then delayed H7 notification/response | Current projection never regresses due to late refresh result; demonstrate ticket/CAS protocol, not assumed event timestamps |
| S02 | Force push to unrelated commit or deliberate return to previous commit | Legitimate authoritative update accepted with new local generation; ancestry is not the authority decision |
| S03 | Base branch changes; PR closes/reopens; head changes during admission | Revision/currentness policy enforced for each condition; stale candidate admission refused; only one current projection per subject |
| S04 | Forged webhook signature, duplicate delivery, wrong repository or unknown source | Refuse or deduplicate as specified; cannot select tenant/project/source authority from body; record authenticated-event identity separately |
| S05 | GitHub/API freshness unavailable, stale refresh window or delayed sync | Fail closed for new authoritative admission; existing historical receipts remain clearly historical and do not certify currentness |
| S06 | Two concurrent source updates and receipt admission | One generation-linearized outcome; constraints prevent multiple current rows; receipt records exact admitted generation |

## Artifact and crash durability

| ID | Input/fault | Required outcome and observable evidence |
|---|---|---|
| C01 | Kill process before artifact promotion, after promotion/before DB commit, after commit/before response | No committed receipt references absent/unverified artifact; precommit orphan is identifiable/reclaimable; postcommit retry recovers exact receipt |
| C02 | Disk full or fsync/rename/DB commit failure | Correct rollback/reconciliation outcome; no false success; no fictional UNCERTAIN record claimed to survive a rolled-back transaction |
| C03 | Existing digest path has wrong bytes, symlink or concurrent promotion | Safe no-overwrite admission, verified existing bytes, no path escape; one durable valid blob per scoped digest |
| C04 | Concurrent quota reservations, oversized/missing/expired artifacts | Quotas enforced under concurrency, actual bytes checked; retention cannot delete referenced evidence without explicit expired state |
| C05 | Real restart/reopen with committed/uncommitted local ingestion | Durable receipt/action recovered, no duplicated work or funds released; no new generic remote-execution uncertainty inferred from local rollback |
| C06 | Future external effect included in revised design | Requires separately agreed durable outbox/fence/reconciliation tests before inclusion; otherwise explicitly excluded from this milestone |

## Schema, evidence and operability

| ID | Input/fault | Required outcome and observable evidence |
|---|---|---|
| D01 | Existing pre-GHA04 DB migration/reopen, repeated migration, interrupted migration | Atomic additive upgrade; preserve existing rows/history/checksums; no production enrollment; defined version compatibility |
| D02 | Missing/mutated required table/index/trigger or malformed ownership row | Reopen detects drift or declared repair mechanism safely addresses it; no silent acceptance under broken integrity assumptions |
| D03 | UPDATE/DELETE immutable history; legitimate current-projection update/expiry cleanup | History protected; legitimate mutable projection and retention operations obey distinct explicit rules |
| D04 | Audit/error failures with arbitrary sentinel inputs | Public and private failure logs exclude input/exception values; retained categories/correlation sufficient to diagnose outcome |
| D05 | Installed wheel in clean environment, tests copied outside checkout | Imports resolve in site-packages; migrations/artifact/query modules available; actual scenarios run without checkout imports |

## Required submission evidence

1. Numbered invariant-to-mechanism-to-scenario closure matrix, naming exact source/files and API owners.
2. Candidate-specific actual results with skips/failures, configured dependencies and known unsupported behavior.
3. Barrier-controlled concurrent races and real process kill/restart receipts for durability scenarios; mocked success cannot prove recovery.
4. Database row/constraint and filesystem existence/hash evidence; outputs must not contain secrets or raw customer data.
5. Targeted suites, final full repository gate and installed-wheel verification after final code edit.

Independent review reproduces selected failures and adjacent paths; passing this list alone does not prove production deployment or the full agent loop. Final verdict retains agreed scope and records any newly discovered requirement separately.
