# GHA-04A: durable quarantined receipt slice — reference contract

Author: Codex. Proposed implementation owner: Antigravity. Independent implementation reviewer: Codex. **DESIGN CHALLENGE REQUIRED BEFORE IMPLEMENTATION.** This document supersedes the broad GHA-04 implementation proposal for the first increment only; outstanding source/artifact/authority mechanisms remain deferred, not silently waived.

## Outcome and scope

One authenticated supported caller stores a bounded untrusted observation, loses the response, restarts, obtains fresh authentication and recovers the same immutable receipt without duplicate records or business-state changes.

Allowed: persist/query quarantined metadata and bounded inline JSON claims in the existing scoped project database; additive receipt/action/item schema proposed below. Excluded: artifact file storage/lifecycle/URLs; current PR-head authority; durable OIDC token consumption; live workflow/public endpoint/provider dispatch; delivery phase/submission/evidence/budget mutations. GHA-03 authenticates witness transport but does not create an IAM bearer; reuse of valid authentication is allowed here. This slice cannot claim token replay protection or exactly-once remote execution.

## Exact identities and request

`record_observation(authenticated_binding, action_id, observation_id, contract, payload)` returns `{status: CREATED|EXISTING, receipt_id, authority_verified:false, source_authority_verified:false}`. `get_receipt(authenticated_binding, receipt_id)` returns scoped immutable content or not-found without cross-owner disclosure.

- Ownership: tenant/project/issue resolved against configured binding and actual parent task ownership. Caller claims cannot select another database/tenant. Never accept a naked caller-supplied TenantContext as proof of IAM authentication or grant privileged storage access.
- `action_id`: caller-supplied opaque correlation ID scoped to tenant/project/issue. It is NOT authority or inferred from candidate GitHub state. Maximum128 ASCII identifier characters. Same ID binds one immutable contract digest.
- Contract: schema_version1; claimed candidate/base SHA, suite digest, brief/policy versions, optional claimed source generation, and sorted unique check IDs. All execution/source/policy associations are claims only until separately qualified. Canonical JSON hashes the structured map `{owner: [authenticated tenant, configured project, validated issue], contract: validated contract}`; ownership is never taken from caller contract fields; key order normalized, nonfinite numbers forbidden. No concatenation hashing.
- `observation_id`: caller-supplied opaque stable retry ID, scoped to action. Maximum128 ASCII identifier characters; NOT guessed solely from GitHub run ID. Distinct checks/tasks/attempts can share one GitHub invocation without collision.
- Payload: schema_version1; claimed GitHub repository/run/attempt, claimed MAS run/intent/attempt/fence, items sorted by unique check ID, artifact digest claims (no bytes or trusted URLs), bounded limitations. Payload check IDs must form a subset **including equality** of the contract's sorted unique check IDs. Reject unsorted/duplicate check IDs and items before hashing/transaction; reporting every agreed check is valid. Outcomes are `PASSED|FAILED|SKIPPED|UNAVAILABLE` and remain claims. Changed outcome requires a NEW observation_id. Unknown fields refused; stable canonical normalization is defined before hashing.
- Limits: action+payload encoded canonical JSON <=1 MiB combined; <=128 items, <=64 artifact digest claims, limits on individual identifiers/limitations; <=10,000 receipts per project in this pilot (duplicates can still retrieve when full). No writes or archival blobs to external paths. Admission is atomic relative to this count under BEGIN IMMEDIATE.

Receipt ID: `rcpt_` plus full SHA256 of structured ownership/action_id/observation_id/payload_digest map. Immutable stored receipt includes canonical contract/payload, admitted time, claimed identity labels and fixed false authority flags. Production adapter must use exact canonical bytes once; fixture hashing is the example, not an independent verification signature.

## Auth and revocation profile — choose explicitly in design challenge

Use existing supported fresh IAM/tenant storage binding and explicit receipt read/write scope, never trusted-admin runtime fallback. Request caller and query caller must be authenticated afresh; issuer/role labels in stored observations do not confer access. Tenant/connector revocation is rechecked for each operation. Quarantined admission is not permission to execute or approve.

For the first local pilot, require one service process to own receipt operations and the supported tenant/connector administration paths. One shared authority guard serializes revocation and the receipt transaction; lock order authority guard then PM BEGIN IMMEDIATE, bounded local work only. A revoke winning the guard first blocks admission. Admission winning first may commit before revocation; subsequent retrieval is refused. The database can survive process restart; lock ordering does not claim coordination across other service processes or external IAM admin tools.

**Before agreement:** Antigravity must name the actual IAM and connector mutators wired through the guard, startup fresh-status checks and read/write authentication API. Any unsupported external mutation path disables this profile rather than pretending it is guarded. If actual deployment requires multi-process administration, this slice cannot be activated until durable authority coordination is separately agreed. This is an explicit limitation, not the previously rejected cross-store atomicity claim.

## Exact transaction and retry order

