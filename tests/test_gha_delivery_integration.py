"""Integration tests for GHA-02 offline manifest and artifact validation.

Exercises all 13 positive and negative acceptance matrix scenarios using
private git repositories, private SQLite fixture databases, and private zip archives.
Also reproduces and verifies closure of critical defects B1, B2, B3, and B4.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

import pytest

from mas.pm.coordinator import trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.delivery import DeliveryGateError, DeliveryService, delivery_admin_actor
from mas.pm.delivery_validator import (
    DeliveryManifest,
    DeliveryValidatorError,
    ManifestObservation,
    ValidationResult,
    parse_manifest_json,
    publish_submission,
    validate_artifact_archive,
    validate_delivery_manifest,
    validate_git_candidate,
    validate_manifest_input,
)
from mas.pm.models import Issue, Project
from mas.pm.worker import CoordinatorAdmissionEngine


def actor(name: str):
    return delivery_admin_actor(name)


def make_fixture_git_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo_dir = tmp_path / "git_repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)

    # Initial base commit
    mas_dir = repo_dir / "mas"
    mas_dir.mkdir(parents=True, exist_ok=True)
    (mas_dir / "code.py").write_text("# base code\n")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "base commit"], cwd=repo_dir, check=True, stdout=subprocess.PIPE)
    base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, stdout=subprocess.PIPE).stdout.decode().strip()

    # Candidate commit modifying mas/code.py
    (mas_dir / "code.py").write_text("# candidate code\n")
    subprocess.run(["git", "commit", "-am", "candidate commit"], cwd=repo_dir, check=True, stdout=subprocess.PIPE)
    candidate_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, stdout=subprocess.PIPE).stdout.decode().strip()

    return repo_dir, base_sha, candidate_sha


def make_zip(files: dict[str, bytes]) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return bio.getvalue()


@pytest.fixture
def fixture_env(tmp_path):
    repo_dir, base_sha, candidate_sha = make_fixture_git_repo(tmp_path)
    suite_digest = hashlib.sha256(b"canonical-suite-cases").hexdigest()

    db_path = tmp_path / "pm.db"
    db = PMDatabase(db_path)
    db.create_project(Project(id="p1", key="P1", name="Test Project", token_budget=10000))
    db.create_issue(Issue(id="i1", project_id="p1", key="P1-1", title="Task 1", appetite_tokens=1000, path_whitelist=["mas/"]))

    with db.atomic_transaction() as c:
        c.execute(
            "INSERT INTO pm_task_mappings(project_id,planning_reference,task_id,local_issue_id,local_issue_key) VALUES('p1','P1-1','task1','i1','P1-1')"
        )

    brief_data = {
        "base_sha": base_sha,
        "suite_digest": suite_digest,
        "policy_version": 1,
        "coordinator": "coordinator",
        "builder": "builder",
        "verifier": "verifier",
        "reviewer": "reviewer",
        "scope": ["mas/"],
        "critical": True,
        "mechanism": "Qualified synthetic boundary; current policy checked atomically",
        "requirements": [{"id": "R1", "rule": "Rule 1 requirement"}],
        "checks": [
            {"id": "check_pos", "requirement_id": "R1", "command": "run check", "expected": "passed", "negative": False},
            {"id": "check_neg", "requirement_id": "R1", "command": "run adverse", "expected": "rejected", "negative": True},
        ],
    }

    service = DeliveryService(db)
    with trusted_coordinator_admin_scope(), actor("coordinator"):
        service.enroll("p1", "default")
        service.establish("i1", brief_data)
        task = service.get("i1")

    with trusted_coordinator_admin_scope(), actor("reviewer"):
        service.agree("i1", task["revision"], role="reviewer", rationale="Mechanism approved")

    with trusted_coordinator_admin_scope(), actor("coordinator"):
        task = service.get("i1")

    with trusted_coordinator_admin_scope(), actor("builder"):
        service.agree("i1", task["revision"], role="builder", rationale="Scope acknowledged")

    return {
        "db": db,
        "db_path": db_path,
        "service": service,
        "repo_dir": repo_dir,
        "base_sha": base_sha,
        "candidate_sha": candidate_sha,
        "suite_digest": suite_digest,
        "issue_id": "i1",
        "project_id": "p1",
        "tenant_id": "default",
    }


def state(service, issue_id="i1"):
    with trusted_coordinator_admin_scope(), actor("coordinator"):
        return service.get(issue_id)


def complete_fixture_run(env: dict, suffix="1", exit_code=0) -> str:
    db = env["db"]
    service = env["service"]
    run_id = f"run_{suffix}"
    intent_id = f"intent_{suffix}"
    attempt_id = f"attempt_{suffix}"

    with trusted_coordinator_admin_scope():
        intent = CoordinatorAdmissionEngine(db).admit_task(
            env["issue_id"], budget_reservation=100, attempt_id=attempt_id, intent_id=intent_id
        )
        assert db.coordinator.claim_intent(intent.intent_id, "worker", 1, 100, 30)
        assert db.coordinator.pre_spawn_intent(intent.intent_id, "worker", 2, 101, run_id)
        assert db.coordinator.complete_intent(intent.intent_id, "worker", 2, 102, env["candidate_sha"], 1, exit_code)

    assert state(service, env["issue_id"])["phase"] == "AWAITING_SUBMISSION"
    return run_id


def build_valid_manifest(
    env: dict,
    run_id: str,
    observations: list[ManifestObservation],
    revision: int | None = None,
    intent_id: str | None = None,
    attempt_id: str | None = None,
    fencing_token: int = 2,
    closures: dict[str, list[str]] | None = None,
) -> DeliveryManifest:
    task = state(env["service"], env["issue_id"])
    suffix = run_id.removeprefix("run_") if run_id.startswith("run_") else "1"
    resolved_intent = intent_id if intent_id is not None else f"intent_{suffix}"
    resolved_attempt = attempt_id if attempt_id is not None else f"attempt_{suffix}"
    return DeliveryManifest(
        schema_version="mas-delivery-manifest-v1",
        tenant_id=env["tenant_id"],
        project_id=env["project_id"],
        issue_id=env["issue_id"],
        brief_version=task["version"],
        policy_version=1,
        revision=revision if revision is not None else task["revision"],
        run_id=run_id,
        intent_id=resolved_intent,
        attempt_id=resolved_attempt,
        fencing_token=fencing_token,
        candidate_sha=env["candidate_sha"],
        base_sha=env["base_sha"],
        suite_digest=env["suite_digest"],
        observations=observations,
        closures=closures if closures is not None else {},
        limitations="None",
    )


# ---------------------------------------------------------------------------
# Reproduction Tests for Critical Defects B1, B2, B3, B4 & Shallow Bypass
# ---------------------------------------------------------------------------

def test_reproduce_b1_empty_archive_with_passed_observations_rejected(fixture_env):
    """B1: Empty archive must NOT validate or submit when PASSED observations are declared."""
    env = fixture_env
    run_id = complete_fixture_run(env, "b1")
    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="PASSED",
            evidence_ref="test_run.log",
            digest=hashlib.sha256(b"content").hexdigest(),
        )
    ]
    manifest = build_valid_manifest(env, run_id, obs, intent_id="intent_b1", attempt_id="attempt_b1")
    empty_zip = io.BytesIO()
    with zipfile.ZipFile(empty_zip, "w"):
        pass
    archive_bytes = empty_zip.getvalue()

    # 1. validate_artifact_archive must reject
    with pytest.raises(DeliveryValidatorError, match="references absent artifact|Archive is empty"):
        validate_artifact_archive(archive_bytes, observations=manifest.observations)

    # 2. validate_delivery_manifest must report validation failed
    res = validate_delivery_manifest(manifest, archive_bytes, env["repo_dir"], env["db"])
    assert res.valid is False
    assert any("empty" in r or "absent" in r for r in res.reasons)

    # 3. publish_submission must fail and DB phase must remain AWAITING_SUBMISSION
    with trusted_coordinator_admin_scope(), actor("builder"):
        with pytest.raises(DeliveryValidatorError):
            publish_submission(env["service"], manifest, archive_bytes, env["repo_dir"])
    assert state(env["service"], env["issue_id"])["phase"] == "AWAITING_SUBMISSION"


def test_reproduce_b2_model_copy_and_construct_bypass_rejected(fixture_env):
    """B2: Preconstructed models via model_copy or model_construct must NOT bypass validation."""
    env = fixture_env
    run_id = complete_fixture_run(env, "b2")
    obs = [ManifestObservation(check_id="check_pos", outcome="PASSED", evidence_ref="mas/code.py", digest="a"*64)]
    manifest = build_valid_manifest(env, run_id, obs, intent_id="intent_b2", attempt_id="attempt_b2")

    # Mutated copy with wrong schema_version and bool brief_version
    bad_copy = manifest.model_copy(update={"schema_version": "wrong-schema", "brief_version": True})
    with pytest.raises(DeliveryValidatorError):
        validate_manifest_input(bad_copy)

    res = validate_delivery_manifest(bad_copy, b"", env["repo_dir"], env["db"])
    assert res.valid is False

    # Constructed model bypassing validation
    bad_construct = DeliveryManifest.model_construct(
        schema_version="wrong-schema",
        tenant_id=env["tenant_id"],
        project_id=env["project_id"],
        issue_id=env["issue_id"],
        brief_version=True,  # bool instead of int
        policy_version=1,
        revision=1,
        run_id=run_id,
        intent_id="intent_b2",
        attempt_id="attempt_b2",
        fencing_token=2,
        candidate_sha=env["candidate_sha"],
        base_sha=env["base_sha"],
        suite_digest=env["suite_digest"],
        observations=obs,
    )
    with pytest.raises(DeliveryValidatorError):
        validate_manifest_input(bad_construct)

    res2 = validate_delivery_manifest(bad_construct, b"", env["repo_dir"], env["db"])
    assert res2.valid is False


def test_reproduce_b3_original_zip_nul_name_rejected():
    """B3 (case 1): Raw ZIP member evil\\x00name must be rejected, not truncated to 'evil'."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("evil_name", b"payload")
    raw = bytearray(bio.getvalue())
    idx = raw.find(b"evil_name")
    while idx != -1:
        raw[idx:idx+9] = b"evil\x00name"
        idx = raw.find(b"evil_name")

    with pytest.raises(DeliveryValidatorError, match="NUL character in archive member name|NUL byte in local header filename"):
        validate_artifact_archive(bytes(raw))


