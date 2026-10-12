# Delayed Docker creation recovery — Codex takeover delivery

Date: 12 October 2026. Implementation owner: Codex, explicitly assigned by the CEO after Antigravity exhausted credits. Baseline: `5be8a22e`. Implementation candidate: **`5a7a32eb`**. Workstream: existing SBA / CC-11 / CC-12 and CC-05/CC-06 acceptance. This is an implementation delivery, not self-issued independent approval.

## Handoff recovered

The supplied Antigravity transcript contains synchronization, tests, code inspection and a delayed-create reproduction but no committed implementation or completed gate receipt. Remote HEAD still matched the baseline. No uncommitted remote-IDE work was assumed transferred to the cloud. Codex completed the implementation here and ran its own checks.

## Delivered behavior

- Shared private SQLite journal for both container paths: durable operation/run ownership, generation, exact name/image and acknowledged immutable container ID before dispatch.
- UNKNOWN_CREATE tombstones survive client timeout and process restart. An early empty daemon listing cannot mark them CLOSED or allow a retry. Repeated janitor passes discover late objects and remove only verified owned IDs.
- Creation cancellation and late acknowledgements cannot restore start authority. Existing PM intent/worker/generation/lease and swarm role/run/lease authority are rechecked before execution. A blocked old generation stays blocked after cleanup; accounting is separate.
- Whole-boundary cleanup handles natural exit, guest failure, timeout, cancellation and output overflow. Bounded control metadata is separated from guest output capture and inspection returns only ID/name/image/labels.
- Concurrent reconciliation is safe: a reader may report unresolved deletion in progress, but durable state and later passes converge. Recovery checks remaining pending rows instead of inferring success from one remove response or batch outcome.
- Cross-tenant/current-controller objects are protected from unrelated cleanup. Existing authenticated exact-run legacy recovery remains compatible and rejects journal-owned objects under legacy matching.
- Installed operator command `mas-container-recover`, repository wrapper, explicit authorized run retirement, bounded 100-record passes and watch mode. It never clears funding or grants retry/release permission.
- Tests use isolated journal paths; runtime state is excluded from Git and default candidate snapshots. Existing CC-03 migration identities/checksums are unchanged; the shared journal has its own initial schema.

Read [the recovery runbook](CONTAINER_RECOVERY_RUNBOOK.md) for configuration, restart/quarantine, command examples and unresolved-operation handling.

## Verification evidence

Full repository command:

```bash
bash scripts/run_quality_gate.sh
```

**All five gates passed: 792 tests passed in 321.77 seconds, zero failures/skips.** Actual stages: Ruff, CLI health/capabilities, local research integrity, Python compilation and full pytest. Receipt: `/workspace/review-evidence/container-recovery-final/quality-gate.log`.

Focused final recovery/container run: **40 passed in 53.34 seconds**, zero failures/skips. Includes 11 new recovery cases and 29 CC-05 cases. Receipt: `/workspace/review-evidence/container-recovery-focused.log`.

The new cases cover both container paths with injected lost acknowledgement and real late daemon creation; reopen and actual process death; repeated empty snapshots; stale/canceled starts; unavailable daemon; foreign object refusal; same-run cross-tenant ownership; concurrent janitors; private journal paths; installed command diagnostics; and unchanged PM HELD reservation/accounting after uncertain execution.

Clean wheel build/install outside the checkout passed actual container lifecycle cleanup, durable journal reopen, an unresolved-create hold and the installed `mas-container-recover` entry point. Receipt: `/workspace/review-evidence/container-recovery-final/installed-smoke.log`. Ruff and `git diff --check` passed.

Intermediate broad testing exposed cleanup metadata exceeding a 4 KiB guest-output limit. Both affected fixture objects were recovered through their exact durable journal records; the implementation now uses a separate bounded metadata channel and verifies closure after overflow. A concurrent-reader test was corrected to distinguish truthful temporary UNRESOLVED observations from final durable convergence. Failed intermediate runs are not represented as passing evidence.

## Remaining boundaries

An unacknowledged create that never produces an observable object remains unresolved until authoritative control-plane investigation; no time-based guess or budget release is provided. The janitor defaults to already-retired rows. Process death with an active-looking row requires the owning run's authorized retirement/recovery, not an unauthenticated age-based kill of healthy work.

No production janitor service was deployed, no live provider calls occurred and no runtime registry was expanded. Live Antigravity/Codex dispatch, provider broker, candidate integration, general repository verification and continuous handoff remain separately qualified packages. Existing solve-profile and synthetic-only boundaries are preserved.

Codex authored these changes; separate candidate-specific review is still required before runtime acceptance. Antigravity's credit exhaustion does not turn author tests into independent review, and completing this handed-over implementation does not require waiting for its credits.

## Next reviewer instructions

1. Fetch this branch and inspect `5a7a32eb`, its journal/state machine, startup callbacks, immutable ownership checks and CLI owner boundary.
2. Independently reproduce lost create acknowledgement followed by late real creation for both paths. Verify absence does not close UNKNOWN_CREATE and stale/canceled actors never start the object.
3. Repeat process-death/reopen, same-name foreign object, same-run different tenant, unavailable daemon, concurrent janitors, small-output-limit cleanup and unchanged funding tests.
4. Verify owner authorization before run quarantine, private durable journal placement and installed-wheel command behavior. Test at least one real delayed control operation in the deployment environment; injected transport faults remain explicitly labelled.
5. Run the targeted suites and full quality gate on the exact candidate. Record actual results, failure/skip categories and a scoped independent verdict. Do not mark the complete loop DONE or register live adapters solely from these author receipts.
