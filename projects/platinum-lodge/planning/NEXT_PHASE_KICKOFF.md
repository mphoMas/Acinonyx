# Discovery and foundations kickoff

9 October 2026. The owner authorized starting the next phase and using the open Antigravity IDE. Desktop control is not attached to this cloud session; no IDE interaction, message delivery or Antigravity execution is claimed.

## Work started by Codex

- Inspected the actual MAS Scrum portal and confirmed it consumes MAS-PM, not Jira.
- Verified PLG contains 55 records and 92 blocker edges in the cloud workspace.
- Prepared a repeatable desktop import through existing MAS-PM APIs, preserving existing states, assignments and evidence.
- Added a frontend distinction between planned delivery ownership and authenticated executor; direct project navigation and project changes show unsprinted planning work.
- Prepared the first frontend journey/state specification below. These are discovery design hypotheses, pending hotel interviews and shared API agreement.

No production gate has passed. Starting specifications does not complete the staff study, scope decisions or backend foundations. This phase authorization does not authorize a later production rollout.

## Desktop synchronization

In the actual `/home/acinonyx/Desktop/MAS` checkout, preserve uncommitted work and confirm the correct remote/branch before integrating. The board integration is published on `plan/platinum-lodge-board`, based on the current ownership/frontier baseline; the hotel prototype remains on its separate feature branch.

After a reviewed integration of `portal/scrum.html` and `projects/platinum-lodge/planning/` into the desktop checkout, use its normal configured Python environment from the repository root:

```sh
python projects/platinum-lodge/planning/import_board.py
python projects/platinum-lodge/planning/import_board.py --apply
```

The default database is the target repository's `mas_pm.db`. If the running dashboard uses another configured database, pass its actual path with `--database`; do not guess a tenant database or bypass authorization. Import adds only missing planning records and blocker edges. Existing workflow states, assignees, budgets, evidence and reviews are preserved. The stable source-to-local-key mapping is printed because an existing desktop PLG project may allocate different issue numbers. No agent is dispatched.

Serve/open the board through the normal dashboard, preferably `http://127.0.0.1:8080/portal/scrum.html?project=PLG`, using the local server's required authentication. Choose **PLG** and **All Sprints**. A `file://` page falls back to the local 8080 API and may face origin/authentication restrictions; serving it through the dashboard is preferred.

Actual executor binding must use the authenticated assignment workflow after registered principals are identified. Do not put 'Codex', 'Antigravity' or 'admin' into a field and treat that as verified authority. The board can show the agreed delivery owners before executor binding.

## Antigravity development-team launch instruction

> Read `company/DELIVERY_OWNERSHIP.md` and the Platinum Lodge planning package. Acknowledge the split in MAS-PM. You own backend/data/security/infrastructure; Codex owns frontend/UX/design/art direction. The supervised coding swarm is a separate bounded actor. Identify your actual authenticated principal and check the local PLG key mapping. Begin discovery work D3–D6 when their actual blockers are satisfied: jurisdiction/financial policies, regional provider feasibility, architecture/capacity/cost and execution-plan synchronization. Prepare ADR options, a versioned API proposal and a scoped first foundation task. Preserve the prototype's tested behavior through contracts. Do not silently merge the old feature branch, invent scope decisions, bypass dependencies, fabricate reviewer approvals or deploy. Return commits and actual evidence; unresolved owner/finance/provider decisions remain visible blockers.

This instruction is prepared for the IDE; it has not been delivered. The next backend implementation package is F1/F2 after G0 discovery decisions. Propose refinements and parallelizable subtasks rather than changing the backlog's dependencies unilaterally.

## Codex frontend discovery specification

| Journey | Required interface | Critical states / safeguards | Backend contract needed |
| --- | --- | --- | --- |
| Enter property workspace | Explicit authorized property selection; persistent property label; role navigation | No accessible properties, revoked membership, loading, stale prior response; no default to another tenant | Authorized memberships/capabilities and property metadata |
| Create/amend reservation | Availability calendar; room/type/date/guest/rate details; policy and price summary | Sold-out/concurrency conflict, changed version, invalid dates, capacity, uncertain acknowledgement; preserve input and operation key | Scoped availability, policy/price snapshot, reservation version, idempotent commands |
| Check in guest | Arrival task list; eligibility and room readiness; confirmation | Unready/blocked/occupied room, deposit/payment exception, unauthorized override; explain next action | Server-derived eligibility, readiness, payment status and action permissions |
| Settle and check out | Readable folio, split/routed charges, tender choice, invoice/receipt | Pending/unknown provider outcome, partial settlement, refund approval, credit balance, version conflict | Journal-backed totals, allowed tenders, payment/refund state, tax document and settlement commands |
| Assign/complete room work | Mobile assigned list, arrival priority and quick room update; supervisor inspection | Stale/reassigned task, concurrent change, offline read-only, inspection required; readiness distinct from occupancy | Assignment, room states/versions, permission capabilities and freshness events |
| Resolve room failure | Inventory/guest impact and relocation choices | No suitable room, in-house guest, future bookings, concurrent allocation; accountable escalation | Out-of-service impact, protected relocation commands and audit |
| Manage multiple properties | Portfolio overview, separate currencies, prioritized exceptions and drill-down | Partial/stale property data, insufficient permission, no silent cross-property action | Permission-scoped aggregates, metric definitions, exception owner/age/source/action |

Reusable component inventory: property selector/context header; task queue; accessible calendar/table; guest lookup with minimal disclosure; validated form; money/currency display; folio/journal view; operation-status banner; conflict dialog; room-status badge; mobile assignment card; confirmation dialog; empty/error/stale states; safe export action.

Interaction rules: keyboard first for reception, touch-friendly housekeeping, semantic status text plus color, readable density, preserved inputs and explicit irreversible financial intent. Property switches invalidate cached context and handle unsaved forms. All consequential decisions originate in server policy; hidden buttons are not authorization.

Art direction: preserve the prototype's forest-green/cream identity, improve readable typography and contrast, minimize decorative imagery in operating screens, and maintain an approved-rights register for actual hotel photography. EN/PT labels and instructions need human operational review.

Next Codex deliverables: interview/task baseline protocol (D2), full journey inventory (U1), tokens/component specifications (U2), then property shell and API client against agreed contracts (U3/U4). API proposals are for joint review; Codex does not implement backend policy. Do not claim measured productivity before staff trials.


## Codex delivery candidate — 9 October 2026

Review `planning/codex/DELIVERY_REGISTER.md` on `feat/platinum-lodge-codex-delivery`. It maps all 13 Codex-owned work packages to frontend previews, specifications, discovery/measurement and training drafts, evidence and remaining acceptance gaps. Owner has confirmed Mozambique and Excel as the current workflow baseline. Multi-property release-one scope remains; owner selected Platinum Hotel as the sole initial pilot, with live second-property acceptance deferred to expansion. No packages are declared DONE and no runtime assignment/dependency was bypassed. Backend/API work remains with the Antigravity development team.