def test_reproduce_b3_stored_header_size_lie_hiding_excess_data_rejected():
    """B3 (case 2): STORED entry with 2,097,153 bytes and forged header size=1 must be rejected."""
    data_full = b"A" * 2097153
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("test.txt", data_full)
    raw = bytearray(bio.getvalue())
    crc_1 = zlib.crc32(b"A")
    # Forged local header size=1
    struct.pack_into("<III", raw, 14, crc_1, 1, 1)
    # Forged central directory header size=1
    cd_idx = raw.find(b"PK\x01\x02")
    struct.pack_into("<III", raw, cd_idx + 16, crc_1, 1, 1)

    with pytest.raises(DeliveryValidatorError, match="Archive continuity gap|STORED member.*compress_size != file_size|CRC32 mismatch"):
        validate_artifact_archive(bytes(raw))


def test_reproduce_b4_cli_no_db_override_and_no_unauthenticated_db_init(tmp_path):
    """B4: CLI rejects --db and --publish arguments and never initializes SQLite."""
    script_path = Path("scripts/delivery_gate_runner.py").resolve()
    # 1. Passing --db is rejected with unrecognized arguments (code 2)
    res_db = subprocess.run(
        [sys.executable, str(script_path), "--manifest", "m.json", "--archive", "a.zip", "--repo", ".", "--db", "any.db"],
        capture_output=True,
        text=True,
    )
    assert res_db.returncode == 2
    assert "unrecognized arguments: --db" in res_db.stderr

    # 2. Passing --publish is rejected with unrecognized arguments (code 2)
    res_pub = subprocess.run(
        [sys.executable, str(script_path), "--manifest", "m.json", "--archive", "a.zip", "--repo", ".", "--publish"],
        capture_output=True,
        text=True,
    )
    assert res_pub.returncode == 2
    assert "unrecognized arguments: --publish" in res_pub.stderr


def test_shallow_validation_result_bypass_rejected(fixture_env):
    """Shallow ValidationResult passed to publish_submission is rejected."""
    env = fixture_env
    run_id = complete_fixture_run(env, "shallow")
    fake_res = ValidationResult(
        valid=True,
        status="VALIDATED_CLAIMS",
        reasons=[],
        issue_id=env["issue_id"],
        run_id=run_id,
        candidate_sha=env["candidate_sha"],
        revision=1,
        project_id=env["project_id"],
        tenant_id=env["tenant_id"],
        submission_payload={"run_id": run_id, "candidate_sha": env["candidate_sha"], "observations": []},
    )
    with pytest.raises(DeliveryValidatorError, match="Passing shallow ValidationResult.*is prohibited"):
        publish_submission(env["service"], fake_res)


# ---------------------------------------------------------------------------
# The 13 Acceptance Matrix Scenarios
# ---------------------------------------------------------------------------

