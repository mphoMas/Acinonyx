# GHA-01 architecture review

Reviewed 14 October 2026 (Africa/Johannesburg). Candidate: `6f620549`. Implementation/design owner: Antigravity. Reviewer: Codex. Scope: the integration specification, acceptance matrix and proposed first implementation increment; not a new independent acceptance of Codex's delivery-gate code.

## 1. Verdict & Executive Summary

**REJECTED (REQUIRES RE-WORK) as the governing implementation contract.** The submission maps the case-study remedies and preserves the no-activation restrictions. However, its runner lifecycle cannot execute against the current service, its verification/digest model exceeds the qualified contract, and OIDC, idempotency and PR-head freshness are described without the required interfaces. Correct these design points before implementation to avoid repeating the documented mechanism-versus-guarantee failures.

The protected-oracle direction, separate readiness/acceptance checks, durable metrics and explicit reviewer independence are retained. Passing the 47 existing process tests validates the unchanged baseline, not the new specification.

## 2. Architectural Audit & Critical Findings

### High severity — implementation blockers

**B1. Runner lifecycle contradicts actual service phases.** The proposed GHA-02 wrapper starts from READY, executes checks and calls submit (delivery note section 5). Actual `DeliveryService.submit` only permits AWAITING_SUBMISSION/READINESS_RETURNED and requires an existing successful run/attempt/intent linked to the current dispatch. The specification also depicts new execution from READINESS_RETURNED, while dispatch requires READY and no authorized return-to-READY path for that correction is specified. **Impact:** the first runnable increment fails before meaningful integration, or encourages inventing run rows/success. **Fix:** distinguish existing-run observation resubmission from changed-candidate execution. Define admission -> claim -> pre-spawn -> measured outcome -> submission, and list genuinely missing transitions as proposed work. No new run ID can substitute for coordinator ownership. First increment must collect/validate observations for an already authorized completed fixture run; no arbitrary check execution or fabricated production run.

**B2. Oracle and suite digest are incompatible with the existing trust contract.** Contract lines 63 and 73–82 define file-tree/harness hashes and general candidate tests. Existing `VerificationContract.suite_digest` hashes canonical `{source_path,cases}` and supports only host-compared bounded solve(payload) results. Trusted pytest files sharing an interpreter with untrusted candidate imports do not independently establish test truth; a checkout alone does not protect the oracle. **Impact:** digest mismatch and renewed manufactured-success risk. **Fix:** separate immutable workflow/harness/image provenance digests from the existing suite digest. Preserve current bounded verifier semantics for the first increment. General repository/browser verification requires its own qualification; unsigned CI observations cannot become trusted evidence. Candidate tests may be reviewed as proposed changes but never redefine the current oracle without separate accepted contract revision.

**B3. OIDC and credential separation are not specified sufficiently to implement.** Contract lines 129–136 imply MultiTenantIAM validates GitHub OIDC; it currently validates local issued sessions, not GitHub JWT/JWKS identity. Sections 4/5 prohibit coordinator tokens on runners yet describe a runner holding a submitting session and possibly direct service/database access. Builder and verifier identities are also conflated. **Impact:** inaccessible transport or overly privileged runner identity. **Fix:** define a separate trusted control-plane gateway as proposed, with issuer/audience/signature/expiry validation and server-owned mapping of repository ID, approved workflow revision/ref/environment to tenant/job/action. The guest never gets OIDC, GitHub, session or signing credentials. Verifier observation collection is not impersonation of the builder; require an explicit coordinator-controlled ingestion path. A secure host wrapper remains privileged infrastructure, not an ordinary candidate runner. No public OIDC endpoint exists today.

**B4. Immutable history/CAS are not durable event idempotency or PR-head freshness.** Contract lines 144–163 promise duplicate receipts and rejection of superseded commits. Existing submit compares the completed run with its submission, not GitHub's current PR head. Triggers prevent overwriting, not duplicate logical dispatch. Checking HEAD on the runner races server submission. **Impact:** duplicate paid work or acceptance of a superseded candidate. **Fix:** propose server-owned source registry and idempotency records with immutable repository/PR/head generation, workflow run/attempt, action kind, payload digest and result. Persist before launch; exact replay returns its original result, changed-payload replay rejects, interrupted effects remain uncertain. Atomically compare head generation with gate admission/acceptance; authenticate source updates and handle out-of-order events. GitHub final merge checks must still validate the current head/base or merge-group candidate.

