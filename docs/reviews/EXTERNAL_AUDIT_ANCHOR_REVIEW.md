# Independent external identity audit anchor review

Baseline: `22ddde03a97e558efb7488ab462dc627bde5609b`. Scope: explicitly anchored durable IAM stores and the separately deployed HTTPS witness. Operational instructions: [external audit anchor](../architecture/EXTERNAL_AUDIT_ANCHOR.md).

### 1. Verdict & Executive Summary

- **Status:** APPROVED WITH CONDITIONS for the supported single-host identity pilot. Production activation requires an independently administered witness; whole-platform enterprise deployment remains REJECTED (REQUIRES RE-WORK).
- **Core Summary:** Restoring an authentic old identity database can no longer revive revoked credentials when its configured independent witness retains the newer checkpoint. Authority mutations advance the external fence before local commit; uncertain outcomes deny authentication rather than silently restoring old authority. Real verified TLS and separate-process tests establish the protocol behavior, not production hosting independence.

### 2. Architectural Audit & Critical Findings

- **High Severity (Deployment Blockers):**
  - *Issue:* Shared administration, storage or backup rollback between coordinator and witness defeats external freshness. No independently hosted production endpoint has been deployed in this work.
  - *Impact:* A coordinated rollback could resurrect revoked authority.
  - *Remediation:* Deploy the witness under separate administrative credentials, signing key, persistent private storage and restore policy; provision its HTTPS origin and scoped writer credential securely.
  - *Issue:* Anchoring covers durable identity authority, not all platform logs, model runtimes or shared data services.
  - *Impact:* These tests do not qualify enterprise tenancy or AI correctness.
  - *Remediation:* Extend tenant enforcement to each admitted runtime service and independently qualify release evidence.
- **Medium Severity (Technical Debt / Fragility):**
  - *Issue:* Acknowledgment loss or local commit failure after witness advance deliberately quarantines the coordinator. Authentication also depends on witness availability.
  - *Remediation:* Exercise the documented trusted recovery procedure operationally; preserve matching backups and qualify availability. Never rewind the witness or drop its binding to recover service.
  - *Issue:* Each authority transaction performs fresh HTTPS probes in isolated workers and verifies retained audit history. Production concurrency, rate limiting, retention, key rotation and high availability are unqualified.
  - *Remediation:* Use an operationally controlled TLS ingress and measure authentication throughput and failure behavior before production admission. Any optimization must preserve fresh revocation enforcement.
- **Low Severity (Optimizations / Best Practices):**
  - *Issue:* Unconfigured development stores remain unanchored.
  - *Remediation:* Require complete anchor configuration in deployment policy; attaching once persists a binding that prevents accidental downgrade.

### 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** Separate-process TLS witness with its own durable SQLite state and key; authenticated forward-only compare-and-set checkpoints. TLS handshakes and request reads are timed out in request threads, so a stalled handshake does not block the listener. The client bounds total network lifetime with a killable isolated worker and rejects redirects.
- **Data & Schema Contracts:** Checkpoints contain audit sequence and signature, not identity payloads. Signed persisted origin/namespace binding prevents accidental downgrade. Exact checkpoint equality is required for reads; concurrent forks admit one winner. Existing authority must be reviewed and enrolled at its exact current head.
- **AI & Model Runtimes:** No model behavior or quality was re-rated. Witness provisioning and recovery are trusted operator actions, absent from agent tool interfaces. Transport workers avoid importing code from an untrusted current directory and do not inherit unrelated application credentials.
- **Resilience & Governance:** Tests cover full authentic database rollback, independent witness restart, outage, malformed and replayed responses, TLS trust rejection, slow transport, concurrent forks, audit failure, commit failure, lost acknowledgment and actual process death on both sides of publication. Actual PM HTTP authorization rejects rollback. The witness writer cannot remotely enroll, delete or rewind checkpoints.

### 4. Architect’s Action Directive

1. Independently deploy the witness using the documented TLS and private-file requirements; enroll a fresh namespace at genesis or a reviewed existing checkpoint.
2. Configure the coordinator's private durable store, fixed witness origin/namespace and scoped bearer through environment secrets.
3. Test witness outage and matching-backup restoration in that actual deployment. Retain the old fenced generation when uncertain state requires a new reviewed authority generation.
4. Qualify capacity, independent retention/restore, key lifecycle and runtime tenant enforcement before requesting enterprise approval.

## Verification

Full repository gate: **424 passed, zero failures/errors/skips**, including **30 external anchoring cases**. A clean installed wheel outside the checkout passed separate-process verified-TLS persistence, revocation and rollback checks; all **96 packaged MAS Python files** match the final source byte-for-byte. Final counts and artifact hashes are recorded in [external anchor evidence](EXTERNAL_AUDIT_ANCHOR_EVIDENCE.json). Raw logs, JUnit and wheel are retained outside Git under `/workspace/review-evidence/external-anchor-*`. No production endpoint, multi-host qualification or live model reevaluation is claimed.
