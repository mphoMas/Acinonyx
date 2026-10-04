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


if __name__ == "__main__":
    unittest.main()
