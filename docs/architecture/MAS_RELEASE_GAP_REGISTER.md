# MAS-Core release gap register

Date: 15 October 2026. Integration baseline: `dd195c01` plus the local
`release/mas-core` working changes. This register does not approve a gate or
change an operational MAS-PM record. The earlier 65% estimate is not a readiness
measurement.

## Current delivered increment

GHA-04A's documented receipt blockers have author-side corrections: server-owned
connector profile and current read/write checks; repeated complete guarded IAM
authorization; storage binding; guarded principal changes; exact nested schemas;
bounded identifiers and digest claims. Unconfigured receipt services refuse
operations. Trusted-local operation requires explicit startup configuration.

The rejected candidate's SQL migration and immutable stored receipt format are
unchanged. Claims remain untrusted; no receipt grants execution, evidence admission,
budget changes, task completion or release approval. The local authority guard
does not coordinate separate service or administration processes.

The receipt API intentionally removes implicit profile selection and per-request
connector registry injection. Configure once at trusted service startup:

```python
from mas.pm.receipts import DeliveryReceiptService

service = DeliveryReceiptService(
    db, registry, connector_key=(repository_id, repository_owner_id),
    tenant_id=tenant_id, project_id=project_id,
)
# Explicit nonconnector trusted-host use only; never expose this as a client flag:
local_service = DeliveryReceiptService(db, trusted_local=True)
```

The general DeliveryService accepts a startup-only `receipt_access=ReceiptAccess(...)`.
Without it, normal delivery functionality remains available but receipt operations
are denied. Direct helper calls likewise require an explicit ReceiptAccess.
Callers supply `issue_id` explicitly; ownership is validated from the parent task.
Payloads require repository and repository-owner IDs, GitHub run/attempt, MAS
run/intent/attempt/fence, sorted check items, digest-only artifact claims and
limitations. Optional source_generation is a positive integer or null. Limitations
are at most 8192 characters; check identifiers are at most 128 ASCII characters.
Unknown fields are refused recursively.

## Gate reconciliation

| Gate | Current evidence / implementation | Remaining closure |
| --- | --- | --- |
| A0 inventory | Existing source inventory and new execution scope | Confirm actual deployment consumers, effects, ownership and reviewed supported envelope |
| A1 contracts | Existing coding contracts plus strict receipt claim boundary | General message/capability/result/approval/audit and shared lifecycle contracts; independent conformance review |
| A2 compatibility | Existing regression and installed-package checks | Explicit extraction comparison and reviewed historical upgrade mapping |
| A3 unified authority | Existing shared IAM; receipt guarded checks repaired | Complete all admitted CLI/HTTP/MCP workflow cutover and active-run revocation qualification |
| A4 migration | Existing fixture migration/recovery tests | Actual historical inventory, owner-approved identity mappings, credential reissue and reconciled rehearsal |
| A5 witness | Local TLS witness/recovery tests | Independently administered production host, writer setup and actual deployment drills |
| A6 lifecycle | Existing coordinator concurrency and recovery tests | Integrated candidate-specific lifecycle admission and separate acceptance |
| A7 isolation | Existing tenant/message adversarial tests | Admitted routing/context/delegation/cancellation envelope qualification |
| A8 execution | Real Docker and bubblewrap isolation tests | Actual deployment isolation policy/resource envelope and independent qualification |
| A9 verification | Existing measured verifier and approval controls; receipts stay quarantined | Review changed candidate and integrated provenance/approval/export behavior |
| A10 vertical slice | Live Gemini from persisted PM source, Docker verification, restart/idempotence and requester approval denial | Automatic PM funding/scheduling; accepted PM-to-coding-to-human-approval-to-export journey with restart/effect reconciliation |
| A11 memory/research | Local retrieval, asset and link checks | Actual adapter retention/deletion, tenant isolation, injection and recovery qualification; factual accuracy is separate |
| A12 models | Published Gemini configuration; verified gemini-3.8-flash, three live calls, 1,611 tokens and four passing cases | Held-out quality, cost and failure evaluation; separate capability admission |
| A13 interfaces | Existing CLI, HTTP and MCP tests | Full production interface admission/cutover matrix; disable excluded paths |
| A14 operations | Local recovery and staged startup checks | Agreed capacity; 24-hour soak; two measured RPO/RTO drills; monitoring/support; 30-day pilot observation |
| A15 reproduction | 1,006 passing gate tests; pinned worker, clean wheel, built runtime image and restart/authentication-denial checks | Qualification on the actual deployment host; complete reproducible release packet |
| A16 verdict | Owner volunteered as reviewer; verdict pending | Independent review of the exact candidate and explicit owner release decision |

## External prerequisites

1. Published provider configuration is verified. No replacement API key or additional
   settings publication is required for the completed live qualification.
2. The owner delegated host selection: a private Compute Engine pilot is proposed
   in `infra/gce`. The target Google Cloud project ID, billing/access verification,
   real cloud plan and cost review remain prerequisites to provisioning. An
   independently administered witness still requires separate authority.
3. Supply actual historical identity/state inventory and authorized mapping
   decisions before migration. Do not infer account ownership from fixtures.
4. The owner will review the release. The actual verdict remains pending; author
   checks and automated model review do not supply human release approval.

Additional engineering remains in the gate table; configuration alone will not
complete consolidation or the integrated release. Resume those work packages
against the declared deployment and approved contracts, then qualify each extra
adapter separately. The initial receipt increment did not spend live model tokens. Subsequent bounded
qualification consumed 1,611 reported tokens. No production rollout or remote push
has occurred. See `docs/releases/mas-core/REVIEW.md` for the current evidence.
