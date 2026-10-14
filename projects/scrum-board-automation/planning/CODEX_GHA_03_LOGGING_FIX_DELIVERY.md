# Codex GHA-03 logging correction delivery

Implementation owner: Codex, explicitly assigned by CEO. Base: `2426f3ab`; preserves Antigravity gateway candidate `2afe1f44`. Status: SUBMITTED FOR INDEPENDENT REVIEW; acceptance cannot be self-conferred.

## Problem and change

Rejected coordinate values were still interpolated into private audit diagnostics. The correction makes GatewayError retain only a schema-owned error category, regardless of caller-provided message/diagnostic text. Every gateway diagnostic producer now uses static categories, including JWT, JWKS, schema, coordinates, archive, limits and internal errors. JWKS and audit-callback warnings no longer include exception messages, key IDs or rejected values.

Public codes/messages and request correlation remain available. Valid success events retain their existing operational metadata. This deliberately reduces failure diagnostic detail: investigate through category/correlation, without copying rejected inputs into logs. No delivery/IAM roles, registry snapshot semantics, business-state writes, schema, persistent replay or live workflow behavior changed.

## Producer closure matrix

| Path | Safe diagnostic mechanism | Evidence |
|---|---|---|
| Manifest tenant/project mismatch | static COORDINATE_MISMATCH category | actual audit-callback sentinel regressions |
| Rejected issuer/audience/workflow/event/ref/environment | static producer categories, allowlisted GatewayError storage | real signed-token sentinel matrix |
| Pydantic/schema and generic dependency exceptions | category only; input values and exception strings discarded | original regression tests retained, expected diagnostic format updated |
| JWKS retrieval/key errors | static categories and warning messages | existing JWKS failure tests and source enumeration |
| Archive/base64/size failures | static categories, no library exception formatting | existing artifact/size/refusal tests |
| Audit callback failures | fixed warning, no exception value or dynamic class label | caplog regression retained |
| Future error callers | GatewayError ignores arbitrary diagnostics | tests across all public codes and unknown-code fallback |

## Verification

- Ruff: passed.
- Targeted gateway/GHA-02/delivery suites: **138 passed in 9.67 seconds**.
- Original coordinate and nested-input audit probes: raw sentinel absent from audit and public envelope.
- Installed wheel: built and installed into a clean environment; copied tests outside checkout; isolated Python resolved gateway inside site-packages. **61 gateway tests passed in 4.68 seconds**.
- Full five-stage gate: **5/5 stages passed; 930 tests passed in 359.30 seconds, zero failures and zero skips**.

Evidence remains in `/workspace/review-evidence/gha03-final/` (`codex-*` receipts). These local paths are not GitHub download links. No raw customer secrets were used.

## Independent review directive

Antigravity should review this Codex-authored correction independently: reproduce arbitrary sentinel rejection paths, inspect actual audit/logger outputs, confirm public messages/correlation and valid observation behavior, and verify original policy/size regressions remain intact. Record verdict on the immutable implementation commit. GHA-04 remains gated until independent GHA-03 acceptance; no live activation is authorized.
