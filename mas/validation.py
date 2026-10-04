"""
mas.validation: Strict payload validation at bus and pipeline edges (Pydantic-class API, zero dep).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from mas.core.message import ContentType, Message, Role


class ValidationError(ValueError):
    """Raised when a payload fails schema or message-edge validation."""


@dataclass
class SchemaSpec:
    """Minimal JSON-Schema-like validator for pipeline artifacts."""

    required_keys: List[str] = None
    min_length: int = 1
    must_contain: List[str] = None
    json_object: bool = False
    pattern: Optional[str] = None

    def __post_init__(self) -> None:
        self.required_keys = self.required_keys or []
        self.must_contain = self.must_contain or []


def validate_message(message: Message) -> Message:
    """Reject silent/invalid cross-agent messages at the bus edge."""
    if not isinstance(message, Message):
        raise ValidationError("EventBus only accepts Message instances")
    if not message.sender or not str(message.sender).strip():
        raise ValidationError("Message.sender is required")
    if not message.recipient or not str(message.recipient).strip():
        raise ValidationError("Message.recipient is required")
    if not isinstance(message.role, Role):
        raise ValidationError("Message.role must be a Role enum")
    if not isinstance(message.content_type, ContentType):
        raise ValidationError("Message.content_type must be a ContentType enum")
    if message.content is None:
        raise ValidationError("Message.content cannot be None")
    if not isinstance(message.content, str):
        raise ValidationError("Message.content must be a string")
    if message.metadata is None or not message.metadata.correlation_id:
        raise ValidationError("Message.metadata.correlation_id is required")
    return message


def validate_against_schema(content: str, schema: SchemaSpec) -> Tuple[bool, str]:
    """Validate stage output; returns (ok, reason)."""
    if content is None:
        return False, "content is None"
    text = content.strip()
    if len(text) < schema.min_length:
        return False, f"content shorter than min_length={schema.min_length}"

    for needle in schema.must_contain:
        if needle not in text:
            return False, f"missing required substring: {needle!r}"

    if schema.pattern and not re.search(schema.pattern, text, re.IGNORECASE | re.DOTALL):
        return False, f"content does not match pattern: {schema.pattern}"

    if schema.json_object or schema.required_keys:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            return False, f"expected JSON object: {exc}"
        if not isinstance(data, dict):
            return False, "JSON payload must be an object"
        for key in schema.required_keys:
            if key not in data:
                return False, f"missing required JSON key: {key}"

    return True, "ok"


def require_grounding(content: str, evidence_ids: List[str]) -> None:
    """Invariant 1: claims that assert facts must cite observation ids when evidence exists."""
    if not evidence_ids:
        return
    lower = content.lower()
    if any(marker in lower for marker in ("therefore", "confirmed", "verified", "proves")):
        if not any(eid in content for eid in evidence_ids):
            raise ValidationError(
                "Ungrounded claim: factual language used without citing tool/memory evidence ids"
            )
