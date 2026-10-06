"""
tests/test_strike_pod.py: Unit tests for the Liquid Strike Pod Orchestrator.
Validates dynamic assembly, Level 2 Gated Milestones, Merkle provenance, and auto-disbandment.
"""

import unittest
from mas.organization.company import AcinonyxEnterprise
from mas.orchestration.strike_pod import (
    StrikePodOrchestrator,
    PodMissionSpec,
    PodMissionResult,
    PodStatus,
)


class TestLiquidStrikePodOrchestrator(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.enterprise = AcinonyxEnterprise()
        self.orchestrator = StrikePodOrchestrator(enterprise=self.enterprise)

    def test_pod_assembly(self):
        """Verify dynamic pod assembly pulls agents from AcinonyxEnterprise guilds."""
        spec = PodMissionSpec(
            title="Competitor Intelligence SaaS",
            requirements="Build an automated competitive monitoring dashboard.",
        )
        pod = self.orchestrator.assemble_pod(spec)

        self.assertEqual(pod.status, PodStatus.INITIALIZED)
        self.assertIn("market_researcher", pod.agents)
        self.assertIn("chief_architect", pod.agents)
        self.assertIn("backend_engineer", pod.agents)
        self.assertIn("adversarial_red_team", pod.agents)
        self.assertIn("qa_critic", pod.agents)
        self.assertIn(pod.pod_id, self.orchestrator.list_active_pods())

    async def test_full_ephemeral_mission_lifecycle(self):
        """Verify atomic run_ephemeral_mission executes all 5 phases, computes Merkle root, and auto-disbands."""
        spec = PodMissionSpec(
            title="Real-Time Agent Observability SaaS",
            requirements="Develop an agent execution cockpit with WebSocket streaming and error telemetry.",
            auto_gate1=True,
            auto_gate2=True,
        )

        result: PodMissionResult = await self.orchestrator.run_ephemeral_mission(spec)

        # 1. Verification of delivery success
        self.assertTrue(result.success)
        self.assertEqual(result.status, PodStatus.COMPLETED)

        # 2. Verification of all phase artifacts
        self.assertTrue(len(result.research_dossier) > 0)
        self.assertTrue(len(result.prd) > 0)
        self.assertTrue(len(result.design_system) > 0)
        self.assertTrue(len(result.architecture_spec) > 0)
        self.assertTrue(len(result.implementation_code) > 0)
        self.assertTrue(len(result.test_suite) > 0)
        self.assertTrue(len(result.qa_report) > 0)
        self.assertTrue(len(result.red_team_report) > 0)
        self.assertTrue(len(result.documentation) > 0)

        # 3. Verification of Cryptographic Merkle Provenance
        self.assertEqual(len(result.merkle_provenance_hash), 64)  # Valid SHA-256 length

        # 4. Verification of FinOps 2.0 ROI Score
        self.assertGreater(result.value_roi_score, 0.0)

        # 5. Verification of Auto-Disbandment
        self.assertEqual(len(self.orchestrator.list_active_pods()), 0)

    async def test_gated_milestone_rejection(self):
        """Verify that a rejected Gate 1 stops the pipeline before implementation begins."""
        async def reject_gate1(artifacts):
            return False

        spec = PodMissionSpec(
            title="Rejected Mission Spec",
            requirements="Ambiguous requirements that should fail Gate 1 review.",
            auto_gate1=False,
            gate1_callback=reject_gate1,
        )

        pod = self.orchestrator.assemble_pod(spec)
        result = await pod.execute_mission()

        self.assertFalse(result.success)
        self.assertEqual(result.status, PodStatus.FAILED)
        self.assertNotIn("phase3_implementation_code", result.artifacts_manifest)

        # Cleanup
        disband_info = await pod.disband()
        self.assertEqual(disband_info["status"], "disbanded")


if __name__ == "__main__":
    unittest.main()
