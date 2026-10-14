# Independent review: GHA-02 candidate 14408e20

## 1. Verdict & executive summary

**REJECTED (REQUIRES RE-WORK)** for final GHA-02 contract acceptance. The previous three reproduced blockers are closed. One bounded archive-integrity correction and truthful delivery-report correction remain; GHA-03 is not released by this review.

This is a narrower rejection than the previous review. The remaining archive defect does not demonstrate forged artifact content, authorization bypass or final acceptance of failed work. It demonstrates acceptance of an internally inconsistent ZIP despite the existing archive-integrity requirement.

## 2. Findings and closures

### Confirmed closures

Independent targeted suites: **74 passed in 3.56 seconds**.

- A manifest naming nonexistent intent/attempt IDs now raises `Intent ID mismatch`; the task state is unchanged.
- A real unwritten FIFO is rejected in approximately 0.000021 seconds.
- The same six-MiB forged-size DEFLATE input now fails at the producer boundary. Instrumentation observed output chunks no larger than 65,536 bytes, all calls supplied `max_length`, and the final overflow output/allowance was 1 byte.
- Source inspection confirms streaming Git stdout/stderr collection with deadlines and bounded chunk buffers. This avoids the previous unbounded `subprocess.run` capture. A fixed read-chunk overshoot remains bounded; this review does not claim byte-perfect zero-overhead allocation or whole process-tree containment.

### B1 — Corrupted ZIP data descriptor accepted (medium; contract blocker)

Create a DEFLATED ZIP using an unseekable output buffer. This creates a bit-3 member with a signed data descriptor. Replace the descriptor's CRC32, compressed size and uncompressed size with zero. Leave the actual payload and central directory unchanged. `validate_artifact_archive` accepts `result.log` containing `ok`.

The validator detects descriptor signature presence only to advance the physical offset by 12 or 16 bytes. It never validates the descriptor values. Actual payload CRC and digest remain correctly calculated; the failure is contradictory physical metadata being admitted under the claimed ZIP integrity profile.

**Required correction:** Either reject data-descriptor/ZIP64 profiles explicitly for this bounded artifact format, or fully validate supported descriptors against measured CRC, physical compressed length and actual uncompressed length, with truncation and boundary checks. State the supported profile. Test both signed and unsigned descriptor forms if supported, corrupted fields separately, truncated descriptors and valid archives. Keep existing STORED/DEFLATE resource limits and observation digest checks.

### B2 — Delivery gate description contradicts repository script (medium; evidence correction)

The submitted report lists Mypy, CC contracts and wheel installation as stages of `scripts/run_quality_gate.sh`. The actual unchanged script runs Ruff, doctor/capabilities, research assets/links, compilation and the full pytest suite. Separate wheel or coordinator runs may have happened; they are not stages of this script. Correct the report using exact command receipts and retain skips and limitations. Do not infer that this mismatch proves the reported test count false.

## 3. Pillars

- Platform: previous FIFO and decompression mechanisms are corrected; Git collection is now streamed.
- Data: authoritative intent/attempt binding is corrected; descriptor integrity remains incomplete.
- AI: this is offline claim validation, not a qualification of arbitrary verification or provider dispatch.
- Governance: independent acceptance is still required; accurate evidence descriptions are part of readiness.

## 4. Action directive

1. Choose and document a minimal ZIP descriptor profile before editing. Reject unsupported variants rather than expanding the general ZIP parser unnecessarily.
2. Close B1 across every supported descriptor variant and add independent malformed-metadata regressions.
3. Correct B2 and run final targeted tests, quality gate and installed-wheel checks on the unchanged final candidate.
4. Submit for independent review. Preserve the earlier fixes; do not modify delivery core, activate workflows or start GHA-03.

Local probe records: `/workspace/review-evidence/gha02-rework3/closures.json` and `archive.json`; reproduction scripts in the same directory. These are local evidence locations, not published GitHub attachments. The full quality gate was not independently repeated after this remaining contract violation was reproduced.
