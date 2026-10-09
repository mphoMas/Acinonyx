# Tenant boundary review

Historical assessment of `7624d83f`. The subsequent [durable identity review](DURABLE_IDENTITY_REVIEW.md) closes its process-local identity/session blocker for the documented single-host pilot. Other deployment restrictions remain.

Baseline: `3a373990e1cdd5d8cc1269d41dce4bdd48efa52b`. This review covers the new tenant-bound PM HTTP and MCP request paths. See [deployment contract](../architecture/TENANT_BOUNDARY.md).

### 1. Verdict & Executive Summary

- **Status:** APPROVED WITH CONDITIONS for the supported tenant-bound pilot; REJECTED (REQUIRES RE-WORK) for whole-platform enterprise multi-tenancy.
- **Core Summary:** Verified credentials now control tenant-scoped PM persistence, filesystem tools and isolated Python execution. Cross-tenant requests, caller impersonation, cached foreign databases and unsupported shared endpoints fail closed. Production approval still requires durable identity/session management and isolation of the remaining services.

### 2. Architectural Audit & Critical Findings

- **High Severity (Blockers):**
  - *Issue:* Default legacy entry points and general orchestration/memory/model integrations remain single-tenant; tenant mode denies unsupported endpoints rather than exposing shared state.
  - *Impact:* Publishing legacy services as a shared multi-tenant platform would bypass this boundary.
  - *Remediation:* Admit each additional service only after authenticated identity, tenant storage and credentials reach its actual handlers and negative integration tests pass.
  - *Issue:* Legacy IAM provisioning is process-local and has no durable per-token revocation ledger.
  - *Impact:* Restart requires trusted reprovisioning; session-level revocation cannot yet be guaranteed across hosts/restarts.
  - *Remediation:* Add durable authoritative tenant/principal/session storage or integrate a supported external identity provider, including revocation and restart tests. Do not assume a signing key persists the registry.
- **Medium Severity (Technical Debt / Fragility):**
  - *Issue:* The built-in HTTP server has no TLS and does not provide a complete tenant dashboard UI.
  - *Remediation:* Keep the pilot on a trusted host behind authenticated TLS infrastructure; build UI integration only after the backend contract is stable.
  - *Issue:* Trusted coordinator and storage ancestors remain part of the security boundary; shared-kernel workers are not strong hostile-tenant isolation.
  - *Remediation:* Keep host code/configuration trusted, preserve mandatory worker isolation and evaluate stronger containment before hostile public workloads.
- **Low Severity (Optimizations / Best Practices):**
  - *Issue:* Tenant PM requests create fresh database objects and repeat idempotent schema setup.
  - *Remediation:* Measure overhead before optimizing; any pool must retain tenant ownership checks and avoid a shared unscoped singleton.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** Fixed tenant binding per server/registry; independent task/thread contexts; unsupported shared routes rejected. Python workspace mounts are tenant-specific.
- **Data & Schema Contracts:** Separate SQLite databases and workspaces; equal keys stay isolated. Explicit foreign database paths and cached objects are rejected within tenant scope. No schema migration is needed for separate database files.
- **AI & Model Runtimes:** Worker authority derives from the authenticated request, including storage-write permission. Model behavior and quality are not re-rated by these isolation tests. General AI services remain outside the supported tenant pilot.
- **Resilience & Governance:** Current permission reductions, tenant suspension, expiry and verifier-issued context checks protect requests. Missing isolation fails closed. Durable session revocation, verifier-issued release proofs and externally anchored audit state remain open.

### 4. Architect’s Action Directive

1. Run the tenant-bound PM/MCP pilot only with trusted host provisioning, private configured signing keys and the documented supported endpoints.
2. Implement durable identity and session revocation with restart and concurrent revocation tests.
3. Extend tenant ownership to memory, model credentials and orchestration before admitting those endpoints.
4. Complete independent release evidence, external audit anchoring and sustained recovery/load qualification before resubmitting whole-platform enterprise deployment.

## Verification

`bash scripts/run_quality_gate.sh` passed all five gates: Ruff, runtime/capability checks, research links, compilation and full tests. Final result: **367 passed, 0 failed, 0 errors, 0 skipped**, 70.73 seconds. This includes **18 tenant-boundary cases**: actual HTTP requests, separate persistent databases, parallel writes, concurrent identity contexts, stale permissions, tenant suspension, caller impersonation, foreign cached DBs, path traversal, symlink swaps and real bubblewrap execution. Existing Docker recovery/adversarial checks ran in the same full suite.

Machine-readable source and artifact hashes are in [tenant boundary evidence](TENANT_BOUNDARY_EVIDENCE.json). Private raw gate/JUnit outputs remain outside Git under `/workspace/review-evidence/tenant-boundary-*`. No new live model evaluation or cloud-service validation was performed for this change.
