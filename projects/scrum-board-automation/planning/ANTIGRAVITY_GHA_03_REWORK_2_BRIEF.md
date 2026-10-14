# Antigravity: complete GHA-03 authority and log closure

Candidate `be9c59df` closes the original examples but is not accepted. Read `GHA_03_REWORK_REVIEW.md`. All 122 targeted tests passed; independent variants still break the underlying rules.

First submit a short mechanism/closure matrix before patching, as the recurrence rule requires:

1. Define complete connector policy identity and the sole supported update API. Use a deeply detached immutable snapshot/canonical digest including event/ref policies, and monotonically advance generations for authorization updates. Completion compares current full identity. Tests must change event/ref policies with the old generation, mutate nested containers, replace/remove/revoke entries, and prove failure at real mid-validation stages. Avoid another partial field list.
2. Define safe diagnostic schemas. Never feed `str(ValidationError)` or arbitrary dependency exception text to audit logs where it can contain raw inputs. Record bounded field locations/types/codes without values; sanitize audit-callback failures too. Reproduce invalid github_run_attempt carrying an arbitrary secret sentinel and inspect actual audit output. Cover nested inputs and JWT/Bearer cases; retain public bounded error messages.
3. Correct any scope/evidence claims to actual implementation. Keep tests and diagnostics independent of invented APIs and do not modify IAM/delivery permissions.
4. After complete closure run targeted regressions, full gate and outside-checkout installed-wheel verification on the final candidate; commit/push and submit exact SHA with counts/skips/limitations.

No GHA-04 implementation or live workflow/public gateway/provider activation; no production enrollment, privileged session or core/schema changes. Mark SUBMITTED FOR REVIEW, not DONE or accepted.
