#!/usr/bin/env python3
"""
scripts/live_computer_use_demo.py: Live Human-Like Desktop & Chrome Automation Demo.
Drives native X11 virtual display :99, launches Google Chrome, searches for local businesses in Benoni,
executes human-like mouse movements, clicks, typing, scrolling, and captures artifacts.

Architect: Acinonyx / MAS-Core
"""

import os
import sys
import time
import base64
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mas.tools.display import VirtualDisplayManager, VirtualDisplayConfig
from mas.tools.computer_use import ComputerUseController


ARTIFACT_DIR = Path("/home/acinonyx/.gemini/antigravity-ide/brain/cb20c3b1-4785-4d47-9c27-9d47cfab2e33")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def save_screenshot(controller: ComputerUseController, filename: str, apply_som: bool = False) -> str:
    shot = controller.take_screenshot(apply_som=apply_som, max_dimension=1280)
    out_path = ARTIFACT_DIR / filename
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(shot["base64_data"]))
    print(f"📸 Captured: {filename} ({shot['scaled_width']}x{shot['scaled_height']}, SoM={apply_som})")
    return str(out_path)


def run_demo():
    print("🚀 Initializing MAS Native Virtual Display (:99, 1440x900)...")
    vdm = VirtualDisplayManager(VirtualDisplayConfig(display_num=99, width=1440, height=900))
    vdm.start()

    controller = ComputerUseController(display_manager=vdm)
    print("✅ Virtual Display active. Initial status:", controller.get_status())

    env = os.environ.copy()
    env["DISPLAY"] = ":99"
    if "WAYLAND_DISPLAY" in env:
        del env["WAYLAND_DISPLAY"]

    # Step 1: Launch Google Chrome on Google
    print("\n🌐 Step 1: Launching Google Chrome to Google Homepage...")
    chrome_proc = subprocess.Popen([
        "google-chrome",
        "--ozone-platform=x11",
        "--no-sandbox",
        "--test-type",
        "--user-data-dir=/tmp/mas_chrome_user_session",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "https://www.google.com"
    ], env=env)

    time.sleep(5)
    save_screenshot(controller, "cua_step1_chrome_homepage.webp", apply_som=True)

    # Step 2: Human-like mouse movement and click into Google Search bar
    print("\n🖱️ Step 2: Moving cursor with human trajectory to Google Search bar (x=700, y=415) and clicking...")
    # Realistic human mouse movement with natural curve and decelerating approach
    trajectory = [
        (150, 150),
        (320, 240),
        (490, 310),
        (610, 370),
        (680, 405),
        (700, 415)
    ]
    for x, y in trajectory:
        controller.mouse_move(x, y)
        time.sleep(0.08)
    
    controller.mouse_click(700, 415, button="left")
    time.sleep(0.4)
    save_screenshot(controller, "cua_step2_search_bar_focused.webp")

    # Step 3: Type search query with natural keystroke cadence
    search_query = "top manufacturing and logistics companies in Benoni Gauteng"
    print(f"\n⌨️ Step 3: Typing query with human cadence: '{search_query}'...")
    controller.type_text(search_query, delay_ms=35.0)
    time.sleep(0.6)
    save_screenshot(controller, "cua_step3_query_typed.webp")

    # Step 4: Submit search and wait for results to settle
    print("\n⏎ Step 4: Pressing Return and waiting for search results to render...")
    controller.key_combination(["Return"])
    time.sleep(4.0)
    controller.wait_for_state_change(timeout_sec=3.0)
    save_screenshot(controller, "cua_step4_google_search_results.webp", apply_som=True)

    # Step 5: Human-like page inspection: Scroll down
    print("\n📜 Step 5: Scrolling down page like a human reading listings...")
    controller.mouse_scroll(clicks=5, direction="down")
    time.sleep(1.2)
    save_screenshot(controller, "cua_step5_scrolled_results.webp")

    # Step 6: Navigate directly to Google Maps for Benoni commercial directory
    print("\n🗺️ Step 6: Directing Chrome to Google Maps business directory for Benoni, Gauteng...")
    maps_url = "https://www.google.com/maps/search/businesses+in+Benoni+Gauteng"
    controller.key_combination(["ctrl", "l"])
    time.sleep(0.4)
    controller.type_text(maps_url, delay_ms=12.0)
    time.sleep(0.3)
    controller.key_combination(["Return"])
    time.sleep(6.0)
    controller.wait_for_state_change(timeout_sec=4.0)
    save_screenshot(controller, "cua_step6_google_maps_benoni.webp")

    # Step 7: Hover over the Maps listings pane and scroll
    print("\n📍 Step 7: Inspecting Google Maps business pane and scrolling through companies...")
    # Move smoothly into the left results drawer
    maps_panel_trajectory = [
        (600, 300),
        (450, 360),
        (260, 420)
    ]
    for x, y in maps_panel_trajectory:
        controller.mouse_move(x, y)
        time.sleep(0.08)
    
    controller.mouse_click(260, 420)
    time.sleep(0.5)
    controller.mouse_scroll(clicks=6, direction="down")
    time.sleep(1.5)
    save_screenshot(controller, "cua_step7_maps_scrolled_businesses.webp", apply_som=True)

    # Step 8: Click on a business card to inspect its details profile
    print("\n🔍 Step 8: Clicking on a business card in the drawer to inspect contact & address details...")
    controller.mouse_click(240, 350)
    time.sleep(3.0)
    save_screenshot(controller, "cua_step8_business_detail_inspected.webp")

    # Clean up
    print("\n🧹 Shutting down demo session...")
    chrome_proc.terminate()
    try:
        chrome_proc.wait(timeout=3)
    except Exception:
        chrome_proc.kill()
    vdm.stop()
    print("✨ Demo execution finished successfully!")


if __name__ == "__main__":
    run_demo()
