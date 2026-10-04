"""
MAS-Core: Interactive Demonstration & Mission Runner
Architect: Acinonyx, Chief Principal Agentic Engineer
"""

from __future__ import annotations
import argparse
import asyncio
import sys
from mas.core.agent import BaseAgent
from mas.core.event_bus import EventBus
from mas.core.message import Message, Role, ContentType
from mas.core.state import StateMachine
from mas.mcp.protocol import MCPRegistry
from mas.mcp.transport import MCPClient
from mas.memory.episodic import EpisodicMemory
from mas.orchestration.supervisor import SupervisorAgent
from mas.orchestration.debate import DebateEngine
from mas.orchestration.pipeline import SOPPipeline
from mas.squad.squad import EngineeringSquad
from mas.organization.company import ConsultingEnterprise
from mas.organization.engagement import ConsultingEngagement
from mas.tools.executor import register_default_tools
from mas.tools.filesystem import register_filesystem_tools
from mas.dashboard.server import run_dashboard


class DemoAgent(BaseAgent):
    """Demonstration agent that produces formatted stage outputs."""

    def __init__(self, name: str, role_title: str, template_fn, **kwargs):
        super().__init__(name=name, **kwargs)
        self.role_title = role_title
        self.template_fn = template_fn

    async def reason(self, context_messages):
        last_msg = context_messages[-1] if context_messages else None
        content = last_msg.content if last_msg else ""
        return self.template_fn(content)


async def run_supervisor_demo():
    print("\n" + "=" * 60)
    print("🚀 [TOPOLOGY 1] HIERARCHICAL SUPERVISOR MISSION")
    print("=" * 60)

    supervisor = SupervisorAgent(name="director")

    data_agent = DemoAgent(
        name="data_specialist",
        role_title="Data Specialist",
        template_fn=lambda c: "Analyzed 1.2M events: 4.2% latency regression detected in auth microservice.",
        role=Role.ASSISTANT,
    )
    infra_agent = DemoAgent(
        name="infra_specialist",
        role_title="Infra Specialist",
        template_fn=lambda c: "Allocated 4x Redis cluster nodes; deployed connection pool optimizations.",
        role=Role.ASSISTANT,
    )

    supervisor.register_worker(data_agent)
    supervisor.register_worker(infra_agent)

    specs = [
        {"id": "t1", "description": "Telemetry root-cause analysis", "worker": "data_specialist", "dependencies": []},
        {"id": "t2", "description": "Scale and tune cache infrastructure", "worker": "infra_specialist", "dependencies": ["t1"]},
    ]

    result = await supervisor.run_mission("Resolve Production Latency Spike", specs)
    print(result)


async def run_debate_demo():
    print("\n" + "=" * 60)
    print("⚖️  [TOPOLOGY 2] ANTI-SYCOPHANCY MULTI-AGENT DEBATE (MAD)")
    print("=" * 60)

    proponent = DemoAgent(
        name="proponent",
        role_title="Distributed Systems Advocate",
        template_fn=lambda c: "Position: Adopt event-driven microservices for independent horizontal scaling and resilience.",
        role=Role.ASSISTANT,
    )
    pragmatist = DemoAgent(
        name="pragmatist",
        role_title="Engineering Lead",
        template_fn=lambda c: "Position: A modular monolith is 5x faster to deploy, simpler to debug, and avoids distributed transaction overhead.",
        role=Role.ASSISTANT,
    )
    contrarian = DemoAgent(
        name="devil_advocate",
        role_title="Contrarian Challenger",
        template_fn=lambda c: "Critique: Both sides ignore network partition failure modes and operational costs. We lack Kubernetes telemetry.",
        role=Role.CRITIC,
    )
    moderator = DemoAgent(
        name="moderator",
        role_title="Chief Architect",
        template_fn=lambda c: (
            "VERDICT: Adopt a Modular Monolith with strictly bounded contexts. "
            "Microservices introduce premature distributed systems complexity at our current scale."
        ),
        role=Role.MODERATOR,
    )

    engine = DebateEngine(
        debaters=[proponent, pragmatist],
        contrarian=contrarian,
        moderator=moderator,
        max_rounds=2,
    )

    topic = "Architecture Decision: Microservices vs. Modular Monolith for MAS-Core"
    print(f"Proposition: '{topic}'")
    verdict = await engine.conduct_debate(topic)
    print(f"\nAuthoritative Moderator Synthesis:\n{verdict}")


