# Independent Reviewer & Chief Architect — Comprehensive Assessment Report

**Owner:** Codex, acting as Independent Reviewer & Chief Architect for Platform, AI & Data  
**Scope:** `mphoMas/Acinonyx`, branch `Acinonyx_frontier`  
**Baseline Inspected:** Git commit `7e75b857703b3744da456eced493f83d87d10559`  
**Date of Audit:** October 8, 2026  
**Final Verdict:** **REJECTED (REQUIRES RE-WORK)** for enterprise production and untrusted execution environments.

---

## Executive Summary & Architectural Verdict

Following an exhaustive source code audit, empirical test execution, and security boundary evaluation of `mphoMas/Acinonyx` at commit `7e75b857`, the multi-agent operating runtime (**Acinonyx / MAS-Core**) demonstrates impressive conceptual architecture, thoughtful agentic patterns (CoALA lifecycle, ReAct loops, supervisor DAGs, and judicial release policies), and comprehensive local unit/integration test coverage (219 passing tests).

However, for **enterprise multi-tenant production** and **untrusted code/prompt execution**, the runtime cannot be approved. It presents critical security vulnerabilities, architectural decouplings, unisolated tool execution boundaries, unauthenticated public API control surfaces, and unsupported marketing claims.

### Summary Verdict: REJECTED (REQUIRES RE-WORK)
The primary deployment blockers are:
1. **Critical Execution Boundary Vulnerability (P0):** The Python code executor relies solely on regular-expression substring blocking with zero OS containment, allowing trivial sandbox escapes, arbitrary file access across the host, and full environment variable credential leakage.
2. **MCP Tool ACL Auto-Grant Vulnerability (P0):** Every registered tool automatically adds itself to `tool_acl.default_allow`, effectively rendering the tool ACL a no-op for unauthenticated or default callers.
3. **Unauthenticated Public HTTP Control Plane (P0):** The observability dashboard binds to `0.0.0.0:8080` with permissive CORS (`*`), exposing unauthenticated endpoints that leak internal event streams and allow any remote actor to toggle the live dispatch switch from `STAGED` to `ARMED`.
4. **Decoupled Security & Storage Stubs (P1):** Multi-tenant IAM and vector SaaS adapters are completely unwired in the production runtime; Vertex AI, Pinecone, and Qdrant adapters are thin mocks delegating to in-memory Python dictionaries.
5. **Divergent Capability Claims & Quality Gate Illusion (P1):** Runtime capability reporting claims 100% implementation (29/29) while documentation notes features as planned or demo-only; the quality gate script unconditionally prints a "10.0 / 10.0" certification while CI linting (`ruff check`) currently fails with 6 unresolved errors.
6. **Submodule Disconnection & Broken Gitlinks (P2):** Git submodule tree entries for `bmm` and `omniledger` exist at mode 160000 without `.gitmodules` metadata or remote URLs, preventing reproducible fresh clones.

---

## 1. Reproducible Validation Baseline & Quality Gate Audit

### 1.1 Test Execution & Toolchain Baseline
* **Python Environment:** Python 3.14.6 (`pytest-9.0.3`, `pluggy-1.6.0`, `anyio-4.12.1`).
* **Package Specifications:** Defined in `pyproject.toml` (`requires-python = ">=3.11"`).
* **Test Suite Counts:**
  * **219 tests collected** across 35 test modules.
  * **219 passed in 26.75s to 53.09s** (0 failures, 0 errors, 0 skips when Playwright/Chromium and Xvfb dependencies are available).
* **Headless Browser Integration:** Headless Chromium executed via `playwright==1.49.1` utilizing bundled binary located in `bin/browsers/chromium_headless_shell-1243/...`.

### 1.2 Quality Gate vs. CI Pipeline Discrepancy
Comparing `scripts/run_quality_gate.sh` against `.github/workflows/ci.yml` reveals critical gaps:

