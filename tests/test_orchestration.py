"""
Tests for mas.orchestration (Supervisor, DebateEngine, SOPPipeline).
"""

import unittest
from mas.core.agent import BaseAgent
from mas.core.message import Message, Role
from mas.orchestration.supervisor import SupervisorAgent
from mas.orchestration.debate import DebateEngine
from mas.orchestration.pipeline import SOPPipeline


class CustomEchoAgent(BaseAgent):
    """Specialized mock agent returning deterministic test responses."""

    def __init__(self, name: str, response_prefix: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.response_prefix = response_prefix

    async def reason(self, context_messages):
        last_msg = context_messages[-1] if context_messages else None
        content = last_msg.content if last_msg else ""
        return f"{self.response_prefix} processed: {content}"


class TestOrchestrationTopologies(unittest.IsolatedAsyncioTestCase):

    async def test_hierarchical_supervisor_dag(self):
        supervisor = SupervisorAgent(name="head_supervisor")
        worker_a = CustomEchoAgent(name="worker_a", response_prefix="[Worker A]", role=Role.ASSISTANT)
        worker_b = CustomEchoAgent(name="worker_b", response_prefix="[Worker B]", role=Role.ASSISTANT)

        supervisor.register_worker(worker_a)
        supervisor.register_worker(worker_b)

        # Worker B depends on Worker A
        specs = [
            {"id": "t1", "description": "Extract features", "worker": "worker_a", "dependencies": []},
            {"id": "t2", "description": "Train model", "worker": "worker_b", "dependencies": ["t1"]},
        ]

        summary = await supervisor.run_mission("Deploy ML Pipeline", specs)
        self.assertIn("MISSION SUMMARY: Deploy ML Pipeline", summary)
        self.assertIn("[worker_a] Task 'Extract features'", summary)
        self.assertIn("[worker_b] Task 'Train model'", summary)
        self.assertIn("Preceding Artifacts", summary)

    async def test_anti_sycophancy_debate(self):
        debater_1 = CustomEchoAgent(name="debater_1", response_prefix="[Proponent]", role=Role.ASSISTANT)
        debater_2 = CustomEchoAgent(name="debater_2", response_prefix="[Pragmatist]", role=Role.ASSISTANT)
        contrarian = CustomEchoAgent(name="contrarian", response_prefix="[Devil's Advocate]", role=Role.CRITIC)
        moderator = CustomEchoAgent(name="moderator", response_prefix="[Judge Consensus]", role=Role.MODERATOR)

        engine = DebateEngine(
            debaters=[debater_1, debater_2],
            contrarian=contrarian,
            moderator=moderator,
            max_rounds=2,
        )

        verdict = await engine.conduct_debate("Should microservices be adopted for MAS-Core?")
        self.assertIn("[Judge Consensus]", verdict)
        self.assertEqual(len(engine.transcript), 6)  # 3 agents * 2 rounds

    async def test_sop_pipeline_execution(self):
        architect = CustomEchoAgent(name="architect", response_prefix="[SPEC]", role=Role.ASSISTANT)
        engineer = CustomEchoAgent(name="engineer", response_prefix="[CODE]", role=Role.ASSISTANT)

        pipeline = SOPPipeline(name="Feature-Dev")
        pipeline.add_stage(
            name="Specification",
            agent=architect,
            output_key="prd",
            instruction_template="Draft PRD for: {input}",
            validator=lambda out: "[SPEC]" in out,
        )
        pipeline.add_stage(
            name="Implementation",
            agent=engineer,
            output_key="code",
            instruction_template="Implement code based on PRD: {prd}",
            validator=lambda out: "[CODE]" in out,
        )

        artifacts = await pipeline.execute("Distributed Cache Layer")
        self.assertIn("prd", artifacts)
        self.assertIn("code", artifacts)
        self.assertIn("[SPEC]", artifacts["prd"])
        self.assertIn("[CODE]", artifacts["code"])


if __name__ == "__main__":
    unittest.main()
