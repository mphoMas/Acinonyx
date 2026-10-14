# GHA-02 second independent review

## 1. Verdict & executive summary

**REJECTED (REQUIRES RE-WORK)** — candidate `677a85c2`.

The original empty-archive, model revalidation, NUL-name, STORED-size and CLI database-override regression cases now pass. Independent checking nevertheless reproduced incomplete provenance binding and resource-bound enforcement. GHA-03 activation remains gated; passing tests are not independent acceptance.

## 2. Critical findings

### B1 — Claimed intent and attempt identities are not bound (high)

Using a genuinely completed fixture run, replace manifest `intent_id` and `attempt_id` with `nonexistent_intent` and `nonexistent_attempt`. Keep genuine candidate, fence, artifacts and other metadata. `validate_and_submit` accepts the manifest and changes the task from `AWAITING_SUBMISSION` to `IN_REVIEW` (revision 7).

`validate_db_binding` checks the run's joined lifecycle but does not compare these two manifest claims to the joined identities. Publication drops these claims. This is a V01/V02 binding failure, not a demonstration that arbitrary unfinished code can be accepted.

Required correction: make contractual identity fields mandatory; compare every declared identity to the actual joined run/intent/attempt before submission. Missing and mismatched claims must fail without revision, event or submission changes. Do not change core delivery storage merely to accommodate unvalidated claims.

### B2 — DEFLATE output is bounded after allocation (high)

A compressed member containing 6,291,456 repeated bytes, with local and central uncompressed-size declarations changed to 1, passes header checks. Instrumenting the real decompressor shows `decompress(chunk)` returns all 6,291,456 bytes before the validator rejects against its 2,097,152-byte limit. No `max_length` is supplied. The member is ultimately rejected, but the advertised allocation bound is not enforced.

Required correction: bound decompression at the producer, accounting for remaining per-member and aggregate allowances. Handle `unconsumed_tail`, EOF, trailing bytes, CRC and exact sizes without an unbounded flush. Permit at most a documented small overflow sentinel to distinguish exact-bound EOF from excess data. Include instrumentation proving no individual output exceeds the remaining allowance plus sentinel.

### B3 — Nonregular input can block before rejection (medium)

Create an unwritten FIFO and call `read_file_bounded(fifo, 1024)` in a subprocess. It is still blocked after one second and must be killed. Blocking `os.open` happens before `fstat` rejects nonregular files.

Required correction: use a nonblocking, no-follow open followed by descriptor-based regular-file validation, or an equivalently race-safe mechanism. Confirm both manifest and archive paths return bounded structured errors for FIFOs and other unsupported file types.

### Related resource-bound closure

Git stdout limits remain checked after `subprocess.run` captures output. Close this previously identified bounded-collection requirement using bounded streaming, timeout and confirmed process cleanup; also cap stderr. Do not describe post-hoc size checks as hard collection bounds.

## 3. Pillars

- Platform: producer-side resource limits and nonblocking input admission remain incomplete.
- Data: declared intent/attempt provenance can disagree with the authoritative run.
- AI: observations remain claims; these findings do not qualify a live provider or arbitrary test runner.
- Governance: the final review remains independent, and no workflow activation is authorized by this submission.

## 4. Evidence and directive

Independent targeted run: **68 passed in 2.72 seconds**. Independent probes: `/workspace/review-evidence/gha02-rework/probes.json`; reproduction script alongside it. These local evidence paths are not GitHub download links. Author-reported full-gate results were not independently rerun after blockers were reproduced.

1. Pause local patching for a mechanism checkpoint: document how V01/V02 identity binding and V04 bounded collection apply across every input route.
2. Correct the three reproduced defects and Git collection bound within existing GHA-02 scope.
3. Add missing/mismatched identity and no-mutation tests, producer-bound decompression tests, and bounded FIFO refusal tests.
4. Revalidate original regressions, then run the full gate and installed-wheel checks on the final unchanged candidate.
5. Submit for independent review; do not mark accepted or start GHA-03.

The recurrence concerns the same resource-bound rule after claimed remediation. This invokes the agreed design reassessment rule rather than introducing a new feature or weakening acceptance.