**B5. Workflow/check publication semantics leave trust gaps.** The mutable `github.base_ref` alternative at line 75 does not pin an oracle. `workflow_run.rerun` at line 148 is not a GitHub workflow event/action; reruns retain run ID and increment run_attempt. Checks API status is queued/in_progress/completed, while success/failure/action_required are conclusions; pending belongs to commit-status APIs. A contents:read-only token cannot publish Check Runs. Checkout of trusted scripts does not establish that the workflow itself came from an approved revision. **Impact:** invalid workflows, spoofed check authority or silently moving acceptance definitions. **Fix:** specify trusted workflow trigger/ref and code/data separation; pin action revisions and oracle SHA. Use a separate trusted publisher (Checks write, no candidate execution) and require checks from the expected GitHub App/source where supported. Define all conclusions for failures/pauses/outages and the branch/merge-queue/base-update strategy. New heads lack qualifying checks; a check suite is not automatically created merely because head SHA changed. No branch settings are to be changed in this resubmission.

### Medium severity — qualification and accuracy

- The shown Docker flags do not configure a rootless daemon, non-root user, resource limits, output/deadline bounds or durable late-create cleanup. Reuse the qualified boundary/journal and define runtime/image limits; no new partial cleanup implementation.
- Artifact zip/hash/90-day retention does not establish origin, measured results or tamper-safe extraction. Specify bounded sizes/counts, safe relative names, symlink/traversal/duplicate rejection, provenance and digest verification; artifacts remain claims until trusted verification.
- Matrix claims direct SQL DONE is guarded. Only supported PM methods/FSM paths are guarded; raw privileged SQLite UPDATE can bypass them. Keep DB inaccessible to candidates and state the threat boundary accurately.
- Different failure phases are not all formal rejection: readiness return, new scope, stale event, infrastructure outage, recurrence and review disagreement need distinct records. A pre-execution scope failure cannot call submit without a completed run; specify a separate proposed admission-return observation.
- The blanket tests/config denylist conflicts with legitimate scoped tasks. Candidate changes to such files must never change the trusted oracle, but explicitly authorized changes may be evaluated by an independently fixed oracle. `git diff --name-only` needs NUL-safe rename/deletion/type/symlink handling.

### Low severity

Replace desktop `file://` links with repository-relative links. Correct the stated mandate date, baseline commit subjects and overbroad 'exhaustive'/'qualified' labels. Include a scoped implementation backlog with owners/dependencies rather than treating all transport and trust functions as existing.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** architecture direction retained; lifecycle, transport, workflow origin and runtime qualification are incomplete.
- **Data:** source/head generation, event idempotency and canonical digest domains must be defined separately from immutable process history.
- **AI/model runtimes:** live agents remain disabled; arbitrary commands and stdout are not trusted outcomes. Builder/verifier/reviewer identity must stay separate.
- **Resilience/governance:** unknown execution/billing holds remain correct policy. Reruns, credential publication and artifact provenance need concrete controls before activation.

## 4. Architect's Action Directive

1. Revise only the three GHA-01 documents. Mark every interface Existing / Proposed / Unsupported and link it to current code or scoped planned work.
2. Correct B1–B5 and medium findings with the bounded solution in `ANTIGRAVITY_GHA_01_CORRECTION_HANDOFF.md`.
3. For GHA-02 propose strict offline manifest/artifact/readiness validation against already completed private coordinator fixtures. Do not run arbitrary brief commands, add live workflows, weaken evidence, fabricate dispatch rows or grant signing credentials.
4. Map each revised requirement to a failure scenario and exact expected outcome; include new-head race, changed-payload replay, wrong OIDC workflow, compromised guest result, invalid check status and interrupted artifact transfer.
5. Submit the corrected contract before broader runner/provider implementation. No requirement to rerun the entire repository for documentation-only work; report actual selected checks separately.

## Verification

- Exact submission fetched/fast-forwarded; only three planning documents changed. No application/workflow code changed in review.
- Independently ran `tests/test_delivery_process_gates.py`: **47 passed in 1.69 seconds**, zero failures/skips.
- Private lifecycle probes: submit from READY returns `Successful execution required before submission`; redispatch after READINESS_RETURNED returns `Agreed, ready delivery brief required`.
- Inspected current service/schema: no GitHub PR-head registry or inbound logical-event ledger exists; absence does not prove no future implementation is possible.
- Inspected actual suite digest implementation and workflow YAML. No live GitHub API writes, provider calls, production enrollment or branch settings changed; no full gate rerun.
- Evidence: `/workspace/review-evidence/gha01/interface-probes.json`. This is a specification checkpoint, not another implementation rejection added to the original nineteen-round research sample.