| Pipeline Step | CI Workflow (`.github/workflows/ci.yml`) | Quality Gate Script (`scripts/run_quality_gate.sh`) | Empirical Result on `Acinonyx_frontier` |
|---|---|---|---|
| **Branch Target** | `push: [main]`, `pull_request` | Manual execution | Bypassed on push to `Acinonyx_frontier` |
| **Linting (`ruff`)** | `ruff check mas tests` | **Omitted completely** | **FAILED: 6 lint errors** |
| **Unit/Integration** | `pytest --cov=mas ...` | `pytest tests/ -v` | PASSED (219/219) |
| **Docker Build** | `docker build -t mas-core:ci .` | **Omitted completely** | Untested in gate |
| **Non-root Container** | `test $(docker run ... -u) != "0"` | **Omitted completely** | Untested in gate |
| **Swarm Verification** | Omitted | `python3 scripts/verify_research_swarm.py` | PASSED (Merkle hash: `626f08...`) |
| **Portal Compilation** | Omitted | `python3 scripts/compile_portal_catalog.py` | PASSED |
| **Final Exit Declaration** | Standard CI exit code | Unconditional `"CERTIFIED 10.0 / 10.0"` | Misleading success declaration |

### 1.3 Identified Lint Failures
Running `ruff check mas tests` yields 6 failures:
1. `mas/release_policy.py:13:8`: `F401` `os` imported but unused.
2. `mas/validation.py:144:1`: `E402` Module level import not at top of file.
3. `mas/validation.py:145:5`: `F401` `PolicySpec` imported but unused.
4. `mas/validation.py:146:5`: `F401` `PolicyEvaluationResult` imported but unused.
5. `mas/validation.py:147:5`: `F401` `compute_candidate_hash` imported but unused.
6. `mas/validation.py:148:5`: `F401` `evaluate_release_policy` imported but unused.

---

## 2. Capability Claims Reconciliation vs. Concrete Implementation

A direct reconciliation between documentation (`docs/CAPABILITIES.md`, `README.md`), runtime matrix (`mas/capabilities.py`), and source code indicates major discrepancies:

| Capability Name | Status in `docs/CAPABILITIES.md` | Status in `mas/capabilities.py` | Inspected Implementation Status | Evidence / Analysis |
|---|---|---|---|---|
| `multi_tenant_iam` | **planned** ("Not shipped") | **implemented** | **Stub / Unwired Mock** | Implemented as in-memory class in `mas/iam.py`, but completely unreferenced across `mas/core/`, `mas/mcp/`, and `mas/dashboard/`. No OAuth/OIDC client. |
| `managed_vector_saas` | **planned** ("Not shipped") | **implemented** | **Mock Delegation Only** | `VertexAIVectorSearchAdapter`, `PineconeAdapter`, and `QdrantAdapter` in `mas/memory/vector_saas.py` delegate all calls to `MockManagedVectorStore`. Zero cloud network calls. |
| `enterprise_engagement` | **demo-only** ("Scripted pipeline") | **implemented** | **Scripted Templates** | `mas/organization/engagement.py` runs deterministic text pipelines without live external integrations unless provider is explicitly attached. |
| `demo_echo_agents` | **demo-only** | **implemented** | **Demo-only** | Echo fallbacks in `main.py`. |
| Quality Score Wording | N/A | Hardcoded 29 implemented | **Unconditional "10.0/10.0"** | `scripts/run_quality_gate.sh` asserts full compliance regardless of real lint or boundary health. |

### Proposed Correction
`mas/capabilities.py` must reflect ground truth:
* `multi_tenant_iam`: Reclassify to `CapabilityStatus.DEMO_ONLY` or `PLANNED` until wired to MCP/Dashboard.
* `managed_vector_saas`: Reclassify to `CapabilityStatus.DEMO_ONLY` (Mock adapters).
* `enterprise_engagement`: Reclassify to `CapabilityStatus.DEMO_ONLY`.

---

## 3. Execution & Tool Security Boundaries Audit