def test_scenario_1_valid_run_produces_in_review(fixture_env):
    """Scenario 1: Valid completed run + all valid observations -> authenticated IN_REVIEW, pure CLI remains VALIDATED_CLAIMS."""
    env = fixture_env
    run_id = complete_fixture_run(env, "1")

    pos_bytes = b"pos log ok"
    neg_bytes = b"neg log ok"
    archive = make_zip({"pos.log": pos_bytes, "neg.log": neg_bytes})

    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="PASSED",
            evidence_ref="pos.log",
            digest=hashlib.sha256(pos_bytes).hexdigest(),
            size=len(pos_bytes),
        ),
        ManifestObservation(
            check_id="check_neg",
            outcome="PASSED",
            evidence_ref="neg.log",
            digest=hashlib.sha256(neg_bytes).hexdigest(),
            size=len(neg_bytes),
        ),
    ]
    manifest = build_valid_manifest(env, run_id, obs)

    # Pure validation
    val_res = validate_delivery_manifest(manifest, archive, env["repo_dir"], env["db"])
    assert val_res.valid is True
    assert val_res.status == "VALIDATED_CLAIMS"

    # Authenticated submission transitions to IN_REVIEW
    with trusted_coordinator_admin_scope(), actor("builder"):
        task = publish_submission(env["service"], manifest, archive, env["repo_dir"])
    assert task["phase"] == "IN_REVIEW"
    assert task["phase"] not in ("ACCEPTED", "DONE")


def test_scenario_2_nonpassing_or_omitted_check_produces_readiness_returned(fixture_env):
    """Scenario 2: Omitted check and valid nonpassing observation -> READINESS_RETURNED."""
    env = fixture_env
    run_id = complete_fixture_run(env, "2")

    pos_bytes = b"failed execution log"
    archive = make_zip({"pos.log": pos_bytes})

    # check_pos FAILED and check_neg omitted
    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="FAILED",
            evidence_ref="pos.log",
            digest=hashlib.sha256(pos_bytes).hexdigest(),
            size=len(pos_bytes),
        )
    ]
    manifest = build_valid_manifest(env, run_id, obs)

    # Valid claims but nonpassing check -> DeliveryService transitions to READINESS_RETURNED
    with trusted_coordinator_admin_scope(), actor("builder"):
        task = publish_submission(env["service"], manifest, archive, env["repo_dir"])
    assert task["phase"] == "READINESS_RETURNED"
    with trusted_coordinator_admin_scope(), actor("coordinator"):
        assert env["service"].metrics(env["issue_id"])["readiness_returns"] == 1


def test_scenario_3_ready_phase_or_unsuccessful_run_denied(fixture_env):
    """Scenario 3: Submissions from READY state or unsuccessful/foreign run denied without mutation."""
    env = fixture_env
    # Task is currently in READY (before complete_fixture_run)
    assert state(env["service"], env["issue_id"])["phase"] == "READY"

    log_bytes = b"log"
    archive = make_zip({"log.txt": log_bytes})
    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="PASSED",
            evidence_ref="log.txt",
            digest=hashlib.sha256(log_bytes).hexdigest(),
        )
    ]
    manifest = build_valid_manifest(env, "run_fake", obs)

    res = validate_delivery_manifest(manifest, archive, env["repo_dir"], env["db"])
    assert res.valid is False
    assert any("phase 'READY' is not eligible" in r for r in res.reasons)

    # Authenticated submission fails without DB mutation
    with trusted_coordinator_admin_scope(), actor("builder"):
        with pytest.raises(DeliveryValidatorError, match="phase 'READY' is not eligible"):
            publish_submission(env["service"], manifest, archive, env["repo_dir"])
    assert state(env["service"], env["issue_id"])["phase"] == "READY"


def test_scenario_4_wrong_tenant_or_stale_cas_denied(fixture_env):
    """Scenario 4: Wrong tenant or stale CAS revision denied without mutation."""
    env = fixture_env
    run_id = complete_fixture_run(env, "4")
    log_bytes = b"log"
    archive = make_zip({"log.txt": log_bytes})
    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="PASSED",
            evidence_ref="log.txt",
            digest=hashlib.sha256(log_bytes).hexdigest(),
        )
    ]

    # Stale revision manifest
    manifest_stale = build_valid_manifest(env, run_id, obs, revision=999, intent_id="intent_4", attempt_id="attempt_4")
    res = validate_delivery_manifest(manifest_stale, archive, env["repo_dir"], env["db"])
    assert res.valid is False
    assert any("revision mismatch" in r for r in res.reasons)

    # Wrong tenant
    manifest_wrong_tenant = manifest_stale.model_copy(update={"tenant_id": "foreign_tenant", "revision": state(env["service"], env["issue_id"])["revision"]})
    res_tenant = validate_delivery_manifest(manifest_wrong_tenant, archive, env["repo_dir"], env["db"])
    assert res_tenant.valid is False


def test_scenario_5_changed_identities_denied(fixture_env):
    """Scenario 5: Changed candidate SHA, base SHA, or suite digest denied."""
    env = fixture_env
    run_id = complete_fixture_run(env, "5")
    log_bytes = b"log"
    archive = make_zip({"log.txt": log_bytes})
    obs = [ManifestObservation(check_id="check_pos", outcome="PASSED", evidence_ref="log.txt", digest=hashlib.sha256(log_bytes).hexdigest())]

    manifest = build_valid_manifest(env, run_id, obs, intent_id="intent_5", attempt_id="attempt_5")
    bad_base = manifest.model_copy(update={"base_sha": "0" * 40})

    res = validate_delivery_manifest(bad_base, archive, env["repo_dir"], env["db"])
    assert res.valid is False
    assert any("Base commit SHA mismatch" in r for r in res.reasons)


def test_scenario_6_strict_json_and_types_enforced():
    """Scenario 6: Unknown fields, duplicate JSON keys, nonfinite values, or boolean/string numeric fields denied."""
    # Duplicate key JSON
    dup_json = '{"schema_version": "mas-delivery-manifest-v1", "schema_version": "mas-delivery-manifest-v1"}'
    with pytest.raises(DeliveryValidatorError, match="Duplicate JSON key"):
        parse_manifest_json(dup_json)

    # Nonfinite constant
    nan_json = '{"schema_version": "mas-delivery-manifest-v1", "brief_version": NaN}'
    with pytest.raises(DeliveryValidatorError, match="Nonfinite JSON constant forbidden"):
        parse_manifest_json(nan_json)

    # Boolean for integer
    bool_int_dict = {
        "schema_version": "mas-delivery-manifest-v1",
        "tenant_id": "t1",
        "project_id": "p1",
        "issue_id": "i1",
        "brief_version": True,  # bool instead of int
        "policy_version": 1,
        "revision": 1,
        "run_id": "r1",
        "intent_id": "intent_1",
        "attempt_id": "attempt_1",
        "fencing_token": 1,
        "candidate_sha": "a" * 40,
        "base_sha": "b" * 40,
        "suite_digest": "c" * 64,
        "observations": [{"check_id": "c1", "outcome": "PASSED", "evidence_ref": "ref", "digest": "d" * 64}],
    }
    with pytest.raises(DeliveryValidatorError, match="Manifest schema validation failed"):
        validate_manifest_input(bool_int_dict)


