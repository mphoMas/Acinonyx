"""
Evaluation harness: structural scoring for golden missions (mock-safe).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from mas.core.agent import BaseAgent
from mas.core.message import Role
from mas.eval.golden import GOLDEN_MISSIONS, GoldenMission
from mas.orchestration.debate import DebateEngine
from mas.orchestration.pipeline import SOPPipeline
from mas.orchestration.supervisor import SupervisorAgent
from mas.validation import SchemaSpec


@dataclass
class EvalResult:
    mission_id: str
    passed: bool
    score: float
    details: Dict[str, Any] = field(default_factory=dict)


class EchoAgent(BaseAgent):
    def __init__(self, name: str, prefix: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.prefix = prefix

    async def reason(self, context_messages):
        last = context_messages[-1] if context_messages else None
        content = last.content if last else ""
        return f"{self.prefix} {content}"


class DistinctEcho(BaseAgent):
    """Returns a short unique claim to keep lexical overlap low in mock debates."""

    def __init__(self, name: str, claim: str, **kwargs):
        super().__init__(name=name, **kwargs)
        self.claim = claim

    async def reason(self, context_messages):
        return self.claim


class EvaluationHarness:
    """Runs golden missions with deterministic echo agents (CI-safe)."""

    async def run_mission(self, mission: GoldenMission) -> EvalResult:
        if mission.domain == "supervisor":
            return await self._eval_supervisor(mission)
        if mission.domain == "debate":
            return await self._eval_debate(mission)
        if mission.domain == "pipeline":
            return await self._eval_pipeline(mission)
        return EvalResult(mission.id, False, 0.0, {"error": f"unknown domain {mission.domain}"})

    async def _eval_supervisor(self, mission: GoldenMission) -> EvalResult:
        supervisor = SupervisorAgent(name="eval_supervisor")
        a = EchoAgent("worker_a", "[A]", role=Role.ASSISTANT)
        b = EchoAgent("worker_b", "[B]", role=Role.ASSISTANT)
        supervisor.register_worker(a)
        supervisor.register_worker(b)
        summary = await supervisor.run_mission(
            mission.goal,
            [
                {"id": "t1", "description": "Extract", "worker": "worker_a", "dependencies": []},
                {"id": "t2", "description": "Train", "worker": "worker_b", "dependencies": ["t1"]},
            ],
        )
        hits = sum(1 for s in mission.must_include if s in summary)
        score = hits / max(len(mission.must_include), 1)
        return EvalResult(mission.id, score >= mission.min_score, score, {"summary_len": len(summary)})

    async def _eval_debate(self, mission: GoldenMission) -> EvalResult:
        engine = DebateEngine(
            debaters=[
                DistinctEcho("d1", "Monolith keeps transactional consistency simpler for MAS-Core.", role=Role.ASSISTANT),
                DistinctEcho("d2", "Independent deployability favors a modular service mesh later.", role=Role.ASSISTANT),
            ],
            moderator=DistinctEcho(
                "mod",
                "Judge Consensus: adopt modular monolith first, extract services on proven seams.",
                role=Role.MODERATOR,
            ),
            contrarian=DistinctEcho(
                "devil",
                "Both camps ignore operational cost of distributed tracing and partitions.",
                role=Role.CRITIC,
            ),
            max_rounds=2,
        )
        verdict = await engine.conduct_debate(mission.goal)
        hits = sum(1 for s in mission.must_include if s in verdict)
        score = hits / max(len(mission.must_include), 1)
        syc = engine.sycophancy_score()
        max_syc = float(mission.metadata.get("max_sycophancy", 1.0))
        passed = score >= mission.min_score and syc <= max_syc
        return EvalResult(
            mission.id,
            passed,
            score,
            {"sycophancy": syc, "transcript_turns": len(engine.transcript)},
        )

    async def _eval_pipeline(self, mission: GoldenMission) -> EvalResult:
        pipeline = SOPPipeline(name="eval-pipe")
        pipeline.add_stage(
            "spec",
            EchoAgent("architect", "[SPEC]", role=Role.ASSISTANT),
            "prd",
            "Draft: {input}",
            schema=SchemaSpec(must_contain=["[SPEC]"], min_length=5),
        )
        pipeline.add_stage(
            "impl",
            EchoAgent("engineer", "[CODE]", role=Role.ASSISTANT),
            "code",
            "Implement: {prd}",
            schema=SchemaSpec(must_contain=["[CODE]"], min_length=5),
        )
        artifacts = await pipeline.execute(mission.goal)
        hits = sum(1 for s in mission.must_include if s in artifacts)
        score = hits / max(len(mission.must_include), 1)
        return EvalResult(mission.id, score >= mission.min_score, score, {"keys": list(artifacts)})


async def run_default_evals() -> List[EvalResult]:
    harness = EvaluationHarness()
    results: List[EvalResult] = []
    for mission in GOLDEN_MISSIONS:
        results.append(await harness.run_mission(mission))
    return results
