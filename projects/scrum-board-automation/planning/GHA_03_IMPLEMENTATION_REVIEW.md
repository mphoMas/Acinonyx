# Independent GHA-03 implementation review

Candidate: **025bede6**. Verdict: **REJECTED (REQUIRES RE-WORK)** for implementation acceptance.

## 1. Executive summary

The candidate implements actual RS256 verification and keeps outputs untrusted and stateless, but independently reproduced failures violate the agreed completion-time revocation, request bounds and error-redaction conditions. No public listener is present and these probes did not establish business-state mutation or trusted acceptance of observations. GHA-04 implementation remains dependency-gated.

## 2. Critical findings

### B1 — Connector revocation recheck uses stale object (high)

During real artifact validation, replace the frozen connector registry entry with a new entry having `status='REVOKED'`, `generation=2`. The original entry is generation 1 and ACTIVE. The request still returns `VALIDATED_UNTRUSTED_OBSERVATION`, `transport_authenticated=true`.

The initial config is retained locally; the completion check tests that same object's status rather than looking up the current registry entry. Removal or replacement/reconfiguration is not checked. Since the model is frozen, replacement is a natural supported update mechanism. The agreed condition required checking current status/generation, not an old reference.

Required correction: use a synchronized server-owned registry lookup/snapshot protocol, retaining initial identity/generation and checking current entry at completion. Refuse revoked, deleted, replaced or generation-changed configuration; tenant/project/workflow mapping changes must not reuse the old authority. Test replacement and removal during real artifact processing, not just tenant suspension before the initial tenant check. Do not manufacture a bearer/session or modify IAM/delivery permissions.

### B2 — Manifest and dictionary request bounds are not enforced (high)

Supply an otherwise valid manifest with a closure path of approximately two MiB. The serialized manifest is **2,097,866 bytes**, above the agreed 1 MiB limit, yet validation returns success. `MAX_MANIFEST_JSON_SIZE` is declared but not enforced on the nested manifest. The dictionary request path returns the input unchanged, bypassing total serialized request bounds; JSON input checks only the total 18 MiB envelope, not the nested manifest limit.

Required correction: enforce equivalent limits across bytes/string/dictionary and nested model paths before digesting/validating expensive input. Reuse strict GHA-02 manifest revalidation/size admission where appropriate. Avoid an unbounded intermediate serialization merely to reject it afterwards where bounded collection is required. Test >1 MiB nested manifests on dict and JSON routes, envelope limits, exact boundaries and preservation of valid 12 MiB archive allowance. No business writes on refusals.

### B3 — Public errors expose internal exception details (high)

Inject an internal dependency failure with message `/private/host/keys SECRET_SENTINEL`. The public `GatewayError.to_envelope()` contains `Internal gateway validation error: /private/host/keys SECRET_SENTINEL`. The catch-all directly interpolates `str(exc)` into a public error. Several other exception wrappers also embed library/input messages, including Pydantic validation representations.

Required correction: map public errors to stable bounded messages and codes, with correlation IDs. Keep exception details in private, sanitized diagnostics only. Apply across authentication/JWKS, schema, archive, base64 and generic exceptions, not only this catch-all example. Ensure private logging also never records bearer tokens or raw sensitive payloads. Test hostile nested validation values and sentinel-bearing dependency exceptions; errors must not disclose secret/path/input values or create unbounded responses.

## 3. Evidence and scope

Independent configured targeted run: **111 passed in 5.44 seconds** (see actual log; author reports are distinct). The environment initially lacked newly declared `cryptography`; after installing the declared dependency, collection and tests ran. That initial dependency failure is not an implementation defect.

Independent reproduction script and output: `/workspace/review-evidence/gha03/probe.py` and `probes.json`. These are private local evidence paths, not published GitHub attachments. Full gate and clean wheel were not independently repeated after blockers were reproduced. The reported author full gate remains author evidence only.

Delivery narrative also names `temporary_tenant_context`, `.is_active` and `config.enabled` mechanisms not used in the submitted code; actual implementation constructs a plain context and checks `tenant.status` / `config.status`. Correct documentation to describe the actual mechanism. Do not implement imaginary APIs to match the report.

## 4. Pillars

- Platform: local stateless boundary is preserved, but per-route input/resource admission is incomplete.
- Data: current connector generation must be authoritative at validation completion; no durable ingestion or replay guarantee exists.
- AI: observations correctly remain untrusted and cannot approve work; that does not excuse transport authorization or bounds defects.
- Governance: public diagnostics breach the redaction contract; independent evidence and accurate delivery descriptions remain required.

## 5. Architect's action directive

1. Document the registry freshness, universal size admission and error-mapping mechanisms before patching.
2. Close each finding across related entry/failure routes with explicit closure evidence and shared tests.
3. Run final targeted/full gate/installed-wheel checks on the unchanged candidate, then submit for independent review.
4. Preserve witness-only stateless scope. No live endpoint, workflow activation, provider dispatch, durable receipt/replay store, production enrollment or core/schema changes are authorized by this review.
