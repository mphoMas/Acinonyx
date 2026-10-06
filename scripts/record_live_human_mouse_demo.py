#!/usr/bin/env python3
"""
scripts/record_live_human_mouse_demo.py: High-Visibility Live Mouse & Computer Use Demo.
Drives Chrome on :99, mirrors to host screen :0 via live ffplay window, captures smooth
human-like mouse trajectories, click pulses, typing cadence, and compiles an animated recording.

Architect: Acinonyx / MAS-Core
"""

import os
import sys
import time
import base64
import json
import math
import subprocess
from pathlib import Path
from PIL import Image

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mas.tools.display import VirtualDisplayManager, VirtualDisplayConfig
from mas.tools.computer_use import ComputerUseController, draw_hardware_cursor


ARTIFACT_DIR = Path("/home/acinonyx/.gemini/antigravity-ide/brain/cb20c3b1-4785-4d47-9c27-9d47cfab2e33")
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
FRAME_DIR = Path("/tmp/mas_demo_frames")
FRAME_DIR.mkdir(parents=True, exist_ok=True)


def interpolate_bezier(p0, p1, p2, p3, steps=12):
    """Generate cubic bezier curve coordinates for natural human mouse motion."""
    points = []
    for i in range(steps + 1):
        t = i / steps
        # Cubic Bezier formula: B(t) = (1-t)^3*p0 + 3(1-t)^2*t*p1 + 3(1-t)*t^2*p2 + t^3*p3
        x = (1 - t)**3 * p0[0] + 3 * (1 - t)**2 * t * p1[0] + 3 * (1 - t) * t**2 * p2[0] + t**3 * p3[0]
        y = (1 - t)**3 * p0[1] + 3 * (1 - t)**2 * t * p1[1] + 3 * (1 - t) * t**2 * p2[1] + t**3 * p3[1]
        points.append((int(x), int(y)))
    return points


