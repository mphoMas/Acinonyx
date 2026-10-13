# Reducing Rework in Acinonyx’s Multi-Agent Development Process

Evidence-based case study and applicable delivery improvement plan

Version 1.1 | 13 October 2026 | Retrospective findings complete for the stated sample; intervention validation pending

## Executive summary

Acinonyx seeks a delivery workflow in which the owner communicates goals to one coordinator, agents perform work with focused context, independent checks establish the result, and corrections and handoffs proceed without routine owner relay. The observed development process has not consistently achieved that outcome. Selected implementations repeatedly required correction before scoped acceptance.

Across five selected Antigravity implementation packages reviewed by Codex, nineteen submission rounds were recorded: five initial submissions and fourteen follow-ups. Seventeen submissions were rejected and two conditionally accepted. These quantities describe recorded review outcomes, not incorrect-code percentages, engineering hours or universal provider performance. Three implementation sequences subsequently involved Codex corrections, making final delivery a cross-agent outcome.

The strongest evidence supports incomplete enforcement across related paths, checks that tested weaker properties than claimed, and mechanisms that did not establish the promised guarantee. Evolving specifications, environment limitations and reviewer/reporting errors are also documented contributors. The applicable response is a shared, versioned acceptance target; early mechanism review; coherent increments; complete finding closure; independent adverse-case checks; and a recurrence pause. Four refinements make this operational: shared checks, readiness screening, challengeable reviewer decisions and explicit recurrence reassessment.

The case study recommends adopting the lightweight process immediately within authorized work, then validating it on a defined pilot. It does not claim the interventions have already reduced rejection or that automated coordinator enforcement has been implemented.

## 1. Problem and intended outcome

The delivery process repeatedly produces submissions that appear complete but fail independent acceptance. Corrections sometimes close the reported example while leaving related operations, states or configurations open. This creates repeat implementation, review and retesting and leaves the owner coordinating messages.

The problem to solve is complete, verifiable requirement closure with fewer correction cycles and less owner intervention, while preserving independent quality controls. The objective is not zero rejection: justified rejection remains necessary when a real blocker exists. Acceptance refers to a defined development scope; it is not automatically production release.

## 2. Research questions

1. How much repeat submission activity is documented in the selected packages?
2. Which failure families persist after correction, and what mechanisms explain that persistence?
3. Which findings represent original violations, specification changes, infrastructure limitations or reviewer errors?
4. Which concrete workflow controls could prevent recurrence without weakening acceptance?
5. How will improvements be measured without moving or hiding repeat work upstream?

## 3. Scope, sources and method

The corpus was collected from the Acinonyx repository after fetching current origin branch heads. It preserves 186 reachable commits and patches, three GitHub PRs with available reviews/conversations, 138 document snapshots, 21 uploaded transcripts and 188 existing evidence files, plus available issues, Actions metadata and repository events. Five hundred and sixty original source-file hashes were checked. Later analysis files are additions, not part of that original collection count.

The review denominator is five selected security-heavy implementation packages, not every repository task. Combined SBA-02/05 and CC-05/06 deliveries count once per review round. A submission is a candidate presented for review, not every commit or push. Conditional acceptance counts only within its stated scope. Design/discovery decisions are not implementation acceptance. Author tests are not independent review.

Method: construct candidate-linked sequences; associate rejection findings with later corrections; identify recurring rule families; preserve exact excerpts and distinguish observation from causal interpretation. Thirteen remediation candidates and eight overlapping issue families were selected for detailed tracing. Uploaded transcript pointers are supplemental claims, not automatically measured evidence. No unavailable hours are estimated.

## 4. Baseline results

| Package | Submissions | Follow-ups | Rejected | Outcome in counted sequence |
|---|---:|---:|---:|---|
| SBA-02/05 | 3 | 2 | 2 | Conditional development acceptance |
| SBA-03 | 5 | 4 | 5 | Later Codex correction; standalone final package acceptance not counted |
| CC-03 | 3 | 2 | 3 | Later Codex correction independently accepted separately |
| CC-04 | 6 | 5 | 5 | Conditional synthetic-only acceptance |
| CC-05/06 | 2 | 1 | 2 | Later Codex correction partially accepted; runtime pending |
| Total | 19 | 14 | 17 | Selected retrospective sequence |

