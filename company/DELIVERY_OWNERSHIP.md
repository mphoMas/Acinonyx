# Delivery ownership: Codex and Antigravity

Effective: 9 October 2026. Authority: the project owner's assignment in this conversation.

Codex owns frontend development, UX/UI design, design direction and art direction. The Antigravity development team owns backend development, the engine and the remaining technical implementation. Both work against agreed interfaces and measured acceptance criteria. The project owner sets priorities and makes final product and release decisions. On 9 October 2026 the owner additionally assigned Codex coordination of the full hotel delivery lifecycle across all nine epics, explicitly retaining this implementation split.

This agreement supersedes the earlier proposal that Codex should initially implement backend contracts, IAM and coordinator changes. Those implementations now belong to Antigravity. Codex remains available for architecture critique, acceptance definition and review, especially where engine behavior affects the product experience.

## Ownership

| Area | Accountable delivery owner | Collaboration |
| --- | --- | --- |
| Hotel delivery lifecycle coordination, dependency/readiness reconciliation and cross-epic acceptance tracking | Codex | Antigravity supplies backend delivery evidence; the owner resolves product decisions and approves release. Coordination does not confer backend implementation or runtime authority. |
| Frontend implementation | Codex | Antigravity supplies documented APIs and integration support. |
| UX, navigation, interaction and product-facing information architecture | Codex | The project owner sets product goals; Antigravity confirms technical constraints. |
| UI design, design system, accessibility, responsive behavior and frontend performance | Codex | Antigravity reviews backend assumptions and independently checks integration where appropriate. |
| Art direction, visual identity, typography, colour, illustration, imagery and motion | Codex | The project owner makes final brand/product decisions. |
| Backend APIs, domain logic, engine, coordinator, capability broker and orchestration | Antigravity development team | Codex reviews user-facing contracts and can challenge architecture and evidence. |
| IAM, tenancy, persistence, audit, witness integration, migration, providers and execution workers | Antigravity development team | Separate review and the applicable acceptance gates remain required. |
| Infrastructure, CI/CD, packaging, service observability, operational recovery and backend performance | Antigravity development team | Codex provides frontend requirements and verifies product-facing behavior. |
| Shared API/data contracts and end-to-end acceptance | Joint agreement; each task names one delivery owner | Codex defines what the interface needs to present; Antigravity defines and implements server behavior and enforcement. |
| Task priority, scope disputes and final release approval | Project owner | Both teams provide evidence, tradeoffs and recommendations. Existing explicit authorization still applies. |

Ownership means responsibility for delivery, not exclusive knowledge or an automatic permission grant. Either side may investigate or propose improvements. Cross-boundary changes require coordination through the task and contract; routine work inside an agreed scope does not need repeated permission requests.

## Frontend and backend boundary

Codex's normal edit scope includes `portal/`, `mas/dashboard/static/`, frontend templates, visual assets, the design system and frontend/browser interaction checks. Existing mixed files, including `acinonyx_scrum.html`, must be assigned explicitly rather than edited concurrently.

Antigravity's normal edit scope includes backend Python under `mas/`, server-side handlers, API/CLI/MCP implementations, engine and data migrations, infrastructure configuration and backend tests. `mas/dashboard/server.py` is backend-owned; its HTTP contracts and the frontend consuming them are agreed jointly. The static dashboard assets remain Codex-owned despite being under `mas/`.

These paths are a starting map, not a blanket allowlist. Every task specifies its actual allowed files. Shared configuration, documentation, browser tooling, generated assets and integration tests receive an explicit owner per task. A browser tool implemented in the engine is backend work; browser tests of the product UI are frontend work.

Frontend controls display server decisions. They must not replace authorization, tenancy, budget enforcement, verification or approval rules with client-side checks. Mock UI data is labelled and cannot become completion or release evidence.

## Antigravity development team versus supervised coding swarm