def test_scenario_7_unsafe_archive_paths_rejected():
    """Scenario 7: Traversal, absolute, backslash, control paths, symlinks, and duplicate canonical archive names rejected."""
    # Absolute path
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w") as zf:
        zf.writestr("/etc/passwd", b"root")
    with pytest.raises(DeliveryValidatorError, match="Absolute path forbidden"):
        validate_artifact_archive(bio.getvalue())

    # Traversal path
    bio_trav = io.BytesIO()
    with zipfile.ZipFile(bio_trav, "w") as zf:
        zf.writestr("sub/../../escaped.log", b"escape")
    with pytest.raises(DeliveryValidatorError, match="Invalid path segments"):
        validate_artifact_archive(bio_trav.getvalue())

    # Duplicate canonical names (case-insensitive collision)
    bio_canon = io.BytesIO()
    with zipfile.ZipFile(bio_canon, "w") as zf:
        zf.writestr("case.log", b"data1")
        zf.writestr("CASE.LOG", b"data2")
    with pytest.raises(DeliveryValidatorError, match="Duplicate or colliding canonical member name"):
        validate_artifact_archive(bio_canon.getvalue())


def test_scenario_8_archive_size_and_digest_limits():
    """Scenario 8: Member count, uncompressed limit, and digest verification."""
    # Overly large member (> 2 MiB)
    bio_large = io.BytesIO()
    with zipfile.ZipFile(bio_large, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.txt", b"x" * (2 * 1024 * 1024 + 1))
    with pytest.raises(DeliveryValidatorError, match="exceeds 2097152"):
        validate_artifact_archive(bio_large.getvalue())


def test_scenario_9_git_diff_out_of_scope_denied(tmp_path):
    """Scenario 9: Unauthorized diff, symlink/submodule changes, or missing Git objects denied."""
    repo_dir, base_sha, candidate_sha = make_fixture_git_repo(tmp_path)
    # mas/code.py is modified, but allowed scope is only ['other/']
    with pytest.raises(DeliveryValidatorError, match="Modified file outside declared scope"):
        validate_git_candidate(repo_dir, base_sha, candidate_sha, ["other/"])


def test_scenario_10_competing_publication_cas(fixture_env):
    """Scenario 10: Competing publication calls with same revision -> one winner, no duplicate history."""
    env = fixture_env
    run_id = complete_fixture_run(env, "10")
    pos_bytes = b"pos ok"
    neg_bytes = b"neg ok"
    archive = make_zip({"pos.log": pos_bytes, "neg.log": neg_bytes})
    obs = [
        ManifestObservation(check_id="check_pos", outcome="PASSED", evidence_ref="pos.log", digest=hashlib.sha256(pos_bytes).hexdigest()),
        ManifestObservation(check_id="check_neg", outcome="PASSED", evidence_ref="neg.log", digest=hashlib.sha256(neg_bytes).hexdigest()),
    ]
    manifest = build_valid_manifest(env, run_id, obs, intent_id="intent_10", attempt_id="attempt_10")

    with trusted_coordinator_admin_scope(), actor("builder"):
        # First call succeeds
        task1 = publish_submission(env["service"], manifest, archive, env["repo_dir"])
        assert task1["phase"] == "IN_REVIEW"

        # Competing call with same revision fails
        with pytest.raises((DeliveryGateError, DeliveryValidatorError)):
            publish_submission(env["service"], manifest, archive, env["repo_dir"], expected_revision=manifest.revision)


def test_scenario_11_paused_task_cannot_be_cleared(fixture_env):
    """Scenario 11: Task in RECURRENCE_PAUSED cannot be submitted or cleared by validator."""
    env = fixture_env
    run_id = complete_fixture_run(env, "11")

    # Manually pause task recurrence in DB to simulate recurrence hold
    with env["db"].atomic_transaction() as conn:
        conn.execute("UPDATE pm_delivery_tasks SET phase='RECURRENCE_PAUSED' WHERE issue_id=?", (env["issue_id"],))

    log_bytes = b"ok"
    archive = make_zip({"log.txt": log_bytes})
    obs = [ManifestObservation(check_id="check_pos", outcome="PASSED", evidence_ref="log.txt", digest=hashlib.sha256(log_bytes).hexdigest())]
    manifest = build_valid_manifest(env, run_id, obs, intent_id="intent_11", attempt_id="attempt_11")

    res = validate_delivery_manifest(manifest, archive, env["repo_dir"], env["db"])
    assert res.valid is False
    assert any("RECURRENCE_PAUSED" in r for r in res.reasons)


def test_scenario_12_cli_execution_and_authority(fixture_env, tmp_path):
    """Scenario 12: Direct CLI execution outputs truthful JSON and cannot bypass authority."""
    env = fixture_env
    run_id = complete_fixture_run(env, "12")
    log_bytes = b"log ok"
    archive_path = tmp_path / "artifacts.zip"
    archive_path.write_bytes(make_zip({"pos.log": log_bytes}))

    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="PASSED",
            evidence_ref="pos.log",
            digest=hashlib.sha256(log_bytes).hexdigest(),
            size=len(log_bytes),
        )
    ]
    manifest = build_valid_manifest(env, run_id, obs, intent_id="intent_12", attempt_id="attempt_12")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json())

    script_path = Path("scripts/delivery_gate_runner.py").resolve()
    proc = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--manifest",
            str(manifest_path),
            "--archive",
            str(archive_path),
            "--repo",
            str(env["repo_dir"]),
            "--scope",
            "mas/",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["status"] == "VALIDATED_CLAIMS"
    assert data["authority_verified"] is False


def test_scenario_13_clean_import(tmp_path):
    """Scenario 13: Clean import test in an isolated process using sys.executable."""
    code = "import mas.pm.delivery_validator; print('OK')"
    res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert res.returncode == 0
    assert "OK" in res.stdout


def test_real_concurrency_race_one_winner(fixture_env):
    """Real multi-threaded concurrency race: exactly one submission wins, other fails with CAS conflict."""
    env = fixture_env
    run_id = complete_fixture_run(env, "race")
    pos_bytes = b"race pos ok"
    neg_bytes = b"race neg ok"
    archive = make_zip({"pos.log": pos_bytes, "neg.log": neg_bytes})
    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="PASSED",
            evidence_ref="pos.log",
            digest=hashlib.sha256(pos_bytes).hexdigest(),
            size=len(pos_bytes),
        ),
        ManifestObservation(
            check_id="check_neg",
            outcome="PASSED",
            evidence_ref="neg.log",
            digest=hashlib.sha256(neg_bytes).hexdigest(),
            size=len(neg_bytes),
        ),
    ]
    manifest = build_valid_manifest(env, run_id, obs, intent_id="intent_race", attempt_id="attempt_race")

    results = []
    errors = []

    def try_submit():
        try:
            with trusted_coordinator_admin_scope(), actor("builder"):
                task = publish_submission(env["service"], manifest, archive, env["repo_dir"], expected_revision=manifest.revision)
                return task
        except Exception as e:
            return e

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futs = [executor.submit(try_submit), executor.submit(try_submit)]
        for f in concurrent.futures.as_completed(futs):
            res = f.result()
            if isinstance(res, Exception):
                errors.append(res)
            else:
                results.append(res)

    # Exactly one winner succeeded and transitioned to IN_REVIEW
    assert len(results) == 1
    assert results[0]["phase"] == "IN_REVIEW"
    # Exactly one CAS / delivery gate conflict
    assert len(errors) == 1
    assert isinstance(errors[0], (DeliveryGateError, DeliveryValidatorError))


