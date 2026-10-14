# Independent GHA-03 rework review

Candidate **be9c59df**. **REJECTED (REQUIRES RE-WORK)** for final acceptance. GHA-04 implementation remains gated.

## 1. Executive summary

The three original probes now fail safely, and **122 targeted tests passed in 6.61 seconds**. Independent related-path probes nevertheless found incomplete closure of connector authority freshness and sensitive-input logging. This invokes the agreed recurrence design-checkpoint rule: reassess the complete mechanism before another local patch.

The local stateless witness boundary remains intact. These probes do not show trusted acceptance, business-state mutation or public exposure of the earlier sentinel. Public generic error messages are corrected.

## 2. Findings

### Closed original examples

- Registry replacement with REVOKED generation 2 now refuses.
- The 2,097,866-byte nested manifest is refused.
- The generic exception sentinel/path no longer appears in the public error envelope.

### B1 — Authority comparison omits event/ref policies (high)

At the actual `artifact_validation` stage, replace the connector entry with one having `permitted_events=[]` and `permitted_ref_patterns={}`, preserving its generation and other fields. Validation still returns `VALIDATED_UNTRUSTED_OBSERVATION` although current policy permits no event or ref.

Completion compares tenant, project, workflow and runner fields, but omits event/ref policy. `ConnectorRegistry` does not enforce generation advancement on replacement, and nested lists/dicts remain mutable despite Pydantic's frozen top-level model. A caller can therefore change authorization fields without making the checked generation change. This is an existing B1 authority-field requirement, not a new feature.

**Solution:** centralize the entire authorization policy identity in one immutable canonical snapshot/digest, including repository/owner, tenant/project, workflow, event/ref allowlists, runner environment and status. Registry updates must validate identities and monotonically advance generation for every policy change, with deeply detached snapshots; completion must re-resolve and compare all relevant authority. Keep a supported update API and test same-generation replacements, nested mutations, removal/revocation and normal valid validation. Do not merely add two fields to another handwritten list without addressing mutation/update ownership.

### B2 — Sensitive request values are copied into audit diagnostics (high)

Supply `github_run_attempt='RAW_PAYLOAD_SECRET_SENTINEL'`. The request is properly refused, but the configured audit callback receives the sentinel inside the diagnostic derived from `str(ValidationError)`. Pydantic embeds input values in its error string. The sanitizer redacts selected top-level keys and JWT/Bearer-like strings, not arbitrary sensitive request content.

**Solution:** log schema failure categories and bounded field locations with input values excluded, e.g. safe validation error metadata rather than full exception formatting. Arbitrary dependency exception messages may likewise contain sensitive request values. Use allowlisted, bounded diagnostic fields; do not assume regex detects all secrets. Test arbitrary non-token secrets in invalid nested fields, dependency exceptions and audit-callback failures, as well as JWTs. Public stable messages must remain unchanged. Ensure the logging system itself does not echo unsafe audit-callback exception text.

## 3. Evidence and pillars

Private evidence: `/workspace/review-evidence/gha03-rework/probes.json`, `variants.json`, `variants.py` and `targeted.log`. These local paths are not published attachments. The false `stage_called` field in the variant script was a unused reporting default; the stage callback was executed under the actual `artifact_validation` hook and changed the registry policy. The observed returned success is the material result.

- Platform: original input refusal routes are repaired; arbitrary in-process serialization allocations are not newly qualified.
- Data: complete current policy identity and mutation ownership remain insufficient.
- AI: observations remain correctly untrusted; no live automated loop is approved.
- Governance: public errors improved, but private audit logs must also exclude raw sensitive payload values.

Author reports 894 passed/20 skipped; that full run was not independently repeated after reproduced blockers. Author isolated-wheel results remain author evidence. No new runtime feature, schema or core changes are requested.

## 4. Action directive

1. Pause patching for a short shared mechanism checkpoint covering complete immutable policy updates and input-free diagnostics.
2. Implement and test the mechanisms across all related routes, retaining original regression closures.
3. Run final targeted/full-gate/installed-wheel checks after final code freeze; submit a new candidate for independent acceptance.
4. Preserve stateless witness-only scope and GHA-04 gating; no public endpoint, workflows, provider dispatch, operational enrollment or core/schema change.
