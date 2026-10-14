# Antigravity GHA-03 Rework 2: Mechanism and Closure Checkpoint

Document ID: `antigravity-gha-03-rework-2-checkpoint`  
Date: 14 October 2026  
Status: Proposed Mechanism Checkpoint (Submitted for recurrence rule alignment before code patching)  
Implementation Owner: Antigravity Development Team  
Architecture Reviewer: Codex  
Reference Review: `f01839ff` (`GHA_03_REWORK_REVIEW.md` and `ANTIGRAVITY_GHA_03_REWORK_2_BRIEF.md`)  

---

## 1. Problem Statement & Recurrence Root Cause Analysis

Codex's review of candidate `be9c59df` confirmed that the three original defect probes (revoked generation-2 replacement, 2 MiB manifest size, and public sentinel leakage) are safely refused. However, two related-path vulnerabilities were identified:

1. **B1 (Policy Freshness Incompleteness)**: The completion-stage comparison in `GatewayObservationValidator` checked `tenant_id`, `project_id`, `approved_workflow_sha`, `approved_workflow_path`, `approved_workflow_repo`, and `required_runner_env`, but omitted `permitted_events` and `permitted_ref_patterns`. When a connector was replaced at `artifact_validation` with `permitted_events=[]` and `permitted_ref_patterns={}` with the same generation, validation returned success. Furthermore, `ConnectorRegistry` allowed direct dict item assignment without monotonic generation enforcement, and nested collections in `GitHubConnectorConfig` remained mutable.
2. **B2 (Sensitive Payload Leakage in Diagnostics)**: When invalid input (e.g. `github_run_attempt='RAW_PAYLOAD_SECRET_SENTINEL'`) was supplied, `validator.py` assigned `diagnostic=str(exc)`. Pydantic's `str(ValidationError)` embeds the raw input value (`input_value='RAW_PAYLOAD_SECRET_SENTINEL'`). The audit logger passed this diagnostic to the audit callback, leaking arbitrary payload secrets into audit streams.

---

## 2. Technical Mechanisms for Complete Closure

### 2.1 Mechanism 1: Complete Connector Policy Identity & Monotonic Registry Updates

#### Complete Authorization Policy Identity
The complete connector authorization identity is defined across all 12 policy-governing attributes:
- `repository_id: str`
- `repository_owner_id: str`
- `tenant_id: str`
- `project_id: str`
- `approved_workflow_repo: str`
- `approved_workflow_path: str`
- `approved_workflow_sha: str`
- `permitted_events: tuple[str, ...]` (canonical sorted tuple)
- `permitted_ref_patterns: tuple[tuple[str, str], ...]` (canonical sorted pairs)
- `required_runner_env: str`
- `status: Literal["ACTIVE", "REVOKED"]`
- `generation: int` ($\ge 1$, strictly monotonic)

#### Immutable Policy Snapshot & Canonical Digest
We introduce a deeply detached, immutable `ConnectorPolicySnapshot` dataclass:
```python
@dataclass(frozen=True)
class ConnectorPolicySnapshot:
    repository_id: str
    repository_owner_id: str
    tenant_id: str
    project_id: str
    approved_workflow_repo: str
    approved_workflow_path: str
    approved_workflow_sha: str
    permitted_events: tuple[str, ...]
    permitted_ref_patterns: tuple[tuple[str, str], ...]
    required_runner_env: str
    status: str
    generation: int
    canonical_digest: str  # SHA-256 hex digest of sorted canonical JSON
```
The canonical digest covers all 12 attributes including `permitted_events` and `permitted_ref_patterns`. Any mutation to event or ref rules changes `canonical_digest`.

#### Sole Supported Update API in `ConnectorRegistry`
`ConnectorRegistry` is the sole supported update interface:
1. **Thread-Safe Monotonicity**: Updates must call `registry.update(config)`.
   - If an existing entry exists, `config.generation` must be strictly greater than `current.generation` (`config.generation > current.generation`).
   - If `config.generation <= current.generation`, `update()` raises `ValueError("Monotonically advancing generation required for connector policy updates")`.
2. **Deeply Detached Storage**: Entries are converted into `ConnectorPolicySnapshot` instances upon ingestion. Direct mutation of the caller's lists or dictionaries has zero effect on the registry.
3. **Registry Mutations**:
   - `register(config)`: registers initial entry (`generation >= 1`).
   - `update(config)`: validates monotonic generation advancement and updates snapshot.
   - `remove(key)`: thread-safely removes entry.
   - `get_snapshot(key)`: returns the immutable `ConnectorPolicySnapshot`.
   - Direct subscript assignment `__setitem__` routes through `update()` or `register()`.

#### Completion Re-Resolution in Validator
At Step 4 (Resolution):
The validator fetches `initial_snapshot = registry.get_snapshot(repo_coord)`.
At Step 10 (Completion Recheck):
The validator re-resolves `current_snapshot = registry.get_snapshot(repo_coord)`.
- If `current_snapshot is None` $\rightarrow$ 403 `CONNECTOR_REMOVED`.
- If `current_snapshot.status != "ACTIVE"` $\rightarrow$ 403 `CONNECTOR_REVOKED`.
- If `current_snapshot.generation != initial_snapshot.generation` $\rightarrow$ 403 `CONNECTOR_GENERATION_CHANGED`.
- If `current_snapshot.canonical_digest != initial_snapshot.canonical_digest` $\rightarrow$ 403 `CONNECTOR_AUTHORITY_CHANGED`.

