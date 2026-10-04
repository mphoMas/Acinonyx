"""
mas.organization: Modern IT SaaS Consulting Enterprise multi-agent organizational structure.
"""

from mas.organization.department import Department, DepartmentType, Guild, GuildType
from mas.organization.roles import (
    ClientManagerAgent,
    ProductManagerAgent,
    DesignerAgent,
    MarketingAgent,
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
from mas.organization.hr import HRAgent, JobRequisition
from mas.organization.company import ConsultingEnterprise, AcinonyxEnterprise
from mas.organization.engagement import ConsultingEngagement, EngagementArtifacts

__all__ = [
    "Department",
    "DepartmentType",
    "Guild",
    "GuildType",
    "ClientManagerAgent",
    "ProductManagerAgent",
    "DesignerAgent",
    "MarketingAgent",
    "MarketResearcherAgent",
    "DataEngineerAgent",
    "VectorRAGArchitectAgent",
    "BackendEngineerAgent",
    "FrontendEngineerAgent",
    "AgentWorkflowEngineerAgent",
    "AdversarialRedTeamAgent",
    "FinOpsGovernorAgent",
    "TechnicalWriterAgent",
    "DevAdvocateAgent",
    "HRAgent",
    "JobRequisition",
    "ConsultingEnterprise",
    "AcinonyxEnterprise",
    "ConsultingEngagement",
    "EngagementArtifacts",
]
