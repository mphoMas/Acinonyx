"""
Integration tests for computer use against a *real* Xvfb display and xdotool
(no mock simulation). Skipped automatically when Xvfb/xdotool are not installed.
"""

import os
import shutil
import subprocess
import tempfile
import unittest

from mas.tools.computer_use import ComputerUseController
from mas.tools.display import VirtualDisplayConfig, VirtualDisplayManager

HAVE_X = shutil.which("Xvfb") is not None and shutil.which("xdotool") is not None


@unittest.skipUnless(HAVE_X, "Xvfb and xdotool are required")
class TestRealXvfbComputerUse(unittest.TestCase):
    DISPLAY_NUM = 97  # avoid clashing with the default :99 used elsewhere

    @classmethod
    def setUpClass(cls):
        cls._saved_display = os.environ.get("DISPLAY")
        cfg = VirtualDisplayConfig(display_num=cls.DISPLAY_NUM, width=800, height=600, window_manager=None)
        cls.display = VirtualDisplayManager(cfg).start()
        if cls.display.is_mock:
            cls.display.stop()
            raise unittest.SkipTest("Xvfb failed to start; display fell back to mock mode")
        cls.audit = tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False)
        cls.audit.close()
        cls.controller = ComputerUseController(display_manager=cls.display, audit_log_path=cls.audit.name)

    @classmethod
    def tearDownClass(cls):
        cls.display.stop()
        os.unlink(cls.audit.name)
        if cls._saved_display is None:
            os.environ.pop("DISPLAY", None)
        else:
            os.environ["DISPLAY"] = cls._saved_display

    def _pointer(self):
        env = {**os.environ, "DISPLAY": self.display.display_str}
        out = subprocess.run(["xdotool", "getmouselocation"], env=env, capture_output=True, text=True, check=True).stdout
        parts = dict(p.split(":") for p in out.split() if ":" in p)
        return int(parts["x"]), int(parts["y"])

    def test_display_is_native(self):
        self.assertFalse(self.display.is_mock)
        self.assertTrue(self.display.get_status()["is_active"])

    def test_mouse_move_reaches_real_pointer(self):
        self.controller.mouse_move(321, 123)
        self.assertEqual(self._pointer(), (321, 123))

    def test_screenshot_has_expected_content(self):
        shot = self.controller.take_screenshot(apply_som=False, max_dimension=800)
        self.assertGreater(shot["byte_size"], 0)
        self.assertTrue(shot["base64_data"])


if __name__ == "__main__":
    unittest.main()
