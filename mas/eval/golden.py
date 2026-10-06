"""
Golden mission definitions for structural evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class GoldenMission:
    id: str
    domain: str  # supervisor | debate | pipeline
    goal: str
    must_include: List[str] = field(default_factory=list)
    min_score: float = 0.7
    metadata: Dict = field(default_factory=dict)


GOLDEN_MISSIONS: List[GoldenMission] = [
    GoldenMission(
        id="supervisor_feature_extract",
        domain="supervisor",
        goal="Deploy ML Pipeline",
        must_include=["MISSION SUMMARY", "worker_a", "worker_b"],
        min_score=0.8,
    ),
    GoldenMission(
        id="debate_microservices",
        domain="debate",
        goal="Should microservices be adopted for MAS-Core?",
        must_include=["Judge", "Consensus"],
        min_score=0.6,
        # Echo agents share prompt tokens; structural CI allows full overlap.
        # Live LLM evals should tighten this (e.g. 0.55).
        metadata={"max_sycophancy": 1.0},
    ),
    GoldenMission(
        id="pipeline_feature_dev",
        domain="pipeline",
        goal="Build auth module",
        must_include=["prd", "code"],
        min_score=0.8,
    ),
]
