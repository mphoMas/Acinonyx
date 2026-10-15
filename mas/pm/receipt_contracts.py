"""Strict version-one quarantined claim shapes; validation grants no authority."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,128}$")]
SHA = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Positive = Annotated[int, Field(ge=1)]
Coordinate = Annotated[str, Field(pattern=r"^[0-9]{1,64}$")]


class ClaimModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class VersionedClaims(ClaimModel):
    schema_version: Literal[1]

    @field_validator("schema_version", mode="before")
    @classmethod
    def exact_version(cls, value):
        if type(value) is not int or value != 1:
            raise ValueError("schema_version must be integer 1")
        return value


class ExecutionClaims(ClaimModel):
    candidate_sha: SHA
    base_sha: SHA
    suite_digest: Digest
    policy_version: Positive
    brief_version: Positive
    source_generation: Positive | None = None


class ReceiptContract(VersionedClaims):
    claims: ExecutionClaims
    check_ids: list[Identifier] = Field(max_length=4096)

    @field_validator("check_ids")
    @classmethod
    def ordered_checks(cls, value):
        if value != sorted(set(value)):
            raise ValueError("check_ids must be strictly sorted and unique")
        return value


class TransportClaims(ClaimModel):
    repository_id: Coordinate
    repository_owner_id: Coordinate
    github_run_id: Coordinate
    github_run_attempt: Positive


class MASClaims(ClaimModel):
    run_id: Identifier
    intent_id: Identifier
    attempt_id: Identifier
    fence: Positive


class ReceiptItem(ClaimModel):
    check_id: Identifier
    claimed_outcome: Literal["PASSED", "FAILED", "SKIPPED", "UNAVAILABLE"]


class ArtifactClaim(ClaimModel):
    # Digest metadata only. No URL, path, bytes or authenticity assertion.
    digest: Digest


class ReceiptPayload(VersionedClaims):
    transport_claims: TransportClaims
    mas_claims: MASClaims
    items: list[ReceiptItem] = Field(max_length=128)
    artifact_claims: list[ArtifactClaim] = Field(max_length=64)
    limitations: str = Field(max_length=8192)

    @model_validator(mode="after")
    def ordered_items(self):
        checks = [item.check_id for item in self.items]
        if checks != sorted(set(checks)):
            raise ValueError("item check_ids must be strictly sorted and unique")
        return self
