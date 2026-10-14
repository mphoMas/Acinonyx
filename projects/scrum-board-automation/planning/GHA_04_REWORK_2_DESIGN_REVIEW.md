# GHA-04 rework 2 design review

Candidate **9ccea91d**. **REJECTED (REQUIRES RE-WORK)** for implementation agreement. GHA-03 remains accepted. This is a design review; no runtime tests are claimed.

## Retained improvements and decisions

Separate logical actions/attempt receipts, structured canonical identity, permanent token provenance versus expiring replay cache, composite parent indexes, no-overwrite artifact link promotion and historical lookup before freshness are retained.

Open questions resolved:
1. **Retention:** for this initial local slice retain referenced artifacts under quota; reject new admissions when quota is exhausted. Defer configurable archive expiry/deletion. Never UPDATE an immutable receipt to mark expiry; a later retention feature needs a separate mutable lifecycle projection/event.
2. **Stale refresh:** fail closed for new admission and schedule background authoritative refresh. No synchronous network fetch while holding a business transaction. Historical authorized reads remain available and labeled historical. Fifteen-minute projection TTL is a bounded-cache policy, not proof of instantaneous GitHub currentness.

## Remaining blockers

### B1 — Refresh publication is not fenced (high)

Ticket acquisition sets a UUID/expiry, but publication UPDATEs current heads and clears the ticket using only tenant/project/PR. Suppose worker A's lease expires, B obtains a new ticket and publishes H8, then A returns H7: A can still publish and clear B's ticket. BEGIN IMMEDIATE serializes those writes; it does not reject stale ownership.

**Required:** publication transaction must conditionally verify ticket ID, owner/fencing epoch, REFRESHING status and unexpired lease, then update projection and finish ONLY that owned ticket atomically. Zero matching rows means discarded stale response, no generation update. Specify creation of initial tickets/projections, failed-refresh transitions and admission during active/stalled refresh. Add expired-A/B-refresh/late-A scenario to S01/S06.

### B2 — Authority synchronization lacks an actual integration/recovery protocol (high)

The document names proposed `iam.set_tenant_status`/`registry.update_connector` as supported mutators. Existing methods include `iam.suspend_tenant` and registry update/register/remove. A PM epoch mirror alone does not keep existing APIs, separate IAM stores and all process instances synchronized. The tenant-only epoch row also conflates multiple connector policies.

**Required:** explicitly select the supported profile, current APIs that must be integrated and connector identity key. Specify update ordering (fail-closed revocation fence before external-store change; activation only after authoritative activation), crash/reconciliation and unavailable-sync handling. All supported mutators must honor it, including removal and suspension. Identify any necessary IAM/registry changes as scoped design additions before implementation. Do not claim mathematical exclusion of races merely from PM locking; name the authoritative epoch and admission/update linearization points.

### B3 — Quota and GC protocol has no per-admission reservation/fence (high)

The only quota table has aggregate counters, but reaper needs reservation age, owner, digest and receipt association—all absent. A paused admission can lose its reservation after 10 minutes and still commit. GC performs a read-reference query then unlink, allowing a new reference between them. Existing-blob reuse can also double-charge used bytes.

**Required:** persist uniquely identified reservations with digest/size/owner/expiry/state and fencing; expired reservation cannot later commit without reacquisition. Define deduplicated blob accounting and shared quota/GC/admission lock or transactional fence. GC must atomically exclude active reservations AND committed references while preventing a new reference until unlink is durably recorded. Descriptor-based no-follow existing-file validation avoids an islink/open race. Specify every crash boundary and reservation reconciliation.

### B4 — Observation-to-receipt ownership remains independent (high)

Observation records have one FK to receipt_id and another to tenant/project/issue. A valid TenantB task can therefore be combined with TenantA receipt. The receipt relation itself must enforce the matching ownership tuple. Composite parent task checks alone do not do that.

**Required:** add parent receipt UNIQUE ownership tuple and one composite observation-to-receipt FK covering receipt_id/tenant/project/issue. Test direct mismatched insertion with two otherwise valid tasks. Preserve complete MAS execution association or explicitly quarantine it without claiming authoritative binding.

## Action

Update exact SQL/protocols and acceptance scenarios for these existing requirements; preserve retained improvements. Submit revised design only. Read `ANTIGRAVITY_GHA_04_REWORK_3_BRIEF.md`. No code/migrations/live deployment, workflow or provider activation before agreement.
