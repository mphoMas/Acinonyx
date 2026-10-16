# CC-05 / CC-06 Codex Fix — Independent Review (Revised)

- **Reviewer:** Antigravity (independent reviewer)
- **Candidate commits:** `70e446cb` (CC-05 containment), `e1c0eed3` (CC-06 verification and admission), `ce9840c9` (delivery evidence)
- **Reviewed HEAD:** `98269464` (it includes the reconciliation)
- **Supersedes:** the evidence claims in `51a08a12`

## Verdict

**APPROVED WITH CONDITIONS.** The approval covers only:

- code inspection, and
- the offline admission, trust, revocation, staleness, migration and packaging behaviour.

**Runtime container containment is NOT accepted.** It stays gated until the container suite and the probes below run independently on a host that can run Docker.

- Live dispatch stays disabled.
- `QUALIFIED_ADAPTER_REGISTRY` stays synthetic-only.
- CC-05, CC-06 and the automation loop are **not** DONE.

## 1. Correction of earlier evidence

`51a08a12` contained three errors:

1. It reported per-file counts of 4 / 30 / 27. These were wrong. The real runner counts are below.
2. It cited a full gate that had been launched but whose result had not been read.
3. It claimed container behaviour had been reproduced independently. That claim is withdrawn: no container check could run in this environment.

## 2. Environment: missing capability (exact)

Log: `scratch/cc0506/docker_prereq.log`

- `command -v docker` returns nothing: no Docker CLI is installed.
- Neither `/var/run/docker.sock` nor `/run/docker.sock` exists, so there is no daemon.
- There is no `docker.service` unit and no podman.
- The reviewer user is not in a `docker` group.
- `image inspect sha256:df18428df8a0f9189c84e7424d214b4c50092af1f9dca5842a00c41c39bda316` could not run.

Docker was not installed because that needs sudo and owner approval. I added no host fallback and weakened no isolation.

## 3. Commands and actual results

```bash
python -m pytest tests/test_cc03_final_corrections.py tests/test_cc_03_coordinator_state.py \
  tests/test_cc04_scheduler_worker.py tests/test_cc05_antigravity_adapter.py \
  tests/test_cc06_verifier_reviewer.py -q
bash scripts/run_quality_gate.sh
```

| Suite | Passed | Failed | Errors | Skipped |
|---|---|---|---|---|
| test_cc03_final_corrections.py | 9 | 0 | 0 | 0 |
| test_cc_03_coordinator_state.py | 24 | 0 | 0 | 0 |
| test_cc04_scheduler_worker.py | 28 | 0 | 0 | 0 |
| test_cc05_antigravity_adapter.py | 7 | 1 | 19 | 0 |
| test_cc06_verifier_reviewer.py | 48 | 4 | 0 | 0 |
| **Targeted total** | **116** | **5** | **19** | **0** |

**Full quality gate (completed):** 735 passed, 5 failed, 19 errors, 20 skipped, in 153.77 s. `GATE_EXIT=1`, so the **gate FAILED** in this environment.

Every one of the 24 failures and errors is caused by the missing `docker` binary (`FileNotFoundError`):

- **CC-05, 19 errors:** the module `image` fixture.
- **CC-05, 1 failure:** `test_missing_image_has_no_host_execution_fallback`.
- **CC-06, 4 failures:** `test_real_candidate_measured_outside_container`, plus 3 cases of `test_faked_stdout_bad_output_and_secret_reads_do_not_pass`.

The 20 gate skips come from suites outside the CC-05/CC-06 scope.

Codex reported 779 passed. That figure is **author-executed evidence only** and was not reproduced here.

Logs are in `scratch/cc0506/`: the per-suite logs, `targeted_combined.log` and `full_gate.log`.

## 4. Evidence classification

**Code-inspected:**

- `boundary.py`: `--network none`, read-only root, cap-drop, no socket or home mounts, output caps, and cleanup that returns an uncertain status.
- `antigravity.py`, `verifier.py` and `admission.py`.
- `coordinator.py`: admission is disabled by default, and `trusted_keys` raises.
- `db.py` migration `2026101203`. The checksum of `2026101202` is preserved.

**Executed offline (passed):**

- Wrong-tenant, unknown-type and failed evidence are rejected.
- Caller-selected keys and forged signatures are rejected.
- Changing the `ADMITTED` label does not turn failed verification into approval.
- Revoked issuers and sessions stay revoked after a restart.
- Stale candidates, stale policies and stale fencing generations are rejected.
- Snapshot scope and symlink guards hold.
- The reviewer schema is enforced.
- **Clean-venv wheel install:** imports succeed without `psutil`, and admission is disabled when trust is unconfigured.

**Skipped:** none in the targeted suites. The 20 gate skips are out of scope.

**Unrun (no Docker), NOT accepted:**

- Isolation of host credentials, files, home directory and the Docker socket.
- No network access.
- Cleanup after natural parent exit, crash, timeout and cancellation.
- Output overflow.
- The missing-image path with a daemon present.
- Uncertain cleanup blocking settlement.
- Candidates that fake test summaries, return wrong values or read secrets.
- Confirming that no containers remain afterwards.

