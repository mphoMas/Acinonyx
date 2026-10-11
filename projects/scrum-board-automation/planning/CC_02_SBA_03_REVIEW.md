# Independent review: coordinator contracts and SBA-03

Candidates: `69e40290` (planning), `8f842ece` (probes), `90021f4c` (contract). Reviewed 11 October 2026.

## 1. Verdict & Executive Summary

**SBA-03: REJECTED (REQUIRES RE-WORK).** Explicit REMOVE/REPLACE staging fixes the prior null reviewer defect, but the unbound MCP publication path still treats a nonempty principal as sufficient authority. Reconciliation adds a new mutable policy decision without proposal version binding or durable decision audit.

**CC-01: APPROVED WITH CONDITIONS for interface discovery only.** Early session IDs are reported and UNKNOWN_EXECUTION is a sound safe-stop policy. Several empirical claims still exceed the actual probes.

**CC-02: REJECTED as the governing implementation contract.** Drafting may continue; CC-03 is not yet dependency-ready against this draft. Missing fencing, recovery and evidence details directly affect durable state design.

## 2. Architectural Audit & Critical Findings

### High Severity (Blockers)

- **Planning authorization:** `mas/pm/tools.py:pm_publish_plan` unbound branch only checks that the actor string is nonempty. Remove that exposed fallback or require verified planning authority. Shared HTTP bearer mode defaults `allow_admin_token_planning` to true rather than requiring explicit configuration. Define the intentional trusted local administrator mode, configure it explicitly and test negative HTTP/MCP cases; do not claim all publication paths enforce the same authority.
- **Reconciliation concurrency and audit:** `reconcile_staged_changes` applies whichever staged proposal is current, without an expected plan/proposal revision, and does not persist actor/tenant/decision audit. A delayed apply request can approve a different proposal. Bind apply/reject to an immutable proposal version and expected live policy version; record before/after policy and actor transactionally. Applying policy changes must invalidate previously admitted evidence/approvals as appropriate.
- **Probe evidence classification:** probe 2 launches a synthetic Python worker, not either CLI; probe 3 returns predefined dictionaries without crash injection. Probe 4 checks for a write only half a second after cancellation although the child waits 30 seconds; it neither enumerates surviving descendants nor observes the write deadline. Probe 5 supplies a two-line prompt, no Git repository, actual commit, tests or immutable candidate. Relabel these honestly; provide runtime-specific measured probes or explicitly retain unverified/unsupported classifications.
- **CC-02 fencing and crash boundary:** specify persisted pre-spawn dispatch claim, monotonic fencing generation, compare-and-swap updates, stale worker/result rejection, uniqueness constraints, and how a crashed PROCESSING intent is reconciled. Session IDs do not identify a unique execution turn. Do not redispatch solely after lease expiry.
- **CC-02 recovery safety:** Git rollback cannot undo external side effects. DISCARD_ATTEMPT must not imply safe retry until local descendants, remote work, external effects and budget uncertainty are reconciled under authorized policy. Define pause/cancel/timeout, bounded settlement and manual escalation.
- **CC-02 evidence and completion:** define canonical signed payload, issuer/key ownership, exact tenant/task/attempt/run/candidate/base/policy/test-suite/runner bindings, replay prevention and trusted verifier ownership. A hashed zero-exit log alone is insufficient. Define independent reviewer authority, integrated candidate checks and applicable human release gates. Workspace path selection and process groups are not execution containment.

### Medium Severity

- Probe 1 uses blocking readline/wait without deadlines, labels parsed JSON supported even if the required ID is absent, and does not use process-group cleanup. Make probes fail on missing required evidence and bound every operation.
- Contract task lifecycle omits existing REFINED and EXECUTING states and uses new states without migration rules. Specify separate attempt/run states and map them to existing board FSM; define schemas, adapter request/response/errors and event cursor/deduplication rules.
- No authenticated deployment API receipts or before/after preservation comparison are supplied. Database listings alone do not qualify the end-to-end board interface.

### Low Severity

- The uploaded “full test suite gate” is three targeted modules, not the repository quality gate. Keep those labels distinct.

## 3. Pillar-by-Pillar Breakdown

- **Platform:** Batch adapters remain viable; durable dispatch requires enforceable fencing and crash semantics.
- **Data:** Null staging improves preservation; proposal versions, transactional audit and uniqueness need explicit contracts.
- **AI:** Model text rejection is a smoke check, not immutable-candidate review qualification.
- **Resilience/Governance:** UNKNOWN_EXECUTION is appropriate; cancellation, external effects, budget settlement, auth and evidence ownership remain incomplete.

## 4. Architect’s Action Directive

1. Antigravity closes publication authority and version-binds/audits reconciliation, with regression evidence.
2. Correct probe and receipt classifications; supply bounded runtime-specific measurements where available. Unknown capabilities must stay unknown.
3. Revise CC-02 with concrete schemas, FSM mappings, fencing, recovery, budget and signed evidence rules before CC-03 implementation relies on it.
4. Submit authenticated board preservation receipts and candidate-specific test/quality-gate evidence. Preserve the existing SBA branch, board and task UUIDs.

No backend code or deployment state was changed by this review. Live provider probes were not rerun: agy is unavailable here, and the supplied script has unbounded operations. The implementation and receipts were inspected directly.

Independent targeted validation: `/workspace/venvs/acinonyx/bin/python -m pytest tests/test_sba_02_discovery.py tests/test_sba_03_plan_publication.py tests/test_sba_05_session_integration.py -q`: **64 passed in 21.62 seconds**. This is not full repository qualification.
