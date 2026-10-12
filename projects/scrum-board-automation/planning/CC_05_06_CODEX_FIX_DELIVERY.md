# CC-05 / CC-06 corrective implementation

Owner: Codex, explicitly assigned by the project owner on 12 October 2026 to fix both milestones. Antigravity remains the normal backend owner and is the separate reviewer of this correction. This delivery supersedes the unsafe behavior in `4c60713f` / `b4db4a7d`; it does not supersede their recorded rejection or certify its own acceptance.

## Implemented behavior

### CC-05 execution boundary

`mas/pm/adapters/boundary.py` supervises pinned-image containers with no host mounts, no network, an unprivileged user, a read-only root, dropped capabilities, no privilege escalation, bounded memory/CPU/PIDs/file descriptors and bounded output. Explicit workspace files are copied as data; traversal, symlinks, credential/control paths and oversized snapshots are rejected. Candidate children receive a minimal environment and no host signing credentials, home or Docker socket. Proxy and CA settings remain available to the trusted Docker client; they are not transferred into the offline candidate boundary.

All execution paths, including fixture commands and model discovery, use this boundary. Parent exit, crash, timeout, cancellation and output overflow lead through forced container removal and successful daemon absence confirmation. No host subprocess execution fallback exists. Cleanup uncertainty cannot settle execution. Missing/conflicting/invalid usage, malformed candidate identity or budget overrun produces UNKNOWN_EXECUTION and no measured billing. Only selected observation fields are emitted; raw runtime stdout is not published as board evidence.

Model discovery requires a successful bounded JSON model list from the container CLI. Empty/malformed/unavailable discovery never fabricates the requested model. Live discovery cannot be disabled. Test commands are explicitly labelled TEST observations; they are not trusted completion evidence.

The psutil dependency was removed entirely, rather than assuming it exists in users' development environments. Packaging is verified from a clean installed wheel.

### CC-06 measured verification

`VerificationContract` supplies an operator-owned source path, bounded cases and expected outputs, and a pinned worker image. The supported executable contract is the existing supervised swarm's Python `solve(payload)` workflow. Candidate and base must be exact, existing Git commits in the authorized repository; source must be a regular Git blob. No candidate checkout or code execution occurs in the verifier host process.

Each case runs in the existing restricted `DockerWorker`. Expected outputs remain on the trusted host; the verifier measures actual returned values and constructs case outcomes/counts itself. Printing `1 passed`, failing outputs, secret reads and extra stdout cannot fabricate successful test evidence. Missing contracts, arbitrary test commands, absent/distinct builder identity, mutable refs and nonexistent candidates/bases are rejected.

This intentionally replaces the unsafe arbitrary-command interface. Repository-wide pytest execution is **not** supported as trusted completion evidence by this adapter; that requires a separately designed isolated test/result contract. No broader workflow is claimed from the bounded solve contract.

### Strict evidence and review authority

Signed envelopes contain an explicit schema, production/test domain, type, issuer/key identity, nonce and result. They bind tenant/project/issue/task/attempt/run, exact candidate/base, policy version, fencing generation, suite digest, worker image and developer principal. Keys require at least 32 bytes; public defaults and environment fallbacks are gone. The canonical encoding is deterministic sorted JSON, not an RFC 8785 claim.

`EvidenceTrust` is injected by the trusted service at startup. Each key is scoped to a distinct issuer principal, tenant and verifier/reviewer role; shared role keys are prohibited. Each issuer has an actual platform IAM session, checked on admission for current authority and revocation. Receipt callers cannot provide trust keys. Bound callers require `coordinator:evidence:admit` in addition to storage authority; explicit trusted internal administration remains supported.

An immutable durable job manifest binds all execution fields, verifier/reviewer assignments and owner case IDs. Admission atomically checks the current successful physical run/attempt/intent, candidate, ownership, policy, pending reconciliation and generation. Unknown schemas/types/domains, incomplete outcomes, failures, zero/boolean counts and substituted suites/issuers are rejected. Nonces retain the existing durable UNIQUE replay constraint. Default coordinator instances admit nothing.

