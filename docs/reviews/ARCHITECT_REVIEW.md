# Independent Architecture Review — Acinonyx Frontier

> Historical assessment. See [current revision verification](REVISION_VERIFICATION_2026_10_08.md) for the latest remediation and executed evidence.

Reviewed commit: `7e75b857703b3744da456eced493f83d87d10559` (`Acinonyx_frontier`).
Reviewer: Codex, Independent Reviewer & Chief Architect (Platform, AI & Data).
Scope: initial source and local execution audit of the runtime, security boundaries, data integrity, AI evidence, packaging, and deployment claims. This is not an exhaustive penetration test or certification.

## 1. Verdict & Executive Summary

**Status: REJECTED (REQUIRES RE-WORK) for enterprise production deployment, multi-tenant operation, and execution of untrusted agent-generated code.**

The repository contains substantial working local orchestration code and tests, but its security and verification claims exceed its demonstrated guarantees. Fixture-based checks reproduce authorization bypasses, filesystem escapes, unrestricted host execution, fabricated verification results, and state/data integrity defects. It remains a development prototype suitable for controlled offline experimentation with trusted inputs; passing tests do not establish production readiness.

### Validation evidence

Python 3.12.14; pytest 9.1.1; Ruff 0.16.10; PyYAML 6.0.3 added only to the review environment. The original package dependencies were not edited.

| Check | Actual outcome |
|---|---|
| Install from `.[dev]` | Installed, but tests then failed collection with **15 errors**: undeclared `yaml` dependency |
| Full tests after supplying PyYAML | **211 passed, 4 failed, 4 skipped**, 71% combined statement/branch coverage |
| Full tests after fixing review UV cache and virtualenv bindings | **211 passed, 4 failed, 4 skipped**, 71% coverage; UV test now passed, gateway test failed |
| Diagnostic full-suite rerun | **212 passed, 3 failed, 4 skipped**; captured 17 provider error responses containing HTTP 429/rate-limit markers |
| Isolated gateway tests | **2 passed**; does not establish an external model connection |
| `ruff check mas tests --output-format concise` | Exit 1, **1,041 findings** with the installed Ruff version; many are style/modernization findings, not runtime defects |
| CLI doctor | Exit 0; STAGED dispatch, sandbox/ACL enabled, no provider configured; registry claims all 29 capabilities implemented |
| Supervisor demo | Exit 0; deterministic text output, not evidence that claimed infrastructure actions occurred |
| Research verifier | Exit 0; scanned **zero documents**, then emitted **10/10, RATIFIED & VERIFIED** |
| Safe local adversarial fixtures | All assertions passed in the final reproduction script; reproduced defects listed below |
| Installed wheel inspection outside checkout | Dashboard static HTML absent from installed package |

Three repeatable remaining suite failures: invalid SQL accepted by the offline BigQuery dry-run; fabricated BigQuery result lacks the expected `num` field; GitOps integration depends on missing OmniLedger project tests. Three desktop tests require Xvfb/xdotool and one portal test requires Playwright, so they were skipped, not validated. Gateway instability is consistent with shared handler-level rate state: diagnostic responses contained 429 errors, and isolated tests passed. The precise scheduling cause of the intermittent gateway assertion failure was not traced exhaustively.

Evidence is retained at `/workspace/review-evidence/acinonyx/`: `pytest.log`, `pytest-with-yaml.log`, `pytest-final.log`, `pytest-diagnostic.log`, `gateway-isolated.log`, `ruff-verified.log`, `coverage-final.xml`, `doctor.log`, `supervisor-demo.log`, `research-verifier.log`, `reproduce_findings.py`, and `reproductions.json`.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

**H1 — Python execution is not an isolation boundary.**

- Issue: `mas/tools/executor.py:16` and `:48` apply regex restrictions then run the host Python interpreter with inherited environment and permissions. With sandbox mode enabled, fixture code successfully read a file outside the configured jail, read an injected disposable environment marker, and ran `os.system`. Output is fully buffered; timeout kills only the immediate process without awaiting its exit.
- Impact: agent-generated code can access everything permitted to the runtime account, including other workspaces and accessible credentials; descendants and output/resource consumption are not contained by these checks.
- Remediation: execute untrusted code in a separate hardened worker/container with explicit mounts, scrubbed environment, network policy, non-root identity, CPU/memory/PID/output limits, and process-tree cancellation. Treat regex checks as supplemental validation. Verify containment with safe fixtures before enabling untrusted execution.

**H2 — MCP authorization can be bypassed.**

