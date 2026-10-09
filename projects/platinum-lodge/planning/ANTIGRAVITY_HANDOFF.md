# Antigravity development-team kickoff

Read [PROJECT_PLAN.md](PROJECT_PLAN.md), [BENCHMARKS_AND_ACCEPTANCE.md](BENCHMARKS_AND_ACCEPTANCE.md), [BACKLOG.md](BACKLOG.md) and the pinned [ownership agreement](https://github.com/mphoMas/Acinonyx/blob/8b92e33794339d4917e2c0060991c3523d32b605/company/DELIVERY_OWNERSHIP.md).

The owner requires multi-property in release one, with reservations/check-in, billing/payments and housekeeping. You own backend/engine/data/security/infrastructure and their implementation tests. Codex owns frontend, UX/UI, design and art direction. Joint interfaces are agreed before implementation; each issue has one delivery and integration owner.

First action: acknowledge the agreement in the task record; validate backend capacity and feasibility; inspect the prototype and current frontier divergence; propose the transactional database/hosting/identity approach and supported regional payment providers. Do not begin with a broad merge of the older feature branch or infer that hotel identity inherits MAS privileges.

Prioritize organization/property tenancy, concurrent inventory correctness and financial policy/provider feasibility. Preserve tested prototype behaviors through contracts, then implement production foundations. The frontend depends on scoped pagination, capabilities, versions, durable operation keys, safe errors and freshness. Agree OpenAPI and two-org/property fixtures with Codex before shared changes.

Backend scope starts with project server modules, migrations, operational scripts, server tests and infrastructure. `public/` and visual assets are Codex-owned. Package/CI/shared tests require a named owner. The backlog paths are planning bounds; refine precise allowlists before execution. Provide candidate commits, migrations, actual runner evidence and separate review. Do not self-certify or deploy merely because a task is assigned.

The supervised coding swarm is a different actor. It supports bounded Python `solve(payload)` tasks under its existing verifier/approval workflow; it has no general authority to implement or deploy this hotel application. Development-team membership grants no requester/approver/admin credentials.

MAS-PM records were initiated locally and remain BACKLOG with descriptive delivery ownership, no authenticated executor assignment and zero execution-token appetite. Check synchronization to the shared PM instance and bind actual principals through the authorized workflow before staging work. The export is a static snapshot. No external notification, acknowledgement, sprint activation, procurement, provider account or production authorization is claimed.

Return: acknowledgement, backend estimates/capacity, ADR proposals, first contract draft, decision blockers, task splits and independent-review plan. Codex will proceed with frontend inventory/journeys/design-system specifications against the jointly agreed scope.
