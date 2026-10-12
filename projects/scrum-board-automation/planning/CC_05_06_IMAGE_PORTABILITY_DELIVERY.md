# CC-05 / CC-06 portable execution-image fixture correction

Date: 12 October 2026. Owner: Codex. Candidate: `3f45246d`. Separate reviewer: Antigravity. Branch: `feat/scrum-board-automation`.

## Corrected defect and supported setup

The author-specific local image ID in the CC-06 tests was a portability defect. Different Docker hosts may hold different immutable images even when a mutable setup tag has the same name. A local image/config ID is not a registry manifest digest; retagging another image cannot make it acquire the required content identity.

Both container suites now share `coordinator_test_image`. By default it discovers the available local `python:3.12-slim` image once and executes using the daemon's actual immutable `.Id`. Operators may instead select an existing immutable ID or repository digest through `MAS_COORDINATOR_TEST_IMAGE`. The selector is validated, inspected and resolved to an immutable ID. An unavailable configured image, mutable configured tag or mismatched local ID is an explicit fixture error: there is no fallback, automatic download, host execution or weakened pinning.

Offline admission/provenance tests use an explicitly fictitious pinned identity and do not require Docker. Only the real candidate execution tests request `runtime_contract` and the actual image fixture. Those fixtures measure actual outcomes; they do not fabricate evidence from availability or a guest summary.

Production adapter image validation is unchanged. This is a test portability correction, not production image registration or live runtime acceptance.

## Executed receipts

- CC-03 through CC-06 targeted suite: **142 passed in 32.56s**, zero failures/skips. Receipt: `/workspace/review-evidence/cc0506-portable-image.log`.
- Four real CC-06 candidate/adversarial execution cases on a different lightweight immutable fixture image: **4 passed, 48 deselected in 15.68s**. Receipt: `/workspace/review-evidence/cc06-lightweight-alternate-image.log`. The disposable image genuinely had ID `sha256:4b4190fd96346661f5e361dede98d0fd465377bda1b2371c66da36b116c876d4`; it was removed after testing.
- Explicit missing pinned image and mutable configured tag: deliberately invoked fixture checks returned errors with the expected no-fallback/immutable-selection diagnostics. These are negative prerequisite probes, not additional passing tests. Receipts: `cc06-missing-pinned-rejection.log` and `cc06-mutable-tag-rejection.log` under `/workspace/review-evidence/`.
- Ruff and `git diff --check`: passed. No full-gate rerun is claimed for this fixture-only correction.

## Separate Docker creation/recovery finding

A portability probe using the larger existing `mas-audit:revision` image produced **2 passed / 2 failed**: the failures were Docker create-control timeouts, not image-hash mismatches or passing candidate claims. The configured ten-second control deadline was not increased. The public verifier raised uncertainty rather than producing a success envelope.

After those timeouts, two daemon-created containers appeared in CREATED state after the attempted cleanup. They had never started candidate execution. Both fixture-owned containers were identified by their names, creation timestamps and `acinonyx.swarm.run=run` labels and explicitly removed; the final daemon listing was empty. Receipt: `/workspace/review-evidence/cc06-alternate-image.log`.

This exposes a separate resource-recovery gap: killing/timing out a Docker create client does not prove the daemon canceled its create operation, and an early empty listing can precede late creation. Do not claim universal cleanup confirmation for that path. Backend recovery owner: Antigravity, under CC-12/CC-11 and container acceptance. Required follow-up: durable pending container/run identity, reconciliation of uncertain create operations, a janitor/recovery scan of authorized run labels, and a delayed-create regression proving late resources are recovered before uncertainty/funding holds are cleared. No blind retry or host fallback is permitted. This does not establish a host escape or fabricated successful verification; it does prevent declaring all resource-recovery conditions closed.

## Antigravity next steps

1. Preserve local changes, fetch and fast-forward this branch. Review `653e26b3` (typed missing-Docker correction) and `3f45246d` (portable fixture correction); the supplied 27-test CC-05 report predates the current 29-test suite and does not independently cover both new regressions.
2. Keep the actual local image, rather than trying to reproduce the author's config ID. Optional: set `MAS_COORDINATOR_TEST_IMAGE` to its actual immutable ID or supported repository digest. Do not use a mutable tag in that variable or relabel an image as someone else's hash.
3. Run:

   ```bash
   python -m pytest tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_cc04_scheduler_worker.py tests/test_cc05_antigravity_adapter.py tests/test_cc06_verifier_reviewer.py -q
   bash scripts/run_quality_gate.sh
   ```

   Current targeted collection: 9 CC-03 correction + 24 coordinator state + 28 CC-04 + 29 CC-05 + 52 CC-06 = 142. Report actual counts, failures, errors and skips; do not label all CC-05 tests container tests.
4. Independently rerun the required container probes from the revised review, including uncertainty and the delayed-create finding above. A successfully installed Docker dependency alone is not acceptance evidence.
5. Commit the candidate-specific scoped review and any backend recovery delivery. Keep synthetic-only registration and live dispatch disabled. Provider/export/activity/loop designs remain proposed until acknowledged and qualified.
