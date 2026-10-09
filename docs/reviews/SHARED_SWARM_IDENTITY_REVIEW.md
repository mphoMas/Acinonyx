# Independent review: shared swarm and platform identity

Baseline: `aa79cdcbeba1778dc7204fe73314b10893011c9c`. Scope: explicitly platform-bound coding stores, durable IAM authority and CLI integration. See [operational contract](../architecture/SHARED_SWARM_IDENTITY.md).

### 1. Verdict & Executive Summary

- **Status:** APPROVED WITH CONDITIONS for the supported single-host shared-identity pilot. Historical migration, broader consolidation and enterprise deployment remain incomplete.
- **Core Summary:** One durable platform session can authorize both tenant PM MCP and swarm operations through explicit permissions. The swarm retains signed task/evidence state while rejecting local credential fallback in platform mode. Current revocation is enforced at store operations and active-run monitoring; lost authority cannot approve or mutate state to hide uncertain work.

### 2. Architectural Audit & Critical Findings

- **High Severity (Blockers to broader cutover):**
  - *Issue:* Existing local stores are not automatically migrated; a common broker and complete interface cutover remain pending.
  - *Impact:* This adapter cannot qualify blanket platform-wide tenancy or silently upgrade historical identities.
  - *Remediation:* Review tenant/subject/history mappings, reissue credentials and rehearse compatible recovery before admitting migrated stores/interfaces. Keep unsupported legacy paths separate.
  - *Issue:* Independent production witness activation is unconfigured; swarm run history is not externally anchored.
  - *Impact:* Authentic whole swarm-store rollback is outside this guarantee; unanchored IAM lacks external freshness protection.
  - *Remediation:* Activate configured IAM witnessing independently; qualify additional streams separately. Preserve administrative/storage/restore independence.
- **Medium Severity (Technical Debt / Fragility):**
  - *Issue:* Short swarm transactions reserve the IAM writer slot and scan signed history. Anchored operations add synchronous HTTPS probes.
  - *Impact:* Authorization is serialized and can delay identity updates and cancellation monitoring; throughput is unqualified.
  - *Remediation:* Measure the agreed workload and authority latency before wider deployment; preserve fresh authorization and witness ordering when optimizing.
  - *Issue:* Revoked active runs retain their lease and uncertain usage because revoked callers cannot write terminal state.
  - *Impact:* Administrative reconciliation is required; stopping local transport cannot undo upstream billed effects.
  - *Remediation:* An authorized owner must inspect and recover expired leases and containers. Never bypass IAM or refund uncertain reservations automatically.
- **Low Severity (Optimizations / Best Practices):**
  - *Issue:* Persisted path/key binding deliberately prevents automatic IAM relocation or key rotation.
  - *Remediation:* Provide a reviewed authority migration before supporting these operations; do not edit binding rows.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** `PlatformAuthority` requires durable IAM and separate database files. Dedicated requester/approver/owner permissions preserve role separation. CLI platform mode requires a private token file and matching tenant/subject at initialization; no local owner credential is issued.
- **Data & Schema Contracts:** Swarm schema 2 and historical signatures remain. Signed authority binding plus an audit event detect changes/selective deletion. IAM-before-swarm writer reservation prevents revocation publication/commit between authorization and swarm commit. No cross-store atomicity or external-effect exactly-once guarantee is claimed.
- **AI & Model Runtimes:** Provider/prompts are unchanged. Real fixture TLS and Docker workflows exercise shared credentials and separate approval. Active revocation cancels/joins provider processes, retains uncertain usage and produces no approval evidence. Fixtures are not live-quality evidence.
- **Resilience & Governance:** Cases exercise MCP plus swarm session use, tenant isolation, unrelated roles, self-approval denial, suspension/role update/revocation, restart, expiry/outage, binding downgrade/tampering/removal, CLI export and revocation ordering with an independent HTTPS witness. Trusted host administrators remain outside the boundary.

### 4. Architect’s Action Directive

1. Configure durable IAM, explicit swarm roles and private token files; initialize new platform-bound state rather than silently rebinding old stores.
2. Independently activate witnessing where required and perform deployed recovery/outage drills.
3. Implement reviewed historical mapping/import and credential reissue before deployment cutover; preserve original signed evidence and stop on ambiguous ownership.
4. Continue shared task/capability/coordinator contracts and the PM-to-coding vertical slice; qualify latency, concurrency and recovery before broader admission.

## Verification

All five repository gates passed: **478 tests, zero failures/errors/skips**, including **24 shared-identity acceptance cases**. Actual TLS model fixtures and Docker workers exercise the shared workflow and active revocation; independent HTTPS witness tests prove rollback denial and revocation-publication ordering. A clean wheel outside the checkout passes shared CLI/PM MCP sessions and revocation after reopening authority/state; all **100 packaged MAS Python files** match the final source. Executed counts and source/artifact hashes are recorded in [shared identity evidence](SHARED_SWARM_IDENTITY_EVIDENCE.json). Raw logs, JUnit and clean wheel are retained outside Git under `/workspace/review-evidence/shared-identity-*`. No production deployment, live-model reevaluation, historical import or enterprise rating is claimed.
