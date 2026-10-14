# GHA-04A independent challenge resolution and implementation handoff

Challenge target: Codex reference `5f83e250`. Reviewer: Antigravity, supplied by CEO in chat. Decision: APPROVED WITH CONDITIONS. This record is a transcription/resolution of that decision, not a claim of an independently committed runtime review.

## Resolved conditions

1. SQLite REPLACE bypass: confirmed; added BEFORE INSERT guards for every immutable logical/physical conflict and tests for REPLACE/IGNORE/UPSERT. Do not depend on recursive_triggers.
2. Parent mapping: choose existing `pm_delivery_tasks(tenant_id,project_id,issue_id)` with additive UNIQUE index. Require existing enrolled task, no pm_issues tenant-column mutation and no new enrollment.
3. Check scope/order: reference admission now refuses unknown, duplicate and unsorted check IDs before transaction. Equality with the contract set is allowed; a proper subset is not required.
4. Contract digest: hash structured authenticated owner + validated contract; source fields remain claims. Never allow caller ownership to select tenant storage.
5. Quota: duplicate lookup before quota; count and new insertion share BEGIN IMMEDIATE. Preserve authorized existing retrieval at cap.

Verification: **10 reference checks passed in 0.032 seconds**. Reference tests are not runtime authorization, concurrency or crash acceptance. No production code or migration was applied.

## Antigravity's next task — implement GHA-04A

- Read corrected `GHA_04_RECEIPT_SLICE_CONTRACT.md` and fixtures. Treat the transaction/identity/ownership/scope contract as frozen; name deviations before coding.
- Implement supported authenticated record/get interfaces, additive checksum/reopen-verified migration using actual task parents, immutable action/receipt/item storage and receipt quota.
- Wire one shared single-process authority guard into supported IAM/session/principal/connector mutators and receipt transactions. Name actual integration points and supported process profile. Preserve existing roles/storage authorization and refuse forged context or trusted-admin fallback. No external-process authority claims.
- Cover real kill-before/after-commit, fresh-auth recovery, concurrent identical/conflicting/new-attempt writes, revocation order, cross-tenant read/write, REPLACE/UPSERT immutability, exact limits/quota and migration drift.
- Run targeted/full gate and isolated installed-wheel acceptance; submit exact SHA and closure evidence. Codex independently reviews; do not self-mark accepted.

Excluded: PR freshness, filesystem artifacts, durable token consumption, live workflow/public endpoint/provider dispatch, task phase/submission/budget/evidence mutation, new operational enrollment or distributed/multi-process deployment. This implementation is the receipt slice, not completion of full GHA-04 or the agent loop.

No additional CEO confirmation is required to execute this agreed implementation task. Independent runtime acceptance remains mandatory.
