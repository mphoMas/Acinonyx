# CC-05 missing Docker control correction

Owner: Codex, correcting the assigned low-severity defect from Antigravity's revised independent review `5c661118`. Candidate: `653e26b3`. Separate reviewer: Antigravity. Branch: `feat/scrum-board-automation`.

`ContainerBoundary._docker` now maps operating-system launch/control failures to `SwarmError`. It explicitly preserves `TimeoutError`, which is an OSError subclass, so existing bounded deadline semantics remain intact. `AntigravityExecutionAdapter.execute` receives a typed domain failure and returns UNKNOWN_EXECUTION, unknown billing and `settlement_allowed=False`. No host execution fallback is introduced and inability to confirm cleanup does not authorize settlement.

The real-container image fixture reports an explicit required-infrastructure failure if the Docker executable is missing, instead of a raw fixture exception. This does not make unavailable Docker tests pass or qualify containment without execution.

Two new regressions remove the Docker command from the execution path using a nonexistent executable: direct boundary calls raise a typed domain error; adapter execution returns uncertain status with no fabricated spend, no settlement and no host marker creation. Existing real-container timeout, cancel, natural exit, output limits and IAM/evidence regressions still run.

Verification on this candidate's unchanged code:

```bash
python -m pytest tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py tests/test_cc04_scheduler_worker.py tests/test_cc05_antigravity_adapter.py tests/test_cc06_verifier_reviewer.py -q
ruff check mas tests
```

- **142 passed in 54.10s**, zero failures/skips, using actual Docker containers for container cases.
- Ruff and `git diff --check`: passed.
- Receipt: `/workspace/review-evidence/cc0506-missing-docker-fix.log`.
- The first wrapper draft also caught TimeoutError; the existing timeout test detected it. The submitted correction preserves timeout classification and passed the rerun. No passing result is claimed for that failed intermediate draft.
- The complete 779-test gate belongs to the earlier implementation baseline. It was not rerun for this narrow exception-classification change; the relevant coordinator/container/evidence suites above were rerun.

Antigravity: independently recheck `653e26b3` alongside the still-outstanding real-container acceptance of `70e446cb` / `e1c0eed3`. Do not infer runtime acceptance from this author receipt or from a missing-Docker fixture result. Keep live dispatch disabled and the registry synthetic-only.
