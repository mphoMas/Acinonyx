"""
mas.tools.hitl_tool: Human-in-the-Loop (HITL) Clarification & Decision Gate Tool.
Pauses agent execution or logs structured inquiries when requirement ambiguity is detected.

Architect: Acinonyx
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from mas.config import REPO_ROOT
from mas.mcp.protocol import MCPRegistry
from mas.observability import LOGGER, METRICS

HITL_LOG_PATH = f"{REPO_ROOT}/workspace/hitl_inbox.jsonl"


class HumanClarificationManager:
    """Manages interactive human inquiries and decision queues."""

    def __init__(self, log_path: str = HITL_LOG_PATH) -> None:
        self.log_path = log_path
        self._interactive_responder: Optional[Callable[[str, List[str]], str]] = None
        self._ensure_log_dir()

    def _ensure_log_dir(self) -> None:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
        except Exception:
            pass

    def register_interactive_responder(self, responder: Callable[[str, List[str]], str]) -> None:
        """Attach an interactive callback for live UI / chat prompting."""
        self._interactive_responder = responder

    def ask(
        self,
        question: str,
        options: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        opt_list = options or ["Approve & Proceed", "Reject & Abort", "Provide Custom Input"]
        timestamp = datetime.now(timezone.utc).isoformat()
        METRICS.incr("hitl.questions_asked")

        chosen_answer: str
        status: str

        if self._interactive_responder:
            try:
                chosen_answer = self._interactive_responder(question, opt_list)
                status = "user_answered"
            except Exception as e:
                LOGGER.warning(f"Interactive responder error: {e}. Falling back to default option.")
                chosen_answer = opt_list[0]
                status = "fallback_resolved"
        else:
            # Autonomous execution fallback: default to first recommended option
            chosen_answer = opt_list[0]
            status = "auto_resolved"

        entry = {
            "timestamp": timestamp,
            "question": question,
            "options": opt_list,
            "context": context,
            "status": status,
            "chosen_answer": chosen_answer,
        }

        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            LOGGER.error(f"Failed to append to HITL inbox: {e}")

        return {
            "success": True,
            "status": status,
            "question": question,
            "chosen_answer": chosen_answer,
            "options_considered": opt_list,
            "timestamp": timestamp,
        }


# Global HITL manager instance
GLOBAL_HITL_MANAGER = HumanClarificationManager()


def ask_human_clarification_tool(
    question: str,
    options: Optional[List[str]] = None,
    context: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute structured human clarification inquiry."""
    return GLOBAL_HITL_MANAGER.ask(question=question, options=options, context=context)


def register_hitl_tools(registry: MCPRegistry) -> None:
    """Register Human-in-the-Loop clarification tools into MCP."""
    registry.register_tool(
        name="ask_human_clarification",
        description="Prompt the human user for clarification on ambiguous business requirements or critical architectural decisions.",
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The exact question to ask the user"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of distinct selectable response options",
                },
                "context": {"type": "string", "description": "Optional architectural context"},
            },
            "required": ["question"],
        },
        handler=lambda **kwargs: ask_human_clarification_tool(
            question=kwargs["question"],
            options=kwargs.get("options"),
            context=kwargs.get("context"),
        ),
    )