This guarantees that changing `permitted_events`, `permitted_ref_patterns`, or any other authority field without advancing generation, or mutating nested collections in-place, fails deterministically with 403 `CONNECTOR_AUTHORITY_CHANGED`.

---

### 2.2 Mechanism 2: Safe Diagnostic Schemas & Input-Free Diagnostics

#### Safe Validation Error Formatting
To completely prevent raw request inputs from leaking into diagnostics and audit logs:
1. **Zero Raw Value Extraction**: We never call `str(ValidationError)`.
2. **Location & Error Type Only**: We extract only field locations and Pydantic error types:
   ```python
   def sanitize_validation_error(exc: ValidationError) -> str:
       items = []
       for err in exc.errors()[:8]:
           loc = ".".join(str(p) for p in err.get("loc", ()) if str(p).isidentifier() or str(p).isdigit())[:64]
           err_type = str(err.get("type", "invalid"))[:32]
           items.append(f"field={loc or 'root'}, error={err_type}")
       return "; ".join(items) or "validation_error"
   ```
   No `input_value`, `input`, or `msg` containing user strings is ever extracted.
3. **Sanitized Dependency & Generic Exceptions**:
   Generic exceptions are summarized by exception class name and static safe category:
   `f"{exc.__class__.__name__}: internal_failure"` or `f"{exc.__class__.__name__}: validation_failed"`.
   No exception message text is echoed into diagnostics or logs.
4. **Audit Callback Exception Protection**:
   In `_log_audit`, if the configured `audit_logger` callback raises an exception, the logging handler logs only `exc.__class__.__name__`, preventing unsafe audit-callback exception messages from leaking secrets into standard error.
5. **Preservation of Public Error Contracts**:
   Public envelopes (`to_envelope()`) and `GatewayError.message` remain strictly mapped to static, non-interpolated strings from `PUBLIC_ERROR_MESSAGES`.

---

## 3. Findings Closure Matrix

| Review Finding | Root Cause in `be9c59df` | Reassessed Mechanism in Rework 2 | Regression Verification Test |
|---|---|---|---|
| **B1: Authority comparison omits event/ref policies** | Step 10 compared handwritten scalar fields and omitted event/ref policies. Generation advancement was not enforced in `ConnectorRegistry`, and nested containers were mutable. | Defined `ConnectorPolicySnapshot` covering all 12 policy attributes in `canonical_digest`. `ConnectorRegistry` enforces strictly monotonic generation advancement (`new.generation > current.generation`) on `update()`. Re-resolution at Step 10 compares `current_snapshot.canonical_digest != initial_snapshot.canonical_digest`. | 1. Replace connector during `artifact_validation` with `permitted_events=[]` preserving generation $\rightarrow$ rejects with 403 `CONNECTOR_AUTHORITY_CHANGED`.<br>2. Mutate nested dict/list in-place $\rightarrow$ snapshot unaffected, passes if valid.<br>3. Attempt `registry.update()` with same or lower generation $\rightarrow$ raises `ValueError`. |
| **B2: Sensitive request values copied into audit diagnostics** | `str(ValidationError)` and `str(exc)` were assigned to `diagnostic`, exposing raw inputs like `RAW_PAYLOAD_SECRET_SENTINEL`. | `sanitize_validation_error` extracts strictly field locations and error types without inputs. Dependency exceptions map to class and static category. Audit callback errors echo only exception class. | 1. Supply `github_run_attempt='RAW_PAYLOAD_SECRET_SENTINEL'` $\rightarrow$ verify diagnostic and audit logs contain NO sentinel.<br>2. Supply nested sensitive strings in manifest fields $\rightarrow$ verify diagnostic contains NO sentinel.<br>3. Test audit callback failure $\rightarrow$ verify logger echoes only class name. |

---

## 4. Implementation Plan & Gate Order

1. Update `mas/pm/gateway/models.py`:
   - Implement `ConnectorPolicySnapshot` and `canonical_policy_digest`.
   - Update `ConnectorRegistry` with monotonic generation enforcement and immutable snapshot storage.
   - Implement `sanitize_validation_error` and `sanitize_exception`.
2. Update `mas/pm/gateway/validator.py`:
   - Use `ConnectorPolicySnapshot` for initial and completion checks.
   - Replace all `str(ValidationError)` and `str(exc)` diagnostic assignments with safe sanitized metadata.
   - Sanitize audit callback exception logging.
3. Update `tests/test_gha_gateway_integration.py`:
   - Add tests for same-generation event/ref mutation refusal.
   - Add tests for monotonic generation enforcement on `ConnectorRegistry.update()`.
   - Add tests verifying zero sentinel presence in audit logs when `github_run_attempt='RAW_PAYLOAD_SECRET_SENTINEL'` or nested sensitive inputs are supplied.
   - Add test for safe audit-callback exception handling.
4. Execute full verification:
   - Targeted gateway integration tests.
   - Combined delivery suites.
   - CC regression suite.
   - Full 5-stage repository quality gate (`scripts/run_quality_gate.sh`).
   - Clean isolated-wheel verification in `/tmp` outside checkout.
