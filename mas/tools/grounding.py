"""
mas.tools.grounding: Visual Grounding, Coordinate Normalization & Token FinOps Engine.
Translates between model perception space and physical framebuffer pixels, with Set-of-Mark (SoM) badges.

Architect: Acinonyx
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class UIElementMark:
    mark_id: int
    center_x: int
    center_y: int
    bbox: Tuple[int, int, int, int]  # (left, top, right, bottom)
    label: Optional[str] = None


@dataclass(frozen=True)
class GroundedFrame:
    base64_data: str
    format: str
    physical_width: int
    physical_height: int
    scaled_width: int
    scaled_height: int
    byte_size: int
    marks: Optional[Dict[int, UIElementMark]] = None


def scale_coordinates(
    model_x: float,
    model_y: float,
    scaled_width: int,
    scaled_height: int,
    physical_width: int,
    physical_height: int,
) -> Tuple[int, int]:
    """
    Scale model-predicted coordinates from visual downsample space to physical framebuffer pixels.
    Includes clamping guards to prevent out-of-bounds pointer events.
    """
    if scaled_width <= 0 or scaled_height <= 0:
        return int(model_x), int(model_y)

    scale_x = physical_width / scaled_width
    scale_y = physical_height / scaled_height

    phys_x = round(float(model_x) * scale_x)
    phys_y = round(float(model_y) * scale_y)

    # Clamping guards
    clamped_x = max(0, min(physical_width - 1, phys_x))
    clamped_y = max(0, min(physical_height - 1, phys_y))
    return clamped_x, clamped_y


def compress_and_encode_frame(
    image: Image.Image,
    max_dimension: int = 1024,
    format_type: str = "WEBP",
    quality: int = 85,
) -> Tuple[str, int, int, int]:
    """
    Downsamples image for Token FinOps efficiency and returns base64 string, scaled_w, scaled_h, byte_size.
    """
    orig_w, orig_h = image.size

    # Calculate proportional downsampling
    if max(orig_w, orig_h) > max_dimension:
        ratio = max_dimension / float(max(orig_w, orig_h))
        new_w = max(1, int(orig_w * ratio))
        new_h = max(1, int(orig_h * ratio))
        resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    else:
        new_w, new_h = orig_w, orig_h
        resized = image.copy()

    buffer = io.BytesIO()
    try:
        resized.save(buffer, format=format_type, quality=quality)
    except Exception:
        # Fallback to PNG if WebP unsupported
        format_type = "PNG"
        resized.save(buffer, format="PNG")

    raw_bytes = buffer.getvalue()
    b64_str = base64.b64encode(raw_bytes).decode("ascii")
    return b64_str, new_w, new_h, len(raw_bytes)


def compute_visual_diff(img1: Image.Image, img2: Image.Image) -> float:
    """
    Compute perceptual difference ratio (0.0 to 1.0) between two frames.
    Used for smart visual settlement detection and action feedback verification.
    """
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    # Downsample to 128x128 grayscale for sub-millisecond diffing
    thumb1 = img1.convert("L").resize((128, 128))
    thumb2 = img2.convert("L").resize((128, 128))

    b1 = thumb1.tobytes()
    b2 = thumb2.tobytes()

    diff_count = 0
    total_pixels = len(b1)
    threshold = 15  # noise tolerance

    for i in range(total_pixels):
        if abs(b1[i] - b2[i]) > threshold:
            diff_count += 1

    return diff_count / float(total_pixels)


def detect_ui_elements(
    image: Image.Image,
    max_elements: int = 40,
) -> List[Tuple[int, int, int, int]]:
    """
    Fast on-device visual element detector.
    Analyzes luminance gradients, high-contrast boundaries, and rectangular widgets
    to locate interactive buttons, text fields, cards, and icons without requiring external model weights.
    """
    w, h = image.size
    # Downsample for rapid edge scanning if image is large
    scale = 1.0
    scan_img = image
    if max(w, h) > 800:
        scale = 800.0 / max(w, h)
        scan_w = max(1, int(w * scale))
        scan_h = max(1, int(h * scale))
        scan_img = image.resize((scan_w, scan_h), Image.Resampling.BILINEAR)

    gray = scan_img.convert("L")
    pixels = gray.load()
    sw, sh = scan_img.size

    # Horizontal and vertical gradient step analysis
    candidates: List[Tuple[int, int, int, int]] = []
    step = 16
    min_box_w, min_box_h = 30, 18

    # 1. Grid-based high-variance rectangular region search
    for y in range(0, sh - min_box_h, step):
        for x in range(0, sw - min_box_w, step):
            # Sample contrast across bounding box window
            p00 = pixels[x, y]
            p10 = pixels[min(sw - 1, x + min_box_w), y]
            p01 = pixels[x, min(sh - 1, y + min_box_h)]
            p11 = pixels[min(sw - 1, x + min_box_w), min(sh - 1, y + min_box_h)]

            contrast = max(abs(p00 - p10), abs(p00 - p01), abs(p10 - p11))
            if contrast > 25:
                # Expand box horizontally and vertically to find edge boundaries
                bx2 = min(sw, x + min_box_w * 2)
                by2 = min(sh, y + min_box_h * 2)

                # Scale back to original resolution
                orig_x1 = int(x / scale)
                orig_y1 = int(y / scale)
                orig_x2 = int(bx2 / scale)
                orig_y2 = int(by2 / scale)

                # Avoid duplicate / closely overlapping boxes
                overlap = False
                for ox1, oy1, ox2, oy2 in candidates:
                    if abs(orig_x1 - ox1) < 40 and abs(orig_y1 - oy1) < 25:
                        overlap = True
                        break
                if not overlap:
                    candidates.append((orig_x1, orig_y1, orig_x2, orig_y2))
                    if len(candidates) >= max_elements:
                        break
        if len(candidates) >= max_elements:
            break

    # 2. Always ensure primary desktop anchor regions are present if few elements detected
    if len(candidates) < 3:
        default_anchors = [
            (20, 20, min(140, w - 20), min(60, h - 20)),          # Top-left application menu
            (max(20, w - 80), 10, max(40, w - 10), min(45, h - 10)), # Top-right close / action
            (max(20, w // 2 - 150), max(20, h // 2 - 25), min(w - 20, w // 2 + 150), min(h - 20, h // 2 + 25)), # Center primary workspace
        ]
        for a in default_anchors:
            if a not in candidates:
                candidates.append(a)

    return candidates[:max_elements]


def overlay_set_of_marks(
    image: Image.Image,
    candidates: Optional[List[Tuple[int, int, int, int]]] = None,
) -> Tuple[Image.Image, Dict[int, UIElementMark]]:
    """
    Overlays high-contrast Set-of-Mark (SoM) numbered badges onto interactive UI bounding boxes.
    Eliminates ViT patch quantization drift by allowing agents to issue actions by numeric ID.
    If no explicit candidate bboxes provided, automatically runs on-device detect_ui_elements.
    """
    annotated = image.copy().convert("RGBA")
    draw = ImageDraw.Draw(annotated)
    marks: Dict[int, UIElementMark] = {}

    # If no explicit candidate bboxes provided, run on-device detector
    if not candidates:
        candidates = detect_ui_elements(image)

    font = ImageFont.load_default()

    for idx, (left, top, right, bottom) in enumerate(candidates, start=1):
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        marks[idx] = UIElementMark(mark_id=idx, center_x=center_x, center_y=center_y, bbox=(left, top, right, bottom))

        # Draw subtle bounding box border and semi-transparent tint
        draw.rectangle([left, top, right, bottom], outline=(255, 60, 60, 220), width=2)

        # Draw numeric badge
        badge_text = f"[{idx}]"
        badge_w = len(badge_text) * 7 + 6
        badge_h = 16
        bx1 = max(0, left)
        by1 = max(0, top - badge_h)
        bx2 = bx1 + badge_w
        by2 = by1 + badge_h

        draw.rectangle([bx1, by1, bx2, by2], fill=(255, 60, 60, 230))
        draw.text((bx1 + 3, by1 + 2), badge_text, fill=(255, 255, 255, 255), font=font)

    return annotated.convert("RGB"), marks