First-recorded-review acceptance: 0/5. Rejected submissions: 17/19 = 89.5%. Follow-up round proportion: 14/19 = 73.7%. These are descriptive fractions. They do not establish a statistically representative error margin or 73.7% wasted effort. The selected sequences are incomplete for some final outcomes; do not compare nineteen historical rounds with a fully accepted future cohort as if endpoint coverage were equal.

The Codex comparison is not balanced: two corrective packages received first-recorded-review acceptance and one further package received partial offline acceptance. Corrective tasks benefit from prior failure analysis and differ from original implementation. Remaining Codex recovery fixes and pending runtime review rule out a general zero-defect claim.

## 5. Diagnostic findings and causal interpretation

### 5.1 Incomplete boundary closure

Planning authorization appeared across four review observations. Active-policy preservation appeared across two. Null reviewer removal and alternate authorization paths escaped earlier corrections. The supported diagnosis is incomplete enforcement of a shared invariant, rather than all code being wrong. The evidence does not reveal the model’s internal reasoning.

### 5.2 Tests measured a weaker property

A forged receipt test expected promotion under trusted scope; a delayed-effect check ended too early; a browser report asserted populated tickets without checking cards; stdout resembling pytest output became signed passing evidence. These examples explain how passing suites and rejection can coexist. The remedy is a test that can falsify the actual claimed guarantee.

### 5.3 Mechanism did not establish the guarantee

CC-04 progressed from cooperative execution control to declared capability, then exact-class registration, then configuration qualification. Physical execution still survived in intermediate candidates. A valid uncertainty record is not confirmed termination; a worktree is not isolation; a signature cannot turn an unmeasured claim into truth.

### 5.4 Historical and concurrent integration gaps

Fresh database behavior did not cover previous migration ledgers. Separate policy checks could race launch authorization. These are boundary conditions that happy-path tests do not establish. Upgrade chains and competing operations must be tested against the same invariant.

### 5.5 Specification and environment contributors

Reviews clarified version binding, strict types, supported adapter scope and required evidence. Initial omissions cannot all be attributed to the implementer without comparing the requirement baseline. Missing Docker is infrastructure; claiming its tests ran is a reporting error. Context quality and concurrency are plausible additional contributors that need prospective measurement.

### 5.6 Review accountability and owner dependency

The revised Antigravity review of Codex CC-05/06 withdrew incorrect count and container-verification claims. Reviewers can therefore introduce error as well as detect it. Transcripts establish repeated owner-mediated handoffs, but not a causal percentage for code defects. Reviewer consistency, shared agent assumptions, premature completion incentives and proportionality must be controlled on both sides.

## 6. Proposed solution: one shared acceptance workflow

The six interventions and four refinements form one process; automated enforcement is its future implementation, not a separate remedy or an existing capability.

### 6.1 Versioned acceptance contract and shared checks

Coordinator and reviewer translate the goal into requirement IDs, invariant statements, permitted scope, code baseline, known positive/adverse checks and evidence expectations. The implementer confirms understanding. Record additions as scope changes; a new test exposing an existing rule is not automatically a new requirement. Owner approval is needed for relevant business changes, not every technical clarification.

### 6.2 Early review of the enforcement mechanism

Before substantial code, explain how critical rules hold under failure. Reviewer challenges the boundary for identity, funds, isolation, evidence and recovery. A short frontend task uses a brief check; critical control work uses a failure matrix. Resolve mechanism mismatch before implementation, rather than add lengthy design bureaucracy to every task.

### 6.3 Coherent increments with end-to-end accountability

Prove one meaningful behavior at a time, with named owner and interface. Each increment demonstrates real behavior. Retain a final integration gate and the approval-ready workflow objective; smaller tickets must not become an excuse for indefinite component work.

### 6.4 Complete finding closure and readiness screening

Implementer maps each requirement/finding to all affected operations, states/configurations, changed or inspected paths, actual checks and remaining gaps. Coordinator checks completeness before full review. A readiness return is counted, not hidden. Screening does not certify correctness or authorize self-approval.