- Issue: `mas/mcp/protocol.py:233` prefers the request payload's `principal` over the transport caller. `:146` grants every registered tool to the default allowlist; `:148` exposes a synchronous dispatch path without ACL or argument filtering. A request authenticated as a denied fixture reader succeeded by naming an allowed fixture admin; anonymous and synchronous calls also succeeded.
- Impact: registering a privileged tool can make it available to unknown callers; caller-controlled identity defeats restrictions.
- Remediation: derive identity solely from trusted transport authentication; deny unknown callers by default; separate tool registration from grants; centralize authorization and schema validation across synchronous/async calls, resources, and prompts. Add spoofing and negative-access tests.

**H3 — Filesystem jail permits escapes and incomplete enforcement.**

- Issue: `mas/tools/filesystem.py:31` uses `abspath(...).startswith(root)`. A sibling directory named `allowed-sibling` passes the `allowed` prefix, and symlinks are not resolved. `:61` and `:78` list/glob without jail checks. All four cases were reproduced using disposable files. Patch tools reuse the same unsafe path check; Git tools accept caller-specified working directories without this boundary.
- Impact: reads/writes and directory discovery extend beyond the advertised root. Global allowed roots also cannot represent independent per-request tenant isolation.
- Remediation: use a centralized, request-scoped path policy with component-aware containment and symlink-safe file opening. Enforce it for read/write/list/glob/patch/Git/package operations. Use OS isolation to avoid relying solely on application checks vulnerable to path races.

**H4 — Dashboard control plane has no authentication.**

- Issue: `mas/dashboard/server.py:198` permits POST dispatch changes without identity or permission checks; other handlers expose events, prompts, artifacts, and engagement execution. Default binding is `0.0.0.0` (`:224`); Compose publishes port 8080. Wildcard CORS increases browser reachability. An unauthenticated loopback POST changed dispatch state on an inert fixture enterprise; no real dispatch was armed.
- Impact: any client able to reach the service can inspect shared data and invoke control operations. STAGED default alone does not protect its enabling endpoint.
- Remediation: bind locally by default; require authenticated, tenant-scoped authorization for every API action; constrain origins; validate input and body sizes; add concurrency/rate limits. Protect dispatch enablement with an explicit authorized operation. Isolate handler state per server/request.

**H5 — IAM trusts a published default signing key and is not integrated into the exposed boundary.**

- Issue: `mas/iam.py:90` provides a constant signing secret; verification accepts signed role claims rather than revalidating current principal grants. A separate default-configured fixture IAM instance issued admin claims accepted by a victim instance where the same user was read-only. `authorize` (`:278`) ignores the stored custom-policy structure and `resource_urn`; it does not itself recheck expiry or tenant lifecycle. Dashboard/MCP do not enforce this tenant context at their exposed entry points.
- Impact: using the default permits claim forgery; role revocation and fine-grained resource policy guarantees are incomplete. An IAM module alone is not platform tenant isolation or an OAuth integration.
- Remediation: fail startup without an explicitly supplied signing key for protected modes; support rotation/revocation and current principal validation; enforce deny precedence and resource scopes; integrate authenticated context into actual endpoints and storage/tool access. Add expired, revoked, suspended, forged, and cross-tenant cases.

**H6 — Verification paths manufacture success and conceal upstream failure.**

- Issue: `scripts/verify_research_swarm.py:30` scans a hard-coded workstation path and uses fixed 10.0 reviewer ratings (`:120` onward), without making ratification depend on scan results. It ratified an empty scan. `mas/tools/delegation_tool.py:48` returns unexecuted persona text claiming QA assertions passed. `mas/providers/gateway.py:200` catches upstream failure and emits synthetic output; a stubbed outage returned HTTP 200 with a “PRODUCTION READY” QA certificate. Golden evaluations use echo agents and structural keyword scoring (`mas/eval/harness.py`).
- Impact: operator-facing success is not reliable evidence of completed work, model reasoning, or verified quality. An outage can be mistaken for an approved deliverable.
- Remediation: make production paths fail closed; make simulation explicit and opt-in with machine-readable provenance; prohibit simulated output from signing off releases. Run actual reviewers/tests, require nonzero targets and fresh result artifacts, and separate structural orchestration tests from AI quality benchmarks.

**H7 — Cloud persistence claims are mock-only.**

- Issue: all Vertex AI, Pinecone, and Qdrant methods in `mas/memory/vector_saas.py:147` onward delegate directly to `MockManagedVectorStore`. No live SDK/HTTP operation exists in these adapters. Describe responses nevertheless label provider/cloud properties. `mas/capabilities.py` calls them implemented production connectors.
- Impact: data assumed to be stored remotely is held only in process memory; restart loses it and cloud isolation/durability are unproven.
- Remediation: label existing adapters simulation-only; production selection must refuse mock substitution. Implement real connectors with explicit credentials, namespaces, dimension checks, error handling, and integration tests before claiming remote persistence.

