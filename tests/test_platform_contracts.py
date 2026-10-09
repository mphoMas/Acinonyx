"""Consolidation evidence admission: malformed claims and cross-task provenance."""
import copy
import json
import time

import pytest
from pydantic import ValidationError

from mas.platform.coding import validate_coding_evidence
from mas.platform.contracts import ContractError, TaskIdentity, VerificationEvidence
from mas.swarm.contracts import SwarmError, digest

IMAGE = "python@sha256:" + "a" * 64


def fixture():
    source = "def solve(payload):\n    return payload\n"
    cases = [{"id": "identity", "input": 7, "expected": 7}]
    doc = {"tenant": "alpha", "id": "task", "lease": "attempt", "source": source,
           "candidate_hash": digest(source), "image": IMAGE, "provider": {"model": "fixture"}, "request": {"cases": cases}}
    evidence = {"run_id": "task", "candidate_hash": digest(source), "suite_hash": digest(cases), "image": IMAGE,
                "provider": doc["provider"], "results": [{"id": "identity", "passed": True, "status": "passed"}], "finished": time.time()}
    return doc, evidence


def shared():
    doc, evidence = fixture()
    return VerificationEvidence(identity=TaskIdentity(tenant_id="alpha", task_id="task", attempt_id="attempt", workflow="coding.solve.v1"),
                                candidate_hash=doc["candidate_hash"], suite_hash=evidence["suite_hash"], executor_image=IMAGE,
                                verifier="coding-json-equality.v1", results=({"case_id": "identity", "passed": True, "status": "passed"},),
                                finished=evidence["finished"])


def test_existing_evidence_format_is_preserved_without_mutation():
    doc, evidence = fixture()
    before = copy.deepcopy((doc, evidence))
    assert validate_coding_evidence(doc, evidence, IMAGE) is evidence
    assert (doc, evidence) == before


@pytest.mark.parametrize("field,value", [
    ("run_id", "other"), ("candidate_hash", "b" * 64), ("suite_hash", "b" * 64),
    ("image", "sha256:" + "b" * 64), ("provider", {"model": "other"}),
    ("finished", float("nan")), ("finished", float("inf")), ("finished", True),
    ("results", []), ("extra", "claim"),
    ("results", [{"id": "identity", "passed": True, "status": "mismatch"}]),
    ("results", [{"id": "identity", "passed": "true", "status": "passed"}]),
    ("results", [{"id": "identity", "passed": True, "status": "passed", "claim": "all passed"}]),
    ("results", [{"id": "other", "passed": True, "status": "passed"}]),
    ("results", [{"id": "identity", "passed": True, "status": "passed"}] * 2),
])
def test_coding_adapter_denies_fabricated_or_mismatched_evidence(field, value):
    doc, evidence = fixture()
    evidence[field] = value
    with pytest.raises(SwarmError):
        validate_coding_evidence(doc, evidence, IMAGE)


@pytest.mark.parametrize("field,value", [("source", "def solve(payload): return 0"), ("image", "sha256:" + "b" * 64)])
def test_trusted_run_artifact_must_match_execution(field, value):
    doc, evidence = fixture()
    doc[field] = value
    with pytest.raises(SwarmError):
        validate_coding_evidence(doc, evidence, IMAGE)


@pytest.mark.parametrize("field,value", [("tenant_id", "beta"), ("task_id", "other"), ("attempt_id", "replayed")])
def test_evidence_cannot_bind_to_another_tenant_task_or_attempt(field, value):
    evidence = shared()
    identity = evidence.identity.model_copy(update={field: value})
    with pytest.raises(ContractError):
        evidence.bind(identity, evidence.candidate_hash, evidence.suite_hash, IMAGE, ("identity",))


@pytest.mark.parametrize("raw", [
    '{"schema_version":1,"schema_version":2}', '{"schema_version":true}',
    '{"schema_version":2}', '{"finished":NaN}', '{"finished":Infinity}', '[]',
    '{"payload":"' + 'x' * 65536 + '"}',
])
def test_untrusted_json_contract_rejects_ambiguity_and_oversize(raw):
    with pytest.raises(ContractError):
        VerificationEvidence.from_json(raw)


def test_shared_evidence_is_immutable_and_roundtrips_json():
    evidence = shared()
    assert VerificationEvidence.from_json(evidence.model_dump_json()) == evidence
    with pytest.raises(ValidationError):
        evidence.identity.tenant_id = "beta"
    with pytest.raises(ValidationError):
        evidence.results[0].passed = False
    assert json.loads(evidence.model_dump_json())["schema_version"] == 1


def test_observed_failure_is_valid_evidence_but_not_success():
    doc, evidence = fixture()
    evidence["results"][0].update(passed=False, status="invalid_execution")
    assert validate_coding_evidence(doc, evidence, IMAGE)["results"][0]["passed"] is False
