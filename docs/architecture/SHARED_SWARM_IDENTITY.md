# Shared platform and swarm identity

Implemented for explicitly platform-bound coding stores. This is an incremental consolidation adapter, not a completed platform/interface cutover. Baseline: `aa79cdcbeba1778dc7204fe73314b10893011c9c`.

## Authority and permissions

`PlatformAuthority` uses durable `MultiTenantIAM` for issued session verification, current tenant lifecycle, revocation and permission checks on every swarm operation. No platform session is copied into the swarm's local credential table. Tenant and subject come from authenticated IAM, not CLI claims or task arguments.

| Platform role | Permission | Swarm behavior |
| --- | --- | --- |
| `swarm_requester` | `swarm:request` | Submit, read, claim, execute, reserve/settle usage and cancel tenant runs; cannot approve. |
| `swarm_approver` | `swarm:approve` | Read and approve tenant runs with real evidence; cannot submit/execute. |
| `swarm_owner` | All three swarm permissions | Requester/approver operations plus owner recovery, cleanup, audit and backup. Cannot approve its own submission. |

Tenant administrator does not implicitly gain swarm permissions. Assign dedicated swarm roles or explicitly reviewed scopes through trusted IAM provisioning. A user needing PM operations can hold a PM-capable role alongside its swarm role; the same issued session then works through supported tenant-bound platform interfaces and the swarm. Unrelated legacy interfaces are not admitted by this adapter.

Swarm owner is not an IAM security administrator. Platform session enrollment, role changes, tenant suspension and revocation remain IAM operations; swarm CLI `enroll` and `revoke` are rejected in platform mode. Self/admin revocation uses existing platform identity APIs and authorization rules.

## Persisted binding and transaction ordering

A signed `authority_binding` row fixes the mode, binding version, absolute IAM database path and non-secret signing-key identifier. A matching signed audit event detects selective binding-table removal. Reopening a platform-bound store without the adapter, with another IAM store/key or with a changed binding fails. Historical signed run schema remains version 2; the binding is an additional table and audit event, not rewritten historical records.

Acquire the IAM SQLite writer reservation before the swarm write transaction. Retain it through authentication and swarm commit. This prevents concurrent identity revocation from either publishing a newer external witness checkpoint or committing between the authorization check and the swarm mutation. A read lock alone would not prevent early witness publication. The guard does not mutate IAM or advance its witness when no identity data changes.

The guard lasts only for short local operations; it does not span model requests or container execution. Authorization is checked again for subsequent operations. No cross-database atomicity or reversal of completed side effects is promised. Fixed IAM-before-swarm lock order and existing bounded SQLite waits apply. Serialization and repeated audit/HTTPS checks require capacity qualification before high-throughput use.

Trusted host administrators still control keys, stores and code. Whole authentic swarm database/audit rollback is not externally fenced by this change; the witness protects configured IAM authority only. Binding deletion detection is selective integrity protection, not an external immutable ledger.

## CLI setup

1. Provision a private durable platform IAM database outside tenant workspaces using the existing [durable identity instructions](DURABLE_IDENTITY.md). Persist its signing key. If external freshness protection is required, configure and enroll the [independent witness](EXTERNAL_AUDIT_ANCHOR.md); its production deployment remains separate.
2. Through trusted IAM provisioning, assign an owner, requester and separate approver their explicit roles, then issue sessions. Store each bearer in an owner-only regular file; never place credentials in chat, argv, tracked files or test evidence. The CLI file size limit is 8 KiB.
3. Configure `MAS_IAM_DB_PATH` and the original private `MAS_IAM_SECRET` through trusted local runtime configuration. No demonstration credentials are production credentials.
4. Initialize a **fresh** private swarm state directory with the platform owner session. The supplied tenant/subject must match the verified owner. No local `owner.token` is created.

```bash
mas-swarm --identity platform --state-dir /private/swarm --token-file /private/owner.token init --tenant acinonyxlabs --subject owner
mas-swarm --identity platform --state-dir /private/swarm --token-file /private/requester.token submit --request-key task-v1 --goal 'Return input unchanged' --cases /private/cases.json
mas-swarm --identity platform --state-dir /private/swarm --token-file /private/requester.token run RUN_ID --image REVIEWED_DIGEST_PINNED_IMAGE
mas-swarm --identity platform --state-dir /private/swarm --token-file /private/approver.token approve RUN_ID --candidate-hash EXACT_HASH
mas-swarm --identity platform --state-dir /private/swarm --token-file /private/requester.token export RUN_ID --out /private/approved.py
```

Use actual reviewed image/IDs/hashes from the run; placeholders are not runnable values. Provider configuration and restricted Docker requirements remain as documented in [supervised swarm](SUPERVISED_SWARM.md). Export and backup retain the authority guard during their local file effect, so revocation cannot commit during that authorized operation. Filesystem effects are not transactionally reversible with SQLite.

The Python API is `Store(state_path, swarm_signing_key, authority=PlatformAuthority(iam))`. IAM and swarm state must use different database files. Keys have separate purposes and are never mounted into candidate workers. Persistent state remains trusted-host storage, not a remote enrollment service.

## Existing local stores and migration

Local-only stores remain supported for compatibility, with their own persisted local binding. Selecting platform mode does not import local tokens, change subject ownership or silently switch an existing local store. Nonempty legacy state and already local-bound state are rejected for direct rebinding.

For a pilot, create new platform-bound state and retain old signed stores as restricted historical evidence. Do not copy credentials or modify binding rows to force a migration. A general historical run/identity import tool and reviewed manifest/cutover procedure remain pending under the [consolidation migration plan](MAS_CONSOLIDATION_MIGRATION.md). Existing local workflows have not been automatically migrated in any deployment.

Signing-key rotation, IAM database relocation and authority generation replacement need a reviewed binding migration; automatic rebinding is intentionally absent.

## Active revocation and recovery

The existing workflow monitor rechecks store authorization between asynchronous steps. Revocation/suspension/outage cancels local model/worker activity when observed, with cancellation cleanup joining child processes. This is polling plus synchronous authority checks, not an instantaneous or hard 100 ms guarantee. An upstream provider may already have billed or completed a request; cancelling the local transport cannot undo it.

Once authorization is lost, the revoked caller cannot mark a run cancelled or settle uncertain usage. Its active lease and reservation remain; no approval evidence is manufactured. An authorized owner must inspect state, wait for lease expiry and use existing `recover` with the run's reviewed image to reconcile containers and mark it interrupted. Never restore the revoked token or bypass IAM to write a terminal state. Subsequent retry is a new explicitly admitted run, not automatic replay.

Fresh sessions after restart see current revocation. Restoring stale IAM state is denied when its independently retained witness head is newer. IAM unavailability causes denial; no local credential fallback exists.

## Verification scope

See [shared identity review](../reviews/SHARED_SWARM_IDENTITY_REVIEW.md) for executed evidence. Real fixture TLS and Docker tests exercise the adapter; fixture model output is not a live-model quality benchmark. Production witness activation, historical migration, wider broker/interface cutover and sustained capacity remain incomplete.
