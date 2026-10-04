"""
mas.capabilities: Honest capability matrix — implemented / demo-only / planned.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List


class CapabilityStatus(str, Enum):
    IMPLEMENTED = "implemented"
    DEMO_ONLY = "demo-only"
    PLANNED = "planned"


@dataclass(frozen=True)
class Capability:
    name: str
    status: CapabilityStatus
    notes: str
    module: str


CAPABILITIES: List[Capability] = [
    Capability("typed_message_bus", CapabilityStatus.IMPLEMENTED, "Async topic bus + validation + JSONL audit", "mas.core.event_bus"),
    Capability("supervisor_dag", CapabilityStatus.IMPLEMENTED, "Dependency-aware concurrent subtasks with timeout/retry", "mas.orchestration.supervisor"),
    Capability("anti_sycophancy_debate", CapabilityStatus.IMPLEMENTED, "Blind masking, contrarian, sycophancy score", "mas.orchestration.debate"),
    Capability("sop_pipeline", CapabilityStatus.IMPLEMENTED, "Sequential stages with schema validators", "mas.orchestration.pipeline"),
    Capability("mcp_jsonrpc", CapabilityStatus.IMPLEMENTED, "tools/resources/prompts + initialize handshake", "mas.mcp.protocol"),
    Capability("working_episodic_memory", CapabilityStatus.IMPLEMENTED, "Sliding window + SQLite vector episodic store", "mas.memory"),
    Capability("sandboxed_python", CapabilityStatus.IMPLEMENTED, "Subprocess + import deny-list + timeout", "mas.tools.executor"),
    Capability("filesystem_jail", CapabilityStatus.IMPLEMENTED, "Path allowlist roots", "mas.tools.filesystem"),
    Capability("llm_provider_http", CapabilityStatus.IMPLEMENTED, "OpenAI-compatible HTTP provider", "mas.providers.http_provider"),
    Capability("agent_react_loop", CapabilityStatus.IMPLEMENTED, "Tool loop when provider attached", "mas.core.agent"),
    Capability("squad_self_heal", CapabilityStatus.IMPLEMENTED, "QA loop; LLM repair when provider present else generator fallback", "mas.squad.squad"),
    Capability("hr_gap_analysis", CapabilityStatus.IMPLEMENTED, "LLM analysis with keyword catalog fallback", "mas.organization.hr"),
    Capability("enterprise_engagement", CapabilityStatus.DEMO_ONLY, "Scripted departmental pipeline; dry-run default", "mas.organization.engagement"),
    Capability("demo_echo_agents", CapabilityStatus.DEMO_ONLY, "Template agents without LLM are pass-through", "main.py"),
    Capability("distributed_swarm_auth", CapabilityStatus.IMPLEMENTED, "Swarm relay with token auth", "mas.core.swarm"),
    Capability("visual_diff_gate", CapabilityStatus.IMPLEMENTED, "Pixel RMSE visual regression", "mas.tools.visual_diff"),
    Capability("eval_harness", CapabilityStatus.IMPLEMENTED, "Golden missions + structural/quality scoring", "mas.eval"),
    Capability("cli_doctor", CapabilityStatus.IMPLEMENTED, "Runtime health / mode report", "mas.cli"),
    Capability("multi_tenant_iam", CapabilityStatus.PLANNED, "Full OAuth/PAB multi-tenant IAM", "n/a"),
    Capability("managed_vector_saas", CapabilityStatus.PLANNED, "External managed vector DB adapters", "n/a"),
]


def capability_matrix() -> Dict[str, Dict[str, str]]:
    return {
        c.name: {"status": c.status.value, "notes": c.notes, "module": c.module}
        for c in CAPABILITIES
    }


def summary_counts() -> Dict[str, int]:
    counts = {s.value: 0 for s in CapabilityStatus}
    for c in CAPABILITIES:
        counts[c.status.value] += 1
    return counts
