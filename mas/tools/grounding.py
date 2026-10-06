"""
mas.tools.grounding: Visual Grounding, Coordinate Normalization & Token FinOps Engine.
Translates between model perception space and physical framebuffer pixels, with Set-of-Mark (SoM) badges.

Architect: Acinonyx
"""

from __future__ import annotations

import base64
import io
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
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


def overlay_set_of_marks(
    image: Image.Image,
    candidates: Optional[List[Tuple[int, int, int, int]]] = None,
) -> Tuple[Image.Image, Dict[int, UIElementMark]]:
    """
    Overlays high-contrast Set-of-Mark (SoM) numbered badges onto interactive UI bounding boxes.
    Eliminates ViT patch quantization drift by allowing agents to issue actions by numeric ID.
    """
    annotated = image.copy().convert("RGBA")
    draw = ImageDraw.Draw(annotated)
    marks: Dict[int, UIElementMark] = {}

    # If no explicit candidate bboxes provided, generate grid/heuristic anchors
    if not candidates:
        w, h = image.size
        # Generate representative sample anchors for desktop controls
        candidates = [
            (20, 20, 120, 50),     # Top-left application menu
            (w - 60, 10, w - 10, 40), # Top-right close button
            (w // 2 - 150, h // 2 - 25, w // 2 + 150, h // 2 + 25), # Center primary button
        ]

    font = ImageFont.load_default()

    for idx, (left, top, right, bottom) in enumerate(candidates, start=1):
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        marks[idx] = UIElementMark(mark_id=idx, center_x=center_x, center_y=center_y, bbox=(left, top, right, bottom))

        # Draw subtle bounding box border
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
