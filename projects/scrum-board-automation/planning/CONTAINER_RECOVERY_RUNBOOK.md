# Durable container creation and recovery runbook

Implementation owner: Codex, explicitly taking over the unfinished Antigravity task at the CEO's request. Deployment/integration ownership remains as recorded in the company agreement. Applicable tasks: CC-05/CC-06 containment acceptance, CC-11 uncertainty controls and CC-12 operations.

## What changed

Both `ContainerBoundary` and `DockerWorker` persist a private host-side operation before `docker create`. Records bind controller, namespace, tenant, principal, physical run, generation, image, exact container name and, when observed, immutable container ID. Containers receive matching ownership labels. The journal is not candidate input, an evidence signature authority or a token/currency ledger.

Lifecycle: PREPARED → CREATING → CREATED → STARTING → CLEANUP_PENDING → CLOSED. Lost/failed creation acknowledgement becomes UNKNOWN_CREATE and blocks the run. A late acknowledgement cannot restore canceled start authority. A confirmed known object must be removed and absence verified through a successful daemon response before CLOSED. An absent unacknowledged create remains UNKNOWN_CREATE: one or many empty snapshots cannot prove the daemon will not finish later.

The blocked generation stays blocked after cleanup. An explicit higher-generation admission is possible only after all old resources are resolved, under the same bound principal; this never authorizes a workflow retry or clears budget reservations. Existing PM/Store policy, current authenticated authority, task allowance and exact execution generation remain necessary. New admissions normally use new physical run identities.

The PM worker supplies a fresh start-authority callback checking the current intent, worker, generation and lease. The supervised swarm rechecks current role, run state and lease before candidate execution. Actual live adapters remain unregistered; this change qualifies recovery mechanics, not provider access or a general repository agent loop.

## Private state configuration

Set `MAS_CONTAINER_JOURNAL_PATH` to a persistent host-controlled SQLite path outside guest snapshots and writable tenant/agent workspaces. The prototype default is `.mas-runtime/container-recovery.sqlite` under the trusted supervisor's working directory; this directory is Git-ignored and excluded from default workspace snapshots. Production deployment should use an explicitly configured host state location, not a tenant-controlled working directory.

New state directories are created private and the database must be owned by and private to the supervisor user (created with mode 0600). Symlink paths and nonprivate journal files are rejected. Keep the file across process/service restarts; use the same path for the execution supervisor and its janitor. The file contains operational identities, not bearer/provider/signing credentials. Do not copy it into container images, candidate artifacts or Git.

## Operator command

The installed wheel provides `mas-container-recover`; the repository wrapper is `python scripts/reconcile_container_recovery.py`.

One conservative pass over already-retired resources:

```bash
mas-container-recover --journal /trusted/host-state/container-recovery.sqlite
```

Scope a pass to one previously authorized run:

```bash
mas-container-recover \
  --journal /trusted/host-state/container-recovery.sqlite \
  --namespace coordinator --tenant TENANT_ID --run-id RUN_ID
```

Repeat pending reconciliation continuously:

```bash
mas-container-recover \
  --journal /trusted/host-state/container-recovery.sqlite \
  --watch --interval 5
```

These are example paths/placeholders, not a claim that a production service is deployed. Configure restart supervision and persistent storage in the actual deployment. The command is a host-owner maintenance interface with private journal and Docker control access, not a tenant HTTP API or an administrative permission granted by this document.

Each pass handles at most 100 retired records. It ignores active objects. Output reports operation outcomes, unresolved observations in the batch and whether scoped pending records remain. Single-pass exit is 1 when pending records remain, 0 when none remain, and 130 on operator interruption. A concurrent janitor can transiently observe deletion in progress and return UNRESOLVED; subsequent passes converge through durable state. No output field clears funding or approves work.

## Crash, restart and explicit retirement

An UNKNOWN_CREATE already persists for an interrupted control request and is picked up by the janitor after restart. If a supervisor process dies while the durable row still says CREATING/CREATED/STARTING, first authorize quarantine through the owning PM/Store run controls; do not infer expiry from an arbitrary journal timestamp.

For an explicitly authorized crashed/canceled run, the host owner can quarantine its journal entries:

```bash
mas-container-recover \
  --journal /trusted/host-state/container-recovery.sqlite \
  --namespace swarm --tenant TENANT_ID --run-id RUN_ID \
  --retire-run
```

`--retire-run` requires all three identity selectors and blocks that run's starts. It is not an automatic detector of crashed workers and must not be used to kill healthy runs indiscriminately. Authenticated swarm `recover`/`cleanup` first checks existing owner authority, state and lease rules, then reconciles the correct tenant's journal. Pre-journal legacy containers retain the existing exact-run recovery compatibility; journal-owned objects from another controller/tenant are refused under legacy label matching.

If the original daemon operation never produces an observable object and no definitive terminal create acknowledgement exists, the row remains unresolved. Do not clear it using a TTL, a quiet period, guessed zero usage, SQLite edits, or automatic retry. Escalate for authoritative daemon/control-plane investigation. Recovery may be unable to make progress while the daemon or private journal is unavailable; this is visible uncertainty, not proof of cleanup.

## Ownership, output limits and budgeting

The janitor verifies exact name, private controller/operation/run/generation labels, configured immutable image and previously bound container ID before removal. It removes by immutable container ID and confirms daemon absence. Unknown or mismatched objects are left untouched and reported unresolved. It does not scan-delete by broad prefixes.

Guest stdout/stderr limits are separate from a bounded control-metadata channel. Inspection asks only for ID/name/image/labels, not environment or command contents. Output overflow cannot prevent metadata inspection merely because the guest's capture cap is small. Deletion and journal closure remain required even when execution, timeout, cancellation or output parsing fails.

No recovery method releases or settles reservations, invents measured usage, marks a task DONE or authorizes another model call. PM UNKNOWN_EXECUTION keeps funded reservations HELD and stale generations fenced. The existing swarm keeps uncertain provider usage reserved and cannot release terminal work without its separate approval gates. Store/PM accounting reconciliation remains a distinct authorized operation.

## Required independent review

Review the journal state machine and callbacks, then reproduce delayed daemon creation for both paths, actual process death, stale/canceled starts, unavailable daemon, foreign containers, same-run cross-tenant isolation, concurrent janitors, small-output-limit cleanup and retained funding. Distinguish injected transport faults with real daemon objects from an actual provider/runtime incident. Run the complete gate on the exact submitted revision and verify the installed command.

Codex authored this implementation and does not self-issue independent acceptance. Keep synthetic-only registration and live dispatch disabled until separate acceptance and the provider/export/activity/loop conditions are met.
