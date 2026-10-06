"""
mas.core.message: Typed, validated message protocol for multi-agent communication.
Architect: Acinonyx
"""

from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SUPERVISOR = "supervisor"
    CRITIC = "critic"
    MODERATOR = "moderator"


class ContentType(str, Enum):
    TEXT = "text"
    JSON = "json"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    REFLECTION = "reflection"
    ARTIFACT = "artifact"
    IMAGE = "image"
    MULTIMODAL = "multimodal"


@dataclass(frozen=True)
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    @classmethod
    def from_counts(cls, prompt: int, completion: int) -> TokenUsage:
        return cls(prompt_tokens=prompt, completion_tokens=completion, total_tokens=prompt + completion)


@dataclass(frozen=True)
class MessageMetadata:
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    topic: str = "general"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = "system"
    recipient: str = "broadcast"
    role: Role = Role.ASSISTANT
    content: Any = ""
    content_type: ContentType = ContentType.TEXT
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    token_usage: Optional[TokenUsage] = None

    @property
    def text_content(self) -> str:
        """Extract plain text representation even if content is multimodal blocks."""
        if isinstance(self.content, str):
            return self.content
        if isinstance(self.content, list):
            texts = []
            for block in self.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif isinstance(block, str):
                    texts.append(block)
            return " ".join(texts)
        if isinstance(self.content, dict):
            return json.dumps(self.content)
        return str(self.content)

    def create_reply(
        self,
        sender: str,
        content: Any = "",
        role: Role = Role.ASSISTANT,
        content_type: ContentType = ContentType.TEXT,
        token_usage: Optional[TokenUsage] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """Create a causal child reply message referencing this message."""
        reply_meta = MessageMetadata(
            correlation_id=self.metadata.correlation_id,
            parent_id=self.id,
            topic=self.metadata.topic,
            extra=extra or {},
        )
        return Message(
            sender=sender,
            recipient=self.sender,
            role=role,
            content=content,
            content_type=content_type,
            metadata=reply_meta,
            token_usage=token_usage,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "role": self.role.value,
            "content": self.content,
            "content_type": self.content_type.value,
            "metadata": {
                "timestamp": self.metadata.timestamp,
                "correlation_id": self.metadata.correlation_id,
                "parent_id": self.metadata.parent_id,
                "topic": self.metadata.topic,
                "extra": self.metadata.extra,
            },
            "token_usage": asdict(self.token_usage) if self.token_usage else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        meta_data = data.get("metadata", {})
        metadata = MessageMetadata(
            timestamp=meta_data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            correlation_id=meta_data.get("correlation_id", str(uuid.uuid4())),
            parent_id=meta_data.get("parent_id"),
            topic=meta_data.get("topic", "general"),
            extra=meta_data.get("extra", {}),
        )
        tokens_data = data.get("token_usage")
        token_usage = TokenUsage(**tokens_data) if tokens_data else None

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            sender=data.get("sender", "system"),
            recipient=data.get("recipient", "broadcast"),
            role=Role(data.get("role", "assistant")),
            content=data.get("content", ""),
            content_type=ContentType(data.get("content_type", "text")),
            metadata=metadata,
            token_usage=token_usage,
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Message:
        return cls.from_dict(json.loads(json_str))
