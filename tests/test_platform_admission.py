"""Task admission consistency and persisted coding compatibility, not authority minting."""
import copy
import json
import secrets
import sqlite3
from dataclasses import asdict

import pytest
from pydantic import ValidationError

from mas.platform.coding import validate_coding_admission
from mas.platform.contracts import CodingTaskAdmission, ContractError
from mas.swarm.contracts import Limits, SwarmError, digest
from mas.swarm.store import Store


def submission():
    request = {"goal": "Return input", "cases": [{"id": "identity", "input": 7, "expected": 7}], "limits": asdict(Limits())}
    return {"id": "task", "tenant": "alpha", "submitted_by": "developer", "request": request,
            "request_hash": digest(request), "state": "queued", "version": 0, "created": 123.0}


def admission():
    doc = submission()
    return CodingTaskAdmission(tenant_id=doc["tenant"], task_id=doc["id"], subject_id=doc["submitted_by"],
                               request_key="key", workflow="coding.solve.v1", request_hash=doc["request_hash"],
                               suite_hash=digest(doc["request"]["cases"]), limits=doc["request"]["limits"], created=doc["created"])


def test_submission_is_validated_without_rewriting_signed_document():
    doc = submission()
    before = copy.deepcopy(doc)
    assert validate_coding_admission(doc, "key", {"tenant": "alpha", "subject": "developer"}) is doc
    assert doc == before


@pytest.mark.parametrize("field,value", [
    ("tenant", "beta"), ("submitted_by", "other"), ("request_hash", "b" * 64),
    ("id", "../task"), ("created", float("nan")), ("created", float("inf")), ("created", True),
    ("state", "approved"), ("version", 1), ("version", False),
])
def test_admission_denies_forged_bindings_and_nonfresh_task(field, value):
    doc = submission()
    doc[field] = value
    with pytest.raises(SwarmError):
        validate_coding_admission(doc, "key", {"tenant": "alpha", "subject": "developer"})


@pytest.mark.parametrize("field,value", [
    ("deadline_seconds", 601), ("worker_seconds", 31), ("provider_seconds", 121),
    ("max_tokens", 100001), ("completion_tokens", 8193), ("context_bytes", 65537),
    ("source_bytes", 16385), ("output_bytes", 65537), ("max_cases", 65), ("parallel_cases", 5),
    ("parallel_cases", True), ("max_tokens", "30000"), ("worker_seconds", float("nan")),
    ("worker_seconds", float("inf")), ("provider_seconds", 0), ("extra", 1),
])
def test_admission_cannot_expand_or_coerce_coding_policy(field, value):
    data = admission().model_dump()
    data["limits"][field] = value
    with pytest.raises(ValidationError):
        CodingTaskAdmission.model_validate(data)


def test_changed_request_does_not_retain_old_hash():
    doc = submission()
    doc["request"]["cases"][0]["expected"] = 8
    with pytest.raises(SwarmError):
        validate_coding_admission(doc, "key", {"tenant": "alpha", "subject": "developer"})


def test_admission_roundtrip_is_deeply_immutable_and_binds_request():
    task = admission()
    assert CodingTaskAdmission.from_json(task.model_dump_json()) == task
    with pytest.raises(ValidationError):
        task.limits.parallel_cases = 4
    with pytest.raises(ContractError):
        task.bind("beta", task.subject_id, task.request_key, task.request_hash, task.suite_hash)
    with pytest.raises(ContractError):
        task.bind(task.tenant_id, task.subject_id, "other", task.request_hash, task.suite_hash)


@pytest.mark.parametrize("change", [
    lambda raw: raw.replace('"worker_seconds":5', '"worker_seconds":1e999'),
    lambda raw: raw.replace('"worker_seconds":5', '"worker_seconds":5,"worker_seconds":6'),
    lambda raw: raw.replace('"schema_version":1', '"schema_version":true'),
    lambda raw: raw.replace('"schema_version":1', '"schema_version":2'),
    lambda raw: raw.replace('"coding.solve.v1"', '"arbitrary.execute.v1"'),
])
def test_json_admission_rejects_ambiguous_numbers_keys_and_versions(change):
    raw = json.dumps(admission().model_dump(), separators=(",", ":"))
    with pytest.raises(ContractError):
        CodingTaskAdmission.from_json(change(raw))


def test_existing_schema_and_idempotent_terminal_retry_are_preserved(tmp_path):
    store = Store(tmp_path / "state.db", secrets.token_bytes(32))
    token = store.provision("alpha", "developer", "owner")
    request = submission()["request"]
    original = store.submit(token, "key", request["goal"], request["cases"])
    assert set(original) == {"id", "tenant", "submitted_by", "state", "version", "request", "request_hash", "usage", "created"}
    store.cancel(token, original["id"])
    with sqlite3.connect(store.path) as db:
        audit_count = db.execute("SELECT count(*) FROM audit").fetchone()[0]
    retry = store.submit(token, "key", request["goal"], request["cases"])
    assert retry["id"] == original["id"] and retry["state"] == "cancelled"
    with pytest.raises(SwarmError):
        store.submit(token, "key", "Changed goal", request["cases"])
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT version FROM metadata").fetchall() == [(2,)]
        assert db.execute("SELECT count(*) FROM runs").fetchone()[0] == 1
        assert db.execute("SELECT count(*) FROM audit").fetchone()[0] == audit_count
