#!/usr/bin/env python3
"""
run_native_desktop_verification.py: Outcome-verified native desktop interaction trial.
Spawns an isolated Xvfb virtual display (:98), launches a real Tkinter interactive GUI application,
dispatches synthetic mouse clicks and keyboard typing via xdotool, and asserts resulting state changes
in the application's runtime data.

CRITICAL ARCHITECTURAL CLARIFICATION:
Xvfb is a DEDICATED VIRTUAL DISPLAY (virtual X11 framebuffer). It provides display server isolation to
prevent visual interference with the host's Wayland desktop (:0). It is NOT a security boundary; it does
not isolate filesystem access, processes, or network resources.

Date: 2026-10-07
Evaluator: MAS Research & Evaluation Team
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/home/acinonyx/Desktop/MAS")
EVIDENCE_DIR = REPO_ROOT / "workspace" / "computer_use_research" / "2026-10-07" / "EVIDENCE"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(REPO_ROOT))
from mas.tools.display import VirtualDisplayConfig, VirtualDisplayManager
from mas.tools.computer_use import ComputerUseController

DISPLAY_NUM = 98
STATE_FILE = EVIDENCE_DIR / "tkinter_app_state.json"
APP_SCRIPT = EVIDENCE_DIR / "sample_desktop_app.py"

# Write the Tkinter GUI app script
APP_CODE = f"""#!/usr/bin/env python3
import tkinter as tk
import json
from pathlib import Path

state_file = Path(r"{STATE_FILE}")

class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MAS Interactive Desktop App")
        self.root.geometry("400x300+50+50")
        
        self.counter = 0
        self.text_content = ""
        
        # Use deterministic place layout
        self.label = tk.Label(root, text="Counter: 0", font=("Helvetica", 14), bg="#22272e", fg="#58a6ff")
        self.label.place(x=50, y=20, width=300, height=35)
        
        # Increment Button (center at X=200, Y=85 in window)
        self.btn = tk.Button(root, text="[ Increment Counter ]", font=("Helvetica", 12, "bold"),
                             command=self.on_click, bg="#238636", fg="#ffffff")
        self.btn.place(x=50, y=70, width=300, height=35)
        
        # Entry (center at X=200, Y=140 in window)
        self.entry = tk.Entry(root, font=("Helvetica", 12), width=25)
        self.entry.place(x=50, y=125, width=300, height=30)
        self.entry.bind("<Return>", self.on_enter)
        
        # Submit Button (center at X=200, Y=190 in window)
        self.submit_btn = tk.Button(root, text="[ Submit Text ]", font=("Helvetica", 11),
                                   command=lambda: self.on_enter(None), bg="#1f6feb", fg="#ffffff")
        self.submit_btn.place(x=50, y=175, width=300, height=30)
        
        # Status Label
        self.status = tk.Label(root, text="Awaiting Input...", font=("Helvetica", 10), fg="#8b949e", bg="#0d1117")
        self.status.place(x=50, y=225, width=300, height=30)
        
        self.save_state("initialized")

    def on_click(self):
        self.counter += 1
        self.label.config(text=f"Counter: {{self.counter}}")
        self.status.config(text=f"Button Clicked (Count: {{self.counter}})")
        self.save_state("button_clicked")

    def on_enter(self, event):
        self.text_content = self.entry.get()
        self.status.config(text=f"Received Text: '{{self.text_content}}'")
        self.save_state("text_submitted")

    def save_state(self, action):
        data = {{
            "action": action,
            "counter": self.counter,
            "text_content": self.text_content,
            "entry_current": self.entry.get(),
            "timestamp": time.time(),
        }}
        state_file.write_text(json.dumps(data, indent=2))

if __name__ == "__main__":
    import time
    root = tk.Tk()
    root.configure(bg="#0d1117")
    app = TestApp(root)
    root.mainloop()