**H8 — Clean package/CI validation is broken.**

- Issue: `pyproject.toml:12` declares no runtime dependencies while `mas/tools/data_contract_tool.py:13` imports PyYAML at module import. The clean documented install caused 15 collection errors. The required lint command fails. GitOps integration references unpopulated Git-linked project content without usable `.gitmodules` metadata.
- Impact: a fresh install and configured CI cannot validate this branch as delivered. Docker's `pip install -e .` also lacks the dependency required by its dashboard import chain.
- Remediation: declare true runtime/optional dependencies with supported import boundaries; establish reproducible tool constraints and an explicit lint policy; make integration fixtures self-contained or declare and provision their external checkouts. Verify in a fresh environment without ambient packages.

### Medium Severity (Technical Debt / Fragility)

**M1 — Data-contract validation omits declared types and mishandles values.** `mas/tools/data_contract_tool.py:65` does not enforce schema types; `:104` skips falsey enum values; `:90` string-concatenates compound keys. Fixtures admitted a string into an integer column and zero outside its enum. Validate the contract schema, enforce typed values/null rules, and use tuples for compound-key identity. Add malformed, zero/false, and delimiter-containing cases.

**M2 — Fail-fast does not stop sibling work.** `mas/orchestration/supervisor.py:179` uses `asyncio.gather` without explicit sibling cancellation on a worker exception. A fixture sibling performed its delayed side effect after the mission raised. Use structured cancellation, await cleanup, and distinguish retry-safe/idempotent actions. Add a concurrency bound and deadline budget; validate task identifiers/dependencies before starting work.

**M3 — Context grows beyond the advertised window.** `mas/core/agent.py:183` inserts retrieved reflections as SYSTEM messages; `mas/memory/working.py:28` pins every SYSTEM message outside capacity eviction. Forty retrievals exceeded capacity in a fixture. Separate trusted pinned instructions from bounded retrieved data, enforce a token budget, and deduplicate/summarize context. Retrieved text must not gain system-instruction authority.

**M4 — Gateway accounting and state are not robust.** `mas/providers/gateway.py:50` accepted a negative reservation that reduced cumulative spend. HTTP accounting reserves input-size estimates (`:188`) but does not settle actual completion usage. Governor/upstream settings live on a shared request-handler class (`:134`, `:392`), coupling servers and tests. Validate nonnegative amounts, reserve completion ceilings, settle actual usage, scope budgets per tenant/engagement, and instantiate server-owned state. Add parallel and over-budget cases and propagate error responses as failed tasks.

**M5 — Checkpoints are mutable and not durable transactions.** `mas/core/state.py:63` returns the same checkpoint containing a mutable dictionary; modifying it changed subsequent rollback in a fixture. State/checkpoints are memory-only and unsynchronized while the dashboard uses multiple threads and loops over shared objects. Protect mutation, return immutable/defensive snapshots, and define persisted transactional checkpoints if restart recovery is required. SQLite uses `check_same_thread=False` without a write-ownership policy; trajectory and reflection commits are separate (`mas/memory/episodic.py:217`). Test atomic failure and concurrent writers before claiming ACID recovery.

**M6 — Audit failures are suppressed.** `mas/core/event_bus.py:130` catches append failures and continues. The fixture reported audit enabled and successful publish after an append OSError. Define mandatory-audit versus optional-observability policy; fail closed for governed operations, or emit explicit degraded status/alerts. Bound event history and subscriber work, and avoid synchronous fsync blocking the event loop under load.

**M7 — Release integrity assumes trusted declarations.** `mas/release_policy.py:96` validates hashes/IDs and suite completeness, but self-asserted completed suites with empty findings and no output artifacts receive permission. File existence checks apply only to blocking findings; a hash label is not proof that a runner executed against that candidate. Keep the useful mismatch/duplicate/incomplete rejection checks, but require trusted runner provenance, artifact digests and fresh results for every required suite. The fixture demonstrates the API's trust assumption, not a compromise of an independently secured runner.

**M8 — BigQuery cost/syntax gates fail open offline.** `mas/tools/bigquery_tool.py:43` returns valid/zero-cost without a CLI, including invalid SQL. Real execution only compares an optional estimate and does not pass a maximum-bytes-billed limit to the execution command (`:155`). Return explicit unavailable/simulation status that cannot authorize production execution; apply the server-side billing ceiling and reject unparseable estimates. Two existing tests already fail on the fallback.

