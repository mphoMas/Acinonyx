# Delivery Evidence and Handoff: Task GHA-01 (Corrected Specification)

Task: **GHA-01 — Define the GitHub Actions integration contract**
Branch: `feat/scrum-board-automation`
Implementation Owner: Antigravity Development Team
Architecture Reviewer: Codex
Date: 14 October 2026
Reviewed Baseline: `15e9f763` (incorporating `GHA_01_ARCHITECT_REVIEW.md` and `ANTIGRAVITY_GHA_01_CORRECTION_HANDOFF.md`)
Status: Corrected specification submitted for Codex architectural review.

---

## 1. Executive summary

In response to Codex's architectural review (`GHA_01_ARCHITECT_REVIEW.md`, verdict: *REJECTED (REQUIRES RE-WORK)* on candidate `6f620549`), Antigravity has revised the GitHub Actions integration contract, acceptance matrix, and delivery plan.

The revised documents eliminate the architectural gaps identified in the audit:
1. **Lifecycle alignment**: `DeliveryService.submit()` is strictly bound to an existing completed run in `AWAITING_SUBMISSION` or `READINESS_RETURNED`. Submitting from `READY` is eliminated. The distinction between resubmitting observations for the same candidate and launching a new candidate attempt is formally defined, and the missing readiness-to-ready transition is explicitly specified as proposed work (`retry_readiness`).
2. **Preservation of bounded verifier**: Canonical `suite_digest` remains strictly bound to `{source_path, cases}` under the existing solve(payload) verifier contract. Workflow, test harness, and runner image provenance are separated into distinct digests (`oracle_digest`, `runner_image_digest`). Candidate edits to tests are evaluated by an independently fixed base oracle, never modifying the evaluator.
3. **Authentication gateway specification**: Detailed the missing Authentication Gateway that validates GitHub OIDC JWTs against GitHub JWKS (issuer, audience, repository ID, workflow ref, expiry) and maps them to server-owned tenant sessions (`delivery:submit`). Confirmed that `MultiTenantIAM` does not directly consume GitHub JWTs and that no public OIDC endpoint currently exists.
4. **Source registry & idempotency ledger**: Designed `pm_source_events` to provide durable deduplication by `(action_id, payload_digest)` before side-effects, atomic PR-head freshness comparison (`pr_head_sha == candidate_commit_sha`) to prevent head-race conditions, and proper rerun semantics (`workflow_run_attempt > 1`).
5. **Valid GitHub Actions semantics**: Pinned immutable action commit SHAs and base oracle commit SHAs; separated the untrusted candidate runner from a dedicated, authorized *Trusted Check Publisher*; mapped coordinator states to valid GitHub Checks API `status` and `conclusion` enums.
6. **Bounded runtime and safe artifacts**: Reused the qualified `ContainerBoundary` (rootless, `--read-only`, `--network=none`, `--cap-drop=ALL`, no Docker socket, 1 MiB output truncation, recovery journal) and specified strict artifact limits (<=64 files, <=10 MiB uncompressed, <=2 MiB/file, safe relative POSIX paths, symlink/traversal rejection, completeness checks).
7. **Accurate threat boundary & classification**: All matrix controls are classified into `[Existing]`, `[Proposed]`, and `[Unsupported]`. Clarified that direct host SQLite file editing is an administrative action outside the software application boundary, while all supported PM methods and API entry points are strictly guarded.

All changes preserve the governing constraints:
- **No live workflows activated** under `.github/workflows/`.
- **No live adapters or cloud providers enabled**; worker registry remains synthetic-only.
- **No branch protection settings modified**.
- **No operational projects enrolled**.

---

## 2. Review findings closure table

