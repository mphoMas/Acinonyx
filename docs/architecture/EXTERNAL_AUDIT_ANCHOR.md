# External identity audit anchoring

The coordinator compares its signed identity audit checkpoint with a live independently administered HTTPS witness. A checkpoint contains the audit sequence and the latest audit signature. The witness retains one forward-only head per enrolled authority namespace, with a signed audit history of its own.

This implementation is verified with a separate TLS process and independently stored witness database. Production requires a separate host or security domain, distinct witness signing key, independent administrators and a retention/restore policy that prevents rolling the witness back with the coordinator. Running both databases in the same snapshot domain does not provide that independence. The service does not attest identity-policy semantics or defend a compromised trusted coordinator.

## Commit protocol

```mermaid
sequenceDiagram
    participant C as Trusted coordinator
    participant D as Identity SQLite
    participant W as Independent HTTPS witness
    C->>D: Begin transaction; verify local signed history
    C->>W: Fresh authenticated head read
    W-->>C: Current checkpoint + request challenge
    C->>C: Require exact local/witness match
    C->>D: Stage identity change and signed audit
    C->>W: Compare-and-set old head to proposed head
    W-->>C: Persisted proposed checkpoint + challenge
    C->>D: Commit with FULL synchronization
    C-->>C: Acknowledge the identity operation
```

The external fence is published **before** the SQLite commit. If publication never occurs, a failed or crashed transaction rolls back normally. If publication occurs and commit fails, crashes or loses its acknowledgement, the witness can remain ahead of the local database. Authorization then fails closed until trusted recovery. The service never rewinds its head to accommodate an older database.

This deliberately prioritizes rejection of stale authority over availability. A mutation exception can leave the authority quarantined; do not interpret an exception as proof that the witness did not advance. A successful mutation is returned only after external acknowledgement and local commit. Exact compare-and-set replay is idempotent; competing forks, older sequences and same-sequence different hashes are rejected.

Every authority transaction checks the live witness. There is no offline checkpoint cache or fallback to local signatures. Reads already authorized before a revocation are not retroactively undone; later checks reject a mismatched or stale authority. Existing unanchored coordinator objects cannot continue using a database after another trusted process attaches its witness binding.

## Coordinator configuration

Set all three values through trusted configuration outside the identity database's restore boundary:

| Name | Purpose |
| --- | --- |
| `MAS_IAM_ANCHOR_URL` | HTTPS origin of the independent witness, without user info, query or path |
| `MAS_IAM_ANCHOR_NAMESPACE` | Unique pre-enrolled authority namespace, fixed across normal coordinator restarts |
| `MAS_IAM_ANCHOR_TOKEN` | Private writer credential, scoped to that namespace; supply through secure settings |

Continue configuring durable `MAS_IAM_DB_PATH` and private `MAS_IAM_SECRET`. Partial anchor settings are rejected. A database that records a signed witness binding cannot reopen with anchoring omitted or with another endpoint/namespace. Token values are not stored in the binding. TLS trust must validate the configured witness; never disable certificate checks.

Explicit host integration is also supported:

```python
from mas.audit_anchor import HTTPAuditAnchor
from mas.iam import MultiTenantIAM

anchor = HTTPAuditAnchor(witness_origin, authority_namespace, writer_credential)
iam = MultiTenantIAM(db_path=identity_database_path, anchor=anchor)
```

The bearer credential travels through stdin to an isolated trusted transport worker, not process arguments. The worker receives proxy/CA configuration without coordinator identity or model signing secrets. Python isolated mode prevents imports from an untrusted working directory. Each exchange has a total hard deadline (default three seconds), a bounded response and a fresh unpredictable challenge; redirects, duplicate JSON keys, nonfinite values and mismatched namespaces/challenges are rejected.

## Witness enrollment and deployment

The witness administrator owns a distinct private POSIX directory/database and signing key. Keep that key off the coordinator. Generate a high-entropy namespace writer credential through the witness administrator's secret-management process; supply it to the coordinator securely. Credential files used by the CLI must be private owner-only regular files. The writer credential can read and advance its enrolled head, but cannot enroll, delete, reset or rewind namespaces.

For a **new** identity database, enroll its unique namespace at genesis (sequence zero, empty hash) before starting the anchored coordinator:

```bash
python -m mas.audit_witness \
  --database /private/witness/state.sqlite \
  --key-file /private/witness/signing.key \
  enroll --namespace authority-prod \
  --token-file /private/witness/authority-prod.token
```

For an **existing** identity database, stop request servers and review its current authority first. Trusted host administration may export `iam.audit_checkpoint()` to a non-secret JSON checkpoint file while the existing store is still unanchored. Enroll a new namespace with that checkpoint:

```bash
python -m mas.audit_witness \
  --database /private/witness/state.sqlite \
  --key-file /private/witness/signing.key \
  enroll --namespace authority-prod \
  --token-file /private/witness/authority-prod.token \
  --initial-checkpoint-file /reviewed/current-checkpoint.json
```

Attaching an anchor never automatically publishes or overwrites a historical local head. Enrollment of an existing namespace fails. Capture the checkpoint from reviewed current state, not from an arbitrary backup presented by a requester.

Start the independently deployed TLS witness with its managed certificate and private TLS key:

```bash
python -m mas.audit_witness \
  --database /private/witness/state.sqlite \
  --key-file /private/witness/signing.key \
  serve --host 0.0.0.0 --port 9043 \
  --cert-file /private/tls/certificate.pem \
  --tls-key-file /private/tls/server.key
```

Its sole application endpoint is authenticated `POST /v1/checkpoints/<namespace>` with read/advance operations. It does not expose namespace administration. Keep the witness behind appropriate network controls and qualify request-rate limits, availability and independent storage retention before production. Coordinator credentials can force denial by advancing to an unusable head; treat them as privileged control-plane secrets.

## Backup and crash recovery

A current identity snapshot matching the witness can reopen normally. Any older snapshot, even one with valid local signatures, is rejected. The coordinator must never change its configured namespace or strip the witness binding merely to bypass that rejection.

If the witness is ahead after an uncertain commit, keep request servers offline. Investigate the witness head and transaction outcome. Recover a valid local snapshot that exactly matches the witnessed checkpoint when available. Neither automatic rewind nor accepting a local head that is merely less than the witness is allowed.

If no matching snapshot exists, recovery requires a separately authorized **new authority generation**: keep the old witness namespace permanently fenced; create a fresh identity store with a new private signing key; provision current permissions from reviewed trusted sources; let the witness administrator enroll a new namespace for that generation; issue fresh credentials before allowing traffic. Old bearer credentials cannot authenticate in the fresh store. This is controlled reprovisioning, not an automatic rollback repair. Do not restore the witness database from the same old snapshot to make the heads agree.

The unanchored `invalidate_all_sessions()` restore procedure remains useful for unanchored deployments, but it cannot bypass an external checkpoint mismatch.

## Scope

Anchoring covers the durable identity audit authority. It does not independently verify release tests, attest model quality, or automatically anchor PM/general/swarm audit histories. Whole-platform multi-tenancy, multi-host failover, witness storage disaster recovery, key rotation and production load remain separate qualifications. Witness integrity currently scans its retained audit history; authentication paths also incur fresh HTTPS/process overhead. No production latency or availability rating is claimed from the acceptance suite.
