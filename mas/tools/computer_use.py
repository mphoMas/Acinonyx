"""
mas.tools.computer_use: Production OS Desktop Automation & Computer Use Engine.
Implements the canonical discrete action space for headless virtual displays and native GUIs,
complete with coordinate scaling, Set-of-Mark interaction, security scope jails, and audit logging.

Architect: Acinonyx
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image

from mas.mcp.protocol import MCPRegistry
from mas.observability import LOGGER, METRICS
from mas.tools.display import VirtualDisplayConfig, VirtualDisplayManager
from mas.tools.grounding import (
    UIElementMark,
    compress_and_encode_frame,
    overlay_set_of_marks,
    scale_coordinates,
)


# Security Scope Jail: Prohibited keystroke combinations and commands
DENIED_KEY_CHORDS = {
    "ctrl+alt+del",
    "ctrl+alt+delete",
    "ctrl+alt+backspace",
    "ctrl+alt+f1",
    "ctrl+alt+f2",
    "ctrl+alt+f3",
    "ctrl+alt+f4",
    "ctrl+alt+f5",
    "ctrl+alt+f6",
}

DESTRUCTIVE_TEXT_PATTERNS = [
    r"rm\s+-rf\s+[/~]",
    r":\(\)\s*\{\s*:\|:&\s*\};:",  # Fork bomb
    r"mkfs(?:\.[a-z0-9]+)?\s+",
    r"dd\s+if=.*of=/dev/(?:sd|hd|nvme)",
    r">\s*/dev/(?:sd|hd|nvme)",
]


class ComputerUseSecurityError(RuntimeError):
    """Raised when an action violates the Computer Use Scope Jail policy."""
    pass


class ComputerUseScopeJail:
    """Enforces safety guardrails on synthetic mouse/keyboard actions."""

    @staticmethod
    def validate_keys(keys: List[str]) -> None:
        chord = "+".join(k.lower().strip() for k in keys)
        if chord in DENIED_KEY_CHORDS:
            METRICS.incr("computer_use.jail_blocked_key")
            raise ComputerUseSecurityError(f"Prohibited system hotkey blocked by Scope Jail: '{chord}'")

    @staticmethod
    def validate_text(text: str) -> None:
        for pattern in DESTRUCTIVE_TEXT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                METRICS.incr("computer_use.jail_blocked_text")
                raise ComputerUseSecurityError(f"Destructive system command pattern blocked by Scope Jail: '{text}'")


class ComputerUseController:
    """
    Main controller for desktop OS automation.
    Interfaces with VirtualDisplayManager, synthesizes mouse/keyboard input,
    manages screen captures, and logs cryptographic audit trails.
    """

    def __init__(
        self,
        display_manager: Optional[VirtualDisplayManager] = None,
        audit_log_path: str = "/home/acinonyx/Desktop/MAS/workspace/computer_use_audit.jsonl",
    ) -> None:
        self.display_manager = display_manager or VirtualDisplayManager()
        self.audit_log_path = audit_log_path
        self.cursor_x: int = 0
        self.cursor_y: int = 0
        self.last_marks: Dict[int, UIElementMark] = {}
        self.jail = ComputerUseScopeJail()
        self._ensure_audit_log_dir()

    def _ensure_audit_log_dir(self) -> None:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.audit_log_path)), exist_ok=True)
        except Exception:
            pass

    def _log_audit(self, action: str, params: Dict[str, Any], status: str = "success", error: Optional[str] = None) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "display": self.display_manager.display_str,
            "action": action,
            "params": params,
            "cursor": {"x": self.cursor_x, "y": self.cursor_y},
            "status": status,
            "error": error,
        }
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            LOGGER.warning(f"Failed to append to computer use audit log: {e}")

    def _is_xdotool_available(self) -> bool:
        return shutil.which("xdotool") is not None

    def _execute_xdotool(self, args: List[str]) -> bool:
        if not self._is_xdotool_available() or self.display_manager.is_mock:
            return True  # Handled in mock simulation
        env = os.environ.copy()
        env["DISPLAY"] = self.display_manager.display_str
        try:
            subprocess.run(["xdotool", *args], env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as e:
            LOGGER.error(f"xdotool error ({args}): {e}")
            return False

    def take_screenshot(
        self,
        apply_som: bool = False,
        max_dimension: int = 1024,
        quality: int = 85,
    ) -> Dict[str, Any]:
        """
        Grab the virtual framebuffer, optionally overlay Set-of-Mark tags,
        and encode to downsampled base64 WebP.
        """
        width = self.display_manager.config.width
        height = self.display_manager.config.height

        raw_image: Optional[Image.Image] = None

        # Attempt to grab screen using mss if native display is active
        if not self.display_manager.is_mock:
            try:
                import sys
                pkg_dir = "/home/acinonyx/Desktop/MAS/bin/packages"
                if pkg_dir not in sys.path:
                    sys.path.insert(0, pkg_dir)
                import mss
                with mss.MSS() as sct:
                    # Capture root monitor
                    monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                    sct_img = sct.grab(monitor)
                    raw_image = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as e:
                LOGGER.warning(f"Native screenshot grab failed: {e}. Falling back to canvas synthesis.")

        if raw_image is None:
            # Generate deterministic synthetic desktop canvas with wallpaper & taskbar
            raw_image = Image.new("RGB", (width, height), color=(34, 40, 49))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(raw_image)
            # Draw bottom taskbar
            draw.rectangle([0, height - 40, width, height], fill=(24, 28, 34))
            draw.rectangle([10, height - 34, 80, height - 6], fill=(57, 62, 70))
            # Draw cursor representation
            draw.polygon(
                [
                    (self.cursor_x, self.cursor_y),
                    (self.cursor_x + 10, self.cursor_y + 10),
                    (self.cursor_x + 3, self.cursor_y + 11),
                    (self.cursor_x, self.cursor_y + 15),
                ],
                fill=(255, 255, 255),
            )

        marks_dict: Optional[Dict[int, UIElementMark]] = None
        if apply_som:
            raw_image, marks_dict = overlay_set_of_marks(raw_image)
            self.last_marks = marks_dict or {}

        b64, sw, sh, byte_size = compress_and_encode_frame(
            raw_image, max_dimension=max_dimension, quality=quality
        )

        img_hash = hashlib.sha256(b64.encode("ascii")).hexdigest()
        self._log_audit("screenshot", {"width": width, "height": height, "som": apply_som, "hash": img_hash})
        METRICS.incr("computer_use.screenshots_taken")

        return {
            "success": True,
            "base64_data": b64,
            "format": "webp",
            "physical_width": width,
            "physical_height": height,
            "scaled_width": sw,
            "scaled_height": sh,
            "byte_size": byte_size,
            "sha256": img_hash,
            "element_marks": {
                mid: {"x": m.center_x, "y": m.center_y, "bbox": m.bbox}
                for mid, m in (marks_dict or {}).items()
            },
        }

    def mouse_move(self, x: int, y: int, scaled: bool = False, scaled_width: int = 1024, scaled_height: int = 640) -> Dict[str, Any]:
        """Move cursor to specified coordinates."""
        pw = self.display_manager.config.width
        ph = self.display_manager.config.height

        if scaled:
            target_x, target_y = scale_coordinates(x, y, scaled_width, scaled_height, pw, ph)
        else:
            target_x = max(0, min(pw - 1, int(x)))
            target_y = max(0, min(ph - 1, int(y)))

        self.cursor_x = target_x
        self.cursor_y = target_y

        self._execute_xdotool(["mousemove", str(target_x), str(target_y)])
        self._log_audit("mouse_move", {"x": target_x, "y": target_y})
        METRICS.incr("computer_use.mouse_moves")

        return {"success": True, "cursor_x": target_x, "cursor_y": target_y}

    def mouse_click(
        self,
        x: Optional[int] = None,
        y: Optional[int] = None,
        button: str = "left",
        click_count: int = 1,
        scaled: bool = False,
    ) -> Dict[str, Any]:
        """Execute single, double, or triple mouse click."""
        if x is not None and y is not None:
            self.mouse_move(x, y, scaled=scaled)

        btn_map = {"left": "1", "middle": "2", "right": "3"}
        btn_code = btn_map.get(button.lower(), "1")

        args = ["click", "--repeat", str(max(1, min(3, click_count))), btn_code]
        self._execute_xdotool(args)
        self._log_audit("mouse_click", {"x": self.cursor_x, "y": self.cursor_y, "button": button, "count": click_count})
        METRICS.incr(f"computer_use.clicks_{button}")

        return {"success": True, "clicked_at": {"x": self.cursor_x, "y": self.cursor_y}, "button": button, "count": click_count}

    def click_element_by_id(self, element_id: int) -> Dict[str, Any]:
        """Click a numbered visual element identified during a Set-of-Mark screenshot."""
        if element_id not in self.last_marks:
            err = f"Element ID [{element_id}] not found in active Set-of-Mark cache. Call screenshot(apply_som=True) first."
            self._log_audit("click_element_by_id", {"id": element_id}, status="failed", error=err)
            return {"success": False, "error": err}

        mark = self.last_marks[element_id]
        return self.mouse_click(x=mark.center_x, y=mark.center_y, button="left", click_count=1)

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int) -> Dict[str, Any]:
        """Simulate mouse click-and-drag from start to end coordinate."""
        self.mouse_move(start_x, start_y)
        self._execute_xdotool(["mousedown", "1"])
        self.mouse_move(end_x, end_y)
        self._execute_xdotool(["mouseup", "1"])
        self._log_audit("mouse_drag", {"from": (start_x, start_y), "to": (end_x, end_y)})
        METRICS.incr("computer_use.mouse_drags")
        return {"success": True, "from": {"x": start_x, "y": start_y}, "to": {"x": end_x, "y": end_y}}

    def mouse_scroll(self, clicks: int = 3, direction: str = "down") -> Dict[str, Any]:
        """Simulate mouse wheel scrolling (button 4=up, 5=down)."""
        btn = "5" if direction.lower() == "down" else "4"
        for _ in range(max(1, min(20, clicks))):
            self._execute_xdotool(["click", btn])
        self._log_audit("mouse_scroll", {"clicks": clicks, "direction": direction})
        METRICS.incr("computer_use.scrolls")
        return {"success": True, "clicks": clicks, "direction": direction}

    def type_text(self, text: str, delay_ms: float = 12.0) -> Dict[str, Any]:
        """Type text string with Scope Jail validation."""
        self.jail.validate_text(text)
        delay_arg = str(int(delay_ms))
        self._execute_xdotool(["type", "--delay", delay_arg, text])
        self._log_audit("type_text", {"char_count": len(text), "preview": text[:20]})
        METRICS.incr("computer_use.text_typed")
        return {"success": True, "typed_characters": len(text)}

    def key_combination(self, keys: List[str]) -> Dict[str, Any]:
        """Press key combination chord with Scope Jail validation."""
        self.jail.validate_keys(keys)
        chord = "+".join(keys)
        self._execute_xdotool(["key", chord])
        self._log_audit("key_combination", {"keys": keys})
        METRICS.incr("computer_use.key_combinations")
        return {"success": True, "keys": keys}

    def get_status(self) -> Dict[str, Any]:
        """Return operational state of the Computer Use engine."""
        disp_status = self.display_manager.get_status()
        return {
            "display": disp_status["display"],
            "is_virtual_display_active": disp_status["is_active"],
            "is_mock_simulation": disp_status["is_mock"],
            "cursor": {"x": self.cursor_x, "y": self.cursor_y},
            "cached_som_marks": len(self.last_marks),
            "xdotool_installed": self._is_xdotool_available(),
            "audit_log_path": self.audit_log_path,
        }


# Global singleton controller instance
GLOBAL_COMPUTER_CONTROLLER = ComputerUseController()


def register_computer_use_tools(registry: MCPRegistry) -> None:
    """Register all discrete OS automation tools into the MCP tool registry."""
    controller = GLOBAL_COMPUTER_CONTROLLER

    registry.register_tool(
        name="computer_screenshot",
        description="Capture a visual frame of the virtual desktop display. Supports Token FinOps WebP encoding and Set-of-Mark [ID] badges.",
        input_schema={
            "type": "object",
            "properties": {
                "apply_som": {"type": "boolean", "default": False, "description": "Overlay numbered [ID] badges on interactive UI elements"},
                "max_dimension": {"type": "integer", "default": 1024, "description": "Max pixel edge for Token FinOps compression"},
            },
        },
        handler=lambda **kwargs: controller.take_screenshot(
            apply_som=kwargs.get("apply_som", False),
            max_dimension=kwargs.get("max_dimension", 1024),
        ),
    )

    registry.register_tool(
        name="computer_mouse_click",
        description="Execute a mouse click on the desktop. Can click at current location or jump to (x, y) coordinates first.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Target X coordinate"},
                "y": {"type": "integer", "description": "Target Y coordinate"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "click_count": {"type": "integer", "enum": [1, 2, 3], "default": 1},
                "scaled": {"type": "boolean", "default": False, "description": "True if coordinates are from a 1024px scaled screenshot"},
            },
        },
        handler=lambda **kwargs: controller.mouse_click(
            x=kwargs.get("x"),
            y=kwargs.get("y"),
            button=kwargs.get("button", "left"),
            click_count=kwargs.get("click_count", 1),
            scaled=kwargs.get("scaled", False),
        ),
    )

    registry.register_tool(
        name="computer_click_element_id",
        description="Click an interactive UI element by its Set-of-Mark numeric ID (e.g. [1], [2]) without needing coordinate calculation.",
        input_schema={
            "type": "object",
            "properties": {
                "element_id": {"type": "integer", "description": "Numeric badge ID from prior Set-of-Mark screenshot"},
            },
            "required": ["element_id"],
        },
        handler=lambda **kwargs: controller.click_element_by_id(element_id=kwargs["element_id"]),
    )

    registry.register_tool(
        name="computer_mouse_move",
        description="Move the cursor to specific pixel coordinates on the virtual display.",
        input_schema={
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "Target X pixel"},
                "y": {"type": "integer", "description": "Target Y pixel"},
                "scaled": {"type": "boolean", "default": False},
            },
            "required": ["x", "y"],
        },
        handler=lambda **kwargs: controller.mouse_move(
            x=kwargs["x"], y=kwargs["y"], scaled=kwargs.get("scaled", False)
        ),
    )

    registry.register_tool(
        name="computer_mouse_drag",
        description="Click and drag from (start_x, start_y) to (end_x, end_y) to drag files, sliders, or select regions.",
        input_schema={
            "type": "object",
            "properties": {
                "start_x": {"type": "integer"},
                "start_y": {"type": "integer"},
                "end_x": {"type": "integer"},
                "end_y": {"type": "integer"},
            },
            "required": ["start_x", "start_y", "end_x", "end_y"],
        },
        handler=lambda **kwargs: controller.mouse_drag(
            start_x=kwargs["start_x"], start_y=kwargs["start_y"], end_x=kwargs["end_x"], end_y=kwargs["end_y"]
        ),
    )

    registry.register_tool(
        name="computer_mouse_scroll",
        description="Scroll the mouse wheel up or down by a given number of clicks.",
        input_schema={
            "type": "object",
            "properties": {
                "clicks": {"type": "integer", "default": 3},
                "direction": {"type": "string", "enum": ["up", "down"], "default": "down"},
            },
        },
        handler=lambda **kwargs: controller.mouse_scroll(
            clicks=kwargs.get("clicks", 3), direction=kwargs.get("direction", "down")
        ),
    )

    registry.register_tool(
        name="computer_type_text",
        description="Type a string into the active desktop window with safety scope jail inspection.",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Characters to type"},
                "delay_ms": {"type": "number", "default": 12.0},
            },
            "required": ["text"],
        },
        handler=lambda **kwargs: controller.type_text(
            text=kwargs["text"], delay_ms=kwargs.get("delay_ms", 12.0)
        ),
    )

    registry.register_tool(
        name="computer_key_combination",
        description="Press keyboard chord combinations (e.g. ['Ctrl', 'Alt', 't'], ['Return'], ['Ctrl', 's']).",
        input_schema={
            "type": "object",
            "properties": {
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key names to press simultaneously",
                },
            },
            "required": ["keys"],
        },
        handler=lambda **kwargs: controller.key_combination(keys=kwargs["keys"]),
    )

    registry.register_tool(
        name="computer_status",
        description="Inspect the operational state of the virtual display, cursor position, and computer use engine.",
        input_schema={"type": "object", "properties": {}},
        handler=lambda **kwargs: controller.get_status(),
    )
