#!/usr/bin/env python3
"""
scripts/mas_mcp_stdio.py: Stdio MCP Server integrating MAS-Core directly into Google Antigravity IDE.
Communicates via standard JSON-RPC 2.0 over stdin/stdout.

Architect: Acinonyx
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

# Ensure project root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from mas.organization.company import AcinonyxEnterprise
from mas.organization.engagement import ConsultingEngagement, EngagementArtifacts
from mas.tools.git_tool import git_branch_tool


# Global singleton instance for stdio session
_ENTERPRISE: Optional[AcinonyxEnterprise] = None
_LATEST_ARTIFACTS: Optional[EngagementArtifacts] = None


def get_enterprise() -> AcinonyxEnterprise:
    global _ENTERPRISE
    if _ENTERPRISE is None:
        _ENTERPRISE = AcinonyxEnterprise()
    return _ENTERPRISE


# ---------------------------------------------------------------------------
# Tool Implementations
# ---------------------------------------------------------------------------

async def tool_mas_projects(arguments: Dict[str, Any]) -> str:
    """List registered project workspaces and dispatch state."""
    ent = get_enterprise()
    allowed = ent.state_machine.get("allowed_projects", [])
    current = ent.state_machine.get("current_client", "Idle")
    is_live = ent.is_live_dispatch_enabled()

    lines = [
        "### MAS Project Registry",
        f"• **Current Client:** {current}",
        f"• **Live Dispatch:** {'ARMED (Live Execution)' if is_live else 'STAGED (Preview / Dry-Run)'}",
        "• **Allowed Project Roots:**",
    ]
    for p in allowed:
        lines.append(f"  - `{p}`")
    return "\n".join(lines)


async def tool_mas_submit_task(arguments: Dict[str, Any]) -> str:
    """Submit an RFP or consulting mandate to the enterprise squad."""
    global _LATEST_ARTIFACTS
    ent = get_enterprise()
    client_name = arguments.get("client_name", "Enterprise Client")
    rfp = arguments.get("rfp", "")

    if not rfp:
        return "ERROR: Missing required argument 'rfp'."

    engagement = ConsultingEngagement(ent)
    artifacts = await engagement.execute_engagement(client_name=client_name, raw_rfp=rfp)
    _LATEST_ARTIFACTS = artifacts

    return (
        f"✅ Consulting Engagement for '{client_name}' executed successfully!\n"
        f"• Newly Hired Specialists: {', '.join(artifacts.newly_hired_agents) if artifacts.newly_hired_agents else 'None (existing staff covered all domains)'}\n"
        f"• Total Headcount: {ent.get_headcount()} agents\n"
        f"• Checkpoint: staffed_{client_name}\n\n"
        f"Use `mas_inspect_artifact` to view PRD, Design System, Engineering, or Sign-off."
    )


async def tool_mas_get_status(arguments: Dict[str, Any]) -> str:
    """Inspect enterprise headcount, departments, checkpoints, and event stats."""
    ent = get_enterprise()
    stats = ent.event_bus.stats
    lines = [
        f"### {ent.name} Status",
        f"• Status: {ent.state_machine.get('company_status', 'active').upper()}",
        f"• Headcount: {ent.get_headcount()} agents",
        f"• Engagements Completed: {ent.state_machine.get('total_engagements', 0)}",
        f"• Events Routed: {stats.get('published_count', 0)}",
        f"• Tokens Routed: {stats.get('total_tokens_routed', 0)}",
        "",
        "**Departments & Roster:**",
    ]
    for dept_type, dept in ent.departments.items():
        agents = ", ".join(dept.list_agents()) or "[Empty]"
        lines.append(f"• **{dept_type.value.replace('_', ' ').title()}** ({dept.headcount}): {agents}")

    return "\n".join(lines)


async def tool_mas_inspect_artifact(arguments: Dict[str, Any]) -> str:
    """Read PRD, Design System, Specialist Audits, or Delivery Sign-off."""
    global _LATEST_ARTIFACTS
    if _LATEST_ARTIFACTS is None:
        return "No engagement artifacts generated yet. Use `mas_submit_task` first."

    target = arguments.get("target", "brief").lower()
    art = _LATEST_ARTIFACTS

    if target in ("brief", "client_brief"):
        return f"### Client Brief ({art.client_name})\n\n{art.client_brief}"
    elif target in ("prd", "requirements"):
        return f"### Product Requirements Document\n\n{art.prd}"
    elif target in ("design", "design_system"):
        return f"### Design System Specs\n\n{art.design_system}"
    elif target in ("audits", "specialist"):
        if not art.specialist_audits:
            return "No specialist audits recorded for this engagement."
        return "\n\n".join(f"=== {k.upper()} ===\n{v}" for k, v in art.specialist_audits.items())
    elif target in ("eng", "engineering"):
        return f"### Engineering Synthesis\n\n{art.engineering_summary}"
    elif target in ("gtm", "marketing"):
        return f"### Go-To-Market Package\n\n{art.gtm_package}"
    elif target in ("signoff", "delivery"):
        return f"### Delivery Sign-off\n\n{art.delivery_signoff}"
    else:
        return f"Unknown artifact target '{target}'. Valid options: brief, prd, design, audits, eng, gtm, signoff."


async def tool_mas_cio_audit(arguments: Dict[str, Any]) -> str:
    """Trigger a live infrastructure and software inventory."""
    ent = get_enterprise()
    report = await ent.cio.run_infrastructure_audit()
    return report.to_markdown()


async def tool_mas_git_branch(arguments: Dict[str, Any]) -> str:
    """Create or inspect git branches for project artifacts."""
    repo_path = arguments.get("repo_path", "/home/acinonyx/Desktop/MAS")
    branch_name = arguments.get("branch_name", "")
    res = await git_branch_tool(repo_path=repo_path, branch_name=branch_name)
    return json.dumps(res, indent=2)


async def tool_mas_search_memory(arguments: Dict[str, Any]) -> str:
    """Semantic vector search over episodic memory reflections."""
    ent = get_enterprise()
    query = arguments.get("query", "")
    if not query:
        return "ERROR: Missing 'query' argument."

    # Search through lead engineer's episodic vector memory
    results = ent.lead_engineer.episodic_memory.retrieve_relevant_reflections(query, limit=3)
    if not results:
        return f"No episodic reflections found matching '{query}'."

    lines = [f"### Episodic Memory Search Results for '{query}':"]
    for i, r in enumerate(results, 1):
        status = "SUCCESS" if r.success else "FAILURE"
        lines.append(f"{i}. [{status}] (Relevance: {r.similarity_score:.2f}) Task: {r.task}")
        lines.append(f"   Critique: {r.critique}")
        lines.append(f"   Strategy: {r.suggested_strategy}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool Catalog Metadata
# ---------------------------------------------------------------------------

TOOLS_CATALOG = [
    {
        "name": "mas_projects",
        "description": "List registered project roots, current client, and live dispatch state in MAS-Core.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mas_submit_task",
        "description": "Submit a client RFP or consulting mission to the autonomous MAS enterprise squad.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Name of the client entity"},
                "rfp": {"type": "string", "description": "Project requirements or RFP description"},
            },
            "required": ["rfp"],
        },
    },
    {
        "name": "mas_get_status",
        "description": "Inspect MAS corporate status, department roster, event statistics, and checkpoints.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mas_inspect_artifact",
        "description": "Inspect deliverables from the latest engagement (brief, prd, design, audits, eng, gtm, signoff).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Artifact type: brief, prd, design, audits, eng, gtm, signoff",
                }
            },
        },
    },
    {
        "name": "mas_cio_audit",
        "description": "Perform live CIO infrastructure, hardware, binary, and workspace audit.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mas_git_branch",
        "description": "Inspect or create git branches in the MAS workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "branch_name": {"type": "string", "description": "Branch name to create/checkout (or empty to list)"},
                "repo_path": {"type": "string", "description": "Path to git repository"},
            },
        },
    },
    {
        "name": "mas_search_memory",
        "description": "Perform semantic vector search over episodic memory reflections using SQLite vector engine.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Conceptual search query (e.g. rate limit error, database timeout)"},
            },
            "required": ["query"],
        },
    },
]

TOOL_HANDLERS = {
    "mas_projects": tool_mas_projects,
    "mas_submit_task": tool_mas_submit_task,
    "mas_get_status": tool_mas_get_status,
    "mas_inspect_artifact": tool_mas_inspect_artifact,
    "mas_cio_audit": tool_mas_cio_audit,
    "mas_git_branch": tool_mas_git_branch,
    "mas_search_memory": tool_mas_search_memory,
}


# ---------------------------------------------------------------------------
# JSON-RPC 2.0 Stdio Loop
# ---------------------------------------------------------------------------

async def handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method")
    req_id = req.get("id")

    # Notifications (no id)
    if req_id is None:
        return None

    # MCP Protocol Methods
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mas-coordinator", "version": "1.0.0"},
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS_CATALOG},
        }

    elif method == "tools/call":
        params = req.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        handler = TOOL_HANDLERS.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {tool_name}"},
            }

        try:
            output_text = await handler(arguments)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": output_text}],
                },
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"EXECUTION_ERROR: {str(e)}"}],
                    "isError": True,
                },
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown MCP method: {method}"},
        }


async def main_loop():
    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        text = line.decode("utf-8").strip()
        if not text:
            continue

        try:
            req = json.loads(text)
            resp = await handle_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as ex:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(ex)}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    asyncio.run(main_loop())
