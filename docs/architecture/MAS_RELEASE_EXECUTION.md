# MAS-Core release execution

Status: implementation and qualification in progress; no production approval.

The owner requested execution of the complete release plan on 15 October 2026.
This authorizes Codex to implement the scoped release work, including backend
corrections, superseding the normal delivery split for this task. It does not
appoint Codex as its own independent reviewer or provision production credentials.

## Baseline and release scope

Starting implementation: `dc453a0d276574171fcf51335cb132ebb8a9761e` on
`feat/scrum-board-automation`. Local integration branch: `release/mas-core`.
Use this existing checkout; do not create a worktree for cloud execution.
The subsequent upstream CI change at `dd195c01` was integrated without resetting
the checkout. Its mutable coordinator-image selector was corrected to the pinned
digest required by the existing fixture.

First release: tenant-scoped PM submission, authorized scheduling, isolated coding,
host-owned verification, distinct approval, exact approved source export, durable
retry/restart recovery and observable outcomes. Automatic deployment is excluded.
Memory, research, live providers and additional interfaces require their own
qualification before admission. Existing staged demos are not release evidence.

## Work packages and known gaps

These are release work-package references, not fabricated runtime ticket states.
The configured MAS-PM instance remains authoritative for assignments and review.
No active project is enrolled or migrated by this document.

| Package | Gates | Deliverable | Current baseline / gap | Owner / reviewer |
| --- | --- | --- | --- | --- |
| REL-01 | A0 | Inventory and frozen pilot envelope | Deployment consumer inventory requires actual deployment access | Codex / separate architecture reviewer |
| REL-02 | A1–A2 | Strict shared contracts and compatibility | Coding admission/evidence exist; general contracts/lifecycle incomplete | Codex / separate backend reviewer |
| REL-03 | A3–A5 | Shared authority, migration and witness | Fresh bound-store scope exists; historical migration and independently operated witness not qualified | Codex / separate security reviewer + identity operator |
| REL-04 | A6–A8 | Coordinator, isolation and effect reconciliation | Existing coordinator/container implementation requires candidate-specific qualification | Codex / separate runtime reviewer |
| REL-05 | A9–A10 | Real PM-to-coding-to-approval/export journey | Isolated component checks do not establish accepted integrated operation | Codex / separate integration reviewer |
| REL-06 | A11–A13 | Per-capability admission and interface cutover | Real providers/deployment bindings must be supplied; unsupported adapters stay unavailable | Codex / separate adapter reviewers |
| REL-07 | A14–A15 | Reproducible installation, performance and recovery | Fresh candidate tests/package/runtime measurements required | Codex / separate operations reviewer |
| REL-08 | A16 | Final release packet and pilot acceptance | Independent verdict and production decision outstanding | Project owner / independent release reviewer |

## First corrective increment: receipt authority and schema

Requirements are the existing GHA-04A reference contract and independent review,
not a new receipt authority or public endpoint. Allowed files: receipt module,
IAM guard integration, focused regression tests, release evidence/docs.

1. B1: bind connector identity at trusted service construction. Never choose the
   connector from client metadata. Check current connector tenant/project/status
   for reads and writes, including historical retrieval. Nonconnector operation
   must use an explicit trusted-local service profile.
2. B2: repeat the supported complete IAM authorization inside the authority guard;
   include expiry, revocation, current permissions and configured storage binding.
   Principal re-registration must use the same guard. Constructed contexts remain
   unauthenticated. Profile remains one process; no cross-process atomicity claim.
3. B3: exact nested version-one schema; reject unknown fields, boolean versions,
   malformed hashes, invalid/oversized identifiers and limitations. Preserve
   sorted unique check subsets including equality, 1 MiB combined canonical size,
   128 items, 64 digest claims, immutable identities and duplicate-before-quota.

Acceptance: supported read/write tests for omitted/altered claims, wrong connector
ownership, revoke/remove, guard-wait expiry/role change, storage mismatch and
recursive schema negatives; existing concurrency, crash, quota and immutability
cases still pass. Receipts remain untrusted and cannot approve or mutate budgets.

## Evidence and completion

Every result names source candidate, command, environment, pass/fail/skip counts,
and evidence paths. Test author results are not independent acceptance. Do not
mark A0–A16 approved without an actual separate reviewer decision.

Proposed operational envelope: single host, five workers; 30 acceptance journeys;
100 held-out tasks with at least 90% accepted outcomes; 24-hour soak; two restore
drills with RPO <=15 minutes/RTO <=60 minutes; 30-day observed availability >=99.5%.
These are targets to agree and measure, not results or universal certification.
Required suites cannot pass with skipped mandatory cases. Live provider quality,
independent witness administration and sustained observation remain distinct from
local fixture verification.

## Development reproduction

Run `bash scripts/setup_cloud_development.sh` from the existing checkout. It uses
the recorded Python dependency constraints, the managed Docker daemon and a
digest-pinned worker. Debian tools are authenticated against signed apt metadata
and extracted locally; no system package or sandbox policy is weakened. Browser
tests use the managed image's system Chromium, not a downloaded pinned browser.

For the repository quality gate:

```sh
export PATH=/workspace/mas-release-tools:/workspace/mas-release-venv/bin:$PATH
export UV_CACHE_DIR=/workspace/mas-release-cache/uv
export MAS_SWARM_TEST_IMAGE=python@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f
export MAS_COORDINATOR_TEST_IMAGE="$MAS_SWARM_TEST_IMAGE"
bash scripts/run_quality_gate.sh
```

The outer cloud filesystem sandbox prevents nested bubblewrap UID-map setup.
Isolation tests must run through the supported command escalation flow; keep the
application sandbox and ACLs enabled. A sandbox prerequisite failure is not a
passing test or permission to use unrestricted candidate execution.

For staged development startup, keep the same PATH and run:

```sh
export MAS_PM_DB_PATH=/workspace/mas-release-state/pm.db
export MAS_AUDIT_LOG=/workspace/mas-release-state/audit/events.jsonl
export MAS_GIT_QUEUE_AUTOSYNC=false
export MAS_ENABLE_LIVE_DISPATCH=false
python main.py --mode dashboard --port 8080
```

Health must return `status=active` from `/api/status`; the portal must return HTML.
Without configured authentication, a POST to `/api/dispatch` must return 401.
These checks validate staged startup, not tenant production configuration.

## Live provider qualification

Published configuration was verified with `gemini-3.8-flash`. The bounded real
coding workflow used three calls and 1,611 reported tokens. All four Docker-run
cases passed; signed audit, durable restart, idempotent recovery and denial of
requester self-approval passed. This is smoke qualification, not sustained model
quality or production admission.

`scripts/qualify_live_coding.py` reproduces the workflow with fresh private state
and report paths, the pinned worker image above, and configured provider variables.
Its default budget is 20,000 tokens and four cases. It reads a persisted PM goal,
but uses a separate operator budget: automatic PM funding/scheduling remains open.
It stops at `awaiting_approval`; no human approval, export or deployment occurred.

The owner delegated host selection and volunteered as release reviewer. The
private Compute Engine pilot template is in `infra/gce`; no resources were created.
A target project ID and actual cloud plan/cost review are still required.
Current evidence and limitations: `docs/releases/mas-core/REVIEW.md`.
