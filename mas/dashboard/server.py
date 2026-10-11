"""
mas.dashboard.server: High-performance, zero-dependency HTTP Observability Server for MAS-Core.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
import json
import os
import threading
import sqlite3
from dataclasses import asdict
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, List, Optional
from pathlib import Path
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
    session_manager: Any = None

    def log_message(self, format, *args):
        # Silence default request console spam for a clean operational terminal
        pass

    def _is_authenticated(self) -> bool:
        """Verify request bearer token against configured dashboard auth token."""
        if not self.auth_token:
            return False
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            import hmac
            return hmac.compare_digest(token, self.auth_token)
        return False

    def _validate_origin(self) -> bool:
        """
        Validates Origin or Referer header against allowed_origins and loopback addresses.
        Returns True if valid or if neither header is provided (non-browser requests).
        Returns False if Origin or Referer is untrusted.
        """
        origin = self.headers.get("Origin")
        if not origin:
            referer = self.headers.get("Referer")
            if referer:
                parsed = urlparse(referer)
                origin = f"{parsed.scheme}://{parsed.netloc}"
        if not origin:
            return True
        if origin == "null":
            return False
        # Check loopback
        if (
            origin.startswith("http://127.0.0.1:")
            or origin == "http://127.0.0.1"
            or origin.startswith("http://localhost:")
            or origin == "http://localhost"
            or origin.startswith("http://[::1]:")
            or origin == "http://[::1]"
        ):
            return True
        # Check allowed_origins
        if origin in self.allowed_origins:
            return True
        return False

    def _resolve_session_or_auth(self):
        """
        Resolves authentication via Bearer token or opaque cookie session.
        Enforces strict rules:
        - If Authorization: Bearer is present but invalid, immediately return UNAUTHORIZED (no silent fallback).
        - If no Authorization header, inspects mas_session cookie.
        - If mas_session cookie is valid, returns COOKIE auth mode.
        - Otherwise returns ANONYMOUS.
        Returns:
            (mode, principal, tenant_id, permitted_actions, session_data)
        """
        auth_header = self.headers.get("Authorization", "")
        if auth_header:
            if not auth_header.startswith("Bearer "):
                return ("UNAUTHORIZED", None, None, None, None)
            token = auth_header[7:].strip()
            srv = getattr(self, "server", None)
            ds = getattr(srv, "dashboard_server", None)
            iam = getattr(self, "iam", None) or getattr(srv, "iam", None) or getattr(ds, "iam", None)
            if iam:
                try:
                    identity = iam.verify_token(token)
                    return ("BEARER", f"{identity.tenant_id}:{identity.principal_id}", identity.tenant_id, list(identity.scopes), None)
                except Exception:
                    return ("UNAUTHORIZED", None, None, None, None)
            if self.auth_token:
                import hmac
                if hmac.compare_digest(token, self.auth_token):
                    return ("BEARER", getattr(self, "auth_principal", "dashboard_operator"), getattr(self, "tenant_id", "default") or "default", ["storage:read", "storage:write", "tools:execute", "issues:create", "issues:transition"], None)
                return ("UNAUTHORIZED", None, None, None, None)
            # Never accept arbitrary Bearer token when auth is unconfigured
            return ("UNAUTHORIZED", None, None, None, None)

        # No Authorization header - inspect mas_session cookie
        from mas.pm.session import extract_session_cookie, SessionManager
        session_secret = extract_session_cookie(self.headers)
        if session_secret:
            sm = getattr(self, "session_manager", None)
            if not sm:
                sm = SessionManager(iam=getattr(self, "iam", None))
            session_data = sm.get_session(session_secret)
            if session_data:
                return ("COOKIE", session_data["principal"], session_data["tenant_id"], session_data["permitted_actions"], session_data)
            return ("EXPIRED_COOKIE", None, None, None, None)

        return ("ANONYMOUS", None, None, None, None)

    def _check_csrf(self, session_data: dict) -> bool:
        from mas.pm.session import SessionManager
        csrf_header = self.headers.get("X-CSRF-Token")
        return SessionManager.verify_csrf(session_data, csrf_header)

    def _send_session_response(self, data: Any, status: int = 200, cookie_header: Optional[str] = None) -> None:
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(response_bytes)))
        if cookie_header:
            self.send_header("Set-Cookie", cookie_header)
        self._apply_cors_headers()
        self.end_headers()
        self.wfile.write(response_bytes)

    def _authenticate_pm_mutation(self):
        """Authenticates a PM mutation request. Validates CSRF for cookie sessions. Fails closed when unconfigured."""
        mode, principal, tenant_id, actions, session_data = self._resolve_session_or_auth()
        if mode == "UNAUTHORIZED":
            self._send_json({"error": "Unauthorized: invalid bearer token"}, status=401)
            return False, None, None
        elif mode == "EXPIRED_COOKIE":
            self._send_json({"error": "Unauthorized: session missing or expired"}, status=401)
            return False, None, None
        elif mode == "COOKIE":
            if not self._check_csrf(session_data):
                self._send_json({"error": "Forbidden: CSRF token missing or invalid"}, status=403)
                return False, None, None
            return True, principal, session_data
        elif mode == "BEARER":
            return True, principal, session_data
        else:
            # Anonymous / unconfigured: fail closed!
            self._send_json({"error": "Unauthorized: authentication required"}, status=401)
            return False, None, None

    def _apply_cors_headers(self) -> None:
        """Apply restricted CORS headers, denying permissive wildcards."""
        origin = self.headers.get("Origin")
        if origin and origin != "null":
            if (
                origin.startswith("http://127.0.0.1:")
                or origin == "http://127.0.0.1"
                or origin.startswith("http://localhost:")
                or origin == "http://localhost"
                or origin.startswith("http://[::1]:")
                or origin == "http://[::1]"
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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-CSRF-Token, Idempotency-Key")
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
                self._apply_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "index.html not found")
                return

        if path == "/favicon.ico":
            self.send_response(204)
            self._apply_cors_headers()
            self.end_headers()
            return


        if path in ("/scrum", "/scrum.html"):
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            candidates = [
                os.path.join(repo_root, "acinonyx_scrum.html"),
                os.path.join(repo_root, "scrum.html"),
                os.path.join(repo_root, "portal", "acinonyx_scrum.html"),
                os.path.join(repo_root, "portal", "scrum.html"),
            ]
            scrum_path = next((p for p in candidates if os.path.exists(p)), None)
            if scrum_path:
                with open(scrum_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self._apply_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "scrum.html not found")
                return

        if path.startswith("/portal/"):
            rel_file = path[len("/portal/"):].lstrip("/")
            if not rel_file:
                rel_file = "scrum.html"
            repo_root = Path(__file__).resolve().parents[2]
            portal_dir = (repo_root / "portal").resolve()
            target_file = (portal_dir / rel_file).resolve()
            if target_file.is_relative_to(portal_dir) and target_file.is_file():
                ext = target_file.suffix.lower()
                content_types = {
                    ".html": "text/html; charset=utf-8",
                    ".js": "application/javascript; charset=utf-8",
                    ".css": "text/css; charset=utf-8",
                    ".json": "application/json",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".svg": "image/svg+xml",
                    ".ico": "image/x-icon",
                }
                ctype = content_types.get(ext, "application/octet-stream")
                content = target_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self._apply_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, f"Portal file not found: {rel_file}")
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
            if type(self).cio_audit_report is None:
                cio = self.enterprise.cio
                loop = asyncio.new_event_loop()
                try:
                    report = loop.run_until_complete(cio.run_infrastructure_audit())
                    report_dict = report.to_dict()
                    report_dict["markdown"] = report.to_markdown()
                    type(self).cio_audit_report = report_dict
                finally:
                    loop.close()
            self._send_json(type(self).cio_audit_report)

        elif path == "/api/gateway":
            self._send_json({
                "connected": hasattr(self.enterprise, "llm_provider") and self.enterprise.llm_provider is not None,
                "model": getattr(self.enterprise.llm_provider, "model_name", "none") if hasattr(self.enterprise, "llm_provider") else "none",
                "endpoint": getattr(self.enterprise.llm_provider, "base_url", "none") if hasattr(self.enterprise, "llm_provider") else "none",
                "mode": "Live Model Gateway (OpenAI Compatible)",
            })

        elif path in ("/api/pm/v1/session", "/api/pm/v1/session/"):
            mode, principal, tenant_id, actions, session_data = self._resolve_session_or_auth()
            if mode == "UNAUTHORIZED":
                self._send_session_response({"error": {"message": "Invalid bearer token"}}, status=401)
                return
            elif mode == "EXPIRED_COOKIE":
                self._send_session_response({"error": {"message": "Session unavailable"}}, status=401)
                return
            elif mode == "COOKIE":
                self._send_session_response({
                    "principal": principal,
                    "tenant_id": tenant_id or getattr(self, "tenant_id", "default") or "default",
                    "permitted_actions": actions or ["storage:read", "storage:write", "tools:execute", "issues:create", "issues:transition"],
                    "csrf_token": session_data["csrf_token"],
                }, status=200)
                return
            elif mode == "BEARER":
                import hashlib
                csrf = hashlib.sha256(f"csrf:{principal}".encode()).hexdigest()
                self._send_session_response({
                    "principal": principal,
                    "tenant_id": tenant_id or getattr(self, "tenant_id", "default") or "default",
                    "permitted_actions": actions or ["storage:read", "storage:write", "tools:execute", "issues:create", "issues:transition"],
                    "csrf_token": csrf,
                }, status=200)
                return
            else:
                self._send_session_response({"error": {"message": "Session unavailable"}}, status=401)
                return

        elif path in ("/api/pm/v1/projects", "/api/pm/v1/projects/"):
            from mas.tenancy import current_binding
            from mas.pm.discovery import ProjectRegistryDiscovery, get_project_discovery
            try:
                binding = current_binding()
                if binding and hasattr(binding, "database"):
                    disc = ProjectRegistryDiscovery(db=binding.database)
                elif hasattr(self, "discovery") and self.discovery:
                    disc = self.discovery
                else:
                    disc = get_project_discovery()
                self._send_json(disc.get_projects_with_freshness())
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        elif path.startswith("/api/pm/v1/projects/") and path.endswith("/board"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 6 and parts[3] == "projects" and parts[5] == "board":
                proj_ref = parts[4]
                from mas.pm.tools import get_pm_db, pm_get_board_state
                db = self.pm_db if getattr(self, "tenant_id", None) else get_pm_db()
                proj = db.get_project(proj_ref) or db.get_project_by_key(proj_ref)
                if not proj:
                    self._send_json({"error": {"code": "not_found", "message": f"Project '{proj_ref}' not found"}}, status=404)
                    return
                try:
                    board = pm_get_board_state(proj.key, db=db)
                    self._send_json(board)
                except Exception as e:
                    self._send_json({"error": {"code": "internal_error", "message": str(e)}}, status=500)
                return

        elif path.startswith("/api/pm/v1/projects/") and path.endswith("/plans"):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 6 and parts[3] == "projects" and parts[5] == "plans":
                proj_ref = parts[4]
                from mas.pm.tools import get_pm_db
                db = self.pm_db if getattr(self, "tenant_id", None) else get_pm_db()
                proj = db.get_project(proj_ref) or db.get_project_by_key(proj_ref)
                if not proj:
                    self._send_json({"error": {"code": "not_found", "message": f"Project '{proj_ref}' not found"}}, status=404)
                    return
                cur = db._get_connection()
                try:
                    rows = cur.execute("SELECT * FROM pm_plans WHERE project_id = ? ORDER BY revision ASC", (proj.id,)).fetchall()
                    plans = [
                        {
                            "project_id": r["project_id"],
                            "plan_id": r["plan_id"],
                            "revision": r["revision"],
                            "source_commit": r["source_commit"],
                            "scope_reference": r["scope_reference"],
                            "published_by": r["published_by"],
                            "tasks_count": r["tasks_count"],
                            "created_at": str(r["created_at"]),
                        }
                        for r in rows
                    ]
                    self._send_json({"project_id": proj.id, "project_key": proj.key, "plans": plans})
                finally:
                    cur.close()
                return

        elif path.startswith("/api/pm/projects"):
            from mas.pm.tools import get_pm_db
            try:
                db = get_pm_db()
                projects = db.list_projects()
                self._send_json({"projects": [p.model_dump() for p in projects]})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        elif path.startswith("/api/pm/board/"):
            project_key = path.replace("/api/pm/board/", "").strip()
            from mas.pm.tools import pm_get_board_state
            try:
                board = pm_get_board_state(project_key)
                self._send_json(board)
            except Exception as e:
                self._send_json({"error": str(e)}, status=404)

        elif path.startswith("/api/pm/issues/"):
            project_key = path.replace("/api/pm/issues/", "").strip()
            from mas.pm.tools import pm_list_issues
            try:
                issues = pm_list_issues(project_key)
                self._send_json(issues)
            except Exception as e:
                self._send_json({"error": str(e)}, status=404)

        elif path.startswith("/api/pm/sprints/"):
            project_key = path.replace("/api/pm/sprints/", "").strip()
            from mas.pm.tools import get_pm_db
            try:
                db = get_pm_db()
                proj = db.get_project_by_key(project_key)
                if not proj:
                    self._send_json({"error": f"Project '{project_key}' not found"}, status=404)
                else:
                    sprints = db.list_sprints(proj.id)
                    self._send_json({"sprints": [s.model_dump() for s in sprints]})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        elif path == "/api/pm/advisor/summary":
            from mas.pm.tools import get_pm_db, pm_get_board_state
            try:
                db = get_pm_db()
                projects = db.list_projects()
                summary_data = []
                for p in projects:
                    board = pm_get_board_state(p.key)
                    summary_data.append({
                        "project_key": p.key,
                        "project_name": p.name,
                        "flow_health": board.get("flow_health"),
                        "total_active_wip": board.get("total_active_wip"),
                        "wip_saturation_pct": board.get("wip_saturation_pct"),
                        "active_sprint_id": board.get("active_sprint_id"),
                        "columns": {k: v.get("count") for k, v in board.get("columns", {}).items()},
                    })
                self._send_json({"projects": summary_data})
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        # Static Portal Serving (/portal or /portal/*)
        elif path == "/portal" or path.startswith("/portal/"):
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            portal_dir = os.path.join(repo_root, "portal")
            subpath = path[len("/portal"):].lstrip("/")
            if not subpath or subpath == "index.html":
                target_file = os.path.join(portal_dir, "index.html")
            else:
                target_file = os.path.join(portal_dir, subpath)

            target_file = os.path.abspath(target_file)
            if not target_file.startswith(portal_dir) or not os.path.exists(target_file) or os.path.isdir(target_file):
                self.send_error(404, "Portal resource not found")
                return

            ext = os.path.splitext(target_file)[1].lower()
            mime_types = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css; charset=utf-8",
                ".js": "application/javascript; charset=utf-8",
                ".json": "application/json; charset=utf-8",
                ".svg": "image/svg+xml",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".ico": "image/x-icon",
            }
            content_type = mime_types.get(ext, "application/octet-stream")
            with open(target_file, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self._apply_cors_headers()
            self.end_headers()
            self.wfile.write(content)
            return

        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        if not self._validate_origin():
            self._send_json({"error": "Forbidden: Untrusted origin"}, status=403)
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/api/engage", "/api/cio-audit/refresh", "/api/dispatch"):
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
                type(self).latest_artifacts = artifacts
                self._send_json({
                    "success": True,
                    "client_name": client_name,
                    "newly_hired": artifacts.newly_hired_agents,
                })
            finally:
                loop.close()

        elif path == "/api/cio-audit/refresh":
            type(self).cio_audit_report = None
            cio = self.enterprise.cio
            loop = asyncio.new_event_loop()
            try:
                report = loop.run_until_complete(cio.run_infrastructure_audit())
                report_dict = report.to_dict()
                report_dict["markdown"] = report.to_markdown()
                type(self).cio_audit_report = report_dict
            finally:
                loop.close()
            self._send_json({"success": True, "timestamp": type(self).cio_audit_report["audit_timestamp"]})

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

        # --- Session Endpoints (SBA-05) ---

        elif path in ("/api/pm/v1/session/login", "/api/pm/v1/auth/login"):
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            token = payload.get("token") or payload.get("bearer_token")
            iam = getattr(self, "iam", None)
            iam_token = None
            if iam:
                if not token:
                    self._send_session_response({"error": "IAM token required for login"}, status=401)
                    return
                try:
                    identity = iam.verify_token(token)
                    verified_principal = f"{identity.tenant_id}:{identity.principal_id}"
                    verified_tenant = identity.tenant_id
                    claimed_principal = payload.get("principal")
                    claimed_tenant = payload.get("tenant_id")
                    if claimed_principal and claimed_principal != verified_principal and claimed_principal != identity.principal_id:
                        self._send_session_response({"error": "Forbidden: claimed principal does not match IAM credential"}, status=403)
                        return
                    if claimed_tenant and claimed_tenant != verified_tenant:
                        self._send_session_response({"error": "Forbidden: claimed tenant does not match IAM credential"}, status=403)
                        return
                    principal = verified_principal
                    tenant_id = verified_tenant
                    iam_token = token
                except Exception as exc:
                    self._send_session_response({"error": f"Invalid IAM token: {exc}"}, status=401)
                    return
            elif self.auth_token:
                import hmac
                if not token or not hmac.compare_digest(token, self.auth_token):
                    self._send_session_response({"error": "Invalid auth token"}, status=401)
                    return
                expected_principal = getattr(self, "auth_principal", "dashboard_operator")
                expected_tenant = getattr(self, "tenant_id", "default") or "default"
                claimed_principal = payload.get("principal")
                claimed_tenant = payload.get("tenant_id")
                if claimed_principal and claimed_principal != expected_principal:
                    self._send_session_response({"error": "Forbidden: client cannot select principal"}, status=403)
                    return
                if claimed_tenant and claimed_tenant != expected_tenant:
                    self._send_session_response({"error": "Forbidden: client cannot select tenant"}, status=403)
                    return
                principal = expected_principal
                tenant_id = expected_tenant
            else:
                self._send_session_response({"error": "Authentication unconfigured on server"}, status=401)
                return

            from mas.pm.session import SessionManager, make_session_cookie
            sm = getattr(self, "session_manager", None)
            if not sm:
                sm = SessionManager(iam=iam)
            session_secret, session_meta = sm.create_session(
                principal=principal,
                tenant_id=tenant_id,
                iam_token=iam_token,
                context=identity if iam else None,
            )
            host = self.headers.get("Host", self.server.server_address[0])
            cookie_header = make_session_cookie(session_secret, host=host, headers=self.headers)
            self._send_session_response({
                "success": True,
                "principal": session_meta["principal"],
                "tenant_id": session_meta["tenant_id"],
                "permitted_actions": session_meta["permitted_actions"],
                "csrf_token": session_meta["csrf_token"],
            }, status=200, cookie_header=cookie_header)
            return

        elif path in ("/api/pm/v1/session/logout", "/api/pm/v1/auth/logout"):
            mode, principal, tenant_id, actions, session_data = self._resolve_session_or_auth()
            if mode in ("UNAUTHORIZED", "ANONYMOUS", "EXPIRED_COOKIE"):
                self._send_session_response({"error": "Unauthorized: authentication required for logout"}, status=401)
                return
            if mode == "COOKIE":
                if not self._check_csrf(session_data):
                    self._send_session_response({"error": "Forbidden: CSRF token missing or invalid"}, status=403)
                    return

            from mas.pm.session import extract_session_cookie, make_clear_session_cookie, SessionManager
            session_secret = extract_session_cookie(self.headers)
            sm = getattr(self, "session_manager", None)
            if sm and session_secret:
                sm.revoke_session(session_secret)
            host = self.headers.get("Host", self.server.server_address[0])
            clear_cookie = make_clear_session_cookie(host=host, headers=self.headers)
            self._send_session_response({"success": True}, status=200, cookie_header=clear_cookie)
            return

        # --- PM Board Endpoints ---

        elif path == "/api/pm/transition":
            ok, actor, session_data = self._authenticate_pm_mutation()
            if not ok:
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            issue_key = payload.get("issue_key")
            target_state = payload.get("target_state")
            caller_principal = actor
            if "caller_principal" in payload and payload["caller_principal"] != caller_principal:
                self._send_json({"error": "Caller identity must match authenticated dashboard principal"}, status=403)
                return
            reason = payload.get("reason", "")

            if not issue_key or not target_state:
                self._send_json({"error": "Missing issue_key or target_state"}, status=400)
                return

            from mas.pm.tools import pm_transition_issue
            try:
                from mas.security import ExecutionContext
                with ExecutionContext.scope(caller_principal):
                    result = pm_transition_issue(
                        issue_key=issue_key,
                        target_state=target_state,
                        caller_principal=caller_principal,
                        reason=reason,
                    )
                self._send_json({"success": True, "result": result})
            except Exception as e:
                self._send_json({
                    "success": False,
                    "error": e.__class__.__name__,
                    "message": str(e),
                    "issue_key": issue_key,
                    "target_state": target_state,
                }, status=400)

        elif path == "/api/pm/verdicts":
            ok, actor, session_data = self._authenticate_pm_mutation()
            if not ok:
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            issue_key = payload.get("issue_key")
            verdict = payload.get("verdict")
            reviewer_principal = actor
            if "reviewer_principal" in payload and payload["reviewer_principal"] != reviewer_principal:
                self._send_json({"error": "Reviewer identity must match authenticated dashboard principal"}, status=403)
                return
            findings = payload.get("findings", {})
            commit_sha = payload.get("commit_sha")

            if not issue_key or not verdict or not reviewer_principal:
                self._send_json({"error": "Missing issue_key, verdict, or reviewer_principal"}, status=400)
                return

            from mas.security import ExecutionContext
            from mas.pm.tools import pm_record_verdict
            try:
                with ExecutionContext.scope(reviewer_principal):
                    result = pm_record_verdict(
                        issue_key=issue_key,
                        verdict=verdict,
                        findings=findings,
                        commit_sha=commit_sha,
                    )
                self._send_json({"success": True, "result": result})
            except Exception as e:
                self._send_json({
                    "success": False,
                    "error": e.__class__.__name__,
                    "message": str(e),
                }, status=403)

        elif path == "/api/pm/issues/create":
            ok, actor, session_data = self._authenticate_pm_mutation()
            if not ok:
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            project_key = payload.get("project_key", "MAS")
            title = payload.get("title", "")
            description = payload.get("description", "")
            issue_type = payload.get("issue_type", "TASK")
            priority = payload.get("priority", "MEDIUM")
            sprint_id = payload.get("sprint_id")
            assignee_principal = payload.get("assignee_principal")
            appetite_tokens = int(payload.get("appetite_tokens", 50000))
            path_whitelist = payload.get("path_whitelist", ["*"])

            if not title:
                self._send_json({"error": "Issue title is required"}, status=400)
                return

            from mas.security import ExecutionContext
            from mas.pm.tools import pm_create_issue
            try:
                with ExecutionContext.scope(actor):
                    result = pm_create_issue(
                        project_key=project_key,
                        title=title,
                        description=description,
                        issue_type=issue_type,
                        priority=priority,
                        sprint_id=sprint_id,
                        assignee_principal=assignee_principal,
                        appetite_tokens=appetite_tokens,
                        path_whitelist=path_whitelist,
                    )
                self._send_json({"success": True, "result": result})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)

        elif path == "/api/pm/sprints/create":
            ok, actor, session_data = self._authenticate_pm_mutation()
            if not ok:
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            import uuid
            from mas.pm.models import Sprint, SprintState
            from mas.pm.tools import get_pm_db

            project_key = payload.get("project_key", "MAS")
            name = payload.get("name")
            goal = payload.get("goal", "")
            state = payload.get("state", "FUTURE")

            if not name:
                self._send_json({"error": "Sprint name is required"}, status=400)
                return

            db = get_pm_db()
            proj = db.get_project_by_key(project_key)
            if not proj:
                self._send_json({"error": f"Project '{project_key}' not found"}, status=404)
                return

            sprint = Sprint(
                id=str(uuid.uuid4()),
                project_id=proj.id,
                name=name,
                goal=goal,
                state=SprintState(state),
                start_date=payload.get("start_date"),
                end_date=payload.get("end_date"),
            )
            saved = db.create_sprint(sprint)
            self._send_json({"success": True, "sprint": saved.model_dump()})

        elif path == "/api/pm/sprints/state":
            ok, actor, session_data = self._authenticate_pm_mutation()
            if not ok:
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            sprint_id = payload.get("sprint_id")
            state = payload.get("state")
            if not sprint_id or not state:
                self._send_json({"error": "Missing sprint_id or state"}, status=400)
                return

            from mas.pm.models import SprintState
            from mas.pm.tools import get_pm_db
            db = get_pm_db()
            db.update_sprint_state(sprint_id, SprintState(state))
            self._send_json({"success": True, "sprint_id": sprint_id, "state": state})

        elif path == "/api/pm/issues/assign_sprint":
            ok, actor, session_data = self._authenticate_pm_mutation()
            if not ok:
                return

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            payload = json.loads(body.decode("utf-8")) if body else {}

            issue_key_or_id = payload.get("issue_key") or payload.get("issue_id")
            sprint_id = payload.get("sprint_id")

            from mas.pm.tools import get_pm_db
            db = get_pm_db()
            issue = db.get_issue(issue_key_or_id)
            if not issue:
                self._send_json({"error": f"Issue '{issue_key_or_id}' not found"}, status=404)
                return

            db.assign_issue_to_sprint(issue.id, sprint_id)
            self._send_json({"success": True, "issue_key": issue.key, "sprint_id": sprint_id})

        elif path.startswith("/api/pm/v1/projects/") and path.endswith("/plans"):
            ok, actor, session_data = self._authenticate_pm_mutation()
            if not ok:
                return

            parts = [p for p in path.split("/") if p]
            if len(parts) != 6 or parts[3] != "projects" or parts[5] != "plans":
                self._send_json({"error": {"code": "not_found", "message": "Invalid endpoint path"}}, status=404)
                return
            project_id_or_key = parts[4]

            idempotency_key = self.headers.get("Idempotency-Key")

            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 1_048_576:
                self._send_json({"error": {"code": "payload_too_large", "message": "Plan payload exceeds 1 MiB limit", "retryable": False}}, status=413)
                return

            body = self.rfile.read(content_length)
            if not body:
                self._send_json({"error": {"code": "malformed", "message": "Empty request body", "retryable": False}}, status=400)
                return

            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception as e:
                self._send_json({"error": {"code": "malformed", "message": f"Malformed JSON: {e}", "retryable": False}}, status=400)
                return

            if not isinstance(payload, dict):
                self._send_json({"error": {"code": "malformed", "message": "Expected JSON object for plan publication", "retryable": False}}, status=400)
                return

            from mas.pm.models import PlanPublicationRequest
            from mas.pm.plans import (
                PlanPublisherService,
                PlanValidationError,
                IdempotencyConflictError,
                StaleRevisionError,
                RevisionMismatchError,
                ProjectNotFoundError,
            )
            from mas.pm.tools import get_pm_db

            try:
                plan_req = PlanPublicationRequest(**payload)
            except Exception as e:
                self._send_json({"error": {"code": "malformed", "message": str(e), "retryable": False}}, status=400)
                return

            db = self.pm_db if getattr(self, "tenant_id", None) else get_pm_db()
            publisher = PlanPublisherService(db)
            mode, principal, auth_tenant_id, actions, session_data = self._resolve_session_or_auth()
            tenant_id = auth_tenant_id or getattr(self, "tenant_id", None) or "default"

            # Enforce authenticated planning/architect authority
            # Planning publication requires verified planning permission:
            # - Roles: {"architect", "data_architect", "chief_architect", "tenant_admin"}
            # - Scopes: {"pm:plan:publish", "admin:*"}
            PLANNING_ROLES = {"architect", "data_architect", "chief_architect", "tenant_admin"}
            PLANNING_ACTIONS = {"pm:plan:publish", "admin:*"}

            user_roles = set()
            user_scopes = set()
            srv = getattr(self, "server", None)
            ds = getattr(srv, "dashboard_server", None)
            iam_inst = getattr(self, "iam", None) or getattr(srv, "iam", None) or getattr(ds, "iam", None)
            if session_data and session_data.get("tenant_context"):
                ctx = session_data["tenant_context"]
                user_roles = set(getattr(ctx, "roles", set()))
                user_scopes = set(getattr(ctx, "scopes", set()))
            elif mode == "BEARER" and iam_inst:
                auth_hdr = self.headers.get("Authorization", "")
                if auth_hdr.startswith("Bearer "):
                    try:
                        ctx = iam_inst.verify_token(auth_hdr[7:].strip())
                        user_roles = set(getattr(ctx, "roles", set()))
                        user_scopes = set(getattr(ctx, "scopes", set()))
                    except Exception:
                        pass
            elif mode == "BEARER" and self.auth_token and not iam_inst:
                # Standalone single-tenant dashboard running with static admin bearer token
                # Authorize if actions include planning action or caller role is configured
                srv_role = getattr(self, "auth_role", None) or getattr(srv, "auth_role", None)
                if srv_role in PLANNING_ROLES:
                    user_roles.add(srv_role)
                # Allow configured admin/planner server bearer token by checking explicit permission
                configured_scopes = getattr(self, "auth_scopes", None) or getattr(srv, "auth_scopes", None)
                if configured_scopes:
                    user_scopes.update(configured_scopes)
                elif getattr(self, "allow_admin_token_planning", False):
                    # Explicitly configured administrative server token grants planning authority
                    user_scopes.add("pm:plan:publish")

            has_role_authority = bool(user_roles & PLANNING_ROLES)
            has_action_authority = bool(set(actions or []) & PLANNING_ACTIONS) or bool(user_scopes & PLANNING_ACTIONS)

            if not (has_role_authority or has_action_authority):
                self._send_json({
                    "error": {
                        "code": "forbidden",
                        "message": f"Principal '{actor}' lacks planning authority (requires architect/tenant_admin role or pm:plan:publish scope).",
                        "retryable": False,
                    }
                }, status=403)
                return

            try:
                status_code, resp = publisher.publish_plan(
                    project_id_or_key=project_id_or_key,
                    request=plan_req,
                    actor=actor,
                    tenant_id=tenant_id,
                    idempotency_key=idempotency_key,
                )
                self._send_json(resp.model_dump(), status=status_code)
            except IdempotencyConflictError as e:
                self._send_json({"error": {"code": e.code, "message": str(e), "retryable": False}}, status=409)
            except (StaleRevisionError, RevisionMismatchError) as e:
                self._send_json({"error": {"code": e.code, "message": str(e), "retryable": False}}, status=409)
            except PlanValidationError as e:
                self._send_json({"error": {"code": e.code, "message": str(e), "retryable": False, "details": e.details}}, status=400)
            except ProjectNotFoundError as e:
                self._send_json({"error": {"code": e.code, "message": str(e), "retryable": False}}, status=404)
            except PermissionError as e:
                self._send_json({"error": {"code": "unauthorized", "message": str(e), "retryable": False}}, status=403)
            except Exception as e:
                self._send_json({"error": {"code": "internal_error", "message": str(e), "retryable": False}}, status=500)

        elif path.startswith("/api/pm/v1/projects/") and "/issues/" in path and path.endswith("/reconcile"):
            ok, actor, session_data = self._authenticate_pm_mutation()
            if not ok:
                return

            parts = [p for p in path.split("/") if p]
            # /api/pm/v1/projects/{key}/issues/{issue_key}/reconcile -> 8 parts: ['api', 'pm', 'v1', 'projects', '{key}', 'issues', '{issue_key}', 'reconcile']
            if len(parts) != 8 or parts[3] != "projects" or parts[5] != "issues" or parts[7] != "reconcile":
                self._send_json({"error": {"code": "not_found", "message": "Invalid endpoint path"}}, status=404)
                return
            project_id_or_key = parts[4]
            issue_key_or_id = parts[6]

            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                payload = json.loads(body.decode("utf-8")) if body else {}
            except Exception as e:
                self._send_json({"error": {"code": "malformed", "message": f"Malformed JSON: {e}"}}, status=400)
                return

            from mas.pm.models import PlanReconciliationRequest
            from mas.pm.plans import PlanPublisherService, PlanValidationError, ProjectNotFoundError, StaleProposalError
            from mas.pm.tools import get_pm_db

            try:
                recon_req = PlanReconciliationRequest(**payload)
            except Exception as e:
                self._send_json({"error": {"code": "bad_request", "message": f"Invalid reconciliation request: {e}"}}, status=400)
                return

            decision = recon_req.decision
            expected_proposal_id = recon_req.expected_proposal_id
            expected_proposal_rev = recon_req.expected_proposal_rev
            expected_base_policy_version = recon_req.expected_base_policy_version
            db = self.pm_db if getattr(self, "tenant_id", None) else get_pm_db()
            publisher = PlanPublisherService(db)

            # Check planning authority
            PLANNING_ROLES = {"architect", "data_architect", "chief_architect", "tenant_admin"}
            PLANNING_ACTIONS = {"pm:plan:publish", "admin:*"}
            mode, principal, auth_tenant_id, actions, session_data = self._resolve_session_or_auth()
            user_roles = set()
            user_scopes = set()
            srv = getattr(self, "server", None)
            ds = getattr(srv, "dashboard_server", None)
            iam_inst = getattr(self, "iam", None) or getattr(srv, "iam", None) or getattr(ds, "iam", None)
            if session_data and session_data.get("tenant_context"):
                ctx = session_data["tenant_context"]
                user_roles = set(getattr(ctx, "roles", set()))
                user_scopes = set(getattr(ctx, "scopes", set()))
            elif mode == "BEARER" and iam_inst:
                auth_hdr = self.headers.get("Authorization", "")
                if auth_hdr.startswith("Bearer "):
                    try:
                        ctx = iam_inst.verify_token(auth_hdr[7:].strip())
                        user_roles = set(getattr(ctx, "roles", set()))
                        user_scopes = set(getattr(ctx, "scopes", set()))
                    except Exception:
                        pass
            elif mode == "BEARER" and self.auth_token and not iam_inst:
                srv_role = getattr(self, "auth_role", None) or getattr(srv, "auth_role", None)
                if srv_role in PLANNING_ROLES:
                    user_roles.add(srv_role)
                configured_scopes = getattr(self, "auth_scopes", None) or getattr(srv, "auth_scopes", None)
                if configured_scopes:
                    user_scopes.update(configured_scopes)
                elif getattr(self, "allow_admin_token_planning", False):
                    user_scopes.add("pm:plan:publish")

            has_role_authority = bool(user_roles & PLANNING_ROLES)
            has_action_authority = bool(set(actions or []) & PLANNING_ACTIONS) or bool(user_scopes & PLANNING_ACTIONS)
            if not (has_role_authority or has_action_authority):
                self._send_json({"error": {"code": "forbidden", "message": "Planning authority required to reconcile staged changes"}}, status=403)
                return

            try:
                updated_issue = publisher.reconcile_staged_changes(
                    project_id_or_key=project_id_or_key,
                    issue_id_or_key=issue_key_or_id,
                    decision=decision,
                    actor=actor,
                    tenant_id=auth_tenant_id or getattr(self, "tenant_id", None) or "default",
                    expected_proposal_id=expected_proposal_id,
                    expected_proposal_rev=expected_proposal_rev,
                    expected_base_policy_version=expected_base_policy_version,
                )
                self._send_json({
                    "success": True,
                    "issue": {
                        "id": updated_issue.id,
                        "key": updated_issue.key,
                        "current_state": updated_issue.current_state.value,
                        "policy_version": updated_issue.policy_version,
                        "path_whitelist": updated_issue.path_whitelist,
                        "acceptance_criteria": updated_issue.acceptance_criteria,
                        "reviewer_requirement": updated_issue.reviewer_requirement,
                        "has_pending_reconciliation": updated_issue.has_pending_reconciliation,
                    }
                }, status=200)
            except StaleProposalError as e:
                self._send_json({"error": {"code": e.code, "message": str(e), "retryable": False}}, status=409)
            except ProjectNotFoundError as e:
                self._send_json({"error": {"code": "not_found", "message": str(e)}}, status=404)
            except (PlanValidationError, ValueError) as e:
                self._send_json({"error": {"code": "bad_request", "message": str(e)}}, status=400)
            except Exception as e:
                self._send_json({"error": {"code": "internal_error", "message": str(e)}}, status=500)

        else:
            self._send_json({"error": {"code": "not_found", "message": f"Endpoint not found: {path}"}}, status=404)



class TenantDashboardRequestHandler(DashboardRequestHandler):
    """Tenant-bound PM API. Shared enterprise, portal and model routes fail closed."""

    def _is_authenticated(self) -> bool:
        from mas.tenancy import current_binding
        binding = current_binding()
        return bool(binding and binding.iam is self.iam and binding.identity.tenant_id == self.tenant_id)

    def _tenant_request(self, method):
        path = urlparse(self.path).path

        # 1. Non-privileged public login page:
        if method == "GET" and path in ("/portal/login.html", "/portal/login", "/login.html"):
            repo_root = Path(__file__).resolve().parents[2]
            login_file = repo_root / "portal" / "login.html"
            if login_file.is_file():
                content = login_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self._apply_cors_headers()
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "login.html not found")
                return

        # 2. Session endpoints (unauthenticated query or login/logout):
        if method == "GET" and path in ("/api/pm/v1/session", "/api/pm/v1/session/"):
            super().do_GET()
            return
        if method == "POST" and path in ("/api/pm/v1/session/login", "/api/pm/v1/auth/login", "/api/pm/v1/session/logout", "/api/pm/v1/auth/logout"):
            super().do_POST()
            return

        from mas.tenancy import tenant_scope
        auth = self.headers.get("Authorization", "")
        token = None

        if auth:
            if not auth.startswith("Bearer "):
                self._send_json({"error": "Unauthorized: invalid bearer token"}, status=401)
                return
            token = auth[7:].strip()
            # If Bearer token is provided, do NOT fall back to cookie
        else:
            from mas.pm.session import extract_session_cookie, SessionManager
            cookie_val = extract_session_cookie(self.headers)
            if cookie_val:
                sm = getattr(self, "session_manager", None) or SessionManager(iam=self.iam)
                try:
                    sess = sm.get_session(cookie_val)
                except (OSError, sqlite3.Error):
                    self._send_json({"error": "Identity authority unavailable"}, status=503)
                    return
                if sess and sess.get("tenant_id") == self.tenant_id:
                    if method == "POST":
                        csrf_hdr = self.headers.get("X-CSRF-Token")
                        if not SessionManager.verify_csrf(sess, csrf_hdr):
                            self._send_json({"error": "Forbidden: CSRF token missing or invalid"}, status=403)
                            return
                    token = sess.get("tenant_context")
                elif sess:
                    self._send_json({"error": "Forbidden: session does not match tenant"}, status=403)
                    return
                else:
                    if path.startswith("/portal/") or path in ("/portal", "/scrum", "/scrum.html"):
                        self.send_response(302)
                        self.send_header("Location", "/portal/login.html")
                        self.end_headers()
                        return
                    self._send_json({"error": "Unauthorized: session missing or expired"}, status=401)
                    return
            else:
                if path.startswith("/portal/") or path in ("/portal", "/scrum", "/scrum.html"):
                    self.send_response(302)
                    self.send_header("Location", "/portal/login.html")
                    self.end_headers()
                    return
                self._send_json({"error": "Missing, invalid or unauthorized tenant credential"}, status=403)
                return

        if not token:
            self._send_json({"error": "Missing, invalid or unauthorized tenant credential"}, status=403)
            return

        try:
            with tenant_scope(self.iam, token, self.tenant_id, self.tenant_root) as binding:
                path = urlparse(self.path).path
                if method == "POST" and path in {"/api/identity/sessions/revoke", "/api/identity/principals/revoke-sessions"}:
                    try:
                        length = int(self.headers.get("Content-Length", "0"))
                        if not 0 <= length <= 8192:
                            raise ValueError("Invalid revocation request size")
                        body = self.rfile.read(length)
                        payload = json.loads(body) if body else {}
                        if not isinstance(payload, dict):
                            raise ValueError("Expected a JSON object")
                        if path == "/api/identity/sessions/revoke":
                            result = self.iam.revoke_session(token if isinstance(token, str) else None, payload.get("session_id", binding.identity.token_id))
                        else:
                            result = self.iam.revoke_principal_sessions(token if isinstance(token, str) else None, payload.get("user_id"))
                        self._send_json({"success": True, "result": result})
                    except (ValueError, TypeError):
                        self._send_json({"error": "Malformed revocation request"}, status=400)
                    return

                action = "storage:read" if method == "GET" else "storage:write"
                binding.require(action)

                if path.startswith("/portal/") or path in ("/portal", "/scrum", "/scrum.html"):
                    if path == "/portal/snapshot.json":
                        self._send_json({"error": "Endpoint lacks tenant isolation"}, status=403)
                        return
                    super().do_GET()
                    return

                if not path.startswith("/api/pm/"):
                    self._send_json({"error": "Endpoint lacks tenant isolation"}, status=403)
                    return
                self.auth_principal = f"{self.tenant_id}:{binding.identity.principal_id}"
                if method == "GET":
                    super().do_GET()
                else:
                    binding.require("tools:execute")
                    super().do_POST()
        except PermissionError:
            self._send_json({"error": "Missing, invalid or unauthorized tenant credential"}, status=403)
        except (OSError, sqlite3.Error):
            self._send_json({"error": "Identity authority unavailable"}, status=503)

    def do_GET(self):
        self._tenant_request("GET")

    def do_POST(self):
        if not self._validate_origin():
            self._send_json({"error": "Forbidden: Untrusted origin"}, status=403)
            return
        self._tenant_request("POST")


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
        *, iam=None, tenant_id: Optional[str] = None, tenant_root: Optional[Path] = None,
        allow_admin_token_planning: bool = False,
    ) -> None:
        if any(value is not None for value in (iam, tenant_id, tenant_root)) and not all(value is not None for value in (iam, tenant_id, tenant_root)):
            raise ValueError("Tenant dashboard requires IAM, tenant ID and storage root")
        self.enterprise = enterprise
        self.host = host
        self.port = port
        self.auth_token = auth_token or os.environ.get("MAS_DASHBOARD_TOKEN")
        self.allow_admin_token_planning = allow_admin_token_planning
        self.allowed_origins = set(allowed_origins or [])
        self.static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

        # Each server owns its credentials, enterprise, database and discovery.
        from mas.pm.session import SessionManager
        from mas.pm.db import PMDatabase
        from mas.pm.discovery import ProjectRegistryDiscovery

        if tenant_root is not None and iam is not None and tenant_id is not None:
            from mas.tenancy import resolve_tenant_database_path
            db_path = resolve_tenant_database_path(iam, tenant_id, tenant_root)
            server_db = PMDatabase(db_path)
            self.tenant_db_path = db_path
        elif tenant_root is not None:
            db_path = Path(tenant_root).resolve() / "pm.db"
            server_db = PMDatabase(db_path)
            self.tenant_db_path = db_path
        else:
            server_db = PMDatabase()
            self.tenant_db_path = server_db.db_path

        session_mgr = SessionManager(db=server_db, iam=iam)
        discovery = ProjectRegistryDiscovery(db=server_db)
        self.db = server_db
        self.server_db = server_db
        self.session_manager = session_mgr
        self.discovery = discovery

        handler = type("BoundDashboardRequestHandler", (TenantDashboardRequestHandler if iam is not None else DashboardRequestHandler,), {
            "iam": iam, "tenant_id": tenant_id,
            "tenant_root": Path(tenant_root).resolve() if tenant_root is not None else None,
            "enterprise": self.enterprise,
            "static_dir": self.static_dir,
            "initial_roster_names": set(self.enterprise.get_roster().keys()),
            "auth_token": self.auth_token,
            "auth_principal": os.environ.get("MAS_DASHBOARD_PRINCIPAL", "dashboard_operator"),
            "allow_admin_token_planning": self.allow_admin_token_planning,
            "allowed_origins": self.allowed_origins,
            "latest_artifacts": None,
            "cio_audit_report": None,
            "session_manager": session_mgr,
            "discovery": discovery,
            "pm_db": server_db,
        })

        self.server = ThreadingHTTPServer((self.host, self.port), handler)
        self.server.dashboard_server = self
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

    def stop(self) -> None:
        self.shutdown()


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

    # Sync the Git-tracked work queue to MAS-PM on startup and whenever the
    # checked-out manifest changes. No workflow transitions or dispatch occur.
    import os
    from mas.pm.git_queue import MANIFEST, sync as sync_git_queue

    def _sync_queue_once():
        try:
            result = sync_git_queue()
            if result["created"]:
                print(f"📋 MAS-PM Git queue: {len(result['created'])} issues imported")
        except Exception as exc:
            print(f"⚠️  MAS-PM Git queue sync failed: {exc}")

    _sync_queue_once()
    if os.environ.get("MAS_GIT_QUEUE_AUTOSYNC", "true").lower() not in ("0", "false", "no"):
        def _watch_git_queue():
            import time
            previous = MANIFEST.stat().st_mtime_ns if MANIFEST.exists() else None
            while True:
                time.sleep(30)
                current = MANIFEST.stat().st_mtime_ns if MANIFEST.exists() else None
                if current != previous:
                    _sync_queue_once()
                    previous = current

        threading.Thread(target=_watch_git_queue, name="mas-git-queue-sync", daemon=True).start()

    # Synchronize repository project discovery (SBA-02)
    from mas.pm.discovery import get_project_discovery
    try:
        discovery = get_project_discovery()
        disc_res = discovery.sync()
        print(f"📁 MAS-PM Project Discovery: {disc_res.get('total_registered', 0)} projects registered ({disc_res.get('status')})")
        discovery.start_discovery_daemon(interval_seconds=30)
    except Exception as exc:
        print(f"⚠️  MAS-PM Project Discovery notice: {exc}")

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