1. Authenticate current caller, resolve server-owned storage/owner, validate bounded request/canonical forms outside DB lock. No token ledger or file staging.
2. Acquire the supported authority guard; recheck current session/tenant/connector status and ownership; begin IMMEDIATE on the scoped PM DB.
3. Find `(owner,action_id)`. If existing contract_digest differs: ACTION_CONTRACT_CONFLICT; rollback.
4. Find `(owner,action_id,observation_id)`. If existing payload_digest differs: OBSERVATION_CONFLICT; rollback. If equal: return EXISTING same receipt; no receipt/action/item or budget changes. No source currentness check, artifact staging or authentication bypass.
5. Check project receipt quota for new records. Insert missing immutable action, receipt and all item rows in ONE transaction. Composite parent/receipt ownership FKs are mandatory; BEFORE INSERT duplicate-identity guards also refuse REPLACE/UPSERT/IGNORE paths on immutable rows.
6. Commit, release guard, return CREATED. Sending response may fail after commit; that does not imply rollback.
7. Fresh authentication with identical owner/action/observation/contract/payload after lost response returns EXISTING, including after original token expiry or claimed PR head changes.

Distinct observation_id may record a different outcome/attempt for the SAME immutable action contract. Same action with a changed candidate/base/suite/policy contract requires a NEW action_id; retaining the old action ID conflicts. Multiple attempts are retained as observations, not redispatched execution or extra spending.

## Persistence and recovery

Reference executable schema in `gha04-receipt-contract/proposed_schema.sql` models immutable owner parents, action contract, receipt and composite-owned items. Production migration uses actual parent UNIQUE tuples, checksum and reopen drift detection, and preserves all existing rows; fixture parent tables are NEVER deployed. Migration ID allocated after inventory check, not reserved by this contract.

Rollback before commit leaves no new action/receipt/items. Crash after commit is recovered by lookup on reopen. No new UNKNOWN_EXECUTION record is created: no remote side effect occurs. Receipt queries require current authentication after restart. Direct update/delete and cross-owner item insertion fail under FK/triggers. No receipt expiry/deletion in this pilot; quota exhaustion refuses new admission instead of growing storage indefinitely.

## Acceptance demonstration and evidence

Runnable reference command:
`python3 projects/scrum-board-automation/planning/gha04-receipt-contract/check_fixtures.py`

Observed after independent challenge corrections: **10 reference checks passed**. This only checks proposed SQL/canonical identities and sample transaction outcomes. It does not test runtime IAM, supported API, process kill, true concurrent admission or production migration.

Antigravity implementation acceptance must additionally prove through the supported interface:
- real subprocess kill after commit before response, reopen and freshly authenticated recovery;
- concurrent same observation: one CREATED, one EXISTING, same receipt and one item set;
- conflicting observation and changed contract preserve originals; new attempt retains different claims;
- actual denied cross-tenant read/write and composite ownership mismatch;
- real session/tenant/connector revocation ordered by the named guard; no trusted-context forgery;
- limits/quota exact boundaries, no delivery/evidence/budget mutation;
- preexisting DB migration/reopen/drift and outside-checkout installed-wheel tests.

## Next gate

Antigravity independently challenges this reference contract, including the local authority profile and deferred guarantees. Record agreed changes and freeze exact inputs, outputs and acceptance evidence. If the profile cannot meet the actual deployment, stop and name that mismatch rather than expand silently. No backend implementation is authorized until that design challenge is resolved.


## Independent challenge resolution (Antigravity's supplied review)

The CEO supplied Antigravity's APPROVED WITH CONDITIONS challenge of `5f83e250`. Codex accepts the REPLACE bypass finding and closes it with BEFORE INSERT conflict guards on actions, receipts and items, independent of recursive_triggers. Fixtures now test REPLACE/IGNORE/UPSERT, physical and logical receipt conflicts, scope/order validation, and unchanged original rows. This corrects Codex-authored reference material; it is not production implementation acceptance.

Production parent mapping is **pm_delivery_tasks**, not pm_issues: tasks already carry tenant_id/project_id/issue_id. Add an additive UNIQUE index on that exact tuple; bind actions to it. Receipts bind to scoped actions and items bind to scoped receipts. This slice requires an existing enrolled delivery task; enrollment and legacy task backfill are excluded. No tenant column is added to pm_issues. Fixture-owned parents are only structural models, not deployable replacements.

Quota count is performed inside the receipt transaction after EXISTING lookups. Conflict-before-quota and duplicate-before-quota semantics are frozen. Strict check ID subset means equality is allowed; reject unknown/duplicate/unsorted IDs. Owner-wrapped contract digest above resolves the fixture/prose mismatch without trusting caller ownership. It also domain-scopes the digest.

The named authentication/session/registry APIs identified by Antigravity must use the one shared authority guard for this supported local host profile, including principal/session invalidation, tenant suspension and connector register/update/remove/pop/item mutation. Fresh token authentication uses existing IAM/tenant binding; constructed witness contexts are not bearer credentials. Guard integrations are a scoped implementation requirement, not an already implemented feature. External-process IAM changes and multi-process service writers remain unsupported; do not silently enable them.

Authorization to implement this bounded local slice follows existing CEO direction and the independent conditional design challenge, after these corrections. No additional CEO confirmation is needed. Antigravity owns runtime implementation; Codex independently reviews. Later scope additions remain separately agreed.
