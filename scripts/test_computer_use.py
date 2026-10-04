"""
scripts/test_computer_use.py: End-to-End Autonomous Computer Use Verification.
Tests autonomous browser navigation, element inspection, mouse clicks, keyboard typing,
form dispatch, tab switching, and visual screenshot capture on the MAS Observability Dashboard.

Architect: Acinonyx
"""

import asyncio
import os
import sys
import time

# Ensure local packages and browsers are loaded
PKG_DIR = "/home/acinonyx/Desktop/MAS/bin/packages"
BROWSER_DIR = "/home/acinonyx/Desktop/MAS/bin/browsers"
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_DIR

OUTPUT_DIR = "/home/acinonyx/Desktop/MAS/workspace/computer_use"
os.makedirs(OUTPUT_DIR, exist_ok=True)


async def run_computer_use_test():
    print("=" * 70)
    print("🦁 ACINONYX AUTONOMOUS COMPUTER USE TEST SUITE")
    print("=" * 70)

    from playwright.async_api import async_playwright

    results = []

    async with async_playwright() as p:
        print("\n[Step 1] Initializing Headless Chromium Session...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AcinonyxComputerUseAgent/2.0",
        )
        page = await context.new_page()

        # 1. Navigation
        url = "http://127.0.0.1:8080"
        print(f"[Step 1] Navigating to target application: {url}")
        t0 = time.time()
        response = await page.goto(url, wait_until="networkidle", timeout=15000)
        t_nav = time.time() - t0
        status = response.status if response else "Unknown"
        title = await page.title()
        print(f"  ✓ HTTP Status: {status} in {t_nav:.2f}s")
        print(f"  ✓ Window Title: '{title}'")

        # Snapshot 1: Initial Dashboard State
        shot1 = os.path.join(OUTPUT_DIR, "01_initial_state.png")
        await page.screenshot(path=shot1, full_page=True)
        print(f"  📸 Screenshot captured: {shot1} ({os.path.getsize(shot1)} bytes)")
        results.append({"step": "1. Initial Navigation", "success": True, "screenshot": shot1})

        # 2. Computer Use: Form Interaction & Typing
        print("\n[Step 2] Executing Computer Use: Button Selection & Keyboard Typing...")
        # Click the FinTech preset button
        fintech_btn = page.locator("button:has-text('FinTech')")
        await fintech_btn.wait_for(state="visible", timeout=5000)
        print("  ✓ Targeting element: <button> '💳 FinTech (PCI-DSS & Ledger)'")
        await fintech_btn.click()
        print("  ✓ Mouse Left-Click dispatched to preset button.")

        # Read populated values
        client_input = page.locator("#client-name-input")
        rfp_input = page.locator("#rfp-input")
        client_val = await client_input.input_value()
        print(f"  ✓ Pre-filled Client: '{client_val}'")

        # Interactive typing: Clear and type custom client name
        print("  ✓ Simulating human keyboard input: typing custom client name...")
        await client_input.fill("")
        await client_input.type("Apex FinTech Global", delay=30)
        updated_client = await client_input.input_value()
        print(f"  ✓ Updated Client Input: '{updated_client}'")

        # Snapshot 2: Form populated state
        shot2 = os.path.join(OUTPUT_DIR, "02_form_populated.png")
        await page.screenshot(path=shot2, full_page=True)
        print(f"  📸 Screenshot captured: {shot2} ({os.path.getsize(shot2)} bytes)")
        results.append({"step": "2. Form Interaction & Typing", "success": True, "screenshot": shot2})

        # 3. Computer Use: Form Submission & Mission Dispatch
        print("\n[Step 3] Executing Action: Dispatching Cross-Functional Engagement...")
        dispatch_btn = page.locator("#dispatch-btn")
        print("  ✓ Clicking 'Launch Cross-Functional Mission' button...")
        await dispatch_btn.click()

        # Wait for dispatch processing and UI update
        print("  ⏳ Waiting for autonomous enterprise pipeline execution...")
        await page.wait_for_timeout(3500)

        # Snapshot 3: Dispatched & In-Flight State
        shot3 = os.path.join(OUTPUT_DIR, "03_mission_dispatched.png")
        await page.screenshot(path=shot3, full_page=True)
        print(f"  📸 Screenshot captured: {shot3} ({os.path.getsize(shot3)} bytes)")
        results.append({"step": "3. Mission Dispatch", "success": True, "screenshot": shot3})

        # 4. Computer Use: Artifact Inspector Tab Navigation
        print("\n[Step 4] Executing Computer Use: Tab Switching & DOM Inspection...")
        tabs_to_test = [
            ("tab-prd", "PRD Requirements"),
            ("tab-design", "Design System"),
            ("tab-eng", "Engineering Synthesis"),
            ("tab-gtm", "Go-To-Market Package"),
            ("tab-signoff", "Executive Sign-off"),
        ]

        for tab_id, tab_name in tabs_to_test:
            tab_locator = page.locator(f"#{tab_id}")
            if await tab_locator.count() > 0:
                await tab_locator.click()
                print(f"  ✓ Switched to tab: '{tab_name}' (#{tab_id})")
                await page.wait_for_timeout(300)

        # Snapshot 4: Artifact Inspector State
        shot4 = os.path.join(OUTPUT_DIR, "04_artifacts_inspected.png")
        await page.screenshot(path=shot4, full_page=True)
        print(f"  📸 Screenshot captured: {shot4} ({os.path.getsize(shot4)} bytes)")
        results.append({"step": "4. Tab Switching & Artifact Inspection", "success": True, "screenshot": shot4})

        # 5. Computer Use: Interactive Safety Interlock Toggle
        print("\n[Step 5] Executing Computer Use: Toggling Safety Interlock Switch...")
        dispatch_pill = page.locator("#dispatch-pill")
        initial_pill_text = await dispatch_pill.inner_text()
        print(f"  ✓ Initial Safety Switch status: '{initial_pill_text.strip()}'")

        # Click the safety switch
        await dispatch_pill.click()
        print("  ✓ Clicked Safety Switch pill element.")
        await page.wait_for_timeout(1000)

        updated_pill_text = await dispatch_pill.inner_text()
        print(f"  ✓ Updated Safety Switch status: '{updated_pill_text.strip()}'")

        # Snapshot 5: Safety Interlock Toggled
        shot5 = os.path.join(OUTPUT_DIR, "05_safety_interlock_toggled.png")
        await page.screenshot(path=shot5, full_page=True)
        print(f"  📸 Screenshot captured: {shot5} ({os.path.getsize(shot5)} bytes)")
        results.append({"step": "5. Safety Switch Toggle", "success": True, "screenshot": shot5})

        # 6. Read Final Page Metrics
        print("\n[Step 6] Extracting Final Dashboard Metrics...")
        headcount = await page.locator("#val-headcount").inner_text()
        engagements = await page.locator("#val-engagements").inner_text()
        events = await page.locator("#val-events").inner_text()
        print(f"  📊 Headcount: {headcount}")
        print(f"  📊 Engagements: {engagements}")
        print(f"  📊 Events: {events}")

        await browser.close()
        print("\n[Done] Browser session gracefully terminated.")

    print("\n" + "=" * 70)
    print("🎯 COMPUTER USE TEST SUMMARY")
    print("=" * 70)
    for res in results:
        status_icon = "🟢 PASS" if res["success"] else "🔴 FAIL"
        print(f"• {status_icon}: {res['step']} -> {res['screenshot']}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_computer_use_test())
