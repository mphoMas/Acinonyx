# MAS repository verification and remediation — 2026-10-08

## 1. Verdict & Executive Summary

- **Status: APPROVED WITH CONDITIONS** for a dedicated-machine, supervised coding pilot. **REJECTED (REQUIRES RE-WORK)** for enterprise production, hostile public tenants and a full-MAS 10/10 certification.
- **Baseline:** `d5020a0fada6d0838f6507b5dcc685cdfbfa7f18`, branch `Acinonyx_frontier`. The results below apply to the repaired working tree; its source fingerprint is recorded in `REVISION_VERIFICATION_EVIDENCE.json`. Historical reviews describe earlier revisions.
- **Core summary:** The complete application suite now executes real browser, desktop and Docker tests, and the reproduced failures have been repaired. Recovery, adversarial and live Gemini acceptance evidence supports the supervised pilot; it does not establish multi-tenant isolation, broad model reliability or production recovery guarantees.

### Executed evidence

| Check | Result | Scope and limit |
|---|---|---|
| Initial collection | 23 errors | Required Pydantic dependency was undeclared |
| Baseline after installing dependency | 303 passed, 13 failed, 5 skipped | Established real failure baseline; no successes fabricated |
| Final documented quality gate | **349 passed, zero failed, zero skipped** | Lint, doctor/capability reporting, research links, source compilation, full pytest suite |
| Coverage run during remediation | 342 passed, zero failed/skipped; 74% combined coverage | Later regressions also run by the final gate; coverage is not a security score |
| Dedicated recovery/adversarial suite | 51 passed, zero failed/skipped | Real Docker workers; scripted TLS model fixture; not live model-quality evidence |
| Added audit/revision regressions | 17 passed | Includes event-bus failure, database restart, shared-token isolation and related bus tests |
| Fresh live Gemini benchmark | 26/26 cases across three tasks | Nine model calls, 11,651 reported tokens; one sample per goal |
| Local research asset/link scan | 89 Markdown documents, 197 links, zero missing local targets | Does not verify academic claims, external URLs or agent reviews |
| Wheel build and clean installation | Passed | Required runtime imports, CLI entry points and packaged dashboard asset checked outside checkout |
| Digest-pinned runtime image | Built; UID 10001, portal HTTP 200, unconfigured mutation HTTP 401, PM record survives container recreation | Non-root startup, real HTTP responses, restart persistence and cleanup checked separately |

The live tasks were stable deduplication (10 cases, 2,883 tokens), invoice reconciliation (10 cases, 6,076 tokens), and an imported prompt requesting fabricated approval/credential access (6 cases, 2,692 tokens). All three runs ended in `awaiting_approval`. No candidate was granted human approval, exported or deployed.

Private signing keys, tokens, databases and generated source remain outside Git under `/workspace/swarm-live/revision-audit-20261008`. Detailed non-secret logs are under `/workspace/review-evidence`; the checked-in manifest summarizes outcomes and fingerprints application sources.

## 2. Architectural Audit & Critical Findings

### Confirmed defects repaired

1. **Packaging and CI:** Declared required Pydantic 2 and Pillow; included the Python browser extra in the runtime image; pinned Ruff 0.5.7 to stabilize the existing CI rule set; repaired actual lint errors. CI installs pinned browser/desktop prerequisites and the digest-pinned worker image instead of silently skipping integration checks.
2. **Execution:** Bubblewrap now mounts the real interpreter behind virtualenv symlinks, no longer mounts all of `/etc`, and refuses host fallback when sandboxing is required. Timeouts are validated, output is bounded, and cancellation/overflow cleanup kills process groups, drains pipes without retaining output and reaps children. The shared swarm subprocess helper also received the overflow cleanup correction.
3. **Cloud-result honesty:** BigQuery and GCS no longer synthesize successful validation/data when their CLI is absent. A nonzero GCS listing fails. Missing BigQuery cost estimates fail closed and requested billing caps reach the execution CLI. Cloud vector adapters advertise simulated, nonpersistent backing; managed vector SaaS is marked demo-only.
4. **Governance:** Removed public signing-key defaults. Persistent PM evidence/verdicts require configured private keys; empty and `sig_*` approvals no longer bypass verification. Unconfigured IAM instances have different random process-local keys. Existing fake/default-key approvals are not migrated into trusted approvals.
5. **Dashboard:** Missing configured tokens deny protected operations. Reviewer identity comes from trusted server configuration, rather than request JSON. Each server owns its enterprise reference, token and cached artifacts. A shared token still represents one operator, not several independent reviewers.
6. **Required audit:** A configured event-bus audit failure stops publication before history/counter mutation or subscriber dispatch; it is no longer ignored.
7. **Data/recovery:** Container PM state uses `/app/workspace/mas_pm.db`, inside the persistent workspace mount. Backup/restore checks preserve evidence immutability and signed verdict verification. Concurrent swarm submission testing exercises 32 submissions through eight threads, producing exactly eight idempotent jobs and consistent restored cancelled states.
8. **Verification integrity:** Local CI rejects zero discovered tests and propagates actual failures. Evidence tests preserve immutable-record enforcement. Test default PM databases are isolated from operational checkout state. The research checker measures assets/links and cannot award canned ratings or pass an empty corpus.
9. **Browser and delivery:** Fixed the offline snapshot row-array/grouped-board mismatch and label offline/demo telemetry explicitly. Browser tools respect configured binary paths. Runtime image includes portal and work-queue assets, required sandbox tools, a supported Bookworm base pinned by digest, and transient build-time CA trust. Repaired 138 stale workstation-specific research links and portable catalog paths.

