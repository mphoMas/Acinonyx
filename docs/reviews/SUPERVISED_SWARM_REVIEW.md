# Supervised swarm delivery review — 2026-10-08

> Historical assessment. See [current revision verification](REVISION_VERIFICATION_2026_10_08.md) for the latest remediation and executed evidence.

## 1. Verdict & Executive Summary

- **Status: APPROVED WITH CONDITIONS** for a dedicated-machine, supervised Python-function pilot. **REJECTED** for enterprise production, public hostile-code execution or a 10/10 certification of full MAS.
- **Scoped assurance rating: 8/10.** This is an engineering assessment of the bounded pilot, not a score calculated from test pass percentages. The requested 10/10 target remains unmet.
- **Core summary:** The new `mas.swarm` control plane actually generates code with Gemini, executes it in constrained containers, verifies results outside the candidate process, persists signed state and requires a distinct operator identity for release. It substantially improves the demonstrated workflow, while leaving legacy MAS paths and broader production assurance unresolved.

### Executed evidence

| Check | Observed result | Practical limit |
|---|---|---|
| Fresh wheel installation, outside-checkout CLI/imports | Passed; new package and dashboard HTML included | Does not prove future cloud snapshot restoration |
| Installed-wheel swarm regression/integration suite | **34 passed, 0 failed, 0 skipped**, 50.64s | TLS model fixture; actual Docker execution |
| Full repository suite | **246 passed, 3 failed, 4 skipped**, 65.93s | Existing BigQuery/GitOps defects and desktop/browser skips remain |
| Gemini authenticated discovery | `gemini-3.8-flash` found at Google OpenAI-compatible endpoint | Availability must be rechecked in each environment |
| Real Gemini sum workflow | 3/3 black-box cases passed; 3 calls; 2,917 reported tokens | Small example; awaiting human approval |
| Real Gemini benchmark | **26/26 cases across three tasks passed** | Single sampled run per task, not broad model-quality assurance |
| Orphan-worker inspection after tests | No labelled swarm containers remained | Does not prove behavior during every daemon/network failure |
| Hardware isolation capability | `/dev/kvm` absent | MicroVM execution was not available or tested |
| Targeted lint and diff whitespace | Passed | Repository-wide historical lint debt remains |

The live benchmark covered stable deduplication (10 cases, 31.59s, 3,138 tokens),
invoice reconciliation (10 cases, 39.74s, 6,095 tokens), and an untrusted imported
note requesting forged approval/credential access (6 cases, 25.17s, 2,954 tokens).
All three reached `awaiting_approval`; no human approval, export or deployment was
performed for these live candidates. Their total reported usage was 12,187 tokens.
The model reviewer used a separate inference/context, with the same model family;
this does not remove correlated model errors.

The first live sum run failed closed because Gemini reported thinking overhead
outside visible prompt/completion counts. The adapter was corrected to charge
the entire reported total while rejecting underreported, negative, missing and
over-budget usage. Regression tests cover both accepted overhead and rejected
underreporting. The failed run retained its reservation instead of manufacturing
success or assuming no provider cost.

Machine-local evidence: `/workspace/review-evidence/swarm-clean-release.log`,
`swarm-full-release.log`, `swarm-full-release.xml`, and the non-secret live summary
at `/workspace/swarm-live/benchmark-v1/report.json`. State, signing keys and bearer
credentials remain private and are not committed. The structural verification
script emits source-bound reports and deliberately awards no numerical rating.

## 2. Architectural Audit & Critical Findings

### High Severity — production blockers

- **Issue:** Existing dashboard, MCP, IAM, filesystem and Python-executor paths retain the previously reproduced security defects. The new CLI does not route through them.
  - **Impact:** Exposing the legacy services or allowing legacy tools to execute untrusted work would bypass the new swarm's safety boundary. Full MAS remains rejected.
  - **Remediation:** Apply the prioritized fixes in [ARCHITECT_REVIEW.md](ARCHITECT_REVIEW.md), then test the same adversarial cases through every exposed route. Retire unsafe routes before migration; a second safer entry point does not repair the first.
- **Issue:** Docker shares the host kernel; stronger containment and hostile-tenant isolation have not been demonstrated. This environment lacks `/dev/kvm`.
  - **Impact:** The current execution profile does not establish suitability for a public arbitrary-code or multi-tenant production service.
  - **Remediation:** Validate workers on dedicated infrastructure with microVM or equivalent hardened isolation, penetration tests, tenant separation and explicit host/worker compromise recovery before accepting that scope.
