"""
Tests for mas.organization (ConsultingEnterprise, HRAgent, Departments, and ConsultingEngagement).
"""

import unittest
from mas.organization.company import ConsultingEnterprise
from mas.organization.department import DepartmentType
from mas.organization.engagement import ConsultingEngagement


class TestEnterpriseOrganization(unittest.IsolatedAsyncioTestCase):

    async def test_enterprise_initial_roster_and_departments(self):
        enterprise = ConsultingEnterprise(name="Test Consulting Firm")

        # Verify initial department count and headcount (7 original + CIOAgent = 8)
        self.assertEqual(len(enterprise.departments), len(DepartmentType))
        self.assertEqual(enterprise.get_headcount(), 8)

        roster = enterprise.get_roster()
        self.assertIn("CIOAgent", roster)
        self.assertIn("hr_director", roster)
        self.assertIn("client_director", roster)
        self.assertIn("product_lead", roster)
        self.assertIn("design_lead", roster)
        self.assertIn("senior_engineer", roster)
        self.assertIn("qa_critic", roster)
        self.assertIn("marketing_lead", roster)

        self.assertEqual(roster["CIOAgent"], "executive")
        self.assertEqual(roster["hr_director"], "human_resources")
        self.assertEqual(roster["client_director"], "client_management")
        self.assertEqual(roster["product_lead"], "product")
        self.assertEqual(roster["design_lead"], "design")
        self.assertEqual(roster["senior_engineer"], "engineering")
        self.assertEqual(roster["qa_critic"], "engineering")
        self.assertEqual(roster["marketing_lead"], "marketing")

    async def test_hr_dynamic_skill_gap_analysis_and_recruitment(self):
        enterprise = ConsultingEnterprise()
        hr = enterprise.hr_agent

        # RFP with heavy cybersecurity and HIPAA requirements
        rfp = "We need an enterprise healthcare telehealth platform with strict HIPAA compliance and vulnerability penetration audits."

        current_roster = list(enterprise.get_roster().keys())
        requisitions = hr.analyze_skill_gaps(rfp, current_roster)

        # HR should detect missing cybersecurity_auditor
        self.assertEqual(len(requisitions), 1)
        self.assertEqual(requisitions[0].role_title, "cybersecurity_auditor")
        self.assertEqual(requisitions[0].department_type, DepartmentType.ENGINEERING)

        # Recruit and onboard
        new_agent = hr.recruit_agent(requisitions[0], event_bus=enterprise.event_bus)
        enterprise.hire_agent(new_agent, requisitions[0].department_type)

        # Headcount should increase to 9 (8 base including CIO + 1 newly recruited)
        self.assertEqual(enterprise.get_headcount(), 9)
        self.assertIn("cybersecurity_auditor", enterprise.get_roster())
        self.assertEqual(enterprise.get_roster()["cybersecurity_auditor"], "engineering")

    async def test_full_consulting_engagement_workflow(self):
        enterprise = ConsultingEnterprise()
        engagement = ConsultingEngagement(enterprise)

        raw_rfp = (
            "We are a FinTech startup building an AI-powered automated ledger reconciliation SaaS. "
            "We need Stripe payment gateway integration, PCI-DSS compliance, and vector embeddings for anomaly detection."
        )

        initial_headcount = enterprise.get_headcount()
        artifacts = await engagement.execute_engagement(
            client_name="Apex Financial Technologies",
            raw_rfp=raw_rfp,
        )

        # Verify artifacts across all departments
        self.assertEqual(artifacts.client_name, "Apex Financial Technologies")
        self.assertTrue(len(artifacts.client_brief) > 0)
        self.assertTrue(len(artifacts.prd) > 0)
        self.assertTrue(len(artifacts.design_system) > 0)
        self.assertTrue(len(artifacts.engineering_summary) > 0)
        self.assertTrue(len(artifacts.gtm_package) > 0)
        self.assertTrue(len(artifacts.delivery_signoff) > 0)

        # Verify HR gap detection and dynamic hiring
        # RFP mentioned 'fintech', 'payment', 'pci-dss', 'ai', 'vector'
        # HR should have detected gaps for fintech_compliance_officer and data_architect_ai
        self.assertGreater(len(artifacts.newly_hired_agents), 0)
        self.assertGreater(enterprise.get_headcount(), initial_headcount)

        # Verify specialist audits were performed by newly recruited agents
        for hired_agent in artifacts.newly_hired_agents:
            self.assertIn(hired_agent, artifacts.specialist_audits)

        # Verify state machine transitions
        self.assertEqual(enterprise.state_machine.get("total_engagements"), 1)
        self.assertEqual(enterprise.state_machine.get("last_completed_client"), "Apex Financial Technologies")


if __name__ == "__main__":
    unittest.main()
