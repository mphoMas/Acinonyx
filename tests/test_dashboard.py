"""
Tests for mas.dashboard.server (DashboardServer and REST API endpoints).
"""

import json
import socket
import time
import unittest
import urllib.request
from mas.dashboard.server import DashboardServer
from mas.organization.company import ConsultingEnterprise


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class TestDashboardServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.port = get_free_port()
        cls.enterprise = ConsultingEnterprise(name="Test Dashboard Enterprise")
        cls.server = DashboardServer(cls.enterprise, host="127.0.0.1", port=cls.port)
        cls.server.start_background()
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        time.sleep(0.3)  # Allow thread to bind

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_get_index_html(self):
        url = f"http://127.0.0.1:{self.port}/"
        with self.opener.open(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("ACINONYX // MAS-Core Observability Dashboard", html)
            self.assertIn("Client Intake & Engagement Dispatcher", html)

    def test_api_status(self):
        url = f"http://127.0.0.1:{self.port}/api/status"
        with self.opener.open(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["enterprise_name"], "Test Dashboard Enterprise")
            self.assertGreaterEqual(data["headcount"], 7)
            self.assertEqual(data["status"], "active")

    def test_api_roster(self):
        url = f"http://127.0.0.1:{self.port}/api/roster"
        with self.opener.open(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("departments", data)
            depts = data["departments"]
            self.assertIn("human_resources", depts)
            self.assertIn("client_management", depts)
            self.assertIn("engineering", depts)

    def test_api_events(self):
        url = f"http://127.0.0.1:{self.port}/api/events"
        with self.opener.open(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("events", data)
            self.assertIsInstance(data["events"], list)

    def test_api_engage_post(self):
        url = f"http://127.0.0.1:{self.port}/api/engage"
        payload = json.dumps({
            "client_name": "Stripe Gateway Client",
            "rfp": "Payment reconciliation service requiring stripe and pci-dss compliance."
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with self.opener.open(req, timeout=10.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])
            self.assertEqual(data["client_name"], "Stripe Gateway Client")

        # Now test that /api/artifacts returns the generated deliverables
        art_url = f"http://127.0.0.1:{self.port}/api/artifacts"
        with self.opener.open(art_url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            art_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(art_data["client_name"], "Stripe Gateway Client")
            self.assertTrue(len(art_data["prd"]) > 0)

    def test_api_pm_board(self):
        from mas.pm.tools import pm_create_project, pm_create_issue
        pkey = f"DP{int(time.time()*1000) % 100000}"
        pm_create_project(key=pkey, name="Dashboard Project")
        pm_create_issue(project_key=pkey, title="Board Test Issue")

        url = f"http://127.0.0.1:{self.port}/api/pm/board/{pkey}"
        with self.opener.open(url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["project_key"], pkey)
            self.assertIn("columns", data)
            self.assertEqual(data["columns"]["BACKLOG"]["count"], 1)

        issues_url = f"http://127.0.0.1:{self.port}/api/pm/issues/{pkey}"
        with self.opener.open(issues_url, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            issues = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(len(issues), 1)
            self.assertEqual(issues[0]["title"], "Board Test Issue")


class TestDashboardSecurity(unittest.TestCase):
    """SEC-04: Test bearer token authorization and CORS policy enforcement."""

    @classmethod
    def setUpClass(cls):
        cls.port = get_free_port()
        cls.token = "mas-secure-admin-token-777"
        cls.enterprise = ConsultingEnterprise(name="Security Test Enterprise")
        cls.server = DashboardServer(
            cls.enterprise,
            host="127.0.0.1",
            port=cls.port,
            auth_token=cls.token,
        )
        cls.server.start_background()
        cls.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_unauthenticated_mutating_dispatch_denied(self):
        url = f"http://127.0.0.1:{self.port}/api/dispatch"
        payload = json.dumps({"enabled": True}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with self.opener.open(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 401)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)

    def test_authenticated_mutating_dispatch_allowed(self):
        url = f"http://127.0.0.1:{self.port}/api/dispatch"
        payload = json.dumps({"enabled": True}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with self.opener.open(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(data["success"])

    def test_unauthenticated_events_read_denied(self):
        url = f"http://127.0.0.1:{self.port}/api/events"
        req = urllib.request.Request(url)
        try:
            with self.opener.open(req, timeout=3.0) as resp:
                self.assertEqual(resp.status, 401)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 401)

    def test_authenticated_events_read_allowed(self):
        url = f"http://127.0.0.1:{self.port}/api/events"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        with self.opener.open(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("events", data)

    def test_cors_denies_untrusted_origin(self):
        url = f"http://127.0.0.1:{self.port}/api/status"
        req = urllib.request.Request(url, headers={"Origin": "http://malicious-site.example.com"})
        with self.opener.open(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIsNone(resp.headers.get("Access-Control-Allow-Origin"))


if __name__ == "__main__":
    unittest.main()