Review requires a single strict final object with schema `mas-review-v1`, the full binding, verdict and comments. Earlier approvals, multiple conflicting objects, text suffixes and quoted/sub-string approval cannot approve. Reviewer commands run in the same restricted boundary with an immutable diff supplied as data. Review admission requires a matching, still-authorized, cryptographically rechecked successful verification; an ADMITTED database label alone cannot convert a signed failure into a pass.

### Durable upgrades

New migration `2026101203` adds `pm_coordinator_evidence_contracts` and demotes historical unjustified ADMITTED receipts to SUBMITTED while preserving their signature/payload bytes. The existing `2026101202` CC-03 migration source/checksum is unchanged. Upgrade/reopen and data-integrity checks are covered. Service trust and issuer credentials must be reconfigured securely after a service restart; persisted labels never recreate trust.

## Trusted service integration

1. Provision three separate platform principals for builder, verifier and reviewer. Grant issuer scopes `coordinator:evidence:verify` and `coordinator:evidence:review` respectively. Issue actual IAM sessions; keep their tokens and distinct private signing keys outside candidate images/workspaces.
2. Construct `EvidenceTrust(grants, iam=platform_iam, issuer_tokens=...)` using `IssuerGrant` values from trusted service configuration. Inject it into `CoordinatorStore(db, evidence_trust=trust)`; do not expose this constructor/configuration through receipt HTTP inputs.
3. Register the immutable run job through trusted internal administration using `register_evidence_contract(binding, verifier_id, reviewer_id, case_ids)`. The binding must reflect the authorized operator test contract and selected physical execution.
4. Run the bounded `VerifierAdapter` with that contract; record its envelope as SUBMITTED. Admit through the configured service, with current execution and IAM authority. Repeat independently for structured review; review cannot replace verification.
5. Never pass `trusted_keys` to receipt admission. Never turn test-domain envelopes, runtime observation claims or stdout summaries into production evidence.

## Remaining activation conditions

- `CoordinatorWorker` remains synthetic-only. This correction does not register live Antigravity or Codex adapters, mark board work DONE or deploy a service.
- The offline boundary deliberately has no provider egress or credentials. Live AI execution requires a separately qualified provider broker, approved runtime image and measured candidate/artifact integration. Unsupported/missing CLI discovery fails closed.
- Runtime observations are not proof of a Git commit or integration. The verifier checks exact repository objects separately.
- Execution events are currently bounded observations delivered after the container result. Continuous activity/session persistence and automatic developer/reviewer handoff remain integration work, not completed by this correction.
- Docker is a supervised pilot isolation boundary sharing the host kernel, not a hostile public tenant microVM.
- Codex authored these fixes and cannot independently accept them. Antigravity must review the immutable submitted candidate and execute its own negative probes before any live registry change.

## Verification receipts

Receipt locations are under `/workspace/review-evidence/cc0506-fix/`. Real containers, private temporary repositories/databases and fixture-only signing keys were used; no live model requests or real secret values were printed.

- CC-05 implementation: `70e446cb`.
- CC-06 implementation: `e1c0eed3`.
- Initial targeted CC-03 through CC-06 run: 134 passed in 59.91s, zero skips/failures. Additional authorization and integrity tests were subsequently added and verified in the final full gate.
- Final five-stage repository gate: **779 passed in 342.79s, zero failures/skips**, all five stages passed. This includes the final adversarial, revocation, upgrade and browser cases.
- Clean installed wheel: imports outside the checkout, absence of undeclared psutil, durable upgrade/reopen, default disabled admission and actual restricted container execution all passed.
- Ruff and `git diff --check`: passed. No coordinator containers remained after the gate.
- Local research asset/link check: passed (its scope is research assets, not an assertion of all repository documentation correctness).

**Delivery state:** implemented and submitted for separate review. No self-issued architectural approval, live model execution or production readiness claim.