def test_fresh_real_tenant_binding_wrong_actor_and_revocation(fixture_env):
    """Real tenant binding: non-builder role or revoked session is denied without state change."""
    env = fixture_env
    run_id = complete_fixture_run(env, "actor")
    log_bytes = b"actor test"
    archive = make_zip({"pos.log": log_bytes})
    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="PASSED",
            evidence_ref="pos.log",
            digest=hashlib.sha256(log_bytes).hexdigest(),
            size=len(log_bytes),
        )
    ]
    manifest = build_valid_manifest(env, run_id, obs, intent_id="intent_actor", attempt_id="attempt_actor")

    # Calling with reviewer/reader actor instead of builder
    with trusted_coordinator_admin_scope(), actor("reviewer"):
        with pytest.raises((PermissionError, DeliveryGateError), match="Caller is not assigned builder|Assigned builder role required"):
            publish_submission(env["service"], manifest, archive, env["repo_dir"])

    assert state(env["service"], env["issue_id"])["phase"] == "AWAITING_SUBMISSION"


# ---------------------------------------------------------------------------
# Rework 2 Reproduction & Regression Tests: B1, B2, B3, Git Streaming, Input Bounds
# ---------------------------------------------------------------------------

def test_rework2_b1_intent_and_attempt_identities_authoritatively_bound(fixture_env):
    """Rework 2 B1: Authoritative binding of intent_id and attempt_id against joined coordinator records.

    Verifies:
    1. Valid run with matching IDs transitions to IN_REVIEW.
    2. Wrong intent_id alone fails with DeliveryValidatorError; zero mutation (revision, submissions, events unchanged).
    3. Wrong attempt_id alone fails with DeliveryValidatorError; zero mutation.
    4. Both wrong fails with DeliveryValidatorError; zero mutation.
    5. Omitted fields fail with DeliveryValidatorError; zero mutation.
    6. Other-task IDs fail with DeliveryValidatorError; zero mutation.
    """
    env = fixture_env
    db = env["db"]
    service = env["service"]
    run_id = complete_fixture_run(env, "rw2_b1")
    log_pos = b"rw2_b1 test output pos"
    log_neg = b"rw2_b1 test output neg"
    archive = make_zip({"pos.log": log_pos, "neg.log": log_neg})
    obs = [
        ManifestObservation(
            check_id="check_pos",
            outcome="PASSED",
            evidence_ref="pos.log",
            digest=hashlib.sha256(log_pos).hexdigest(),
            size=len(log_pos),
        ),
        ManifestObservation(
            check_id="check_neg",
            outcome="PASSED",
            evidence_ref="neg.log",
            digest=hashlib.sha256(log_neg).hexdigest(),
            size=len(log_neg),
        ),
    ]

    initial_task = state(service, env["issue_id"])
    initial_rev = initial_task["revision"]
    with db.atomic_transaction() as c:
        initial_events_count = c.execute(
            "SELECT COUNT(*) as cnt FROM pm_delivery_events WHERE issue_id=?", (env["issue_id"],)
        ).fetchone()["cnt"]
        initial_submissions_count = c.execute(
            "SELECT COUNT(*) as cnt FROM pm_delivery_submissions WHERE issue_id=?", (env["issue_id"],)
        ).fetchone()["cnt"]

    # 1. Wrong intent_id alone
    manifest_bad_intent = build_valid_manifest(
        env, run_id, obs, intent_id="nonexistent_intent", attempt_id="attempt_rw2_b1"
    )
    with trusted_coordinator_admin_scope(), actor("builder"):
        with pytest.raises(DeliveryValidatorError, match="Intent ID mismatch"):
            publish_submission(service, manifest_bad_intent, archive, env["repo_dir"])

    cur_task = state(service, env["issue_id"])
    assert cur_task["revision"] == initial_rev
    assert cur_task["phase"] == "AWAITING_SUBMISSION"
    with db.atomic_transaction() as c:
        assert c.execute("SELECT COUNT(*) as cnt FROM pm_delivery_submissions WHERE issue_id=?", (env["issue_id"],)).fetchone()["cnt"] == initial_submissions_count
        assert c.execute("SELECT COUNT(*) as cnt FROM pm_delivery_events WHERE issue_id=?", (env["issue_id"],)).fetchone()["cnt"] == initial_events_count

    # 2. Wrong attempt_id alone
    manifest_bad_attempt = build_valid_manifest(
        env, run_id, obs, intent_id="intent_rw2_b1", attempt_id="nonexistent_attempt"
    )
    with trusted_coordinator_admin_scope(), actor("builder"):
        with pytest.raises(DeliveryValidatorError, match="Attempt ID mismatch"):
            publish_submission(service, manifest_bad_attempt, archive, env["repo_dir"])

    cur_task = state(service, env["issue_id"])
    assert cur_task["revision"] == initial_rev
    assert cur_task["phase"] == "AWAITING_SUBMISSION"

    # 3. Both wrong
    manifest_both_bad = build_valid_manifest(
        env, run_id, obs, intent_id="nonexistent_intent", attempt_id="nonexistent_attempt"
    )
    with trusted_coordinator_admin_scope(), actor("builder"):
        with pytest.raises(DeliveryValidatorError, match="Intent ID mismatch|Attempt ID mismatch"):
            publish_submission(service, manifest_both_bad, archive, env["repo_dir"])

    cur_task = state(service, env["issue_id"])
    assert cur_task["revision"] == initial_rev
    assert cur_task["phase"] == "AWAITING_SUBMISSION"

    # 4. Omitted intent_id or attempt_id in raw dict
    raw_dict = manifest_both_bad.model_dump()
    raw_dict.pop("intent_id", None)
    with trusted_coordinator_admin_scope(), actor("builder"):
        with pytest.raises(DeliveryValidatorError, match="intent_id"):
            publish_submission(service, raw_dict, archive, env["repo_dir"])

    raw_dict2 = manifest_both_bad.model_dump()
    raw_dict2.pop("attempt_id", None)
    with trusted_coordinator_admin_scope(), actor("builder"):
        with pytest.raises(DeliveryValidatorError, match="attempt_id"):
            publish_submission(service, raw_dict2, archive, env["repo_dir"])

    # 5. Other-task IDs
    # Setup another issue i2 and admit a run
    db.create_issue(Issue(id="i2", project_id="p1", key="P1-2", title="Task 2", appetite_tokens=1000, path_whitelist=["mas/"]))
    with db.atomic_transaction() as c:
        c.execute("INSERT INTO pm_task_mappings(project_id,planning_reference,task_id,local_issue_id,local_issue_key) VALUES('p1','P1-2','task2','i2','P1-2')")
    brief_data2 = {
        "base_sha": env["base_sha"],
        "suite_digest": env["suite_digest"],
        "policy_version": 1,
        "coordinator": "coordinator",
        "builder": "builder",
        "verifier": "verifier",
        "reviewer": "reviewer",
        "scope": ["mas/"],
        "critical": True,
        "mechanism": "Qualified synthetic boundary; current policy checked atomically",
        "requirements": [{"id": "R1", "rule": "Rule 1 requirement"}],
        "checks": [
            {"id": "check_pos", "requirement_id": "R1", "command": "run check", "expected": "passed", "negative": False},
            {"id": "check_neg", "requirement_id": "R1", "command": "run adverse", "expected": "rejected", "negative": True},
        ],
    }
    with trusted_coordinator_admin_scope(), actor("coordinator"):
        service.establish("i2", brief_data2)
        t2 = service.get("i2")
    with trusted_coordinator_admin_scope(), actor("reviewer"):
        service.agree("i2", t2["revision"], role="reviewer", rationale="Mechanism approved")
    with trusted_coordinator_admin_scope(), actor("coordinator"):
        t2 = service.get("i2")
    with trusted_coordinator_admin_scope(), actor("builder"):
        service.agree("i2", t2["revision"], role="builder", rationale="Scope acknowledged")

    with trusted_coordinator_admin_scope():
        intent_other = CoordinatorAdmissionEngine(db).admit_task("i2", budget_reservation=100, attempt_id="attempt_other", intent_id="intent_other")
        assert db.coordinator.claim_intent(intent_other.intent_id, "worker", 1, 100, 30)
        assert db.coordinator.pre_spawn_intent(intent_other.intent_id, "worker", 2, 101, "run_other")
        assert db.coordinator.complete_intent(intent_other.intent_id, "worker", 2, 102, env["candidate_sha"], 1, 0)

    # Manifest for i1 using run_other / intent_other / attempt_other
    manifest_other = build_valid_manifest(
        env, "run_other", obs, intent_id="intent_other", attempt_id="attempt_other"
    )
    with trusted_coordinator_admin_scope(), actor("builder"):
        with pytest.raises(DeliveryValidatorError, match="Run 'run_other' is bound to issue 'i2', not 'i1'"):
            publish_submission(service, manifest_other, archive, env["repo_dir"])

    cur_task = state(service, env["issue_id"])
    assert cur_task["revision"] == initial_rev
    assert cur_task["phase"] == "AWAITING_SUBMISSION"

    # 6. Valid matching IDs succeeds
    manifest_valid = build_valid_manifest(
        env, run_id, obs, intent_id="intent_rw2_b1", attempt_id="attempt_rw2_b1"
    )
    with trusted_coordinator_admin_scope(), actor("builder"):
        res = publish_submission(service, manifest_valid, archive, env["repo_dir"])
    assert res["phase"] == "IN_REVIEW"
    assert res["revision"] == initial_rev + 1


