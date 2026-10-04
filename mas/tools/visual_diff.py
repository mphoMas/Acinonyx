"""
mas.tools.visual_diff: Autonomous Pixel-by-Pixel and Perceptual Visual Regression Diffing.
Compares UI screenshot revisions, computes color delta and RMSE, highlights discrepancies
with visual diff masks, and enforces automated regression gates for QA agents.

Architect: Acinonyx
"""

from __future__ import annotations

import math
import os
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

# Ensure local packages are available for PIL and Playwright
PKG_DIR = "/home/acinonyx/Desktop/MAS/bin/packages"
BROWSER_DIR = "/home/acinonyx/Desktop/MAS/bin/browsers"
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_DIR

try:
    from PIL import Image, ImageChops, ImageEnhance
except ImportError:
    Image = None
    ImageChops = None
    ImageEnhance = None


@dataclass
class VisualDiffMetrics:
    total_pixels: int
    differing_pixels: int
    mismatch_pct: float
    rmse: float
    status: str  # "PASSED" or "FAILED_REGRESSION"
    diff_image_path: Optional[str]
    baseline_dimensions: Tuple[int, int]
    current_dimensions: Tuple[int, int]
    threshold_pct: float
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_visual_diff(
    baseline_path: str,
    current_path: str,
    diff_output_path: Optional[str] = None,
    threshold_pct: float = 0.5,
    color_sensitivity: int = 15,
) -> VisualDiffMetrics:
    """
    Compare baseline and current screenshot images pixel-by-pixel.
    Computes mismatch percentage, RMSE, and creates an annotated diff mask image.
    """
    if Image is None:
        raise RuntimeError("Pillow (PIL) is required for visual regression diffing.")

    if not os.path.exists(baseline_path):
        raise FileNotFoundError(f"Baseline screenshot not found: {baseline_path}")
    if not os.path.exists(current_path):
        raise FileNotFoundError(f"Current revision screenshot not found: {current_path}")

    img_base = Image.open(baseline_path).convert("RGBA")
    img_curr = Image.open(current_path).convert("RGBA")

    base_dims = img_base.size
    curr_dims = img_curr.size

    # Handle dimension discrepancies by creating a common union canvas
    max_w = max(base_dims[0], curr_dims[0])
    max_h = max(base_dims[1], curr_dims[1])

    if base_dims != (max_w, max_h):
        canvas_base = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
        canvas_base.paste(img_base, (0, 0))
        img_base = canvas_base

    if curr_dims != (max_w, max_h):
        canvas_curr = Image.new("RGBA", (max_w, max_h), (0, 0, 0, 0))
        canvas_curr.paste(img_curr, (0, 0))
        img_curr = canvas_curr

    # Compute channel-by-channel absolute difference
    diff = ImageChops.difference(img_base, img_curr)
    diff_data = diff.getdata()
    base_data = img_base.getdata()

    total_pixels = max_w * max_h
    differing_pixels = 0
    sum_squared_error = 0.0

    # Build highlighted output mask:
    # Dimmed grayscale baseline with bright magenta highlights (#FF0055) on changed pixels
    grayscale_base = ImageEnhance.Brightness(img_base.convert("L").convert("RGBA")).enhance(0.45)
    highlight_pixels = []

    for idx, (r_diff, g_diff, b_diff, a_diff) in enumerate(diff_data):
        max_delta = max(r_diff, g_diff, b_diff)
        sq_err = (r_diff**2 + g_diff**2 + b_diff**2) / 3.0
        sum_squared_error += sq_err

        if max_delta > color_sensitivity or a_diff > color_sensitivity:
            differing_pixels += 1
            # Bright fluorescent magenta highlight on changed pixels
            highlight_pixels.append((255, 0, 85, 255))
        else:
            # Retain dimmed baseline pixel
            base_px = base_data[idx]
            # Convert to muted monochrome
            mono = int(0.299 * base_px[0] + 0.587 * base_px[1] + 0.114 * base_px[2])
            highlight_pixels.append((int(mono * 0.5), int(mono * 0.5), int(mono * 0.5), 255))

    mismatch_pct = round((differing_pixels / total_pixels) * 100.0, 4)
    rmse = round(math.sqrt(sum_squared_error / total_pixels), 4)

    status = "PASSED" if mismatch_pct <= threshold_pct else "FAILED_REGRESSION"

    diff_saved_path = None
    if diff_output_path:
        os.makedirs(os.path.dirname(os.path.abspath(diff_output_path)), exist_ok=True)
        diff_img = Image.new("RGBA", (max_w, max_h))
        diff_img.putdata(highlight_pixels)
        diff_img.save(diff_output_path)
        diff_saved_path = diff_output_path

    summary = (
        f"Visual Regression Check {status}: {differing_pixels}/{total_pixels} pixels mismatched "
        f"({mismatch_pct}%, threshold: {threshold_pct}%, RMSE: {rmse})"
    )

    return VisualDiffMetrics(
        total_pixels=total_pixels,
        differing_pixels=differing_pixels,
        mismatch_pct=mismatch_pct,
        rmse=rmse,
        status=status,
        diff_image_path=diff_saved_path,
        baseline_dimensions=base_dims,
        current_dimensions=curr_dims,
        threshold_pct=threshold_pct,
        summary=summary,
    )


async def browser_visual_regression_check(
    url: str,
    baseline_path: str,
    diff_output_path: Optional[str] = None,
    threshold_pct: float = 0.5,
    viewport_width: int = 1280,
    viewport_height: int = 800,
) -> Dict[str, Any]:
    """
    Navigate to a live web page using Playwright, capture a fresh screenshot,
    and compare it against the baseline screenshot for visual regression gating.
    """
    from playwright.async_api import async_playwright

    temp_revision_path = os.path.join(
        os.path.dirname(os.path.abspath(diff_output_path or baseline_path)),
        "current_revision_capture.png",
    )
    os.makedirs(os.path.dirname(os.path.abspath(temp_revision_path)), exist_ok=True)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": viewport_width, "height": viewport_height})
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.screenshot(path=temp_revision_path, full_page=False)
            await browser.close()

        metrics = compute_visual_diff(
            baseline_path=baseline_path,
            current_path=temp_revision_path,
            diff_output_path=diff_output_path,
            threshold_pct=threshold_pct,
        )

        res = metrics.to_dict()
        res["success"] = True
        res["current_screenshot"] = temp_revision_path
        res["url"] = url
        return res

    except Exception as e:
        return {
            "success": False,
            "error": f"Visual regression check failed: {str(e)}",
            "url": url,
        }
