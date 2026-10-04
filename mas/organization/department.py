"""
mas.organization.department: Departmental structures and domain classifications for enterprise MAS.
Architect: Acinonyx
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional
from mas.core.agent import BaseAgent


class DepartmentType(str, Enum):
    # Core Legacy & Compatibility Departments
    EXECUTIVE = "executive"
    CLIENT_MANAGEMENT = "client_management"
    PRODUCT = "product"
    DESIGN = "design"
    ENGINEERING = "engineering"
    MARKETING = "marketing"
    HUMAN_RESOURCES = "human_resources"

    # Acinonyx Labs v2.0 Capability Guilds
    RESEARCH_PRODUCT = "research_product"
    DATA_AI = "data_ai"
    SOFTWARE_DEV = "software_dev"
    QA_VERIFICATION = "qa_verification"
    PLATFORM_SECURITY = "platform_security"
    GROWTH_GTM = "growth_gtm"


# Semantic Aliases for the 10/10 Architecture
GuildType = DepartmentType


class Department:
    """
    Departmental container managing a cluster of specialized agents,
    workload distribution, and domain-specific communication.
    """

    def __init__(self, dept_type: DepartmentType, description: str = "") -> None:
        self.dept_type = dept_type
        self.description = description
        self.members: Dict[str, BaseAgent] = {}

    def add_agent(self, agent: BaseAgent) -> None:
        """Register an agent into the department."""
        self.members[agent.name] = agent

    def remove_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Remove an agent from the department."""
        return self.members.pop(agent_name, None)

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        return self.members.get(agent_name)

    def list_agents(self) -> List[str]:
        return list(self.members.keys())

    @property
    def headcount(self) -> int:
        return len(self.members)


# Semantic Alias for 10/10 Liquid Architecture
Guild = Department
