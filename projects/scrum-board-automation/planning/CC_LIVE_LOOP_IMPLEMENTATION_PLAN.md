# Live coordinator integration implementation plan

Date: 12 October 2026. Architecture/planning owner: Codex. Backend integration owner: Antigravity. Project: existing SBA. Branch: `feat/scrum-board-automation`. This is a reviewable proposed plan; contract acknowledgement, authenticated plan publication and runtime assignments are separate actions. No second project/board/branch is created.

## Baseline and immediate gate

Implementation baseline: CC-05 `70e446cb`, CC-06 `e1c0eed3`; delivery `ce9840c9`. Author validation: 779 tests, zero failures/skips. Antigravity corrected its conditional review in `5c661118`: offline checks are accepted, the full gate failed without Docker, and independent actual-container execution remains unproved; see [review reconciliation](CC_05_06_REVIEW_RECONCILIATION.md).

The current registry is synthetic-only. The verification foundation supports operator-owned solve(payload) cases. No provider credential broker, safe Git export/integration, continuous runtime feed or automatic real developer/reviewer handoff is claimed implemented. Prototype/design work may proceed, but live registry admission requires the independent evidence gate and package-specific qualification.

## Package sequence, owners and existing task identities

References in this table are packages within existing tasks, not new board tickets or competing identity records. Preserve task UUIDs, deployment issue mappings, assignees, spend and runtime history.

| Order / package | Existing task | Delivery owner | Separate review | Readiness and acceptance artifact |
| --- | --- | --- | --- | --- |
| P0: independent container acceptance | CC-05 / CC-06 | Antigravity reviewer | Codex reconciles evidence; cannot self-accept authored code | Corrected review received; missing-Docker typed-error fix and real Docker probes against immutable candidates |
| P1: broker protocol and mediated runtime | CC-05 | Antigravity | Codex implementation review; Antigravity first acknowledges Codex's draft | [Provider broker contract](CC_PROVIDER_BROKER_CONTRACT_V1.md); P0 before live qualification |
| P2: candidate export and integration intent | CC-09 | Antigravity | Codex | [Git contract](CC_CANDIDATE_INTEGRATION_CONTRACT_V1.md); accepted containment foundation; real producer before live export acceptance |
| P3: repository-profile verifier and reviewer | CC-06 extension | Antigravity | Codex | Exact P2 candidate, externally controlled suite/oracle, P1 for model review; preserve current solve profile |
| P4: durable runtime activity/backend feed | SBA-04 | Antigravity | Codex | [Activity contract](CC_ACTIVITY_BRIDGE_CONTRACT_V1.md); accepted storage foundation; live qualification uses P1/P2/P3 |
| P5: live board polling/recovery | SBA-06 / CC-10 | Codex | Antigravity | Acknowledged P4 read contract and actual backend fixtures; mock UI work cannot certify runtime |
| P6: bounded automatic correction | CC-07 | Antigravity | Codex | [Loop contract](CC_AUTOMATIC_LOOP_CONTRACT_V1.md); P1–P4 accepted for the declared task profile |
| P7: recovery/adversarial qualification | SBA-07 / CC-13 | Antigravity | Codex | P5/P6 plus existing CC-08 policy changes, CC-11 cancellation and CC-12 operations controls |
| P8: zero routine CEO relay | SBA-08 / CC-14 | Codex coordinates | Antigravity and required separate human approver | Real provider, runtime, candidate, verification, review, deliberate correction and browser receipts from P7 |

SBA-09 / CC-15 startup automation follows SBA-08 as already planned; it is not a prerequisite for removing routine message relay after one authorized kickoff.

## Dependency interpretation

The coarse existing backlog dependencies remain planning references, not authority. In particular, CC-09 depends on the accepted CC-06 **foundation**; the subsequent CC-06 repository-profile extension depends on P2 candidate export. Do not add a reciprocal CC-06→CC-09 dependency to the coarse task DAG and create a cycle.