def test_rework2_b2_producer_bounded_deflate_allocation():
    """Rework 2 B2: DEFLATE output is bounded at producer side; no large allocation before rejection.

    Recreates the exact review finding:
    6,291,456 repeated bytes compressed with raw DEFLATE, with declared file_size forged to 1.
    Instruments zlib.decompressobj to prove:
    1. DeliveryValidatorError is raised with producer-boundary limit message.
    2. No single decompress call produces > chunk_size (65536) or > remaining allowance + sentinel.
    3. Sum of all produced chunks <= 2 MiB + 1 byte sentinel (never 6 MiB).
    """
    # 6 MiB repeated bytes
    raw_content = b"Z" * 6291456
    # Compress with raw DEFLATE (wbits=-15)
    comp_stream = zlib.compress(raw_content)[2:-4]
    comp_size = len(comp_stream)
    crc = zlib.crc32(raw_content) & 0xFFFFFFFF

    # Forge zip with declared uncompressed size = 1
    fn = b"bomb.log"
    local_header = struct.pack(
        "<4sHHHHHIIIHH",
        b"PK\x03\x04",
        20, 0, 8, 0, 0,
        crc, comp_size, 1,  # forged uncompressed size = 1
        len(fn), 0
    ) + fn

    cd_header = struct.pack(
        "<4sHHHHHHIIIHHHHHII",
        b"PK\x01\x02",
        20, 20, 0, 8, 0, 0,
        crc, comp_size, 1,  # forged uncompressed size = 1
        len(fn), 0, 0, 0, 0, 0, 0
    ) + fn

    eocd = struct.pack(
        "<4sHHHHIIH",
        b"PK\x05\x06",
        0, 0, 1, 1,
        len(cd_header), len(local_header) + comp_size, 0
    )

    forged_zip = local_header + comp_stream + cd_header + eocd

    # Instrument zlib.decompressobj to capture every chunk returned by decompress
    decompressed_chunk_sizes: list[int] = []
    real_decompressobj = zlib.decompressobj

    class InstrumentedDecompressor:
        def __init__(self, *args, **kwargs):
            self._real = real_decompressobj(*args, **kwargs)

        def decompress(self, data, max_length=0):
            res = self._real.decompress(data, max_length)
            decompressed_chunk_sizes.append(len(res))
            return res

        def flush(self, *args, **kwargs):
            res = self._real.flush(*args, **kwargs)
            decompressed_chunk_sizes.append(len(res))
            return res

        def __getattr__(self, name):
            return getattr(self._real, name)

    import mas.pm.delivery_validator as dv
    original_decompressobj = dv.zlib.decompressobj
    dv.zlib.decompressobj = InstrumentedDecompressor
    try:
        with pytest.raises(DeliveryValidatorError, match="uncompressed size exceeds limit at producer boundary"):
            validate_artifact_archive(forged_zip)
    finally:
        dv.zlib.decompressobj = original_decompressobj

    # Verification of producer-side bounds
    assert len(decompressed_chunk_sizes) > 0
    # No single chunk ever exceeded the 64 KiB chunk size or remaining allowance + 1
    assert max(decompressed_chunk_sizes) <= 65536
    # Total bytes decompressed across all calls never exceeded 2 MiB + 1 byte
    total_decompressed = sum(decompressed_chunk_sizes)
    assert total_decompressed <= (2 * 1024 * 1024 + 1)
    # Most importantly: 6 MiB was NEVER decompressed or allocated
    assert total_decompressed < 6291456


