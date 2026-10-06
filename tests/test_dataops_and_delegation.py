"""
tests.test_dataops_and_delegation: Unit and integration tests for Enterprise BigQuery,
Data Contract Validation, GCS Storage, and Dynamic Multi-Agent Delegation tools.
"""

import os
import unittest
from mas.capabilities import capability_matrix
from mas.mcp.protocol import MCPRegistry
from mas.tools.bigquery_tool import (
    bigquery_dry_run_tool,
    bigquery_query_run_tool,
    register_bigquery_tools,
)
from mas.tools.data_contract_tool import (
    data_contract_validate_tool,
    register_data_contract_tools,
)
from mas.tools.delegation_tool import (
    GLOBAL_DELEGATION_DISPATCHER,
    delegate_subtask_tool,
    register_delegation_tools,
)
from mas.tools.storage_tool import (
    gcs_list_objects_tool,
    gcs_read_text_tool,
    register_storage_tools,
)


class TestBigQueryFinOpsTools(unittest.TestCase):
    def test_bigquery_dry_run_syntax(self):
        query = "SELECT 1 as id, 'Acinonyx' as name, CURRENT_TIMESTAMP() as ts;"
        res = bigquery_dry_run_tool(query)
        self.assertTrue(res["success"])
        self.assertTrue(res["valid"])
        self.assertIn("bytes_processed", res)
        self.assertIn("estimated_cost_usd", res)

    def test_bigquery_dry_run_invalid_sql(self):
        query = "SELEECT BROKEN FROM NOT_A_TABLE WHERE ;;"
        res = bigquery_dry_run_tool(query)
        self.assertFalse(res["valid"])
        self.assertIn("error", res)

    def test_bigquery_query_execution(self):
        query = "SELECT 100 as num, 'verified' as tag;"
        res = bigquery_query_run_tool(query, max_rows=10)
        self.assertTrue(res["success"])
        self.assertIn("rows", res)
        self.assertTrue(len(res["rows"]) >= 1)
        self.assertEqual(res["rows"][0]["num"], "100")


class TestDataContractValidation(unittest.TestCase):
    def setUp(self):
        self.contract_path = "/home/acinonyx/Desktop/MAS/templates/data-contract.template.yml"

    def test_contract_syntax_verification(self):
        res = data_contract_validate_tool(self.contract_path)
        self.assertTrue(res["success"])
        self.assertTrue(res["passed"])
        self.assertEqual(res["dataset"], "core_transactions_mart")
        self.assertIn("transaction_id", res["schema_columns"])

    def test_contract_valid_records_pass(self):
        valid_records = [
            {
                "transaction_id": "tx_001",
                "client_id": "client_abc",
                "transaction_timestamp": "2026-10-06T10:00:00Z",
                "amount": "1500.50",
                "currency_code": "ZAR",
                "status": "SETTLED",
                "ingestion_timestamp": "2026-10-06T10:05:00Z",
            },
            {
                "transaction_id": "tx_002",
                "client_id": "client_xyz",
                "transaction_timestamp": "2026-10-06T10:01:00Z",
                "amount": "-250.00",
                "currency_code": "ZAR",
                "status": "PENDING",
                "ingestion_timestamp": "2026-10-06T10:05:00Z",
            },
        ]
        res = data_contract_validate_tool(self.contract_path, data=valid_records)
        self.assertTrue(res["success"])
        self.assertTrue(res["passed"])
        self.assertEqual(res["failed_checks"], 0)

    def test_contract_violations_detected(self):
        invalid_records = [
            {
                "transaction_id": "tx_001",
                "client_id": "client_abc",
                "transaction_timestamp": "2026-10-06T10:00:00Z",
                "amount": "",  # Violation: nullable=false but empty/null
                "currency_code": "ZAR",
                "status": "INVALID_STATUS_CODE",  # Violation: not in enum
                "ingestion_timestamp": "2026-10-06T10:05:00Z",
            },
            {
                "transaction_id": "tx_001",  # Violation: duplicate primary key
                "client_id": "client_def",
                "transaction_timestamp": "2026-10-06T10:02:00Z",
                "amount": "50.00",
                "currency_code": "USD",
                "status": "FAILED",
                "ingestion_timestamp": "2026-10-06T10:05:00Z",
            },
        ]
        res = data_contract_validate_tool(self.contract_path, data=invalid_records)
        self.assertTrue(res["success"])
        self.assertFalse(res["passed"])
        self.assertTrue(res["failed_checks"] >= 2)
        self.assertTrue(len(res["violations"]) >= 2)


class TestGCSStorageTools(unittest.TestCase):
    def test_gcs_list_objects(self):
        res = gcs_list_objects_tool("gs://bmm-metro-mz-stage")
        self.assertIn("success", res)
        self.assertIn("items", res)

    def test_gcs_read_text_invalid_uri(self):
        res = gcs_read_text_tool("http://not-gcs.com/file.txt")
        self.assertFalse(res["success"])
        self.assertIn("error", res)


class TestAgentDelegationTool(unittest.TestCase):
    def test_delegate_subtask_to_engineer(self):
        import asyncio
        res = asyncio.run(delegate_subtask_tool(
            target_role="engineer",
            task="Refactor SQL window function for 30-day rolling client spend.",
        ))
        self.assertTrue(res["success"])
        self.assertEqual(res["target_role"], "engineer")
        self.assertIn("Engineer Agent", res["result"])

    def test_custom_role_handler_registration(self):
        import asyncio
        GLOBAL_DELEGATION_DISPATCHER.register_role_handler(
            "custom_finops",
            lambda task, ctx: f"FinOps approved: cost of {task} is below $0.05",
        )
        res = asyncio.run(delegate_subtask_tool(
            target_role="custom_finops",
            task="Large table query scan",
        ))
        self.assertTrue(res["success"])
        self.assertIn("FinOps approved", res["result"])


class TestMCPRegistryAndCapabilitiesIntegration(unittest.TestCase):
    def test_mcp_registration_all_new_tools(self):
        registry = MCPRegistry()
        register_bigquery_tools(registry)
        register_data_contract_tools(registry)
        register_storage_tools(registry)
        register_delegation_tools(registry)

        tool_names = set(registry.tools.keys())
        expected = {
            "bigquery_dry_run",
            "bigquery_query_run",
            "data_contract_validate",
            "gcs_list_objects",
            "gcs_read_text",
            "delegate_subtask",
        }
        self.assertTrue(expected.issubset(tool_names), f"Missing tools: {expected - tool_names}")

    def test_capability_matrix_updated(self):
        matrix = capability_matrix()
        for cap in ["bigquery_finops_sql", "data_contract_validator", "gcs_storage_manager", "agent_to_agent_delegation"]:
            self.assertIn(cap, matrix, f"Missing capability: {cap}")
            self.assertEqual(matrix[cap]["status"], "implemented")


if __name__ == "__main__":
    unittest.main()
