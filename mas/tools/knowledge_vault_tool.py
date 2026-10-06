"""
mas.tools.knowledge_vault_tool: Full-Text RAG and Research Knowledge Base Retrieval Tool.
Enables MAS agents to actively query the multi-agent research encyclopedia, SDLC standards,
and architecture compendiums during the cognitive ReAct loop.

Architect: Acinonyx
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from mas.mcp.protocol import MCPRegistry
from mas.observability import LOGGER, METRICS

RESEARCH_ROOT = "/home/acinonyx/Desktop/MAS/research"


@dataclass
class KnowledgeSnippet:
    file_path: str
    relative_path: str
    title: str
    section: str
    snippet: str
    score: float


def _score_text(query_terms: List[str], text: str, header: str) -> float:
    text_lower = text.lower()
    header_lower = header.lower()
    score = 0.0

    for term in query_terms:
        if term in header_lower:
            score += 5.0  # Header match weight
        # Count term occurrences in content
        count = text_lower.count(term)
        if count > 0:
            score += min(count * 1.5, 6.0)

    return score


def query_knowledge_vault_tool(
    query: str,
    category: Optional[str] = None,
    max_results: int = 5,
) -> Dict[str, Any]:
    """
    Search the Acinonyx Research Knowledge Base for architecture patterns, papers, and standards.
    Returns ranked document snippets matching the query terms.
    """
    if not os.path.exists(RESEARCH_ROOT):
        return {"success": False, "error": f"Research root not found at '{RESEARCH_ROOT}'"}

    query_terms = [t.lower().strip() for t in re.split(r"\s+", query) if len(t.strip()) > 2]
    if not query_terms:
        return {"success": True, "query": query, "count": 0, "results": []}

    target_dir = RESEARCH_ROOT
    if category and category.lower() != "all":
        cat_clean = category.lower().strip().replace(" ", "_")
        candidate = os.path.join(RESEARCH_ROOT, cat_clean)
        if os.path.exists(candidate):
            target_dir = candidate

    snippets: List[KnowledgeSnippet] = []

    # Traverse markdown files in research directory
    for root, _, files in os.walk(target_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, RESEARCH_ROOT)

            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as doc:
                    content = doc.read()
            except Exception:
                continue

            # Split by markdown headers
            sections = re.split(r"\n(?=#{1,3}\s+)", content)
            doc_title = f
            for sec in sections:
                lines = sec.strip().splitlines()
                if not lines:
                    continue
                first_line = lines[0].strip()
                if first_line.startswith("#"):
                    header = first_line.lstrip("#").strip()
                else:
                    header = doc_title

                body = "\n".join(lines[1:]) if len(lines) > 1 else first_line
                score = _score_text(query_terms, body, header)

                if score > 0:
                    snippet_text = body[:400] + ("..." if len(body) > 400 else "")
                    snippets.append(
                        KnowledgeSnippet(
                            file_path=full_path,
                            relative_path=rel_path,
                            title=header,
                            section=header,
                            snippet=snippet_text.strip(),
                            score=score,
                        )
                    )

    # Sort by descending relevance score
    snippets.sort(key=lambda s: s.score, reverse=True)
    top_results = snippets[: max(1, min(20, max_results))]

    METRICS.incr("knowledge_vault.queries")
    return {
        "success": True,
        "query": query,
        "category_filter": category or "all",
        "count": len(top_results),
        "results": [
            {
                "title": s.title,
                "file": s.relative_path,
                "score": round(s.score, 2),
                "snippet": s.snippet,
            }
            for s in top_results
        ],
    }


def register_knowledge_vault_tools(registry: MCPRegistry) -> None:
    """Register Knowledge Vault tools into MCP."""
    registry.register_tool(
        name="query_knowledge_vault",
        description="Search the enterprise research knowledge base (AI Encyclopedia, CoALA, SDLC, XOps, Computer Use) for authoritative patterns and citations.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords or question topic"},
                "category": {
                    "type": "string",
                    "description": "Optional research category (e.g. 'agentic_systems', 'multi_agent_systems', 'all')",
                    "default": "all",
                },
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
        handler=lambda **kwargs: query_knowledge_vault_tool(
            query=kwargs["query"],
            category=kwargs.get("category"),
            max_results=kwargs.get("max_results", 5),
        ),
    )