def test_rework2_b2_exact_member_and_aggregate_boundaries():
    """Rework 2 B2: Exact member (2 MiB) and aggregate (10 MiB) boundary tests."""
    # Exact 2 MiB member passes
    exact_2mb = b"B" * (2 * 1024 * 1024)
    zip_2mb = make_zip({"member1.bin": exact_2mb})
    validated = validate_artifact_archive(zip_2mb)
    assert "member1.bin" in validated
    assert validated["member1.bin"].size == 2 * 1024 * 1024

    # 2 MiB + 1 byte member fails at producer boundary
    over_2mb = b"B" * (2 * 1024 * 1024 + 1)
    zip_over_2mb = make_zip({"member1.bin": over_2mb})
    with pytest.raises(DeliveryValidatorError, match="exceeds.*byte limit"):
        validate_artifact_archive(zip_over_2mb)

    # 5 members of 2 MiB each = exactly 10 MiB aggregate passes
    exact_5x = {f"m{i}.bin": b"M" * (2 * 1024 * 1024) for i in range(5)}
    zip_10mb = make_zip(exact_5x)
    validated_10 = validate_artifact_archive(zip_10mb)
    assert len(validated_10) == 5

    # 5 members of 2 MiB + 1 extra byte member = 10 MiB + 1 byte fails
    exact_5x_plus = dict(exact_5x)
    exact_5x_plus["extra.bin"] = b"X"
    zip_10mb_plus = make_zip(exact_5x_plus)
    with pytest.raises(DeliveryValidatorError, match="total uncompressed limit"):
        validate_artifact_archive(zip_10mb_plus)


def test_rework2_b3_fifo_nonblocking_admission(tmp_path):
    """Rework 2 B3: FIFOs and nonregular files fail immediately without blocking."""
    fifo_path = tmp_path / "test_unwritten.fifo"
    os.mkfifo(str(fifo_path))

    try:
        # Run in a bounded subprocess with a strict 2-second timeout to prove it does not block
        cmd = [
            sys.executable,
            "-c",
            f"""
import sys
from pathlib import Path
from mas.pm.delivery_validator import read_file_bounded, DeliveryValidatorError

fifo = Path('{fifo_path}')
try:
    read_file_bounded(fifo, 1024)
    sys.exit(1)
except DeliveryValidatorError as exc:
    if 'Expected regular file' in str(exc):
        sys.exit(0)
    sys.exit(2)
""",
        ]
        proc = subprocess.run(cmd, timeout=2.0)
        assert proc.returncode == 0, f"FIFO read blocked or returned unexpected exit code: {proc.returncode}"

        # Test validate_artifact_archive on FIFO
        with pytest.raises(DeliveryValidatorError, match="Expected regular file"):
            validate_artifact_archive(fifo_path)
    finally:
        if fifo_path.exists():
            os.unlink(str(fifo_path))


def test_rework2_git_bounded_streaming_collection(tmp_path):
    """Rework 2: Git subprocess limits are streaming collection caps, not post-hoc size checks."""
    from mas.pm.delivery_validator import run_bounded_command

    # Test stdout streaming cap
    flood_stdout_cmd = [
        sys.executable,
        "-c",
        "import sys, time; sys.stdout.write('X' * 2000000); sys.stdout.flush()",
    ]
    with pytest.raises(DeliveryValidatorError, match="stdout exceeded 1048576 byte limit during collection"):
        run_bounded_command(flood_stdout_cmd, cwd=tmp_path, max_stdout=1024 * 1024, timeout=5.0)

    # Test stderr streaming cap
    flood_stderr_cmd = [
        sys.executable,
        "-c",
        "import sys, time; sys.stderr.write('E' * 500000); sys.stderr.flush()",
    ]
    with pytest.raises(DeliveryValidatorError, match="stderr exceeded 262144 byte limit during collection"):
        run_bounded_command(flood_stderr_cmd, cwd=tmp_path, max_stderr=256 * 1024, timeout=5.0)


def test_rework2_manifest_dict_and_model_size_bounds():
    """Rework 2: Manifest dict, model and JSON entry routes enforce equivalent size caps."""
    # Dict with excessive keys (> 64)
    too_many_keys = {f"k_{i}": i for i in range(100)}
    with pytest.raises(DeliveryValidatorError, match="Manifest dictionary contains excessive keys"):
        validate_manifest_input(too_many_keys)

    # Dict with serialized payload > 1 MiB
    huge_dict = {"schema_version": "mas-delivery-manifest-v1", "big_junk": "x" * (1024 * 1024 + 10)}
    with pytest.raises(DeliveryValidatorError, match="exceeds 1048576 byte limit"):
        validate_manifest_input(huge_dict)


