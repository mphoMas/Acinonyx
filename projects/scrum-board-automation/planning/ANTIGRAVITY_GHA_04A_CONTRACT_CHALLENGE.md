# Antigravity — independently challenge GHA-04A reference contract

Read `GHA_04_RECEIPT_SLICE_CONTRACT.md` and run the fixtures in `gha04-receipt-contract/`. Codex wrote this concrete reference to stop repeated broad design rewrites. Your task now is independent design challenge, NOT another entire platform specification or implementation.

1. Test the proposed ownership/immutability/retry SQL in disposable storage. Challenge actual protocol, not test count.
2. Identify exact current IAM/storage/connector APIs for the single-process authority guard profile; name supported mutators and startup/revocation semantics. State whether this local scope is usable. No invented API or multiple-process guarantee.
3. Confirm canonical contract versus observation identity, same-ID conflicts and distinct attempt outcomes; include any real counterexample.
4. Map the required supported-service crash/concurrency/auth tests before coding. Reference checks are not runtime acceptance.
5. Return one decision record: APPROVED WITH CONDITIONS or REQUIRES RE-WORK, exact contract edits and unresolved deployment limitations. Keep scope frozen once agreed; record later requirements separately.

Do not implement code/migrations/live workflows yet. Deferred freshness, durable token replay and artifact file lifecycle remain pending later GHA-04 increments; this slice does not close the full GHA-04 or automate the complete agent loop.
