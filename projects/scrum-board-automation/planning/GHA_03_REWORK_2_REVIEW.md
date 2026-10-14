# Independent GHA-03 rework 2 review

Candidate: **2afe1f44**. **REJECTED (REQUIRES RE-WORK)** for final GHA-03 acceptance. GHA-04 implementation remains gated.

## 1. Executive summary

The complete connector-policy snapshot fixes the reproduced event/ref mutation gap. Input-free schema and dependency formatting fixes the earlier audit examples. **129 targeted tests passed in 12.17 seconds.** One related audit branch still writes arbitrary request values, so the claimed input-free logging guarantee is not fully closed.

This is a narrow remaining logging failure. It is not evidence of public response leakage, business-state mutation, forged trusted evidence or failure of the new policy snapshot reproduction.

## 2. Closures and remaining finding

### Confirmed closures

- Changing allowed events/ref patterns at the actual artifact-validation hook now returns CONNECTOR_AUTHORITY_CHANGED.
- Earlier invalid `github_run_attempt` sentinel no longer appears in audit events.
- Tests cover detached immutable policy snapshots and monotonic supported registry updates.
- Previous size/public-error regression cases remain in the passing targeted suites.

### B1 — Coordinate mismatch diagnostics still log raw input (high; recurrence of input-free audit requirement)

Set an otherwise valid manifest `tenant_id` to `RAW_PAYLOAD_SECRET_SENTINEL`. The request correctly fails with COORDINATE_MISMATCH. The actual audit callback nevertheless receives:

`Manifest tenant_id (RAW_PAYLOAD_SECRET_SENTINEL) does not match configured tenant (tenant-alpha)`

The new sanitizer addresses Pydantic exceptions and generic exception text, but manually constructed diagnostics still interpolate request/token values. Similar source branches include manifest project ID, requested run coordinates, workflow refs and execution-condition values. These are untrusted data, even when expected to resemble identifiers.

**Required correction:** make diagnostic fields allowlisted and value-free across ALL validation rejection branches. Log a static reason and schema-owned field label (`coordinate_mismatch`, `manifest.tenant_id`) with request correlation ID; do not log the mismatched value. Any authoritative server-side identifier needed operationally must be explicitly distinguished from the rejected client claim. Remove handwritten interpolations rather than rely on secret regex detection. Include coordinate, workflow/event/ref and parser/exception branches in the closure matrix.

The public envelope remains safe. The policy is to exclude raw sensitive input from audit diagnostics; this review does not imply all normal operational identifiers are inherently secret.

## 3. Evidence and scope

Private reproduction records: `/workspace/review-evidence/gha03-final/variants.json`, `log-probe.json`, corresponding scripts and `targeted.log`. No raw customer data or actual credentials were used; sentinel is synthetic. These local paths are not GitHub attachments.

No full-gate/installed-wheel run was independently repeated after this blocker was reproduced. Author-reported 901 passed/20 skipped and wheel results remain separate author evidence. Scope remains local stateless witness validation, with no durable replay guarantee.

## 4. Pillars and directive

- Platform/data: reproduced policy-authority gap is closed; local stateless scope remains.
- AI: observations remain untrusted and do not create trusted acceptance.
- Governance: private logging still needs comprehensive input-free branch coverage.

1. Finish the centralized safe diagnostic schema; enumerate every diagnostic producer before patching.
2. Add actual audit-output checks for rejected coordinate and execution-policy values, including arbitrary non-token sentinels.
3. Revalidate all original closures, run final gate and isolated wheel on the final candidate, and submit for independent review.
4. Preserve GHA-04 gating and all existing no-live/no-business-write restrictions.