### 3.1 Python Executor Sandbox Escape (Vulnerability P0-A)
* **Location:** [`mas/tools/executor.py#L16-L36`](file:///home/acinonyx/Desktop/MAS/mas/tools/executor.py#L16-L36)
* **Mechanics:** `run_python_code` checks code using regex pattern matching:
  ```python
  FORBIDDEN_IMPORT_PATTERNS = [
      r"\bimport\s+subprocess\b",
      r"\bfrom\s+subprocess\s+import\b",
      r"\bimport\s+socket\b",
      r"\bfrom\s+socket\s+import\b",
      r"\bimport\s+ctypes\b",
      r"\bfrom\s+ctypes\s+import\b",
      r"\b__import__\s*\(",
      r"\beval\s*\(",
      r"\bexec\s*\(",
  ]
  ```
* **Vulnerabilities Demonstrated:**
  1. **Direct Unchecked Standard Modules:** `import os; print(os.name)` executes without restriction.
  2. **Dynamic Subprocess Bypass:** `import importlib; importlib.import_module("subprocess")` completely bypasses the regex check.
  3. **Full Environment Secret Leakage:** The child process inherits `os.environ` completely, exposing API keys and tokens.
  4. **Arbitrary Filesystem Read:** `open('/etc/os-release').read()` reads host filesystem outside any workspace.
  5. **Network Sockets via Unblocked Libraries:** `import urllib.request` allows arbitrary outbound network exfiltration.
  6. **Process Group Orphanage:** `proc.kill()` on timeout only kills the direct child PID, leaving spawned grandchild processes running.

### 3.2 Filesystem Jail Path Enforcement Inadequacy (Vulnerability P0-B)
* **Location:** [`mas/tools/filesystem.py#L15-L32`](file:///home/acinonyx/Desktop/MAS/mas/tools/filesystem.py#L15-L32)
* **Mechanics:**
  ```python
  ALLOWED_PROJECT_ROOTS = [str(REPO_ROOT), "/srv/mas-projects", "/tmp"]
  def _is_path_safe(path: str) -> bool:
      abs_path = os.path.abspath(path)
      return any(abs_path.startswith(root) for root in ALLOWED_PROJECT_ROOTS)
  ```
* **Flaws:**
  1. **Global `/tmp` Inclusion:** Any agent or tenant can read and overwrite shared files in `/tmp`.
  2. **Missing Realpath Symlink Resolution:** `os.path.abspath` does not resolve symlinks; symlinks pointing from `/tmp` into sensitive directories bypass the check.
  3. **Missing Traversal Check on Listing & Glob:** `fs_list_dir` ([line 61](file:///home/acinonyx/Desktop/MAS/mas/tools/filesystem.py#L61)) and `fs_glob` ([line 78](file:///home/acinonyx/Desktop/MAS/mas/tools/filesystem.py#L78)) do **not** call `_is_path_safe`! An agent can list `/etc`, `/var`, or `/home`.

### 3.3 Automatic ACL Bypass upon Registration (Vulnerability P0-C)
* **Location:** [`mas/mcp/protocol.py#L146`](file:///home/acinonyx/Desktop/MAS/mas/mcp/protocol.py#L146)
* **Mechanics:**
  ```python
  def register_tool(self, name: str, ...):
      ...
      self.tool_acl.default_allow.add(name)
  ```
* **Flaw:** Every registered tool automatically adds itself to `tool_acl.default_allow`. In `handle_request` ([line 249](file:///home/acinonyx/Desktop/MAS/mas/mcp/protocol.py#L249)), unauthenticated callers or callers not registered in `principals` are granted access to all default allowed tools.

---

## 4. IAM, Tenant Isolation, and Exposed Interfaces Audit

### 4.1 Dashboard Observability Server Exposed Control Plane (Vulnerability P0-D)
* **Location:** [`mas/dashboard/server.py#L159-L225`](file:///home/acinonyx/Desktop/MAS/mas/dashboard/server.py#L159-L225)
* **Flaws:**
  1. **Wildcard Host Binding:** Binds to `0.0.0.0:8080` by default.
  2. **Unauthenticated Public Endpoints:**
     * `POST /api/engage`: Triggers full agent consulting workflow and dynamic recruitment.
     * `POST /api/dispatch`: **Allows any unauthenticated HTTP caller to flip `live_dispatch_enabled` between STAGED and ARMED.**
     * `GET /api/events` & `GET /api/artifacts`: Dumps all internal agent conversations, client PRDs, and architecture specs to unauthenticated callers.
     * `Access-Control-Allow-Origin: *`: Enables malicious third-party websites to make cross-origin requests to local dashboard instances.

### 4.2 Multi-Tenant IAM Disconnection & Hardcoded Signing Key (Vulnerability P1-A)
* **Location:** [`mas/iam.py#L90-L93`](file:///home/acinonyx/Desktop/MAS/mas/iam.py#L90-L93)
* **Flaws:**
  1. **Hardcoded Secret:** `DEFAULT_SECRET = "mas-enterprise-iam-secret-key-prod-001"`.
  2. **Zero Runtime Integration:** `MultiTenantIAM` is never invoked in `MCPRegistry.handle_request`, `DashboardRequestHandler`, or `SwarmHub`.
  3. **No OAuth/OIDC Provider:** Advertised as "OAuth/PAB", but actually implemented as a custom HMAC token format (`payload_b64.hmac_sha256`).

### 4.3 Swarm TCP Relay Hardcoded Secret & Raw Transport (Vulnerability P1-B)
* **Location:** [`mas/core/swarm.py#L36-L98`](file:///home/acinonyx/Desktop/MAS/mas/core/swarm.py#L36-L98)
* **Flaws:**
  1. Default token is static: `auth_token = "acinonyx-swarm-secret-key"`.
  2. Raw plaintext TCP socket without TLS/mTLS encryption.
  3. Plain string equality `auth_req.get("auth_token") != self.auth_token` subject to timing side-channels.
  4. Global broadcast topic subscription (`["*"]`) without tenant isolation.

---

## 5. Data Contracts and Persistence Audit

### 5.1 SQLite Episodic Vector Store Threading & Scaling (Finding P1-C)
* **Location:** [`mas/memory/episodic.py#L142-L165`](file:///home/acinonyx/Desktop/MAS/mas/memory/episodic.py#L142-L165)
* **Analysis:**
  1. `sqlite3.connect(..., check_same_thread=False)` is used across concurrent agent calls without a threading lock. SQLite write operations will raise `sqlite3.OperationalError: database is locked`.
  2. WAL mode is omitted (`PRAGMA journal_mode = WAL;` is present in `comms_vault.py`, but missing in `episodic.py`).
  3. No `tenant_id` column in `reflections` or `trajectories` tables, allowing cross-tenant memory leakage.
  4. Vector k-NN search (`cosine_sim`) is an in-process Python callback executing a linear `O(N)` scan across all database rows, unpacking binary floats on the GIL.

### 5.2 BigQuery & Cloud Storage Fallbacks
* **Location:** [`mas/tools/bigquery_tool.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/bigquery_tool.py) & [`mas/tools/storage_tool.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/storage_tool.py)
* **Analysis:**
  1. `_find_bq_binary()` hardcodes an accidental directory path:
     `{REPO_ROOT}/gcloud auth application-default login/google-cloud-sdk/bin/bq`.
  2. If GCP CLI tools are missing, tools return synthetic mock payloads (`mode: "simulated"`), masking failures during testing.

---

## 6. Orchestration and Agent Termination Audit

### 6.1 Unbounded Concurrency & Fault Isolation in Supervisor (Finding P1-D)
* **Location:** [`mas/orchestration/supervisor.py#L105-L175`](file:///home/acinonyx/Desktop/MAS/mas/orchestration/supervisor.py#L105-L175)
* **Analysis:**
  1. `await asyncio.gather(*[_run_single(t) for t in ready_tasks])` runs all ready tasks concurrently with no semaphore limit.
  2. When `failure_policy == FailurePolicy.FAIL_FAST`, a single failure raises `RuntimeError`, but sibling concurrent tasks are **not cancelled** and continue executing unmonitored side effects.
  3. Unconditional retry loops duplicate non-idempotent tool calls (e.g. file writes or external API mutations).

### 6.2 Prompt & Tool Output Injection Boundaries (Finding P1-E)
* **Location:** [`mas/core/agent.py#L271-L279`](file:///home/acinonyx/Desktop/MAS/mas/core/agent.py#L271-L279)
* **Analysis:**
  Raw tool output is concatenated directly into memory:
  `content=f"Observation from tool [{tc.name}] id={evidence_id}:\n{tool_result}"`
  Untrusted webpage content or file data returned by tools can inject formatting commands and hijack subsequent model reasoning steps.

---

## 7. AI Quality and Release Evidence Audit

### 7.1 Release Policy Judicial Audit
* **Location:** [`mas/release_policy.py`](file:///home/acinonyx/Desktop/MAS/mas/release_policy.py)
* **Strengths:** High rigor in cryptographic candidate binding (`compute_candidate_hash`), verification completeness checks, and advisory thresholds.
* **Limitations:** Unused imports and module-level import ordering break `ruff` compliance.

### 7.2 PII Anonymization vs. Regulatory Reality
* **Location:** [`mas/tools/pii_tool.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/pii_tool.py)
* **Analysis:** Regex-based replacement of 13-digit SA IDs and credit cards is an algorithmic sanitization tool, not a full compliance framework for POPIA or GDPR. Marketing claims should clearly state this distinction.

---

## 8. Deployment and Operational Readiness Audit

### 8.1 Docker & Deployment Configuration
* **Dockerfile:** Builds unprivileged user `mas` (UID 10001) and sets up Playwright browsers.
* **Missing Submodule Metadata (Finding P2-A):**
  * `workspace/projects/bmm` (commit `a9437a80...`) and `workspace/projects/omniledger` (commit `fbc6c066...`) are committed as Git mode 160000 gitlinks.
  * No `.gitmodules` file exists in the repository root.
  * Fresh clones cannot fetch or resolve these nested projects.

---

## 9. Prioritized Remediation Plan & Acceptance Criteria

| Priority | Issue ID | Component | Defect Description | Required Remediation |
|---|---|---|---|---|
| **P0** | SEC-01 | `mas/tools/executor.py` | Subprocess regex sandbox bypass | Migrate execution to OS isolation (Docker container, gVisor, or Linux bubblewrap/cgroups). Restrict environment inheritance. |
| **P0** | SEC-02 | `mas/tools/filesystem.py` | Missing path jail on `fs_list_dir`/`fs_glob`; `/tmp` in roots | Enforce `_is_path_safe` on all operations using `os.path.realpath`. Remove `/tmp` from global default roots. |
| **P0** | SEC-03 | `mas/mcp/protocol.py` | Auto-allow in `register_tool` | Remove `default_allow.add(name)` from `register_tool`. Require explicit principal grants. |
| **P0** | SEC-04 | `mas/dashboard/server.py` | Unauthenticated public endpoints & dispatch flip | Bind to `127.0.0.1` by default. Add bearer token auth to all mutating routes (`/api/dispatch`, `/api/engage`). Remove permissive CORS. |
| **P1** | IAM-01 | `mas/iam.py` | Hardcoded secret & lack of runtime wiring | Load secrets from environment; integrate `MultiTenantIAM` into MCP request dispatch and Dashboard auth middleware. |
| **P1** | ORCH-01 | `mas/orchestration/supervisor.py` | Unbounded task concurrency & missing sibling cancellation | Introduce `asyncio.Semaphore` and cancel sibling tasks on `FAIL_FAST`. |
| **P1** | DATA-01 | `mas/memory/episodic.py` | Threading locks, missing WAL mode, linear k-NN | Add threading lock, enable WAL mode, add `tenant_id` column, and evaluate vector index library (e.g. SQLite VSS or external vector store). |
| **P1** | QA-01 | `.github/workflows/ci.yml` & `mas/` | 6 `ruff` lint errors failing CI | Fix unused imports in `mas/release_policy.py` and `mas/validation.py`. Update CI to run on all feature branches. |
| **P2** | OPS-01 | Root repository | Missing `.gitmodules` for `bmm` and `omniledger` | Add proper `.gitmodules` configuration or vendor project directories. |
| **P2** | DOC-01 | `docs/CAPABILITIES.md` | Inconsistent capability statuses | Reconcile capability matrix to distinguish implemented features from mocks and planned modules. |

---

## Conclusion

The architecture of **Acinonyx / MAS-Core** exhibits strong structural design and a comprehensive testing discipline, but requires remediation across execution containment, interface authentication, and tenant isolation before it can be certified for enterprise production.

**Architectural Recommendation:** Implement P0 security boundaries and P1 runtime wiring before re-submitting for independent verification.
