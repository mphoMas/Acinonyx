"""
tests/test_portal_web.py: Automated E2E verification of the Acinonyx Research Portal.
Tests reader rendering, Copilot neural assistant, toast notifications,
and keyboard shortcuts in headless Chromium.
"""

import unittest
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
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
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(cls.portal_path.parent)))
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.portal_url = f"http://127.0.0.1:{cls.http.server_port}/index.html"

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()

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

    def test_portal_board_flow(self):
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

            # 1. Load portal and navigate to Board
            page.goto(self.portal_url)
            page.wait_for_selector("#app-container")
            page.click("#nav-board")
            page.wait_for_selector("#view-board:visible")

            # 2. Verify 7 Columns exist
            columns = ["backlog", "refined", "staged", "in_progress", "verification", "judicial_review", "done"]
            for col in columns:
                page.wait_for_selector(f"#column-{col}")

            # 3. Verify Telemetry HUD badges
            page.wait_for_selector("#board-flow-health")
            page.wait_for_selector("#board-wip-saturation")

            # 4. Verify Cards rendered and clicking opens slide-over drawer
            page.wait_for_selector(".kanban-card")
            self.assertIn("OFFLINE SNAPSHOT", page.inner_text("#board-flow-health"))
            first_card = page.locator(".kanban-card").first
            card_key = first_card.locator(".card-key").inner_text()
            first_card.click()

            page.wait_for_selector("#board-detail-drawer.drawer-open")
            drawer_key = page.inner_text("#drawer-issue-key")
            self.assertEqual(card_key, drawer_key)

            # Close drawer
            page.click("#drawer-close-btn")
            page.wait_for_function("!document.getElementById('board-detail-drawer').classList.contains('drawer-open')")

            # 5. Open New Issue Modal
            page.click("#board-new-issue-btn")
            page.wait_for_selector("#modal-new-issue:visible")
            page.keyboard.press("Escape")
            page.wait_for_function("document.getElementById('modal-new-issue').style.display === 'none'")

            # 6. Test Guard Rejection Modal presentation
            page.evaluate("""() => {
                window.boardView.showRejectionModal({
                    error: 'WIPLimitExceededError',
                    targetState: 'IN_PROGRESS',
                    message: "Column WIP limit exceeded for state 'IN_PROGRESS' [Current: 4, Limit: 4]. Flow throttled per Little's Law."
                });
            }""")
            page.wait_for_selector("#rejection-modal-backdrop.modal-open")
            self.assertIn("WIPLimitExceededError", page.inner_text("#rejection-modal-title"))
            page.click("#rejection-modal-close-btn")
            page.wait_for_function("!document.getElementById('rejection-modal-backdrop').classList.contains('modal-open')")

            # 7. Zero fatal console errors
            fatal_errors = [e for e in console_errors if "Failed to load resource" not in e and "Backend board API unreachable" not in e]
            self.assertEqual(fatal_errors, [])

            browser.close()


if __name__ == "__main__":
    unittest.main()
