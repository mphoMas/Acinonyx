"""
tests.test_cio: Unit tests for the CIOAgent infrastructure audit system.
Architect: Acinonyx
"""

import asyncio
import os
import sys
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mas.organization.executive import (
    CIOAgent,
    HardwareProfile,
    SoftwareProfile,
    WorkspaceProfile,
    InfrastructureAuditReport,
)


class TestCIOAgentInit(unittest.TestCase):
    def setUp(self):
        self.cio = CIOAgent()

    def test_name(self):
        self.assertEqual(self.cio.name, "CIOAgent")

    def test_role_is_supervisor(self):
        from mas.core.message import Role
        self.assertEqual(self.cio.role, Role.SUPERVISOR)

    def test_system_prompt_contains_cio(self):
        self.assertIn("Chief Information Officer", self.cio.system_prompt)

    def test_no_audit_initially(self):
        self.assertIsNone(self.cio.last_audit)


class TestHardwareProbe(unittest.TestCase):
    def setUp(self):
        self.cio = CIOAgent()

    def test_hardware_profile_type(self):
        hw = self.cio._probe_hardware()
        self.assertIsInstance(hw, HardwareProfile)

    def test_os_name_populated(self):
        hw = self.cio._probe_hardware()
        self.assertIsInstance(hw.os_name, str)
        self.assertTrue(len(hw.os_name) > 0)

    def test_cpu_count_positive(self):
        hw = self.cio._probe_hardware()
        self.assertGreater(hw.cpu_count_logical, 0)

    def test_ram_positive(self):
        hw = self.cio._probe_hardware()
        self.assertGreater(hw.total_ram_gb, 0)

    def test_ram_available_leq_total(self):
        hw = self.cio._probe_hardware()
        self.assertLessEqual(hw.available_ram_gb, hw.total_ram_gb)

    def test_disk_partitions_non_empty(self):
        hw = self.cio._probe_hardware()
        self.assertIsInstance(hw.disk_partitions, list)
        self.assertGreater(len(hw.disk_partitions), 0)

    def test_disk_partition_fields(self):
        hw = self.cio._probe_hardware()
        for partition in hw.disk_partitions:
            self.assertIn("mountpoint", partition)
            self.assertIn("total_gb", partition)
            self.assertIn("free_gb", partition)


class TestSoftwareProbe(unittest.TestCase):
    def setUp(self):
        self.cio = CIOAgent()

    def test_software_profile_type(self):
        sw = self.cio._probe_software()
        self.assertIsInstance(sw, SoftwareProfile)

    def test_python_version_populated(self):
        sw = self.cio._probe_software()
        self.assertIsInstance(sw.python_version, str)
        self.assertRegex(sw.python_version, r"^\d+\.\d+")

    def test_python_executable_exists(self):
        sw = self.cio._probe_software()
        self.assertTrue(os.path.exists(sw.python_executable), f"Executable not found: {sw.python_executable}")

    def test_binaries_dict_populated(self):
        sw = self.cio._probe_software()
        self.assertIsInstance(sw.installed_binaries, dict)
        self.assertGreater(len(sw.installed_binaries), 0)

    def test_python3_binary_found(self):
        sw = self.cio._probe_software()
        python3_status = sw.installed_binaries.get("python3", "not found")
        self.assertNotEqual(python3_status, "not found", "python3 must be discoverable via which")

    def test_env_vars_populated(self):
        sw = self.cio._probe_software()
        self.assertIsInstance(sw.environment_variables, dict)
        # HOME should always be set
        self.assertIn("HOME", sw.environment_variables)

    def test_binary_values_are_strings(self):
        sw = self.cio._probe_software()
        for k, v in sw.installed_binaries.items():
            self.assertIsInstance(v, str, f"Binary value for '{k}' must be str")


class TestWorkspaceProbe(unittest.TestCase):
    def setUp(self):
        self.cio = CIOAgent()
        self.workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )

    def test_workspace_profile_type(self):
        ws = self.cio._probe_workspace(self.workspace_root)
        self.assertIsInstance(ws, WorkspaceProfile)

    def test_root_path_correct(self):
        ws = self.cio._probe_workspace(self.workspace_root)
        self.assertEqual(ws.root_path, self.workspace_root)

    def test_file_count_positive(self):
        ws = self.cio._probe_workspace(self.workspace_root)
        self.assertGreater(ws.total_files, 0)

    def test_python_modules_found(self):
        ws = self.cio._probe_workspace(self.workspace_root)
        self.assertIsInstance(ws.python_modules, list)
        self.assertGreater(len(ws.python_modules), 0, "Should detect at least one Python package")

    def test_mas_package_in_modules(self):
        ws = self.cio._probe_workspace(self.workspace_root)
        module_paths = " ".join(ws.python_modules)
        self.assertIn("mas", module_paths)

    def test_size_positive(self):
        ws = self.cio._probe_workspace(self.workspace_root)
        self.assertGreater(ws.total_size_mb, 0)