class FrameRecorder:
    def __init__(self, controller: ComputerUseController):
        self.controller = controller
        self.frame_count = 0
        self.frames = []

    def record_frame(self, draw_cursor=True):
        shot = self.controller.take_screenshot(apply_som=False, max_dimension=1024, draw_cursor=draw_cursor)
        data = base64.b64decode(shot["base64_data"])
        frame_path = FRAME_DIR / f"frame_{self.frame_count:05d}.png"
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

    # Step 1: Launch Google Chrome on :99
    print("🌐 Step 1: Launching Google Chrome to Google Homepage...")
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

    # Launch live mirror viewer on user's host display :0 if available
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
            "-window_title", "🔴 MAS Computer Use - LIVE HUMAN MOUSE DRIVE (:99)",
            "-loglevel", "quiet"
        ], env=host_env)
        print("📺 Live viewer mirror spawned on host DISPLAY :0 (Watch the live window on your screen!)")
    except Exception as e:
        print(f"Note: Host mirror skipped: {e}")

    time.sleep(4.5)
    recorder.record_burst(count=4, interval=0.1)

    # Save Keyframe 1: Start of mouse motion
    controller.mouse_move(120, 140)
    recorder.record_frame()
    shot1 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "mouse_step1_cursor_start.webp").write_bytes(base64.b64decode(shot1["base64_data"]))
    print("📸 Saved: mouse_step1_cursor_start.webp")

    # Step 2: Smooth human bezier curve to Google Search box (700, 415)
    print("🖱️ Step 2: Gliding mouse along human bezier curve to Google Search bar...")
    curve_points = interpolate_bezier(
        (120, 140),
        (350, 180),
        (520, 360),
        (700, 415),
        steps=18
    )
    for px, py in curve_points:
        controller.mouse_move(px, py)
        recorder.record_frame()
        time.sleep(0.04)

    # Step 3: Click inside search box with click pulse indicator
    print("🎯 Step 3: Clicking search bar (with visual click pulse)...")
    controller.mouse_click(700, 415, button="left")
    recorder.record_burst(count=3, interval=0.08)
    shot2 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "mouse_step2_search_bar_clicked.webp").write_bytes(base64.b64decode(shot2["base64_data"]))
    print("📸 Saved: mouse_step2_search_bar_clicked.webp")

    # Step 4: Type query with natural human cadence
    query = "top manufacturing and logistics companies in Benoni Gauteng"
    print(f"⌨️ Step 4: Typing query with human cadence: '{query}'...")
    controller.last_action_was_click = False
    for char in query:
        controller.type_text(char, delay_ms=10.0)
        # Capture frames periodically as text appears
        if len(recorder.frames) % 4 == 0:
            recorder.record_frame()
        time.sleep(0.035)

    recorder.record_burst(count=3, interval=0.08)
    shot3 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "mouse_step3_query_typed.webp").write_bytes(base64.b64decode(shot3["base64_data"]))
    print("📸 Saved: mouse_step3_query_typed.webp")

    # Step 5: Press Return and wait for results
    print("⏎ Step 5: Submitting search and waiting for results to render...")
    controller.key_combination(["Return"])
    time.sleep(3.5)
    recorder.record_burst(count=4, interval=0.1)
    shot4 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "mouse_step4_search_results.webp").write_bytes(base64.b64decode(shot4["base64_data"]))
    print("📸 Saved: mouse_step4_search_results.webp")

    # Step 6: Scroll down like a human reading
    print("📜 Step 6: Scrolling down search results...")
    for _ in range(4):
        controller.mouse_scroll(clicks=2, direction="down")
        recorder.record_frame()
        time.sleep(0.2)
    recorder.record_burst(count=3, interval=0.1)

    # Step 7: Navigate to Google Maps Benoni
    print("🗺️ Step 7: Navigating to Google Maps for Benoni commercial directory...")
    maps_url = "https://www.google.com/maps/search/businesses+in+Benoni+Gauteng"
    controller.key_combination(["ctrl", "l"])
    time.sleep(0.3)
    controller.type_text(maps_url, delay_ms=10.0)
    time.sleep(0.2)
    controller.key_combination(["Return"])
    time.sleep(5.0)
    recorder.record_burst(count=4, interval=0.1)

    # Step 8: Glide mouse into left business directory drawer
    print("📍 Step 8: Gliding cursor into Google Maps business results pane...")
    drawer_curve = interpolate_bezier(
        (700, 415),
        (550, 320),
        (380, 390),
        (260, 420),
        steps=12
    )
    for px, py in drawer_curve:
        controller.mouse_move(px, py)
        recorder.record_frame()
        time.sleep(0.04)

    controller.mouse_click(260, 420)
    recorder.record_burst(count=2, interval=0.08)

    # Scroll through the business cards
    print("📜 Step 9: Scrolling through business listings in drawer...")
    for _ in range(4):
        controller.mouse_scroll(clicks=2, direction="down")
        recorder.record_frame()
        time.sleep(0.25)
    recorder.record_burst(count=3, interval=0.1)

    shot5 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "mouse_step5_maps_drawer_scrolled.webp").write_bytes(base64.b64decode(shot5["base64_data"]))
    print("📸 Saved: mouse_step5_maps_drawer_scrolled.webp")

    # Step 10: Click on a specific business card to inspect profile
    print("🔍 Step 10: Clicking on a business card to open its profile...")
    controller.mouse_move(240, 350)
    recorder.record_frame()
    controller.mouse_click(240, 350)
    recorder.record_burst(count=4, interval=0.1)
    time.sleep(2.5)
    recorder.record_burst(count=5, interval=0.1)

    shot6 = controller.take_screenshot(apply_som=False, max_dimension=1280)
    (ARTIFACT_DIR / "mouse_step6_business_profile_opened.webp").write_bytes(base64.b64decode(shot6["base64_data"]))
    print("📸 Saved: mouse_step6_business_profile_opened.webp")

    # Clean up browser and live viewer
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

    # Step 11: Compile animated recordings (MP4, animated WebP, and GIF)
    print(f"\n🎬 Step 11: Compiling {recorder.frame_count} frames into animated recordings...")
    mp4_path = ARTIFACT_DIR / "mas_live_mouse_recording.mp4"
    webp_path = ARTIFACT_DIR / "mas_live_mouse_recording.webp"
    gif_path = ARTIFACT_DIR / "mas_live_mouse_recording.gif"

    # Encode MP4
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", "12",
        "-i", str(FRAME_DIR / "frame_%05d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        str(mp4_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✨ Compiled MP4: {mp4_path.name} ({mp4_path.stat().st_size // 1024} KB)")

    # Encode animated WebP
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", "10",
        "-i", str(FRAME_DIR / "frame_%05d.png"),
        "-vf", "scale=720:-1:flags=lanczos",
        "-vcodec", "libwebp",
        "-lossless", "0",
        "-compression_level", "4",
        "-q:v", "70",
        "-loop", "0",
        str(webp_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✨ Compiled Animated WebP: {webp_path.name} ({webp_path.stat().st_size // 1024} KB)")

    # Encode animated GIF (downscaled for fast loading)
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", "8",
        "-i", str(FRAME_DIR / "frame_%05d.png"),
        "-vf", "fps=8,scale=560:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        "-loop", "0",
        str(gif_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"✨ Compiled Animated GIF: {gif_path.name} ({gif_path.stat().st_size // 1024} KB)")

    # Clean up temp frames
    for f in FRAME_DIR.glob("frame_*.png"):
        f.unlink()

    print("🎉 All recordings and visual artifacts generated successfully!")


if __name__ == "__main__":
    run()
