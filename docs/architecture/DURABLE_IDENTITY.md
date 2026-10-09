# Durable identity and session revocation

This is the single-host identity authority for the explicitly tenant-bound PM HTTP/MCP pilot. It does not enable multi-tenancy for legacy MAS entry points and is not an OAuth/OIDC identity provider. Use the [tenant boundary contract](TENANT_BOUNDARY.md) when constructing services.

## Configuration and enrollment

Set `MAS_IAM_DB_PATH` to an absolute SQLite file in a private host directory, and supply the persistent private `MAS_IAM_SECRET` through the host secret manager. Alternatively pass `db_path` and `signing_secret` to `MultiTenantIAM`. Never embed production key values in Git, logs or client requests. Proxy-injected remote API placeholders are not local signing keys.

The store requires POSIX ownership and permissions: directory `0700`, database and initialization lock `0600`, owned by the service UID, without symlink ancestors or hard-linked database files. New directories/files are created privately; existing unsafe permissions are rejected. Place identity storage outside every tenant workspace; tenant scope rejects a store configured underneath the workspace tree. Workers do not receive the store or signing key.

A missing configured key, mismatched existing key, unsupported schema, corruption or unavailable authority fails closed. Opening an existing unrecognized database never silently initializes a replacement registry. Do not delete a production store to clear an error. Investigate and recover it while services are offline.

Provision tenants and principals through trusted host code once. Restart reopens current persisted identities and sessions without reenrollment. `get_tenant` and `get_principal` return snapshots in durable mode; mutating those objects does not persist changes. Use `register_principal` to explicitly replace a principal's roles/scopes. That operation atomically revokes the principal's current sessions, requiring fresh enrollment credentials. Empty role/scope sets remain empty. Suspending a tenant atomically revokes its sessions and prevents further issuance.

No public registration endpoint exists. Session issuance remains a trusted host operation. Signed token claims alone do not grant access: the token must match a recorded issued session. Only token hashes are stored; bearer credentials and the signing key are absent from the SQLite store.

## Revocation

Python API:

```python
# Read your public session ID through the verifier; never log the bearer token.
identity = iam.verify_token(credential)
iam.revoke_session(credential, identity.token_id)  # Self logout.

# A valid tenant administrator may revoke another session in the same tenant.
iam.revoke_session(admin_credential, target_session_id)
iam.revoke_principal_sessions(admin_credential, "operator")
```

Tenant HTTP API:

| POST endpoint | JSON body | Required authority |
| --- | --- | --- |
| `/api/identity/sessions/revoke` | `{}` | Valid session; revokes itself |
| `/api/identity/sessions/revoke` | `{"session_id":"<64-character session ID>"}` | Own session, or current tenant administrator |
| `/api/identity/principals/revoke-sessions` | `{"user_id":"operator"}` | Current tenant administrator |

Send the issued credential in the Authorization Bearer header. The server's configured tenant controls ownership; clients cannot choose another tenant. Readers can log themselves out without write permission. An administrator cannot revoke another tenant's session. Administrative authority and the revoker's own session are rechecked inside the same write transaction as the revocation. Bulk revocation applies to sessions existing at that transaction; a trusted issuer may create a fresh session afterward.

Repeated administrator revocation of an already-revoked target is harmless. A self-revoked credential immediately ceases to authenticate, so retrying logout with that credential is denied.

## Consistency and failure handling

The store uses SQLite transactions, FULL synchronization, a five-second busy timeout and a bounded initialization lock. Role changes, issuance, revocation and their signed audit events commit together. If audit persistence fails, the operation fails and rolls back; it does not report successful revocation while leaving the credential valid. Process death during an uncommitted transaction recovers the earlier authority state.

Authorization reads current tenant/principal/session state from a database snapshot on every check, including checks on previously verified request contexts. Separate coordinator processes on the same host observe committed revocation without a local credential cache. Checks ordered after the revocation commit deny access. A previously authorized side effect can already be in progress; revocation does not retroactively undo work or automatically kill running workers. Workload cancellation remains a separate runtime responsibility.

Record HMACs, a signed audit chain/head and current record digests reject modified records, selective old-session replay and truncated audit tails when the current authority head remains intact. They cannot distinguish restoration of an older authentic authority snapshot. External audit anchoring remains a production blocker.

## Backup and recovery

Use the SQLite backup API through `iam.backup(destination)` from trusted host administration. The destination must be a new file in an existing private directory; backups are `0600`, consistent snapshots and never overwrite existing files. Retain the corresponding private signing key separately through the secret manager. A replacement key cannot validate an existing store.

For a normal restart, reopen the existing database with its original key. This retains committed session revocations.

For backup restoration, keep all request servers offline. Restore into a private directory, reopen with the original key, and **invalidate every session before allowing traffic**, especially when the backup predates recent revocations:

```python
restored = MultiTenantIAM(db_path=restored_database_path)
restored.invalidate_all_sessions()  # Trusted host operation; not an HTTP/agent tool.
# Issue fresh credentials through trusted provisioning, then start request servers.
```

The invalidation is transactional and remains effective after restart. Restoring an old backup and serving it immediately with the original key can revive old credentials; local signatures cannot detect that replay. The offline fence mitigates deliberate restore operations and does not detect hostile rollback. Do not advertise it as an external audit anchor.

## Limits and follow-up

Use one trusted POSIX host and a local SQLite filesystem. Multi-host/NFS authority, external identity federation, online signing-key rotation and production-scale authentication load have not been qualified. The current integrity check scans the audit history on each read; its cost grows with retained history. Measure and design bounded authenticated indexing/retention before high-volume use without weakening freshness or integrity checks.

Durable identity does not isolate shared memory, the model gateway, Git/browser/cloud-data tools, general orchestration or legacy APIs. Those services still require explicit tenant-aware integration and adversarial acceptance.
