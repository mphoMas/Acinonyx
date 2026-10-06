"""
tests.test_computer_use: Comprehensive test suite for MAS-Core Computer Use capabilities.
Verifies discrete OS action spaces, Set-of-Mark grounding, virtual display isolation,
Token FinOps compression, security Scope Jails, and MCP tool registration.
"""

import json
import os
import unittest
from PIL import Image

from mas.capabilities import CAPABILITIES, capability_matrix
from mas.core.message import ContentType, Message, Role
from mas.mcp.protocol import MCPRegistry
from mas.providers.http_provider import OpenAICompatibleProvider
from mas.tools.computer_use import (
    ComputerUseController,
    ComputerUseScopeJail,
    ComputerUseSecurityError,
    register_computer_use_tools,
)
from mas.tools.display import VirtualDisplayConfig, VirtualDisplayManager
from mas.tools.grounding import (
    compress_and_encode_frame,
    overlay_set_of_marks,
    scale_coordinates,
)


class TestComputerUseGrounding(unittest.TestCase):
    def test_coordinate_scaling_exact(self):
        # 1024x768 -> 1440x900
        phys_x, phys_y = scale_coordinates(
            512, 384, scaled_width=1024, scaled_height=768, physical_width=1440, physical_height=900
        )
        self.assertEqual(phys_x, 720)
        self.assertEqual(phys_y, 450)

    def test_coordinate_scaling_clamping(self):
        # Negative and overflowing coordinates must be clamped to screen bounds
        phys_x, phys_y = scale_coordinates(
            -50, 2000, scaled_width=1024, scaled_height=768, physical_width=1440, physical_height=900
        )
        self.assertEqual(phys_x, 0)
        self.assertEqual(phys_y, 899)

    def test_token_finops_downsampling(self):
        raw_img = Image.new("RGB", (1920, 1080), color=(100, 150, 200))
        b64, sw, sh, byte_size = compress_and_encode_frame(raw_img, max_dimension=1024)
        self.assertEqual(sw, 1024)
        self.assertEqual(sh, 576)
        self.assertTrue(len(b64) > 0)
        self.assertTrue(byte_size > 0)

    def test_set_of_mark_badges(self):
        raw_img = Image.new("RGB", (1000, 800), color=(40, 40, 40))
        custom_boxes = [(50, 50, 150, 100), (200, 200, 400, 300)]
        som_img, marks = overlay_set_of_marks(raw_img, candidates=custom_boxes)
        self.assertEqual(len(marks), 2)
        self.assertEqual(marks[1].center_x, 100)
        self.assertEqual(marks[1].center_y, 75)
        self.assertEqual(marks[2].center_x, 300)
        self.assertEqual(marks[2].center_y, 250)


class TestComputerUseScopeJail(unittest.TestCase):
    def setUp(self):
        self.jail = ComputerUseScopeJail()

    def test_prohibited_hotkeys_blocked(self):
        with self.assertRaises(ComputerUseSecurityError):
            self.jail.validate_keys(["ctrl", "alt", "delete"])
        with self.assertRaises(ComputerUseSecurityError):
            self.jail.validate_keys(["Ctrl", "Alt", "F1"])

    def test_allowed_hotkeys_pass(self):
        # Standard shortcuts should not raise
        self.jail.validate_keys(["ctrl", "c"])
        self.jail.validate_keys(["ctrl", "shift", "t"])
        self.jail.validate_keys(["Return"])

    def test_destructive_shell_commands_blocked(self):
        with self.assertRaises(ComputerUseSecurityError):
            self.jail.validate_text("rm -rf /")
        with self.assertRaises(ComputerUseSecurityError):
            self.jail.validate_text(":(){ :|:& };:")

    def test_benign_text_typing_allowed(self):
        self.jail.validate_text("SELECT count(*) FROM billing.invoices;")
        self.jail.validate_text("echo 'System healthy'")


