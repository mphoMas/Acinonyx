"""
mas.organization.roles: Specialized departmental agent roles for a modern IT SaaS consulting company.
Architect: Acinonyx
"""

from __future__ import annotations
from mas.core.agent import BaseAgent
from mas.core.message import Message, Role


class ClientManagerAgent(BaseAgent):
    """
    Account Executive & Client Engagement Director.
    Conducts client intake, translates stakeholder RFP into project scope,
    negotiates deliverables, and manages delivery acceptance.
    """

    def __init__(self, name: str = "client_director", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.SUPERVISOR,
            system_prompt=(
                "You are the Director of Client Management. You interface directly with enterprise clients, "
                "synthesize raw business requests into structured Engagement Briefs, define SLAs, and ensure client satisfaction."
            ),
            **kwargs,
        )

    async def intake_request(self, client_name: str, raw_rfp: str) -> str:
        """Process raw client RFP and generate a structured Client Engagement Brief."""
        prompt = (
            f"Client: {client_name}\n"
            f"Raw RFP Request:\n{raw_rfp}\n\n"
            f"Task: Generate a formal Client Engagement Brief outlining:\n"
            f"1. Executive Problem Statement\n"
            f"2. Core Business Objectives & KPIs\n"
            f"3. Scope Boundaries & Constraints\n"
            f"4. Target Delivery Timeline & Deliverables"
        )
        msg = Message(sender="client", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class ProductManagerAgent(BaseAgent):
    """
    Principal Product Manager.
    Translates Client Engagement Briefs into detailed Product Requirements Documents (PRDs),
    user personas, epics, and engineering acceptance criteria.
    """

    def __init__(self, name: str = "product_lead", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Principal Product Manager. You translate strategic business requirements "
                "into exhaustive, actionable Product Requirements Documents (PRDs) with user stories and acceptance criteria."
            ),
            **kwargs,
        )

    async def draft_prd(self, client_brief: str) -> str:
        prompt = (
            f"Client Engagement Brief:\n{client_brief}\n\n"
            f"Task: Author a comprehensive Product Requirements Document (PRD) including:\n"
            f"1. Feature Breakdown & Priority (Must-Have, Should-Have, Nice-to-Have)\n"
            f"2. User Stories in standard 'As a [user], I want [action], so that [outcome]' format\n"
            f"3. Detailed Functional Acceptance Criteria (Gherkin format: Given/When/Then)\n"
            f"4. API & Integration Requirements"
        )
        msg = Message(sender="client_director", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class DesignerAgent(BaseAgent):
    """
    Lead UI/UX & Solutions Designer.
    Develops design systems, component architecture, user interaction flows,
    and responsive layout specifications.
    """

    def __init__(self, name: str = "design_lead", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Lead UI/UX and Solutions Designer. You translate product requirements "
                "into user journey maps, design tokens, component hierarchies, and responsive UI layouts."
            ),
            **kwargs,
        )

    async def create_design_system_and_flow(self, prd: str) -> str:
        prompt = (
            f"PRD Specifications:\n{prd}\n\n"
            f"Task: Create a UI/UX Specification Document detailing:\n"
            f"1. Information Architecture & Navigation Tree\n"
            f"2. Core Screen Wireframes & Component Hierarchy\n"
            f"3. Design Tokens (Color Palette, Typography, Spacing, Responsive Breakpoints)\n"
            f"4. Interactive State Matrix (Hover, Active, Error, Loading, Success)"
        )
        msg = Message(sender="product_lead", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class MarketingAgent(BaseAgent):
    """
    Head of Product Marketing & Growth.
    Designs go-to-market (GTM) strategy, value propositions, competitive positioning,
    press releases, and client pitch collateral.
    """

    def __init__(self, name: str = "marketing_lead", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Head of Product Marketing. You craft compelling value propositions, "
                "Go-To-Market (GTM) launch playbooks, competitive battlecards, and executive pitch collateral."
            ),
            **kwargs,
        )

    async def create_gtm_package(self, prd: str, client_brief: str) -> str:
        prompt = (
            f"Product PRD:\n{prd}\n\n"
            f"Client Brief Context:\n{client_brief}\n\n"
            f"Task: Create a complete Go-To-Market (GTM) Package containing:\n"
            f"1. Core Value Proposition & Positioning Statement\n"
            f"2. Target Customer Segments & ICP (Ideal Customer Profile)\n"
            f"3. Multi-Channel Launch Strategy & Messaging Hierarchy\n"
            f"4. Executive Client Pitch Deck Narrative & Case Study Summary"
        )
        msg = Message(sender="product_lead", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


# ===========================================================================
# Acinonyx Labs 10/10 Specialized Guild Agents
# ===========================================================================

class MarketResearcherAgent(BaseAgent):
    """
    Lead Market & Domain Intelligence Agent.
    Drives Phase 0 Market Research-1st discovery: competitive moats, TAM/SAM sizing,
    pricing benchmarks, customer workflow friction, and empirical demand signals.
    """

    def __init__(self, name: str = "market_researcher", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.RESEARCHER if hasattr(Role, "RESEARCHER") else Role.ASSISTANT,
            system_prompt=(
                "You are the Lead Market & Domain Intelligence Researcher for Acinonyx Labs. "
                "Your mandate is to ground every product initiative in empirical market data, "
                "rigorous competitor analysis, TAM/SAM modeling, and validated user workflow friction points."
            ),
            **kwargs,
        )

    async def conduct_market_research(self, topic_or_idea: str) -> str:
        prompt = (
            f"Target Product / Market Opportunity: {topic_or_idea}\n\n"
            f"Task: Produce a formal Phase 0 Market Intelligence Dossier outlining:\n"
            f"1. Problem Space & Customer Pain Points\n"
            f"2. Competitive Landscape & Technical Moats\n"
            f"3. Market Opportunity (TAM/SAM/SOM & Pricing Elasticity)\n"
            f"4. Core Value Proposition & Recommended MVP Feature Set\n"
            f"5. Key Technical Invariants & Execution Risks"
        )
        msg = Message(sender="mission_supervisor", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class DataEngineerAgent(BaseAgent):
    """
    Data Systems & Pipeline Architect.
    Architects high-throughput ETL/ELT data pipelines, market data ingestors,
    and structured warehouse/lakehouse models.
    """

    def __init__(self, name: str = "data_engineer", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Staff Data Systems Architect. You design automated data ingestion pipelines, "
                "telemetry streaming backbones, data schemas, and analytics warehouse architectures."
            ),
            **kwargs,
        )

    async def design_pipeline_spec(self, requirements: str) -> str:
        prompt = (
            f"Requirements:\n{requirements}\n\n"
            f"Task: Author a Data Ingestion & Pipeline Specification Document detailing:\n"
            f"1. Ingestion Sources & Streaming/Batch Protocols\n"
            f"2. Raw -> Curated Data Transformation Schemas\n"
            f"3. Storage & Partitioning Strategy\n"
            f"4. Data Quality Checks, SLA Bounds & Error Handling"
        )
        msg = Message(sender="market_researcher", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class VectorRAGArchitectAgent(BaseAgent):
    """
    Semantic Retrieval & Vector Knowledge Graph Architect.
    Manages vector embeddings, hybrid dense/sparse indexing, semantic chunking,
    and agentic context compression.
    """

    def __init__(self, name: str = "vector_rag_architect", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Vector & Semantic Retrieval Architect. You design embedding topologies, "
                "hybrid search vector indices, metadata filtering layers, and high-precision RAG pipelines."
            ),
            **kwargs,
        )

    async def design_rag_topology(self, data_sources: str) -> str:
        prompt = (
            f"Data Sources & Query Requirements:\n{data_sources}\n\n"
            f"Task: Author a Vector RAG Topology Design detailing:\n"
            f"1. Chunking Strategy & Dimensionality Profile\n"
            f"2. Embedding Model Selection & Vector Store Indexing\n"
            f"3. Hybrid Retrieval & Re-ranking Topology\n"
            f"4. Grounding Verification & Context Injection Architecture"
        )
        msg = Message(sender="systems_architect", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class BackendEngineerAgent(BaseAgent):
    """
    Principal Backend & Distributed Systems Engineer.
    Develops scalable APIs, microservices, database schemas, and asynchronous event loops.
    """

    def __init__(self, name: str = "backend_engineer", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Principal Backend Engineer. You implement clean, asynchronous, "
                "well-typed Python/FastAPI services, database models, and robust REST/gRPC interfaces."
            ),
            **kwargs,
        )

    async def implement_backend_service(self, spec: str) -> str:
        prompt = (
            f"Technical Specification:\n{spec}\n\n"
            f"Task: Author the complete production backend implementation including:\n"
            f"1. Data Models and Schemas (Pydantic / SQLModel)\n"
            f"2. API Route Handlers with Type Annotations and Error Handling\n"
            f"3. Async Database Integration & Event Publishing"
        )
        msg = Message(sender="systems_architect", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class FrontendEngineerAgent(BaseAgent):
    """
    Principal Frontend & UI/UX Engineer.
    Builds dynamic, responsive SaaS frontends, real-time observability cockpits,
    and interactive agentic workflows using modern component design systems.
    """

    def __init__(self, name: str = "frontend_engineer", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Principal Frontend Engineer. You translate design systems and user journey specs "
                "into high-performance, dynamic, accessible web interfaces and SaaS control cockpits."
            ),
            **kwargs,
        )

    async def implement_ui_spec(self, design_spec: str) -> str:
        prompt = (
            f"Design System & UI Spec:\n{design_spec}\n\n"
            f"Task: Implement the frontend component architecture, responsive layout structure, "
            f"and interactive state management."
        )
        msg = Message(sender="design_lead", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class AgentWorkflowEngineerAgent(BaseAgent):
    """
    Autonomous Agent Workflow & Orchestration Engineer.
    Designs and implements multi-agent state machines, LangGraph/MAS event loops,
    and Model Context Protocol (MCP) tool integration fabrics.
    """

    def __init__(self, name: str = "agent_workflow_engineer", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Autonomous Agent Workflow Engineer. You design multi-agent state machines, "
                "MCP tool bridges, deterministic decision graphs, and resilient Reflexion loops."
            ),
            **kwargs,
        )

    async def implement_workflow_graph(self, requirements: str) -> str:
        prompt = (
            f"Workflow Requirements:\n{requirements}\n\n"
            f"Task: Author the multi-agent workflow graph specification detailing:\n"
            f"1. Agent State Machine Nodes and Transitions\n"
            f"2. MCP Tool Registrations and Permissions\n"
            f"3. Error Recovery, Timeout Bounds & Self-Healing Reflexion Paths"
        )
        msg = Message(sender="systems_architect", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class AdversarialRedTeamAgent(BaseAgent):
    """
    Synthetic Adversary & Chaos Engineering Agent.
    Proactively attacks software, workflows, and prompts before production deployment.
    Simulates malicious users, prompt-injection exploits, fuzzing, and race conditions.
    """

    def __init__(self, name: str = "adversarial_red_team", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.CRITIC,
            system_prompt=(
                "You are the Adversarial Chaos Engineer and Red Team Lead for Acinonyx Labs. "
                "Your objective is to BREAK systems before clients touch them. You relentlessly test for "
                "prompt injection vulnerabilities, unauthorized tool escalation, state desynchronization, and edge-case crashes."
            ),
            **kwargs,
        )

    async def execute_penetration_test(self, system_spec: str, code_or_workflow: str) -> str:
        prompt = (
            f"System Spec:\n{system_spec}\n\n"
            f"Target Code / Workflow:\n{code_or_workflow}\n\n"
            f"Task: Perform a comprehensive Adversarial Penetration Audit detailing:\n"
            f"1. Prompt Injection & Jailbreak Vulnerability Vectors\n"
            f"2. State Corruption & Concurrency Race Condition Risks\n"
            f"3. Boundary Fuzzing & Malformed Input Handling\n"
            f"4. PASS/FAIL Verdict with Required Hardening Remediation"
        )
        msg = Message(sender="qa_lead", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class FinOpsGovernorAgent(BaseAgent):
    """
    FinOps & Value-per-Token Economic Governor.
    Monitors token burn, computes task ROI efficiency metrics, dynamically tunes model tiering,
    and enforces budget circuit-breakers.
    """

    def __init__(self, name: str = "finops_governor", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.SUPERVISOR,
            system_prompt=(
                "You are the FinOps & Value-per-Token Economic Governor. You enforce economic discipline, "
                "calculate task ROI metrics, optimize model tiering for margin efficiency, and prevent runaway compute burn."
            ),
            **kwargs,
        )

    async def evaluate_mission_budget(self, mission_plan: str, projected_tokens: int) -> str:
        prompt = (
            f"Mission Plan:\n{mission_plan}\n\n"
            f"Projected Token Consumption: {projected_tokens}\n\n"
            f"Task: Produce a FinOps Economic Clearance Report:\n"
            f"1. Model Routing Tier Allocation (Tier 1 vs Tier 2 vs Tier 3)\n"
            f"2. Estimated Cost & Value-per-Token Efficiency Index\n"
            f"3. Budget Clearance Decision: APPROVED / THROTTLED / REJECTED\n"
            f"4. Recommended Cost Optimization Strategies"
        )
        msg = Message(sender="mission_supervisor", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class TechnicalWriterAgent(BaseAgent):
    """
    Lead Technical Documentation Specialist.
    Authors clean, exhaustive developer documentation, interactive guides, API references,
    and architectural invariants manuals.
    """

    def __init__(self, name: str = "technical_writer", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Lead Technical Writer. You synthesize complex architectures and codebase implementations "
                "into crystal-clear developer documentation, OpenAPI specs, quickstart guides, and operational playbooks."
            ),
            **kwargs,
        )

    async def author_documentation(self, prd: str, architecture_spec: str, code_summary: str) -> str:
        prompt = (
            f"PRD:\n{prd}\n\n"
            f"Architecture:\n{architecture_spec}\n\n"
            f"Code Summary:\n{code_summary}\n\n"
            f"Task: Author the complete Developer Reference Guide containing:\n"
            f"1. System Architecture Overview & Component Diagram\n"
            f"2. Getting Started & Local Environment Setup\n"
            f"3. API Reference & Request/Response Contracts\n"
            f"4. Troubleshooting Guide & Invariant Rules"
        )
        msg = Message(sender="product_lead", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content


class DevAdvocateAgent(BaseAgent):
    """
    Developer Relations & Community Ecosystem Advocate.
    Builds open-source demos, sample workflows, interactive sandboxes, and developer feedback loops.
    """

    def __init__(self, name: str = "dev_advocate", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Developer Relations Advocate. You craft engaging developer tutorials, "
                "interactive code sandboxes, and sample agentic workflow templates for the open developer ecosystem."
            ),
            **kwargs,
        )

    async def create_developer_starter_kit(self, product_summary: str, api_spec: str) -> str:
        prompt = (
            f"Product Summary:\n{product_summary}\n\n"
            f"API Specification:\n{api_spec}\n\n"
            f"Task: Create a complete Developer Starter Kit containing:\n"
            f"1. 5-Minute Quickstart Code Snippet\n"
            f"2. Realistic End-to-End Sample Workflow\n"
            f"3. Interactive CLI Example\n"
            f"4. Developer FAQ and Best Practices"
        )
        msg = Message(sender="marketing_lead", recipient=self.name, role=Role.USER, content=prompt)
        resp = await self.step(msg)
        return resp.content
