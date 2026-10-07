#!/usr/bin/env python3
import tkinter as tk
import json
from pathlib import Path

state_file = Path(r"/home/acinonyx/Desktop/MAS/workspace/computer_use_research/2026-10-07/EVIDENCE/tkinter_app_state.json")

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
        self.label.config(text=f"Counter: {self.counter}")
        self.status.config(text=f"Button Clicked (Count: {self.counter})")
        self.save_state("button_clicked")

    def on_enter(self, event):
        self.text_content = self.entry.get()
        self.status.config(text=f"Received Text: '{self.text_content}'")
        self.save_state("text_submitted")

    def save_state(self, action):
        data = {
            "action": action,
            "counter": self.counter,
            "text_content": self.text_content,
            "entry_current": self.entry.get(),
            "timestamp": time.time(),
        }
        state_file.write_text(json.dumps(data, indent=2))

if __name__ == "__main__":
    import time
    root = tk.Tk()
    root.configure(bg="#0d1117")
    app = TestApp(root)
    root.mainloop()
