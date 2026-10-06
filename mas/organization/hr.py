"""
mas.organization.hr: Human Resources & Talent Operations agent for dynamic skill gap analysis and agent synthesis.
Architect: Acinonyx
"""

from __future__ import annotations
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from mas.core.agent import BaseAgent
from mas.core.message import Message, Role
from mas.organization.department import DepartmentType


@dataclass
class JobRequisition:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role_title: str = ""
    department_type: DepartmentType = DepartmentType.ENGINEERING
    system_prompt: str = ""
    required_skills: List[str] = field(default_factory=list)
    rationale: str = ""


class HRAgent(BaseAgent):
    """
    Chief People Officer & Talent Operations Agent.
    Responsible for:
    1. Analyzing client requirements & technical briefs to detect skill/role gaps.
    2. Dynamically formulating Job Requisitions for missing specializations.
    3. Synthesizing and provisioning new autonomous agents into company departments.
    """

    def __init__(self, name: str = "hr_director", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.SUPERVISOR,
            system_prompt=(
                "You are the Director of Human Resources & Talent Operations for the enterprise consulting firm. "
                "Your mission is to perform organizational capacity planning, identify missing domain competencies, "
                "and dynamically create specialized autonomous agents to fill project gaps."
            ),
            **kwargs,
        )

        # Domain competency keyword map to match requirements against missing roles
        self.competency_catalog: Dict[str, Dict[str, Any]] = {
            "security": {
                "role_title": "cybersecurity_auditor",
                "department": DepartmentType.ENGINEERING,
                "keywords": ["security", "audit", "compliance", "soc2", "hipaa", "gdpr", "vulnerability", "penetration", "auth"],
                "system_prompt": (
                    "You are the Principal Cybersecurity & Compliance Auditor. You perform threat modeling, "
                    "verify OWASP Top 10 vulnerabilities, enforce zero-trust policies, and audit data privacy regulations."
                ),
            },
            "data_science": {
                "role_title": "data_architect_ai",
                "department": DepartmentType.ENGINEERING,
                "keywords": ["ai", "machine learning", "ml", "embeddings", "vector", "pipeline", "etl", "analytics", "llm"],
                "system_prompt": (
                    "You are the Staff Data & AI Systems Architect. You design data ingestion pipelines, "
                    "RAG vector stores, model fine-tuning topologies, and high-throughput streaming architectures."
                ),
            },
            "devops": {
                "role_title": "site_reliability_engineer",
                "department": DepartmentType.ENGINEERING,
                "keywords": ["kubernetes", "docker", "terraform", "ci/cd", "infra", "deploy", "monitoring", "latency", "scale"],
                "system_prompt": (
                    "You are the Senior Site Reliability Engineer (SRE). You architect cloud infrastructure, "
                    "Docker/Kubernetes deployments, CI/CD pipelines, and real-time observability telemetry."
                ),
            },
            "fintech": {
                "role_title": "fintech_compliance_officer",
                "department": DepartmentType.CLIENT_MANAGEMENT,
                "keywords": ["fintech", "payment", "stripe", "pci-dss", "banking", "ledger", "kyc", "aml"],
                "system_prompt": (
                    "You are the Chief FinTech Compliance Officer. You enforce PCI-DSS standards, double-entry ledger "
                    "integrity, payment gateway security, and international financial regulations."
                ),
            },
            "seo_growth": {
                "role_title": "growth_hacker_seo",
                "department": DepartmentType.GROWTH_GTM,
                "keywords": ["seo", "conversion", "funnel", "growth", "cac", "ltv", "adwords", "retention"],
                "system_prompt": (
                    "You are the Senior Growth & SEO Strategist. You optimize customer acquisition funnels, "
                    "search engine indexing, viral referral loops, and user retention analytics."
                ),
            },
            "market_research": {
                "role_title": "market_researcher",
                "department": DepartmentType.RESEARCH_PRODUCT,
                "keywords": ["market", "research", "competitor", "tam", "sam", "pricing", "moat", "discovery", "friction"],
                "system_prompt": (
                    "You are the Lead Market & Domain Intelligence Researcher. You ground every initiative in empirical data, "
                    "competitor analysis, and customer workflow friction points."
                ),
            },
            "chaos_red_team": {
                "role_title": "adversarial_red_team",
                "department": DepartmentType.QA_VERIFICATION,
                "keywords": ["red team", "chaos", "fuzzing", "prompt injection", "jailbreak", "exploit", "adversarial testing", "adversary"],
                "system_prompt": (
                    "You are the Adversarial Chaos Engineer and Red Team Lead. You aggressively attack workflows for "
                    "prompt injection vulnerabilities, unauthorized tool escalation, state corruptions, and race conditions."
                ),
            },
            "finops": {
                "role_title": "finops_governor",
                "department": DepartmentType.PLATFORM_SECURITY,
                "keywords": ["finops", "budget", "token", "roi", "cost", "margin", "pricing tier", "spend", "efficiency"],
                "system_prompt": (
                    "You are the FinOps & Value-per-Token Economic Governor. You enforce economic discipline, "
                    "calculate task ROI metrics, optimize model tiering, and prevent runaway compute burn."
                ),
            },
            "vector_rag": {
                "role_title": "vector_rag_architect",
                "department": DepartmentType.DATA_AI,
                "keywords": ["vector", "rag", "embeddings", "semantic search", "retrieval", "chunking", "knowledge graph"],
                "system_prompt": (
                    "You are the Vector & Semantic Retrieval Architect. You design embedding topologies, "
                    "hybrid search vector indices, metadata filtering layers, and high-precision RAG pipelines."
                ),
            },
            "backend_systems": {
                "role_title": "backend_engineer",
                "department": DepartmentType.SOFTWARE_DEV,
                "keywords": ["backend", "fastapi", "api", "database", "postgres", "microservice", "asyncio", "rest"],
                "system_prompt": (
                    "You are the Principal Backend Engineer. You implement clean, asynchronous, "
                    "well-typed Python/FastAPI services, database models, and robust REST/gRPC interfaces."
                ),
            },
            "frontend_ui": {
                "role_title": "frontend_engineer",
                "department": DepartmentType.SOFTWARE_DEV,
                "keywords": ["frontend", "ui", "react", "css", "component", "dashboard", "wireframe", "cockpit"],
                "system_prompt": (
                    "You are the Principal Frontend Engineer. You translate design systems and user journey specs "
                    "into high-performance, dynamic, accessible web interfaces and SaaS control cockpits."
                ),
            },
            "agent_orchestration": {
                "role_title": "agent_workflow_engineer",
                "department": DepartmentType.SOFTWARE_DEV,
                "keywords": ["workflow", "agentic", "langgraph", "state machine", "mcp", "orchestration", "multi-agent"],
                "system_prompt": (
                    "You are the Autonomous Agent Workflow Engineer. You design multi-agent state machines, "
                    "MCP tool bridges, deterministic decision graphs, and resilient Reflexion loops."
                ),
            },
        }

    def analyze_skill_gaps(
        self,
        project_requirements: str,
        current_roster_names: List[str],
    ) -> List[JobRequisition]:
        """
        Keyword catalog fallback: scan requirements against roster.
        Prefer analyze_skill_gaps_async when an LLM provider is attached.
        """
        requirements_lower = project_requirements.lower()
        active_roles_lower = {r.lower() for r in current_roster_names}

        requisitions: List[JobRequisition] = []

        for domain, info in self.competency_catalog.items():
            role_title = info["role_title"]
            keywords = info["keywords"]

            matched_keywords = [kw for kw in keywords if kw in requirements_lower]

            if matched_keywords:
                already_staffed = any(role_title in active_role for active_role in active_roles_lower)
                if not already_staffed:
                    req = JobRequisition(
                        role_title=role_title,
                        department_type=info["department"],
                        system_prompt=info["system_prompt"],
                        required_skills=matched_keywords,
                        rationale=f"Project requires '{domain}' expertise due to keywords: {', '.join(matched_keywords)}",
                    )
                    requisitions.append(req)

        return requisitions

    async def analyze_skill_gaps_async(
        self,
        project_requirements: str,
        current_roster_names: List[str],
    ) -> List[JobRequisition]:
        """
        LLM-backed gap analysis when provider is attached; otherwise keyword fallback.
        Provider is asked to name catalog role_titles that are missing; unknown titles ignored.
        """
        if not self.llm_provider:
            return self.analyze_skill_gaps(project_requirements, current_roster_names)

        catalog_roles = {
            info["role_title"]: (domain, info) for domain, info in self.competency_catalog.items()
        }
        prompt = (
            "You are HR Talent Ops. Given the project requirements and current roster, "
            "list missing specialized role_titles from this catalog only "
            f"(comma-separated, or NONE):\n{', '.join(catalog_roles.keys())}\n\n"
            f"Roster: {', '.join(current_roster_names)}\n"
            f"Requirements:\n{project_requirements}\n"
        )
        msg = Message(sender="hr_ops", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        text = (resp.content or "").strip()
        if not text or text.upper().startswith("NONE"):
            # Still merge keyword hits as safety net
            return self.analyze_skill_gaps(project_requirements, current_roster_names)

        active = {r.lower() for r in current_roster_names}
        requisitions: List[JobRequisition] = []
        for token in re.split(r"[,\n]+", text):
            role = token.strip().strip("`").lower().replace(" ", "_")
            # fuzzy match catalog keys
            match = None
            for title in catalog_roles:
                if title in role or role in title:
                    match = title
                    break
            if not match:
                continue
            if any(match in a for a in active):
                continue
            domain, info = catalog_roles[match]
            requisitions.append(
                JobRequisition(
                    role_title=info["role_title"],
                    department_type=info["department"],
                    system_prompt=info["system_prompt"],
                    required_skills=info["keywords"][:5],
                    rationale=f"LLM gap analysis selected '{domain}' for staffing",
                )
            )

        if not requisitions:
            return self.analyze_skill_gaps(project_requirements, current_roster_names)
        return requisitions

    def recruit_agent(
        self,
        requisition: JobRequisition,
        event_bus: Optional[Any] = None,
        mcp_client: Optional[Any] = None,
    ) -> BaseAgent:
        """
        Dynamically instantiate, provision, and return a newly synthesized agent.
        """
        new_agent = BaseAgent(
            name=requisition.role_title,
            role=Role.ASSISTANT,
            system_prompt=requisition.system_prompt,
            event_bus=event_bus,
            mcp_client=mcp_client,
        )

        # Record recruitment in HR episodic memory
        self.episodic_memory.record_reflection(
            task=f"Recruit specialized agent: {requisition.role_title}",
            success=True,
            critique=f"Addressed gap in {requisition.department_type.value}: {requisition.rationale}",
            suggested_strategy=f"Assign {requisition.role_title} to cross-functional squad.",
            tags=["hr", "recruitment", requisition.department_type.value],
        )

        return new_agent
