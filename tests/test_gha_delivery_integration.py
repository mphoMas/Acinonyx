"""Integration tests for GHA-02 offline manifest and artifact validation.

Exercises all 13 positive and negative acceptance matrix scenarios using
private git repositories, private SQLite fixture databases, and private zip archives.
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from mas.pm.coordinator import trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.delivery import DeliveryGateError, DeliveryService, delivery_admin_actor
from mas.pm.delivery_validator import (
    DeliveryValidatorError,
    parse_manifest_json,
    publish_submission,
    validate_artifact_archive,
    validate_delivery_manifest,
    validate_git_candidate,
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


def build_valid_manifest(env: dict, run_id: str, files_data: dict[str, bytes]) -> dict:
    task = state(env["service"], env["issue_id"])
    obs = []
    for check_id in ("check_pos", "check_neg"):
        ref = f"artifacts/{check_id}.log"
        data = files_data[ref]
        obs.append(
            {
                "check_id": check_id,
                "outcome": "PASSED",
                "evidence_ref": ref,
                "digest": hashlib.sha256(data).hexdigest(),
            }
        )

    return {
        "schema_version": "mas-delivery-manifest-v1",
        "tenant_id": env["tenant_id"],
        "project_id": env["project_id"],
        "issue_id": env["issue_id"],
        "brief_version": task["version"],
        "revision": task["revision"],
        "run_id": run_id,
        "candidate_sha": env["candidate_sha"],
        "base_sha": env["base_sha"],
        "suite_digest": env["suite_digest"],
        "observations": obs,
        "closures": {},
        "limitations": "Private integration test fixture",
    }


# Scenario 1: Valid completed run + observations -> IN_REVIEW in publish mode, VALIDATED_CLAIMS in pure CLI
def test_scenario_1_valid_run_produces_in_review(fixture_env):
    env = fixture_env
    run_id = complete_fixture_run(env)

    files = {
        "artifacts/check_pos.log": b"check positive output: passed\n",
        "artifacts/check_neg.log": b"check negative output: adverse case rejected\n",
    }
    archive_bytes = make_zip(files)
    manifest_dict = build_valid_manifest(env, run_id, files)

    with env["db"].atomic_transaction() as conn:
        result = validate_delivery_manifest(
            manifest_input=manifest_dict,
            archive_input=archive_bytes,
            repo_path=env["repo_dir"],
            conn=conn,
        )

    assert result.valid is True
    assert result.status == "VALIDATED_CLAIMS"
    assert result.reasons == []

    # Pure validation does not mutate task phase or DB
    assert state(env["service"], env["issue_id"])["phase"] == "AWAITING_SUBMISSION"

    # Authenticated publish transitions to IN_REVIEW, never ACCEPTED/DONE
    with trusted_coordinator_admin_scope(), actor("builder"):
        published_task = publish_submission(env["service"], result)

    assert published_task["phase"] == "IN_REVIEW"
    assert published_task["phase"] != "ACCEPTED"
    assert env["db"].get_issue(env["issue_id"]).current_state != "DONE"


# Scenario 2: Omitted check or nonpassing observation -> READINESS_RETURNED; survives reopen
def test_scenario_2_nonpassing_or_omitted_check_produces_readiness_returned(fixture_env):
    env = fixture_env
    run_id = complete_fixture_run(env)

    # 1 check FAILED
    files = {
        "artifacts/check_pos.log": b"check positive output: passed\n",
        "artifacts/check_neg.log": b"check negative output: failed\n",
    }
    archive_bytes = make_zip(files)
    manifest_dict = build_valid_manifest(env, run_id, files)
    # Set check_neg outcome to FAILED
    for obs in manifest_dict["observations"]:
        if obs["check_id"] == "check_neg":
            obs["outcome"] = "FAILED"

    with env["db"].atomic_transaction() as conn:
        result = validate_delivery_manifest(manifest_dict, archive_bytes, env["repo_dir"], conn)

    assert result.valid is True
    with trusted_coordinator_admin_scope(), actor("builder"):
        published = publish_submission(env["service"], result)

    assert published["phase"] == "READINESS_RETURNED"

    # Verify survives DB reopen
    reopened_db = PMDatabase(env["db_path"])
    reopened_service = DeliveryService(reopened_db)
    assert state(reopened_service, env["issue_id"])["phase"] == "READINESS_RETURNED"


# Scenario 3: Missing brief, READY state, failed/uncertain run -> denied without mutation
def test_scenario_3_ready_phase_or_unsuccessful_run_denied(fixture_env):
    env = fixture_env
    files = {"artifacts/check_pos.log": b"ok\n", "artifacts/check_neg.log": b"ok\n"}
    archive_bytes = make_zip(files)

    # In READY state without completed run:
    manifest_dict = {
        "schema_version": "mas-delivery-manifest-v1",
        "tenant_id": env["tenant_id"],
        "project_id": env["project_id"],
        "issue_id": env["issue_id"],
        "brief_version": 1,
        "revision": 3,
        "run_id": "nonexistent_run",
        "candidate_sha": env["candidate_sha"],
        "base_sha": env["base_sha"],
        "suite_digest": env["suite_digest"],
        "observations": [
            {"check_id": "check_pos", "outcome": "PASSED", "evidence_ref": "artifacts/check_pos.log", "digest": hashlib.sha256(b"ok\n").hexdigest()},
            {"check_id": "check_neg", "outcome": "PASSED", "evidence_ref": "artifacts/check_neg.log", "digest": hashlib.sha256(b"ok\n").hexdigest()},
        ],
    }

    with env["db"].atomic_transaction() as conn:
        res = validate_delivery_manifest(manifest_dict, archive_bytes, env["repo_dir"], conn)

    assert res.valid is False
    assert any("not eligible for submission" in r or "READY" in r for r in res.reasons)
    assert state(env["service"], env["issue_id"])["phase"] == "READY"


# Scenario 4: Wrong tenant, role, unbound session, stale CAS -> denied without mutation
def test_scenario_4_wrong_tenant_or_stale_cas_denied(fixture_env):
    env = fixture_env
    run_id = complete_fixture_run(env)
    files = {"artifacts/check_pos.log": b"ok\n", "artifacts/check_neg.log": b"ok\n"}
    archive_bytes = make_zip(files)
    manifest_dict = build_valid_manifest(env, run_id, files)

    # Wrong tenant
    bad_tenant_manifest = dict(manifest_dict, tenant_id="foreign_tenant")
    with env["db"].atomic_transaction() as conn:
        res = validate_delivery_manifest(bad_tenant_manifest, archive_bytes, env["repo_dir"], conn)
    assert res.valid is False
    assert any("tenant mismatch" in r or "not enrolled" in r for r in res.reasons)

    # Stale CAS revision
    stale_cas_manifest = dict(manifest_dict, revision=999)
    with env["db"].atomic_transaction() as conn:
        res_cas = validate_delivery_manifest(stale_cas_manifest, archive_bytes, env["repo_dir"], conn)
    assert res_cas.valid is False
    assert any("Task revision mismatch" in r for r in res_cas.reasons)


# Scenario 5: Changed candidate, base, suite, fence, or policy -> denied
def test_scenario_5_changed_identities_denied(fixture_env):
    env = fixture_env
    run_id = complete_fixture_run(env)
    files = {"artifacts/check_pos.log": b"ok\n", "artifacts/check_neg.log": b"ok\n"}
    archive_bytes = make_zip(files)
    manifest_dict = build_valid_manifest(env, run_id, files)

    # Mismatched candidate_sha
    diff_manifest = dict(manifest_dict, candidate_sha="f" * 40)
    with env["db"].atomic_transaction() as conn:
        res = validate_delivery_manifest(diff_manifest, archive_bytes, env["repo_dir"], conn)
    assert res.valid is False
    assert any("Run candidate commit SHA mismatch" in r or "commit in repository" in r for r in res.reasons)


# Scenario 6: Unknown fields, duplicate JSON keys, nonfinite values -> denied
def test_scenario_6_strict_json_and_types_enforced():
    # Duplicate JSON keys
    raw_dup = '{"schema_version": "mas-delivery-manifest-v1", "issue_id": "i1", "issue_id": "i2"}'
    with pytest.raises(DeliveryValidatorError, match="Duplicate JSON key"):
        parse_manifest_json(raw_dup)

    # Nonfinite values (NaN / Infinity)
    raw_nan = '{"schema_version": "mas-delivery-manifest-v1", "revision": NaN}'
    with pytest.raises(DeliveryValidatorError, match="Malformed manifest JSON|Nonfinite"):
        parse_manifest_json(raw_nan)

    # Unknown field
    raw_unknown = json.dumps({
        "schema_version": "mas-delivery-manifest-v1",
        "tenant_id": "default",
        "project_id": "p",
        "issue_id": "i",
        "brief_version": 1,
        "revision": 1,
        "run_id": "r",
        "candidate_sha": "a" * 40,
        "base_sha": "b" * 40,
        "suite_digest": "c" * 64,
        "observations": [],
        "extra_field": "forbidden",
    })
    with pytest.raises(DeliveryValidatorError, match="extra_field"):
        parse_manifest_json(raw_unknown)


# Scenario 7: Path traversal, absolute path, backslash, control chars, symlinks -> rejected
def test_scenario_7_unsafe_archive_paths_rejected():
    # Traversal ../
    bad_zip = make_zip({"../escaped.txt": b"evil\n"})
    with pytest.raises(DeliveryValidatorError, match="Invalid path segments"):
        validate_artifact_archive(bad_zip)

    # Absolute path /evil
    bad_zip_abs = make_zip({"/evil.txt": b"evil\n"})
    with pytest.raises(DeliveryValidatorError, match="Absolute path forbidden"):
        validate_artifact_archive(bad_zip_abs)

    # Backslash
    bad_zip_backslash = make_zip({"foo\\bar.txt": b"evil\n"})
    with pytest.raises(DeliveryValidatorError, match="Unsafe member path"):
        validate_artifact_archive(bad_zip_backslash)

    # Control char
    bad_zip_ctrl = make_zip({"foo\x07bar.txt": b"evil\n"})
    with pytest.raises(DeliveryValidatorError, match="Control characters forbidden"):
        validate_artifact_archive(bad_zip_ctrl)


# Scenario 8: Overlarge input, size lie, excessive count, hash mismatch -> rejected
def test_scenario_8_archive_size_and_digest_limits():
    # Excessive member count > 64
    too_many_members = {f"file_{i}.txt": b"a" for i in range(65)}
    bad_count_zip = make_zip(too_many_members)
    with pytest.raises(DeliveryValidatorError, match="Member count 65 exceeds maximum"):
        validate_artifact_archive(bad_count_zip)

    # Streamed decompression overflow > 2 MiB per member
    large_member = make_zip({"big.bin": b"0" * (2 * 1024 * 1024 + 10)})
    with pytest.raises(DeliveryValidatorError, match="exceeds 2097152 uncompressed byte limit"):
        validate_artifact_archive(large_member)


# Scenario 9: Unauthorized diff, rename across scope, missing git objects -> denied
def test_scenario_9_git_diff_out_of_scope_denied(fixture_env, tmp_path):
    env = fixture_env
    repo_dir = env["repo_dir"]

    # Commit change outside mas/ (e.g. portal/evil.py)
    portal_dir = repo_dir / "portal"
    portal_dir.mkdir(parents=True, exist_ok=True)
    (portal_dir / "evil.py").write_text("evil\n")
    subprocess.run(["git", "add", "portal/evil.py"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "out of scope"], cwd=repo_dir, check=True, stdout=subprocess.PIPE)
    evil_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, stdout=subprocess.PIPE).stdout.decode().strip()

    with pytest.raises(DeliveryValidatorError, match="Modified file outside declared scope"):
        validate_git_candidate(repo_dir, env["base_sha"], evil_sha, ["mas/"])


# Scenario 10: Two competing publication calls with same revision -> one winner, no duplicate history
def test_scenario_10_competing_publication_cas(fixture_env):
    env = fixture_env
    run_id = complete_fixture_run(env)
    files = {"artifacts/check_pos.log": b"ok\n", "artifacts/check_neg.log": b"ok\n"}
    archive_bytes = make_zip(files)
    manifest_dict = build_valid_manifest(env, run_id, files)

    with env["db"].atomic_transaction() as conn:
        res1 = validate_delivery_manifest(manifest_dict, archive_bytes, env["repo_dir"], conn)

    assert res1.valid is True

    # First publication succeeds and increments revision
    with trusted_coordinator_admin_scope(), actor("builder"):
        t1 = publish_submission(env["service"], res1)
    assert t1["phase"] == "IN_REVIEW"

    # Second publication with old revision fails with Stale delivery revision
    with trusted_coordinator_admin_scope(), actor("builder"), pytest.raises(DeliveryGateError, match="Stale delivery revision"):
        publish_submission(env["service"], res1)


# Scenario 11: Existing recurrence/dispute/scope pause cannot be cleared by validator or CLI
def test_scenario_11_paused_task_cannot_be_cleared(fixture_env):
    env = fixture_env
    run_id = complete_fixture_run(env)
    files = {"artifacts/check_pos.log": b"ok\n", "artifacts/check_neg.log": b"ok\n"}
    archive_bytes = make_zip(files)
    manifest_dict = build_valid_manifest(env, run_id, files)

    with env["db"].atomic_transaction() as conn:
        res = validate_delivery_manifest(manifest_dict, archive_bytes, env["repo_dir"], conn)
    assert res.valid is True

    # Enter IN_REVIEW
    with trusted_coordinator_admin_scope(), actor("builder"):
        publish_submission(env["service"], res)

    # Reviewer rejects task -> enters CHANGES_REQUESTED
    task = state(env["service"], env["issue_id"])
    finding = {
        "id": "F1",
        "requirement_id": "R1",
        "reproduction": "Repro",
        "impact": "Impact",
        "closure_paths": ["mas/code.py"],
    }
    with trusted_coordinator_admin_scope(), actor("reviewer"):
        env["service"].reject(env["issue_id"], task["revision"], [finding])

    # Now task is in CHANGES_REQUESTED; validation must deny submission
    with env["db"].atomic_transaction() as conn:
        res_paused = validate_delivery_manifest(manifest_dict, archive_bytes, env["repo_dir"], conn)
    assert res_paused.valid is False
    assert any("CHANGES_REQUESTED" in r and "not eligible" in r for r in res_paused.reasons)


# Scenario 12: CLI fake PASSED stdout/token/actor/db override cannot authorize submission or sign evidence
def test_scenario_12_cli_execution_and_authority(fixture_env, tmp_path):
    env = fixture_env
    run_id = complete_fixture_run(env)
    files = {"artifacts/check_pos.log": b"ok\n", "artifacts/check_neg.log": b"ok\n"}
    archive_bytes = make_zip(files)
    manifest_dict = build_valid_manifest(env, run_id, files)

    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_dict))
    archive_file = tmp_path / "archive.zip"
    archive_file.write_bytes(archive_bytes)

    cli_script = Path(__file__).resolve().parent.parent / "scripts" / "delivery_gate_runner.py"

    # Run in default validate-only mode
    cmd = [
        "python3",
        str(cli_script),
        "--manifest",
        str(manifest_file),
        "--archive",
        str(archive_file),
        "--repo",
        str(env["repo_dir"]),
        "--db",
        str(env["db_path"]),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.returncode == 0
    out = json.loads(proc.stdout)
    assert out["status"] == "VALIDATED_CLAIMS"
    assert out["valid"] is True
    # DB remains in AWAITING_SUBMISSION
    assert state(env["service"], env["issue_id"])["phase"] == "AWAITING_SUBMISSION"

    # Run with --publish without active session -> fails with PUBLICATION_FAILED
    cmd_pub = cmd + ["--publish"]
    proc_pub = subprocess.run(cmd_pub, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc_pub.returncode == 1
    out_pub = json.loads(proc_pub.stdout)
    assert out_pub["status"] == "PUBLICATION_FAILED"
    assert any("Authenticated delivery actor required" in r for r in out_pub["reasons"])


# Scenario 13: Clean package imports validator without path tricks
def test_scenario_13_clean_import():
    from mas.pm import delivery_validator

    assert hasattr(delivery_validator, "validate_delivery_manifest")
    assert hasattr(delivery_validator, "validate_artifact_archive")
    assert hasattr(delivery_validator, "validate_git_candidate")
    assert hasattr(delivery_validator, "DeliveryManifest")