class TestIntelligenceEngine(unittest.TestCase):
    def setUp(self):
        self.cio = CIOAgent()

    def _make_hw(self, ram=16.0, cpus=8, disk_pct=50):
        return HardwareProfile(
            os_name="Linux", os_release="6.x", os_version="test",
            machine="x86_64", processor="", hostname="testhost",
            cpu_count_logical=cpus, cpu_count_physical=None,
            total_ram_gb=ram, available_ram_gb=ram * 0.5,
            swap_total_gb=4.0, swap_free_gb=4.0,
            disk_partitions=[{
                "mountpoint": "/", "total_gb": 100,
                "used_gb": disk_pct, "free_gb": 100 - disk_pct,
                "percent": disk_pct,
            }],
        )

    def _make_sw(self, git="not found", pip="not found"):
        return SoftwareProfile(
            python_version="3.14.4",
            python_executable="/usr/bin/python3",
            python_path="",
            installed_binaries={"git": git, "pip3": pip, "curl": "/usr/bin/curl"},
            environment_variables={},
        )

    def _make_ws(self):
        return WorkspaceProfile(
            root_path="/test", total_files=50, total_dirs=10,
            total_size_mb=20.0, top_level_dirs=[], python_modules=["mas"],
        )

    def test_low_ram_triggers_risk(self):
        hw = self._make_hw(ram=2.0)
        risks, _, _ = self.cio._generate_intelligence(hw, self._make_sw(), self._make_ws())
        self.assertTrue(any("MEMORY" in r for r in risks), f"Expected LOW MEMORY risk, got: {risks}")

    def test_good_ram_triggers_opportunity(self):
        hw = self._make_hw(ram=32.0)
        _, _, opps = self.cio._generate_intelligence(hw, self._make_sw(), self._make_ws())
        self.assertTrue(any("RAM" in o or "ram" in o.lower() for o in opps))

    def test_missing_git_triggers_risk(self):
        hw = self._make_hw()
        risks, _, _ = self.cio._generate_intelligence(hw, self._make_sw(git="not found"), self._make_ws())
        self.assertTrue(any("git" in r.lower() for r in risks))

    def test_disk_critical_at_95pct(self):
        hw = self._make_hw(disk_pct=95)
        risks, _, _ = self.cio._generate_intelligence(hw, self._make_sw(), self._make_ws())
        self.assertTrue(any("DISK" in r for r in risks))

    def test_curl_found_opportunity(self):
        hw = self._make_hw()
        _, _, opps = self.cio._generate_intelligence(hw, self._make_sw(), self._make_ws())
        self.assertTrue(any("curl" in o.lower() for o in opps))


class TestAsyncAudit(unittest.TestCase):
    def setUp(self):
        self.cio = CIOAgent()

    def test_run_infrastructure_audit_returns_report(self):
        workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(
                self.cio.run_infrastructure_audit(workspace_root=workspace_root)
            )
        finally:
            loop.close()

        self.assertIsInstance(report, InfrastructureAuditReport)
        self.assertEqual(report.auditor, "CIOAgent")
        self.assertIsNotNone(report.audit_timestamp)
        self.assertIsInstance(report.hardware, HardwareProfile)
        self.assertIsInstance(report.software, SoftwareProfile)
        self.assertIsInstance(report.workspace, WorkspaceProfile)

    def test_last_audit_cached_after_run(self):
        workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                self.cio.run_infrastructure_audit(workspace_root=workspace_root)
            )
        finally:
            loop.close()

        self.assertIsNotNone(self.cio.last_audit)

    def test_audit_to_dict_serializable(self):
        workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(
                self.cio.run_infrastructure_audit(workspace_root=workspace_root)
            )
        finally:
            loop.close()

        import json
        d = report.to_dict()
        json_str = json.dumps(d)
        self.assertIn("hardware", json_str)
        self.assertIn("software", json_str)

    def test_audit_markdown_contains_sections(self):
        workspace_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..")
        )
        loop = asyncio.new_event_loop()
        try:
            report = loop.run_until_complete(
                self.cio.run_infrastructure_audit(workspace_root=workspace_root)
            )
        finally:
            loop.close()

        md = report.to_markdown()
        self.assertIn("## 1. Hardware Profile", md)
        self.assertIn("## 2. Software Profile", md)
        self.assertIn("## 3. Workspace Profile", md)
        self.assertIn("## 4. Risk Flags", md)
        self.assertIn("## 5. Recommendations", md)
        self.assertIn("## 6. Opportunities", md)


class TestCIOEnterpriseIntegration(unittest.TestCase):
    def test_cio_in_executive_department(self):
        from mas.organization.company import ConsultingEnterprise
        from mas.organization.department import DepartmentType
        enterprise = ConsultingEnterprise()
        exec_dept = enterprise.departments[DepartmentType.EXECUTIVE]
        self.assertIn("CIOAgent", exec_dept.members)

    def test_cio_accessible_via_enterprise(self):
        from mas.organization.company import ConsultingEnterprise
        enterprise = ConsultingEnterprise()
        self.assertIsNotNone(enterprise.cio)
        self.assertEqual(enterprise.cio.name, "CIOAgent")

    def test_enterprise_headcount_includes_cio(self):
        from mas.organization.company import ConsultingEnterprise
        enterprise = ConsultingEnterprise()
        headcount = enterprise.get_headcount()
        # Original 7 + CIO = 8
        self.assertGreaterEqual(headcount, 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
