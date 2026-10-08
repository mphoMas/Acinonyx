# Acinonyx / MAS-Core — Remediation Backlog & Action Plan

**Derived from:** [ARCHITECT_REVIEW.md](file:///home/acinonyx/Desktop/MAS/ARCHITECT_REVIEW.md)  
**Target:** Transition runtime from **REJECTED (REQUIRES RE-WORK)** to **APPROVED FOR ENTERPRISE DEPLOYMENT**  
**Branch:** `Acinonyx_frontier` (Baseline: `7e75b857`)

---

## Phase 0: Critical Security & Execution Containment (P0 Deployment Blockers)

These items represent immediate vulnerabilities preventing untrusted code execution and public exposure.

- [x] **SEC-01: Isolate Python Code Execution (`mas/tools/executor.py`)**
  - [x] Replace naive regex-based substring blocking with OS-level isolation (Linux namespaces/bubblewrap, Docker sidecar, or gVisor sandbox).
  - [x] Strip environment variables inherited by the subprocess (prevent `os.environ` secret leakage).
  - [x] Implement process group termination (`os.killpg`) to ensure child and grandchild processes are terminated on timeout.
  - [x] Apply CPU, memory, and file-descriptor limits (cgroups or `resource.setrlimit`).
  - [x] Add negative verification tests asserting that `import os`, `importlib.import_module()`, and `urllib` cannot execute or exfiltrate host data.

- [x] **SEC-02: Enforce Strict Filesystem Jailing (`mas/tools/filesystem.py`)**
  - [x] Remove `/tmp` from `ALLOWED_PROJECT_ROOTS` to prevent cross-tenant/host shared directory tampering.
  - [x] Replace `os.path.abspath` with `os.path.realpath` to resolve symlink directory escapes.
  - [x] Implement boundary enforcement on `fs_list_dir` and `fs_glob` to prevent arbitrary host directory listing (`/etc`, `/home`).
  - [x] Ensure path prefix verification strictly matches directories (e.g., using `Path.is_relative_to` rather than substring `startswith`).

- [x] **SEC-03: Eliminate Tool ACL Auto-Grant Bypass (`mas/mcp/protocol.py`)**
  - [x] Remove `self.tool_acl.default_allow.add(name)` from `MCPRegistry.register_tool`.
  - [x] Require explicit principal-to-tool permission grants or a strictly enumerated safe default allowlist.
  - [x] Add negative authorization tests asserting that unauthenticated MCP callers cannot invoke sensitive tools (`run_python`, `fs_write`, `git_init`).

- [x] **SEC-04: Secure Observability Dashboard Control Plane (`mas/dashboard/server.py`)**
  - [x] Change default server bind host from `0.0.0.0` to `127.0.0.1` (loopback only).
  - [x] Implement bearer token authentication middleware for state-mutating endpoints (`POST /api/dispatch` and `POST /api/engage`).
  - [x] Restrict or remove permissive wildcard CORS (`Access-Control-Allow-Origin: *`).
  - [x] Gate telemetry and artifact endpoints (`/api/events`, `/api/artifacts`, `/api/roster`) behind authentication.

---

## Phase 1: CI Baseline, Linting & Claim Alignment (P1 Immediate)

These items restore verifiable CI integrity and align runtime claims with ground truth.

- [x] **QA-01: Resolve Lint Failures & Unify CI Checks**
  - [x] Fix unused imports in [`mas/release_policy.py`](file:///home/acinonyx/Desktop/MAS/mas/release_policy.py#L13) (`os`).
  - [x] Fix module-level import ordering and unused imports in [`mas/validation.py`](file:///home/acinonyx/Desktop/MAS/mas/validation.py#L144-L149).
  - [x] Verify `ruff check mas tests` exits with 0 errors.
  - [x] Update [`.github/workflows/ci.yml`](file:///home/acinonyx/Desktop/MAS/.github/workflows/ci.yml) trigger to include `branches: [main, Acinonyx_frontier]` and feature PRs.
  - [x] Add `ruff check mas tests` into [`scripts/run_quality_gate.sh`](file:///home/acinonyx/Desktop/MAS/scripts/run_quality_gate.sh) and remove unconditional "10.0 / 10.0" exit banner.

- [ ] **CAP-01: Reconcile Capability Matrix with Reality**
  - [ ] Update [`mas/capabilities.py`](file:///home/acinonyx/Desktop/MAS/mas/capabilities.py) statuses:
    - Set `multi_tenant_iam` to `DEMO_ONLY` or `PLANNED` until wired to runtime.
    - Set `managed_vector_saas` to `DEMO_ONLY` (Mock adapters).
    - Set `enterprise_engagement` to `DEMO_ONLY`.
  - [ ] Align [`docs/CAPABILITIES.md`](file:///home/acinonyx/Desktop/MAS/docs/CAPABILITIES.md) and [`README.md`](file:///home/acinonyx/Desktop/MAS/README.md) with updated runtime counts.

---

## Phase 2: IAM & Swarm Hardening (P1 Platform)

- [ ] **IAM-01: Wire Multi-Tenant IAM into Core Runtime**
  - [ ] Remove hardcoded fallback secret `mas-enterprise-iam-secret-key-prod-001` in [`mas/iam.py`](file:///home/acinonyx/Desktop/MAS/mas/iam.py#L90); enforce environment-based key injection (`MAS_IAM_SECRET`).
  - [ ] Wire `MultiTenantIAM` into `MCPRegistry.handle_request` so caller tokens enforce principal RBAC and tenant workspace scoping.
  - [ ] Add integration tests exercising cross-tenant access rejection at MCP entry points.

- [ ] **SWARM-01: Secure Distributed Swarm Relay (`mas/core/swarm.py`)**
  - [ ] Remove static plaintext token `"acinonyx-swarm-secret-key"`; require dynamic configuration.
  - [ ] Implement constant-time token comparison (`hmac.compare_digest`) for handshake authentication.
  - [ ] Implement TLS/mTLS encryption for stream connections between worker nodes and hub.
  - [ ] Add tenant-aware topic filtering to prevent cross-tenant message broadcasting.

---

## Phase 3: Data Integrity, Concurrency & Persistence (P1 Data)

- [ ] **DATA-01: Harden SQLite Episodic Vector Memory (`mas/memory/episodic.py`)**
  - [ ] Implement threading lock (`threading.Lock` / `asyncio.Lock`) around database transactions to prevent `database is locked` operational errors.
  - [ ] Enable WAL journal mode (`PRAGMA journal_mode = WAL;`) and busy timeout on connection initialization.
  - [ ] Add `tenant_id TEXT NOT NULL` column to `reflections` and `trajectories` tables, with indexed queries scoped per tenant.
  - [ ] Implement record retention / cleanup TTL policies and GDPR/POPIA right-to-be-forgotten deletion hooks.
  - [ ] Benchmark and optimize linear $O(N)$ Python k-NN vector scan for large reflection stores.

- [ ] **DATA-02: Secure Communication Vault (`mas/memory/comms_vault.py`)**
  - [ ] Remove hardcoded developer home path `DEFAULT_BRAIN_DIR = Path("/home/acinonyx/...")`; rely on dynamic environment configuration.
  - [ ] Integrate PII redaction (`pii_anonymize_text_tool`) into the message ingestion pipeline before committing conversation text to disk.
  - [ ] Add tenant/session isolation and optional database encryption.

- [ ] **GCP-01: Clean Up Cloud Tool Binaries & Fallbacks**
  - [ ] Remove accidental directory `'gcloud auth application-default login'` from repository root.
  - [ ] Update `_find_bq_binary()` in [`mas/tools/bigquery_tool.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/bigquery_tool.py#L30) to reference canonical SDK paths only.
  - [ ] Make simulated/mock mode explicit and logged as a warning when live cloud credentials are unavailable.

---

## Phase 4: Orchestration, Lifecycle & Prompt Safety (P1 AI)

- [ ] **ORCH-01: Constrain Supervisor Concurrency & Fault Handling (`mas/orchestration/supervisor.py`)**
  - [ ] Add `asyncio.Semaphore(max_concurrency)` to prevent unconstrained task explosion in `execute_subtasks`.
  - [ ] In `FailurePolicy.FAIL_FAST` mode, explicitly cancel running sibling tasks when a failure occurs to avoid orphan side effects.
  - [ ] Add pre-execution cycle detection (topological sort) in `plan_subtasks` to fail fast on circular dependencies.
  - [ ] Implement idempotency keys for task retries to prevent duplicate file writes or billable API calls.

- [ ] **INJ-01: Mitigate Tool Observation Prompt Injection (`mas/core/agent.py`)**
  - [ ] Enclose tool observation outputs in structured XML-style delimiters (e.g. `<tool_output id="...">...</tool_output>`) with clear instructions that content is untrusted data.
  - [ ] Handle ReAct loop exhaustion explicitly (raise or signal turn limit) rather than returning silent partial thoughts after 5 steps.
  - [ ] Update `WorkingMemory` sliding window to track cumulative token budgets instead of static message counts.

---

## Phase 5: Deployment, Submodules & Governance (P2 Operational)

- [ ] **GIT-01: Resolve Broken Git Submodules**
  - [ ] Add `.gitmodules` containing valid remote repository URLs for `workspace/projects/bmm` and `workspace/projects/omniledger`, OR vendor them as regular directories if they are internal templates.
  - [ ] Validate that a fresh `git clone --recurse-submodules` checks out clean working trees for both projects.

- [ ] **DOCKER-01: Align Container Health Checks & Validate Startup**
  - [ ] Align health check endpoint between `Dockerfile` (`/api/status`) and `docker-compose.yml` (`/`).
  - [ ] Add an automated container startup smoke test to CI verifying non-root execution (`mas:10001`) and healthy readiness probe.

- [ ] **GOV-01: Clarify Regulatory Governance Scope**
  - [ ] Update documentation for [`mas/tools/pii_tool.py`](file:///home/acinonyx/Desktop/MAS/mas/tools/pii_tool.py) to explicitly distinguish algorithmic regex redaction from full POPIA/GDPR legal compliance.