| Property | Antigravity development team | Supervised coding swarm |
| --- | --- | --- |
| What it is | The development team assigned backend/engine engineering work | The bounded `mas-swarm` workflow implemented in this repository |
| Supported work | Scoped repository engineering: backend services, APIs, engine, infrastructure and reviewed tests/docs | Generate a Python `solve(payload)` function from an operator-owned goal and test contract |
| How it works | Inspects and edits authorized files, runs relevant checks and submits patches through the development workflow | Fixed architect/engineer/reviewer model calls, restricted Docker execution, host-owned verification, then separate human approval |
| Authority | Only the repository, service and runtime permissions actually granted for the task | Authenticated requester/approver/owner permissions for the configured store; platform IAM only when explicitly bound |
| Limits | Task scope, actual environment access, review and applicable acceptance gates; no assumed production administrator rights | Bounded calls, context, usage, resources and deadlines; no arbitrary repository editing, desktop access or automatic deployment |
| Completion evidence | Candidate-specific patches and actual runner results, reviewed separately from the builder | Exact candidate/suite/image/run-bound verifier outcomes and the required separate approval |
| Release power | Development ownership does not itself authorize production activation or certify its own changes | Model agreement cannot approve release; a distinct authenticated human approver is required |

Antigravity may submit a suitable bounded task to the supervised coding swarm only through an authorized requester path. Team membership does not automatically grant requester, approver, owner or IAM-admin permissions. A team may act as the submitter; it does not thereby become the verifier or separate human approver. Exported source still needs normal repository integration and acceptance.

This document changes development responsibilities. It does not provision credentials, grant runtime permissions, broaden admitted adapters or complete a consolidation gate. See the [swarm scope](../docs/architecture/SUPERVISED_SWARM.md), [shared identity permissions](../docs/architecture/SHARED_SWARM_IDENTITY.md) and [consolidation acceptance register](../docs/architecture/MAS_CONSOLIDATION_ACCEPTANCE.md).

## Task handoff and review

1. Keep tasks in MAS-PM, the existing planning source of truth. Record the task ID, desired outcome, one delivery owner, allowed files, contract/version, dependencies, acceptance checks and separate reviewer. Use the [handoff template](../templates/development-handoff.template.md).
2. For a product feature, Codex defines the flow and required UI states. Codex and Antigravity agree on the API shape, permissions, loading/error behavior and compatibility before either changes the shared interface.
3. Work on separate branches/worktrees when development overlaps. Do not edit the same files concurrently. Each work package names its integration owner; frontend packages normally belong to Codex, backend packages to Antigravity, and a mixed package names one owner explicitly.
4. Deliver the patch, actual check commands/results, screenshots for relevant UI changes, assumptions and remaining issues. A proposed test or model-generated report is not evidence that a check ran.
5. The other side may review and challenge the change. If the builder also fixes review findings, the separate reviewer rechecks the changed candidate. AI critique and passing checks do not replace a required human release decision.
6. Preserve the current behavior and authority boundaries until the applicable acceptance gates qualify their replacement. Do not silently migrate historical identity/state or admit unsupported capabilities.

## Acknowledgement

The project owner assigned this split. Codex has recorded and adopted it. Antigravity recorded formal acknowledgement on 9 October 2026 in [the project handoff](../projects/platinum-lodge/planning/ANTIGRAVITY_HANDOFF.md#formal-antigravity-delivery-team-acknowledgement) and [backend discovery](../projects/platinum-lodge/planning/BACKEND_DISCOVERY.md), published at commit `5e96bf95`. This replaces the earlier pending-acknowledgement status. The acknowledgement and reported desktop board-sync evidence do not themselves certify backend implementation, task completion, authenticated cloud assignment or any release gate.

Codex coordinates the full multi-property hotel delivery lifecycle. Antigravity retains backend/engine implementation. Git remains the shared handoff mechanism; runtime task state, reviewers and permissions must be verified in the actual configured MAS-PM instance.
