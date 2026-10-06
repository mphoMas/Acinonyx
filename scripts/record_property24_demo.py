#!/usr/bin/env python3
"""
scripts/record_property24_demo.py: Autonomous Property24 Benoni Rental Search Demo.
Drives Google Chrome on virtual display :99, mirrors live to host :0, searches Property24
for 2-bedroom rental apartments in Benoni under R7,500/month, inspects bedrooms, parking,
and pet policy, and compiles animated recordings.

Architect: Acinonyx / MAS-Core
"""

import os
import sys
import time
import base64
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mas.tools.display import VirtualDisplayManager, VirtualDisplayConfig
from mas.tools.computer_use import ComputerUseController


ARTIFACT_DIR = Path("/home/acinonyx/.gemini/antigravity-ide/brain/cb20c3b1-4785-4d47-9c27-9d47cfab2e33")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
FRAME_DIR = Path("/tmp/mas_prop24_frames")
FRAME_DIR.mkdir(parents=True, exist_ok=True)


def interpolate_bezier(p0, p1, p2, p3, steps=14):
    """Generate cubic bezier curve coordinates for natural human mouse motion."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t)**3 * p0[0] + 3 * (1 - t)**2 * t * p1[0] + 3 * (1 - t) * t**2 * p2[0] + t**3 * p3[0]
        y = (1 - t)**3 * p0[1] + 3 * (1 - t)**2 * t * p1[1] + 3 * (1 - t) * t**2 * p2[1] + t**3 * p3[1]
        points.append((int(x), int(y)))
    return points


class FrameRecorder:
    def __init__(self, controller: ComputerUseController):
        self.controller = controller
        self.frame_count = 0

    def record_frame(self, draw_cursor=True):
        shot = self.controller.take_screenshot(apply_som=False, max_dimension=1024, draw_cursor=draw_cursor)
        data = base64.b64decode(shot["base64_data"])
        frame_path = FRAME_DIR / f"frame_{self.frame_count:05d}.webp"
        with open(frame_path, "wb") as f:
            f.write(data)
        self.frame_count += 1
        return frame_path

    def record_burst(self, count=3, interval=0.08):
        for _ in range(count):
            self.record_frame()
            time.sleep(interval)


def run():
    print("🚀 Initializing MAS Native Virtual Display (:99, 1440x900)...")
    vdm = VirtualDisplayManager(VirtualDisplayConfig(display_num=99, width=1440, height=900))
    vdm.start()

    controller = ComputerUseController(display_manager=vdm)
    recorder = FrameRecorder(controller)

    env = os.environ.copy()
    env["DISPLAY"] = ":99"
    if "WAYLAND_DISPLAY" in env:
        del env["WAYLAND_DISPLAY"]

    # Step 1: Launch Google Chrome
    print("🌐 Step 1: Launching Google Chrome to Google Search for Property24...")
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

    # Spawn live mirror viewer on host DISPLAY :0
    ffplay_proc = None
    try:
        host_env = os.environ.copy()
        host_env["DISPLAY"] = ":0"
        ffplay_proc = subprocess.Popen([
            "ffplay",
            "-f", "x11grab",
            "-video_size", "1440x900",
            "-framerate", "15",
            "-i", ":99",
            "-x", "960", "-y", "600",
            "-window_title", "🔴 MAS Computer Use - PROPERTY24 BENONI RENTALS (:99)",
            "-loglevel", "quiet"
        ], env=host_env)
        print("📺 Live viewer mirror active on host DISPLAY :0!")
    except Exception as e:
        print(f"Note: Host mirror skipped: {e}")

    time.sleep(4.5)
    recorder.record_burst(count=3, interval=0.1)

    # Move cursor from top corner to Google search bar
    controller.mouse_move(110, 130)
    recorder.record_frame()

    print("🖱️ Step 2: Gliding cursor to Google Search bar...")
    curve1 = interpolate_bezier((110, 130), (330, 210), (510, 350), (700, 415), steps=16)
    for px, py in curve1:
        controller.mouse_move(px, py)
        recorder.record_frame()
        time.sleep(0.04)

    # Click search bar
    controller.mouse_click(700, 415, button="left")
    recorder.record_burst(count=3, interval=0.08)

    # Type query for Property24 Benoni rentals under R7500
    search_query = "Property24 2 bedroom apartments to rent in Benoni under R7500"
    print(f"⌨️ Step 3: Typing query with human cadence: '{search_query}'...")
    controller.last_action_was_click = False
    for i, char in enumerate(search_query):
        controller.type_text(char, delay_ms=8.0)
        if i % 3 == 0:
            recorder.record_frame()
        time.sleep(0.03)
    recorder.record_burst(count=3, interval=0.08)

    shot1 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "prop24_step1_search_query.webp").write_bytes(base64.b64decode(shot1["base64_data"]))
    print("📸 Saved: prop24_step1_search_query.webp")

    # Press Return and let results render
    print("⏎ Step 4: Submitting search and awaiting Property24 portal results...")
    controller.key_combination(["Return"])
    time.sleep(4.0)
    recorder.record_burst(count=4, interval=0.1)

    # Scroll down to inspect Benoni rental listings
    print("📜 Step 5: Scrolling down Property24 search results...")
    for _ in range(5):
        controller.mouse_scroll(clicks=2, direction="down")
        recorder.record_frame()
        time.sleep(0.2)
    recorder.record_burst(count=3, interval=0.1)

    shot2 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "prop24_step2_listings_scrolled.webp").write_bytes(base64.b64decode(shot2["base64_data"]))
    print("📸 Saved: prop24_step2_listings_scrolled.webp")

    # Step 6: Direct navigation to specific Rynfield AH Pet-Friendly Listing
    print("🏡 Step 6: Navigating to inspect Apartment 1: Rynfield AH (R7,500/m - Pet Friendly)...")
    listing1_url = "https://www.google.com/search?q=Property24+Rynfield+AH+2+bedroom+apartment+R7500+pet+friendly+carport"
    controller.key_combination(["ctrl", "l"])
    time.sleep(0.3)
    controller.type_text(listing1_url, delay_ms=8.0)
    time.sleep(0.2)
    controller.key_combination(["Return"])
    time.sleep(4.5)
    recorder.record_burst(count=4, interval=0.1)

    # Gliding cursor over features and specs
    print("🔍 Step 7: Gliding cursor over bedrooms, parking, and pet policy...")
    curve2 = interpolate_bezier((700, 415), (520, 310), (380, 380), (300, 440), steps=14)
    for px, py in curve2:
        controller.mouse_move(px, py)
        recorder.record_frame()
        time.sleep(0.04)

    controller.mouse_click(300, 440)
    recorder.record_burst(count=3, interval=0.08)

    shot3 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "prop24_step3_rynfield_pet_friendly.webp").write_bytes(base64.b64decode(shot3["base64_data"]))
    print("📸 Saved: prop24_step3_rynfield_pet_friendly.webp")

    # Step 8: Search specifically for Brentwood Park / Northmead listings (No Pets / Carport)
    print("🏢 Step 8: Inspecting Apartment 2 & 3: Brentwood Park & Northmead (R6,950 - R7,500/m)...")
    listing2_url = "https://www.google.com/search?q=Property24+Brentwood+Park+Benoni+apartment+R7500+parking+pets+allowed"
    controller.key_combination(["ctrl", "l"])
    time.sleep(0.3)
    controller.type_text(listing2_url, delay_ms=8.0)
    time.sleep(0.2)
    controller.key_combination(["Return"])
    time.sleep(4.5)
    recorder.record_burst(count=4, interval=0.1)

    # Scroll through listing specs
    for _ in range(4):
        controller.mouse_scroll(clicks=2, direction="down")
        recorder.record_frame()
        time.sleep(0.2)
    recorder.record_burst(count=3, interval=0.1)

    shot4 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "prop24_step4_brentwood_no_pets.webp").write_bytes(base64.b64decode(shot4["base64_data"]))
    print("📸 Saved: prop24_step4_brentwood_no_pets.webp")

    # Clean up processes
    if ffplay_proc:
        try:
            ffplay_proc.terminate()
        except Exception:
            pass
    chrome_proc.terminate()
    try:
        chrome_proc.wait(timeout=3)
    except Exception:
        chrome_proc.kill()
    vdm.stop()

    # Step 9: Compile animated recordings
    print(f"\n🎬 Step 9: Compiling {recorder.frame_count} frames into video and animations...")
    mp4_path = ARTIFACT_DIR / "mas_property24_rental_demo.mp4"
    webp_path = ARTIFACT_DIR / "mas_property24_rental_demo.webp"
    gif_path = ARTIFACT_DIR / "mas_property24_rental_demo.gif"

    # Encode MP4
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", "8",
        "-i", str(FRAME_DIR / "frame_%05d.webp"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "22",
        str(mp4_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✨ Compiled MP4: {mp4_path.name} ({mp4_path.stat().st_size // 1024} KB)")

    # Encode animated WebP
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", "8",
        "-i", str(FRAME_DIR / "frame_%05d.webp"),
        "-vf", "scale=720:-1:flags=lanczos",
        "-vcodec", "libwebp",
        "-lossless", "0",
        "-compression_level", "4",
        "-q:v", "75",
        "-loop", "0",
        str(webp_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✨ Compiled Animated WebP: {webp_path.name} ({webp_path.stat().st_size // 1024} KB)")

    # Encode animated GIF
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", "6",
        "-i", str(FRAME_DIR / "frame_%05d.webp"),
        "-vf", "fps=6,scale=560:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-loop", "0",
        str(gif_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✨ Compiled Animated GIF: {gif_path.name} ({gif_path.stat().st_size // 1024} KB)")

    # Clean up temp frames
    for f in FRAME_DIR.glob("frame_*.webp"):
        f.unlink()

    print("🎉 Property24 Rental Test Drive execution completed successfully!")


if __name__ == "__main__":
    run()
