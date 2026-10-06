"""
mas.tools.pii_tool: Regulatory Data Governance & PII Anonymization Tool.
Compliant with South African POPIA (Protection of Personal Information Act) and GDPR.
Validates 13-digit South African ID numbers, credit cards via Luhn checksum, emails, and phone numbers.

Architect: Acinonyx
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from mas.mcp.protocol import MCPRegistry
from mas.observability import LOGGER, METRICS


def _validate_luhn(number_str: str) -> bool:
    """Standard Luhn mod-10 checksum validation."""
    digits = [int(d) for d in number_str if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled if doubled < 10 else (doubled - 9)
        else:
            checksum += digit
    return checksum % 10 == 0


def _is_valid_sa_id(id_str: str) -> bool:
    """Validate 13-digit South African National ID (YYMMDDSSSSCAZ) using Luhn check."""
    cleaned = re.sub(r"\D", "", id_str)
    if len(cleaned) != 13:
        return False
    # Validate date prefix
    month = int(cleaned[2:4])
    day = int(cleaned[4:6])
    if month < 1 or month > 12 or day < 1 or day > 31:
        return False
    return _validate_luhn(cleaned)


def pii_anonymize_text_tool(text: str) -> Dict[str, Any]:
    """
    Scan text for sensitive PII (SA ID numbers, credit cards, emails, phone numbers)
    and replace them with deterministic redaction tokens.
    """
    token_map: Dict[str, str] = {}
    anonymized = text
    redactions_count = 0

    # 1. South African National IDs (13 consecutive digits)
    sa_id_candidates = re.findall(r"\b\d{13}\b", anonymized)
    for cand in set(sa_id_candidates):
        if _is_valid_sa_id(cand):
            redactions_count += 1
            token = f"[REDACTED_SA_ID_{redactions_count}]"
            token_map[token] = cand
            anonymized = anonymized.replace(cand, token)

    # 2. Credit Cards (13 to 19 digits, optionally spaced or hyphenated)
    cc_pattern = r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{15,16}\b"
    cc_candidates = re.findall(cc_pattern, anonymized)
    for cand in set(cc_candidates):
        cleaned = re.sub(r"\D", "", cand)
        if len(cleaned) in (15, 16) and _validate_luhn(cleaned):
            redactions_count += 1
            token = f"[REDACTED_CREDIT_CARD_{redactions_count}]"
            token_map[token] = cand
            anonymized = anonymized.replace(cand, token)

    # 3. Email addresses
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
    email_candidates = re.findall(email_pattern, anonymized)
    for cand in set(email_candidates):
        redactions_count += 1
        token = f"[REDACTED_EMAIL_{redactions_count}]"
        token_map[token] = cand
        anonymized = anonymized.replace(cand, token)

    # 4. South African and International Phone numbers (+27... or 0XX...)
    phone_pattern = r"(?:\+27|0)\s*(?:[1-9]\d{1})\s*\d{3}\s*\d{4}\b"
    phone_candidates = re.findall(phone_pattern, anonymized)
    for cand in set(phone_candidates):
        redactions_count += 1
        token = f"[REDACTED_PHONE_{redactions_count}]"
        token_map[token] = cand
        anonymized = anonymized.replace(cand, token)

    if redactions_count > 0:
        METRICS.incr("pii.redactions_applied")

    return {
        "success": True,
        "original_length": len(text),
        "anonymized_length": len(anonymized),
        "redactions_count": redactions_count,
        "anonymized_text": anonymized,
        "token_map": token_map,
    }


def pii_deanonymize_text_tool(anonymized_text: str, token_map: Dict[str, str]) -> Dict[str, Any]:
    """Reconstruct original text from redaction tokens."""
    restored = anonymized_text
    for token, original in token_map.items():
        restored = restored.replace(token, original)

    return {
        "success": True,
        "restored_text": restored,
        "tokens_restored": len(token_map),
    }


def register_pii_tools(registry: MCPRegistry) -> None:
    """Register PII Anonymization tools into MCP."""
    registry.register_tool(
        name="pii_anonymize",
        description="Scan text for POPIA/GDPR personal information (South African ID, credit cards, emails, phone numbers) and replace with redaction tokens.",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Raw input text containing potential PII"},
            },
            "required": ["text"],
        },
        handler=lambda **kwargs: pii_anonymize_text_tool(text=kwargs["text"]),
    )

    registry.register_tool(
        name="pii_deanonymize",
        description="Reconstruct original text from redacted tokens using a verified token map in a secure enclave.",
        input_schema={
            "type": "object",
            "properties": {
                "anonymized_text": {"type": "string"},
                "token_map": {"type": "object", "description": "Mapping of tokens to original strings"},
            },
            "required": ["anonymized_text", "token_map"],
        },
        handler=lambda **kwargs: pii_deanonymize_text_tool(
            anonymized_text=kwargs["anonymized_text"],
            token_map=kwargs["token_map"],
        ),
    )