### 6.5 Independent failure checks and challengeable decisions

Reviewer tests adverse cases independently on the exact candidate and qualified environment. Each blocker cites the requirement/version, reproduction or missing essential evidence, impact and closure test. Implementer can challenge facts, applicability or severity. Resolve technical disagreement before another patch; unresolved business/scope decisions go to the owner. Optional improvements do not silently become blockers.

### 6.6 Recurrence pause and concrete corrective plan

When a claimed-closed invariant fails again, pause the local patch cycle. Reassess mechanism, paths, brief and tests jointly. Record a corrective plan and then resume. Do not waive a real defect because retries are costly. Final acceptance remains independent, and release authority remains unchanged.

## 7. Responsibilities and decision rules

| Role | Responsibility | Must not do |
|---|---|---|
| Owner | Business direction, scope decisions and required release approval | Act as routine message courier |
| Coordinator | Brief/context integrity, prerequisites, handoffs, readiness and record completeness | Treat metadata completeness as proof of correctness |
| Implementer | Scoped change, pre-submission checks and complete closure evidence | Approve its own candidate |
| Reviewer/verifier | Independent evidence and justified scoped decisions | Introduce undisclosed requirements as original defects or claim unrun tests |
| Integration owner | Preserve exact candidate/base and concurrent work; recheck resulting candidate | Transfer acceptance to changed integrated code automatically |

Decision records distinguish accepted scope, original violation, new scope, infrastructure gap, reviewer/reporting error and incomplete closure. Review may require essential missing evidence without an executable reproduction, but must explain why that evidence is necessary. If no independent reviewer is available, record pending review; author tests do not close that gap.

## 8. Practical records and templates

Task brief: task/package ID; one owner; separate reviewer; repository/base SHA; allowed files; requirement version; invariants; known checks; environment prerequisites; dependencies; limits and scope-change log.

Submission: immutable candidate/base; author identity; requirement/finding coverage; actual commands and outcomes; evidence locations/digests; failures/skips; uncertainty; related paths inspected; remaining limitations.

Finding: ID and rule family; candidate; requirement/version; severity; reproduction or missing essential evidence; expected/observed behavior; impact; classification; dispute and resolution; required closure checks.

Closure: finding ID; related entry points/states/configuration; mechanism change; tests of original and related failure paths; new candidate; reviewer disposition.

Readiness-return and recurrence-pause labels are prospective record categories, not deployed PM FSM/API states. Use documents/manual records initially; do not introduce new live state transitions without compatible contracts.

## 9. Adoption and automation roadmap

1. Adopt the checklist for the next scoped task. Produce an agreed brief and shared checks; keep the original acceptance standard.
2. Run a small connected task through implementation, readiness and independent review. Record each return, challenge and correction, including work discovered before formal review.
3. Extend to a five-package pilot, grouping tasks by frontend, backend/data and critical-control risk. Record incomplete tasks as pending; do not drop them from reporting.
4. Implement coordinator record validation and idempotent handoff controls only after the process fields and interface are agreed. Existing IAM, funding and durable-state boundaries remain enforced. Do not duplicate SBA tasks or silently change statuses.
5. Qualify automation against missing/stale briefs, mismatched candidates, incomplete evidence, revoked authority, disputed findings, repeated failures, crashes and duplicate events. Uncertain work pauses; no blind replay or extra funding.
6. Decide whether to retain, revise or stop an intervention based on the pilot. No production activation is authorized by this case study.

## 10. Pilot measurement and safeguards

| Measure | Definition | Interpretation |
|---|---|---|
| First-pass acceptance | First submissions accepted within explicit scope / adjudicated first submissions | Separate full and conditional decisions; report pending denominator |
| Follow-up proportion | Follow-up formal rounds / total formal rounds | Not hours or code error |
| Total repeat episodes | Readiness returns, correction rounds and design revisions, with episode IDs | Avoid counting the same episode twice across categories |
| Recurrence | Previously claimed-closed rule observed again | Distinguish new scope and new manifestations |
| Rounds to acceptance | Total recorded rounds through scoped acceptance per completed package | Report pending and cross-builder work separately |
| Owner intervention | Routine relay/coordination actions per package | Exclude intended business/release decisions, record other human involvement |
| Quality safeguard | Confirmed post-acceptance requirement violations | Use a consistent 14-day observation window, not zero incidents as proof of zero risk |

