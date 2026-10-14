# GHA-03 Authentication Gateway & Observation Ingestion Specification (V1 — Revised Design)

**Task**: GHA-03 — Authentication Gateway & Observation Ingestion Mechanism
**Branch**: `feat/scrum-board-automation`
**Implementation Owner**: Antigravity Development Team
**Architecture Reviewer**: Codex
**Date**: 14 October 2026
**Status**: Revised Design & Specification Checkpoint (Pre-Implementation Submission)
**Reviewed Candidate**: `54cc7916`
**Baseline Commit**: `334a1227`
**Governing Documents**:
- [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_REWORK_BRIEF.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_REWORK_BRIEF.md)
- [`projects/scrum-board-automation/planning/GHA_03_DESIGN_REVIEW.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_03_DESIGN_REVIEW.md)
- [`projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_HANDOFF.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/ANTIGRAVITY_GHA_03_DESIGN_HANDOFF.md)
- [`projects/scrum-board-automation/planning/GHA_02_FINAL_ACCEPTANCE_REVIEW.md`](file:///home/acinonyx/Desktop/MAS/projects/scrum-board-automation/planning/GHA_02_FINAL_ACCEPTANCE_REVIEW.md)
- [`company/DELIVERY_OWNERSHIP.md`](file:///home/acinonyx/Desktop/MAS/company/DELIVERY_OWNERSHIP.md)

---

## 1. Review Finding Closure & Architectural Slice Selection

### 1.1 Review Finding Reconciliation Table

The following table maps each architectural finding and rework directive from `GHA_03_DESIGN_REVIEW.md` and `ANTIGRAVITY_GHA_03_DESIGN_REWORK_BRIEF.md` directly to its revised design section, responsible component, and testable negative scenario:

| Review Finding & Directive | Revised Section | Responsible Component | Testable Negative Scenario & Expected Outcome |
|---|---|---|---|
| **1. Replay/Receipt Transaction (High)**<br>Replay store undefined; conflicting zero-write claims; restart/concurrency unaddressed; persistent receipt claimed without storage engine. | § 1.2, § 6.1, § 6.2 | `GatewayAdmissionEngine`<br>`GHA03Validator` | **Selected offline validator slice**: Returns `VALIDATED_UNTRUSTED_OBSERVATION` with zero database writes. Durable replay store and persistent ingestion deferred to GHA-04. Security audit logging is separated from business transactions. (TC-22: 200 OK with zero DB mutation). |
| **2. Workflow & Authorization Profile (High)**<br>Direct admin workflow expanded profile unnecessarily; missing repo/path binding; runner claims conflated with verifier evidence. | § 2.1, § 2.2, § 2.3 | `OIDCClaimValidator`<br>`ServerIdentityResolver` | Reusable-workflow, witness-only profile strictly enforced. Direct admin workflow completely removed. Pinned workflow repository, path, and 40-hex SHA verified. Events/refs/runner-env checked. Runner claims treated strictly as untrusted observations (`authority_verified: false`). (TC-15, TC-16, TC-17: 403 Forbidden). |
| **3. Token Age & JWKS Lifecycle (Medium)**<br>`exp - iat` is lifetime not age; missing positive lifetime, max age, duplicate/extra headers, RSA parameter checks, redirect policy, cache expiry. | § 3.1, § 3.2, § 3.3 | `JWKSClient`<br>`TokenParser` | Max JWT length 8192 bytes. Header permits only `alg` and `kid` (and optional `typ`). Duplicate keys and extra headers rejected. Positive lifetime (`exp > iat`), max lifetime $\le 900$s, max age (`now - iat <= 900`s), clock skew $\le 30$s. Fixed JWKS URL with 0 redirects, 64 KiB cap, RSA modulus $\ge 2048$ bits. 24h TTL, single-flight refresh, $\ge 5$ min cool-down, fail closed on outage (503). (TC-03 through TC-12). |
| **4. IAM & Request Contracts Mapping (Medium)**<br>Fictitious project/connector revocation APIs in `MultiTenantIAM`; permission label mismatch (challenge belongs to builder); body role extras ignored instead of rejected; request schema omitted archive/fencing coordinates. | § 4.1, § 4.2, § 5.1, § 5.2 | `ServerIdentityResolver`<br>`ObservationSubmissionSchema` | Server-owned `GitHubConnectorConfig` maps numeric IDs to tenant/project. Uses real `MultiTenantIAM.get_tenant()` for active status. Ephemeral per-request witness context (`delivery:witness_observe`); no invented revocation APIs or minted sessions. Delivery actions aligned (builder challenges, reviewer resolves). Single JSON request format with full `DeliveryManifest` coordinates, inline base64 archive, and fencing token. Request body role/tenant extras rejected via `StrictModel(extra="forbid")`. (TC-13, TC-14, TC-18, TC-19, TC-20). |

---

### 1.2 Architectural Slice Selection: Offline Observation Validator

Per Directive 2 of `ANTIGRAVITY_GHA_03_DESIGN_REWORK_BRIEF.md`, Antigravity explicitly selects the **Offline Observation Validator slice** for GHA-03:

1. **Pure Validation Engine**: The GHA-03 gateway operates as a stateless admission and validation engine. Given a GitHub Actions OIDC Bearer token, a `DeliveryManifest`, and an optional bounded artifact archive, it executes cryptographic verification, claim boundary checks, server-owned identity resolution, and structural schema validation.
2. **Standard Typed Outcome**: A successful admission returns a structured `WitnessObservationValidationResponse` with `status: "VALIDATED_UNTRUSTED_OBSERVATION"`, `transport_authenticated: true`, and `authority_verified: false`.
3. **No Database Writes**: The validator performs **zero database writes** to `pm_delivery_tasks`, `pm_delivery_submissions`, `pm_delivery_events`, or any coordinator state table. Task phase, revision, and budget holds remain entirely unchanged.
4. **Ingestion Persistence Deferred to GHA-04**: Persistent ingestion, durable receipt storage, replay protection via an append-only token ledger, and PR-head freshness tracking are formally deferred to GHA-04, where the transactional idempotency ledger (`pm_source_events`) is owned and integrated.
5. **Separation of Business State and Security Logging**: Validation failure produces zero business state mutation. Security audit records (e.g. append-only `events.jsonl` host logs) capture failed authentication attempts, IP addresses, and rejection codes independently from business database transactions.

---

## 2. GitHub Actions OIDC Profile & Reusable-Workflow Specification

### 2.1 Reusable-Workflow, Witness-Only Profile (Strict)

GHA-03 enforces a single, immutable profile: **Reusable-Workflow, Witness-Only**. Direct admin workflow execution is completely removed from this boundary.

Candidate pull requests execute in untrusted forks or untrusted branches. They must **never** be permitted to define or alter their own verification workflows, test harness assertions, or gateway admission rules.

The caller workflow invokes a server-approved reusable workflow stored in a trusted, protected repository and branch. The gateway extracts and validates the following token claims:

```json
{
  "iss": "https://token.actions.githubusercontent.com",
  "aud": "mas-coordinator-delivery",
  "sub": "repo:octocat/Acinonyx:pull_request",
  "repository": "octocat/Acinonyx",
  "repository_id": "987654321",
  "repository_owner": "octocat",
  "repository_owner_id": "12345678",
  "run_id": "1029384756",
  "run_attempt": "1",
  "job_workflow_ref": "octocat/Acinonyx/.github/workflows/reusable-delivery-gate.yml@15e9f7634f191b29a28bfdf911925b42d71329a1",
  "job_workflow_sha": "15e9f7634f191b29a28bfdf911925b42d71329a1",
  "workflow_ref": "octocat/Acinonyx/.github/workflows/ci.yml@refs/pull/42/merge",
  "workflow_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
  "event_name": "pull_request",
  "ref": "refs/pull/42/merge",
  "sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
  "runner_environment": "github-hosted",
  "exp": 1792065000,
  "nbf": 1792064100,
  "iat": 1792064100,
  "jti": "550e8400-e29b-41d4-a716-446655440000"
}
```

### 2.2 Pinned Workflow Binding & Provenance Checks

The gateway resolves the enrolled project configuration and verifies exact workflow provenance:

1. **Commit SHA Pinning**: `job_workflow_sha` must match `approved_workflow_sha` (exact 40-character hexadecimal string).
2. **Repository & Path Pinning**: `job_workflow_ref` must match the exact string format:
   `f"{approved_workflow_repo}/{approved_workflow_path}@{approved_workflow_sha}"`
3. **Mutable Reference Rejection**: Any token where `job_workflow_ref` references a branch (`@refs/heads/*`), tag (`@refs/tags/*`), or non-40-hex commit reference is rejected immediately with 403 `WORKFLOW_NOT_PINNED`.
4. **Allowlisted Execution Conditions**:
   - `event_name` must be member of `permitted_events` (default: `["pull_request", "workflow_dispatch"]`).
   - `ref` must match the configured regex pattern for the event:
     - For `pull_request`: `r"^refs/pull/\d+/merge$"`.
     - For `workflow_dispatch`: must match an approved protected branch ref (e.g. `r"^refs/heads/main$"`).
   - `runner_environment` must match the configured environment (default: `"github-hosted"`).

### 2.3 Separation of GitHub Coordinates from Coordinator Execution Identity

GitHub Actions execution coordinates are strictly transport coordinates:
- GitHub `run_id` and `run_attempt` identify the CI pipeline invocation on GitHub's infrastructure.
- MAS coordinator execution coordinates are `run_id`, `intent_id`, and `attempt_id`.
- Under no circumstances does GitHub's `run_id` substitute for or impersonate the coordinator's `run_id`.
- **Candidate Identity & PR Head Unproven by Workflow Pinning**: A pinned workflow template proves only which workflow ran; it does **not** prove candidate identity, PR head freshness, or independent verification. In PR merge events, GitHub's `sha` claim is the temporary merge commit `refs/pull/N/merge`, not necessarily the candidate commit head.
- **Untrusted Observations Only**: All uploads from GitHub Actions are treated strictly as untrusted observations (`authority_verified: false`). Even if a runner is compromised, it can only submit untrusted observations; it cannot forge coordinator execution, submit delivery tasks as builder, or create acceptance as reviewer.

---

## 3. Cryptographic JWT Verification & Bounded JWKS Protocol

### 3.1 Strict JWT Token Parsing & Header Validation

1. **Bounded Token Size**: Maximum raw JWT string length is strictly capped at **8192 bytes**. Tokens exceeding this limit are rejected immediately prior to decoding with 413 `PAYLOAD_TOO_LARGE`.
2. **Header Parameter Rules**:
   - The JOSE header JSON must be strictly parsed. Duplicate header keys are rejected.
   - Permitted header parameters: `alg`, `kid`, and optional `typ` (must be `"JWT"` if present).
   - Extra header parameters (e.g. `jku`, `x5u`, `x5c`, `jwk`, `crit`) are strictly forbidden; their presence causes immediate rejection with 401 `INVALID_JWT_HEADER`.
3. **Algorithm Restriction**:
   - Allowed: Strictly asymmetric `RS256` (`RSA-SHA256`).
   - Disallowed: `none`, symmetric algorithms (`HS256`, `HS384`, `HS512`), elliptic curves (`ES256`, `ES384`), and `RS512` are rejected immediately during header inspection with 401 `UNSUPPORTED_ALGORITHM`.
4. **Key ID (`kid`) Requirement**: The header must contain a non-empty `kid` string with length $\le 128$ characters.

### 3.2 Bounded JWKS Retrieval & Cache Lifecycle

The gateway manages an offline-first, bounded JWKS cache:

```mermaid
flowchart TD
    A["Incoming Token (Max 8192 bytes)"] --> B["Inspect Header: alg == RS256, extract kid"]
    B -- "alg != RS256 or extra headers" --> ERR1["401: Invalid Header / Algorithm"]
    B -- "Valid Header" --> C{"kid in Cache?"}

    C -- "Yes (Cache Fresh < 24h)" --> D["Verify RS256 Signature with Public Key"]
    C -- "Yes (Cache Expired > 24h)" --> E["Initiate Single-Flight JWKS Refresh"]
    C -- "No (Unknown kid)" --> F{"Cool-down elapsed? (>= 5 min)"}

    F -- "No (< 5 min)" --> ERR2["401: Unknown Key ID (Throttled)"]
    F -- "Yes" --> E

    E --> G["Bounded HTTP GET: https://token.actions.githubusercontent.com/.well-known/jwks"]
    Note over G: Max 64 KiB buffer, 5.0s timeout, max_redirects = 0

    G -- "Redirect (3xx) / Timeout / HTTP Error" --> H{"Cached keys present?"}
    H -- "Yes, but kid missing/expired" --> ERR3["503: JWKS Unavailable (Fail Closed)"]
    H -- "No" --> ERR4["503: JWKS Unavailable (Fail Closed)"]

    G -- "200 OK" --> I["Validate RSA Keys (kty==RSA, use==sig, n, e, modulus >= 2048)"]
    I --> J["Update Cache (TTL = 24h, record fetch timestamp)"]
    J --> D

    D -- "Invalid Signature" --> ERR5["401: Invalid Signature"]
    D -- "Valid Signature" --> K["Proceed to Temporal & Claim Verification"]
```

1. **Fixed Endpoint & Zero Redirects**:
   - The JWKS URL is fixed to `https://token.actions.githubusercontent.com/.well-known/jwks`.
   - **No HTTP redirects are followed** (`max_redirects = 0`). Any 301, 302, 307, or 308 response is treated as a fatal network error to prevent SSRF and open-redirect exploitation.
2. **Resource Bounds**:
   - Maximum JWKS response payload capped at **64 KiB**.
   - Maximum number of keys parsed from JWKS capped at **32 keys**.
   - HTTP request timeout capped at **5.0 seconds**.
3. **Cache TTL & State Machine**:
   - **Fresh Cache ($< 24$ hours)**: Known `kid` keys are reused immediately.
   - **Expired Cache ($> 24$ hours)**: JWKS must be refreshed. If GitHub is unreachable on an expired cache, verification fails closed with 503 `JWKS_UNAVAILABLE`; stale keys are never accepted indefinitely.
   - **Unknown `kid` Cool-down**: If a token arrives with an unknown `kid`, the gateway refreshes the cache only if at least **5 minutes** have elapsed since the last external fetch. Bursts of tokens with unknown `kid` are throttled without outbound network calls, returning 401 `UNKNOWN_KEY_THROTTLED`.
   - **Single-Flight Synchronization**: Concurrent requests triggering a JWKS refresh share a single-flight mutex/future so that only one outbound HTTP request is dispatched to GitHub.
4. **RSA Key Parameter Validation**:
   - Keys must have `kty == "RSA"` and `use == "sig"`.
   - Modulus `n` and exponent `e` must be valid base64url-encoded integers.
   - The RSA modulus bit length must be $\ge 2048$ bits. Keys with sub-2048-bit moduli are rejected.

### 3.3 Strict Temporal Validity & Clock Skew

The gateway enforces four independent numeric temporal checks:

1. **Positive Lifetime**: `exp > iat`. Tokens with `exp <= iat` are invalid and rejected with 401 `INVALID_TOKEN_LIFETIME`.
2. **Maximum Lifetime**: `exp - iat <= 900` seconds (15 minutes). Tokens with lifetimes exceeding 15 minutes are rejected with 401 `INVALID_TOKEN_LIFETIME`.
3. **Maximum Token Age**: `now - iat <= 900` seconds. Tokens issued more than 15 minutes prior to evaluation are rejected with 401 `TOKEN_AGE_EXCEEDED`, even if `exp` is nominally in the future.
4. **Bounded Clock Skew Tolerance**: Skew tolerance is capped at $\le 30$ seconds:
   - Not issued in future: `iat <= now + 30` (else 401 `TOKEN_ISSUED_IN_FUTURE`).
   - Not valid in future: `nbf <= now + 30` (if `nbf` present; else 401 `TOKEN_FUTURE`).
   - Not expired: `now <= exp + 30` (else 401 `TOKEN_EXPIRED`).

---

## 4. Server-Owned Tenant & Identity Mapping

### 4.1 Server-Owned Connector Registry

Request headers, query parameters, and JSON payloads are untrusted client input. The gateway resolves tenant, project, and authorization properties strictly from a server-owned connector configuration:

```python
class GitHubConnectorConfig(StrictModel):
    """Server-side configuration binding a GitHub repository to a MAS tenant and project."""
    tenant_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=128)
    repository_id: str = Field(pattern=r"^\d+$")  # GitHub numeric repo ID
    repository_owner_id: str = Field(pattern=r"^\d+$")  # GitHub numeric owner ID
    approved_workflow_repo: str = Field(min_length=1, max_length=128)
    approved_workflow_path: str = Field(min_length=1, max_length=256)
    approved_workflow_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    permitted_events: list[str] = Field(default=["pull_request", "workflow_dispatch"])
    permitted_ref_patterns: dict[str, str] = Field(
        default_factory=lambda: {
            "pull_request": r"^refs/pull/\d+/merge$",
            "workflow_dispatch": r"^refs/heads/main$",
        }
    )
    required_runner_env: str = Field(default="github-hosted")
    status: Literal["ACTIVE", "REVOKED"] = "ACTIVE"
    generation: int = Field(default=1, ge=1)
```

**Synchronized Registry & Resolution Protocol**:
1. Server-owned `ConnectorRegistry` is synchronized with thread-safe `threading.RLock`, supporting `register`, `get`, `remove`, `snapshot`, and mapping access.
2. Gateway extracts `repository_id` and `repository_owner_id` from the verified OIDC token.
3. It queries the synchronized registry for a matching `(repository_id, repository_owner_id)` entry.
4. If no entry exists $\rightarrow$ 403 `REPOSITORY_NOT_ENROLLED`.
5. If `config.status != "ACTIVE"` $\rightarrow$ 403 `CONNECTOR_REVOKED`.
6. The validator takes an in-memory snapshot of the initial connector authority fields: `generation`, `tenant_id`, `project_id`, `approved_workflow_sha`, `approved_workflow_path`, `approved_workflow_repo`, and `required_runner_env`.
7. At validation completion (Step 10), the validator re-resolves the connector from the registry (not using the stale initial object):
   - If removed $\rightarrow$ 403 `CONNECTOR_REMOVED`.
   - If revoked $\rightarrow$ 403 `CONNECTOR_REVOKED`.
   - If `current_config.generation != snap_generation` $\rightarrow$ 403 `CONNECTOR_GENERATION_CHANGED`.
   - If any authority field mutated $\rightarrow$ 403 `CONNECTOR_AUTHORITY_CHANGED`.

### 4.2 Integration with Real `MultiTenantIAM` Verification APIs

The gateway integrates with actual, existing `MultiTenantIAM` APIs (`mas/iam.py`):
1. **Tenant Active Status**: Calls `iam.get_tenant(config.tenant_id)`.
   - If tenant is not found or `tenant.status != TenantStatus.ACTIVE` $\rightarrow$ 403 `TENANT_REVOKED`.
2. **Revocation Recheck at Validation Completion**: The gateway rechecks both `iam.get_tenant(config.tenant_id)` and `config.status` at validation completion to detect revocation occurring during slow JWKS or artifact processing.
3. **No Fictitious APIs**: The gateway does **not** call or invent non-existent APIs (e.g. project archival or connector revocation methods in `MultiTenantIAM`). Connector status is owned by the connector registry; tenant status is verified via `iam.get_tenant()`.
4. **Per-Request Ephemeral Witness Context**:
   - The gateway constructs an ephemeral, in-memory `TenantContext`:
     ```python
     TenantContext(
         tenant_id=config.tenant_id,
         principal_id=f"gha-witness:{config.repository_id}:{github_run_id}",
         roles={"witness"},
         scopes={"delivery:witness_observe"},
         token_id="",
         expires_at=token_exp,
     )
     ```
   - No persistent session, database user, or bearer token is minted or written to the IAM identity store. The context is strictly an internal restricted validation context, never granting access to privileged tenant storage or admin tools.

### 4.3 Exact Delivery Service Role & Action Alignment

Delivery action ownership is strictly aligned with the existing `DeliveryService` implementation (`mas/pm/delivery.py`):

| Principal / Role | Permitted Delivery Actions | Forbidden Actions | Service Alignment (`mas/pm/delivery.py`) |
|---|---|---|---|
| **`witness`** (GHA CI) | `delivery:witness_observe` | `delivery:submit`<br>`delivery:accept`<br>`delivery:reject`<br>`delivery:challenge`<br>`delivery:coordinate` | Read-only observation submission. Cannot call any state-changing method on `DeliveryService`. |
| **`builder`** (Developer / Supervised Agent) | `delivery:submit`<br>`delivery:submit` (for `challenge`)<br>`delivery:submit` (for `request_scope_change`) | `delivery:accept`<br>`delivery:reject`<br>`delivery:coordinate` | Calls `submit()`, calls `challenge()` to dispute reviewer findings, requests scope changes. |
| **`reviewer`** (Architect / Independent Verifier) | `delivery:agree`<br>`delivery:reject`<br>`delivery:accept`<br>`delivery:review` (for `resume_review`) | `delivery:submit`<br>`delivery:coordinate`<br>`delivery:resolve_challenge` | Calls `agree()`, `reject()`, and `accept()`. Reviewer cannot resolve disputes. |
| **`coordinator_admin`** | `delivery:enroll`<br>`delivery:establish`<br>`delivery:coordinate` (for `resolve_challenge`)<br>`delivery:reconcile_execution` | `delivery:witness_observe` | Manages project enrollment, task briefs, execution reconciliation, and resolves challenges via `resolve_challenge()`. |

*Note on Challenge Ownership*: In `DeliveryService`, `challenge()` is owned by `builder` with action `delivery:submit`, whereas `resolve_challenge()` is owned by `coordinator` with action `delivery:coordinate`. The gateway has no challenge or resolution authority.

**Strict Rejection of Client Spoofing**:
Request bodies use `StrictModel(extra="forbid")`. If a client passes `role`, `tenant_id`, `actor`, or any extraneous field in the request body, Pydantic validation fails immediately with 422/400 `EXTRA_FIELDS_FORBIDDEN`. The gateway **never** silently filters or ignores client-supplied privilege fields.

---

## 5. Strict Bounded Request/Response Schemas & Failure Invariants

### 5.1 Single Request Format: Bounded JSON Schema

The gateway accepts a single, unambiguous request format: `application/json`. Multipart parsing is excluded from this slice.

**Independent Resource Caps**:
- `MAX_REQUEST_BODY_SIZE`: `18 * 1024 * 1024` bytes (18 MiB total encoded request allowance).
- `MAX_BASE64_ARCHIVE_SIZE`: `16 * 1024 * 1024` bytes (16 MiB maximum base64-encoded string).
- `MAX_MANIFEST_JSON_SIZE`: `1 * 1024 * 1024` bytes (1 MiB maximum manifest JSON).
- `MAX_ARCHIVE_COMPRESSED_SIZE`: `12 * 1024 * 1024` bytes (12 MiB maximum decoded compressed archive bytes).

```python
class WitnessObservationSubmissionRequest(StrictModel):
    """Strict schema for GHA witness observation submission."""
    manifest: DeliveryManifest
    artifact_archive_base64: str | None = Field(
        default=None,
        max_length=16 * 1024 * 1024,  # Max 16 MiB base64 representation (~12 MiB binary)
        description="Optional base64-encoded ZIP artifact archive."
    )
    fencing_token: int = Field(ge=1, description="Active coordinator intent fencing token.")
    github_run_id: str = Field(min_length=1, max_length=64, pattern=r"^\d+$")
    github_run_attempt: int = Field(ge=1, le=100)
```

**Full Coordinate Binding & Artifact Rules**:
1. `manifest.tenant_id` must match `config.tenant_id`.
2. `manifest.project_id` must match `config.project_id`.
3. `manifest.fencing_token` must match `request.fencing_token`.
4. `request.github_run_id` must match token claim `run_id`.
5. `request.github_run_attempt` must match integer conversion of token claim `run_attempt`.
6. `manifest` must satisfy all `DeliveryManifest` structural constraints (non-blank IDs, unique `check_id`, bounded relative closure paths).
7. If any observation declares an `evidence_ref` or digest referencing artifact files, `artifact_archive_base64` is **strictly required**.
8. If `artifact_archive_base64` is provided:
   - Decode using strict base64 decoding (`validate=True`).
   - Decoded bytes must be $\le 12$ MiB (`MAX_ARCHIVE_COMPRESSED_SIZE`).
   - Must pass `validate_artifact_archive(decoded_bytes, observations=manifest.observations)` from `mas/pm/delivery_validator.py`.
   - Every observation reference and digest is verified against the archive.
9. If `artifact_archive_base64` is omitted and observations do not require artifacts, the response records `artifacts_validated: false` and `artifact_digest: None`.

### 5.2 Structured Validation Response

```python
class WitnessObservationValidationResponse(StrictModel):
    """Structured response returned upon successful witness observation validation."""
    status: Literal["VALIDATED_UNTRUSTED_OBSERVATION"] = "VALIDATED_UNTRUSTED_OBSERVATION"
    transport_authenticated: bool = True
    authority_verified: bool = False  # Untrusted observation; not trusted verifier/reviewer evidence
    artifacts_validated: bool = False  # True only if artifact archive was provided and fully matched
    tenant_id: str
    project_id: str
    issue_id: str
    manifest_digest: str  # SHA-256 hex digest of canonical manifest JSON
    artifact_digest: str | None  # SHA-256 hex digest of artifact zip if provided and validated
    observation_count: int
    github_run_id: str
    github_run_attempt: int
    timestamp: str
```

### 5.3 Error Redaction & Standard Envelopes

All gateway errors return standardized structured envelopes:

```json
{
  "status": "ERROR",
  "code": "WORKFLOW_SHA_UNAPPROVED",
  "message": "Workflow commit SHA does not match project configuration.",
  "timestamp": "2026-10-14T12:00:00Z",
  "request_id": "req-9a8b7c6d"
}
```

*Sanitization & Centralized Mapping Rule*:
- Public error messages are strictly defined in a centralized static dictionary (`PUBLIC_ERROR_MESSAGES`), mapping each error code to a constant, non-interpolated string.
- Raw dependency exception messages, user input dumps, stack traces, host paths, and sentinels are strictly kept in the private `diagnostic` attribute on the server and are **never** interpolated into public messages or serialized in `to_envelope()`.
- Private audit logs (`events.jsonl` or callback) sanitize bearer tokens, JWTs, and sensitive payload keys.

### 5.4 Precise Failure Invariants

1. **Zero Business State Mutation**: On any 4xx or 5xx response:
   - No database transaction is opened or committed.
   - `pm_delivery_tasks` phase, revision, and metadata remain strictly unchanged.
   - `pm_delivery_submissions` records zero rows.
   - Budget holds and coordinator reservations are untouched.
2. **Security & Audit Log Separation**:
   - The security audit logger (`events.jsonl` or append-only audit stream) operates outside business state transactions.
   - Failed authentication attempts, revoked connector access, and malformed payloads are written to the security audit log without violating the zero-business-mutation invariant.
3. **Response Loss vs. Zero Writes**:
   - In this offline validator slice, because no database writes occur on any request, zero business state writes is absolute.
   - In any future persistent system (GHA-04), a transaction committed before network response drop cannot promise zero writes on every 5xx; distinguishing business state from transport errors is critical.

---

## 6. Transactional State Boundaries & Deferred Protocols

### 6.1 What GHA-03 Owns (Offline Validator Engine)

1. **OIDC Token Validation Engine**: Strict RS256 JWT parsing, header validation, token length bounds, and positive lifetime / age / clock skew checks.
2. **Bounded JWKS Protocol**: 24h cache TTL, single-flight refresh, unknown-kid cool-down ($\ge 5$ min), zero redirects, 64 KiB buffer cap, RSA modulus validation ($\ge 2048$ bits), and fail-closed behavior on outage.
3. **Server-Owned Project Mapping**: Binding `(repository_id, repository_owner_id)` to `GitHubConnectorConfig` and checking active tenant status via `MultiTenantIAM.get_tenant()`.
4. **Ephemeral Witness Context**: Enforcing strict role separation (`witness` role restricted to `delivery:witness_observe`).
5. **Structural Validation**: Validating `DeliveryManifest` and artifact ZIP bytes against GHA-02 integrity checks, outputting `VALIDATED_UNTRUSTED_OBSERVATION` with `authority_verified: false`.

### 6.2 What GHA-04 Owns (Deferred: Durable Replay & Ingestion Ledger)

The following components are formally deferred to GHA-04:
1. **Durable Security Receipt & Token Store**:
   - Proposed additive table: `pm_security_tokens(token_jti TEXT PRIMARY KEY, tenant_id TEXT, issuer TEXT, subject TEXT, expires_at INTEGER, consumed_at INTEGER)`.
   - Atomic token consumption + receipt insertion protocol within SQLite transaction.
   - Concurrent replay winner semantics: first commit succeeds; concurrent second attempt rolls back with 401 `TOKEN_REPLAYED`.
   - Crash-after-commit / response loss handling: Retry with identical token returns 401 `TOKEN_REPLAYED`; retry with freshly minted token for the same logical source action is deduplicated via the `pm_source_events` ledger.
2. **Source Event Idempotency Ledger (`pm_source_events`)**:
   - Tracking `(action_id, payload_digest, pr_head_sha, base_sha, status)`.
   - Monotonic generation sequencing ensuring stale PR head candidates cannot be submitted or reviewed.
   - CAS transition protocol: `RECORDED -> IN_PROGRESS -> COMPLETED | UNCERTAIN`.

### 6.3 What GHA-05 Owns (Deferred: Trusted Check Publisher)

1. Pinned GitHub App credentials.
2. Checks API publisher emitting check conclusion `success` strictly on verified `ACCEPTED` states.
3. Never emitting `neutral` or `skipped` on required delivery checks.

---

## 7. Formal Pre-Implementation Acceptance Specification Matrix

The following 22 test scenarios specify the **formal pre-implementation test plan** for GHA-03. They define the exact inputs, injected faults, cryptographic conditions, and assertions that will be implemented in `tests/test_gha_gateway_integration.py` once this design checkpoint is approved. They are specification designs, not claimed as already executed runtime tests:

| Test ID | Scenario Description | Injected Condition / Payload | Expected HTTP Status | Expected Error Code / Assertion | Business State Mutation Check |
|---|---|---|---|---|---|
| **TC-01** | Wrong Token Issuer | `iss: "https://evil-issuer.com"` | 401 Unauthorized | `INVALID_ISSUER` | Zero DB mutation; task phase unchanged |
| **TC-02** | Wrong Token Audience | `aud: "wrong-audience"` | 401 Unauthorized | `INVALID_AUDIENCE` | Zero DB mutation; task phase unchanged |
| **TC-03** | Disallowed Algorithm (`none`, `HS256`, `ES256`) | Header `{"alg": "none"}` or `{"alg": "HS256"}` | 401 Unauthorized | `UNSUPPORTED_ALGORITHM` | Zero DB mutation; no JWKS lookup |
| **TC-04** | Malformed Header (Extra keys or missing `kid`) | Header `{"alg": "RS256", "jku": "https://..."}` | 401 Unauthorized | `INVALID_JWT_HEADER` | Zero DB mutation; extra header rejected |
| **TC-05** | Corrupted RSA Signature | Valid payload with altered bytes or wrong key | 401 Unauthorized | `INVALID_SIGNATURE` | Zero DB mutation; task phase unchanged |
| **TC-06** | Expired Token | `exp: now - 60s` | 401 Unauthorized | `TOKEN_EXPIRED` | Zero DB mutation; task phase unchanged |
| **TC-07** | Future Token (`nbf` in future) | `nbf: now + 120s` | 401 Unauthorized | `TOKEN_FUTURE` | Zero DB mutation; task phase unchanged |
| **TC-08** | Token Issued in Future (`iat`) | `iat: now + 120s` | 401 Unauthorized | `TOKEN_ISSUED_IN_FUTURE` | Zero DB mutation; task phase unchanged |
| **TC-09** | Negative or Excessive Lifetime | `exp <= iat` or `exp - iat = 3600s` (> 900s) | 401 Unauthorized | `INVALID_TOKEN_LIFETIME` | Zero DB mutation; task phase unchanged |
| **TC-10** | Token Age Exceeded | Issued 950s ago with lifetime 1000s (`exp = iat + 1000s = now + 50s`), unexpired but `now - iat = 950s > 900s` | 401 Unauthorized | `TOKEN_AGE_EXCEEDED` | Zero DB mutation; task phase unchanged |
| **TC-11** | JWKS Unknown `kid` Throttling | Rapid burst of tokens with random `kid` | 401 Unauthorized | `UNKNOWN_KEY_THROTTLED` | Outbound HTTP calls throttled to $\ge 5$ min |
| **TC-12** | JWKS Endpoint Outage / Refusal | Network timeout, 500, or 3xx redirect from JWKS | 503 Service Unavailable | `JWKS_UNAVAILABLE` | Fails closed; zero DB mutation |
| **TC-13** | Unenrolled Repository ID | `repository_id: "99999999"` | 403 Forbidden | `REPOSITORY_NOT_ENROLLED` | Zero DB mutation; task phase unchanged |
| **TC-14** | Mismatched Repository Owner ID | Valid repo ID, wrong `repository_owner_id` | 403 Forbidden | `OWNER_NOT_AUTHORIZED` | Zero DB mutation; task phase unchanged |
| **TC-15** | Mutable Workflow Ref Used | `job_workflow_ref: "...@refs/heads/main"` | 403 Forbidden | `WORKFLOW_NOT_PINNED` | Zero DB mutation; task phase unchanged |
| **TC-16** | Unapproved Workflow Path or Commit SHA | Mismatched workflow path or 40-hex SHA | 403 Forbidden | `WORKFLOW_UNAPPROVED` | Zero DB mutation; task phase unchanged |
| **TC-17** | Disallowed Event / Caller Ref / Environment | `event_name: "issue_comment"` or invalid ref | 403 Forbidden | `CONDITION_DISALLOWED` | Zero DB mutation; task phase unchanged |
| **TC-18** | Client Role / Tenant Extra Fields Rejected | Request body contains `{"role": "builder"}` | 422 Unprocessable / 400 | `EXTRA_FIELDS_FORBIDDEN` | StrictModel rejects extra fields; zero mutation |
| **TC-19** | Witness Principal Cannot Submit Delivery | Witness principal attempts `DeliveryService.submit()` | 403 Forbidden | `PERMISSION_DENIED` (`witness != builder`) | Task phase remains `AWAITING_SUBMISSION` |
| **TC-20** | Tenant Revoked / Suspended in `MultiTenantIAM` | Tenant marked `SUSPENDED` in `MultiTenantIAM` | 403 Forbidden | `TENANT_REVOKED` | Zero DB mutation; task phase unchanged |
| **TC-21** | Oversized Token or Request Body | Token $> 8$ KiB or Body $> 16$ MiB | 413 Payload Too Large | `PAYLOAD_TOO_LARGE` | Bounded read terminates immediately |
| **TC-22** | Valid Observation Submission Validated | Valid OIDC + approved workflow + valid ZIP | 200 OK | `VALIDATED_UNTRUSTED_OBSERVATION` | `transport_authenticated: true`, `authority_verified: false`, zero DB mutation |

---

## 8. Explicit Exclusions & Implementation Roadmap

### 8.1 Explicit Exclusions in GHA-03
1. **No Public Network Listener**: The gateway engine will be implemented and verified offline via local unit and integration tests using synthetic RSA keys and real token validation routines. No live public HTTPS port or router is opened.
2. **No Production GitHub Credentials**: No live GitHub App private keys, OIDC client secrets, or OAuth tokens are committed or placed in chat.
3. **No Live Workflow Enablement**: Files in `.github/workflows/` remain disabled.
4. **No Core Storage or Schema Changes**: `mas/pm/delivery.py` and the existing SQLite delivery schema remain strictly unmodified.
5. **No Production Project Enrollment**: No live production projects are enrolled in automated gates.

### 8.2 Incremental Implementation Roadmap
- **Step 1 (Current Checkpoint)**: Submit revised `GHA_03_GATEWAY_DESIGN_V1.md`, acceptance matrix, and delivery handoff for Codex independent review.
- **Step 2 (Local Engine Implementation)**: Implement `mas/pm/gateway/` (strict JWT parser, RSA signature validator, bounded JWKS cache with single-flight mutex and cool-down, connector resolver, and observation validator) with pure synthetic test fixtures in `tests/test_gha_gateway_integration.py`.
- **Step 3 (Offline Ingestion Integration)**: Integrate observation validation with existing `DeliveryManifest` and `delivery_validator.py`.
- **Step 4 (Codex Verification & Handoff)**: Run full quality gates and CC contract suites; submit candidate commit for independent review.