async def run_pipeline_demo():
    print("\n" + "=" * 60)
    print("⚙️  [TOPOLOGY 3] SEQUENTIAL SOP-DRIVEN ASSEMBLY LINE")
    print("=" * 60)

    pm = DemoAgent(
        name="product_manager",
        role_title="Product Manager",
        template_fn=lambda c: "PRD: Feature requires sub-millisecond atomic state rollback and JSON-RPC 2.0 interface.",
        role=Role.ASSISTANT,
    )
    architect = DemoAgent(
        name="system_architect",
        role_title="System Architect",
        template_fn=lambda c: "System Design: StateMachine class with versioned Checkpoint stack and copy-on-write immutability.",
        role=Role.ASSISTANT,
    )
    qa = DemoAgent(
        name="qa_engineer",
        role_title="QA Engineer",
        template_fn=lambda c: "QA Report: 100% test pass rate across rollback, concurrency, and serialization tests.",
        role=Role.ASSISTANT,
    )

    pipeline = SOPPipeline(name="Feature-Lifecycle")
    pipeline.add_stage("PRD", pm, output_key="prd", instruction_template="Draft requirements for {input}")
    pipeline.add_stage("Design", architect, output_key="design", instruction_template="Produce architecture from: {prd}")
    pipeline.add_stage("QA", qa, output_key="qa", instruction_template="Verify test criteria for: {design}")

    artifacts = await pipeline.execute("High-Throughput State Machine")
    for key, val in artifacts.items():
        print(f"[{key.upper()}]:\n  {val}")


async def run_reflexion_demo():
    print("\n" + "=" * 60)
    print("🧠 [TOOL GROUNDING & REFLEXION] MCP EXECUTOR WITH SELF-HEALING")
    print("=" * 60)

    registry = MCPRegistry()
    register_default_tools(registry)
    client = MCPClient(registry)

    # Inspect discovered tools via MCP
    tools = await client.list_tools()
    print(f"Discovered MCP Tools: {[t['name'] for t in tools]}")

    episodic_memory = EpisodicMemory()

    # Step 1: Deliberate failure trigger
    print("\n[Step 1] Attempting execution with buggy syntax...")
    buggy_code = "result = sum([1, 2, 'three', 4])\nprint(result)"
    res1 = await client.call_tool("run_python", {"code": buggy_code})
    print(f"Tool Output:\n{res1}")

    # Record verbal reflection
    episodic_memory.record_reflection(
        task="Compute integer sum across list elements",
        success=False,
        critique="TypeError encountered: unsupported operand type(s) for +: 'int' and 'str'.",
        suggested_strategy="Filter and cast elements to integer or catch ValueError.",
        tags=["python", "types", "sum"],
    )

    # Step 2: Self-corrected execution informed by reflection
    print("\n[Step 2] Executing self-corrected code informed by reflection...")
    fixed_code = "data = [1, 2, 'three', 4]\nclean_sum = sum(int(x) for x in data if str(x).isdigit())\nprint(f'Clean Sum: {clean_sum}')"
    res2 = await client.call_tool("run_python", {"code": fixed_code})
    print(f"Tool Output:\n{res2}")

    episodic_memory.record_reflection(
        task="Compute integer sum across list elements",
        success=True,
        critique="Filtered numeric tokens successfully.",
        suggested_strategy="Standardize on sanitization filters for heterogeneous inputs.",
        tags=["python", "types", "sum", "sanitization"],
    )

    print("\n[Episodic Memory Prompt Injection Preview]:")
    print(episodic_memory.format_reflections_for_prompt("sum calculation error"))


