# Durable identity and session revocation review

Historical assessment of `22ddde03`. The subsequent [external audit anchor review](EXTERNAL_AUDIT_ANCHOR_REVIEW.md) adds forward-only witness enforcement for explicitly configured stores. Production deployment of that independent witness remains a separate requirement.

Baseline: `7624d83f5780f404e2413fc25bc1173df73a8a8e`. Scope: durable local identity authority and session revocation for the supported tenant-bound PM HTTP/MCP pilot. See [operational contract](../architecture/DURABLE_IDENTITY.md).

### 1. Verdict & Executive Summary

- **Status:** APPROVED WITH CONDITIONS for the documented single-host pilot. Whole-platform enterprise multi-tenancy remains REJECTED (REQUIRES RE-WORK).
- **Core Summary:** A private SQLite authority now persists tenants, principals, issued sessions and revocations across process/server restarts. Revocation checks use current authoritative state, and identity changes commit atomically with signed audit history. Authentic authority rollback still requires an external anchor; deliberate backup recovery must invalidate restored sessions before traffic resumes.

### 2. Architectural Audit & Critical Findings

- **High Severity (Blockers):**
  - *Issue:* An older authentic authority snapshot can restore previously valid sessions; cryptographic signatures do not establish external freshness.
  - *Impact:* Restoring an old database and immediately serving it can revive revoked credentials.
  - *Remediation:* Use the tested offline `invalidate_all_sessions` recovery fence for deliberate restores. Add externally anchored authority freshness before hostile rollback resistance or enterprise production claims.
  - *Issue:* Legacy entry points, memory, general orchestration and model/cloud/browser/Git integrations remain outside the tenant-bound implementation.
  - *Impact:* This change cannot certify whole-platform multi-tenancy.
  - *Remediation:* Extend authenticated ownership to each service's real storage, credentials and handlers before admission.
- **Medium Severity (Technical Debt / Fragility):**
  - *Issue:* The current audit integrity check scans retained history on every authority read.
  - *Remediation:* Qualify sustained authentication load and implement bounded authenticated indexing/retention without caching away revocation freshness.
  - *Issue:* Local SQLite/POSIX storage, TLS deployment and key lifecycle depend on trusted host operations; multi-host/NFS authority, federation and online key rotation are unqualified.
  - *Remediation:* Limit deployment to a trusted single host behind supported TLS infrastructure, with persistent private keys and the documented restore procedure.
- **Low Severity (Optimizations / Best Practices):**
  - *Issue:* Default development mode is intentionally process-local when no identity database path is configured.
  - *Remediation:* Configure `MAS_IAM_DB_PATH` or `db_path` explicitly for a durable pilot; do not infer durable enrollment from a signing key alone.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** Independent process instances reopen the same authoritative store. Exclusive initialization, SQLite write serialization and bounded lock waits support concurrent startup and issuance. No distributed-service claim is made.
- **Data & Schema Contracts:** Schema version 1 contains tenant/principal/session records, owner indexes, metadata and transactional signed audit events. Token hashes replace bearer persistence. Existing unknown schemas and wrong keys are rejected. Explicit empty permission sets remain empty; principal updates and tenant suspension revoke sessions atomically.
- **AI & Model Runtimes:** Agents cannot select their tenant, access the identity database through workspace mounts or invoke provisioning/offline restore operations through registered tools. Session revocation blocks subsequent authorization checks but does not retroactively undo authorized effects or automatically terminate running workers. Model quality was not re-rated.
- **Resilience & Governance:** Fresh checks reject expired, unissued, revoked or forged authority. Administrative revocation revalidates the revoker inside the write transaction. Audit failures roll back mutations. New-process recovery, actual process death, backup restoration, selective replay and HTTP logout are exercised. External freshness anchoring remains unresolved.

### 4. Architect’s Action Directive

1. Configure the private durable store outside tenant workspaces and persist its original signing key securely.
2. Keep restored services offline until all restored sessions are invalidated; issue fresh credentials before reopening traffic.
3. Add external freshness anchoring, then extend tenant ownership into the remaining runtime services.
4. Complete sustained load, multi-host recovery and key-lifecycle qualification before enterprise deployment review.

## Verification

`bash scripts/run_quality_gate.sh` passed all five gates. Final full-suite result: **394 passed, 0 failed, 0 errors, 0 skipped**, 73.76 seconds, including **27 durable identity acceptance cases**. The existing tenant-isolation, real bubblewrap and Docker recovery/adversarial tests ran in this suite.

A clean offline-built wheel was installed into a fresh environment. Outside the checkout, it reopened persisted identities and rejected a self-revoked session after another restart. Every packaged MAS Python file matches the final checkout byte-for-byte. Source and artifact hashes are in [durable identity evidence](DURABLE_IDENTITY_EVIDENCE.json); raw logs/JUnit/wheel remain outside Git under `/workspace/review-evidence/durable-identity-*`.

The old-backup test explicitly demonstrates the local rollback detection limit before applying the offline invalidation fence. No external anchor, live model reevaluation or multi-host/load qualification is claimed.