**M9 — Installed package and imports are incomplete.** Dashboard static files are not declared in `pyproject.toml:33` and were absent from the installed wheel outside the checkout. Importing `mas.providers` before core initializes also reproduced a circular import through `mas/providers/base.py`, `mas/core/__init__.py`, and `mas/core/agent.py`. Include runtime assets and remove eager cross-package initialization; test entry points/import order and installed-wheel functional behavior outside the source directory.

### Low Severity (Optimizations / Best Practices)

**L1 — Documentation and links drift from the branch.** README/docs label IAM and vector integration planned while the registry labels everything implemented; frontier documentation uses workstation `file://` links. Generate consistent capability documentation from evidence-backed status, use repository-relative links, and keep mock/live provenance visible.

**L2 — Benchmark semantics need clearer names.** Hashed lexical features and SQLite full-scan cosine ranking are useful local primitives, but do not establish model-grade semantic retrieval or scale. Label the method precisely, benchmark retrieval relevance and latency on representative data, and use the same embedding function/dimension for writes and queries when custom embeddings are supplied.

## 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** Local modular orchestration is demonstrable, but host-level execution and shared threaded service state are unsafe for the claimed isolation. Fail-fast cleanup, bounded concurrency, fresh packaging, and per-instance service state need correction. No sustained load/latency benchmark or cost envelope was validated.
- **Data & Schema Contracts:** Basic SQLite/vector and null/uniqueness checks exist, but remote stores are mocks, checkpoints are mutable/in-memory, and declared type checks are absent. End-to-end tenant isolation, atomic restart recovery, and retention/deletion governance are not established.
- **AI & Model Runtimes:** A five-turn ReAct cap is present; prompts alone do not establish safe tool authority. Context growth, swallowed provider/grounding errors, fixed-score evaluations, and simulation-generated signoffs undermine confidence. Local mock gateway tests do not validate paid/external models.
- **Resilience & Governance:** Default STAGED state, HMAC comparison, fsynced JSONL writes, typed bus validation, and release mismatch checks are useful controls. They are insufficient alongside public control endpoints, default signing keys, bypassable ACLs, suppressed audit failures, and fabricated success evidence.

## 4. Architect’s Action Directive

1. **Contain exposed and untrusted execution surfaces (H1–H5).** Keep the runtime locally bound with trusted inputs; require actual authenticated context, deny-by-default tools, symlink-safe path enforcement, and an isolated execution worker. No enterprise production deployment before negative-access and containment tests pass.
2. **Restore trustworthy outcomes (H6–H7, M7–M8).** Remove simulated approval from production flows. Make model/cloud outages explicit failures; label mock stores/demos; require fresh, candidate-bound runner artifacts for release permission. Empty targets and missing providers must never produce verified status.
3. **Repair reproducibility (H8, M9).** Correct dependency/asset declarations and import cycles, provision portable integration fixtures, resolve configured lint, and run CI from a fresh install. Validate the wheel outside the checkout and Docker startup after those fixes.
4. **Make execution and state reliable (M2–M6).** Cancel siblings, bound concurrency/tokens, scope gateway state and budgets, ensure immutable transactional recovery, and surface mandatory audit failures. Add safe regression tests for each reproduced case.
5. **Strengthen data semantics (M1, M5, L2).** Enforce typed contracts and correct compound identities; validate atomic writes, embedding consistency, tenant namespaces, backup/restore, and retention expectations.
6. **Revalidate integrations and claims.** Execute browser/desktop checks with prerequisites, then credentialed cloud/model tests only in an authorized environment. Reconcile README, capability registry, and frontier documentation with those results. Set representative performance targets before benchmarking.
7. **Resubmit for independent review.** Supply a fixed commit, exact test/lint results, negative-security evidence, real integration provenance, and reproducible deployment/recovery checks. Close each relevant blocker with evidence; a high pass count or generated certificate is insufficient.

## Review limits and repository preservation

Application code, tests, manifests, and lockfiles were not changed. No deployment, push, external model/cloud operation, or real dispatch enablement occurred. Docker daemon availability was checked; an image build was not run because clean runtime dependency failure is already established. Browser/desktop execution, credentialed cloud/model integrations, exhaustive concurrency testing, load tests, and production backup/restore remain unvalidated. The full quality-gate script was not run because it regenerates tracked portal assets; its research step was executed separately.

The assigned initial review is complete within this stated scope. Fixes and verification of corrected behavior remain outstanding; this report does not mark defects resolved.
