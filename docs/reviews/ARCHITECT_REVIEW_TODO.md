# Independent Reviewer & Chief Architect — Assigned Tasks

Owner: Codex, acting as Independent Reviewer & Chief Architect for Platform, AI & Data.
Scope: `mphoMas/Acinonyx`, branch `Acinonyx_frontier`.
Baseline inspected: `7e75b857703b3744da456eced493f83d87d10559`.

This is a review backlog, not a production approval. Initial observations are from source inspection; tests have not yet been executed for this branch. Priorities describe review order and potential consequence, not confirmed severity for every subsystem.

## Review status

Initial review completed; verdict: **REJECTED (REQUIRES RE-WORK)** for enterprise production and untrusted execution. See [ARCHITECT_REVIEW.md](ARCHITECT_REVIEW.md) for findings and evidence. Checked items mean the initial assessment was performed, not that its acceptance criteria passed or defects were fixed. Browser/desktop, external cloud/model, load, Docker image startup, and backup/restore validation remain outstanding as recorded in the report.

## Assigned work

- [x] **1. Establish a reproducible validation baseline.** Inspect test setup and side effects before executing tests. Prepare an isolated Python environment using `pyproject.toml` and the CI workflow; identify browser, display, cloud, and credential prerequisites. Run relevant lint, unit/integration tests, CLI health, and offline demos. Record commands, tool versions, exact test counts, failures, skips, and unavailable integrations. Compare `scripts/run_quality_gate.sh` with `.github/workflows/ci.yml`; investigate unexpected failures without changing assertions to obtain a pass.
  - Done when: another developer can reproduce the results, and environment failures are distinguished from code defects.

- [x] **2. Reconcile capability claims with evidence.** Compare `README.md`, `docs/CAPABILITIES.md`, `mas/capabilities.py`, implementations, and tests. The documents mark IAM/vector SaaS as planned and engagement as demo-only, while the runtime registry marks them implemented. Inspect `mas/iam.py`, `mas/memory/vector_saas.py`, and `mas/organization/engagement.py`; distinguish local logic, mocks, real integration paths, and verified live behavior. The quality-gate script's unconditional “10.0 / 10.0” success wording also needs an evidence standard.
  - Done when: every material capability claim has a consistent status, scope, prerequisites, and supporting verification; unsupported claims have a proposed correction.

- [x] **3. Review execution and tool security boundaries.** Inspect `mas/tools/executor.py`, filesystem/path enforcement, shell/Git/browser/desktop tools, and ACL integration. The Python executor visibly uses regex restrictions plus a subprocess; it does not visibly establish an OS isolation boundary. Safely test allowed file/process access using disposable fixtures, environment inheritance, output/resource limits, timeout cleanup, and descendants. Do not execute destructive payloads or access credentials.
  - Done when: the threat model and actual isolation guarantees are explicit, with reproducible findings and prioritized containment recommendations for untrusted code.

- [x] **4. Review IAM, tenant isolation, and exposed interfaces.** Trace authentication and authorization from dashboard/MCP/swarm entry points to tools, memory, and storage. Check token verification, expiry, revocation, key handling, tenant scoping, deny precedence, and path isolation. Distinguish custom HMAC authentication from OAuth integration; exercise negative authorization cases.
  - Done when: enforcement is demonstrated at actual entry points, and cross-tenant or unauthenticated access findings have concrete tests and remediation.

- [x] **5. Audit data contracts and persistence.** Review SQLite memory, vector adapters, communications vault, data-contract validation, BigQuery, and storage tools. Examine transaction boundaries, concurrent writes, retry/idempotency behavior, tenant metadata, schema evolution, lineage, and deletion/retention handling. Separate mocked adapter tests from real service validation.
  - Done when: consistency and recovery guarantees are documented and tested at relevant boundaries, with missing live evidence explicitly identified.

- [x] **6. Audit orchestration and agent termination.** Inspect the event bus, supervisor, SOP pipeline, debate, ReAct loop, delegation, squad repair, and engagement checkpointing. Check cycles, concurrency bounds, cancellation, retry amplification, duplicate side effects, token/cost limits, context growth, and restart behavior. Assess prompt/tool-output injection boundaries.
  - Done when: failure and adversarial cases establish bounded execution, explicit state transitions, and safe side-effect handling, or demonstrate specific defects.

- [x] **7. Evaluate AI quality and release evidence.** Inspect golden missions and scoring, anti-sycophancy evaluation, provider fallback, and `mas/release_policy.py`. Separate deterministic templates from model-driven performance. Check that required suites execute, evidence is bound to the candidate/run, negative cases fail, and missing/tampered evidence blocks release. Treat PII redaction claims separately from proof of regulatory compliance.
  - Done when: benchmarks measure the intended behavior, release decisions are reproducible, and evidence gaps are visible.

- [x] **8. Assess deployment and operational readiness.** Inspect Docker/Compose, CI coverage for this branch, dependency reproducibility, non-root operation, service binding, health checks, configuration, logging, metrics, backups, and failure recovery. Identify latency/resource/cost assumptions; measure representative workloads where practical. Inspect recorded Git links for `workspace/projects/bmm` and `workspace/projects/omniledger`, whose submodule metadata could not be resolved during checkout inspection.
  - Done when: deployment prerequisites and recovery procedures are reproducible, with a supported operating envelope and explicit limitations.

- [x] **9. Produce the independent architecture verdict and remediation plan.** Consolidate confirmed findings across platform, data, AI, and governance. Include file/line evidence, severity, impact, correction, and validation requirements. Issue APPROVED, APPROVED WITH CONDITIONS, or REJECTED (REQUIRES RE-WORK) for an explicitly stated use case; separate deployment blockers from later improvements.
  - Done when: every blocker has a verifiable closure condition and every conclusion is supported by inspected or executed evidence.

## Working rules

- Keep this checklist updated as work completes; record evidence rather than merely checking boxes.
- Preserve existing user changes. Review first; application fixes are separate work from this task-list request.
- Do not publish, deploy, push, arm live dispatch, or perform external side effects as part of a review without authorization.
- Reassess priorities when findings justify it; do not start optional feature expansion before correctness and security are established.
