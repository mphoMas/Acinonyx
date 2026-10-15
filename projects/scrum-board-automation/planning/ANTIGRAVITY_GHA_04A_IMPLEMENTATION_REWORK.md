# Antigravity — GHA-04A focused runtime corrections

Candidate `4e050879` requires correction. Read `GHA_04A_IMPLEMENTATION_REVIEW.md`. Preserve the receipt slice and its real recovery/constraint tests; no new broad design rewrite.

1. Server-configure connector binding/profile in DeliveryReceiptService; payload omissions cannot skip current authority. Bind connector tenant/project and apply read/write checks under the guard. Missing/unregistered/revoked/mismatched config fails closed. If a local IAM-only profile is required, explicitly configure/name it rather than infer it from client fields.
2. Replace partial guarded tenant/session inspection with complete fresh authorization inside authority guard. Recheck credential/session expiry and current roles/scopes/storage binding at action boundary. Use actual supported IAM validation; guard all supported principal/session/tenant/connector changes, including register_principal. Add guard-wait expiry and revoked permission/read scenarios.
3. Implement strict recursive contract/payload schemas exactly matching agreed identities/claims. Reject schema_version=true, missing required claims, unknown fields, invalid SHA/digest formats and wrong types. Retain canonical owner wrapping, check scope/order/equality, limits/quota and no-write failure behavior. Add tests through supported service, not validation helpers only.
4. Correct quality-gate stage descriptions to actual run_quality_gate.sh; distinguish author/independent results. Do not claim unexecuted security/type tools.
5. Run final targeted/full gate and outside-checkout installed-wheel suite; submit immutable SHA, actual counts/skips, closure evidence and supported-profile limitations.

No extra CEO approval is needed for these existing contract corrections. Do not self-mark accepted or expand into PR freshness/artifacts/token ledger/live automation.
