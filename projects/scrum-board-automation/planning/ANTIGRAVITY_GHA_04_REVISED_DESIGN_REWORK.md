# Antigravity — close the remaining GHA-04 design contradictions

Candidate `fdee2afc` retains useful corrections but requires revision. Read `GHA_04_REVISED_DESIGN_REVIEW.md`. Do not code yet.

Deliver four concrete sections:

1. **Executable relational proposal:** exact parent unique indexes and composite ownership FKs; logical-action, attempt and receipt tables; complete bindings; immutable consumption provenance separate from expiring replay cache (or retain referenced tokens). Show insertion and cleanup order under foreign_keys=ON. Include unambiguous canonical digests.
2. **Authority/source protocol:** name actual supported mutators and locks/epochs that establish revocation versus commit ordering across stores. Specify durable refresh tickets, process coordination, CAS publication, failures/stalls/TTL, and generation changes for head/base/open-closed changes. Remove all ancestry ordering.
3. **Retry decision table:** separate semantic action digest from attempt/manifest digest. Authenticate before historical lookup; existing receipts survive head changes/closure as historical reads, not fresh admission. Define same/fresh/expired token, rerun and conflict outcomes consistently with schema uniqueness.
4. **Local artifact protocol:** no-overwrite promotion, content verification, quotas/reservations, fsync and crash recovery; orphan cleanup must not delete files needed by paused/pending/committed admission. Specify expiry metadata and query outcomes.

Update scenario mapping and readiness claims accordingly. Design scenarios are not runtime tests; do not mark Codex design agreement Verified before it exists. Preserve quarantined witness authority, no delivery phase/budget mutations and excluded remote effect journal.

Submit revised documents and immutable SHA for review. No code/schema, live workflows, production credentials/enrollment or provider dispatch before agreement.
