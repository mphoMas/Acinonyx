"""
tests/test_v2_organization.py: Verification suite for Acinonyx Labs v2.0 (10/10) Architecture.
Tests 7 Capability Guilds, 10 specialized agent roles, AcinonyxEnterprise, and HR recruiting.
"""

import asyncio
import unittest
from mas.organization.department import DepartmentType, GuildType, Department, Guild
from mas.organization.company import AcinonyxEnterprise, ConsultingEnterprise
from mas.organization.roles import (
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
from mas.organization.hr import HRAgent


class TestV2OrganizationArchitecture(unittest.IsolatedAsyncioTestCase):

    def test_guild_types_and_aliases(self):
        """Verify the 7 capability guilds exist and alias properly."""
        expected_guilds = [
            "executive",
            "research_product",
            "data_ai",
            "software_dev",
            "qa_verification",
            "platform_security",
            "growth_gtm",
        ]
        for eg in expected_guilds:
            self.assertIn(eg, [gt.value for gt in GuildType])

        self.assertIs(GuildType, DepartmentType)
        self.assertIs(Guild, Department)

    def test_specialized_agents_instantiation(self):
        """Verify all 10 specialized agents can be instantiated with appropriate defaults."""
        agents = [
            MarketResearcherAgent(),
            DataEngineerAgent(),
            VectorRAGArchitectAgent(),
            BackendEngineerAgent(),
            FrontendEngineerAgent(),
            AgentWorkflowEngineerAgent(),
            AdversarialRedTeamAgent(),
            FinOpsGovernorAgent(),
            TechnicalWriterAgent(),
            DevAdvocateAgent(),
        ]
        for agent in agents:
            self.assertTrue(len(agent.name) > 0)
            self.assertTrue(len(agent.system_prompt) > 20)

    async def test_specialized_agent_methods_pass_through(self):
        """Verify specialized agent methods execute and produce output (in deterministic pass-through mode)."""
        market_agent = MarketResearcherAgent()
        res = await market_agent.conduct_market_research("Autonomous Agent SaaS")
        self.assertIn("Market Opportunity", res)

        backend_agent = BackendEngineerAgent()
        res_backend = await backend_agent.implement_backend_service("REST API for user authentication")
        self.assertIn("Technical Specification", res_backend)

        red_team = AdversarialRedTeamAgent()
        res_red = await red_team.execute_penetration_test("Agent workflow", "code_sample")
        self.assertIn("Adversarial Penetration Audit", res_red)

        finops = FinOpsGovernorAgent()
        res_finops = await finops.evaluate_mission_budget("Phase 0 & 1 execution", 50000)
        self.assertIn("FinOps Economic Clearance Report", res_finops)

    def test_acinonyx_enterprise_initialization(self):
        """Verify AcinonyxEnterprise pre-provisions all 7 guilds and specialized agents."""
        enterprise = AcinonyxEnterprise()

        # Check total headcount (8 original core + 11 v2 guild staff)
        self.assertGreaterEqual(enterprise.get_headcount(), 15)

        # Verify key specialized agents exist as attributes
        self.assertIsInstance(enterprise.market_researcher, MarketResearcherAgent)
        self.assertIsInstance(enterprise.data_engineer, DataEngineerAgent)
        self.assertIsInstance(enterprise.vector_rag_architect, VectorRAGArchitectAgent)
        self.assertIsInstance(enterprise.backend_engineer, BackendEngineerAgent)
        self.assertIsInstance(enterprise.frontend_engineer, FrontendEngineerAgent)
        self.assertIsInstance(enterprise.agent_workflow_engineer, AgentWorkflowEngineerAgent)
        self.assertIsInstance(enterprise.adversarial_red_team, AdversarialRedTeamAgent)
        self.assertIsInstance(enterprise.finops_governor, FinOpsGovernorAgent)
        self.assertIsInstance(enterprise.technical_writer, TechnicalWriterAgent)
        self.assertIsInstance(enterprise.dev_advocate, DevAdvocateAgent)

        # Verify guild placements
        dev_guild = enterprise.get_guild(DepartmentType.SOFTWARE_DEV)
        self.assertIn("backend_engineer", dev_guild.list_agents())
        self.assertIn("frontend_engineer", dev_guild.list_agents())
        self.assertIn("agent_workflow_engineer", dev_guild.list_agents())

        qa_guild = enterprise.get_guild(DepartmentType.QA_VERIFICATION)
        self.assertIn("adversarial_red_team", qa_guild.list_agents())

        data_guild = enterprise.get_guild(DepartmentType.DATA_AI)
        self.assertIn("data_engineer", data_guild.list_agents())
        self.assertIn("vector_rag_architect", data_guild.list_agents())

    def test_hr_recruiting_new_domains(self):
        """Verify HRAgent skill gap analysis detects new 10/10 domains."""
        hr = HRAgent()
        current_roster = ["product_lead", "lead_engineer"]

        brief = "We need market research for a new SaaS product with chaos red team penetration and finops token budget optimization."
        gaps = hr.analyze_skill_gaps(brief, current_roster)
        gap_titles = [g.role_title for g in gaps]

        self.assertIn("market_researcher", gap_titles)
        self.assertIn("adversarial_red_team", gap_titles)
        self.assertIn("finops_governor", gap_titles)

        # Test dynamic recruiting of one of the gaps
        red_team_req = next(g for g in gaps if g.role_title == "adversarial_red_team")
        new_agent = hr.recruit_agent(red_team_req)
        self.assertEqual(new_agent.name, "adversarial_red_team")


if __name__ == "__main__":
    unittest.main()
