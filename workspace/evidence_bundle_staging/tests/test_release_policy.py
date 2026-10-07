"""
tests/test_release_policy.py: Unit tests verifying that the release policy engine
deterministically blocks the 3 failure modes identified in the judicial audit,
as well as candidate hash mismatches, unknown classifications, and invalid bounding boxes.
"""

import unittest
from mas.release_policy import (
    PolicySpec,
    compute_candidate_hash,
    evaluate_release_policy,
)


class TestReleasePolicyJudicialAudit(unittest.TestCase):

    def setUp(self):
        self.sample_html = "<html><body><h1>FinOps Dashboard</h1></body></html>"
        self.candidate_hash = compute_candidate_hash(self.sample_html)
        self.run_id = "run_audit_20261007_001"
        self.policy = PolicySpec(
            policy_id="finops_cockpit_v1",
            policy_version="1.0.0",
            target_profile="WCAG_AA",
            mandatory_suites={"static_contract", "axe_a11y", "playwright_render"},
            max_advisories=5,
            enforce_evidence_integrity=True,
        )

    def test_judicial_case_1_empty_required_suites_or_empty_results(self):
        """
        Judge Test 1: execution_complete: true, empty required suites or empty results.
        Old behavior: returned RELEASE_PERMITTED!
        Required behavior: MUST return RELEASE_BLOCKED.
        """
        empty_audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [],  # Empty results
        }
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=empty_audit,
            findings_reports=[],
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertFalse(res.is_permitted)
        self.assertTrue(any("Audit contains no suite_executions" in r or "Missing mandatory" in r for r in res.reasons))

    def test_judicial_case_2_suite_marked_completed_without_findings_report(self):
        """
        Judge Test 2: Required suite marked completed in audit, but no findings report supplied.
        Old behavior: returned RELEASE_PERMITTED (missing report treated as 0 defects)!
        Required behavior: MUST return RELEASE_BLOCKED.
        """
        audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        # Only supply findings for static_contract and axe_a11y; OMIT playwright_render
        incomplete_reports = [
            {
                "suite_name": "static_contract",
                "candidate_hash": self.candidate_hash,
                "run_id": self.run_id,
                "findings": [],
            },
            {
                "suite_name": "axe_a11y",
                "candidate_hash": self.candidate_hash,
                "run_id": self.run_id,
                "findings": [],
            },
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=incomplete_reports,
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertFalse(res.is_permitted)
        self.assertTrue(any("no corresponding findings report was supplied" in r for r in res.reasons))

    def test_judicial_case_3_same_suite_recorded_as_completed_and_crashed(self):
        """
        Judge Test 3: Same suite recorded as both COMPLETED and CRASHED.
        Old behavior: returned RELEASE_PERMITTED (accepted COMPLETED and ignored CRASHED)!
        Required behavior: MUST return RELEASE_BLOCKED due to ambiguous execution records.
        """
        conflicting_audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "axe_a11y", "status": "CRASHED", "duration_ms": 10},  # Conflicting duplicate!
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        reports = [
            {"suite_name": "static_contract", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "axe_a11y", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "playwright_render", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=conflicting_audit,
            findings_reports=reports,
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertFalse(res.is_permitted)
        self.assertTrue(any("Ambiguous execution record" in r or "duplicate executions" in r for r in res.reasons))

    def test_candidate_hash_and_run_id_mismatch(self):
        """Audit and reports tied to a different candidate hash must be rejected."""
        tampered_audit = {
            "candidate_hash": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=tampered_audit,
            findings_reports=[],
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertTrue(any("candidate_hash mismatch" in r for r in res.reasons))

    def test_unknown_classification_is_rejected(self):
        """Unknown defect classification must be rejected as an unhandled violation."""
        audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        reports = [
            {"suite_name": "static_contract", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {
                "suite_name": "axe_a11y",
                "candidate_hash": self.candidate_hash,
                "run_id": self.run_id,
                "findings": [
                    {
                        "finding_id": "FIND-UNKNOWN-01",
                        "rule_id": "custom-rule",
                        "classification": "MALICIOUS_OR_UNKNOWN_CATEGORY",
                        "target_selector": "#header",
                        "observed_state": "Something unexpected",
                        "user_impact": "Unknown",
                    }
                ],
            },
            {"suite_name": "playwright_render", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=reports,
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertTrue(any("Unknown defect classification" in r for r in res.reasons))

    def test_valid_execution_with_zero_blocking_findings_passes(self):
        """Complete, reconciled, zero-blocking-defect execution must permit release."""
        audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        reports = [
            {"suite_name": "static_contract", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "axe_a11y", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {
                "suite_name": "playwright_render",
                "candidate_hash": self.candidate_hash,
                "run_id": self.run_id,
                "findings": [
                    {
                        "finding_id": "ADV-01",
                        "rule_id": "editorial-whitespace",
                        "classification": "ADVISORY_STYLE",
                        "target_selector": "header",
                        "observed_state": "Slight asymmetric tension recommended",
                        "user_impact": "None",
                    }
                ],
            },
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=reports,
        )
        self.assertEqual(res.decision, "RELEASE_PERMITTED")
        self.assertTrue(res.is_permitted)
        self.assertEqual(res.advisory_count, 1)
        self.assertEqual(len(res.blocking_finding_ids), 0)

    def test_invalid_bounding_box_dimension_blocked(self):
        """Bounding box with negative or zero width/height must fail evidence integrity."""
        audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        reports = [
            {"suite_name": "static_contract", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {
                "suite_name": "axe_a11y",
                "candidate_hash": self.candidate_hash,
                "run_id": self.run_id,
                "findings": [
                    {
                        "finding_id": "FIND-BBOX-01",
                        "rule_id": "target-size",
                        "classification": "BLOCKING_A11Y",
                        "target_selector": "#btn-test",
                        "observed_state": "Too small",
                        "user_impact": "Misclick",
                        "evidence_artifact": "evidence/trace.png",
                        "bounding_box": {"x": 10.0, "y": 20.0, "width": -5.0, "height": 18.0},  # Negative width!
                    }
                ],
            },
            {"suite_name": "playwright_render", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=reports,
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertTrue(any("invalid dimensions" in r for r in res.reasons))

    def test_rebalance_action_contract_in_pilot_artifacts(self):
        """Verify that Candidate 1 implements ACT-REBALANCE-01 and Candidate 0 lacks it."""
        from pathlib import Path
        pilot_dir = Path(__file__).resolve().parent.parent / "workspace" / "pilot_brief_b"
        c0 = (pilot_dir / "candidate_0.html").read_text(encoding="utf-8")
        c1 = (pilot_dir / "candidate_1.html").read_text(encoding="utf-8")

        self.assertNotIn('data-action-id="ACT-REBALANCE-01"', c0)
        self.assertIn('data-action-id="ACT-REBALANCE-01"', c1)
        self.assertIn('role="status"', c1)
        self.assertIn('aria-live="polite"', c1)

    def test_judge_round6_missing_findings_field_in_report_blocked(self):
        """Case: All report objects omit their 'findings' field -> MUST BE BLOCKED."""
        audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        # Reports completely omit the 'findings' field
        omitted_findings_reports = [
            {"suite_name": "static_contract", "candidate_hash": self.candidate_hash, "run_id": self.run_id},
            {"suite_name": "axe_a11y", "candidate_hash": self.candidate_hash, "run_id": self.run_id},
            {"suite_name": "playwright_render", "candidate_hash": self.candidate_hash, "run_id": self.run_id},
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=omitted_findings_reports,
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertFalse(res.is_permitted)
        self.assertTrue(any("missing mandatory 'findings' list" in r for r in res.reasons))

    def test_judge_round6_execution_complete_string_false_blocked(self):
        """Case: execution_complete contains the string 'false' -> MUST BE BLOCKED."""
        audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": "false",  # Truthy string in python, but invalid boolean!
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        reports = [
            {"suite_name": "static_contract", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "axe_a11y", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "playwright_render", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=reports,
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertFalse(res.is_permitted)
        self.assertTrue(any("execution_complete must be boolean True" in r for r in res.reasons))

    def test_judge_round6_non_hex_candidate_hash_blocked(self):
        """Case: candidate_hash has 64 characters but contains non-hex values -> MUST BE BLOCKED."""
        non_hex_hash = "z" * 64
        audit = {
            "candidate_hash": non_hex_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        reports = [
            {"suite_name": "static_contract", "candidate_hash": non_hex_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "axe_a11y", "candidate_hash": non_hex_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "playwright_render", "candidate_hash": non_hex_hash, "run_id": self.run_id, "findings": []},
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=non_hex_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=reports,
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertFalse(res.is_permitted)
        self.assertTrue(any("must be exactly 64 hexadecimal characters" in r for r in res.reasons))

    def test_judge_round6_suite_executions_null_blocked_without_crash(self):
        """Case: suite_executions is null (None) -> MUST BE BLOCKED gracefully without TypeError."""
        audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": None,  # None/null value
        }
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=[],
        )
        self.assertEqual(res.decision, "RELEASE_BLOCKED")
        self.assertFalse(res.is_permitted)
        self.assertTrue(any("must be a non-null, non-empty list" in r for r in res.reasons))

    def test_judge_round6_advisories_do_not_block_release(self):
        """Case: Excess advisories must NOT block release (advisories are non-blocking)."""
        audit = {
            "candidate_hash": self.candidate_hash,
            "run_id": self.run_id,
            "execution_complete": True,
            "suite_executions": [
                {"suite_name": "static_contract", "status": "COMPLETED", "duration_ms": 15},
                {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
                {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1100},
            ],
        }
        # 12 advisories, while policy max_advisories is 5
        many_advisories = [
            {
                "finding_id": f"ADV-{i}",
                "rule_id": "style-hint",
                "classification": "ADVISORY_STYLE",
                "target_selector": f"#elem-{i}",
                "observed_state": "Visual recommendation",
                "user_impact": "None",
            }
            for i in range(12)
        ]
        reports = [
            {"suite_name": "static_contract", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "axe_a11y", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": []},
            {"suite_name": "playwright_render", "candidate_hash": self.candidate_hash, "run_id": self.run_id, "findings": many_advisories},
        ]
        res = evaluate_release_policy(
            policy=self.policy,
            candidate_hash=self.candidate_hash,
            run_id=self.run_id,
            audit=audit,
            findings_reports=reports,
        )
        self.assertEqual(res.decision, "RELEASE_PERMITTED")
        self.assertTrue(res.is_permitted)
        self.assertEqual(res.advisory_count, 12)
        self.assertEqual(len(res.blocking_finding_ids), 0)

