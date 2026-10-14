# Antigravity implementation brief: GHA-02 offline validator

Authority: scoped GHA-01 design acceptance in `GHA_01_REVISED_ACCEPTANCE_REVIEW.md`, candidate `6a3797cf`. Branch: feat/scrum-board-automation. Owner: Antigravity. Separate reviewer: Codex. Keep the existing SBA stream; no operational task statuses are changed by this brief.

## Outcome and edit scope

Implement a bounded offline manifest/artifact validator for already completed authorized coordinator runs. No commands/tests executed by the validator; no trusted receipts or acceptance produced.

Allowed new files:
- `mas/pm/delivery_validator.py`
- `scripts/delivery_gate_runner.py` (offline validator/collector, despite its filename)
- `tests/test_gha_delivery_integration.py`
- `projects/scrum-board-automation/planning/GHA_02_DELIVERY.md`

Also update the three GHA-01 documents with the factual/ownership/status corrections recorded in the revised review. Do not refactor delivery.py, alter IAM/evidence/worker/migrations, add public endpoints or change workflows. If a genuine integration defect requires broader code changes, reproduce and record it before expanding scope.

## Shared implementation requirements

**V01 — Strict input.** Versioned manifest schema, strict integer/bool types, no unknown fields, duplicate JSON keys, nonfinite values or overlarge input. Exact tenant/project/issue, brief/policy revision, intent/run, candidate/base/suite identities. Use bounded opaque IDs consistent with existing models. No caller-selected actor or new privileged token.

**V02 — Actual binding.** Resolve task and run through the existing trusted tenant-bound database; enforce AWAITING_SUBMISSION/READINESS_RETURNED, completed intent, successful attempt, exited run, matching fence/brief version, candidate/base/suite and current issue scope/policy. Validate before mutation. No direct SQL inserts of success and no READY->submit shortcut. Current freshness is local coordinator identity only; no claim to validate GitHub head without the future registry.

**V03 — Read committed Git objects safely.** Repository root comes from trusted integration configuration, not arbitrary manifest paths. Resolve exact existing base/candidate commits; inspect Git trees/diff using argument arrays and NUL-safe parsing. Check both rename paths, additions/deletions and modes against declared scope. Reject symlinks/submodules and unsafe filesystem snapshot entries. Do not execute hooks, candidate setup, arbitrary check commands or import candidate code. Git tree inspection cannot detect host hardlinks; avoid copying/extracting host candidates.

**V04 — Bounded archive validation.** At most64 regular members,2 MiB/member,10 MiB total actual uncompressed bytes,12 MiB maximum compressed input. Reject unsupported compression/encryption, unsafe absolute/traversal/backslash/NUL/control paths, duplicate/colliding canonical paths and non-regular entries. Stream with actual byte caps; do not trust ZIP headers for decompression limits. Verify declared/actual sizes, CRC and SHA256. Prefer reading without extracting to host. Close resources on every failure.

**V05 — Observations remain claims.** Each supplied observation names an agreed check and existing validated artifact. Duplicate/unknown checks reject. Missing checks or valid FAILED/SKIPPED/UNAVAILABLE observations are not fabricated PASSED results: they can produce READINESS_RETURNED through the existing service. A digest match proves bytes, not execution truth. CLI must never claim ACCEPTED or publish GitHub success.

**V06 — Authority/atomicity.** Library mutation uses existing DeliveryService.submit under a fresh authenticated tenant binding and assigned builder authority. Separate pure validation from publication. CLI defaults to validation-only and emits a clearly labelled observation manifest; any publication requires trusted service configuration and ordinary existing authority, never --trusted-admin/--actor or a production DB path override. Tests may establish private fixtures using existing test helpers, but no helper enters public library/CLI. Reject stale revisions and ensure validation failure leaves PM phase/events/holds untouched. Revalidate submitted identity after collection before commit.

**V07 — Output and measurement.** Structured bounded JSON outcome: VALIDATED_CLAIMS / VALIDATION_FAILED in pure CLI mode, or actual READINESS_RETURNED/IN_REVIEW after authenticated publication. Identify exact candidate/revision and reasons without secrets/full logs. Validator refusals are separate from formal review rejection. Do not hide upstream errors or manufacture PM events for failed preflight; report that their future durable ingestion is GHA-04 work.

## Negative and positive acceptance matrix

1. Valid private completed run + all valid observations -> authenticated IN_REVIEW, never ACCEPTED/DONE; pure CLI remains VALIDATED_CLAIMS.
2. Omitted check and valid FAILED/SKIPPED/UNAVAILABLE observation -> READINESS_RETURNED when publication is authorized; prior returns survive reopen.
3. Missing brief, READY state, nonexistent/foreign/failed/uncertain run -> denied without mutation.
4. Wrong tenant, role, unbound/revoked session and stale CAS -> denied without mutation.
5. Changed candidate/base/suite/fence/policy or pending reconciliation -> denied.
6. Unknown fields/checks, duplicate JSON/check identities, boolean/string numeric fields -> denied.
7. Traversal/absolute/backslash/control paths, symlink/nonregular member and duplicate canonical archive names -> rejected before extraction/submission.
8. Overlarge compressed input, header size lie, excessive count, streamed decompression overflow, truncation, CRC/hash mismatch -> rejected and resources closed.
9. Unauthorized diff, rename across scope, symlink/submodule/mode changes, missing Git objects -> denied; malicious command-looking filenames handled as data.
10. Two competing publication calls with same revision -> one winner, no duplicate history. Pure validation replay has no paid side effects.
11. Existing recurrence/dispute/scope pause cannot be cleared by validator or CLI.
12. CLI fake PASSED stdout/token/actor/db override cannot authorize submission or sign evidence.
13. Clean installed wheel imports validator; direct script works in documented setup and outputs truthful errors without the checkout on import path assumptions.

## Design/readiness check before submission

Write a short design section in GHA_02_DELIVERY.md covering archive streaming, Git tree validation, authority boundary, CLI publication choice, concurrent/stale handling and how every V01–V07 invariant is tested. Share the known matrix with implementation; preserve reviewer-owned additional probes.

Run targeted new tests plus existing delivery/evidence/coordinator regressions, Ruff, diff check and actual full quality gate after final code changes. Docker/browser missing prerequisites are not passes; fix or report them. Build/install the wheel outside checkout. Record counts, failures/skips, file scopes, candidate SHA, assumptions and unresolved dependencies.

No OIDC gateway, live check publisher, general test executor, source-ledger schema, retry_readiness, signing credentials, production enrollment or branch settings in this increment. Push code and evidence for Codex review, with one finding-closure entry per relevant review condition. Do not self-approve.
