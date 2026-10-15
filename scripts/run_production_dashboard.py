#!/usr/bin/env python3
"""
scripts/run_production_dashboard.py: Production Observability & Scrum Delivery Board Server.
Serves MAS Core, Scrum Board Automation, and Platinum Lodge PM boards.

Endpoints:
  - http://localhost:8080/scrum                (Direct visual Scrum board)
  - http://localhost:8080/portal/scrum.html    (Mission Control delivery board)
  - http://localhost:8080/portal/index.html    (Native portal with PM view)
  - http://localhost:8080/                     (Executive observability dashboard)
  - http://localhost:8080/api/pm/projects      (Registered projects JSON)
  - http://localhost:8080/api/pm/board/MAS     (MAS board state - 72 tickets)
  - http://localhost:8080/api/pm/board/SBA     (SBA board state - 21 tickets)
"""

import os
import signal
import sys
from pathlib import Path

# Set repository root in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from mas.dashboard.server import DashboardServer
from mas.organization.company import ConsultingEnterprise
from mas.pm.discovery import get_project_discovery


def main():
    host = os.environ.get("MAS_DASHBOARD_HOST", "0.0.0.0")
    port = int(os.environ.get("MAS_DASHBOARD_PORT", "8080"))

    print("=" * 70)
    print("🦁 ACINONYX PRODUCTION DASHBOARD & SCRUM DELIVERY BOARD")
    print("=" * 70)

    # 1. Initialize enterprise & discovery
    enterprise = ConsultingEnterprise()
    try:
        discovery = get_project_discovery()
        disc_res = discovery.sync()
        print(f"📁 Project Discovery: {disc_res.get('total_registered', 0)} projects registered")
        discovery.start_discovery_daemon(interval_seconds=30)
    except Exception as exc:
        print(f"⚠️  Project Discovery Notice: {exc}")

    # 2. Initialize DashboardServer
    server = DashboardServer(
        enterprise=enterprise,
        host=host,
        port=port,
        allowed_origins=[
            "http://localhost:8080",
            "http://127.0.0.1:8080",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
    )

    print(f"\n🚀 SERVER IS LIVE ON PORT {port}:")
    print(f"  👉 Scrum Board (Direct):          http://localhost:{port}/scrum")
    print(f"  👉 Mission Control Delivery:     http://localhost:{port}/portal/scrum.html")
    print(f"  👉 Portal Cockpit View:          http://localhost:{port}/portal/index.html")
    print(f"  👉 Observability Dashboard:      http://localhost:{port}/")
    print(f"  👉 REST: Projects List:          http://localhost:{port}/api/pm/projects")
    print(f"  👉 REST: MAS Core Board (72):    http://localhost:{port}/api/pm/board/MAS")
    print(f"  👉 REST: SBA Board (21):         http://localhost:{port}/api/pm/board/SBA")
    print("\nPress Ctrl+C to terminate.")
    print("=" * 70)

    # 3. Graceful shutdown handler
    def handle_signal(sig, frame):
        print("\n[+] Graceful shutdown signal received...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        handle_signal(None, None)


if __name__ == "__main__":
    main()
