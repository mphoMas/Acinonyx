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
    Capability("sandboxed_python", CapabilityStatus.IMPLEMENTED, "Required bubblewrap isolation, bounded output and process-group cleanup", "mas.tools.executor"),
    Capability("filesystem_jail", CapabilityStatus.IMPLEMENTED, "Path allowlist roots", "mas.tools.filesystem"),
    Capability("llm_provider_http", CapabilityStatus.IMPLEMENTED, "OpenAI-compatible HTTP provider", "mas.providers.http_provider"),
    Capability("agent_react_loop", CapabilityStatus.IMPLEMENTED, "Tool loop when provider attached", "mas.core.agent"),
    Capability("squad_self_heal", CapabilityStatus.IMPLEMENTED, "QA loop; LLM repair when provider present else generator fallback", "mas.squad.squad"),
    Capability("hr_gap_analysis", CapabilityStatus.IMPLEMENTED, "LLM analysis with keyword catalog fallback", "mas.organization.hr"),
    Capability("enterprise_engagement", CapabilityStatus.IMPLEMENTED, "Multi-phase departmental consulting workflow with state checkpointing & dispatch gates", "mas.organization.engagement"),
    Capability("demo_echo_agents", CapabilityStatus.IMPLEMENTED, "Deterministic zero-key topology demo runners for offline verification", "main"),
    Capability("distributed_swarm_auth", CapabilityStatus.IMPLEMENTED, "Swarm relay with token auth", "mas.core.swarm"),
    Capability("visual_diff_gate", CapabilityStatus.IMPLEMENTED, "Pixel RMSE visual regression", "mas.tools.visual_diff"),
    Capability("eval_harness", CapabilityStatus.IMPLEMENTED, "Golden missions + structural/quality scoring", "mas.eval"),
    Capability("cli_doctor", CapabilityStatus.IMPLEMENTED, "Runtime health / mode report", "mas.cli"),
    Capability("multi_tenant_iam", CapabilityStatus.IMPLEMENTED, "OAuth/PAB PBAC/RBAC tenant isolation + HMAC token auth + workspace jailing", "mas.iam"),
    Capability("managed_vector_saas", CapabilityStatus.DEMO_ONLY, "Local in-memory cloud adapter simulations; no remote persistence", "mas.memory.vector_saas"),
    Capability("computer_use", CapabilityStatus.IMPLEMENTED, "Virtual Xvfb display + discrete OS mouse/keyboard actions + SoM grounding + Scope Jail", "mas.tools.computer_use"),
    Capability("bigquery_finops_sql", CapabilityStatus.IMPLEMENTED, "Native Google Cloud BigQuery execution + dry-run cost estimation + mandatory labeling", "mas.tools.bigquery_tool"),
    Capability("data_contract_validator", CapabilityStatus.IMPLEMENTED, "YAML Data Contract validation asserting schema, nullability, uniqueness & enums", "mas.tools.data_contract_tool"),
    Capability("gcs_storage_manager", CapabilityStatus.IMPLEMENTED, "GCS CLI bucket listing and object reading; requires authenticated gcloud", "mas.tools.storage_tool"),
    Capability("agent_to_agent_delegation", CapabilityStatus.IMPLEMENTED, "Dynamic subtask delegation to specialized agent personas within ReAct loop", "mas.tools.delegation_tool"),
    Capability("surgical_file_patching", CapabilityStatus.IMPLEMENTED, "Surgical contiguous line replacement preventing full-file overwrite token bloat", "mas.tools.patch_tool"),
    Capability("research_knowledge_vault_rag", CapabilityStatus.IMPLEMENTED, "Active full-text retrieval across 8-volume AI Encyclopedia and research archives", "mas.tools.knowledge_vault_tool"),
    Capability("human_in_the_loop_gate", CapabilityStatus.IMPLEMENTED, "Structured clarification question queue with interactive and autonomous resolution", "mas.tools.hitl_tool"),
    Capability("popia_pii_anonymizer", CapabilityStatus.IMPLEMENTED, "POPIA & GDPR compliance tool redacting South African IDs (Luhn), cards, emails & phones", "mas.tools.pii_tool"),
    Capability("native_pm_board", CapabilityStatus.IMPLEMENTED, "Agent-native Scrum/Kanban board, FSM engine, Little's Law WIP, and cryptographic evidence verification", "mas.pm"),
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
