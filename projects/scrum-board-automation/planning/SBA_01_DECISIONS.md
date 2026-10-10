# SBA-01 decisions and acknowledgement register

Draft decisions: use explicit stable project registration; publish structured plans with optimistic concurrency; keep MAS-PM runtime authority; authenticate agent events server-side; persist attributable activity and verified evidence separately; preserve the FSM; use incremental polling first; require actual Antigravity runtime proof.

Implementation owners: Antigravity owns proposed v1 backend, migrations, adapter and recovery. Codex owns board integration and UX. Codex coordinates the interface. Individual runtime principals and separate reviewers remain to be appointed through authenticated deployment administration.

Before joint sign-off, Antigravity records:
1. Actual runtime startup/progress/completion hooks and durable retry implementation location.
2. Accepted project registry and source branch configuration, migration of existing SBA/PLG identities.
3. Session transport and authenticated portal serving design; identity/critic mapping.
4. Transactional event/outbox persistence and retention/resync implementation.
5. Candidate/evidence validation implementation and artifact origin policy.
6. Exact accepted contract commit/digest, deviations and integration test commands.

Acknowledgement: PENDING; no external message sent. Separate reviewer: PENDING. Execution grant: none created. Runtime SBA-1 remains BACKLOG because the proposal is not jointly accepted and the project has zero allocated execution appetite.

Review verdict: APPROVED WITH CONDITIONS as a design proposal only. Conditions are joint acknowledgement, independent review and measured C1–C6 evidence before rollout. This self-check is not the required independent review.

Validation performed: checked existing dashboard routes, tenant principal binding, PM models and directed FSM against the contract. Documentation-only change; no backend/API implementation or live integration test claimed.
