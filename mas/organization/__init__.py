"""
mas.organization: Modern IT SaaS Consulting Enterprise multi-agent organizational structure.
"""

from mas.organization.department import Department, DepartmentType
from mas.organization.roles import (
    ClientManagerAgent,
    ProductManagerAgent,
    DesignerAgent,
    MarketingAgent,
)
from mas.organization.hr import HRAgent, JobRequisition
from mas.organization.company import ConsultingEnterprise
from mas.organization.engagement import ConsultingEngagement, EngagementArtifacts

__all__ = [
    "Department",
    "DepartmentType",
    "ClientManagerAgent",
    "ProductManagerAgent",
    "DesignerAgent",
    "MarketingAgent",
    "HRAgent",
    "JobRequisition",
    "ConsultingEnterprise",
    "ConsultingEngagement",
    "EngagementArtifacts",
]