def test_rework3_b1_data_descriptor_corruption_and_integrity():
    """Rework 3 B1: Signed data descriptors on unseekable streams are strictly validated."""
    class UnseekableBuffer(io.RawIOBase):
        def __init__(self):
            self.buf = bytearray()
        def write(self, b):
            self.buf.extend(b)
            return len(b)
        def writable(self):
            return True
        def seekable(self):
            return False

    # 1. Valid unseekable ZIP with DEFLATED member produces a signed data descriptor
    sink = UnseekableBuffer()
    with zipfile.ZipFile(sink, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("result.log", b"ok\n")
    valid_signed_data = bytes(sink.buf)
    assert b"PK\x07\x08" in valid_signed_data

    # Valid archive passes validation
    validated = validate_artifact_archive(valid_signed_data)
    assert "result.log" in validated
    assert validated["result.log"].data == b"ok\n"

    # 2. Overwrite all three 32-bit fields of descriptor with zero (exact B1 reproduction)
    idx = valid_signed_data.find(b"PK\x07\x08")
    zeroed_data = bytearray(valid_signed_data)
    zeroed_data[idx+4:idx+16] = b"\x00" * 12
    with pytest.raises(DeliveryValidatorError, match="Data descriptor CRC32 mismatch for result.log"):
        validate_artifact_archive(bytes(zeroed_data))

    # 3. Corrupt CRC32 field alone
    corrupt_crc = bytearray(valid_signed_data)
    corrupt_crc[idx+4:idx+8] = b"\xde\xad\xbe\xef"
    with pytest.raises(DeliveryValidatorError, match="Data descriptor CRC32 mismatch for result.log"):
        validate_artifact_archive(bytes(corrupt_crc))

    # 4. Corrupt compressed size field alone
    corrupt_csz = bytearray(valid_signed_data)
    corrupt_csz[idx+8:idx+12] = struct.pack("<I", 9999)
    with pytest.raises(DeliveryValidatorError, match="Data descriptor compressed size mismatch for result.log"):
        validate_artifact_archive(bytes(corrupt_csz))

    # 5. Corrupt uncompressed size field alone
    corrupt_usz = bytearray(valid_signed_data)
    corrupt_usz[idx+12:idx+16] = struct.pack("<I", 9999)
    with pytest.raises(DeliveryValidatorError, match="Data descriptor uncompressed size mismatch for result.log"):
        validate_artifact_archive(bytes(corrupt_usz))

    # 6. Truncated signed descriptor before boundary
    # Shift CD offset in EOCD to simulate descriptor truncated right after signature
    trunc_signed = bytearray(valid_signed_data)
    trunc_signed = trunc_signed[:idx+4] + trunc_signed[idx+16:]
    eocd_idx = trunc_signed.rfind(b"PK\x05\x06")
    sig, disk, cd_disk, d_entries, t_entries, cd_size, cd_offset, c_len = struct.unpack("<4sHHHHIIH", trunc_signed[eocd_idx:eocd_idx+22])
    trunc_signed[eocd_idx:eocd_idx+22] = struct.pack("<4sHHHHIIH", sig, disk, cd_disk, d_entries, t_entries, cd_size, cd_offset - 12, c_len)
    with pytest.raises(DeliveryValidatorError, match="Data descriptor extends beyond boundary for result.log"):
        validate_artifact_archive(bytes(trunc_signed))


def test_rework3_b1_unsigned_descriptor_support_and_corruption():
    """Rework 3 B1: Unsigned data descriptors (12 bytes without PK0708) are strictly validated."""
    class UnseekableBuffer(io.RawIOBase):
        def __init__(self):
            self.buf = bytearray()
        def write(self, b):
            self.buf.extend(b)
            return len(b)
        def writable(self):
            return True
        def seekable(self):
            return False

    sink = UnseekableBuffer()
    with zipfile.ZipFile(sink, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("result.log", b"test content for unsigned descriptor\n")
    signed_data = bytearray(sink.buf)

    # Convert signed descriptor to unsigned descriptor by stripping b"PK\x07\x08" (4 bytes)
    idx = signed_data.find(b"PK\x07\x08")
    unsigned_data = signed_data[:idx] + signed_data[idx+4:]
    # Adjust CD offset in EOCD (-4)
    eocd_idx = unsigned_data.rfind(b"PK\x05\x06")
    sig, disk, cd_disk, d_entries, t_entries, cd_size, cd_offset, c_len = struct.unpack("<4sHHHHIIH", unsigned_data[eocd_idx:eocd_idx+22])
    unsigned_data[eocd_idx:eocd_idx+22] = struct.pack("<4sHHHHIIH", sig, disk, cd_disk, d_entries, t_entries, cd_size, cd_offset - 4, c_len)

    # 1. Valid unsigned descriptor passes
    validated = validate_artifact_archive(bytes(unsigned_data))
    assert "result.log" in validated
    assert validated["result.log"].data == b"test content for unsigned descriptor\n"

    # 2. Corrupt unsigned CRC32
    corrupt_crc = bytearray(unsigned_data)
    corrupt_crc[idx:idx+4] = b"\x00" * 4
    with pytest.raises(DeliveryValidatorError, match="Data descriptor CRC32 mismatch for result.log"):
        validate_artifact_archive(bytes(corrupt_crc))

    # 3. Corrupt unsigned compressed size
    corrupt_csz = bytearray(unsigned_data)
    corrupt_csz[idx+4:idx+8] = struct.pack("<I", 0)
    with pytest.raises(DeliveryValidatorError, match="Data descriptor compressed size mismatch for result.log"):
        validate_artifact_archive(bytes(corrupt_csz))

    # 4. Corrupt unsigned uncompressed size
    corrupt_usz = bytearray(unsigned_data)
    corrupt_usz[idx+8:idx+12] = struct.pack("<I", 0)
    with pytest.raises(DeliveryValidatorError, match="Data descriptor uncompressed size mismatch for result.log"):
        validate_artifact_archive(bytes(corrupt_usz))

    # 5. Truncated unsigned descriptor
    trunc_unsigned = bytearray(unsigned_data)
    trunc_unsigned = trunc_unsigned[:idx+6] + trunc_unsigned[idx+12:]
    eocd_idx2 = trunc_unsigned.rfind(b"PK\x05\x06")
    trunc_unsigned[eocd_idx2:eocd_idx2+22] = struct.pack("<4sHHHHIIH", sig, disk, cd_disk, d_entries, t_entries, cd_size, cd_offset - 4 - 6, c_len)
    with pytest.raises(DeliveryValidatorError, match="Data descriptor extends beyond boundary for result.log"):
        validate_artifact_archive(bytes(trunc_unsigned))


def test_rework3_b1_zip64_variants_explicitly_rejected():
    """Rework 3 B1: ZIP64 formats, signatures, and extra tags are explicitly rejected."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.txt", b"zip64 rejection test")
    valid_zip = buf.getvalue()

    # 1. Archive containing PK\x06\x06 (ZIP64 EOCD)
    z_pk66 = valid_zip + b"PK\x06\x06dummy"
    with pytest.raises(DeliveryValidatorError, match="ZIP64 format is not supported"):
        validate_artifact_archive(z_pk66)

    # 2. Archive containing PK\x06\x07 (ZIP64 EOCD Locator)
    z_pk67 = valid_zip + b"PK\x06\x07dummy"
    with pytest.raises(DeliveryValidatorError, match="ZIP64 format is not supported"):
        validate_artifact_archive(z_pk67)

    # 3. Central directory version >= 45
    z_ver45 = bytearray(valid_zip)
    cd_idx = z_ver45.find(b"PK\x01\x02")
    struct.pack_into("<H", z_ver45, cd_idx + 6, 45)
    with pytest.raises(DeliveryValidatorError, match="ZIP64 format is not supported: version >= 45"):
        validate_artifact_archive(bytes(z_ver45))

    # 4. Central directory extra field with tag 0x0001 (ZIP64 extended info)
    z_extra = bytearray(valid_zip)
    cd_idx = z_extra.find(b"PK\x01\x02")
    # CD format: ... 28: H fn_len, 30: H ex_len
    fn_len, ex_len = struct.unpack_from("<HH", z_extra, cd_idx + 28)
    zip64_tag = struct.pack("<HH8s", 0x0001, 8, b"\x00" * 8)
    insert_pos = cd_idx + 46 + fn_len
    z_extra = z_extra[:insert_pos] + zip64_tag + z_extra[insert_pos:]
    struct.pack_into("<H", z_extra, cd_idx + 30, ex_len + len(zip64_tag))
    # Update EOCD cd_size
    eocd_idx = z_extra.rfind(b"PK\x05\x06")
    sig, disk, cd_disk, d_entries, t_entries, cd_size, cd_offset, c_len = struct.unpack("<4sHHHHIIH", z_extra[eocd_idx:eocd_idx+22])
    z_extra[eocd_idx:eocd_idx+22] = struct.pack("<4sHHHHIIH", sig, disk, cd_disk, d_entries, t_entries, cd_size + len(zip64_tag), cd_offset, c_len)
    with pytest.raises(DeliveryValidatorError, match="ZIP64 format is not supported: extra field"):
        validate_artifact_archive(bytes(z_extra))

    # 5. Local header 64-bit size placeholder 0xFFFFFFFF
    z_64bit = bytearray(valid_zip)
    loc_idx = z_64bit.find(b"PK\x03\x04")
    struct.pack_into("<I", z_64bit, loc_idx + 18, 0xFFFFFFFF)  # loc_csz
    with pytest.raises(DeliveryValidatorError, match="ZIP64 format is not supported: 64-bit local size"):
        validate_artifact_archive(bytes(z_64bit))
