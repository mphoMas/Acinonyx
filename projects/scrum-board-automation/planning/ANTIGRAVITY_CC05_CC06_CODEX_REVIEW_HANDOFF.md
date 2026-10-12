# Antigravity: independently review the Codex CC-05 / CC-06 correction

The owner explicitly assigned Codex to fix CC-05 and CC-06. The code is now submitted for your independent review; implementation ownership does not authorize self-acceptance or live activation.

## Candidates and scope

- Branch: `feat/scrum-board-automation`.
- CC-05: `70e446cb` — restricted container execution, fail-closed model discovery, scoped file snapshots, bounded telemetry and whole-boundary cleanup.
- CC-06: `e1c0eed3` — trusted solve-contract verification, strict versioned evidence, durable immutable jobs, service-owned issuer registry with live platform IAM session checks, strict final reviewer output and a separate corrective migration.
- Read `CC_05_06_CODEX_FIX_DELIVERY.md` for actual supported scope, integration requirements and receipts.

## Execute in order

1. Fetch and fast-forward the shared branch after preserving any local work. Do not force-push or overwrite uncommitted work. Confirm both candidate commits are ancestors of your reviewed HEAD.
2. Inspect the code before relying on the tests. Review `boundary.py`, `antigravity.py`, `verifier.py`, `admission.py`, the coordinator facade and migration `2026101203`. Confirm the source/checksum identity of old migration `2026101202` is unchanged.
3. Independently reproduce the original failures with private fixtures: wrong-tenant/unknown/failed signed receipt, printed pytest-like success with no tests, a natural-exit parent leaving a child, caller-selected keys and a fabricated ADMITTED label. All must fail safely now.
4. Independently test current policy/fence changes, canceled/uncertain runs, pending reconciliation, zero/boolean/incomplete case results, same builder/issuer, shared signing keys, unknown domains/types, forged signatures, nonce replay, revoked issuer/caller sessions and reopen after durable revocation.
5. Exercise **real containers**, not a mock claiming termination. Test natural exit, crash, timeout, cancellation, output flooding, absent image/daemon, no network, no host home/files/socket/secrets, and cleanup failure. Verify uncertain execution retains its budget and cannot claim completion. Keep production worker registry synthetic-only.
6. Run:

   ```bash
   python -m pytest tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_cc04_scheduler_worker.py tests/test_cc05_antigravity_adapter.py tests/test_cc06_verifier_reviewer.py -q
   bash scripts/run_quality_gate.sh
   ```

   The container tests require Docker access and an available pinned Python execution image. The delivered cloud fixture uses local image ID `sha256:df18428df8a0f9189c84e7424d214b4c50092af1f9dca5842a00c41c39bda316`; CC-05 also resolves the local `python:3.12-slim` image to its immutable ID. Report missing infrastructure and skips honestly. Do not describe mock output, shell exit or skipped containment tests as execution proof.
7. Build/install the wheel into a clean venv outside the checkout. Confirm adapter imports without psutil, new database creation, historical upgrade/demotion preserving receipt bytes, reopen and fail-closed unconfigured admission.
8. Commit a candidate-specific independent review, with APPROVED / APPROVED WITH CONDITIONS / REJECTED and exact supported scope. State actual commands, counts, skips, negative probes and any remaining failures. If you identify a defect, reproduce it and name the mechanism before changing the implementation.

## Restrictions and next dependency

Do not mark CC-05/CC-06 DONE, enable registry admission, enable provider egress, deploy or automate live developer/reviewer communication solely because these tests pass. Verification is limited to the operator-owned solve(payload) contract; arbitrary repository test execution is deliberately rejected. The offline container cannot call live providers; a separately qualified provider broker, runtime image, candidate export/integration and activity/session bridge remain required.

Reviewing these containment/trust corrections is the immediate task. Broader runtime integration follows explicit scoped acceptance. Preserve frontend work and the accepted CC-03 / controlled CC-04 baseline.
