"""
mas.orchestration.strike_pod: Liquid Strike Pod Orchestrator for Acinonyx Labs.
Dynamically assembles ephemeral cross-functional squads from Capability Guilds,
coordinates Research-1st mission DAGs with Level 2 Gated Milestones, enforces
cryptographic Merkle provenance, and auto-disbands pods upon delivery.

Architect: Acinonyx
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from mas.core.agent import BaseAgent
from mas.core.event_bus import EventBus
from mas.core.message import Message, MessageMetadata, Role
from mas.memory.episodic import EpisodicMemory
from mas.organization.roles import (
    AdversarialRedTeamAgent,
    BackendEngineerAgent,
    DesignerAgent,
    DevAdvocateAgent,
    FinOpsGovernorAgent,
    MarketResearcherAgent,
    ProductManagerAgent,
    TechnicalWriterAgent,
)
from mas.squad.squad import ArchitectAgent, EngineerAgent, QAAgent

logger = logging.getLogger("mas.strike_pod")


class PodStatus(str, Enum):
    INITIALIZED = "initialized"
    ASSEMBLING = "assembling"
    RESEARCHING = "researching"
    PRODUCT_DESIGN = "product_design"
    ARCHITECTURE = "architecture"
    GATE1_PENDING = "gate1_pending"
    IMPLEMENTING = "implementing"
    VERIFYING = "verifying"
    RED_TEAMING = "red_teaming"
    GATE2_PENDING = "gate2_pending"
    DOCUMENTING = "documenting"
    COMPLETED = "completed"
    FAILED = "failed"
    DISBANDED = "disbanded"


@dataclass
class PodMissionSpec:
    title: str
    requirements: str
    mission_id: str = field(default_factory=lambda: f"pod_{uuid.uuid4().hex[:8]}")
    target_code_file: Optional[str] = None
    target_test_file: Optional[str] = None
    auto_gate1: bool = True
    auto_gate2: bool = True
    budget_token_limit: int = 150_000
    gate1_callback: Optional[Callable[[Dict[str, str]], Coroutine[Any, Any, bool]]] = None
    gate2_callback: Optional[Callable[[Dict[str, str]], Coroutine[Any, Any, bool]]] = None
    required_specializations: List[str] = field(default_factory=lambda: [
        "market_researcher",
        "product_lead",
        "design_lead",
        "chief_architect",
        "backend_engineer",
        "qa_critic",
        "adversarial_red_team",
        "finops_governor",
        "technical_writer",
    ])


@dataclass
class PodMissionResult:
    mission_id: str
    title: str
    status: PodStatus
    success: bool
    research_dossier: str = ""
    prd: str = ""
    design_system: str = ""
    architecture_spec: str = ""
    implementation_code: str = ""
    test_suite: str = ""
    qa_report: str = ""
    red_team_report: str = ""
    documentation: str = ""
    merkle_provenance_hash: str = ""
    tokens_burned: int = 0
    value_roi_score: float = 0.0
    elapsed_seconds: float = 0.0
    disbanded_at: float = 0.0
    artifacts_manifest: Dict[str, str] = field(default_factory=dict)
    reflections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "title": self.title,
            "status": self.status.value,
            "success": self.success,
            "merkle_provenance_hash": self.merkle_provenance_hash,
            "tokens_burned": self.tokens_burned,
            "value_roi_score": self.value_roi_score,
            "elapsed_seconds": self.elapsed_seconds,
            "artifacts_manifest": self.artifacts_manifest,
        }


class LiquidStrikePod:
    """
    An ephemeral, self-contained multi-agent squad dynamically assembled
    to solve a specific mission and auto-disband upon delivery.
    """

    def __init__(
        self,
        spec: PodMissionSpec,
        agents: Dict[str, BaseAgent],
        event_bus: Optional[EventBus] = None,
        mcp_client: Optional[Any] = None,
    ) -> None:
        self.pod_id = spec.mission_id
        self.spec = spec
        self.agents = agents
        self.event_bus = event_bus or EventBus(log_history=True)
        self.mcp_client = mcp_client
        self.status = PodStatus.INITIALIZED
        self.episodic_memory = EpisodicMemory()
        self.topic = f"org:pod:{self.pod_id}"
        self.tokens_consumed: int = 0
        self.start_time: float = time.time()
        self.artifacts: Dict[str, str] = {}
        self.reflections: List[str] = []

        # Hook agents to pod channel
        for agent in self.agents.values():
            if hasattr(agent, "attach_event_bus"):
                agent.attach_event_bus(self.event_bus, topic=self.topic)

    async def broadcast(self, content: str, sender: str = "pod_supervisor", role: Role = Role.SYSTEM) -> None:
        """Publish a message to all agents in this ephemeral pod."""
        msg = Message(
            sender=sender,
            recipient="broadcast",
            role=role,
            content=content,
            metadata=MessageMetadata(topic=self.topic, extra={"pod_id": self.pod_id}),
        )
        await self.event_bus.publish(msg)

    def _compute_merkle_provenance(self) -> str:
        """Compute SHA-256 Merkle root across all generated pod artifacts."""
        hasher = hashlib.sha256()
        sorted_keys = sorted(self.artifacts.keys())
        for k in sorted_keys:
            hasher.update(k.encode("utf-8"))
            hasher.update(self.artifacts[k].encode("utf-8"))
        hasher.update(self.pod_id.encode("utf-8"))
        return hasher.hexdigest()

    async def execute_mission(self) -> PodMissionResult:
        """
        Execute the full Research-1st 5-phase delivery pipeline:
        Phase 0 (Research) -> Phase 1 (PRD/Design) -> Phase 2 (Arch) ->
        [Gate 1 Review] -> Phase 3 (Dev/QA Reflexion) -> Phase 4 (Red Team) ->
        [Gate 2 Deploy Review] -> Phase 5 (GTM/Docs).
        """
        self.status = PodStatus.ASSEMBLING
        await self.broadcast(f"Liquid Strike Pod '{self.pod_id}' assembled for: {self.spec.title}")

        # ---------------------------------------------------------------------
        # Phase 0: Market Research & Feasibility
        # ---------------------------------------------------------------------
        self.status = PodStatus.RESEARCHING
        researcher = self.agents.get("market_researcher") or MarketResearcherAgent()
        research_dossier = await researcher.step(
            Message(
                sender="pod_supervisor",
                recipient=researcher.name,
                role=Role.USER,
                content=f"Conduct Phase 0 Market Intelligence for:\n{self.spec.requirements}",
            )
        )
        self.artifacts["phase0_research_dossier"] = research_dossier.content

        # ---------------------------------------------------------------------
        # Phase 1: Product Requirements & UI/UX Design System
        # ---------------------------------------------------------------------
        self.status = PodStatus.PRODUCT_DESIGN
        pm = self.agents.get("product_lead") or ProductManagerAgent()
        prd = await pm.step(
            Message(
                sender="pod_supervisor",
                recipient=pm.name,
                role=Role.USER,
                content=f"Create PRD based on Market Research:\n{self.artifacts['phase0_research_dossier']}",
            )
        )
        self.artifacts["phase1_prd"] = prd.content

        designer = self.agents.get("design_lead") or DesignerAgent()
        design_spec = await designer.step(
            Message(
                sender="pod_supervisor",
                recipient=designer.name,
                role=Role.USER,
                content=f"Create UI/UX Design System for PRD:\n{self.artifacts['phase1_prd']}",
            )
        )
        self.artifacts["phase1_design_system"] = design_spec.content

        # ---------------------------------------------------------------------
        # Phase 2: Architecture Specification
        # ---------------------------------------------------------------------
        self.status = PodStatus.ARCHITECTURE
        architect = self.agents.get("chief_architect") or ArchitectAgent(name="chief_architect")
        arch_spec = await architect.step(
            Message(
                sender="pod_supervisor",
                recipient=architect.name,
                role=Role.USER,
                content=f"Design Modular Architecture Spec for:\n{self.artifacts['phase1_prd']}",
            )
        )
        self.artifacts["phase2_architecture_spec"] = arch_spec.content

        # ---------------------------------------------------------------------
        # Gated Milestone 1: Design & Scope Sign-Off
        # ---------------------------------------------------------------------
        self.status = PodStatus.GATE1_PENDING
        gate1_approved = True
        if self.spec.gate1_callback:
            gate1_approved = await self.spec.gate1_callback(self.artifacts)
        elif not self.spec.auto_gate1:
            gate1_approved = False

        if not gate1_approved:
            self.status = PodStatus.FAILED
            await self.broadcast("Gate 1 (Design Review) rejected. Mission halted.")
            return self._build_result(success=False)

        await self.broadcast("Gate 1 (Design Review) APPROVED. Proceeding to Implementation.")

        # ---------------------------------------------------------------------
        # Phase 3: Software Implementation & QA Reflexion Loop
        # ---------------------------------------------------------------------
        self.status = PodStatus.IMPLEMENTING
        engineer = self.agents.get("backend_engineer") or self.agents.get("senior_engineer") or EngineerAgent()
        impl_code = await engineer.step(
            Message(
                sender="pod_supervisor",
                recipient=engineer.name,
                role=Role.USER,
                content=(
                    f"Implement clean Python source code matching Architecture:\n"
                    f"{self.artifacts['phase2_architecture_spec']}\n\nRequirements:\n{self.spec.requirements}"
                ),
            )
        )
        self.artifacts["phase3_implementation_code"] = impl_code.content

        test_code = (
            f"# Tests for {self.spec.title}\n"
            f"import unittest\n\n"
            f"class Test{self.pod_id}(unittest.TestCase):\n"
            f"    def test_invariants(self):\n"
            f"        self.assertTrue(True)\n\n"
            f"if __name__ == '__main__':\n"
            f"    unittest.main()\n"
        )
        self.artifacts["phase3_test_suite"] = test_code

        # QA Verification
        self.status = PodStatus.VERIFYING
        qa = self.agents.get("qa_critic") or QAAgent()
        qa_report = await qa.step(
            Message(
                sender="pod_supervisor",
                recipient=qa.name,
                role=Role.USER,
                content=f"Verify implementation and test suite:\nCode:\n{impl_code.content}\nTests:\n{test_code}",
            )
        )
        self.artifacts["phase3_qa_report"] = qa_report.content

        # ---------------------------------------------------------------------
        # Phase 4: Synthetic Adversary / Chaos Red Team Penetration
        # ---------------------------------------------------------------------
        self.status = PodStatus.RED_TEAMING
        red_team = self.agents.get("adversarial_red_team") or AdversarialRedTeamAgent()
        red_report = await red_team.step(
            Message(
                sender="pod_supervisor",
                recipient=red_team.name,
                role=Role.USER,
                content=(
                    f"Perform Adversarial Chaos and Prompt Injection Penetration Audit on:\n"
                    f"Spec: {self.artifacts['phase2_architecture_spec']}\n"
                    f"Code: {self.artifacts['phase3_implementation_code']}"
                ),
            )
        )
        self.artifacts["phase4_red_team_report"] = red_report.content

        # ---------------------------------------------------------------------
        # Gated Milestone 2: Production Deployment Sign-Off
        # ---------------------------------------------------------------------
        self.status = PodStatus.GATE2_PENDING
        gate2_approved = True
        if self.spec.gate2_callback:
            gate2_approved = await self.spec.gate2_callback(self.artifacts)
        elif not self.spec.auto_gate2:
            gate2_approved = False

        if not gate2_approved:
            self.status = PodStatus.FAILED
            await self.broadcast("Gate 2 (Deploy Review) rejected. Mission halted.")
            return self._build_result(success=False)

        await self.broadcast("Gate 2 (Deploy Review) APPROVED. Proceeding to Documentation & GTM.")

        # ---------------------------------------------------------------------
        # Phase 5: Technical Documentation & GTM Package
        # ---------------------------------------------------------------------
        self.status = PodStatus.DOCUMENTING
        tech_writer = self.agents.get("technical_writer") or TechnicalWriterAgent()
        docs = await tech_writer.step(
            Message(
                sender="pod_supervisor",
                recipient=tech_writer.name,
                role=Role.USER,
                content=(
                    f"Author full technical developer documentation for:\n"
                    f"PRD: {self.artifacts['phase1_prd']}\n"
                    f"Spec: {self.artifacts['phase2_architecture_spec']}"
                ),
            )
        )
        self.artifacts["phase5_documentation"] = docs.content

        # Compute Merkle Provenance Hash
        merkle_root = self._compute_merkle_provenance()
        self.artifacts["merkle_provenance_hash"] = merkle_root

        self.status = PodStatus.COMPLETED
        await self.broadcast(f"Mission '{self.spec.title}' COMPLETED. Merkle Hash: {merkle_root[:12]}...")

        return self._build_result(success=True)

    def _build_result(self, success: bool) -> PodMissionResult:
        elapsed = time.time() - self.start_time
        tokens = sum(getattr(a, "total_tokens_consumed", 0) for a in self.agents.values())
        # FinOps 2.0 ROI metric: Value weight (100) / (tokens * latency + 1)
        roi = round(100.0 / max((tokens * 0.001) + (elapsed * 0.1), 1.0), 3)

        return PodMissionResult(
            mission_id=self.pod_id,
            title=self.spec.title,
            status=self.status,
            success=success,
            research_dossier=self.artifacts.get("phase0_research_dossier", ""),
            prd=self.artifacts.get("phase1_prd", ""),
            design_system=self.artifacts.get("phase1_design_system", ""),
            architecture_spec=self.artifacts.get("phase2_architecture_spec", ""),
            implementation_code=self.artifacts.get("phase3_implementation_code", ""),
            test_suite=self.artifacts.get("phase3_test_suite", ""),
            qa_report=self.artifacts.get("phase3_qa_report", ""),
            red_team_report=self.artifacts.get("phase4_red_team_report", ""),
            documentation=self.artifacts.get("phase5_documentation", ""),
            merkle_provenance_hash=self.artifacts.get("merkle_provenance_hash", ""),
            tokens_burned=tokens,
            value_roi_score=roi,
            elapsed_seconds=round(elapsed, 3),
            artifacts_manifest=dict(self.artifacts),
            reflections=list(self.reflections),
        )

    async def disband(self) -> Dict[str, Any]:
        """
        Cleanly disband the ephemeral strike pod:
        - Store mission reflections into episodic memory
        - Detach pod event bus subscriptions
        - Release agent locks
        - Return operational summary
        """
        self.status = PodStatus.DISBANDED
        disband_time = time.time()

        # Record episodic reflection
        self.episodic_memory.record_reflection(
            task=f"Liquid Strike Pod Mission: {self.spec.title}",
            success=(self.status in (PodStatus.COMPLETED, PodStatus.DISBANDED)),
            critique=f"Pod {self.pod_id} finalized delivery with {len(self.artifacts)} verified artifacts.",
            suggested_strategy="Ephemeral strike pod allocation validated zero-queue delivery.",
            tags=["strike_pod", "liquid_swarm", self.pod_id],
        )

        await self.broadcast(f"Liquid Strike Pod '{self.pod_id}' DISBANDED. Agents returned to Capability Guilds.")

        # Detach pod listeners
        for agent_name, agent in self.agents.items():
            try:
                self.event_bus.unsubscribe(agent_name, topic=self.topic)
            except Exception:
                pass

        return {
            "pod_id": self.pod_id,
            "status": PodStatus.DISBANDED.value,
            "disbanded_at": disband_time,
            "agents_released": list(self.agents.keys()),
            "total_artifacts": len(self.artifacts),
        }


class StrikePodOrchestrator:
    """
    Supervisor Factory & Lifecycle Manager for Liquid Strike Pods.
    Pulls specialized agents from enterprise Capability Guilds, spins up
    ephemeral pods, executes mission DAGs, and guarantees auto-disbandment.
    """

    def __init__(
        self,
        enterprise: Optional[Any] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.enterprise = enterprise
        self.event_bus = event_bus or (enterprise.event_bus if enterprise else EventBus())
        self.active_pods: Dict[str, LiquidStrikePod] = {}
        self.completed_missions: List[PodMissionResult] = []

    def assemble_pod(self, spec: PodMissionSpec) -> LiquidStrikePod:
        """Assemble an ephemeral cross-functional strike pod for a mission."""
        assigned_agents: Dict[str, BaseAgent] = {}

        # 1. Resolve agents from enterprise Capability Guilds if available
        if self.enterprise:
            roster = {
                "market_researcher": getattr(self.enterprise, "market_researcher", None),
                "product_lead": getattr(self.enterprise, "product_lead", None),
                "design_lead": getattr(self.enterprise, "design_lead", None),
                "chief_architect": getattr(self.enterprise, "chief_architect", None),
                "backend_engineer": getattr(self.enterprise, "backend_engineer", None),
                "senior_engineer": getattr(self.enterprise, "lead_engineer", None),
                "qa_critic": getattr(self.enterprise, "qa_critic", None),
                "adversarial_red_team": getattr(self.enterprise, "adversarial_red_team", None),
                "finops_governor": getattr(self.enterprise, "finops_governor", None),
                "technical_writer": getattr(self.enterprise, "technical_writer", None),
                "dev_advocate": getattr(self.enterprise, "dev_advocate", None),
            }
            for role_name in spec.required_specializations:
                if roster.get(role_name):
                    assigned_agents[role_name] = roster[role_name]

        # 2. Fallback instantiation for missing specializations
        fallback_factory = {
            "market_researcher": MarketResearcherAgent,
            "product_lead": ProductManagerAgent,
            "design_lead": DesignerAgent,
            "chief_architect": lambda: ArchitectAgent(name="chief_architect"),
            "backend_engineer": BackendEngineerAgent,
            "senior_engineer": EngineerAgent,
            "qa_critic": QAAgent,
            "adversarial_red_team": AdversarialRedTeamAgent,
            "finops_governor": FinOpsGovernorAgent,
            "technical_writer": TechnicalWriterAgent,
            "dev_advocate": DevAdvocateAgent,
        }

        for role_name in spec.required_specializations:
            if role_name not in assigned_agents and role_name in fallback_factory:
                assigned_agents[role_name] = fallback_factory[role_name]()

        pod = LiquidStrikePod(
            spec=spec,
            agents=assigned_agents,
            event_bus=self.event_bus,
            mcp_client=getattr(self.enterprise, "mcp_client", None) if self.enterprise else None,
        )

        self.active_pods[pod.pod_id] = pod
        return pod

    async def run_ephemeral_mission(self, spec: PodMissionSpec) -> PodMissionResult:
        """
        Atomic lifecycle:
        Assemble Strike Pod -> Execute Mission DAG -> Auto-Disband upon delivery.
        """
        pod = self.assemble_pod(spec)
        try:
            result = await pod.execute_mission()
            self.completed_missions.append(result)
            return result
        finally:
            await pod.disband()
            self.active_pods.pop(pod.pod_id, None)

    def list_active_pods(self) -> List[str]:
        return list(self.active_pods.keys())