A 50% reduction in follow-up rounds is an exploratory target, not a result or forecast. The historical 14 follow-ups gives illustrative scenarios of 10, 7 or 4 follow-ups (29%, 50%, 71% reductions), but incomplete historical endpoints prevent direct efficacy claims. Establish a comparable prospective baseline. Hours remain excluded. Count stronger upfront checking as work rather than pretend it is free.

Retain an intervention if comparable packages show lower recurrence and routine owner intervention without weaker evidence or increased confirmed post-acceptance violations. If the sample is mixed, small or still pending, extend measurement rather than claim success. Revise added ceremony if it merely shifts repeated work upstream. Publish every failure and unresolved case.

## 11. Limitations and alternative explanations

This is a single-project retrospective with a purposive sample and author involvement in review. Reviewer selection and confirmation bias are possible. Git author metadata cannot reliably identify the agent. Uncommitted/deleted/remote session material, provider spending and hours are incomplete. Original requirement attribution is unresolved for some findings. Environment and task complexity differ. Recurring families overlap. A code defect, a reporting error and a new requirement are not interchangeable.

The case study demonstrates recorded failures and supports specific mechanisms; it does not establish provider rankings, exact causal contribution percentages or proven reduction from the proposed intervention. A separate reviewer should challenge the study and pilot classifications before commercial or scientific claims.

## 12. Conclusion and applicability

The observed rework is not primarily resolved by asking the owner to write better prompts. Technical translation, enforcement-design selection, failure testing and closure discipline belong to the delivery process. The practical remedy is to make acceptance shared and explicit before work, preserve independent judgment at the end, and stop repeated symptom patching when an invariant remains open.

The retrospective case study is complete for its declared scope. Its solution is ready for a controlled application trial; effectiveness and automated enforcement remain pending. Success means fewer avoidable repeats and less owner coordination with trustworthy accepted results, not simply a lower rejection count.

## Appendix A. Evidence and source register

Exact excerpts, original review lines and candidate identities follow. These are historical recorded reproductions, not newly executed tests. They must not be presented as unresolved defects in the current revision without checking current code.

### E01 — Incomplete enforcement: planning authority

Reviewed candidate: `7bcdd079e484539545bc5661b6654ac6b0489b7e`.

> 1. **Name-based unbound planning permission persists.** `mas/pm/tools.py` admits a whitelist of principal names and suffixes `:architect` or `:tenant_admin` without verified role/scopes. Disposable reproduction: `ExecutionContext.scope('unprivileged:tenant_admin')` successfully publishes through `pm_publish_plan` with no tenant binding. This is a local entry-point reproduction, not a demonstrated remote exploit. **Fix:** deny unbound exposed publication or validate explicit trusted authority independently of the name; test both allowed-looking names and suffixes.

Interpretation: A permitted-looking identity suffix remained sufficient to publish without verified authority. This supports an incomplete authorization-boundary finding, not a claim of a remote exploit.

