"""
mas.core.agent: Base autonomous agent implementing the CoALA cognitive lifecycle.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from mas.core.event_bus import EventBus
from mas.core.message import ContentType, Message, Role, TokenUsage, MessageMetadata
from mas.mcp.transport import MCPClient
from mas.observability import METRICS, LOGGER

if TYPE_CHECKING:
    from mas.memory.episodic import EpisodicMemory, Reflection
    from mas.memory.working import WorkingMemory


class BaseAgent:
    """
    Autonomous Agent implementing the CoALA cognitive architecture:
    Perception -> Working Memory (+ episodic retrieval) -> Reasoning -> MCP Actions -> Reflection.
    """

    def __init__(
        self,
        name: str,
        role: Role = Role.ASSISTANT,
        system_prompt: str = "You are an autonomous AI agent.",
        working_memory_capacity: int = 25,
        event_bus: Optional[EventBus] = None,
        episodic_memory: Optional[Any] = None,
        mcp_client: Optional[MCPClient] = None,
        llm_provider: Optional[Any] = None,
        retrieve_reflections: bool = True,
        require_grounding: bool = False,
    ) -> None:
        from mas.memory.working import WorkingMemory
        from mas.memory.episodic import EpisodicMemory

        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.working_memory = WorkingMemory(capacity=working_memory_capacity)
        self.episodic_memory = episodic_memory or EpisodicMemory()
        self.event_bus = event_bus
        self.mcp_client = mcp_client
        self.llm_provider = llm_provider
        self.retrieve_reflections = retrieve_reflections
        self.require_grounding = require_grounding
        self._is_active = True
        self.total_tokens_consumed = 0
        self._evidence_ids: List[str] = []

        # Pin system prompt into working memory
        sys_msg = Message(
            sender="system",
            recipient=self.name,
            role=Role.SYSTEM,
            content=self.system_prompt,
        )
        self.working_memory.add(sys_msg, pin=True)

    def attach_event_bus(self, event_bus: EventBus, topic: str = "*") -> None:
        """Attach agent to an event bus and register incoming message listener."""
        self.event_bus = event_bus
        self.event_bus.subscribe(self.name, self._on_bus_message, topic=topic)

    async def _on_bus_message(self, message: Message) -> None:
        """Callback invoked when a message targeted at this agent is published to the bus."""
        if not self._is_active:
            return
        await self.step(message)

    async def perceive(self, message: Message) -> None:
        """Ingest an external percept/message into working memory."""
        self.working_memory.add(message)
        if message.token_usage:
            self.total_tokens_consumed += message.token_usage.total_tokens

    def _inject_episodic_context(self, query: str) -> None:
        """Pull top-k prior reflections into working memory before reasoning."""
        if not self.retrieve_reflections:
            return
        try:
            reflections = self.episodic_memory.retrieve_relevant_reflections(query, limit=3)
        except Exception:
            reflections = []
        if not reflections:
            return
        lines = []
        for ref in reflections:
            rid = getattr(ref, "id", "unknown")
            critique = getattr(ref, "critique", "")
            strategy = getattr(ref, "suggested_strategy", "")
            lines.append(f"- [{rid}] critique={critique} strategy={strategy}")
            self._evidence_ids.append(str(rid))
        mem_msg = Message(
            sender="episodic_memory",
            recipient=self.name,
            role=Role.SYSTEM,
            content="Retrieved episodic reflections (cite ids when making factual claims):\n" + "\n".join(lines),
            content_type=ContentType.REFLECTION,
        )
        self.working_memory.add(mem_msg)

    async def reason(self, context_messages: List[Message]) -> str:
        """
        Reasoning Controller.
        If an LLMProvider is attached, executes inference and handles any MCP tool calls
        in a ReAct reasoning loop.
        Otherwise, acts as a deterministic echo/pass-through (demo mode).
        """
        if self.llm_provider:
            available_tools = await self.mcp_client.list_tools() if self.mcp_client else None

            # ReAct Loop (up to 5 iterative tool turns)
            for _ in range(5):
                resp = await self.llm_provider.generate(context_messages, tools=available_tools)
                if resp.token_usage:
                    self.total_tokens_consumed += resp.token_usage.total_tokens
                    METRICS.incr("tokens.total", resp.token_usage.total_tokens)

                if not resp.tool_calls:
                    content = resp.content
                    if self.require_grounding and self._evidence_ids:
                        from mas.validation import require_grounding
                        try:
                            require_grounding(content, self._evidence_ids)
                        except Exception as exc:
                            LOGGER.warning("grounding check: %s", exc)
                    return content

                if self.mcp_client:
                    for tc in resp.tool_calls:
                        METRICS.incr("tools.calls")
                        tool_result = await self.mcp_client.call_tool(
                            tc.name,
                            tc.arguments,
                            principal=self.name,
                        )
                        evidence_id = f"tool:{tc.name}:{len(self._evidence_ids)}"
                        self._evidence_ids.append(evidence_id)
                        tool_msg = Message(
                            sender="mcp_tool",
                            recipient=self.name,
                            role=Role.TOOL,
                            content=f"Tool [{tc.name}] id={evidence_id} Result:\n{tool_result}",
                            content_type=ContentType.TOOL_RESULT,
                            metadata=MessageMetadata(extra={"evidence_id": evidence_id}),
                        )
                        self.working_memory.add(tool_msg)
                    context_messages = self.working_memory.get_context()
                else:
                    return resp.content

            return resp.content

        last_msg = context_messages[-1] if context_messages else None
        content = last_msg.content if last_msg else ""
        return f"Processed[{self.name}]: {content}"

    async def act(
        self,
        thought_or_action: str,
        recipient: str = "broadcast",
        topic: str = "general",
        content_type: ContentType = ContentType.TEXT,
        token_usage: Optional[TokenUsage] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Execute an action by creating and publishing an outgoing message or invoking MCP.
        """
        msg = Message(
            sender=self.name,
            recipient=recipient,
            role=self.role,
            content=thought_or_action,
            content_type=content_type,
            token_usage=token_usage,
            metadata=MessageMetadata(topic=topic, extra=extra or {}),
        )
        self.working_memory.add(msg)

        if self.event_bus:
            await self.event_bus.publish(msg)

        return msg

    async def reflect(
        self,
        task: str,
        success: bool,
        critique: str,
        suggested_strategy: str,
        tags: Optional[List[str]] = None,
    ) -> Reflection:
        """Record a verbal reflection on task performance into episodic memory."""
        reflection = self.episodic_memory.record_reflection(
            task=task,
            success=success,
            critique=critique,
            suggested_strategy=suggested_strategy,
            tags=tags,
        )
        return reflection

    async def step(self, incoming_message: Message) -> Message:
        """
        Full single-turn lifecycle: Perceive -> Retrieve -> Reason -> Act.
        """
        self._evidence_ids = []
        await self.perceive(incoming_message)
        self._inject_episodic_context(incoming_message.content or "")
        context = self.working_memory.get_context()
        reasoning_output = await self.reason(context)
        out_msg = await self.act(
            thought_or_action=reasoning_output,
            recipient=incoming_message.sender if incoming_message.sender != "system" else "broadcast",
            topic=incoming_message.metadata.topic,
            extra={"evidence_ids": list(self._evidence_ids)} if self._evidence_ids else None,
        )
        METRICS.incr("agent.steps")
        return out_msg
