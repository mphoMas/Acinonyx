# Exact evidence supporting rework diagnostic findings

Source-document revision: `be965a9df2bb71134d03b6d7175e0a7c64263f8d`. Historical review observations; not rerun for this document update.

## E01 — Incomplete enforcement: planning authority

Reviewed candidate: `7bcdd079e484539545bc5661b6654ac6b0489b7e`.

> 1. **Name-based unbound planning permission persists.** `mas/pm/tools.py` admits a whitelist of principal names and suffixes `:architect` or `:tenant_admin` without verified role/scopes. Disposable reproduction: `ExecutionContext.scope('unprivileged:tenant_admin')` successfully publishes through `pm_publish_plan` with no tenant binding. This is a local entry-point reproduction, not a demonstrated remote exploit. **Fix:** deny unbound exposed publication or validate explicit trusted authority independently of the name; test both allowed-looking names and suffixes.

Interpretation: A permitted-looking identity suffix remained sufficient to publish without verified authority. This supports an incomplete authorization-boundary finding, not a claim of a remote exploit.

[Original review, line 19](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_02_REVIEW_3.md#L19)

## E02 — Related-path failure: active reviewer removal

Reviewed candidate: `148ad03403887c8a63471553ecc192060ba072e1`.

> 1. **Active reviewer removal changes live policy.** In `mas/pm/plans.py`, a change from a nonempty reviewer requirement to `None` sets `staged_rev=None`, but `effective_rev` uses `staged_rev is not None` as its staging discriminator. Independent reproduction: create a task requiring `independent`, mark it IN_PROGRESS, then publish a revision with no reviewer requirement. Stored live reviewer becomes null, pending reconciliation true, staged reviewer null. The pending transition guard helps, but the live policy is already erased. **Fix:** represent staged removal explicitly; preserve live policy for every active change, including null/empty values; test authorized application and rejection of the proposal.

Interpretation: The first scope-staging correction did not cover null/removal semantics. This is a concrete edge case under the same preservation requirement.

[Original review, line 15](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_01_SBA_03_RESUBMISSION_REVIEW.md#L15)

## E03 — Failure testing: browser records not asserted

Reviewed candidate: `d19b0924a67edbd0e82d54f385e01031a89a5a43`.

> 4. **Browser acceptance evidence does not assert the claimed records.** record_browser_evidence.py appends “Board rendered live issues SBA-1 and SBA-2” without checking cards or project content. It also seeds DONE/IN_PROGRESS directly as display fixtures, not independently verified workflow states. Independent rerun printed success although the screenshot showed no projects. Fix: explicitly assert expected project, card keys and count; label fixtures synthetic and never use seeded DONE as workflow proof. Add actual create/transition/revocation interaction tests through the same tenant-bound browser. Correct BROWSER_EVIDENCE_REPORT.md and delivery claims around the failing candidate.

Interpretation: The recorded success claim was not backed by an assertion of the expected project/cards. This explains how a failing board could accompany a positive report.

[Original review, line 19](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/SBA_02_05_REWORK_REVIEW.md#L19)

## E04 — Failure testing: forged receipt expected to pass

Reviewed candidate: `fc4886cd99ec2c5ad05615026bdd1807cac2f883`.

> 1. **Forged receipts obtain trusted admission.** `admit_evidence_receipt` only checks mutation authority and SUBMITTED state; it never validates key ID/signature, full envelope or run/attempt/candidate ownership. Independent reproduction stores signature `forged` and unknown key with arbitrary payload, then promotes it successfully. The current test_negative_case_8 explicitly expects the forged record to become ADMITTED under trusted scope, so it proves permission gating rather than authenticity. **Required solution:** if the coordinator verifier is deferred, keep promotion disabled with a fail-closed error and retain SUBMITTED status. Otherwise implement verification against approved issuer keys and complete canonical identity envelope before one atomic promotion; use a distinct admission capability. Change the test to reject fake signatures even for an authorized observer. Authorization is not authenticity.

Interpretation: The test verified authority gating while expecting admission of unauthenticated content. It therefore tested a weaker property than evidence authenticity.

[Original review, line 15](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_03_REVIEW_3.md#L15)

## E05 — Historical integration: migration ledger bypass

Reviewed candidate: `fc4886cd99ec2c5ad05615026bdd1807cac2f883`.

> 2. **Migration ledger bypasses upgrades already marked applied.** Revised DDL keeps version 2026101201 and the same checksum label. When that entry exists, migration returns before inspecting/rebuilding missing structures. Independent reproduction uses actual historical code in sequence: 284cb877 database -> 9c2de7a8 migration -> current candidate. receipt table still lacks admission_status. **Required solution:** freeze historical migration identities and add a NEW version for correction. Under BEGIN IMMEDIATE, validate actual schema and rebuild/alter missing structures with data preservation. Compute a real migration-content checksum. Test this exact upgrade chain with populated runs/events/receipts and ledger, plus injected rollback and reopen. Do not edit or silently delete the old ledger to make tests pass.

Interpretation: Testing a fresh schema did not cover the actual already-applied migration chain. The review names the historical sequence explicitly.

[Original review, line 17](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_03_REVIEW_3.md#L17)

## E06 — Replay integrity: changed termination content accepted

Reviewed candidate: `fc4886cd99ec2c5ad05615026bdd1807cac2f883`.

> 3. **Conflicting termination receipt replay accepted.** Replay compares run_id/attempt_id only. Independent reproduction: record termination receipt `term` with exit -15/spend 2, replay same ID with exit 0/spend 9; returns true. Canonical stored termination payload lacks spending and full receipt identity; synthetic `sig:system:observer` is written as ADMITTED, task_id is populated with attempt_id. **Required solution:** use a separate trusted observation record or a real signed envelope, never placeholder cryptographic proof. Persist full normalized intent/run/attempt/generation/exit/status/spend/observer receipt content and canonical digest. Identical replay returns original outcome; any changed field rejects without accounting or state changes. Derive task identity from the persisted mapping. Verify observer authority separately from generic storage write.

Interpretation: Matching record identity alone did not establish identical observation content. This is a replay-integrity gap, not a distinct measured labor percentage.

[Original review, line 19](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_03_REVIEW_3.md#L19)

## E07 — Mechanism–guarantee mismatch: execution survives stop

Reviewed candidate: `f6d2f34a7f7c72872d10769177ae06f1fe2315a2`.

> 1. **Adapter execution survives a timeout.** Worker supervision still uses a daemon Python thread and a cooperative event. After timeout it records UNKNOWN_EXECUTION and returns, without joining/terminating adapter execution. The new uncooperative test only checks absence of an event immediately; it does not observe later filesystem effects or surviving execution. Independent controlled adapter ignores stop, sleeps .2 seconds, then writes a real disposable file. Worker returned at .038 seconds for a .03-second deadline; the file appeared after return. Holds remain retained, which is correct, but does not establish bounded execution containment. **Required fix:** either restrict CC-04 to an explicitly enforced set of qualified controlled adapters, rejecting unsupported stop capabilities, or run adapter work in an actually terminable supervised execution boundary. Observe termination within cleanup deadline; reject/quarantine late IPC results/events; unknown remote effects retain holds. Tests must wait past the side-effect deadline and inspect execution survival. Do not describe event suppression as cancellation of external effects.

Interpretation: The persisted UNKNOWN_EXECUTION state and retained hold were correct, but they did not stop the physical side effect. The timing probe demonstrates the distinction.

[Original review, line 13](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_04_REVIEW_3.md#L13)

## E08 — Repeated correction: registered configuration bypass

Reviewed candidate: `07294b0fb74d4073b9cd2315cc0f60f35fc9ab38`.

> **Registered adapter has unsafe test escape hatches.** SyntheticExecutionAdapter accepts ignore_stop_signal=True and an arbitrary on_stop callback. Worker registration validates class identity but not these options. Independent reproduction uses the exact registered class, duration .2, ignore_stop_signal=True, callback writing a disposable file, execution timeout .01 and cleanup .01. Worker returns .026 seconds; file is absent on return and present afterward. Intent honestly remains UNKNOWN_EXECUTION and budget uncertainty is retained, but local execution still survives its admitted boundary.

Interpretation: A class registry addressed implementation identity, but options in that very class defeated termination. This supports the symptom-versus-invariant diagnosis.

[Original review, line 13](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_04_REVIEW_5.md#L13)

## E09 — Evidence integrity: printed tests treated as execution

Reviewed candidate: `b4db4a7d1dd3d65273810899341ff0cb2b5178d7`.

> 2. **Issue:** `VerifierAdapter.verify_candidate` derives executed count from a regex over arbitrary stdout. Candidate checkout does not isolate code or protect the verifier environment/files; base commit is copied without validation. **Impact:** manufactured test text becomes signed production evidence, and candidate code executes with verifier-host authority. **Reproduction:** the submitted fixture's Python command prints `1 passed in 0.01s` without running any tests; independent execution produces signed `passed=True`. **Remediation:** use an owner-controlled, immutable test contract and verifier-owned runner/results channel outside candidate control; bind suite/image/base/candidate/fence and actual measured outcomes. Run untrusted code in an enforceable restricted boundary with no verifier secrets or shared writable control files. A worktree alone is not that boundary.

Interpretation: Checkout did not make candidate-controlled stdout trustworthy. The recorded probe ran no tests but produced a signed passing result.

[Original review, line 14](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_05_06_REWORK_REVIEW.md#L14)

## E10 — Atomic enforcement: launch policy race

Reviewed candidate: `f6d2f34a7f7c72872d10769177ae06f1fe2315a2`.

> 2. **Policy authorization races pre-spawn.** Worker reads current policy in a separate operation, then calls pre_spawn_intent whose atomic update does not revalidate admitted policy/version/pending reconciliation. Independent controlled interleaving updates issue policy from 1 to 2 immediately before the actual pre-spawn call; worker executes and completes using the admitted old payload. **Required fix:** inside the pre-spawn transaction, re-read issue policy, pending reconciliation, admitted scope/funded authorization and eligible workflow state. Require the exact admitted policy in the guarded launch update; insert the run and update attempt only after that same decision succeeds. Policy changes after launch must revoke/fence active authority before admitting stale results; define safe interruption/reconciliation rather than merely matching a previously fetched object. Add competing plan update/pre-spawn and pending-reconciliation regressions.

Interpretation: A separately checked policy could change before launch. Permission must participate in the atomic launch decision.

[Original review, line 15](https://github.com/mphoMas/Acinonyx/blob/be965a9df2bb71134d03b6d7175e0a7c64263f8d/projects/scrum-board-automation/planning/CC_04_REVIEW_3.md#L15)

