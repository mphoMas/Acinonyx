# Candidate export and Git integration contract — proposed v1

Contract ID: `mas-candidate-integration-v1`. Design owner: Codex; implementation/integration owner: Antigravity. Antigravity design acknowledgement pending. Work package: `CC-09/candidate-integration`, retaining the existing CC-09 task. Status: proposed contract, not Git write permission or an implemented export API.

## Candidate provenance

The guest produces bounded changed-file data, not a trusted commit claim. It has no host Git credentials, repository metadata, hooks or control database. The trusted exporter receives an immutable candidate proposal and builds Git objects using the operator-selected repository and exact authorized base. Never execute guest-supplied shell commands, Git helpers, hooks, patch scripts or artifact instructions.

Proposal fields (exact keys): schema=`mas-candidate-integration-v1`, proposal_id (UUID), base_commit_sha (exact 40-character supported Git SHA), files (nonempty bounded list). Each file contains exactly path, operation (`WRITE`/`DELETE`), expected_base_blob_sha (or null for a genuinely new file), and content_base64 (null for DELETE). Digest the decoded content and canonical proposal on the host. A missing expected base for an existing file is a conflict.

The host stamps tenant/project/issue/task/attempt/run, generation, authenticated builder, repository immutable identity, scope/policy revision and transport receipt. Supplied IDs, digests, commits, timestamps and signatures cannot overwrite these fields.

Limits match the current bounded snapshot: at most 256 regular files and 2 MiB total decoded content; source/runner-specific limits remain stricter. Reject absolute/traversal/duplicate/ambiguous paths, symlinks/hardlinks/submodules, forbidden credential/control paths (`.git`, `.ssh`, `.aws`, `.env*`, key stores), unapproved file types/modes and files outside the admitted whitelist. Enforce deployment file-name/case semantics and reject conflicting case aliases. A WRITE for an empty file is distinct from DELETE. Artifact references are service-owned content addresses, never arbitrary URLs or paths to fetch.

Tests or CI changes are permitted only when explicitly authorized, and cannot rewrite the external owner-controlled verification oracle. Frontend/backend ownership is enforced by the admitted task scope; an Antigravity runtime cannot expand its scope into Codex-owned frontend work by proposing a file.

## Durable export and candidate construction

1. Validate current issuer/session, job generation, authorized repository/base and proposed scope before consuming the deduplication key.
2. Atomically store the proposal digest, scope/policy binding and durable export intent. Same ID/same digest replays the original receipt; changed content conflicts. Crash or disconnect cannot create an untracked candidate.
3. In a private trusted staging/object area, construct the exact candidate tree and commit from decoded regular files. Use a controlled Git configuration, disabled hooks/helpers and no guest `.git` data. Preserve the operator/user checkout; never reset, clean or stash it automatically. Do not run tests during export.
4. Record commit SHA, tree SHA, base SHA, diff digest, artifact digest, scope revision and exporter identity. Export is a proposal, not evidence that tests passed. A nonexistent or substituted base/candidate is rejected.
5. Verification and independent review target these exact objects and contract hashes. Every content, base, scope or policy change invalidates applicable prior approval. Rework produces a new immutable candidate; historical artifacts remain attributable.

Creating a file-backed working area is an implementation choice for the trusted exporter, not permission for agents to edit the CEO's working tree. Use bounded resources and lifecycle cleanup; no candidate file may execute in the exporter host process.

## Integration and authority

Git integration is a separate durable action, performed by an authenticated merger principal under explicit repository/branch policy. A developer, broker request, guest event, model approval or planning document cannot grant merge/push/release power. Preserve required separate human approval of the exact candidate where the existing workflow demands it.

The integration intent binds repository identity, allowed target ref, expected target commit, candidate/tree SHA, current verification/review receipts, policy/generation and authorization reference. Perform compare-and-swap on the exact target. No force-push, deletion, silent conflict selection, or title-based repository selection is permitted.

If the target advanced, revalidate dependencies and construct a new integrated candidate. Merge/rebase output is a different commit and must be reverified/reviewed; an approval for a development branch cannot certify different integrated code. Report conflicts for bounded rework or human scope decisions. A protected-branch rejection is a blocker, not permission to bypass protection.

Persist INTENDED before the write and CONFIRMED after rereading the ref. On lost acknowledgement, query actual Git state and compare exact objects before retrying. Unknown remote state is UNKNOWN_INTEGRATION; preserve the original intent and do not blindly repeat a write. Repository permissions and session revocation are checked again immediately before mutation.

## Completion and rollback

The board may show candidate exported, verified, reviewed and integration confirmed as distinct states. DONE requires the existing FSM guards and the exact integrated candidate's required evidence/approvals. Deployment and release remain separate. Rollback is an authorized revert/new candidate against the current ref, with its own validation; automatic reset/force-push is forbidden. An emergency stop pauses admissions without rewriting history.

## Acceptance

- A real sandbox-generated change exports to a real immutable Git object without modifying a dirty operator checkout or exposing Git credentials.
- Malicious paths, modes, aliases, symlinks, oversized artifacts, stale bases, unexpected base blobs, scope expansion and changed-ID replay fail atomically.
- Concurrent target updates cause conflict/revalidation; stale review cannot approve merged/rebased code.
- Crash at export/integration commit and lost remote acknowledgement recover by durable receipts and exact ref reconciliation, without duplicate effective mutations.
- Revoked merger, unapproved refs, protected-branch rejection and missing human authorization block integration.
- General repository verification is not inferred from existing solve-contract results. Candidate integration must use the separately qualified workflow profile described in the loop contract.
