"""
scripts/capture_sprint_done_screenshots.py: Captures full high-resolution screenshots
of the Scrum Delivery Board and Native Portal Board showing all 31 tasks in DONE.
"""

from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = Path("/home/acinonyx/.gemini/antigravity-ide/brain/0505e578-300b-41cb-9851-8a1c6895b23c")
REPO_ROOT = Path("/home/acinonyx/Desktop/MAS")


def main():
    chrome_path = shutil.which("google-chrome")
    launch_args = {"headless": True}
    if chrome_path:
        launch_args["executable_path"] = chrome_path
    elif (REPO_ROOT / "bin/browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell").exists():
        launch_args["executable_path"] = str(REPO_ROOT / "bin/browsers/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell")

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_args)
        context = browser.new_context(viewport={"width": 1600, "height": 1050})
        page = context.new_page()

        # 1. Capture standalone Scrum board
        print("[*] Navigating to http://localhost:8080/scrum...")
        page.goto("http://localhost:8080/scrum", wait_until="networkidle")
        page.wait_for_timeout(3000)

        scrum_img_path = ARTIFACTS_DIR / "scrum_board_sprint2_done.png"
        page.screenshot(path=str(scrum_img_path), full_page=True)
        print(f"[+] Saved Scrum board screenshot to: {scrum_img_path}")

        # 2. Capture native portal board
        print("[*] Navigating to http://localhost:8080/portal/index.html...")
        page.goto("http://localhost:8080/portal/index.html", wait_until="networkidle")
        page.wait_for_timeout(2000)

        # Click on PM / Delivery board button in native portal if available
        pm_btn = page.query_selector("button:has-text('Scrum'), button:has-text('Board'), a:has-text('Board'), [data-tab='board']")
        if pm_btn:
            pm_btn.click()
            page.wait_for_timeout(2000)

        portal_img_path = ARTIFACTS_DIR / "portal_board_sprint2_done.png"
        page.screenshot(path=str(portal_img_path), full_page=True)
        print(f"[+] Saved Portal board screenshot to: {portal_img_path}")

        browser.close()


if __name__ == "__main__":
    main()