[Original review, line 19](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_02_REVIEW_3.md#L19)


### E02 — Related-path failure: active reviewer removal

Reviewed candidate: `148ad03403887c8a63471553ecc192060ba072e1`.

> 1. **Active reviewer removal changes live policy.** In `mas/pm/plans.py`, a change from a nonempty reviewer requirement to `None` sets `staged_rev=None`, but `effective_rev` uses `staged_rev is not None` as its staging discriminator. Independent reproduction: create a task requiring `independent`, mark it IN_PROGRESS, then publish a revision with no reviewer requirement. Stored live reviewer becomes null, pending reconciliation true, staged reviewer null. The pending transition guard helps, but the live policy is already erased. **Fix:** represent staged removal explicitly; preserve live policy for every active change, including null/empty values; test authorized application and rejection of the proposal.

Interpretation: The first scope-staging correction did not cover null/removal semantics. This is a concrete edge case under the same preservation requirement.

[Original review, line 15](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_01_SBA_03_RESUBMISSION_REVIEW.md#L15)


### E03 — Failure testing: browser records not asserted

Reviewed candidate: `d19b0924a67edbd0e82d54f385e01031a89a5a43`.

> 4. **Browser acceptance evidence does not assert the claimed records.** record_browser_evidence.py appends “Board rendered live issues SBA-1 and SBA-2” without checking cards or project content. It also seeds DONE/IN_PROGRESS directly as display fixtures, not independently verified workflow states. Independent rerun printed success although the screenshot showed no projects. Fix: explicitly assert expected project, card keys and count; label fixtures synthetic and never use seeded DONE as workflow proof. Add actual create/transition/revocation interaction tests through the same tenant-bound browser. Correct BROWSER_EVIDENCE_REPORT.md and delivery claims around the failing candidate.

Interpretation: The recorded success claim was not backed by an assertion of the expected project/cards. This explains how a failing board could accompany a positive report.

[Original review, line 19](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/SBA_02_05_REWORK_REVIEW.md#L19)


### E04 — Failure testing: forged receipt expected to pass

Reviewed candidate: `fc4886cd99ec2c5ad05615026bdd1807cac2f883`.

> 1. **Forged receipts obtain trusted admission.** `admit_evidence_receipt` only checks mutation authority and SUBMITTED state; it never validates key ID/signature, full envelope or run/attempt/candidate ownership. Independent reproduction stores signature `forged` and unknown key with arbitrary payload, then promotes it successfully. The current test_negative_case_8 explicitly expects the forged record to become ADMITTED under trusted scope, so it proves permission gating rather than authenticity. **Required solution:** if the coordinator verifier is deferred, keep promotion disabled with a fail-closed error and retain SUBMITTED status. Otherwise implement verification against approved issuer keys and complete canonical identity envelope before one atomic promotion; use a distinct admission capability. Change the test to reject fake signatures even for an authorized observer. Authorization is not authenticity.

Interpretation: The test verified authority gating while expecting admission of unauthenticated content. It therefore tested a weaker property than evidence authenticity.

[Original review, line 15](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_03_REVIEW_3.md#L15)


### E05 — Historical integration: migration ledger bypass

Reviewed candidate: `fc4886cd99ec2c5ad05615026bdd1807cac2f883`.

> 2. **Migration ledger bypasses upgrades already marked applied.** Revised DDL keeps version 2026101201 and the same checksum label. When that entry exists, migration returns before inspecting/rebuilding missing structures. Independent reproduction uses actual historical code in sequence: 284cb877 database -> 9c2de7a8 migration -> current candidate. receipt table still lacks admission_status. **Required solution:** freeze historical migration identities and add a NEW version for correction. Under BEGIN IMMEDIATE, validate actual schema and rebuild/alter missing structures with data preservation. Compute a real migration-content checksum. Test this exact upgrade chain with populated runs/events/receipts and ledger, plus injected rollback and reopen. Do not edit or silently delete the old ledger to make tests pass.

Interpretation: Testing a fresh schema did not cover the actual already-applied migration chain. The review names the historical sequence explicitly.

[Original review, line 17](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_03_REVIEW_3.md#L17)


### E06 — Replay integrity: changed termination content accepted

Reviewed candidate: `fc4886cd99ec2c5ad05615026bdd1807cac2f883`.

> 3. **Conflicting termination receipt replay accepted.** Replay compares run_id/attempt_id only. Independent reproduction: record termination receipt `term` with exit -15/spend 2, replay same ID with exit 0/spend 9; returns true. Canonical stored termination payload lacks spending and full receipt identity; synthetic `sig:system:observer` is written as ADMITTED, task_id is populated with attempt_id. **Required solution:** use a separate trusted observation record or a real signed envelope, never placeholder cryptographic proof. Persist full normalized intent/run/attempt/generation/exit/status/spend/observer receipt content and canonical digest. Identical replay returns original outcome; any changed field rejects without accounting or state changes. Derive task identity from the persisted mapping. Verify observer authority separately from generic storage write.

Interpretation: Matching record identity alone did not establish identical observation content. This is a replay-integrity gap, not a distinct measured labor percentage.

[Original review, line 19](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_03_REVIEW_3.md#L19)


### E07 — Mechanism–guarantee mismatch: execution survives stop

Reviewed candidate: `f6d2f34a7f7c72872d10769177ae06f1fe2315a2`.

> 1. **Adapter execution survives a timeout.** Worker supervision still uses a daemon Python thread and a cooperative event. After timeout it records UNKNOWN_EXECUTION and returns, without joining/terminating adapter execution. The new uncooperative test only checks absence of an event immediately; it does not observe later filesystem effects or surviving execution. Independent controlled adapter ignores stop, sleeps .2 seconds, then writes a real disposable file. Worker returned at .038 seconds for a .03-second deadline; the file appeared after return. Holds remain retained, which is correct, but does not establish bounded execution containment. **Required fix:** either restrict CC-04 to an explicitly enforced set of qualified controlled adapters, rejecting unsupported stop capabilities, or run adapter work in an actually terminable supervised execution boundary. Observe termination within cleanup deadline; reject/quarantine late IPC results/events; unknown remote effects retain holds. Tests must wait past the side-effect deadline and inspect execution survival. Do not describe event suppression as cancellation of external effects.

Interpretation: The persisted UNKNOWN_EXECUTION state and retained hold were correct, but they did not stop the physical side effect. The timing probe demonstrates the distinction.

[Original review, line 13](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_04_REVIEW_3.md#L13)


### E08 — Repeated correction: registered configuration bypass

Reviewed candidate: `07294b0fb74d4073b9cd2315cc0f60f35fc9ab38`.

> **Registered adapter has unsafe test escape hatches.** SyntheticExecutionAdapter accepts ignore_stop_signal=True and an arbitrary on_stop callback. Worker registration validates class identity but not these options. Independent reproduction uses the exact registered class, duration .2, ignore_stop_signal=True, callback writing a disposable file, execution timeout .01 and cleanup .01. Worker returns .026 seconds; file is absent on return and present afterward. Intent honestly remains UNKNOWN_EXECUTION and budget uncertainty is retained, but local execution still survives its admitted boundary.

Interpretation: A class registry addressed implementation identity, but options in that very class defeated termination. This supports the symptom-versus-invariant diagnosis.

[Original review, line 13](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_04_REVIEW_5.md#L13)


### E09 — Evidence integrity: printed tests treated as execution

Reviewed candidate: `b4db4a7d1dd3d65273810899341ff0cb2b5178d7`.

> 2. **Issue:** `VerifierAdapter.verify_candidate` derives executed count from a regex over arbitrary stdout. Candidate checkout does not isolate code or protect the verifier environment/files; base commit is copied without validation. **Impact:** manufactured test text becomes signed production evidence, and candidate code executes with verifier-host authority. **Reproduction:** the submitted fixture's Python command prints `1 passed in 0.01s` without running any tests; independent execution produces signed `passed=True`. **Remediation:** use an owner-controlled, immutable test contract and verifier-owned runner/results channel outside candidate control; bind suite/image/base/candidate/fence and actual measured outcomes. Run untrusted code in an enforceable restricted boundary with no verifier secrets or shared writable control files. A worktree alone is not that boundary.

Interpretation: Checkout did not make candidate-controlled stdout trustworthy. The recorded probe ran no tests but produced a signed passing result.

[Original review, line 14](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_05_06_REWORK_REVIEW.md#L14)


### E10 — Atomic enforcement: launch policy race

Reviewed candidate: `f6d2f34a7f7c72872d10769177ae06f1fe2315a2`.

> 2. **Policy authorization races pre-spawn.** Worker reads current policy in a separate operation, then calls pre_spawn_intent whose atomic update does not revalidate admitted policy/version/pending reconciliation. Independent controlled interleaving updates issue policy from 1 to 2 immediately before the actual pre-spawn call; worker executes and completes using the admitted old payload. **Required fix:** inside the pre-spawn transaction, re-read issue policy, pending reconciliation, admitted scope/funded authorization and eligible workflow state. Require the exact admitted policy in the guarded launch update; insert the run and update attempt only after that same decision succeeds. Policy changes after launch must revoke/fence active authority before admitting stale results; define safe interruption/reconciliation rather than merely matching a previously fetched object. Add competing plan update/pre-spawn and pending-reconciliation regressions.

Interpretation: A separately checked policy could change before launch. Permission must participate in the atomic launch decision.

[Original review, line 15](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_04_REVIEW_3.md#L15)



## Appendix B. All seventeen counted rejection records

1. SBA-02/SBA-05, round 1: [SBA_02_05_BACKEND_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/SBA_02_05_BACKEND_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
2. SBA-02/SBA-05, round 2: [SBA_02_05_REWORK_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/SBA_02_05_REWORK_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
3. SBA-03, round 1: [SBA_03_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/SBA_03_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
4. SBA-03, round 2: [CC_01_SBA_03_RESUBMISSION_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_01_SBA_03_RESUBMISSION_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
5. SBA-03, round 3: [CC_02_SBA_03_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_02_SBA_03_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
6. SBA-03, round 4: [CC_02_REVIEW_3.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_02_REVIEW_3.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
7. SBA-03, round 5: [CC_02_REVIEW_4.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_02_REVIEW_4.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
8. CC-03, round 1: [CC_03_INDEPENDENT_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_03_INDEPENDENT_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
9. CC-03, round 2: [CC_03_REWORK_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_03_REWORK_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
10. CC-03, round 3: [CC_03_REVIEW_3.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_03_REVIEW_3.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
11. CC-04, round 1: [CC_04_INDEPENDENT_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_04_INDEPENDENT_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
12. CC-04, round 2: [CC_04_REWORK_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_04_REWORK_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
13. CC-04, round 3: [CC_04_REVIEW_3.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_04_REVIEW_3.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
14. CC-04, round 4: [CC_04_REVIEW_4.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_04_REVIEW_4.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
15. CC-04, round 5: [CC_04_REVIEW_5.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_04_REVIEW_5.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
16. CC-05/CC-06, round 1: [CC_05_06_INDEPENDENT_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_05_06_INDEPENDENT_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.
17. CC-05/CC-06, round 2: [CC_05_06_REWORK_REVIEW.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/CC_05_06_REWORK_REVIEW.md). Antigravity implementation; Codex review. Other design/discovery verdicts in combined reviews are separate.

## Appendix C. Working sources

- [AGENT_DELIVERY_RELIABILITY_AUDIT.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/AGENT_DELIVERY_RELIABILITY_AUDIT.md)
- [AGENT_DELIVERY_AUDIT_LEDGER.json](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/AGENT_DELIVERY_AUDIT_LEDGER.json)
- [REWORK_CAUSE_ANALYSIS.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/REWORK_CAUSE_ANALYSIS.md)
- [REWORK_CAUSE_LEDGER.json](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/REWORK_CAUSE_LEDGER.json)
- [DELIVERY_READINESS_AND_REVIEW_CHECKLIST.md](https://github.com/mphoMas/Acinonyx/blob/9d053629d170c37ff2a6aff31c7c726c8e529bbd/projects/scrum-board-automation/planning/DELIVERY_READINESS_AND_REVIEW_CHECKLIST.md)

## Implementation addendum — 13 October 2026

The proposed process now has durable coordinator enforcement in code candidate `173f940d8e986520bec6f226beb090f80108649d`. The scope is explicitly enrolled projects; operational projects were not enrolled automatically. The service records brief/version agreement, dispatch binding, readiness returns, existing-requirement findings, scope decisions, challenges, recurrence pauses and independently signed acceptance. Low-level coordinator paths and premature PM completion cannot bypass the enrolled gate.

All five repository quality stages passed: 839 tests, zero failures or skips. Forty-seven process-gate cases are included, and the 113-test targeted run is a subset. The clean installed wheel demonstrated controlled synthetic execution and persisted readiness/completion guards outside the checkout. These checks qualify implementation behavior, not a measured reduction in rework or live end-to-end agent delivery.

Metadata screening cannot prove technical correctness; the existing qualified verifier contract and separate reviewer remain necessary. No new public endpoint, live provider admission, activity feed or automatic conversational producer was activated. Separate implementation acceptance and configured client/service integration remain pending. The next evaluation is a deliberately enrolled controlled pilot using the case-study metrics, without weakening existing gates or asking the owner to become the routine messenger.
