"""
mas.organization.engagement: End-to-end enterprise consulting engagement workflow.
Architect: Acinonyx
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from mas.core.message import Message, MessageMetadata
from mas.organization.company import ConsultingEnterprise
from mas.organization.hr import JobRequisition


@dataclass
class EngagementArtifacts:
    client_name: str
    client_brief: str = ""
    job_requisitions: List[JobRequisition] = field(default_factory=list)
    newly_hired_agents: List[str] = field(default_factory=list)
    prd: str = ""
    design_system: str = ""
    specialist_audits: Dict[str, str] = field(default_factory=dict)
    engineering_summary: str = ""
    gtm_package: str = ""
    delivery_signoff: str = ""


class ConsultingEngagement:
    """
    Coordinates an end-to-end consulting engagement across all company departments:
    Client Intake -> HR Gap Analysis & Dynamic Recruitment -> Product -> Design -> Specialist Audit -> Engineering -> Marketing -> Delivery.
    """

    def __init__(self, enterprise: ConsultingEnterprise) -> None:
        self.enterprise = enterprise

    async def execute_engagement(
        self,
        client_name: str,
        raw_rfp: str,
    ) -> EngagementArtifacts:
        artifacts = EngagementArtifacts(client_name=client_name)
        self.enterprise.state_machine.set("current_client", client_name)

        is_live = self.enterprise.is_live_dispatch_enabled()
        dispatch_status = "ARMED (Live Execution)" if is_live else "STAGED (Preview / Dry-Run)"

        # Broadcast engagement start with explicit dispatch status
        start_msg = Message(
            sender="governance",
            recipient="broadcast",
            content=f"[DISPATCH GATE] Engagement initiated for '{client_name}'. Operational Mode: {dispatch_status}",
            metadata=MessageMetadata(topic="org:broadcast"),
        )
        await self.enterprise.event_bus.publish(start_msg)

        # ---------------------------------------------------------------------
        # Phase 1: Client Intake (Client Management)
        # ---------------------------------------------------------------------
        artifacts.client_brief = await self.enterprise.client_director.intake_request(
            client_name=client_name,
            raw_rfp=raw_rfp,
        )
        self.enterprise.state_machine.commit_checkpoint(f"intake_{client_name}")

        # ---------------------------------------------------------------------
        # Phase 2: HR Skill Gap Analysis & Dynamic Staffing (Human Resources)
        # ---------------------------------------------------------------------
        current_roster = list(self.enterprise.get_roster().keys())
        if hasattr(self.enterprise.hr_agent, "analyze_skill_gaps_async"):
            requisitions = await self.enterprise.hr_agent.analyze_skill_gaps_async(
                project_requirements=raw_rfp + " " + artifacts.client_brief,
                current_roster_names=current_roster,
            )
        else:
            requisitions = self.enterprise.hr_agent.analyze_skill_gaps(
                project_requirements=raw_rfp + " " + artifacts.client_brief,
                current_roster_names=current_roster,
            )
        artifacts.job_requisitions = requisitions

        # Dynamically hire missing roles and onboard into appropriate departments
        for req in requisitions:
            new_agent = self.enterprise.hr_agent.recruit_agent(
                requisition=req,
                event_bus=self.enterprise.event_bus,
                mcp_client=self.enterprise.mcp_client,
            )
            self.enterprise.hire_agent(new_agent, req.department_type)
            artifacts.newly_hired_agents.append(new_agent.name)

        self.enterprise.state_machine.commit_checkpoint(f"staffed_{client_name}")

        # ---------------------------------------------------------------------
        # Phase 3: Product Scoping & Requirements (Product)
        # ---------------------------------------------------------------------
        artifacts.prd = await self.enterprise.product_lead.draft_prd(
            client_brief=artifacts.client_brief,
        )
        self.enterprise.state_machine.commit_checkpoint(f"prd_{client_name}")

        # ---------------------------------------------------------------------
        # Phase 4: UI/UX & Solution Design (Design)
        # ---------------------------------------------------------------------
        artifacts.design_system = await self.enterprise.design_lead.create_design_system_and_flow(
            prd=artifacts.prd,
        )
        self.enterprise.state_machine.commit_checkpoint(f"design_{client_name}")

        # ---------------------------------------------------------------------
        # Phase 5: Specialized Domain Audit (Newly Hired Agents)
        # ---------------------------------------------------------------------
        for agent_name in artifacts.newly_hired_agents:
            agent = None
            for dept in self.enterprise.departments.values():
                if agent_name in dept.members:
                    agent = dept.members[agent_name]
                    break

            if agent:
                audit_prompt = (
                    f"Perform domain expert review and compliance/architecture audit of the project:\n"
                    f"PRD Excerpt:\n{artifacts.prd[:500]}...\n\n"
                    f"Design Excerpt:\n{artifacts.design_system[:500]}...\n"
                    f"Provide domain-specific audit findings and critical safeguards."
                )
                audit_msg = Message(sender="project_director", recipient=agent.name, content=audit_prompt)
                audit_resp = await agent.step(audit_msg)
                artifacts.specialist_audits[agent.name] = audit_resp.content

        # ---------------------------------------------------------------------
        # Phase 6: Engineering Synthesis & QA (Engineering)
        # ---------------------------------------------------------------------
        eng_prompt = (
            f"Review PRD and Design for implementation:\n"
            f"PRD: {artifacts.prd[:300]}...\n"
            f"Design: {artifacts.design_system[:300]}...\n"
            f"Generate implementation status and core API module summary."
        )
        eng_msg = Message(sender="product_lead", recipient=self.enterprise.lead_engineer.name, content=eng_prompt)
        eng_resp = await self.enterprise.lead_engineer.step(eng_msg)
        artifacts.engineering_summary = eng_resp.content

        # ---------------------------------------------------------------------
        # Phase 7: Go-To-Market Package (Marketing)
        # ---------------------------------------------------------------------
        artifacts.gtm_package = await self.enterprise.marketing_lead.create_gtm_package(
            prd=artifacts.prd,
            client_brief=artifacts.client_brief,
        )

        # ---------------------------------------------------------------------
        # Phase 8: Client Delivery & Executive Sign-off (Client Management)
        # ---------------------------------------------------------------------
        delivery_msg = Message(
            sender="enterprise",
            recipient=self.enterprise.client_director.name,
            content=(
                f"Package all deliverables for client '{client_name}':\n"
                f"- PRD, Design Specs, Engineering Core, GTM Strategy, and Specialist Audits.\n"
                f"Issue formal Executive Delivery Acceptance Sign-off."
            ),
        )
        delivery_resp = await self.enterprise.client_director.step(delivery_msg)
        artifacts.delivery_signoff = (
            f"{delivery_resp.content}\n\n"
            f"--- Governance Security Verification ---\n"
            f"• Dispatch Safety Switch: {dispatch_status}\n"
            f"• Allowed Project Root: {self.enterprise.state_machine.get('allowed_projects')}\n"
            f"• Verified by Acinonyx Governance Engine"
        )

        # Update corporate state
        self.enterprise.state_machine.update({
            "last_completed_client": client_name,
            "total_engagements": self.enterprise.state_machine.get("total_engagements", 0) + 1,
            "current_headcount": self.enterprise.get_headcount(),
        })

        return artifacts
