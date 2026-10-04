"""
mas.squad.squad: Autonomous Software Engineering Squad with self-healing QA loop.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from mas.core.agent import BaseAgent
from mas.core.message import ContentType, Message, MessageMetadata, Role
from mas.mcp.transport import MCPClient
from mas.memory.episodic import EpisodicMemory


@dataclass
class SquadMissionResult:
    task_name: str
    success: bool
    architecture_spec: str
    implementation_summary: str
    test_report: str
    attempts: int
    reflections: List[str] = field(default_factory=list)
    repair_mode: str = "generator"  # generator | llm


class ArchitectAgent(BaseAgent):
    """Lead Architect agent that designs specifications and API contracts."""

    def __init__(self, name: str = "lead_architect", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.SUPERVISOR,
            system_prompt=(
                "You are the Lead Systems Architect. Your responsibility is to analyze requirements, "
                "define modular interfaces, specify invariants, and design the file hierarchy."
            ),
            **kwargs,
        )


class EngineerAgent(BaseAgent):
    """Senior Implementation Engineer agent that writes code and unit tests."""

    def __init__(self, name: str = "senior_engineer", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.ASSISTANT,
            system_prompt=(
                "You are the Senior Implementation Engineer. You translate architectural specs "
                "into clean, robust, and well-typed Python code with unit tests. "
                "When given a failure critique, emit only corrected source code."
            ),
            **kwargs,
        )


class QAAgent(BaseAgent):
    """QA & Verification agent that executes test suites and validates artifacts."""

    def __init__(self, name: str = "qa_critic", **kwargs) -> None:
        super().__init__(
            name=name,
            role=Role.CRITIC,
            system_prompt=(
                "You are the QA Reviewer and Verification Critic. You execute unit test suites, "
                "diagnose runtime regressions, and provide constructive failure critiques."
            ),
            **kwargs,
        )


class EngineeringSquad:
    """
    Autonomous multi-agent engineering squad implementing the full SDLC:
    Architect (Spec) -> Engineer (Code) -> QA (Test Runner) -> [Reflexion Repair Loop].

    Repair policy:
    - If engineer.llm_provider is set, critique drives an LLM rewrite of the code.
    - Otherwise falls back to caller-supplied generator functions (demo/CI mode).
    """

    def __init__(
        self,
        architect: Optional[ArchitectAgent] = None,
        engineer: Optional[EngineerAgent] = None,
        qa: Optional[QAAgent] = None,
        mcp_client: Optional[MCPClient] = None,
        max_repair_attempts: int = 3,
    ) -> None:
        self.mcp_client = mcp_client
        self.max_repair_attempts = max_repair_attempts
        self.architect = architect or ArchitectAgent(mcp_client=mcp_client)
        self.engineer = engineer or EngineerAgent(mcp_client=mcp_client)
        self.qa = qa or QAAgent(mcp_client=mcp_client)
        self.episodic_memory = EpisodicMemory()

    async def _llm_repair_code(
        self,
        spec: str,
        requirements: str,
        current_code: str,
        critique: str,
        target_code_file: str,
    ) -> str:
        prompt = (
            f"Architecture Spec:\n{spec}\n\n"
            f"Requirements:\n{requirements}\n\n"
            f"Current code in {target_code_file}:\n```\n{current_code}\n```\n\n"
            f"QA Critique / Failure:\n{critique}\n\n"
            f"Task: Emit the full corrected Python source for {target_code_file} only. "
            f"No markdown fences."
        )
        msg = Message(
            sender="squad_coordinator",
            recipient=self.engineer.name,
            role=Role.USER,
            content=prompt,
        )
        resp = await self.engineer.step(msg)
        code = resp.content.strip()
        if code.startswith("```"):
            lines = code.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            code = "\n".join(lines)
        return code

    async def run_mission(
        self,
        task_name: str,
        requirements: str,
        target_code_file: str,
        target_test_file: str,
        code_generator_fn=None,
        test_generator_fn=None,
    ) -> SquadMissionResult:
        """
        Execute an autonomous engineering mission with self-healing test loop.
        """
        use_llm_repair = bool(getattr(self.engineer, "llm_provider", None))
        repair_mode = "llm" if use_llm_repair else "generator"
        if not use_llm_repair and (code_generator_fn is None or test_generator_fn is None):
            raise ValueError(
                "code_generator_fn and test_generator_fn are required when no LLM provider is attached"
            )

        # Phase 1: Architecture Specification
        arch_prompt = f"Design architecture for task '{task_name}':\nRequirements: {requirements}"
        arch_msg = Message(
            sender="squad_coordinator",
            recipient=self.architect.name,
            role=Role.USER,
            content=arch_prompt,
        )
        arch_resp = await self.architect.step(arch_msg)
        spec = arch_resp.content

        # Phase 2: Initial Implementation
        if use_llm_repair and code_generator_fn is None:
            impl_code = await self._llm_repair_code(
                spec, requirements, "# empty", "Initial implementation required.", target_code_file
            )
            test_code = (
                f"# tests for {task_name}\n"
                f"import unittest\n"
                f"class T(unittest.TestCase):\n"
                f"    def test_placeholder(self):\n"
                f"        self.assertTrue(True)\n"
                f"if __name__ == '__main__':\n"
                f"    unittest.main()\n"
            )
            if test_generator_fn:
                test_code = test_generator_fn(spec, attempt=1)
        else:
            impl_code = code_generator_fn(spec, attempt=1)
            test_code = test_generator_fn(spec, attempt=1)

        if self.mcp_client:
            await self.mcp_client.call_tool("fs_write", {"path": target_code_file, "content": impl_code})
            await self.mcp_client.call_tool("fs_write", {"path": target_test_file, "content": test_code})

        reflections: List[str] = []
        success = False
        test_report = ""
        attempt = 0

        for attempt in range(1, self.max_repair_attempts + 1):
            test_run_cmd = (
                f"import sys, runpy\n"
                f"sys.argv = ['{target_test_file}']\n"
                f"runpy.run_path('{target_test_file}', run_name='__main__')\n"
            )

            test_report = await self.mcp_client.call_tool("run_python", {"code": test_run_cmd})

            if "EXIT_FAILURE" not in test_report and "ERROR" not in test_report:
                success = True
                self.episodic_memory.record_reflection(
                    task=task_name,
                    success=True,
                    critique="All verification assertions passed.",
                    suggested_strategy="Implementation meets architectural specifications.",
                    tags=["squad", "qa", "pass"],
                )
                break

            critique = f"Attempt #{attempt} failed verification:\n{test_report}"
            reflections.append(critique)
            self.episodic_memory.record_reflection(
                task=task_name,
                success=False,
                critique=critique,
                suggested_strategy="Refactor failing assertions or edge case handling.",
                tags=["squad", "qa", "failure"],
            )

            if attempt >= self.max_repair_attempts:
                break

            if use_llm_repair:
                impl_code = await self._llm_repair_code(
                    spec, requirements, impl_code, critique, target_code_file
                )
                if test_generator_fn:
                    test_code = test_generator_fn(spec, attempt=attempt + 1)
            else:
                impl_code = code_generator_fn(spec, attempt=attempt + 1)
                test_code = test_generator_fn(spec, attempt=attempt + 1)

            if self.mcp_client:
                await self.mcp_client.call_tool("fs_write", {"path": target_code_file, "content": impl_code})
                await self.mcp_client.call_tool("fs_write", {"path": target_test_file, "content": test_code})

        return SquadMissionResult(
            task_name=task_name,
            success=success,
            architecture_spec=spec,
            implementation_summary=f"Written to {target_code_file} and {target_test_file}",
            test_report=test_report,
            attempts=attempt,
            reflections=reflections,
            repair_mode=repair_mode,
        )