| Finding ID & Summary | Revised Contract Section | Accountable Component | Negative Test Scenario & Expected Outcome |
|---|---|---|---|
| **B1: Runner lifecycle contradicts actual service phases** | Contract §7; Matrix G04 | `mas.pm.delivery.DeliveryService` [Existing] / `retry_readiness` [Proposed] | Calling `submit()` while task is in `READY`: raises `DeliveryGateError("Successful execution required before submission")`. Calling `require_dispatch()` in `READINESS_RETURNED`: raises `DeliveryGateError("Agreed, ready delivery brief required")`. |
| **B2: Suite digest conflated with git tree / general test oracle** | Contract §2.1, §3.2; Matrix G02 | `EvidenceTrust` [Existing] / `gha.runner` [Proposed] | Candidate PR modifies test assertions in `tests/`: runner executes `./trusted-oracle` from base ref; candidate edits do not modify executing assertions; unauthorized diff outside `brief.scope` triggers scope violation. |
| **B3: Missing authentication gateway & OIDC mapping** | Contract §5; Matrix Security | Authentication Gateway [Proposed] | Runner passes expired token, invalid audience, or token from untrusted repository/fork: gateway rejects request with HTTP 401 Unauthorized or `PermissionError`. |
| **B4: Lack of durable event idempotency & PR-head freshness** | Contract §6; Matrix G09, Freshness | Source Registry [Proposed] | Replaying an action with a modified payload digest: rejects with `IdempotencyConflictError`. Submitting a candidate commit when PR head has advanced: rejects with `CANDIDATE_SUPERSEDED`, Check Run marked `neutral`. |
| **B5: Invalid GitHub Actions & Checks API semantics** | Contract §9; Matrix Publication | Trusted Check Publisher [Proposed] | Runner token attempts direct check publication: GitHub API returns HTTP 403. Task in `RECURRENCE_PAUSED` or `CHANGES_REQUESTED`: Check Run conclusion published as `action_required`. |
| **Medium: Unqualified Docker flags** | Contract §4.2; Matrix Security | `ContainerBoundary` [Existing] | Candidate command attempts to access `/var/run/docker.sock` or host network: container denies access (`FileNotFoundError` / network unavailable). |
| **Medium: Unbounded artifact zip extraction** | Contract §8.1; Matrix Security | Artifact Ingestion Gateway [Proposed] | Submitting an archive with `../../etc/passwd`, symlinks, or truncated bytes: ingestion fails with `PathTraversalError` or digest mismatch; task transitions to `READINESS_RETURNED`. |
| **Medium: Direct SQL DONE threat boundary accuracy** | Contract §1.2; Matrix §1.2, G08 | `DeliveryService` / `mas.pm.db` [Existing] | Supported PM issue close attempted while in `IN_REVIEW`: raises `DeliveryGateError("Independent delivery acceptance required before DONE")`. Host DB file remains inaccessible to runners. |
| **Medium: Distinct failure states conflated with rejection** | Contract §7.2, §11; Matrix §1 | `mas.pm.delivery` [Existing] | Pre-review failure causes `READINESS_RETURNED` (not formal rejection). Rejection of previously closed defect causes `RECURRENCE_PAUSED`. New requirement causes `SCOPE_REQUESTED`. |
| **Medium: Out-of-scope blanket test denylist** | Contract §3.2; Matrix G02 | Runner scope checker [Proposed] | NUL-safe diff check (`git diff -z --name-status`) allows authorized test edits if present in `brief.scope`, while evaluating them strictly as candidate data. |
| **Low: Desktop file:// links & metadata inaccuracies** | Delivery Note §3; Contract header | Antigravity Documentation | Replace `file://` URIs with repo-relative paths; correct mandate date (13 October 2026); add explicit `[Existing]`, `[Proposed]`, `[Unsupported]` tags. |

---

## 3. Inspected interfaces and current implementation status

| Component / Interface | Path / Location | Classification | Implementation Status |
|---|---|---|---|
| `DeliveryBrief`, `Requirement`, `AcceptanceCheck` | `mas/pm/delivery.py` | **[Existing]** | Model validation requires 4 distinct actors, positive + adverse checks, bounded relative scope, mechanism explanation. |
| `DeliveryService` & Schema | `mas/pm/delivery.py` | **[Existing]** | Fully implemented and tested (47 tests passing). CAS revisions, readiness screening, recurrence pauses, challenges, scope requests, and immutable event ledger. Additive migration `2026101301`. |
| Gate Enforcement Hooks | `mas/pm/delivery.py` | **[Existing]** | `require_dispatch`, `record_dispatch`, `execution_phase`, `require_execution`, `require_review`, `require_accepted` guard intent pre-spawn and PM DONE transitions. |
| Service-Owned Evidence Trust | `mas/pm/adapters/admission.py`, `mas/pm/adapters/verifier.py` | **[Existing]** | `EvidenceTrust` validates cryptographic signatures. Bounded canonical `suite_digest` hashes `{source_path, cases}`. |
| Container Isolation Boundary | `mas/pm/adapters/boundary.py` | **[Existing]** | `ContainerBoundary` enforces rootless user, read-only rootfs, network isolation, output truncation, deadline timers, and recovery journal. |
| Authentication Gateway | *Not yet implemented* | **[Proposed]** | Validates GitHub OIDC JWTs against GitHub JWKS and maps repository + workflow ref to tenant ID and ephemeral `delivery:submit` session. |
| Source Registry & Event Ledger | *Not yet implemented* | **[Proposed]** | Stores `action_id`, `payload_digest`, `pr_head_sha`, and `workflow_run_attempt` in `pm_source_events` before execution for idempotency and freshness checks. |
| Readiness Retry Transition (`retry_readiness`) | *Not yet implemented* | **[Proposed]** | Transition from `READINESS_RETURNED` to `READY` for a new candidate attempt under the same brief version. |
| Trusted Check Publisher | *Not yet implemented* | **[Proposed]** | Privileged service mapping coordinator state to GitHub Checks API `status` and `conclusion` enums using GitHub App credentials. |
| Offline Manifest & Artifact Validator | *Not yet implemented* | **[Proposed (GHA-02)]** | Local CLI tool validating manifests and safe bounded artifacts against already completed private coordinator runs. |

