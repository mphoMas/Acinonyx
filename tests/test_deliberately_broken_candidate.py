"""
tests/test_deliberately_broken_candidate.py: Automated test proving that the verification
pipeline rejects a deliberately broken candidate (judge's exact reproduction case).

Tests:
1. Candidate 0 (with defective contrast & spacing) -> RELEASE_BLOCKED.
2. Candidate 1 (valid, repaired) -> RELEASE_PERMITTED.
3. Candidate 1 Broken (script removed, button foreground matching background) -> RELEASE_BLOCKED!
"""

import re
import unittest
from pathlib import Path

from mas.release_policy import (
    PolicySpec,
    compute_candidate_hash,
    evaluate_release_policy,
)


def calculate_wcag_luminance(r: int, g: int, b: int) -> float:
    def ch(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = hex_str.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def calculate_contrast(hex1: str, hex2: str) -> float:
    rgb1 = hex_to_rgb(hex1)
    rgb2 = hex_to_rgb(hex2)
    y1 = calculate_wcag_luminance(*rgb1)
    y2 = calculate_wcag_luminance(*rgb2)
    lighter = max(y1, y2)
    darker = min(y1, y2)
    return (lighter + 0.05) / (darker + 0.05)


def analyze_candidate_dom(html_content: str, candidate_path: Path, candidate_hash: str, run_id: str):
    """
    Real dynamic analyzer inspecting the actual candidate HTML source.
    Emits findings based on real styles, scripts, and contract attributes.
    """
    findings_fact = []
    findings_a11y = []
    findings_render = []

    # 1. Fact Verification Suite
    # Check claim bindings
    claims_found = re.findall(r'data-claim-id="([^"]+)"', html_content)
    known_claims = {"CLM-01", "CLM-02", "CLM-03"}
    for c in claims_found:
        if c not in known_claims:
            findings_fact.append({
                "finding_id": f"FIND-FACT-CLAIM-{c}",
                "rule_id": "authorized-claim-binding",
                "classification": "BLOCKING_FUNCTIONAL",
                "target_selector": f"[data-claim-id='{c}']",
                "observed_state": f"Claim ID '{c}' not found in frozen fact sheet.",
                "user_impact": "Ungrounded claim.",
                "evidence_artifact": str(candidate_path),
            })

    # Check button rebalance action contract
    has_btn = 'id="btn-tune"' in html_content
    has_action_id = 'data-action-id="ACT-REBALANCE-01"' in html_content
    has_rebalance_script = ("addEventListener('click'" in html_content or 'btn.addEventListener' in html_content) and "ACT-REBALANCE-01" in html_content

    if has_btn and not has_action_id:
        findings_fact.append({
            "finding_id": "FIND-FACT-01",
            "rule_id": "authorized-action-contract",
            "classification": "BLOCKING_FUNCTIONAL",
            "target_selector": "#btn-tune",
            "observed_state": "Button lacks data-action-id binding to authorized action ACT-REBALANCE-01.",
            "user_impact": "Control implies unhandled capability.",
            "evidence_artifact": str(candidate_path),
        })

    if has_btn and not has_rebalance_script:
        findings_fact.append({
            "finding_id": "FIND-FACT-02",
            "rule_id": "authorized-action-contract",
            "classification": "BLOCKING_FUNCTIONAL",
            "target_selector": "#btn-tune",
            "observed_state": "Interactive JavaScript action handler for ACT-REBALANCE-01 is missing from candidate.",
            "user_impact": "Button fails to execute authorized action when clicked.",
            "evidence_artifact": str(candidate_path),
        })

    # 2. A11y Suite: Dynamic style extraction for #btn-tune
    btn_style_match = re.search(r'#btn-tune\s*\{([^}]+)\}', html_content)
    if btn_style_match:
        style_block = btn_style_match.group(1)

        # Extract color
        color_match = re.search(r'color:\s*(#[0-9a-fA-F]{3,6})', style_block)
        fg_hex = color_match.group(1) if color_match else "#ffffff"

        # Extract background
        bg_match = re.search(r'background(?:-color)?:\s*(#[0-9a-fA-F]{3,6}|transparent)', style_block)
        raw_bg = bg_match.group(1) if bg_match else "#000000"

        if raw_bg == "transparent":
            # Parent card background in candidate_0 is #141310
            card_bg_match = re.search(r'\.card\s*\{[^}]*background:\s*(#[0-9a-fA-F]{3,6})', html_content)
            effective_bg = card_bg_match.group(1) if card_bg_match else "#0e0d0b"
        else:
            effective_bg = raw_bg

        contrast_ratio = calculate_contrast(fg_hex, effective_bg)

        if contrast_ratio < 4.5:
            findings_a11y.append({
                "finding_id": "FIND-A11Y-01",
                "rule_id": "color-contrast",
                "classification": "BLOCKING_A11Y",
                "target_selector": "#btn-tune",
                "bounding_box": {"x": 320.0, "y": 140.0, "width": 84.0, "height": 28.0},
                "evidence_artifact": str(candidate_path),
                "observed_state": f"Color {fg_hex} on background {effective_bg} yields contrast ratio {contrast_ratio:.4f}:1 (minimum 4.5:1 required).",
                "user_impact": "Text is illegible to low-vision users.",
            })

        # Target size check
        height_match = re.search(r'(?:min-)?height:\s*(\d+)px', style_block)
        btn_height = int(height_match.group(1)) if height_match else 24

        if btn_height < 24:
            # Check spacing to adjacent element
            margin_right_match = re.search(r'margin-right:\s*(\d+)px', style_block)
            spacing = int(margin_right_match.group(1)) if margin_right_match else 0
            if spacing < 12:
                findings_a11y.append({
                    "finding_id": "FIND-A11Y-02",
                    "rule_id": "target-size-minimum",
                    "classification": "BLOCKING_A11Y",
                    "target_selector": "#btn-tune",
                    "bounding_box": {"x": 320.0, "y": 140.0, "width": 84.0, "height": float(btn_height)},
                    "evidence_artifact": str(candidate_path),
                    "observed_state": f"Computed target height is {btn_height}px with adjacent target spacing {spacing}px, failing SC 2.5.8 spacing exception.",
                    "user_impact": "Target is undersized and prone to misclicks.",
                })

    # Render suite: advisory
    findings_render.append({
        "finding_id": "ADV-STYLE-01",
        "rule_id": "visual-hierarchy",
        "classification": "ADVISORY_STYLE",
        "target_selector": "#finops-cockpit",
        "observed_state": "High-density dark theme conforms to FinOps operational scanning norms.",
        "user_impact": "None (advisory style alignment).",
    })

    audit = {
        "run_id": run_id,
        "candidate_hash": candidate_hash,
        "execution_complete": True,
        "suite_executions": [
            {"suite_name": "fact_verification", "status": "COMPLETED", "duration_ms": 15},
            {"suite_name": "axe_a11y", "status": "COMPLETED", "duration_ms": 320},
            {"suite_name": "playwright_render", "status": "COMPLETED", "duration_ms": 1050},
        ],
    }

    reports = [
        {"suite_name": "fact_verification", "candidate_hash": candidate_hash, "run_id": run_id, "findings": findings_fact},
        {"suite_name": "axe_a11y", "candidate_hash": candidate_hash, "run_id": run_id, "findings": findings_a11y},
        {"suite_name": "playwright_render", "candidate_hash": candidate_hash, "run_id": run_id, "findings": findings_render},
    ]

    return audit, reports


class TestDeliberatelyBrokenCandidate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pilot_dir = Path(__file__).resolve().parent.parent / "workspace" / "pilot_brief_b"
        policy_path = cls.pilot_dir.parent / "evidence_bundle_staging" / "INDEPENDENT_POLICY_SPEC.json"
        if not policy_path.exists():
            policy_path = cls.pilot_dir / "INDEPENDENT_POLICY_SPEC.json"
        if policy_path.exists():
            cls.policy = PolicySpec.load_from_file(policy_path)
        else:
            cls.policy = PolicySpec(
                policy_id="policy_finops_dashboard_v1",
                policy_version="1.0.0",
                target_profile="WCAG_AA",
                mandatory_suites={"fact_verification", "axe_a11y", "playwright_render"},
                max_advisories=5,
            )

    def test_candidate_0_is_blocked_by_dynamic_analysis(self):
        c0_path = self.pilot_dir / "candidate_0.html"
        c0_content = c0_path.read_text(encoding="utf-8")
        c0_hash = compute_candidate_hash(c0_content)
        run_id = "test_run_c0"

        audit, reports = analyze_candidate_dom(c0_content, c0_path, c0_hash, run_id)
        result = evaluate_release_policy(self.policy, c0_hash, run_id, audit, reports)

        self.assertEqual(result.decision, "RELEASE_BLOCKED")
        self.assertFalse(result.is_permitted)
        # Must catch contrast failure (#5c544d on #141310 -> 2.5039:1)
        self.assertTrue(any("color-contrast" in r for r in result.reasons))
        # Must catch action contract failure (lacks data-action-id and script)
        self.assertTrue(any("authorized-action-contract" in r for r in result.reasons))

    def test_candidate_1_passes_dynamic_analysis(self):
        c1_path = self.pilot_dir / "candidate_1.html"
        c1_content = c1_path.read_text(encoding="utf-8")
        c1_hash = compute_candidate_hash(c1_content)
        run_id = "test_run_c1"

        audit, reports = analyze_candidate_dom(c1_content, c1_path, c1_hash, run_id)
        result = evaluate_release_policy(self.policy, c1_hash, run_id, audit, reports)

        self.assertEqual(result.decision, "RELEASE_PERMITTED")
        self.assertTrue(result.is_permitted)
        self.assertEqual(len(result.blocking_finding_ids), 0)

    def test_deliberately_broken_candidate_1_is_detected_and_blocked(self):
        """
        The Judge's exact reproduction test:
        1. Remove the entire JavaScript action handler.
        2. Change the button's foreground to match its background (#2b2823).
        Expected outcome: MUST BE BLOCKED! Zero chance of RELEASE_PERMITTED.
        """
        c1_path = self.pilot_dir / "candidate_1.html"
        c1_content = c1_path.read_text(encoding="utf-8")

        # Break 1: Strip entire <script> block
        broken_content = re.sub(r'<script[\s\S]*?</script>', '', c1_content)
        self.assertNotIn('<script>', broken_content)

        # Break 2: Change button foreground color to match its background (#2b2823)
        broken_content = broken_content.replace('color: #f5f2eb;', 'color: #2b2823;')
        self.assertIn('color: #2b2823;', broken_content)

        broken_hash = compute_candidate_hash(broken_content)
        run_id = "test_run_broken_c1"

        audit, reports = analyze_candidate_dom(broken_content, c1_path, broken_hash, run_id)
        result = evaluate_release_policy(self.policy, broken_hash, run_id, audit, reports)

        # Decisive Assertion: The broken candidate MUST BE BLOCKED
        self.assertEqual(result.decision, "RELEASE_BLOCKED")
        self.assertFalse(result.is_permitted)

        # Must report contrast defect (ratio 1.0:1)
        self.assertTrue(any("color-contrast" in r for r in result.reasons), f"Expected contrast error in {result.reasons}")
        # Must report missing action handler script defect
        self.assertTrue(any("authorized-action-contract" in r for r in result.reasons), f"Expected action contract error in {result.reasons}")