### High severity — enterprise deployment blockers

- **Issue:** General MAS tools and state do not demonstrate end-to-end authenticated tenant isolation. Bubblewrap exposes configured project roots; trusted Python code can still construct execution contexts and call internal APIs. The supervised swarm's stronger controls do not automatically protect every legacy path.
  - **Impact:** Public or mutually distrusting tenants cannot safely share the full runtime on the evidence available.
  - **Remediation:** Establish tenant-bound identities, workspace/state/tool authorization at actual entry points, restrict trusted control-plane access, and demonstrate cross-tenant negative tests before deployment.
- **Issue:** Authentic whole-database/audit rollback cannot be detected solely by local HMAC records. Backup tests demonstrate restoration, not a remotely anchored history or distributed recovery service.
  - **Impact:** An older authentic snapshot may replay previously valid authority/state without a trusted external freshness anchor.
  - **Remediation:** Provide an external append-only audit/checkpoint anchor and validate rollback rejection, key recovery and crash reconciliation.
- **Issue:** Legacy PM log hashes/signatures prove record integrity, not that a trusted verifier actually executed the claimed tests. Cloud vector adapters remain local simulations, and real BigQuery/GCS authorization and persistence were not exercised.
  - **Impact:** Enterprise verification/data guarantees exceed demonstrated integration behavior.
  - **Remediation:** Accept verifier-issued execution evidence at release boundaries; implement and exercise required real services before promising their guarantees.

### Medium severity — fragility and assurance gaps

- **Issue:** The default runtime container cannot establish nested bubblewrap namespaces under its default Docker security policy. The legacy Python tool refuses execution, while UI/API startup and durable PM storage work.
  - **Remediation:** Run supervised swarm workers on a supported dedicated coordinator host, or provide a separately reviewed execution service. Do not disable isolation or grant broad container privileges to turn this refusal into apparent success. The default image is not an acceptance result for legacy coding missions.


- **Issue:** Docker shares the host kernel. Bounded workers, real cancellation, orphan removal, OOM and network denial tests are useful evidence, not proof against every kernel exploit or Docker daemon failure.
  - **Remediation:** Keep pilots on dedicated hosts; stronger isolation and daemon-loss reconciliation are required for hostile tenants. Do not grant broad container privileges to make nested sandboxing work.
- **Issue:** Live model evidence is three sampled tasks. Concurrent state submissions are a bounded workload, not sustained production load or multi-host failover testing.
  - **Remediation:** Define acceptance distributions, soak/load targets and failure budgets, then test them independently.
- **Issue:** Durable governance now depends on private key provisioning and restoration. One dashboard credential cannot establish separation between several human reviewer identities.
  - **Remediation:** Provision keys through environment secrets, retain them with protected recovery procedures and use individually authenticated reviewers for production approvals.

### Low severity

- **Issue:** Historical review artifacts and generated/demo assets can be mistaken for current evidence.
  - **Remediation:** Use this dated report and source-bound manifest; treat older verdicts as historical. Research verification now expressly excludes factual/model-quality certification.

## 3. Pillar-by-Pillar Breakdown

- **Platform & System Design:** The supervised path and local runtime are tested with real execution prerequisites. The container image has a reproducible base and durable PM placement. Full shared-tenant and multi-host operating guarantees remain unproven.
- **Data & Schema Contracts:** Packaging and immutable evidence tests are repaired; real local backup, process restart and container persistence checks are included. SaaS vector persistence is explicitly unavailable, and service protocol unit tests are not live cloud integration.
- **AI & Model Runtimes:** Fixed-role swarm proposals pass external host checks and cannot grant themselves human approval. Live Gemini tests cover successful and adversarial task inputs; broad reliability is not established.
- **Resilience & Governance:** Audit failures, unavailable sandboxes/services, forged signatures, output floods and cancellation fail visibly. Signing-key management, external audit anchoring and production identity remain deployment requirements.

## 4. Architect’s Action Directive

1. **Completed:** Repair reproduced baseline failures and execute the full repository quality gate with integration prerequisites.
2. **Completed:** Exercise bounded recovery, concurrent idempotency, adversarial execution, forged authority, live Gemini proposals and real local UI tests.
3. **Pilot prerequisite:** Configure private governance keys and a dedicated workspace/host; use a separate human approver. Protected operations intentionally fail when credentials are missing.
4. **Enterprise blocker:** Implement end-to-end tenant enforcement and verifier-issued release evidence. Demonstrate unauthorized cross-tenant access and forged/zero-test evidence rejection.
5. **Enterprise blocker:** Anchor audit freshness externally and test whole-snapshot rollback, daemon loss, host loss, restore and sustained concurrent workloads.
6. **Enterprise blocker:** Validate real required data-service integrations and repeated live-model evaluation before broad rollout. Keep unimplemented integrations and historical evidence clearly labeled.

No new product feature was added in this remediation cycle. A passing test count does not award a 10/10 architecture certification.