- **Issue:** Production identity, external immutable audit and an independent deployment review are absent.
  - **Impact:** Local OS administrators remain trusted; a full authentic database/audit rollback cannot be detected without an external anchor. Separate local subject names do not establish enterprise SSO identities.
  - **Remediation:** Integrate enterprise identity/resource authorization and externally anchored audit, protect/rotate signing keys and obtain independent security review. Keep the human release gate.

### Medium Severity — operational fragility

- **Issue:** The live benchmark is small and each task was sampled once. It provides useful functional evidence, not general correctness or consistent model reliability.
  - **Remediation:** Add a held-out domain corpus, repeated runs, prompt-injection variants, reviewer-disagreement analysis and explicit error-rate/latency acceptance targets. Preserve failing attempts in the evidence.
- **Issue:** Audit verification scans history; state and scheduling are local. Aggregate tenant/run quotas, multi-host failover, retention, key rotation and sustained-load tests are not implemented or established.
  - **Remediation:** Measure load and audit growth, introduce bounded retention with verified archive anchors, implement service-wide admission control and validate crash/failover behavior before scaling.
- **Issue:** A lost Docker creation response or unavailable daemon can leave an uncertain labelled worker requiring reconciliation. Provider cancellation also cannot reverse an already accepted remote inference charge.
  - **Remediation:** Keep conservative reservations and explicit `recover`/`cleanup`. Add durable worker reconciliation and provider-side spending limits; test actual daemon disconnection and coordinator crashes repeatedly. Never auto-replay uncertain work.
- **Issue:** The full suite remains red on two BigQuery simulation expectations and a GitOps test depending on an unavailable OmniLedger project.
  - **Remediation:** Make unavailable services fail explicitly, use meaningful self-contained fixtures, and resolve failures without deleting assertions or fabricating successful integrations. Run a clean full CI suite afterward.

### Low Severity — follow-up

- **Issue:** CI uses version-tagged third-party actions and its new workflow has not run remotely in this task.
  - **Remediation:** Pin reviewed action revisions and observe the actual branch CI before treating its status as evidence. Local commands passing do not prove remote CI passed.

## 3. Pillar-by-Pillar Breakdown

- **Platform & System Design — 8/10 for the pilot:** Digest-pinned, non-root workers, CPU/memory/process/output/time limits, no mounts/egress, joined cancellation and observed cleanup work. Distributed scheduling and hostile-tenant containment remain outside accepted scope.
- **Data & Schema Contracts — 8/10 for the pilot:** Strict bounded JSON, immutable request hashes, tenant-bound idempotency, atomic claims, FULL SQLite transactions, signed state/identity, audit consistency, selective-replay rejection and backup/restore are tested. External rollback anchors, migrations, retention and key lifecycle need production work.
- **AI & Model Runtimes — 8/10 for the pilot:** Live requested-model discovery, three bounded role calls, actual usage including thinking overhead, host-owned behavioral verification, reviewer rejection and truthful provider failure are implemented. The benchmark and reviewer independence are limited; temperature zero is not a determinism guarantee.
- **Resilience & Governance — 8/10 for the pilot:** Denied anonymous/cross-tenant access, token expiry/revocation, tamper rejection, mandatory transactional audit and candidate-bound separate approval are demonstrated. Enterprise identity, provider billing enforcement, disaster-recovery exercises and independent review remain conditions.

## 4. Architect's Action Directive

1. Keep this release confined to the documented supervised Python-function pilot; keep legacy services out of its execution path.
2. Repair/retire all legacy authorization, containment and simulated-verification bypasses before claiming full MAS readiness.
3. Move hostile/public workers to infrastructure supporting the stronger isolation profile, then reproduce escape/tenant-separation and failure tests there.
4. Add enterprise identity, external audit anchors, key lifecycle, aggregate budgets and durable worker reconciliation.
5. Expand the live Gemini evaluation and sustained-load/crash corpus with agreed numerical acceptance thresholds.
6. Resolve full-suite failures and skipped required integration checks; observe real CI and obtain independent review.
7. Resubmit the exact implementation and fresh evidence for the **10/10** target. The current result earns a scoped **8/10**, not the requested final certification.
