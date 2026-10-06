#!/usr/bin/env python3
"""
scripts/launch_portal.py: High-Performance Local Dev Server for the Acinonyx Living AI Research Portal.
Serves the portal at http://localhost:8080/portal/ with direct access to research PDFs and architecture captures.

Architect: cloud_architect / MAS Swarm
"""

import http.server
import socketserver
import sys
from pathlib import Path

ROOT_DIR = Path("/home/acinonyx/Desktop/MAS")
PORT = 8080
MAX_ATTEMPTS = 10

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT_DIR), **kwargs)

    def log_message(self, format, *args):
        # Clean terminal logging
        sys.stderr.write(f"🌐 [PORTAL HTTP] {args[0]} - {args[1]}\n")

def run():
    global PORT
    for attempt in range(MAX_ATTEMPTS):
        try:
            with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
                print("=" * 70)
                print("🐆 ACINONYX LIVING AI RESEARCH PORTAL IS LIVE!")
                print("=" * 70)
                print(f"👉 Local Web Portal:  http://localhost:{PORT}/portal/")
                print(f"📁 Serving Root:      {ROOT_DIR}")
                print("📊 66 Documents • 4 Simulators • 8 Seminal PDFs • Cryptographic Merkle")
                print("=" * 70)
                print("Press Ctrl+C to terminate the local server.\n")
                httpd.serve_forever()
                break
        except OSError as e:
            if "Address already in use" in str(e):
                PORT += 1
            else:
                raise e

if __name__ == "__main__":
    run()
