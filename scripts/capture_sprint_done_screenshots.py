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

        # 1. Capture standalone Scrum board (All Columns)
        print("[*] Navigating to http://localhost:8080/scrum...")
        page.goto("http://localhost:8080/scrum", wait_until="networkidle")
        page.wait_for_timeout(2000)

        all_scrum_path = ARTIFACTS_DIR / "scrum_board_all_columns.png"
        page.screenshot(path=str(all_scrum_path), full_page=True)
        print(f"[+] Saved Scrum board all columns screenshot to: {all_scrum_path}")

        # Click Done Column button
        page.click("button[data-col-view='DONE']")
        page.wait_for_timeout(1000)
        scrum_img_path = ARTIFACTS_DIR / "scrum_board_sprint2_done.png"
        page.screenshot(path=str(scrum_img_path), full_page=True)
        print(f"[+] Saved Scrum board Done view screenshot to: {scrum_img_path}")

        # 2. Capture native portal board
        print("[*] Navigating to http://localhost:8080/portal/index.html...")
        page.goto("http://localhost:8080/portal/index.html", wait_until="networkidle")
        page.wait_for_timeout(1500)

        # Switch to Board view
        page.evaluate('() => app.switchView("board")')
        page.wait_for_timeout(2000)

        all_portal_path = ARTIFACTS_DIR / "portal_board_all_columns.png"
        page.screenshot(path=str(all_portal_path), full_page=True)
        print(f"[+] Saved Portal board all columns screenshot to: {all_portal_path}")

        # Click Done tab on portal board
        page.click("#col-view-done")
        page.wait_for_timeout(1000)
        portal_img_path = ARTIFACTS_DIR / "portal_board_sprint2_done.png"
        page.screenshot(path=str(portal_img_path), full_page=True)
        print(f"[+] Saved Portal board Done view screenshot to: {portal_img_path}")

        browser.close()


if __name__ == "__main__":
    main()

