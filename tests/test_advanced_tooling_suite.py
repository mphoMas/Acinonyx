"""
tests.test_advanced_tooling_suite: Unit tests for surgical file patching,
research knowledge vault RAG, human-in-the-loop gates, and POPIA/GDPR PII anonymization.
"""

import os
import unittest
from mas.capabilities import capability_matrix
from mas.mcp.protocol import MCPRegistry
from mas.tools.hitl_tool import (
    GLOBAL_HITL_MANAGER,
    ask_human_clarification_tool,
    register_hitl_tools,
)
from mas.tools.knowledge_vault_tool import (
    query_knowledge_vault_tool,
    register_knowledge_vault_tools,
)
from mas.tools.patch_tool import (
    fs_patch_file_tool,
    register_patch_tools,
)
from mas.tools.pii_tool import (
    pii_anonymize_text_tool,
    pii_deanonymize_text_tool,
    register_pii_tools,
)


import shutil
import tempfile
from mas.config import REPO_ROOT
from mas.tools.filesystem import ALLOWED_PROJECT_ROOTS, set_allowed_roots


class TestSurgicalPatchTool(unittest.TestCase):
    def setUp(self):
        self.orig_roots = list(ALLOWED_PROJECT_ROOTS)
        self.test_dir = tempfile.mkdtemp(prefix="mas_patch_test_")
        set_allowed_roots([REPO_ROOT, self.test_dir])
        self.test_file = os.path.join(self.test_dir, "test_patch_sample.py")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("def calculate_tax(amount):\n    rate = 0.15\n    return amount * rate\n")

    def tearDown(self):
        set_allowed_roots(self.orig_roots)
        if hasattr(self, "test_dir") and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_patch_unique_match(self):
        res = fs_patch_file_tool(
            path=self.test_file,
            target_content="rate = 0.15",
            replacement_content="rate = 0.20  # Updated SA VAT rate",
        )
        self.assertTrue(res["success"])
        with open(self.test_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("rate = 0.20", content)
        self.assertNotIn("rate = 0.15", content)

    def test_patch_target_not_found(self):
        res = fs_patch_file_tool(
            path=self.test_file,
            target_content="non_existent_code_line()",
            replacement_content="something_else()",
        )
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])

    def test_patch_path_outside_jail(self):
        res = fs_patch_file_tool(
            path="/etc/shadow",
            target_content="root",
            replacement_content="hacked",
        )
        self.assertFalse(res["success"])
        self.assertIn("Access denied", res["error"])


class TestKnowledgeVaultRAGTool(unittest.TestCase):
    def test_query_coala_architecture(self):
        res = query_knowledge_vault_tool(query="CoALA memory working episodic", max_results=3)
        self.assertTrue(res["success"])
        self.assertTrue(res["count"] > 0)
        self.assertTrue(any("CoALA" in r["title"] or "CoALA" in r["snippet"] or "coala" in r["file"].lower() for r in res["results"]))

    def test_query_with_category_filter(self):
        res = query_knowledge_vault_tool(query="POMDP ScreenSpot OSWorld", category="agentic_systems", max_results=2)
        self.assertTrue(res["success"])
        self.assertTrue(res["count"] > 0)


class TestHumanInTheLoopTool(unittest.TestCase):
    def test_autonomous_fallback(self):
        res = ask_human_clarification_tool(
            question="Should the staging database be partitioned by ingestion_date?",
            options=["Yes, partition by date", "No, keep unpartitioned"],
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "auto_resolved")
        self.assertEqual(res["chosen_answer"], "Yes, partition by date")

    def test_interactive_responder(self):
        GLOBAL_HITL_MANAGER.register_interactive_responder(
            lambda q, opts: opts[1]  # Simulate user selecting 2nd option
        )
        res = ask_human_clarification_tool(
            question="Select deployment strategy",
            options=["Rolling update", "Canary deployment"],
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "user_answered")
        self.assertEqual(res["chosen_answer"], "Canary deployment")
        # Reset responder
        GLOBAL_HITL_MANAGER._interactive_responder = None


class TestPIIAnonymizerTool(unittest.TestCase):
    def test_anonymize_sa_id_and_email_and_cards(self):
        # 8001015009087 is a valid Luhn mod-10 13-digit sequence
        raw_text = "Client Mpho Mashile (ID: 8001015009087, email: test.client@bank.co.za) transferred funds from 4111111111111111."
        res = pii_anonymize_text_tool(raw_text)
        self.assertTrue(res["success"])
        self.assertTrue(res["redactions_count"] >= 3)
        anon_text = res["anonymized_text"]
        self.assertNotIn("8001015009087", anon_text)
        self.assertNotIn("test.client@bank.co.za", anon_text)
        self.assertNotIn("4111111111111111", anon_text)
        self.assertIn("[REDACTED_SA_ID_", anon_text)
        self.assertIn("[REDACTED_EMAIL_", anon_text)

        # Verify Roundtrip Deanonymization in Secure Enclave
        restored = pii_deanonymize_text_tool(anon_text, res["token_map"])
        self.assertTrue(restored["success"])
        self.assertEqual(restored["restored_text"], raw_text)


class TestMCPRegistryAndCapabilityMatrix(unittest.TestCase):
    def test_mcp_registration(self):
        registry = MCPRegistry()
        register_patch_tools(registry)
        register_knowledge_vault_tools(registry)
        register_hitl_tools(registry)
        register_pii_tools(registry)

        tool_names = set(registry.tools.keys())
        expected = {
            "fs_patch_file",
            "query_knowledge_vault",
            "ask_human_clarification",
            "pii_anonymize",
            "pii_deanonymize",
        }
        self.assertTrue(expected.issubset(tool_names), f"Missing tools: {expected - tool_names}")

    def test_capability_matrix_updated(self):
        matrix = capability_matrix()
        for cap in [
            "surgical_file_patching",
            "research_knowledge_vault_rag",
            "human_in_the_loop_gate",
            "popia_pii_anonymizer",
        ]:
            self.assertIn(cap, matrix, f"Missing capability: {cap}")
            self.assertEqual(matrix[cap]["status"], "implemented")


if __name__ == "__main__":
    unittest.main()