Before runtime publication, Antigravity and Codex must acknowledge the phase gates and determine whether the actual scheduler requires distinct child tasks for the extension. If it does, publish explicit scoped child identities under the same SBA project through SBA-03, retaining existing parent identity/history. Do not reopen terminal DONE tasks, edit live status in SQL, or interpret a document's package readiness as a dependency completion receipt. Until that reconciliation, packages are engineering/design scopes, not machine-dispatchable new tasks.

## Allowed implementation scope

- P1/P2/P3/P4/P6: Antigravity owns `mas/pm/`, backend API routes in `mas/dashboard/server.py`, relevant `mas/agents/` integration, narrowly necessary scripts/image/CI configuration and backend tests. Each submission names exact edited paths. Shared config changes require an explicit integration owner; no concurrent shared-file edits.
- P5: Codex owns `portal/scrum.html`, frontend assets and browser interaction tests. The server contract stays backend-owned.
- Codex's planning deliverable is these proposed contracts, package map and strengthened existing backlog acceptance. A separate small correction handles the missing-Docker typed-error defect from review `5c661118`; no integration feature, service or credential provisioning is performed.
- Design acknowledgement for all four Codex-authored contracts is pending Antigravity. That is a technical contract agreement, not a new request for the CEO to approve routine drafting.

## Required submissions

Each package delivers: exact candidate commit, one owner, scoped paths, acknowledged contract version, authenticated dependencies/allowances, implementation diff, actual runner receipts, negative/recovery cases, explicit unsupported capabilities and an independent verdict. Claims, mocked tests and skipped checks remain separately labelled. Use [the development handoff template](../../../templates/development-handoff.template.md).

Specifically, provider/runtime discovery must prove the actual requested model identifier and documented mediated CLI protocol. Image pins and secret bindings are configured securely; credentials never enter chat, Git, artifacts or candidate containers. Provider or Git uncertainty holds funding/intent until reconciled rather than causing a blind retry.

## Current next handoff to Antigravity

1. Complete P0 as instructed by `CC_05_06_REVIEW_RECONCILIATION.md` and the corrected review `5c661118`; independently recheck the small missing-Docker typed-error fix submitted by Codex.
2. Review and acknowledge the four proposed contracts. Report concrete incompatibilities with the real agy/codex/provider interfaces; do not assert support from assumed flags.
3. Implement P1's deterministic admission/accounting and mocked transport tests first, explicitly TEST-domain. Prove the mediated transport in an isolated prototype before real provider admission. Secure runtime configuration and independent acceptance precede live registration.
4. Prepare P2 and the P3 external oracle design. If general repository verification cannot yet be qualified, report it unsupported and keep the narrower solve pilot explicit.
5. Agree P4's read/event payload fixtures with Codex, then submit backend feed implementation. Codex can build P5 against agreed fixtures while live integration remains separately gated.
6. Implement P6 only after its declared-profile prerequisites are accepted. Then qualify P7/P8 using a deliberately rejected and automatically corrected real candidate.

## Planning/publication state

`BACKLOG.json` is the reviewed repository planning source; actual board statuses and authenticated assignments remain MAS-PM-owned. This update adds acceptance references to existing records and changes CC-09's planning priority to CRITICAL. It grants no funding and sets no task DONE. No authenticated board publication is claimed by this document. Use the supported plan publisher with expected_previous_revision to stage active scope changes safely; preserve runtime fields and surface reconciliation requirements.

## Draft validation

- All 20 existing planning records and unique task UUIDs preserved.
- Existing dependency edges, owner/path scope, runtime status and zero appetite preserved; dependency graph checked acyclic.
- Existing acceptance requirements preserved as a prefix; new contract requirements appended to eight existing task records.
- Nine relative document links checked and present; JSON parses; `git diff --check` passed.
- These proposed contracts do not implement integration features. The 779-test result above belongs to the prior corrective implementation. Focused results for the separate missing-Docker typed-error correction are recorded in its delivery note; no live integration result is claimed.

The separately submitted missing-Docker correction is `653e26b3`; [its delivery note](CC_05_MISSING_DOCKER_FIX_DELIVERY.md) records 142 focused tests passing with no skips. Antigravity must independently recheck it as part of P0. This is maintenance of the accepted execution interface, not implementation of the proposed broker/feed/loop.
