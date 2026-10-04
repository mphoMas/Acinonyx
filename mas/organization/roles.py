"""
mas.organization.roles: Specialized departmental agent roles for a modern IT SaaS consulting company.
Architect: Acinonyx
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from mas.core.agent import BaseAgent
from mas.core.message import ContentType, Message, MessageMetadata, Role


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
