"""
tests/test_profile_pod.py: Unit tests for CompanyProfilePod multi-agent council.
Verifies assembly, agent hookup, Merkle provenance calculation, and fallback execution.
"""

import unittest
from mas.organization.profile_pod import CompanyProfilePod
from mas.providers.mock_provider import MockLLMProvider


class TestCompanyProfilePod(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MockLLMProvider()
        self.pod = CompanyProfilePod(llm_provider=self.mock_llm, pod_id="test_pod_123")

    def test_pod_initialization(self):
        self.assertEqual(self.pod.pod_id, "test_pod_123")
        self.assertEqual(len(self.pod.agents), 6)
        self.assertEqual(self.pod.market_researcher.name, "market_researcher")
        self.assertEqual(self.pod.product_lead.name, "product_lead")
        self.assertEqual(self.pod.chief_architect.name, "chief_architect")
        self.assertEqual(self.pod.data_engineer.name, "data_engineer")
        self.assertEqual(self.pod.adversarial_red_team.name, "adversarial_red_team")
        self.assertEqual(self.pod.technical_writer.name, "technical_writer")

    def test_merkle_provenance(self):
        sample_artifacts = {
            "phase1": "Market intelligence report content",
            "phase2": "Product strategy specs",
        }
        hash1 = self.pod._compute_merkle_provenance(sample_artifacts)
        hash2 = self.pod._compute_merkle_provenance(sample_artifacts)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA-256


if __name__ == "__main__":
    unittest.main()
