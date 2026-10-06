"""
tests/test_visual_diff.py: Unit and Integration tests for Visual Regression Diffing.
Tests pixel-by-pixel comparisons, RMSE, mask image rendering, and regression threshold gating.

Architect: Acinonyx
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Inject packages for PIL
pkg_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "packages"))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)

from PIL import Image, ImageDraw
from mas.mcp.protocol import MCPRegistry
from mas.tools.browser_tool import register_browser_tools
from mas.tools.visual_diff import compute_visual_diff


class TestVisualRegressionDiffing(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_vis_diff_")
        self.baseline_path = os.path.join(self.temp_dir, "baseline.png")
        self.identical_path = os.path.join(self.temp_dir, "identical.png")
        self.altered_path = os.path.join(self.temp_dir, "altered.png")
        self.diff_output_path = os.path.join(self.temp_dir, "diff_mask.png")

        # Create 100x100 dark blue image
        img1 = Image.new("RGBA", (100, 100), (10, 20, 40, 255))
        img1.save(self.baseline_path)
        img1.save(self.identical_path)

        # Create altered image with a 20x20 bright red square (400 altered pixels)
        img2 = Image.new("RGBA", (100, 100), (10, 20, 40, 255))
        draw = ImageDraw.Draw(img2)
        draw.rectangle([10, 10, 29, 29], fill=(255, 0, 0, 255))
        img2.save(self.altered_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_identical_images_pass_with_zero_diff(self):
        metrics = compute_visual_diff(
            self.baseline_path,
            self.identical_path,
            diff_output_path=self.diff_output_path,
            threshold_pct=0.1,
        )
        self.assertEqual(metrics.differing_pixels, 0)
        self.assertEqual(metrics.mismatch_pct, 0.0)
        self.assertEqual(metrics.rmse, 0.0)
        self.assertEqual(metrics.status, "PASSED")
        self.assertTrue(os.path.exists(self.diff_output_path))

    def test_altered_image_triggers_regression_failure(self):
        # 400 out of 10,000 pixels is 4.0%
        metrics = compute_visual_diff(
            self.baseline_path,
            self.altered_path,
            diff_output_path=self.diff_output_path,
            threshold_pct=1.0,  # 1% threshold
        )
        self.assertGreater(metrics.differing_pixels, 350)
        self.assertAlmostEqual(metrics.mismatch_pct, 4.0, delta=0.5)
        self.assertGreater(metrics.rmse, 0.0)
        self.assertEqual(metrics.status, "FAILED_REGRESSION")
        self.assertTrue(os.path.exists(self.diff_output_path))

        with Image.open(self.diff_output_path) as diff_img:
            self.assertEqual(diff_img.size, (100, 100))

    def test_altered_image_passes_when_within_tolerance(self):
        # Allow up to 10% mismatch
        metrics = compute_visual_diff(
            self.baseline_path,
            self.altered_path,
            threshold_pct=10.0,
        )
        self.assertEqual(metrics.status, "PASSED")

    def test_differing_dimensions_handled_gracefully(self):
        diff_dim_path = os.path.join(self.temp_dir, "larger.png")
        img_large = Image.new("RGBA", (150, 120), (10, 20, 40, 255))
        img_large.save(diff_dim_path)

        metrics = compute_visual_diff(
            self.baseline_path,
            diff_dim_path,
            diff_output_path=self.diff_output_path,
            threshold_pct=50.0,
        )
        self.assertEqual(metrics.baseline_dimensions, (100, 100))
        self.assertEqual(metrics.current_dimensions, (150, 120))
        self.assertEqual(metrics.total_pixels, 150 * 120)
        self.assertTrue(os.path.exists(self.diff_output_path))

    def test_mcp_registration_includes_visual_tools(self):
        registry = MCPRegistry()
        register_browser_tools(registry)
        tool_names = list(registry.tools.keys())

        self.assertIn("visual_diff_compare", tool_names)
        self.assertIn("browser_visual_regression_check", tool_names)
        self.assertIn("browser_screenshot", tool_names)
        self.assertIn("browser_navigate", tool_names)


if __name__ == "__main__":
    unittest.main()
