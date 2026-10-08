"""
tests/test_gitops_ci.py: Unit and Integration tests for GitOps CI/CD Pipeline Automation.
Tests workflow generation, dispatch simulation, local CI execution, and EventBus telemetry.

Architect: Acinonyx
"""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mas.core.event_bus import EventBus
from mas.core.message import Message
from mas.mcp.protocol import MCPRegistry
from mas.tools.gitops_tool import (
    generate_github_actions_workflow,
    generate_gitlab_ci_pipeline,
    trigger_workflow_dispatch,
    run_local_gitops_ci,
    register_gitops_tools,
)


class TestGitOpsTooling(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test_gitops_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_github_actions_workflow(self):
        result = generate_github_actions_workflow(self.temp_dir, workflow_name="Test Enterprise CI")
        self.assertTrue(result["success"])
        wf_path = os.path.join(self.temp_dir, ".github", "workflows", "ci.yml")
        self.assertTrue(os.path.exists(wf_path))

        with open(wf_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("name: Test Enterprise CI", content)
        self.assertIn("actions/checkout@v4", content)
        self.assertIn("test-and-coverage", content)
        self.assertIn("security-audit", content)
        self.assertIn("build-and-package", content)

    def test_generate_gitlab_ci_pipeline(self):
        result = generate_gitlab_ci_pipeline(self.temp_dir)
        self.assertTrue(result["success"])
        ci_path = os.path.join(self.temp_dir, ".gitlab-ci.yml")
        self.assertTrue(os.path.exists(ci_path))

        with open(ci_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("stages:", content)
        self.assertIn("test_suite:", content)
        self.assertIn("security_scan:", content)

    def test_trigger_workflow_dispatch_simulated_mode(self):
        # Default environment: live dispatch is false
        resp = trigger_workflow_dispatch(
            repo="acinonyx/mas-core",
            workflow_id="ci.yml",
            ref="feature/reconciliation-engine",
        )
        self.assertTrue(resp["success"])
        self.assertEqual(resp["mode"], "simulated_preview")
        self.assertEqual(resp["status"], "queued")
        self.assertIn("simulated_run_id", resp)
        self.assertEqual(resp["repo"], "acinonyx/mas-core")

    def test_run_local_gitops_ci_with_event_bus(self):
        # A self-contained project makes real CI portable to clean checkouts.
        project_dir = self.temp_dir
        tests_dir = os.path.join(project_dir, "tests")
        os.makedirs(tests_dir)
        with open(os.path.join(tests_dir, "test_smoke.py"), "w", encoding="utf-8") as fixture:
            fixture.write("import unittest\nclass Smoke(unittest.TestCase):\n    def test_sum(self): self.assertEqual(2 + 3, 5)\n")
        bus = EventBus()
        events = []

        async def capture_event(msg: Message):
            events.append(msg)

        bus.subscribe("gitops-listener", capture_event, topic="gitops.ci.result")

        # Execute
        res = run_local_gitops_ci(project_dir, event_bus=bus)
        self.assertTrue(res["success"], f"CI failed: {res.get('stderr')}")
        self.assertEqual(res["exit_code"], 0)
        self.assertGreater(res["duration_seconds"], 0)

    def test_empty_test_suite_never_reports_success(self):
        os.makedirs(os.path.join(self.temp_dir, "tests"))
        result = run_local_gitops_ci(self.temp_dir)
        self.assertFalse(result["success"])
        self.assertNotEqual(result["exit_code"], 0)

    def test_failing_test_suite_reports_failure(self):
        test_dir = os.path.join(self.temp_dir, "tests")
        os.makedirs(test_dir)
        with open(os.path.join(test_dir, "test_failure.py"), "w") as fixture:
            fixture.write("import unittest\nclass Failure(unittest.TestCase):\n    def test_failure(self): self.fail('intentional failure')\n")
        result = run_local_gitops_ci(self.temp_dir)
        self.assertFalse(result["success"])
        self.assertIn("intentional failure", result["stderr"])

    def test_register_gitops_tools_in_mcp_registry(self):
        registry = MCPRegistry()
        register_gitops_tools(registry)
        tool_names = list(registry.tools.keys())

        self.assertIn("gitops_generate_github_actions", tool_names)
        self.assertIn("gitops_generate_gitlab_ci", tool_names)
        self.assertIn("gitops_trigger_workflow", tool_names)
        self.assertIn("gitops_run_local_ci", tool_names)


if __name__ == "__main__":
    unittest.main()
