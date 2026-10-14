# Antigravity: GHA-02 bounded remediation

Read `GHA_02_REWORK_2_REVIEW.md` first. Candidate `677a85c2` is rejected; the earlier concrete fixes are retained. GHA-03 remains gated.

Before editing, write a short mechanism/closure matrix for the existing V01–V07 contract. Explain authoritative identity comparison, producer-side byte limits, file-type admission and bounded Git collection. Repeated failure of a resource invariant requires reassessing the mechanism, not another example-only patch.

Implement within validator, runner, tests and delivery documentation:

1. Require manifest intent/attempt identities and compare them to the completed run's actual joined records. Test wrong IDs separately and together, omitted fields, other-task IDs and valid IDs. Refusal must preserve revision, submissions and events.
2. Replace unbounded DEFLATE calls with remaining-budget-limited output. Correctly consume pending compressed input, validate EOF/CRC/sizes and reject excess without first allocating it. Test highly compressed forged-size input and exact member/aggregate boundaries; measure output bounds rather than only asserting eventual rejection.
3. Reject FIFO/nonregular manifest and archive inputs without blocking. Use descriptor-based validation with nonblocking/no-follow admission. Exercise a real FIFO in a bounded subprocess and clean it up.
4. Bound Git stdout/stderr while collecting, with timeout and confirmed cleanup. Keep literal arguments and existing scope/mode/rename behavior.
5. Review dict/model/JSON entry routes for equivalent input-size enforcement. Close existing overlarge-input criteria consistently; avoid new business scope.

Retain original B1–B4 regressions, strict model revalidation, fresh authenticated SDK submission and pure CLI claims-only behavior. No workflow, provider dispatch, database migration, signing key, production enrollment or core delivery changes are authorized by this brief.

After the final edit, run targeted regressions, full quality gate and clean installed-wheel checks. Record exact candidate, counts, skips and limitations. A submitted candidate is ready for independent review, not accepted. Report unresolved guarantees explicitly.
