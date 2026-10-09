"""Version-one immutable task identity and measured verification contracts.

Validation establishes shape and consistency, never caller authority. Bindings
must originate from authenticated stores; model output cannot mint evidence.
"""
from __future__ import annotations

import json
import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ContractError(ValueError):
    """Malformed or mismatched data; never evidence of success."""


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("Unsupported contract version")
        return value

    @classmethod
    def from_json(cls, raw: str | bytes):
        if not isinstance(raw, (str, bytes)) or len(raw.encode() if isinstance(raw, str) else raw) > 65536:
            raise ContractError("Contract exceeds 64 KiB")

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ContractError("Duplicate JSON key")
                result[key] = value
            return result

        def constant(_):
            raise ContractError("Non-finite JSON number")

        try:
            data = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
            # JSON arrays map explicitly to immutable tuples at this boundary.
            if cls is VerificationEvidence and isinstance(data, dict) and isinstance(data.get("results"), list):
                data["results"] = tuple(data["results"])
            return cls.model_validate(data)
        except (ValueError, TypeError, RecursionError) as exc:
            raise ContractError("Invalid contract document") from exc


class TaskIdentity(Contract):
    tenant_id: Identifier
    task_id: Identifier
    attempt_id: Identifier
    workflow: Literal["coding.solve.v1"]


class CaseOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    case_id: Identifier
    passed: bool
    status: Literal["passed", "mismatch", "invalid_execution"]

    @model_validator(mode="after")
    def consistent(self):
        if self.passed != (self.status == "passed"):
            raise ValueError("Case status disagrees with observed outcome")
        return self


class VerificationEvidence(Contract):
    identity: TaskIdentity
    candidate_hash: Hash
    suite_hash: Hash
    executor_image: Annotated[str, Field(pattern=r"^(?:[a-zA-Z0-9][a-zA-Z0-9._:/-]*@)?sha256:[a-f0-9]{64}$")]
    verifier: Literal["coding-json-equality.v1"]
    results: Annotated[tuple[CaseOutcome, ...], Field(min_length=1, max_length=64)]
    finished: Annotated[float, Field(gt=0)]

    @field_validator("finished")
    @classmethod
    def finite(cls, value):
        if not math.isfinite(value):
            raise ValueError("Timestamp must be finite")
        return value

    @model_validator(mode="after")
    def unique_cases(self):
        ids = [case.case_id for case in self.results]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate case outcome")
        return self

    def bind(self, identity: TaskIdentity, candidate_hash: str, suite_hash: str, image: str, case_ids: tuple[str, ...]):
        if (self.identity != identity or self.candidate_hash != candidate_hash or self.suite_hash != suite_hash
                or self.executor_image != image or tuple(case.case_id for case in self.results) != case_ids):
            raise ContractError("Evidence differs from trusted task, artifact or suite")
        return self
