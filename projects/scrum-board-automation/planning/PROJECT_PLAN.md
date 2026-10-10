# SBA project plan

## Problem and outcome

The existing board displays database records but does not establish the intended conversation-to-agent delivery loop. Its Git queue imports a single declared project from a local manifest; it is not GitHub discovery or autonomous dispatch. Native UI checks reproduced a forbidden transition caused by a hard-coded client principal. Successful rendering and manual creation are insufficient acceptance evidence.

Target: CEO describes a project to the architect/Scrum master; approved planning is persisted, agents receive scoped tasks, and once Antigravity is started, activity updates the board automatically. Evidence and independent review control completion. Task count, Git commits and agent success claims cannot alone certify DONE.

## Delivery sequence

1. SBA-01: agree contracts and ownership; define repository project registration criteria and identity mapping.
2. SBA-02 and SBA-05: discover projects and repair authenticated board actions.
3. SBA-03: connect architect planning publication to durable MAS-PM projects, tasks and dependencies.
4. SBA-04: connect the actual Antigravity runtime to authenticated progress, comments, notes and evidence updates.
5. SBA-06 and SBA-07: live frontend, recovery and adversarial qualification.
6. SBA-08: demonstrate one real project end to end, independently review and request CEO rollout approval.

Codex owns frontend, UX and coordination; Antigravity owns backend/engine and infrastructure. Shared interfaces require recorded agreement. Separate reviewers must be appointed before completion review. The existing ownership agreement remains applicable. No execution budget or provider expenditure is allocated by this planning registration.

## Requirements and release gate

- Discover registered projects from the configured GitHub repository through automatic synchronization. Explicit project identity avoids confusing packages, examples and folders with projects. Surface source revision and synchronization errors.
- Persist conversation-derived plans through an authenticated architect integration. Record revisions, priorities, dependencies, acceptance and owners; reconcile safely without overwriting runtime evidence or reviewed history.
- Bind each agent update to authenticated tenant, task, attempt and source event. Handle duplicates, retries, out-of-order events and disconnections. Retain attributable comments, notes, blockers and evidence links with candidate/test provenance.
- Enforce transitions server-side. Show active work automatically, but gate completion on required verifiable evidence and independent review. Keep blocked, failed, rejected and disconnected states visible.
- Reflect accepted updates within five seconds on a healthy connection. Display freshness and reconnect without losing activity. This is a target to verify, not a present capability.
- Prove persistence through restart, reconcile GitHub failures, reject cross-tenant writes and forged or replayed events, and prevent fabricated evidence from reaching DONE.
- Run the real workflow with native browser evidence: CEO supplies project details, architect publishes the plan, CEO starts Antigravity once, agents execute and the board shows activity through reviewed completion. No CEO import command, SQL or manual ticket move is allowed in this acceptance scenario.

## Scope and dependencies

Manual Antigravity startup is retained for the first board release. SBA-09 then automates branch synchronization and kickoff after the manual end-to-end workflow is qualified. Production deployment, new model-provider selection and broad MAS consolidation are separate decisions. Actual Antigravity event/access integration, authenticated board session support and remote deployment identity must be established during discovery; a simulated producer cannot satisfy live integration acceptance. No production date is committed before that discovery.

Git planning snapshots record intent. MAS-PM retains runtime state, evidence and review. This project is registered in the cloud workspace's local database; remote board visibility and synchronization remain unverified. Do not describe planning registration as automation delivered.
