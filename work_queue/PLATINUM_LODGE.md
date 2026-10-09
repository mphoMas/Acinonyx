# Platinum Lodge pickup from Git

Updated 9 October 2026. The project owner requested publication to the Git-backed Scrum board so Antigravity can pick up the next phase.

## Queued coordination work

| Allocation ID | Delivery owner | Proposed execution role | Blockers |
| --- | --- | --- | --- |
| PLG-BOARD-01 | Antigravity development team | backend_engineer | None: synchronization and acknowledgement first |
| PLG-BE-01 | Antigravity development team | backend_engineer | PLG-BOARD-01 |
| PLG-FE-01 | Codex | frontend_engineer | PLG-BOARD-01 |
| PLG-CONTRACT-01 | Antigravity development team; jointly agreed interface | backend_engineer | PLG-BE-01 and PLG-FE-01 |

These are coordination tickets in the existing MAS Git queue. The **55-record hotel delivery backlog remains in project PLG**, with its nine epics, 45 work packages and 92 blocker edges. Do not duplicate all PLG work into MAS or create a competing Jira board. [Project plan](../projects/platinum-lodge/planning/PROJECT_PLAN.md), [portable records](../projects/platinum-lodge/planning/BOARD_RECORDS.json), [kickoff](../projects/platinum-lodge/planning/NEXT_PHASE_KICKOFF.md).

The proposed role names match existing queue conventions. They are not proof of authentication, permission grants, active agents or Antigravity acknowledgement. Each ticket has a distinct proposed QA reviewer. Zero token appetite is planning-only: establish actual identities, scopes, prerequisites and approved allowances before implementation. No task is preapproved, dispatched or marked DONE by this publication.

## Antigravity pickup instruction

1. Synchronize the desktop checkout with `Acinonyx_frontier`, preserving local changes. Read `company/DELIVERY_OWNERSHIP.md`, this file and the planning package.
2. Verify the Git queue import using the configured dashboard/workflow. Identify your actual authenticated principal; map it to the proposed role through the authorized assignment workflow rather than self-asserting another identity.
3. Pick up PLG-BOARD-01 first. Confirm the dashboard's actual database, then preview and apply the portable PLG planning import from the repository root using the configured Python environment:

```sh
python projects/platinum-lodge/planning/import_board.py
python projects/platinum-lodge/planning/import_board.py --apply
```

If the dashboard uses another authorized database, pass its actual path with `--database`. Do not guess tenant paths. Preserve the printed source/local key mapping. Confirm 55 mapped records and 92 edges, visible under PLG / All Sprints. Existing states, assignees, budgets, evidence and reviews are not overwritten by this importer.

4. Record ownership acknowledgement and actual board/import evidence, then submit the coordination ticket for independent review under the normal FSM. Subsequent tickets become eligible only when their blockers are actually DONE.
5. Antigravity owns backend discovery and implementation; Codex owns frontend, UX/UI, design and art direction. The supervised coding swarm does not have general hotel application engineering or deployment authority.

The earlier frontend candidate is on `feat/platinum-lodge-frontend-foundations`, commit `920641f42cfc3bf1ad9425a8b1e6bf9294a82bc1`. This queue publication adds planning and board integration to frontier; it does not merge the older hotel prototype or alter backend APIs.

Git publication requires a local fetch/pull before an offline desktop can see it. No IDE delivery, local synchronization, authenticated executor binding or Antigravity execution is claimed from the cloud workspace.

## Codex work available for review

Branch `feat/platinum-lodge-codex-delivery`, commit `836c2721`, now contains a review register for all 13 Codex-owned PLG work packages, an interactive fictional-data frontend preview, design/contract requirements, an Excel baseline observation template and training/continuity drafts. [Delivery register](https://github.com/mphoMas/Acinonyx/blob/feat/platinum-lodge-codex-delivery/projects/platinum-lodge/planning/codex/DELIVERY_REGISTER.md).

Owner confirmed Mozambique as the launch country and Excel as the current workflow baseline; multi-property capability remains release-one scope. A second participating property and real staff measurements remain unconfirmed. Five unit tests and 28 selected browser checks passed. These candidates do not complete backend integration, Portuguese review, staff studies or production qualification. Runtime ticket states and blocker edges remain authoritative and unchanged. Review the candidate for PLG-FE-01 preparation and jointly agree PLG-CONTRACT-01 before production integration.

## Full lifecycle coordination

Owner confirmed Codex coordinates the nine-epic delivery lifecycle with Antigravity retaining backend/engine implementation. [Lifecycle and all 45 packages](../projects/platinum-lodge/planning/DELIVERY_LIFECYCLE.md) and [Codex contract review](../projects/platinum-lodge/planning/CODEX_CONTRACT_REVIEW.md) are the current pickup references. Antigravity's formal acknowledgement at `5e96bf95` is recorded; actual runtime assignment/review and gates remain separately verified. Run `planning/lifecycle_status.py` against the configured MAS-PM database for live dependency/state reporting without transitions.

Owner's subsequent clarification selects Platinum Hotel only for the initial live pilot and no existing payment provider. Read SCOPE_AMENDMENT_2026_10_09.md before treating the historical two-property/provider assertions as cleared decisions. The frontier decision register now keeps statutory/provider verification open. Candidate frontend is `076f012d` on `feat/platinum-lodge-codex-delivery` (six unit tests, 36 browser checks). Preview then apply `planning/link_delivery_evidence.py` in the actual configured governance environment to attach published references; cloud signing configuration is absent and no board completion is claimed.
