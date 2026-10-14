# GHA-04 revised design review

Candidate **fdee2afc**. **REJECTED (REQUIRES RE-WORK)** for implementation agreement. GHA-03 remains accepted. Only design documents changed; no runtime test evidence is implied.

## Assessment and confirmed design improvements

Witness phase changes are removed, observations are quarantined, artifact caps are corrected, and the redundant remote-effect journal is excluded. Receipt reads derive tenant from authenticated context. These improvements are retained. Remaining contradictions prevent a single implementable contract.

## Blocking corrections

### 1. DDL does not enforce claimed ownership or token retention (high)

INV-07 promises composite `(tenant_id,project_id,issue_id)` FKs, but `fk_receipt_task` and `fk_obs_task` reference only `issue_id`. Observation rows reference receipt ID independently, allowing tenant/project/issue disagreement. Source projection/history reference only project ID. The prose cannot substitute for relational constraints.

Token rows contain a receipt_id without a FK; receipts reference live tokens. R09 proposes deleting expired tokens while permanent receipts still reference them, which fails under foreign_keys=ON. Receipt records also omit intent/attempt/run binding despite the action's claimed MAS identity.

Required: write exact composite keys/FKs and parent UNIQUE indexes (explicit additive changes where necessary), receipt-to-observation ownership constraints and server-authoritative run/task binding or label unsupported associations as untrusted only. Separate expiring anti-replay entries from immutable token-consumption provenance, or retain referenced token rows. Provide valid insertion order/deferred-constraint rules and cleanup operations. Canonical action hashing must use structured serialization, not ambiguous concatenation; include tenant/task/policy/base binding. Prefer a full-strength receipt ID rather than a truncated 64-bit digest.

### 2. Authority and freshness ordering still lack enforcement (high)

Section4.2 acknowledges separate IAM/registry stores but repeats PM BEGIN IMMEDIATE plus independent checks. That still permits revocation between recheck and commit and is not a cross-store linearization mechanism.

Section4.3 says serialized refresh tickets, but the schema has no ticket/refresh state, acquisition/CAS/expiry protocol or multi-process owner. S01 still compares commit depth/ancestry, contradicting the force-push requirement. Unknown/stalled freshness and bounded maximum age are not represented. Open/closed transitions alone do not advance generation, allowing state cycling without a source revision change.

Required: choose an explicit supported local authority-update protocol. Either coordinated locks/fences covering every authorized mutator with documented process limits, or persistent authority epochs and a commit protocol establishing their ordering. State exactly which operation is the authorization linearization point. For source refresh, define per-subject durable refresh tickets/epochs, conditional response publication, failed/stalled refresh handling, TTL/currentness policy and state-change generations. Remove ancestry/timestamp ordering. No claim of global GitHub currentness beyond the chosen synchronization boundary.

### 3. Logical action versus attempt and historical recovery conflict (high)

INV-03 deduplicates logical actions, but DDL uniqueness and queries scope by action plus run/attempt. No separate logical-action record enforces immutable semantic digest; attempt changes can alter the action payload undetected. Manifest digest includes execution/revision fields and cannot automatically be semantic action identity. Multiple observation check IDs versus one check-derived action key need an explicit request model.

Admission still validates current source before token/receipt lookup. After head advance or PR closure, the promised historical cached response is therefore refused. New-attempt/new-token behavior contradicts action-only cache rules.

Required: separate logical action, attempt observation and receipt identities, define digest field inclusion precisely, and show one lookup decision table/order. Authenticate current read access first; resolve historical existing receipts without current-source re-admission, returning an explicit historical/stale flag. New attempt observations can be added to a preserved logical action without redispatch, with semantic conflict handled separately. Expired tokens need fresh authentication or the read API; never bypass authentication for cache recovery.

### 4. Artifact durability remains a promise rather than a safe protocol (high)

Staging/fsync precedes DB commit, but rename alone can overwrite an existing digest file. C01's 24h orphan deletion can race a paused admission or another process creating a reference. Quota reservation and current referenced-blob protection have no persistence/locking/restart rules. Chmod and single-process locks do not prove these guarantees.

Required: specify safe server-owned paths, atomic no-replace promotion, existing-content verification, quota ownership/reservation lifecycle, fsync ordering and promotion/receipt crash cases. Reclamation must coordinate with pending reservations and recheck committed references at its deletion linearization point. Define expired-artifact metadata/storage constraints and receipt query behavior. Keep this bounded to local storage, not a new remote journal.

## Action directive

1. Correct the actual DDL and lookup/commit protocols, not only closure tables marked Verified.
2. Map each acceptance case to exact proposed keys/operations and fault points; mark design agreement checklist as pending until granted.
3. Resubmit design only. No migrations/code/public endpoints/workflow/provider activation yet.

These are remaining variants of B2–B6 in the prior review; no new production feature or relaxed standard is introduced. There is no new implementation rejection or test-count claim.
