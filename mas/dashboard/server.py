"""
mas.dashboard.server: High-performance, zero-dependency HTTP Observability Server for MAS-Core.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
import json
import os
import threading
from dataclasses import asdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, List, Optional
from urllib.parse import urlparse
from mas.organization.company import ConsultingEnterprise
from mas.organization.engagement import ConsultingEngagement, EngagementArtifacts


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    """
    HTTP Request Handler serving REST endpoints and the single-page dashboard.
    """

    # Static references attached by DashboardServer
    enterprise: ConsultingEnterprise = None
    latest_artifacts: Optional[EngagementArtifacts] = None
    initial_roster_names: set = set()
    static_dir: str = ""
    cio_audit_report: Optional[dict] = None  # cached after first run
    auth_token: Optional[str] = None
    allowed_origins: set = set()

    def log_message(self, format, *args):
        # Silence default request console spam for a clean operational terminal
        pass

    def _is_authenticated(self) -> bool:
        """Verify request bearer token against configured dashboard auth token."""
        if not self.auth_token:
            return True
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            import hmac
            return hmac.compare_digest(token, self.auth_token)
        return False

    def _apply_cors_headers(self) -> None:
        """Apply restricted CORS headers, denying permissive wildcards."""
        origin = self.headers.get("Origin")
        if origin:
            if (
                origin.startswith("http://127.0.0.1:")
                or origin.startswith("http://localhost:")
                or origin in self.allowed_origins
            ):
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Credentials", "true")
                self.send_header("Vary", "Origin")

    def _send_json(self, data: Any, status: int = 200) -> None:
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self._apply_cors_headers()
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self._apply_cors_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            index_path = os.path.join(self.static_dir, "index.html")
            if os.path.exists(index_path):
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "index.html not found")
                return

        # -----------------------------------------------------------------
        # REST API Endpoints
        # -----------------------------------------------------------------
        if path == "/api/status":
            stats = self.enterprise.event_bus.stats
            data = {
                "enterprise_name": self.enterprise.name,
                "status": self.enterprise.state_machine.get("company_status", "active"),
                "headcount": self.enterprise.get_headcount(),
                "total_engagements": self.enterprise.state_machine.get("total_engagements", 0),
                "total_events_published": stats.get("published_count", 0),
                "total_tokens_routed": stats.get("total_tokens_routed", 0),
                "current_client": self.enterprise.state_machine.get("current_client"),
                "live_dispatch_enabled": self.enterprise.is_live_dispatch_enabled(),
                "allowed_projects": self.enterprise.state_machine.get("allowed_projects", []),
                "checkpoints": self.enterprise.state_machine.list_checkpoints(),
            }
            self._send_json(data)

        elif path == "/api/roster":
            if not self._is_authenticated():
                self._send_json({"error": "Unauthorized: missing or invalid bearer token"}, status=401)
                return
            departments_data = {}
            for dept_type, dept in self.enterprise.departments.items():
                agents_info = []
                for ag_name, ag in dept.members.items():
                    agents_info.append({
                        "name": ag_name,
                        "role": ag.role.value,
                        "is_new": ag_name not in self.initial_roster_names,
                        "system_prompt": ag.system_prompt,
                    })
                departments_data[dept_type.value] = {
                    "headcount": dept.headcount,
                    "agents": agents_info,
                }
            self._send_json({"departments": departments_data})

        elif path == "/api/events":
            if not self._is_authenticated():
                self._send_json({"error": "Unauthorized: missing or invalid bearer token"}, status=401)
                return
            history = self.enterprise.event_bus.get_history()
            event_dicts = [m.to_dict() for m in history]
            self._send_json({"events": event_dicts})

        elif path == "/api/artifacts":
            if not self._is_authenticated():
                self._send_json({"error": "Unauthorized: missing or invalid bearer token"}, status=401)
                return
            if self.latest_artifacts:
                art = self.latest_artifacts
                art_dict = {
                    "client_name": art.client_name,
                    "client_brief": art.client_brief,
                    "job_requisitions": [asdict(r) for r in art.job_requisitions],
                    "newly_hired_agents": art.newly_hired_agents,
                    "prd": art.prd,
                    "design_system": art.design_system,
                    "specialist_audits": art.specialist_audits,
                    "engineering_summary": art.engineering_summary,
                    "gtm_package": art.gtm_package,
                    "delivery_signoff": art.delivery_signoff,
                }
                self._send_json(art_dict)
            else:
                self._send_json({})

        elif path == "/api/cio-audit":
            # Return cached report if available, otherwise run the audit now
            if DashboardRequestHandler.cio_audit_report is None:
                cio = self.enterprise.cio
                loop = asyncio.new_event_loop()
                try:
                    report = loop.run_until_complete(cio.run_infrastructure_audit())
                    report_dict = report.to_dict()
                    report_dict["markdown"] = report.to_markdown()
                    DashboardRequestHandler.cio_audit_report = report_dict
                finally:
                    loop.close()
            self._send_json(DashboardRequestHandler.cio_audit_report)

        elif path == "/api/gateway":
            self._send_json({
                "connected": hasattr(self.enterprise, "llm_provider") and self.enterprise.llm_provider is not None,
                "model": getattr(self.enterprise.llm_provider, "model_name", "none") if hasattr(self.enterprise, "llm_provider") else "none",
                "endpoint": getattr(self.enterprise.llm_provider, "base_url", "none") if hasattr(self.enterprise, "llm_provider") else "none",
                "mode": "Live Model Gateway (OpenAI Compatible)",
            })

        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if not self._is_authenticated():
            self._send_json({"error": "Unauthorized: missing or invalid bearer token"}, status=401)
            return

        if path == "/api/engage":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            client_name = payload.get("client_name", "Enterprise Client")
            rfp = payload.get("rfp", "Standard IT SaaS consulting request.")

            engagement = ConsultingEngagement(self.enterprise)

            # Run engagement in an event loop
            loop = asyncio.new_event_loop()
            try:
                artifacts = loop.run_until_complete(
                    engagement.execute_engagement(client_name=client_name, raw_rfp=rfp)
                )
                DashboardRequestHandler.latest_artifacts = artifacts
                self._send_json({
                    "success": True,
                    "client_name": client_name,
                    "newly_hired": artifacts.newly_hired_agents,
                })
            finally:
                loop.close()

        elif path == "/api/cio-audit/refresh":
            # Force a fresh infrastructure audit (clears cache)
            DashboardRequestHandler.cio_audit_report = None
            cio = self.enterprise.cio
            loop = asyncio.new_event_loop()
            try:
                report = loop.run_until_complete(cio.run_infrastructure_audit())
                report_dict = report.to_dict()
                report_dict["markdown"] = report.to_markdown()
                DashboardRequestHandler.cio_audit_report = report_dict
            finally:
                loop.close()
            self._send_json({"success": True, "timestamp": DashboardRequestHandler.cio_audit_report["audit_timestamp"]})

        elif path == "/api/dispatch":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}
            new_state = payload.get("enabled", not self.enterprise.is_live_dispatch_enabled())
            if new_state:
                self.enterprise.enable_live_dispatch()
            else:
                self.enterprise.disable_live_dispatch()
            self._send_json({
                "success": True,
                "live_dispatch_enabled": self.enterprise.is_live_dispatch_enabled(),
            })

        else:
            self.send_error(404, "Endpoint not found")


class DashboardServer:
    """
    Observability Dashboard Server running on background thread or foreground loop.
    """

    def __init__(
        self,
        enterprise: ConsultingEnterprise,
        host: str = "127.0.0.1",
        port: int = 8080,
        auth_token: Optional[str] = None,
        allowed_origins: Optional[List[str]] = None,
    ) -> None:
        self.enterprise = enterprise
        self.host = host
        self.port = port
        self.auth_token = auth_token or os.environ.get("MAS_DASHBOARD_TOKEN")
        self.allowed_origins = set(allowed_origins or [])
        self.static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

        # Configure request handler
        DashboardRequestHandler.enterprise = self.enterprise
        DashboardRequestHandler.static_dir = self.static_dir
        DashboardRequestHandler.initial_roster_names = set(self.enterprise.get_roster().keys())
        DashboardRequestHandler.auth_token = self.auth_token
        DashboardRequestHandler.allowed_origins = self.allowed_origins

        self.server = ThreadingHTTPServer((self.host, self.port), DashboardRequestHandler)
        self._thread: Optional[threading.Thread] = None

    def start_background(self) -> None:
        """Start server in an asynchronous daemon background thread."""
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def serve_forever(self) -> None:
        """Serve synchronously in current thread."""
        self.server.serve_forever()

    def shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()


def run_dashboard(
    enterprise: Optional[ConsultingEnterprise] = None,
    host: str = "127.0.0.1",
    port: int = 8080,
    gateway_port: int = 8001,
    auth_token: Optional[str] = None,
):
    """Entry point to launch the observability dashboard and live model gateway."""
    from mas.providers.gateway import ModelGatewayServer
    from mas.providers.http_provider import OpenAICompatibleProvider

    ent = enterprise or ConsultingEnterprise()

    # 1. Initialize and launch Live Model Gateway on gateway_port
    gateway = ModelGatewayServer(port=gateway_port)
    try:
        gateway.start_background()
        print(f"🧠 LIVE MODEL GATEWAY ACTIVE ON: {gateway.endpoint_url}")
    except Exception as e:
        print(f"⚠️  Live Model Gateway Notice: {e}")

    # 2. Attach OpenAICompatibleProvider to enterprise
    provider = OpenAICompatibleProvider(
        base_url=f"http://127.0.0.1:{gateway_port}/v1",
        model_name="acinonyx-core-v1",
    )
    ent.attach_llm_provider(provider)
    print("🔗 Enterprise agents connected to Live Model Gateway.")

    server = DashboardServer(ent, host=host, port=port, auth_token=auth_token)
    print(f"\n🦁 ACINONYX OBSERVABILITY DASHBOARD LIVE ON: http://127.0.0.1:{port}")
    print("Press Ctrl+C to terminate.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Dashboard Server...")
        server.shutdown()
        gateway.shutdown()
