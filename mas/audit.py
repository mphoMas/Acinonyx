"""
mas.audit: Append-only JSONL audit trail for every bus mutation.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from mas.core.message import Message


class JsonlAuditLog:
    """Durable, append-only JSONL sink used by EventBus middleware."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append_message(self, message: Message, event_type: str = "message.publish") -> None:
        record = {
            "event_type": event_type,
            "message": message.to_dict(),
        }
        self.append_record(record)

    def append_record(self, record: Dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
                fh.flush()
                os.fsync(fh.fileno())

    def read_tail(self, n: int = 50) -> list[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        out: list[Dict[str, Any]] = []
        for line in lines[-n:]:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out


_DEFAULT: Optional[JsonlAuditLog] = None


def get_audit_log(path: Optional[str | Path] = None) -> JsonlAuditLog:
    global _DEFAULT
    if path is not None:
        return JsonlAuditLog(path)
    if _DEFAULT is None:
        from mas.config import CONFIG

        _DEFAULT = JsonlAuditLog(CONFIG.audit_log_path)
    return _DEFAULT
