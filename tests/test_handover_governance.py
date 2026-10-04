"""
tests.test_handover_governance: Verification suite for adopted security, budgeting,
and stdio MCP governance patterns from the MAS handover plan.

Architect: Acinonyx
"""

import asyncio
import os
import shutil
import tempfile
import unittest
from mas.organization.company import ConsultingEnterprise
from mas.organization.engagement import ConsultingEngagement
from mas.providers.gateway import TokenBudgetGovernor, ModelGatewayServer
from mas.tools.filesystem import fs_read_file, fs_write_file, set_allowed_roots
from mas.tools.browser_tool import web_fetch_url_tool, web_search_tool, _strip_html_tags
from scripts.mas_mcp_stdio import handle_request


class TestDispatchSafetyInterlock(unittest.IsolatedAsyncioTestCase):
    def test_default_dispatch_state_is_safe(self):
        # Fresh enterprise defaults to live_dispatch_enabled = False (safety default)
        ent = ConsultingEnterprise(enable_live_dispatch=False)
        self.assertFalse(ent.is_live_dispatch_enabled())

    def test_arming_and_disarming_dispatch(self):
        ent = ConsultingEnterprise(enable_live_dispatch=False)
        ent.enable_live_dispatch()
        self.assertTrue(ent.is_live_dispatch_enabled())
        ent.disable_live_dispatch()
        self.assertFalse(ent.is_live_dispatch_enabled())

    async def test_engagement_logs_dispatch_mode(self):
        ent = ConsultingEnterprise(enable_live_dispatch=False)
        engagement = ConsultingEngagement(ent)
        artifacts = await engagement.execute_engagement(
            client_name="Acme Health",
            raw_rfp="Build telehealth appointment scheduler.",
        )
        # Verify signoff records governance verification
        self.assertIn("Governance Security Verification", artifacts.delivery_signoff)
        self.assertIn("STAGED (Preview / Dry-Run)", artifacts.delivery_signoff)


class TestProjectRootJailing(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_jail = tempfile.mkdtemp()
        set_allowed_roots([self.temp_jail])

    def tearDown(self):
        shutil.rmtree(self.temp_jail, ignore_errors=True)
        # Restore standard roots
        set_allowed_roots(["/home/acinonyx/Desktop/MAS", "/srv/mas-projects", "/tmp"])

    async def test_write_inside_jail_succeeds(self):
        target = os.path.join(self.temp_jail, "sub", "test.py")
        res = await fs_write_file(target, "print('inside jail')")
        self.assertIn("SUCCESS", res)
        self.assertTrue(os.path.exists(target))

    async def test_write_outside_jail_blocked(self):
        # Attempt to write outside the configured jail boundary
        forbidden = "/var/log/malicious_agent_output.log"
        res = await fs_write_file(forbidden, "payload")
        self.assertIn("ERROR: Access denied", res)
        self.assertIn("outside authorized project boundaries", res)

    async def test_read_outside_jail_blocked(self):
        forbidden = "/etc/passwd"
        res = await fs_read_file(forbidden)
        self.assertIn("ERROR: Access denied", res)


class TestTokenBudgetGovernor(unittest.TestCase):
    def test_cumulative_spend_limit_enforced(self):
        gov = TokenBudgetGovernor(max_total_tokens=1000)
        # First request consumes 600 tokens
        ok, reason = gov.check_and_reserve(estimated_tokens=600)
        self.assertTrue(ok)
        self.assertEqual(reason, "APPROVED")

        # Second request attempts 500 tokens (600 + 500 = 1100 > 1000)
        ok2, reason2 = gov.check_and_reserve(estimated_tokens=500)
        self.assertFalse(ok2)
        self.assertIn("CUMULATIVE_BUDGET_EXCEEDED", reason2)

    def test_request_rate_limiting_enforced(self):
        # Allow max 3 requests per minute
        gov = TokenBudgetGovernor(max_total_tokens=100_000, max_requests_per_minute=3)
        self.assertTrue(gov.check_and_reserve(10)[0])
        self.assertTrue(gov.check_and_reserve(10)[0])
        self.assertTrue(gov.check_and_reserve(10)[0])

        # 4th request should trip rate limit circuit breaker
        ok, reason = gov.check_and_reserve(10)
        self.assertFalse(ok)
        self.assertIn("RATE_LIMIT_EXCEEDED", reason)

    def test_per_engagement_token_ceiling_enforced(self):
        gov = TokenBudgetGovernor(max_total_tokens=500_000, max_tokens_per_engagement=2000)
        # Client A consumes 1500 tokens
        ok_a1, _ = gov.check_and_reserve(1500, engagement_id="client_alpha")
        self.assertTrue(ok_a1)

        # Client A tries another 1000 tokens (1500 + 1000 = 2500 > 2000) -> blocked
        ok_a2, reason_a2 = gov.check_and_reserve(1000, engagement_id="client_alpha")
        self.assertFalse(ok_a2)
        self.assertIn("ENGAGEMENT_BUDGET_EXCEEDED", reason_a2)

        # Client B is completely unblocked (independent engagement bucket)
        ok_b, _ = gov.check_and_reserve(1200, engagement_id="client_beta")
        self.assertTrue(ok_b)


class TestStdioMCPServer(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_protocol(self):
        req = {"jsonrpc": "2.0", "id": 100, "method": "initialize", "params": {}}
        resp = await handle_request(req)
        self.assertEqual(resp.get("id"), 100)
        self.assertEqual(resp.get("result", {}).get("serverInfo", {}).get("name"), "mas-coordinator")

    async def test_tools_list_exposes_7_tools(self):
        req = {"jsonrpc": "2.0", "id": 101, "method": "tools/list", "params": {}}
        resp = await handle_request(req)
        tools = resp.get("result", {}).get("tools", [])
        tool_names = [t["name"] for t in tools]
        expected = [
            "mas_projects", "mas_submit_task", "mas_get_status",
            "mas_inspect_artifact", "mas_cio_audit", "mas_git_branch", "mas_search_memory",
        ]
        for exp in expected:
            self.assertIn(exp, tool_names)

    async def test_tools_call_mas_projects(self):
        req = {
            "jsonrpc": "2.0",
            "id": 102,
            "method": "tools/call",
            "params": {"name": "mas_projects", "arguments": {}},
        }
        resp = await handle_request(req)
        text = resp["result"]["content"][0]["text"]
        self.assertIn("MAS Project Registry", text)
        self.assertIn("Live Dispatch", text)

    async def test_tools_call_mas_search_memory(self):
        req = {
            "jsonrpc": "2.0",
            "id": 103,
            "method": "tools/call",
            "params": {"name": "mas_search_memory", "arguments": {"query": "database connection timeout"}},
        }
        resp = await handle_request(req)
        text = resp["result"]["content"][0]["text"]
        self.assertTrue(len(text) > 0)


class TestBrowserResearchTools(unittest.IsolatedAsyncioTestCase):
    def test_strip_html_tags(self):
        raw_html = "<html><head><style>body {color:red}</style></head><body><h1>API Reference</h1><p>Documentation paragraph.</p></body></html>"
        cleaned = _strip_html_tags(raw_html)
        self.assertNotIn("<style>", cleaned)
        self.assertIn("API Reference", cleaned)
        self.assertIn("Documentation paragraph.", cleaned)

    async def test_web_search_tool(self):
        res = await web_search_tool(query="FastAPI OAuth2 JWT security")
        self.assertTrue(res.get("success"))
        self.assertGreater(len(res.get("results", [])), 0)


if __name__ == "__main__":
    unittest.main()
