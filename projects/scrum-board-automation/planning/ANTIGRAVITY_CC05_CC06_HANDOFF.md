# Next runtime work: CC-05 and CC-06

Date: 12 October 2026. Same feat/scrum-board-automation branch and SBA board. Antigravity owns implementation; Codex performs independent review. This handoff follows CC-04 controlled-only acceptance; it does not authorize live runtime activation or production release.

## CC-05: developer runtime adapter

Implement a supervised headless Antigravity adapter, with explicit task/attempt/run/session separation. Do not treat this interactive IDE/chat as a callable runtime. Reuse approved CC-01 CLI discovery, but revalidate actual installed version/interface in the target deployment.

Run only in a disposable isolated workspace with scoped authority, bounded resources, elapsed time and usage. Keep credentials in secure environment configuration; no chat tokens or committed secrets. Validate requested model availability and fail without silent substitution. Preserve system proxy/CA settings.

Persist launch intent before spawning, capture early runtime session ID, bind output to the exact persisted run/fence and preserve UNKNOWN_EXECUTION on interruption. Conversation resume is a new turn, not proof of exactly-once recovery. Never blindly retry side effects.

Use a real managed process/container execution boundary with confirmed local termination and descendant cleanup; a Boolean supports-stop declaration is insufficient. Remote work/billing uncertainty retains usage holds. Qualify ignored termination, stalled streams, partial/malformed output, revoked authority, crash after spawn and late results. Add the implementation to trusted adapter routing only after independent capability acceptance, not merely because its class exists.

## CC-06: verifier and reviewer runtime adapters

After agreeing the runtime contract, implement trusted verification separately from builder execution and batch Codex review separately from this conversation. Use immutable actual candidate/base/test-contract/policy identities. Candidate changes, stale policy, foreign tenant/run and missing measurements must reject.

Reviewer output text is a claim. A printed APPROVED verdict alone cannot admit evidence or authorize release. Build proper canonical envelope/issuer/key verification and replay controls before enabling the disabled coordinator evidence promotion path. Do not unblock that path merely to pass an integration test. Separate verifier and reviewer authority from developer mutation credentials.

Test a genuine failing Git candidate, forged signatures, candidate swapping, cancellation and budget uncertainty. Preserve required human release approval and task-versus-production-release distinction.

## Submission and integration gate

Start with code/contracts and controlled adapter tests. Live acceptance needs an explicitly authorized bounded task and qualified runtime credentials/environment; use existing owner authorization where applicable and identify concrete missing prerequisites without repeatedly asking for general permission.

Commit implementation/tests and delivery evidence separately where useful. Report exact candidate, commands, test outcomes including skips, remaining capabilities and deployment limitations. Push normally and submit for independent review. Do not force-push, create another board, delete historical state, self-mark implementation accepted/DONE or claim automatic Codex/Antigravity messaging is already operational.

SBA-04 progress/evidence bridge and SBA-06 live frontend integration remain separate shared-contract work; make actual observed events available without inventing running/verified/completed status. End-to-end acceptance must include rejection, correction, resubmission and restart without CEO message relay.
