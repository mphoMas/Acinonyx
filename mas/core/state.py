"""
mas.core.state: Versioned, transactional state machine with immutable checkpointing.
Architect: Acinonyx
"""

from __future__ import annotations
import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class Checkpoint:
    version: int
    name: str
    timestamp: str
    snapshot: Dict[str, Any]


class StateMachine:
    """
    Transactional state manager supporting atomic mutations, versioning,
    checkpoints, and historical rollbacks.
    """

    def __init__(self, initial_state: Optional[Dict[str, Any]] = None) -> None:
        self._current_state: Dict[str, Any] = copy.deepcopy(initial_state) if initial_state else {}
        self._version: int = 0
        self._checkpoints: List[Checkpoint] = []
        self._listeners: List[Callable[[int, Dict[str, Any]], None]] = []

        # Record initial baseline checkpoint
        self.commit_checkpoint("initial")

    @property
    def version(self) -> int:
        return self._version

    @property
    def data(self) -> Dict[str, Any]:
        """Return a deep copy of current state data to preserve encapsulation."""
        return copy.deepcopy(self._current_state)

    def get(self, key: str, default: Any = None) -> Any:
        return copy.deepcopy(self._current_state.get(key, default))

    def set(self, key: str, value: Any) -> int:
        """Mutate a single state key and increment version."""
        self._current_state[key] = copy.deepcopy(value)
        self._version += 1
        self._notify()
        return self._version

    def update(self, delta: Dict[str, Any]) -> int:
        """Batch update state and increment version."""
        for k, v in delta.items():
            self._current_state[k] = copy.deepcopy(v)
        self._version += 1
        self._notify()
        return self._version

    def commit_checkpoint(self, name: str) -> Checkpoint:
        """Record an immutable snapshot of current state."""
        cp = Checkpoint(
            version=self._version,
            name=name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            snapshot=copy.deepcopy(self._current_state),
        )
        self._checkpoints.append(cp)
        return cp

    def rollback_to_checkpoint(self, name_or_version: Any) -> bool:
        """Roll back current state to a named checkpoint or specific version number."""
        target: Optional[Checkpoint] = None
        if isinstance(name_or_version, int):
            for cp in reversed(self._checkpoints):
                if cp.version == name_or_version:
                    target = cp
                    break
        elif isinstance(name_or_version, str):
            for cp in reversed(self._checkpoints):
                if cp.name == name_or_version:
                    target = cp
                    break

        if target is None:
            return False

        self._current_state = copy.deepcopy(target.snapshot)
        self._version += 1  # State mutation occurs on rollback
        self._notify()
        return True

    def add_listener(self, listener: Callable[[int, Dict[str, Any]], None]) -> None:
        self._listeners.append(listener)

    def _notify(self) -> None:
        snap = self.data
        for listener in self._listeners:
            listener(self._version, snap)

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        return [
            {"version": cp.version, "name": cp.name, "timestamp": cp.timestamp}
            for cp in self._checkpoints
        ]
