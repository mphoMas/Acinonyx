"""mas.authority: Process-wide authority guard synchronizing tenant/connector mutations with receipt transactions.

Enforces serialized ordering between IAM tenant/session revocations, connector registry mutations,
and durable receipt admissions within a single-process host environment.
"""

from __future__ import annotations

import threading
from typing import Optional


class AuthorityGuard:
    """Process-wide authority guard synchronizing tenant/connector mutations with receipt transactions."""

    def __init__(self, lock: Optional[threading.RLock] = None) -> None:
        self._lock = lock or threading.RLock()

    def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
        return self._lock.acquire(blocking, timeout)

    def release(self) -> None:
        self._lock.release()

    def __enter__(self) -> AuthorityGuard:
        self._lock.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._lock.release()


_GLOBAL_AUTHORITY_GUARD = AuthorityGuard()


def get_authority_guard() -> AuthorityGuard:
    """Returns the shared process-wide authority guard."""
    return _GLOBAL_AUTHORITY_GUARD
