# Development handoff: <task title>

- MAS-PM task ID: <existing task reference; do not create a competing task board>
- Outcome: <one concrete behavior or artifact>
- Delivery owner: <Codex for frontend/design/art direction; Antigravity for backend/engine>
- Integration owner: <one named owner, particularly for mixed work>
- Separate reviewer: <someone other than the builder>
- Baseline / branch / worktree: <revision and isolated edit location>
- Allowed files: <explicit paths; list shared-file ownership>
- Excluded scope: <what this task must not change>
- Dependencies: <accepted contracts or upstream tasks>
- API/data contract: <version, request/response shapes, permissions and compatibility>
- UI requirements, if applicable: <design references, responsive/accessibility expectations, loading/empty/error/denied states>
- Acceptance checks: <expected behavior, negative cases and relevant runner commands>
- Required authority: <actual permissions needed; never credentials or bearer values>
- Delivery evidence: <patch, executed results, relevant screenshots and unresolved issues>
- Acknowledgement: <owner/reviewer receipt; record pending until confirmed>

The [delivery ownership agreement](../company/DELIVERY_OWNERSHIP.md) governs this handoff. Antigravity development-team ownership is distinct from `mas-swarm` runtime permissions. Bounded swarm tasks need their own operator-owned test contract and authenticated submission; the separate human approval requirement remains enforced.