class TestComputerUseControllerAndMCP(unittest.TestCase):
    def setUp(self):
        self.vdm = VirtualDisplayManager(VirtualDisplayConfig(display_num=99))
        self.audit_log = "/tmp/test_mas_computer_use_audit.jsonl"
        if os.path.exists(self.audit_log):
            os.remove(self.audit_log)
        self.controller = ComputerUseController(display_manager=self.vdm, audit_log_path=self.audit_log)

    def tearDown(self):
        if os.path.exists(self.audit_log):
            try:
                os.remove(self.audit_log)
            except Exception:
                pass

    def test_screenshot_generation(self):
        res = self.controller.take_screenshot(apply_som=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["format"], "webp")
        self.assertTrue(res["byte_size"] > 0)
        self.assertIn("element_marks", res)
        self.assertTrue(len(res["sha256"]) == 64)

    def test_mouse_move_and_clamping(self):
        res = self.controller.mouse_move(500, 300)
        self.assertTrue(res["success"])
        self.assertEqual(res["cursor_x"], 500)
        self.assertEqual(res["cursor_y"], 300)

        # Clamping
        res_clamp = self.controller.mouse_move(3000, -20)
        self.assertEqual(res_clamp["cursor_x"], 1439)
        self.assertEqual(res_clamp["cursor_y"], 0)

    def test_mouse_clicks_and_drags(self):
        click_res = self.controller.mouse_click(100, 200, button="left", click_count=2)
        self.assertTrue(click_res["success"])
        self.assertEqual(click_res["clicked_at"], {"x": 100, "y": 200})

        drag_res = self.controller.mouse_drag(50, 50, 250, 350)
        self.assertTrue(drag_res["success"])
        self.assertEqual(drag_res["to"], {"x": 250, "y": 350})

    def test_click_element_by_id(self):
        # First take screenshot with Set-of-Mark
        self.controller.take_screenshot(apply_som=True)
        self.assertTrue(len(self.controller.last_marks) > 0)

        # Click Mark [1]
        res = self.controller.click_element_by_id(1)
        self.assertTrue(res["success"])

        # Click invalid mark
        res_invalid = self.controller.click_element_by_id(9999)
        self.assertFalse(res_invalid["success"])

    def test_mcp_tools_registration_and_dispatch(self):
        registry = MCPRegistry()
        register_computer_use_tools(registry)
        tool_names = set(registry.tools.keys())

        expected_tools = {
            "computer_screenshot",
            "computer_mouse_click",
            "computer_mouse_move",
            "computer_mouse_drag",
            "computer_mouse_scroll",
            "computer_type_text",
            "computer_key_combination",
            "computer_click_element_id",
            "computer_status",
        }
        self.assertTrue(expected_tools.issubset(tool_names), f"Missing tools: {expected_tools - tool_names}")

        # Invoke computer_status via MCP registry
        status_res = registry.call_tool("computer_status", {})
        self.assertIn("display", status_res)
        self.assertIn("cursor", status_res)


class TestMultimodalMessagingAndCapabilities(unittest.TestCase):
    def test_multimodal_message_creation(self):
        msg = Message(
            sender="vision_agent",
            recipient="controller",
            role=Role.ASSISTANT,
            content=[
                {"type": "text", "text": "Analyzing desktop screen..."},
                {"type": "image_url", "image_url": {"url": "data:image/webp;base64,UklGRg..."}},
            ],
            content_type=ContentType.MULTIMODAL,
        )
        self.assertEqual(msg.text_content, "Analyzing desktop screen...")
        self.assertEqual(msg.content_type, ContentType.MULTIMODAL)

        # Ensure JSON serialization roundtrips
        json_str = msg.to_json()
        restored = Message.from_json(json_str)
        self.assertEqual(restored.text_content, msg.text_content)

    def test_capability_matrix_includes_computer_use(self):
        matrix = capability_matrix()
        self.assertIn("computer_use", matrix)
        self.assertEqual(matrix["computer_use"]["status"], "implemented")


if __name__ == "__main__":
    unittest.main()
