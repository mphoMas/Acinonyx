# Provider broker contract — proposed v1

Contract ID: `mas-provider-broker-v1`. Design owner: Codex. Backend implementation/integration owner: Antigravity. Separate design acknowledgement: pending Antigravity. Work package: `CC-05/provider-broker`; retain CC-05's existing task identity. Status: proposed implementation contract, not an implemented endpoint or execution grant.

## Purpose and trust boundary

Allow isolated developer/reviewer runtimes to call an explicitly authorized model without acquiring provider, Git, verifier, reviewer-signing or administration credentials. Preserve the current no-host-mount/no-egress candidate boundary. A trusted host broker performs HTTPS provider calls using the configured session proxy, CA trust, destination policy and protected credentials. Do not disable TLS verification, inject host HTTP proxy credentials into the guest, mount a host socket/home directory, or permit arbitrary provider URLs.

The broker offers inference only. Repository writes, tools, account changes, evidence signing, scheduling and release approval are separate capabilities. Provider output is untrusted text, never a permission or test verdict.

The runtime transport must be proved before implementation is described as live. Prototype bounded bidirectional request/response IPC between the supervisor and guest. A guest-local provider shim may translate the actual supported CLI protocol into that IPC; its requests remain untrusted and host-authorized. The current one-shot stdin/result boundary has no such transport. If agy/codex cannot use a documented mediated provider interface, declare that runtime unsupported; do not invent SDK flags, silently substitute an API/model, or relax egress.

## Admission and service-owned fields

Before accepting a request, the broker obtains the durable admitted job and current lease from the coordinator. It derives tenant, project, issue, task, attempt, physical run, role, issuer, generation, approved provider/model, context/output limits, timeout and reservation from that job. A guest cannot set or override these fields. Each supervisor channel is bound to exactly one physical run and generation. Builder and reviewer channels have separate authorities and prompts.

Recheck current IAM session, assignment, policy, generation, pause/cancellation, provider allowlist and available held budget on every call. No capability is granted by a planning token estimate. No broker call occurs inside a long-running database write transaction.

Guest request fields (exact keys, no extras):

| Field | Type / limit | Meaning |
| --- | --- | --- |
| schema | literal `mas-provider-broker-v1` | Contract version |
| request_id | UUID | Stable ID reused only for the identical request |
| messages | nonempty list, at most 32 items | Each item has exact `role` (`user`/`assistant`) and plain-text `content` |
| max_output_tokens | positive integer, not boolean | Requested bound, at most the approved job allowance |

The combined serialized request is at most 32 KiB; prompts cannot include executable tool specifications. Trusted role instructions are prepended by the host, not accepted from guest `system` messages. The operator-approved model selector comes from the job; guest requests contain no credential, URL, model override or tenant selector. Reject missing/nonfinite/coerced fields before reserving funding. Default provider deadline: 45 seconds, also bounded by the remaining task deadline.

Successful response fields: schema, request_id, status=`SUCCEEDED`, provider_call_id, exact provider/model ID, response_text (at most 16 KiB), provider-reported input/output tokens, and supervisor receipt_id. Integer usage must be validated; do not manufacture zero usage. A provider stream is bounded while reading, not after buffering. An outcome with unavailable usage remains an accounting uncertainty, not ordinary funded success.

## Durable request and accounting lifecycle

1. Atomically create a request record, canonical request digest, run/generation binding, price/configuration revision and bounded sub-reservation. Return identical persisted results for exact replay; changed content under the same ID is a conflict.
2. Persist intent to send before network transmission. States: RESERVED, SENDING, SUCCEEDED, FAILED_CONFIRMED, UNKNOWN_PROVIDER_EXECUTION, CANCELED_BEFORE_SEND.
3. Only a valid, current supervisor can send. A duplicate SENDING request is reconciled rather than resent. Use provider idempotency only where the actual API proves support.
4. Settle confirmed authoritative usage against the authorization ceiling exactly once. Retain shared funding holds on uncertain transmission, timeout after send, missing usage or crash after send. Estimated tokens/cost are labelled estimates and cannot settle the ledger.
5. If actual usage exceeds the reserved ceiling, stop further calls, retain the uncovered liability, emit an accounting escalation and require reconciliation. Never clamp real usage to a fabricated affordable amount.
6. Persist terminal results before acknowledgement. Restart reuses the same request ID and checks provider status where supported. Unsupported reconciliation means UNKNOWN, not an automatic paid retry. Request retries, task rework and provider transport retries share explicit upper bounds.

Currency costs require a versioned operator-approved price schedule and consistent integer units; token and currency allowances are independently bounded. A price/configuration change invalidates unused admissions or requires explicit reconciliation. No prices or execution budgets are granted by this document.

## Audit, privacy and failure semantics

Audit actor, job identity, request/response hashes, exact provider/model, timestamps, measured usage, reservation/settlement IDs and safe error category. Do not log tokens, raw credential values or unrestricted prompts. Sensitive prompt retention requires a separate owner-approved retention policy; logging failure must be visible and block mandatory-audit calls.

Use bounded errors: INVALID_REQUEST, AUTHORITY_DENIED, STALE_GENERATION, POLICY_CHANGED, BUDGET_EXHAUSTED, UNSUPPORTED_RUNTIME, UNSUPPORTED_MODEL, PROVIDER_UNAVAILABLE, UNKNOWN_PROVIDER_EXECUTION and OUTPUT_LIMIT. Public errors contain no internal paths or credential-bearing URLs. Revocation stops new calls; already-sent uncertain calls retain liability until reconciled. Revoke the channel before cleaning the container.

## Acceptance before live registration

- Real mediated inference using the actual requested provider/model ID, with successful usage and denied unsupported model/runtime paths. The CEO requested Gemini 3.8 Flash; discovery must establish the actual API identifier rather than assuming it exists.
- Real guest attempts to obtain keys, call arbitrary URLs, change tenant/model, invoke tools or reuse another run's channel fail.
- Exact replay does not cause another provider request or another charge; changed replay conflicts.
- Fault injection before send, during send, after response/before commit, after commit/before ack and after restart yields no blind duplicate paid call.
- Cancellation, revoked sessions, expired leases, output flooding and exhausted/overspent budgets stop new calls and preserve appropriate holds.
- Actual configured proxy/CA policy remains in effect. Provider credentials and signing keys remain outside the candidate environment/files.
- A mocked provider qualifies protocol/accounting tests only. Live acceptance requires separate real provider receipts, exact image/runtime version and independent review.
