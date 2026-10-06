"""
tests/test_xops_and_company_enhancements.py: Unit tests for XOps data contract validation
and AcinonyxEnterprise strike pod assembly.
"""

import unittest
from mas.validation import validate_data_contract
from mas.organization.company import AcinonyxEnterprise
from mas.orchestration.strike_pod import LiquidStrikePod, PodStatus


class TestXOpsValidationAndCompany(unittest.TestCase):

    def test_valid_data_contract_yaml(self):
        contract_yaml = """
dataset: core_transactions
version: 1.0.0
owner: analytics_engineering
sla:
  freshness_hours: 1
  availability: 0.999
schema:
  - name: transaction_id
    type: STRING
    nullable: false
  - name: amount
    type: NUMERIC
    nullable: false
"""
        is_valid, reason, parsed = validate_data_contract(contract_yaml)
        self.assertTrue(is_valid, f"Expected valid data contract, got: {reason}")
        self.assertEqual(parsed["dataset"], "core_transactions")
        self.assertEqual(len(parsed["schema"]), 2)

    def test_invalid_data_contract_missing_field(self):
        contract_yaml = """
version: 1.0.0
owner: analytics_engineering
schema:
  - name: id
    type: INT64
"""
        is_valid, reason, parsed = validate_data_contract(contract_yaml)
        self.assertFalse(is_valid)
        self.assertIn("dataset", reason)

    def test_invalid_data_contract_empty_schema(self):
        contract_yaml = """
dataset: orders
version: 1.0.0
owner: sales
schema: []
"""
        is_valid, reason, parsed = validate_data_contract(contract_yaml)
        self.assertFalse(is_valid)
        self.assertIn("non-empty list", reason)

    def test_assemble_strike_pod(self):
        enterprise = AcinonyxEnterprise(name="Test Studio")
        pod = enterprise.assemble_strike_pod(
            title="Test Mission",
            requirements="Test requirements for strike pod assembly",
            required_specializations=["product_lead", "chief_architect", "qa_critic"],
        )
        self.assertIsInstance(pod, LiquidStrikePod)
        self.assertEqual(pod.status, PodStatus.INITIALIZED)
        self.assertIn("product_lead", pod.agents)
        self.assertIn("chief_architect", pod.agents)
        self.assertIn("qa_critic", pod.agents)
        self.assertEqual(len(pod.agents), 3)


if __name__ == "__main__":
    unittest.main()
