# Acinonyx release readiness

Status: **Development prototype; supported single-host shared-identity pilot approved with conditions. Enterprise production activation is not approved.**
Regrouping baseline: `3311a4fa4a99957d9f4c13dde89fc97f0e8817f3` (9 October 2026).

This document supersedes the earlier Sprint 2 certification. Its claims of production readiness, universally authenticated agent squads and blanket completion were broader than the measured evidence. Historical work-queue completion and template reviews do not establish deployment acceptance.

## Evidence and supported scope

The [shared identity review](reviews/SHARED_SWARM_IDENTITY_REVIEW.md) and [evidence manifest](reviews/SHARED_SWARM_IDENTITY_EVIDENCE.json) record 478 passing tests, zero failures/errors/skips, all five repository gates and clean-wheel CLI/PM MCP checks. These results qualify that baseline's source and documented scope; they do not qualify later candidates automatically. TLS model fixtures are integration evidence, not live model-quality results.

Implemented scope includes explicit durable platform IAM for fresh tenant-bound coding stores, tenant PM interfaces, signed coding state/evidence, restricted Docker workers and separate human approval. Historical local stores are not automatically migrated. Legacy single-tenant interfaces, demonstrations and unadmitted capabilities are outside the consolidated pilot.

## Deployment and consolidation register

| Requirement | Current status | Closure evidence |
| --- | --- | --- |
| Shared-identity source and package regression | Passed at the regrouping baseline | Shared identity evidence above; rerun on changed candidates |
| Historical identity/run migration | Pending | Reviewed ownership/history mappings, credential reissue and recovery rehearsal (A4) |
| Independent production IAM witness | Pending; protocol implemented | Actual independent HTTPS deployment and outage/restore drills (A5) |
| Shared contracts, coordinator and capability broker | Partial | Contract conformance, compatibility, lifecycle and routing/execution cases (A0–A9) |
| PM-to-coding end-to-end workflow | Pending | Real admitted interfaces, verification, separate approval, export and restart reconciliation (A10) |
| Wider memory/research/model/interface admission | Pending | Per-adapter qualification and interface cutover (A11–A13) |
| Operational load, backup and recovery targets | Unqualified | Agreed thresholds and measured drills (A14) |
| Reproducible release candidate and final review | Pending for consolidation | Candidate-specific package/deployment checks and independent verdict (A15–A16) |

The [consolidation acceptance register](architecture/MAS_CONSOLIDATION_ACCEPTANCE.md) owns gate status; the [implementation status](architecture/MAS_CONSOLIDATION_STATUS.md) records partial slices. No checkbox here grants production approval. The [capability matrix](CAPABILITIES.md) describes implemented code separately from admitted deployment scope.

## Environment snapshot at regrouping

The managed development environment is connected. No application containers/dashboard were running during inspection. Runtime doctor reported STAGED dispatch, sandbox and tool ACL enabled, and no legacy live provider. Swarm provider variables were present, but current remote authorization/model availability was not tested. Production dashboard credentials, durable IAM configuration and witness endpoint were not set in the inspected shell. Readiness observations for injected credentials/network enforcement were unknown.

These observations describe this development session, not all deployments. Do not infer production configuration from historical container smoke logs.
