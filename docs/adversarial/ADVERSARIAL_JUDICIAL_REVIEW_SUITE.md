# Adversarial Judicial-Review Attack Suite (GOV-05)

## Overview & Threat Model
The MAS-PM governance model enforces mathematical and cryptographic integrity across task lifecycles. 
This document details the adversarial attack suite implemented in [`tests/test_gov_05_adversarial_judicial_review.py`](file:///home/acinonyx/Desktop/MAS/tests/test_gov_05_adversarial_judicial_review.py) to stress-test and actively verify judicial review gates against adversarial manipulation.

## Threat Vectors & Countermeasure Matrix

| Attack Vector | Attacker Objective | Mitigation / Defense Layer | Observed Behavior | Test Case |
|---|---|---|---|---|
| **AV-01: Forged HMAC Signature** | Forge a `PASS` verdict with an invalid or tampered HMAC signature | Cryptographic SHA-256 HMAC verification (`verify_verdict_signature`) | FSM transition raises `UnverifiedWorkError`; gate remains closed | `test_adversarial_attack_forged_verdict_signature` |
| **AV-02: Missing Critic Reviews** | Transition an issue with incomplete reviewer quorum (e.g. only QA without Red Team) | Quorum enforcement in FSM Stage 4/5 (`validate_critic_verdicts`) | FSM transition raises `UnverifiedWorkError`; missing reviewers enumerated | `test_adversarial_attack_missing_critic_reviews` |
| **AV-03: Conflicting Decisions** | Force approval despite an explicit `REJECT_REWORK` or `HARD_FAIL` verdict | Strict unanimity evaluation over current rework cycle | FSM transition aborts; reject findings surfaced | `test_adversarial_attack_conflicting_decisions` |
| **AV-04: Builder Self-Approval** | Assignee attempts to self-certify their own code changes | Dual-layer: SQLite trigger `trg_prevent_self_review` + `assert_separation_of_builder_and_judge` | Persistence rejects insert (`IntegrityError`); FSM raises `SeparationOfDutiesError` | `test_adversarial_attack_builder_self_review` |
| **AV-05: Direct DB Evidence Tampering** | Directly modify or delete evidence rows in `pm_evidence_links` | SQLite database triggers (`trg_prevent_evidence_update`, `trg_prevent_evidence_delete`) | SQLite aborts with `TamperViolationError` (`IntegrityError`) | `test_adversarial_attack_direct_evidence_tampering` |
| **AV-06: Stale Verdict Replay** | Replay a previous cycle's `PASS` verdict after task rejection | Rework cycle isolation (`issue.rework_cycle`) | FSM rejects cycle 0 approvals for cycle 1 review | `test_adversarial_attack_stale_verdict_rework_cycle` |

## Verification Command
```bash
python3 -m pytest tests/test_gov_05_adversarial_judicial_review.py -v
```
Output:
```
tests/test_gov_05_adversarial_judicial_review.py::test_adversarial_attack_forged_verdict_signature PASSED
tests/test_gov_05_adversarial_judicial_review.py::test_adversarial_attack_missing_critic_reviews PASSED
tests/test_gov_05_adversarial_judicial_review.py::test_adversarial_attack_conflicting_decisions PASSED
tests/test_gov_05_adversarial_judicial_review.py::test_adversarial_attack_builder_self_review PASSED
tests/test_gov_05_adversarial_judicial_review.py::test_adversarial_attack_direct_evidence_tampering PASSED
tests/test_gov_05_adversarial_judicial_review.py::test_adversarial_attack_stale_verdict_rework_cycle PASSED
```
