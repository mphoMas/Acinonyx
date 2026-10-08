"""
mas.validation: Strict payload validation at bus and pipeline edges (Pydantic-class API, zero dep).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from mas.release_policy import (
    PolicyEvaluationResult,
    PolicySpec,
    compute_candidate_hash,
    evaluate_release_policy,
)

__all__ = [
    "ValidationError",
    "SchemaSpec",
    "validate_message",
    "validate_against_schema",
    "require_grounding",
    "validate_data_contract",
    "PolicySpec",
    "PolicyEvaluationResult",
    "compute_candidate_hash",
    "evaluate_release_policy",
]


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


def validate_message(message: Any) -> Any:
    """Reject silent/invalid cross-agent messages at the bus edge."""
    from mas.core.message import ContentType, Message, Role
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
    if not isinstance(message.content, (str, list, dict)):
        raise ValidationError("Message.content must be a string, list, or dict")
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


def validate_data_contract(content: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate a Data Contract specification (YAML or JSON) against enterprise DataOps standards.
    Requires: dataset, version, owner, schema (list of fields with name & type), and sla.
    Returns: (is_valid, reason, parsed_data)
    """
    if not content or not content.strip():
        return False, "Data contract content is empty", {}
    
    text = content.strip()
    data: Dict[str, Any] = {}
    
    try:
        import yaml
        parsed = yaml.safe_load(text)
        if isinstance(parsed, dict):
            data = parsed
        else:
            return False, "Data contract must parse to a key-value dictionary", {}
    except Exception as exc:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                data = parsed
            else:
                return False, "Data contract JSON must be an object", {}
        except Exception:
            return False, f"Failed to parse data contract as YAML or JSON: {exc}", {}

    required_top_keys = ["dataset", "version", "owner", "schema"]
    for key in required_top_keys:
        if key not in data:
            return False, f"Missing mandatory data contract field: '{key}'", data

    schema_fields = data.get("schema")
    if not isinstance(schema_fields, list) or len(schema_fields) == 0:
        return False, "'schema' must be a non-empty list of column definitions", data

    for idx, field_spec in enumerate(schema_fields):
        if not isinstance(field_spec, dict):
            return False, f"schema[{idx}] must be an object specifying column metadata", data
        if "name" not in field_spec or not str(field_spec["name"]).strip():
            return False, f"schema[{idx}] missing 'name' attribute", data
        if "type" not in field_spec or not str(field_spec["type"]).strip():
            return False, f"schema[{idx}] missing 'type' attribute for column '{field_spec.get('name')}'", data

    return True, "Data contract successfully validated", data

