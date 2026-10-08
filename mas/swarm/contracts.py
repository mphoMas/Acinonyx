"""Bounded, strict contracts shared by the trusted swarm components."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any


class SwarmError(RuntimeError):
    """A fail-closed workflow error, never evidence of success."""


class CandidateError(SwarmError):
    """Candidate violated execution/result policy, distinct from unavailable infrastructure."""


class OutputLimitError(SwarmError):
    """A subprocess exceeded its output bound."""


def canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (ValueError, TypeError, RecursionError) as exc:
        raise SwarmError("Value is not bounded JSON data") from exc


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def strict_json(raw: str | bytes) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SwarmError("Duplicate JSON key")
            result[key] = value
        return result

    def invalid_constant(_):
        raise SwarmError("Non-finite JSON number")

    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise SwarmError("Non-finite JSON number")
        return result

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant, parse_float=finite_float)
    except (ValueError, TypeError, RecursionError) as exc:
        raise SwarmError("Invalid JSON") from exc


def text(value: Any, name: str, maximum: int = 8192) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode()) > maximum:
        raise SwarmError(f"Invalid or oversized {name}")
    return value


def identifier(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", value):
        raise SwarmError("Invalid identifier")
    return value


def exact_keys(value: Any, keys: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise SwarmError(f"Expected fields: {sorted(keys)}")
    return value


@dataclass(frozen=True)
class Limits:
    deadline_seconds: float = 180
    worker_seconds: float = 5
    provider_seconds: float = 45
    max_tokens: int = 30000
    completion_tokens: int = 2048
    context_bytes: int = 32768
    source_bytes: int = 8192
    output_bytes: int = 32768
    max_cases: int = 32
    parallel_cases: int = 2

    def __post_init__(self):
        for name, value in asdict(self).items():
            if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                raise SwarmError(f"Invalid limit: {name}")
        for name in ("max_tokens", "completion_tokens", "context_bytes", "source_bytes", "output_bytes", "max_cases", "parallel_cases"):
            if type(getattr(self, name)) is not int:
                raise SwarmError(f"Integer required: {name}")
        if self.deadline_seconds > 600 or self.worker_seconds > 30 or self.provider_seconds > 120:
            raise SwarmError("Deadline exceeds operational ceiling")
        if self.max_tokens > 100000 or self.completion_tokens > 8192 or self.completion_tokens > self.max_tokens:
            raise SwarmError("Token limit exceeds ceiling")
        if self.context_bytes > 65536 or self.source_bytes > 16384 or self.output_bytes > 65536:
            raise SwarmError("Byte limit exceeds ceiling")
        if self.max_cases > 64 or self.parallel_cases > 4:
            raise SwarmError("Concurrency/case limit exceeds ceiling")


def cases_contract(cases: Any, limits: Limits) -> list[dict]:
    if not isinstance(cases, list) or not 1 <= len(cases) <= limits.max_cases:
        raise SwarmError("A nonempty bounded operator-owned test suite is required")
    seen = set()
    for case in cases:
        exact_keys(case, {"id", "input", "expected"})
        name = identifier(case["id"])
        if name in seen:
            raise SwarmError("Duplicate test ID")
        seen.add(name)
        if len(canonical(case).encode()) > 8192:
            raise SwarmError("Test case exceeds byte limit")
    # Detach caller-owned mutable structures.
    return strict_json(canonical(cases))
