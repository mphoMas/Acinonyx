# Platinum Lodge integration branch

Use `integration/platinum-lodge` as the shared review and merge target for Platinum Lodge work. It is an integration candidate, not production approval. The source branches remain available.

## Included source heads

| Source branch | Integrated revision | Relationship |
| --- | --- | --- |
| `plan/platinum-lodge-board` | `93e500d37775954a475750f2c402cd409d97779c` | Already contained in Codex delivery. |
| `plan/platinum-lodge-initiation` | `c9239a1b830195459c5486ed7c9d13c44e45f624` | Already contained in frontend foundations. |
| `feat/platinum-lodge-codex-delivery` | `076f012d5e27e528fa749ea3d4a64d073b0ea5a0` | Integration starting point; includes current delivery candidate and reconciled pilot planning. |
| `feat/platinum-lodge-frontend-foundations` | `920641f42cfc3bf1ad9425a8b1e6bf9294a82bc1` | Merged with an explicit merge commit; includes initiation and prototype management. |
| `feat/platinum-lodge-management` | `2c1f063b4fd8369ccb0f89cf1ed4dd45864f465b` | Already contained in initiation and frontend foundations. |

Later changes on other branches are not automatically included. In particular this does not replace or update `main` or automatically incorporate later `Acinonyx_frontier` changes.

## Conflict resolution

Eight add/add conflicts affected `ANTIGRAVITY_HANDOFF.md`, `BACKLOG.csv`, `BACKLOG.json`, `BACKLOG.md`, `BENCHMARKS_AND_ACCEPTANCE.md`, `DECISION_REGISTER.md`, `EVIDENCE.md` and `PROJECT_PLAN.md` in this planning directory.

Retained the Codex delivery versions as the active planning documents because they incorporate newer pilot decisions, ownership coordination and readiness reconciliation. Earlier initiation versions remain reachable in the merged Git history; they are not independent current decision registers. The hotel prototype, frontend foundation code, screenshot/report and design-preview assets from both lines of work remain present. Prototype and design preview are still distinct implementations; this merge does not implement the planned production backend or declare acceptance gates passed.

## Validation performed

Against the combined source, using Node 24.19.0:

- `npm run check`: server and application JavaScript syntax passed.
- `npm test`: six hotel workflow cases passed; zero failures/cancellations/skips.
- `node --test test/browser/model.test.mjs`: six design-preview model/contrast cases passed; zero failures/cancellations/skips.

No fresh browser, live provider/payment, load or production deployment qualification is claimed. Existing historical screenshots and test records retain their original scope.

## Ongoing merge workflow

1. Fetch `origin` and branch new work from `origin/integration/platinum-lodge`.
2. Open each change as a pull request with **base `integration/platinum-lodge`**. Reconcile contract/planning changes and run the relevant application/preview checks before merging.
3. Keep planning decisions and backlog exports consistent; do not overwrite newer scope with older branch snapshots.
4. Promote the reviewed integration candidate to `main` through a separate pull request when its declared release gates are satisfied. Integration alone is not a production release.

No branch protection or default-branch settings have been changed. Configure required reviews/status checks in GitHub separately if enforcement is desired; this document establishes the intended workflow only.
