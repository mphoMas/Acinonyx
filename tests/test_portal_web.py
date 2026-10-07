"""
tests/test_portal_web.py: Automated E2E verification of the Acinonyx Research Portal.
Tests reader rendering, Copilot neural assistant, toast notifications,
and keyboard shortcuts in headless Chromium.
"""

import unittest
from mas.config import REPO_ROOT

try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except ImportError:
    HAVE_PLAYWRIGHT = False


@unittest.skipUnless(HAVE_PLAYWRIGHT, "Playwright is required for browser E2E tests")
class TestPortalWebUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.portal_path = (REPO_ROOT / "portal" / "index.html").resolve()
        cls.portal_url = f"file://{cls.portal_path}"

    def test_portal_e2e_flow(self):
        with sync_playwright() as p:
            import shutil
            chrome_path = shutil.which("google-chrome")
            launch_args = {"headless": True}
            if chrome_path:
                launch_args["executable_path"] = chrome_path
            elif (REPO_ROOT / "bin/browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell").exists():
                launch_args["executable_path"] = str(REPO_ROOT / "bin/browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell")

            browser = p.chromium.launch(**launch_args)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            console_errors = []
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

            # 1. Load portal
            page.goto(self.portal_url)
            page.wait_for_selector("#app-container")
            self.assertIn("Acinonyx", page.title())

            # 2. Test Copilot drawer open & query
            page.click("#copilot-nav-btn")
            page.wait_for_selector("#copilot-drawer.open")

            # Ask Copilot a question
            page.fill("#copilot-input", "What is GRPO?")
            page.press("#copilot-input", "Enter")

            # Verify thinking indicator and synthesized answer
            page.wait_for_selector(".copilot-answer-text", timeout=5000)
            page.wait_for_selector(".copilot-citation-pill", timeout=5000)
            answer_text = page.inner_text(".copilot-answer-text")
            self.assertTrue(len(answer_text) > 20)

            # 3. Test clicking a citation navigates to reader
            page.click(".copilot-citation-pill")
            page.wait_for_selector("#view-reader:visible")
            title_text = page.inner_text("#reader-title")
            self.assertTrue(len(title_text) > 0)

            # 4. Test bookmarking current chapter
            page.click("#star-btn")
            page.wait_for_selector(".toast-item.toast-visible")
            toasts = [t.lower() for t in page.locator(".toast-message").all_inner_texts()]
            self.assertTrue(any("favorites" in t for t in toasts))

            # 5. Test Shortcuts HUD modal
            page.keyboard.press("?")
            page.wait_for_selector("#shortcuts-modal.active")
            page.keyboard.press("Escape")
            page.wait_for_function("!document.getElementById('shortcuts-modal').classList.contains('active')")

            # 6. Verify zero fatal console errors
            # Filter out expected harmless external resource notices if offline
            fatal_errors = [e for e in console_errors if "Failed to load resource" not in e]
            self.assertEqual(fatal_errors, [])

            browser.close()


if __name__ == "__main__":
    unittest.main()