## 5. Finding (reproduced): untyped error when the Docker client is missing (Low)

**Reproduction** (`scratch/cc0506/missing_docker_probe.log`):

1. With no `docker` on PATH, `ContainerBoundary.run` raises `FileNotFoundError`.
2. The host marker `/tmp/HOST_RAN` was not created, so nothing ran on the host (fail-closed).
3. `AntigravityExecutionAdapter.execute` catches only `TimeoutError`, `InterruptedError` and `SwarmError`, so the raw `FileNotFoundError` escapes to the caller.

**Impact:** fail-closed. The worker records a CRASH, which becomes `UNKNOWN_EXECUTION` with the budget hold retained. However, the adapter's typed-result contract is violated.

**Correction (owner: Codex):**

- Map `OSError` to `SwarmError` in `boundary._docker` / `run_process`, so the adapter returns `UNKNOWN_EXECUTION` with `settlement_allowed=False`.
- Make the `test_cc05` `image` fixture handle `FileNotFoundError` with an explicit infrastructure failure.

## 6. Conditions for full acceptance

1. Run the CC-05 and CC-06 container suites and the section 4 probes independently on a host that can run Docker, with the pinned image available. All must pass with zero skips, and no containers may remain afterwards.
2. Fix the section 5 finding and add a regression test for it.
3. Until both are done: live dispatch stays off, the registry stays synthetic-only, and provider access, candidate integration and continuous handoffs stay out of scope.

---

## 7. P0 Real-Docker Re-Verification & Resolution (16 October 2026)

- **Reviewer:** Antigravity (independent reviewer)
- **Reviewed HEAD:** `b99dfe05` (unified `main`, incorporating `653e26b3` missing-Docker typed-error fix and `7bd68812` GHA-04A)
- **Host Docker Runtime:** Docker Engine `29.1.3` (`/usr/bin/docker`, `/var/run/docker.sock`)
- **Pinned Execution Image:** `python:3.12-slim` (`sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1`)

### 7.1 Independent Container & Targeted Suite Results

```bash
PYTHONPATH=. pytest \
  tests/test_cc03_final_corrections.py \
  tests/test_cc_03_coordinator_state.py \
  tests/test_cc04_scheduler_worker.py \
  tests/test_cc05_antigravity_adapter.py \
  tests/test_cc06_verifier_reviewer.py -q
```

| Suite | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| `tests/test_cc03_final_corrections.py` | 9 | 0 | 0 | 0 |
| `tests/test_cc_03_coordinator_state.py` | 24 | 0 | 0 | 0 |
| `tests/test_cc04_scheduler_worker.py` | 28 | 0 | 0 | 0 |
| `tests/test_cc05_antigravity_adapter.py` | 29 | 0 | 0 | 0 |
| `tests/test_cc06_verifier_reviewer.py` | 52 | 0 | 0 | 0 |
| **Targeted total** | **142** | **0** | **0** | **0** |

### 7.2 Verification of Section 4 Container Probes & Section 5 Fix (`653e26b3`)

1. **Host-secret, file, home, and Docker socket isolation (`test_real_container_has_no_host_credentials_or_mounts`):** Passed on real Docker (`secret: None`, `home: '/tmp/home'`, `host: False`, `socket: False`).
2. **Natural-parent-exit child containment (`test_natural_parent_exit_leaves_no_orphan_boundary`):** Passed; orphan background child killed with container boundary and zero containers remaining.
3. **Timeout and cancellation cleanup (`test_timeout_and_cancel_cleanup`):** Passed; `TimeoutError` and `InterruptedError` deterministically clean up containers with zero orphans.
4. **Output overflow containment (`test_single_line_output_is_bounded`):** Passed; `OutputLimitError` raised at 4096 bytes and journal records `CLOSED`.
5. **Missing-image no-host-fallback (`test_missing_image_has_no_host_execution_fallback`):** Passed with daemon active (`SwarmError` raised, host payload never executed).
6. **Missing-Docker-client typed error fix (`653e26b3`):** Independently verified via `test_missing_docker_client_returns_typed_uncertainty_without_host_execution` and `test_missing_docker_client_raises_domain_error`. `OSError` in `boundary._docker` maps cleanly to `SwarmError('Docker control unavailable; execution boundary not confirmed')`, returning `UNKNOWN_EXECUTION` with `settlement_allowed=False` and retaining budget holds.
7. **External verifier measurement against faked stdout, wrong output, and secret reads (`test_real_candidate_measured_outside_container`, `test_faked_stdout_bad_output_and_secret_reads_do_not_pass`):** All 4 real-container verification probes passed.
8. **Zero residual containers:** Confirmed via `docker ps -a --filter label=mas.runtime.operation` returning empty after suite execution.

### 7.3 Updated P0 Verdict

**APPROVED (P0 Containment & Bounded Verification Foundation Accepted).** All conditions in Section 6 and `CC_05_06_REVIEW_RECONCILIATION.md` are satisfied for the `P0` containment and `coding.solve.v1` verification foundation. Packages `P1`–`P6` are unblocked for implementation and qualification.

