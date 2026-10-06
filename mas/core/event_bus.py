"""
mas.core.event_bus: Asynchronous, topic-routed, auditable message bus.
Architect: Acinonyx
"""

from __future__ import annotations
import asyncio
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional
from mas.core.message import Message
from mas.validation import validate_message


SubscriberCallback = Callable[[Message], Coroutine[Any, Any, None]]
MiddlewareCallback = Callable[[Message], Coroutine[Any, Any, Optional[Message]]]


class EventBus:
    """
    Asynchronous event bus supporting topic routing, recipient filtering,
    pluggable middleware, edge validation, and durable JSONL audit trails.
    """

    def __init__(
        self,
        log_history: bool = True,
        audit_path: Optional[str | Path] = None,
        validate: bool = True,
    ) -> None:
        self._subscribers: Dict[str, Dict[str, SubscriberCallback]] = defaultdict(dict)
        self._wildcard_subscribers: Dict[str, SubscriberCallback] = {}
        self._middleware: List[MiddlewareCallback] = []
        self._history: List[Message] = []
        self._log_history: bool = log_history
        self._lock = asyncio.Lock()
        self._published_count: int = 0
        self._total_tokens_routed: int = 0
        self._swarm_node = None
        self._validate = validate
        self._audit = None
        if audit_path is not None:
            from mas.audit import JsonlAuditLog
            self._audit = JsonlAuditLog(audit_path)
        else:
            try:
                from mas.audit import get_audit_log
                from mas.config import CONFIG
                # Lazy default audit under workspace
                CONFIG.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
                self._audit = get_audit_log()
            except Exception:
                self._audit = None

    def attach_swarm(self, swarm_node: Any) -> None:
        """Attach a SwarmNode to replicate events across distributed swarm hosts."""
        self._swarm_node = swarm_node

    def add_middleware(self, middleware: MiddlewareCallback) -> None:
        """Register an async middleware that inspects or transforms messages prior to dispatch."""
        self._middleware.append(middleware)

    def subscribe(
        self,
        subscriber_id: str,
        callback: SubscriberCallback,
        topic: str = "*",
    ) -> None:
        """Subscribe an agent callback to a specific topic or wildcard '*'."""
        if topic == "*":
            self._wildcard_subscribers[subscriber_id] = callback
        else:
            self._subscribers[topic][subscriber_id] = callback

    def unsubscribe(self, subscriber_id: str, topic: Optional[str] = None) -> None:
        """Unsubscribe an agent from a topic or from all topics."""
        if topic is None or topic == "*":
            self._wildcard_subscribers.pop(subscriber_id, None)
            for topic_dict in self._subscribers.values():
                topic_dict.pop(subscriber_id, None)
        else:
            if topic in self._subscribers:
                self._subscribers[topic].pop(subscriber_id, None)

    async def publish(self, message: Message) -> List[asyncio.Task]:
        """
        Publish a message across the bus. Runs through middleware, checks recipient
        and topic filters, logs to audit history, and dispatches to subscribers.
        """
        if self._validate:
            validate_message(message)

        current_msg: Optional[Message] = message

        # Pass through middleware pipeline
        for mw in self._middleware:
            current_msg = await mw(current_msg)
            if current_msg is None:
                # Message was dropped by middleware
                return []
            if self._validate:
                validate_message(current_msg)

        async with self._lock:
            self._published_count += 1
            if current_msg.token_usage:
                self._total_tokens_routed += current_msg.token_usage.total_tokens
            if self._log_history:
                self._history.append(current_msg)
            if self._audit is not None:
                try:
                    self._audit.append_message(current_msg)
                except Exception:
                    pass

        topic = current_msg.metadata.topic
        recipient = current_msg.recipient
        sender = current_msg.sender

        # Determine target callbacks
        target_callbacks: Dict[str, SubscriberCallback] = {}

        # 1. Exact topic matches
        if topic in self._subscribers:
            for sub_id, cb in self._subscribers[topic].items():
                if sub_id != sender and (recipient in ("broadcast", "*", sub_id)):
                    target_callbacks[sub_id] = cb

        # 2. Wildcard subscribers
        for sub_id, cb in self._wildcard_subscribers.items():
            if sub_id != sender and (recipient in ("broadcast", "*", sub_id)):
                target_callbacks[sub_id] = cb

        # Dispatch asynchronously to all targets
        tasks: List[asyncio.Task] = []
        for cb in target_callbacks.values():
            tasks.append(asyncio.create_task(cb(current_msg)))

        # Replicate across swarm if attached and not an incoming replica
        if self._swarm_node and not current_msg.metadata.extra.get("swarm_replicated"):
            tasks.append(asyncio.create_task(self._swarm_node.publish_to_swarm(current_msg)))

        return tasks

    def get_history(self, topic: Optional[str] = None, recipient: Optional[str] = None) -> List[Message]:
        """Retrieve audit history with optional filters."""
        msgs = self._history
        if topic:
            msgs = [m for m in msgs if m.metadata.topic == topic]
        if recipient:
            msgs = [m for m in msgs if m.recipient in (recipient, "broadcast", "*")]
        return list(msgs)

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "published_count": self._published_count,
            "total_tokens_routed": self._total_tokens_routed,
            "active_topics": list(self._subscribers.keys()),
            "wildcard_subscribers": list(self._wildcard_subscribers.keys()),
            "history_size": len(self._history),
            "audit_enabled": self._audit is not None,
        }