"""
APP_SCRIPT.write_text(APP_CODE, encoding="utf-8")

def run():
    print(f"🖥️ Initializing dedicated virtual display :{DISPLAY_NUM} (Xvfb + fluxbox)...")
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        
    cfg = VirtualDisplayConfig(display_num=DISPLAY_NUM, width=1024, height=768, window_manager="fluxbox")
    disp = VirtualDisplayManager(cfg).start()
    
    if disp.is_mock:
        raise RuntimeError("Xvfb is required for native desktop test; cannot run in mock mode.")
        
    audit_path = EVIDENCE_DIR / "native_desktop_effect_audit.jsonl"
    controller = ComputerUseController(display_manager=disp, audit_log_path=str(audit_path))
    
    env = {**os.environ, "DISPLAY": f":{DISPLAY_NUM}"}
    
    # Launch Tkinter App
    print("🚀 Launching interactive Tkinter application in virtual display...")
    proc = subprocess.Popen([sys.executable, str(APP_SCRIPT)], env=env)
    
    time.sleep(1.5)  # Wait for window mapping
    
    try:
        # Find window geometry using xdotool
        win_id_out = subprocess.run(["xdotool", "search", "--name", "MAS Interactive Desktop App"],
                                    env=env, capture_output=True, text=True, check=True).stdout.strip().splitlines()
        win_id = win_id_out[-1]
        print(f"🪟 Found application Window ID: {win_id}")
        
        # Activate window
        subprocess.run(["xdotool", "windowactivate", "--sync", win_id], env=env, check=True)
        time.sleep(0.5)
        
        # 1. Action 1: Click the Increment Button
        print("🖱️ Action 1: Moving to increment button and dispatching click...")
        controller.mouse_move(250, 155)
        controller.mouse_click(1)
        time.sleep(0.5)
        
        # Read state file to assert button click outcome
        state1 = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        print(f"📊 State after click: counter={state1['counter']}, action={state1['action']}")
        assert state1["counter"] == 1, f"Expected counter=1, got {state1['counter']}"
        assert state1["action"] == "button_clicked"
        
        # 2. Action 2: Click the Entry input and type text
        print("⌨️ Action 2: Focusing text entry and typing 'Hello MAS'...")
        controller.mouse_move(250, 210)
        controller.mouse_click(1)
        time.sleep(0.3)
        
        controller.type_text("Hello MAS")
        time.sleep(0.3)
        
        # Click the Submit button to finalize text entry
        print("🖱️ Action 2b: Clicking Submit Text button...")
        controller.mouse_move(250, 260)
        controller.mouse_click(1)
        time.sleep(0.5)
        
        # Read state file to assert text input outcome
        state2 = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        print(f"📊 State after typing: text_content='{state2['text_content']}', action={state2['action']}")
        assert state2["text_content"] == "Hello MAS", f"Expected 'Hello MAS', got '{state2['text_content']}'"
        assert state2["action"] == "text_submitted"
        
        # 3. Capture screenshot of the verified GUI state
        print("📸 Action 3: Capturing outcome-verified GUI screenshot...")
        shot = controller.take_screenshot(apply_som=False)
        shot_path = EVIDENCE_DIR / "native_tkinter_outcome_verified.png"
        shot_path.write_bytes(base64.b64decode(shot["base64_data"]))
        
        outcome_record = {
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "display": f":{DISPLAY_NUM}",
            "is_mock": False,
            "window_id": win_id,
            "state_initial": {"counter": 0, "text": ""},
            "state_after_click": state1,
            "state_after_type": state2,
            "assertions": {
                "counter_incremented_to_1": True,
                "text_content_matches_input": True,
            },
            "screenshot_path": str(shot_path),
            "screenshot_bytes": shot_path.stat().st_size,
            "status": "OUTCOME-VERIFIED"
        }
        (EVIDENCE_DIR / "native_desktop_outcome_evidence.json").write_text(json.dumps(outcome_record, indent=2))
        print("✅ Native desktop interaction verified with 100% independent state confirmation!")
        
    finally:
        proc.terminate()
        proc.wait(timeout=3)
        disp.stop()
        print(f"🛑 Virtual display :{DISPLAY_NUM} shut down cleanly.")

if __name__ == "__main__":
    run()