---

## 4. Proposed GHA-02 scope: Offline manifest and artifact validator

Following Codex's review directive, the first implementation increment (**GHA-02**) is strictly scoped to an offline validator and collector:

### 4.1 Boundary and guarantees
- **Input**: An already completed, authorized coordinator run from private test fixtures (in phase `AWAITING_SUBMISSION` or `READINESS_RETURNED`).
- **Functionality**:
  1. Loads task brief and completed run from private SQLite fixture database.
  2. Inspects candidate diff against `DeliveryBrief.scope` using NUL-safe diff parsing.
  3. Validates bounded artifact archive: verifies file count (<=64), uncompressed sizes (<=2 MiB/file, <=10 MiB total), safe relative POSIX paths, absence of symlinks/hardlinks, and SHA-256 digests.
  4. Parses `CheckObservation` records and validates that all checks from `DeliveryBrief.checks` are present.
  5. Invokes `DeliveryService.submit()` within authenticated `tenant_scope`.
  6. Asserts resulting task phase (`READINESS_RETURNED` if any check failed or missing; `IN_REVIEW` if all checks passed and closures satisfied).
- **Strict exclusions**:
  - **No arbitrary shell command execution**.
  - **No live workflow deployment** or GitHub API calls.
  - **No production database enrollment or path overrides**.
  - **No trusted actor flags or test bypassing**.
  - **No general-repository trusted receipts issued**.
  - **No automatic paid dispatch**.

---

## 5. Ordered implementation backlog

The GitHub Actions integration will be delivered in 6 sequential work packages within the existing Scrum Board Automation (`SBA`) workstream:

| Package ID | Package Name | Delivery Owner | Dependencies | Description |
|---|---|---|---|---|
| **GHA-02** | Offline Manifest & Artifact Validator | **Antigravity** | GHA-01 accepted | Build `mas/pm/delivery_validator.py` and CLI to validate artifact bundles and manifests against completed fixture runs, calling `submit()` and reporting phase. |
| **GHA-03** | Authentication Gateway & Ingestion API | **Antigravity** | GHA-02 | Implement OIDC token validation, server-side repository/workflow mapping, and ephemeral scoped coordinator session issuance. |
| **GHA-04** | Source Registry & Event Idempotency Ledger | **Antigravity** | GHA-03 | Implement `pm_source_events` table, idempotency checks (`action_id`, `payload_digest`), PR-head freshness checks, and rerun tracking. |
| **GHA-05** | Trusted Check Publisher | **Antigravity** (Codex review) | GHA-04 | Implement privileged publisher service mapping coordinator delivery phases to GitHub Checks API `status` and `conclusion` enums. |
| **GHA-06** | Qualified Container Execution Harness | **Antigravity** | GHA-02 | Standardize rootless, networkless container check runner reusing `ContainerBoundary` and recovery journal for CI execution. |
| **GHA-07** | End-to-End Recovery & Rehearsal | **Antigravity** (Codex acceptance) | GHA-04, GHA-05, GHA-06 | Multi-attempt rehearsal on a private test project exercising readiness returns, recurrence pauses, challenge resolutions, and final acceptance. |

---

## 6. Notes for Codex's architectural review

We submit this corrected contract for Codex review. In particular, we invite confirmation on:
1. **Separation of bounded verifier and oracle digests**: Does keeping `VerificationContract.suite_digest` unchanged for solve contracts while adding `oracle_digest` for the base test harness resolve the trust boundary without breaking backwards compatibility?
2. **Readiness retry transition (`retry_readiness`)**: Does the proposed transition from `READINESS_RETURNED` back to `READY` (incrementing attempt sequence and preserving historical submissions) cleanly enable subsequent candidate attempts under an agreed brief?
3. **GHA-02 scope alignment**: Does the offline manifest/artifact validator against completed fixture runs provide the appropriate, safe initial increment before tackling the authentication gateway and event ledger?