async def run_squad_demo():
    print("\n" + "=" * 60)
    print("👥 [AUTONOMOUS ENGINEERING SQUAD] ARCHITECT + ENGINEER + QA")
    print("=" * 60)

    registry = MCPRegistry()
    register_default_tools(registry)
    register_filesystem_tools(registry)
    client = MCPClient(registry)

    squad = EngineeringSquad(mcp_client=client, max_repair_attempts=2)

    target_code = "mas/core/cache.py"
    target_test = "tests/test_cache.py"

    def code_generator(spec: str, attempt: int) -> str:
        # In a real environment, this is generated by EngineerAgent via LLM
        return (
            '"""\n'
            'mas.core.cache: High-performance thread-safe TTL Cache.\n'
            'Synthesized autonomously by the Acinonyx Engineering Squad.\n'
            '"""\n\n'
            'import time\n'
            'from typing import Any, Dict, Optional\n\n\n'
            'class TTLCache:\n'
            '    def __init__(self, default_ttl_sec: float = 60.0, max_size: int = 1000):\n'
            '        self.default_ttl = default_ttl_sec\n'
            '        self.max_size = max_size\n'
            '        self._store: Dict[str, tuple[Any, float]] = {}\n\n'
            '    def set(self, key: str, value: Any, ttl_sec: Optional[float] = None) -> None:\n'
            '        ttl = ttl_sec if ttl_sec is not None else self.default_ttl\n'
            '        expiry = time.time() + ttl\n'
            '        if len(self._store) >= self.max_size and key not in self._store:\n'
            '            oldest_key = min(self._store.keys(), key=lambda k: self._store[k][1])\n'
            '            del self._store[oldest_key]\n'
            '        self._store[key] = (value, expiry)\n\n'
            '    def get(self, key: str, default: Any = None) -> Any:\n'
            '        if key not in self._store:\n'
            '            return default\n'
            '        val, expiry = self._store[key]\n'
            '        if time.time() > expiry:\n'
            '            del self._store[key]\n'
            '            return default\n'
            '        return val\n\n'
            '    def delete(self, key: str) -> bool:\n'
            '        if key in self._store:\n'
            '            del self._store[key]\n'
            '            return True\n'
            '        return False\n\n'
            '    def clear(self) -> None:\n'
            '        self._store.clear()\n\n'
            '    def size(self) -> int:\n'
            '        now = time.time()\n'
            '        self._store = {k: v for k, v in self._store.items() if v[1] > now}\n'
            '        return len(self._store)\n'
        )

    def test_generator(spec: str, attempt: int) -> str:
        return (
            'import time\n'
            'import unittest\n'
            'from mas.core.cache import TTLCache\n\n\n'
            'class TestTTLCache(unittest.TestCase):\n'
            '    def test_cache_set_get_and_expiration(self):\n'
            '        cache = TTLCache(default_ttl_sec=0.1, max_size=2)\n'
            '        cache.set("a", 100)\n'
            '        self.assertEqual(cache.get("a"), 100)\n'
            '        time.sleep(0.15)\n'
            '        self.assertIsNone(cache.get("a"))\n\n'
            '    def test_cache_eviction(self):\n'
            '        cache = TTLCache(default_ttl_sec=10.0, max_size=2)\n'
            '        cache.set("x", 1)\n'
            '        cache.set("y", 2)\n'
            '        cache.set("z", 3)  # Should evict oldest\n'
            '        self.assertEqual(cache.size(), 2)\n\n'
            'if __name__ == "__main__":\n'
            '    unittest.main()\n'
        )

    mission = await squad.run_mission(
        task_name="Concurrent TTL Cache",
        requirements="In-memory cache with configurable TTL, max_size eviction, and O(1) retrieval.",
        target_code_file=target_code,
        target_test_file=target_test,
        code_generator_fn=code_generator,
        test_generator_fn=test_generator,
    )

    print(f"Task: {mission.task_name}")
    print(f"Status: {'✅ VERIFIED & PASSED' if mission.success else '❌ FAILED'}")
    print(f"Attempts: {mission.attempts}")
    print(f"Generated Code: {target_code}")
    print(f"Generated Tests: {target_test}")
    print(f"QA Test Report:\n{mission.test_report}")


