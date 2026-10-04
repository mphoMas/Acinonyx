"""
mas.organization.company: Enterprise container for an IT SaaS Consulting Company.
Architect: Acinonyx
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from mas.core.agent import BaseAgent
from mas.core.event_bus import EventBus
from mas.core.state import StateMachine
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.organization.department import Department, DepartmentType, Guild, GuildType
from mas.organization.hr import HRAgent
from mas.organization.roles import (
    ClientManagerAgent,
    DesignerAgent,
    MarketingAgent,
    ProductManagerAgent,
    MarketResearcherAgent,
    DataEngineerAgent,
    VectorRAGArchitectAgent,
    BackendEngineerAgent,
    FrontendEngineerAgent,
    AgentWorkflowEngineerAgent,
    AdversarialRedTeamAgent,
    FinOpsGovernorAgent,
    TechnicalWriterAgent,
    DevAdvocateAgent,
)
from mas.organization.executive import CIOAgent
from mas.squad.squad import ArchitectAgent, EngineerAgent, QAAgent
from mas.tools.executor import register_default_tools
from mas.tools.filesystem import register_filesystem_tools
from mas.tools.git_tool import register_git_tools
from mas.tools.package_tool import register_package_tools
from mas.tools.browser_tool import register_browser_tools


class ConsultingEnterprise:
    """
    Enterprise container modeling a modern IT SaaS consulting company.
    Encompasses Executive, HR, Client Management, Product, Design, Engineering, and Marketing.
    """

    def __init__(
        self,
        name: str = "Acinonyx Consulting Group (ACG)",
        enable_live_dispatch: Optional[bool] = None,
        allowed_projects: Optional[List[str]] = None,
    ) -> None:
        import os
        self.name = name
        self.event_bus = EventBus(log_history=True)

        # Dispatch interlock: defaults to environment variable or False (safe default)
        dispatch_val = (
            enable_live_dispatch
            if enable_live_dispatch is not None
            else os.environ.get("MAS_ENABLE_LIVE_DISPATCH", "false").lower() in ("true", "1", "yes")
        )

        projects = allowed_projects or [
            "/home/acinonyx/Desktop/MAS/workspace/projects",
            "/srv/mas-projects/acceptance",
        ]

        self.state_machine = StateMachine({
            "company_status": "active",
            "total_engagements": 0,
            "live_dispatch_enabled": dispatch_val,
            "allowed_projects": projects,
        })

        # Initialize MCP Tooling Fabric
        self.mcp_registry = MCPRegistry()
        register_default_tools(self.mcp_registry)
        register_filesystem_tools(self.mcp_registry)
        register_git_tools(self.mcp_registry)
        register_package_tools(self.mcp_registry)
        register_browser_tools(self.mcp_registry)
        self._register_default_prompts()
        self.mcp_client = MCPClient(self.mcp_registry)

        # Initialize Departments
        self.departments: Dict[DepartmentType, Department] = {
            dept_type: Department(dept_type=dept_type)
            for dept_type in DepartmentType
        }

        # Initialize Core Staff
        self.hr_agent = HRAgent(mcp_client=self.mcp_client)
        self.cio = CIOAgent(mcp_client=self.mcp_client)
        self.client_director = ClientManagerAgent(mcp_client=self.mcp_client)
        self.product_lead = ProductManagerAgent(mcp_client=self.mcp_client)
        self.design_lead = DesignerAgent(mcp_client=self.mcp_client)
        self.lead_engineer = EngineerAgent(mcp_client=self.mcp_client)
        self.qa_critic = QAAgent(mcp_client=self.mcp_client)
        self.marketing_lead = MarketingAgent(mcp_client=self.mcp_client)

        # Onboard Core Staff to Departments and Event Bus
        self._onboard_initial_staff()

    def _register_default_prompts(self) -> None:
        async def engagement_brief(client: str = "client", rfp: str = "") -> str:
            return (
                f"Draft a structured engagement brief for {client}.\n"
                f"RFP excerpt:\n{rfp}\n"
                "Include problem statement, KPIs, scope, and deliverables."
            )

        async def architecture_review(requirements: str = "") -> str:
            return (
                "You are the Lead Architect. Produce interfaces, invariants, "
                f"and a file hierarchy for:\n{requirements}"
            )

        self.mcp_registry.register_prompt(
            "engagement_brief",
            "Client engagement briefing prompt",
            engagement_brief,
            [{"name": "client"}, {"name": "rfp"}],
        )
        self.mcp_registry.register_prompt(
            "architecture_review",
            "Architecture review prompt",
            architecture_review,
            [{"name": "requirements"}],
        )

    def _onboard_initial_staff(self) -> None:
        initial_placements = [
            (self.cio, DepartmentType.EXECUTIVE),
            (self.hr_agent, DepartmentType.HUMAN_RESOURCES),
            (self.client_director, DepartmentType.CLIENT_MANAGEMENT),
            (self.product_lead, DepartmentType.PRODUCT),
            (self.design_lead, DepartmentType.DESIGN),
            (self.lead_engineer, DepartmentType.ENGINEERING),
            (self.qa_critic, DepartmentType.ENGINEERING),
            (self.marketing_lead, DepartmentType.MARKETING),
        ]

        for agent, dept_type in initial_placements:
            self.hire_agent(agent, dept_type)

    def attach_llm_provider(self, provider: Any) -> None:
        """Connect all enterprise agents across all departments to a live LLM provider."""
        self.llm_provider = provider
        for dept in self.departments.values():
            for agent in dept.members.values():
                agent.llm_provider = provider

    def hire_agent(self, agent: BaseAgent, dept_type: DepartmentType) -> None:
        """Onboard an agent into the company, assign department, and attach to corporate event bus."""
        dept = self.departments[dept_type]
        dept.add_agent(agent)
        if hasattr(self, "llm_provider") and self.llm_provider:
            agent.llm_provider = self.llm_provider
        agent.attach_event_bus(self.event_bus, topic=f"org:{dept_type.value}")
        # Also listen to company broadcast
        self.event_bus.subscribe(agent.name, agent._on_bus_message, topic="org:broadcast")

    def get_roster(self) -> Dict[str, str]:
        """Return directory of all active agents mapped to their department."""
        roster = {}
        for dept_type, dept in self.departments.items():
            for agent_name in dept.list_agents():
                roster[agent_name] = dept_type.value
        return roster

    def get_headcount(self) -> int:
        return sum(d.headcount for d in self.departments.values())

    def enable_live_dispatch(self) -> None:
        """Arm the live dispatch switch allowing active model calls and execution."""
        self.state_machine.set("live_dispatch_enabled", True)

    def disable_live_dispatch(self) -> None:
        """Disarm the live dispatch switch, placing squads in preview/staging mode."""
        self.state_machine.set("live_dispatch_enabled", False)

    def is_live_dispatch_enabled(self) -> bool:
        """Check if live dispatch is currently armed."""
        return bool(self.state_machine.get("live_dispatch_enabled", False))

    def register_project_path(self, path: str) -> None:
        """Register an authorized project root for agent operations."""
        import os
        norm = os.path.abspath(path)
        projects = list(self.state_machine.get("allowed_projects", []))
        if norm not in projects:
            projects.append(norm)
            self.state_machine.set("allowed_projects", projects)

    def is_path_allowed(self, path: str) -> bool:
        """Check if a file or directory path falls within an authorized project jail."""
        import os
        norm = os.path.abspath(path)
        allowed = self.state_machine.get("allowed_projects", [])
        return any(norm.startswith(os.path.abspath(proj)) for proj in allowed)


class AcinonyxEnterprise(ConsultingEnterprise):
    """
    Acinonyx Labs 10/10 Masterwork Enterprise Runtime.
    Houses the 7 Capability Guilds and provisions the full suite of specialized agents:
    - Executive & Strategy (CIO, HR, Chief Architect)
    - Research & Product (Market Research Lead, Product Lead, Design Lead)
    - Data & AI (Data Engineer, Vector/RAG Architect)
    - Software Engineering (Backend, Frontend, Agent Workflow, Senior Engineer)
    - Independent QA & Verification (QA Critic, Adversarial Chaos Red Team)
    - Platform & Security (FinOps Governor, Security SRE)
    - Growth & GTM (Marketing Lead, Technical Writer, Developer Advocate)
    """

    def __init__(
        self,
        name: str = "Acinonyx Labs (Autonomous SaaS Studio)",
        enable_live_dispatch: Optional[bool] = None,
        allowed_projects: Optional[List[str]] = None,
    ) -> None:
        super().__init__(
            name=name,
            enable_live_dispatch=enable_live_dispatch,
            allowed_projects=allowed_projects,
        )

        # 1. Initialize v2.0 Specialized Agents
        self.chief_architect = ArchitectAgent(mcp_client=self.mcp_client, name="chief_architect")
        self.market_researcher = MarketResearcherAgent(mcp_client=self.mcp_client)
        self.data_engineer = DataEngineerAgent(mcp_client=self.mcp_client)
        self.vector_rag_architect = VectorRAGArchitectAgent(mcp_client=self.mcp_client)
        self.backend_engineer = BackendEngineerAgent(mcp_client=self.mcp_client)
        self.frontend_engineer = FrontendEngineerAgent(mcp_client=self.mcp_client)
        self.agent_workflow_engineer = AgentWorkflowEngineerAgent(mcp_client=self.mcp_client)
        self.adversarial_red_team = AdversarialRedTeamAgent(mcp_client=self.mcp_client)
        self.finops_governor = FinOpsGovernorAgent(mcp_client=self.mcp_client)
        self.technical_writer = TechnicalWriterAgent(mcp_client=self.mcp_client)
        self.dev_advocate = DevAdvocateAgent(mcp_client=self.mcp_client)

        # 2. Onboard Specialized Agents into their Capability Guilds
        self._onboard_guild_staff()

    def _onboard_guild_staff(self) -> None:
        guild_placements = [
            (self.chief_architect, DepartmentType.EXECUTIVE),
            (self.market_researcher, DepartmentType.RESEARCH_PRODUCT),
            (self.data_engineer, DepartmentType.DATA_AI),
            (self.vector_rag_architect, DepartmentType.DATA_AI),
            (self.backend_engineer, DepartmentType.SOFTWARE_DEV),
            (self.frontend_engineer, DepartmentType.SOFTWARE_DEV),
            (self.agent_workflow_engineer, DepartmentType.SOFTWARE_DEV),
            (self.adversarial_red_team, DepartmentType.QA_VERIFICATION),
            (self.finops_governor, DepartmentType.PLATFORM_SECURITY),
            (self.technical_writer, DepartmentType.GROWTH_GTM),
            (self.dev_advocate, DepartmentType.GROWTH_GTM),
        ]

        for agent, guild_type in guild_placements:
            self.hire_agent(agent, guild_type)

    def get_guild(self, guild_type: DepartmentType) -> Department:
        """Retrieve a specific Capability Guild."""
        return self.departments[guild_type]

    def list_guild_agents(self, guild_type: DepartmentType) -> List[str]:
        """List all active agent names within a specific Capability Guild."""
        return self.departments[guild_type].list_agents()
