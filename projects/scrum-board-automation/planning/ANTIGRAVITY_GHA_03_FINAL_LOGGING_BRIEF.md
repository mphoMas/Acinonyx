# Antigravity — finish input-free GHA-03 audit diagnostics

Read `GHA_03_REWORK_2_REVIEW.md`. Candidate `2afe1f44` closes policy identity and previous audit examples; one logging route remains. Preserve the new snapshot/generation mechanism and passing 129-test baseline.

Concrete reproduction: put `RAW_PAYLOAD_SECRET_SENTINEL` in otherwise valid `manifest.tenant_id`. Request is correctly refused, but audit diagnostic includes that value. This violates the existing input-free diagnostic rule.

Solution:
1. Enumerate EVERY diagnostic assignment and logging call in gateway modules. Classify each value as static category, schema-owned field name, server-owned operational metadata or untrusted request/token content.
2. Replace manual interpolation of rejected values with bounded static reason plus schema-owned field label. Use one centralized safe diagnostic representation. Do not log raw values from manifest tenant/project, GitHub coordinates, workflow refs, event/ref/environment claims, malformed values or exception messages. Keep request IDs for correlation. No regex-only secret detection.
3. Add parameterized tests injecting arbitrary sentinels into each rejection branch and inspect actual audit callback/logger records, alongside public envelopes. Confirm valid requests retain useful server-owned metadata and do not log tokens/bodies. Keep callback-failure diagnostics input-free.
4. Run all gateway/delivery targeted regressions, final full gate and clean installed-wheel tests outside checkout after final edits. Commit/push exact immutable candidate and submit truthful closure evidence.

No change to IAM/delivery roles, policy snapshot semantics, database schema, live workflows, provider dispatch or GHA-04 implementation. Submit for review; do not mark accepted.