async def run_enterprise_demo():
    print("\n" + "=" * 60)
    print("🏢 [ENTERPRISE IT SAAS CONSULTING FIRM] FULL SDLC ENGAGEMENT")
    print("=" * 60)

    enterprise = ConsultingEnterprise(name="Acinonyx Consulting Group (ACG)")

    print(f"\n[Organization Initialized]: {enterprise.name}")
    print("Active Departments: Client Management, HR, Product, Design, Engineering, Marketing")
    print(f"Initial Headcount: {enterprise.get_headcount()} agents")
    print("Initial Roster:")
    for role_name, dept_name in enterprise.get_roster().items():
        print(f"  • {role_name.ljust(25)} -> Dept: {dept_name}")

    client_rfp = (
        "We are NovaHealth Telehealth. We need a HIPAA-compliant multi-tenant telehealth SaaS "
        "with real-time video consultation, end-to-end encryption, and AI vector search for clinical records. "
        "Must undergo vulnerability penetration testing and audit before launch."
    )

    engagement = ConsultingEngagement(enterprise)

    print("\n" + "-" * 50)
    print("📥 [PHASE 1] CLIENT INTAKE & BRIEF")
    print("-" * 50)
    print(f"Client: NovaHealth Telehealth\nRequest: {client_rfp}\n")

    artifacts = await engagement.execute_engagement(
        client_name="NovaHealth Telehealth",
        raw_rfp=client_rfp,
    )

    print("✅ Client Engagement Brief synthesized by Director of Client Management.")

    print("\n" + "-" * 50)
    print("🔍 [PHASE 2] HR TALENT OPS: SKILL GAP ANALYSIS & DYNAMIC HIRING")
    print("-" * 50)
    print(f"HR Talent Ops scanned requirements against company roster.")
    print(f"Identified Gaps: {len(artifacts.job_requisitions)}")
    for req in artifacts.job_requisitions:
        print(f"  ⚡ Job Requisition Formulated: [{req.role_title}] in {req.department_type.value}")
        print(f"     Rationale: {req.rationale}")

    print(f"\nDynamically Recruited & Onboarded: {artifacts.newly_hired_agents}")
    print(f"New Company Headcount: {enterprise.get_headcount()} agents")

    print("\n" + "-" * 50)
    print("📋 [PHASE 3] PRODUCT MANAGEMENT: PRD & USER STORIES")
    print("-" * 50)
    print(artifacts.prd[:350] + "...\n")

    print("\n" + "-" * 50)
    print("🎨 [PHASE 4] UI/UX & SYSTEM DESIGN")
    print("-" * 50)
    print(artifacts.design_system[:350] + "...\n")

    print("\n" + "-" * 50)
    print("🛡️  [PHASE 5] SPECIALIST DOMAIN COMPLIANCE AUDITS")
    print("-" * 50)
    for specialist_name, audit_report in artifacts.specialist_audits.items():
        print(f"Specialist: [{specialist_name}]")
        print(f"Audit Findings:\n  {audit_report[:300]}...\n")

    print("\n" + "-" * 50)
    print("💻 [PHASE 6] ENGINEERING & ARCHITECTURE SYNTHESIS")
    print("-" * 50)
    print(artifacts.engineering_summary[:350] + "...\n")

    print("\n" + "-" * 50)
    print("🚀 [PHASE 7] GO-TO-MARKET (GTM) LAUNCH PACKAGE")
    print("-" * 50)
    print(artifacts.gtm_package[:350] + "...\n")

    print("\n" + "-" * 50)
    print("🤝 [PHASE 8] EXECUTIVE CLIENT ACCEPTANCE & DELIVERY")
    print("-" * 50)
    print(artifacts.delivery_signoff)

    print("\n" + "=" * 60)
    print("📈 CORPORATE STATE & ENGAGEMENT METRICS")
    print("=" * 60)
    print(f"Total Engagements Completed: {enterprise.state_machine.get('total_engagements')}")
    print(f"Final Company Headcount:     {enterprise.get_headcount()} agents")
    print(f"Checkpoints Recorded:        {len(enterprise.state_machine.list_checkpoints())}")


async def main():
    parser = argparse.ArgumentParser(description="MAS-Core Runtime Demonstration")
    parser.add_argument(
        "--mode",
        choices=["supervisor", "debate", "pipeline", "reflexion", "squad", "enterprise", "dashboard", "all"],
        default="all",
        help="Orchestration mode to run (default: all)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for observability web dashboard (default: 8080)",
    )
    args = parser.parse_args()

    print("\n🦁 PROJECT ACINONYX — MAS-CORE RUNTIME INITIALIZED")
    print(f"Python: {sys.version.split()[0]} | Platform: {sys.platform}")

    if args.mode == "dashboard":
        run_dashboard(host="0.0.0.0", port=args.port)
        return

    if args.mode in ("supervisor", "all"):
        await run_supervisor_demo()
    if args.mode in ("debate", "all"):
        await run_debate_demo()
    if args.mode in ("pipeline", "all"):
        await run_pipeline_demo()
    if args.mode in ("reflexion", "all"):
        await run_reflexion_demo()
    if args.mode in ("squad", "all"):
        await run_squad_demo()
    if args.mode in ("enterprise", "all"):
        await run_enterprise_demo()

    print("\n" + "=" * 60)
    print("✅ ALL ACINONYX RUNTIME MODES EXECUTED SUCCESSFULLY")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
