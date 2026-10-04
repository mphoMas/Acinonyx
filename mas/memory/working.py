"""
mas.memory.working: Sliding-window working memory with system message pinning and eviction hooks.
Architect: Acinonyx
"""

from __future__ import annotations
from typing import Callable, List, Optional
from mas.core.message import Message, Role


class WorkingMemory:
    """
    In-context working memory buffer managing active dialogue turns,
    preserving pinned system instructions, and evicting older messages.
    """

    def __init__(self, capacity: int = 20, eviction_callback: Optional[Callable[[List[Message]], None]] = None) -> None:
        self.capacity: int = capacity
        self._pinned_messages: List[Message] = []
        self._buffer: List[Message] = []
        self.eviction_callback = eviction_callback

    def add(self, message: Message, pin: bool = False) -> None:
        """Add a message to working memory. Pinned messages are exempt from capacity eviction."""
        if pin or message.role == Role.SYSTEM:
            self._pinned_messages.append(message)
            return

        self._buffer.append(message)
        if len(self._buffer) > self.capacity:
            overflow_count = len(self._buffer) - self.capacity
            evicted = self._buffer[:overflow_count]
            self._buffer = self._buffer[overflow_count:]
            if self.eviction_callback:
                self.eviction_callback(evicted)

    def get_context(self) -> List[Message]:
        """Return combined pinned instructions followed by chronological active buffer."""
        return list(self._pinned_messages) + list(self._buffer)

    def clear(self, keep_pinned: bool = True) -> None:
        self._buffer.clear()
        if not keep_pinned:
            self._pinned_messages.clear()

    def count(self) -> int:
        return len(self._pinned_messages) + len(self._buffer)

    def total_tokens(self) -> int:
        tokens = 0
        for m in self.get_context():
            if m.token_usage:
                tokens += m.token_usage.total_tokens
        return tokens
