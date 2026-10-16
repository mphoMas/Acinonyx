"""Wave 4 qualification tests for AutomaticCorrectionLoop (CC-07, CC-08, CC-11, CC-12 — P6)."""
from __future__ import annotations

import base64
import hashlib
import secrets
import subprocess
import uuid
from pathlib import Path

import pytest

from mas.iam import MultiTenantIAM
from mas.pm.activity import ActivityBridgeService
from mas.pm.adapters.admission import EvidenceTrust, IssuerGrant
from mas.pm.adapters.exporter import CANDIDATE_SCHEMA, CandidateExporter
from mas.pm.adapters.verifier import SCHEMA, evidence_binding, sign_payload
from mas.pm.coordinator import CoordinatorStore, trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.loop import AutomaticCorrectionLoop, LoopError
from mas.pm.models import Issue, IssueState, Project


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("utf-8")
    return hashlib.sha1(header + content).hexdigest()


@pytest.fixture
def wave4_env(tmp_path: Path):
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(repo_path), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    git("init", "-b", "main")
    git("config", "user.name", "Operator")
    git("config", "user.email", "operator@mas.internal")
    (repo_path / "pkg").mkdir()
    init_bytes = b"def solve(payload):\n    return 0\n"
    (repo_path / "pkg" / "solution.py").write_bytes(init_bytes)
    git("add", ".")
    git("commit", "-m", "initial commit")
    base_sha = git("rev-parse", "HEAD")
    base_blob_sha = _git_blob_sha(init_bytes)

    db = PMDatabase(tmp_path / "pm.db")
    db.create_project(Project(id="proj-1", key="SBA", name="SBA Project", token_budget=100000))
    db.create_issue(
        Issue(
            id="iss-1",
            project_id="proj-1",
            key="SBA-1",
            task_id="task-1",
            title="Implement bounded automatic correction loop",
            current_state=IssueState.BACKLOG,
            assignee_principal="tenant-1:builder-1",
            appetite_tokens=20000,
            path_whitelist=["pkg/solution.py"],
            forbidden_paths=["pkg/secret.py"],
        )
    )
    with db.atomic_transaction() as c:
        c.execute(
            """
            INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
            VALUES ('proj-1', 'CC-07', 'task-1', 'iss-1', 'SBA-1')
            """
        )

    iam = MultiTenantIAM(secrets.token_hex(32), db_path=tmp_path / "iam.db")
    iam.create_tenant("tenant-1", "Tenant 1")
    iam.register_principal(
        "tenant-1",
        "builder-1",
        scopes={"coordinator:broker:invoke", "coordinator:candidate:export"},
    )
    iam.register_principal("tenant-1", "verifier-1", scopes={"coordinator:evidence:verify"})
    iam.register_principal("tenant-1", "reviewer-1", scopes={"coordinator:evidence:review"})
    iam.register_principal("tenant-1", "merger-1", scopes={"coordinator:candidate:integrate"})

    tokens = {
        "builder": iam.issue_token("tenant-1", "builder-1"),
        "verifier": iam.issue_token("tenant-1", "verifier-1"),
        "reviewer": iam.issue_token("tenant-1", "reviewer-1"),
        "merger": iam.issue_token("tenant-1", "merger-1"),
    }

    verify_secret = secrets.token_bytes(32)
    review_secret = secrets.token_bytes(32)
    trust = EvidenceTrust(
        {
            "verify-key": IssuerGrant("verifier-1", "tenant-1", "VERIFICATION_EVIDENCE", verify_secret),
            "review-key": IssuerGrant("reviewer-1", "tenant-1", "REVIEW_EVIDENCE", review_secret),
        },
        iam=iam,
        issuer_tokens={"verify-key": tokens["verifier"], "review-key": tokens["reviewer"]},
    )
    store = CoordinatorStore(db, evidence_trust=trust)
    activity = ActivityBridgeService(db, evidence_trust=trust)
    exporter = CandidateExporter(db=db, repo_root=repo_path, repo_identity="test-repo", iam=iam)
    loop = AutomaticCorrectionLoop(db, coordinator=store, activity=activity)

    return {
        "repo_path": repo_path,
        "git": git,
        "base_sha": base_sha,
        "base_blob_sha": base_blob_sha,
        "db": db,
        "iam": iam,
        "tokens": tokens,
        "trust": trust,
        "store": store,
        "activity": activity,
        "exporter": exporter,
        "loop": loop,
        "verify_secret": verify_secret,
        "review_secret": review_secret,
    }


def _record_and_maybe_admit_evidence(
    env: dict,
    *,
    evidence_id: str,
    evidence_type: str,
    attempt_id: str,
    run_id: str,
    fencing_token: int,
    candidate_sha: str,
    result: dict,
    admit: bool,
) -> dict:
    is_verify = evidence_type == "VERIFICATION_EVIDENCE"
    binding = evidence_binding(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id=attempt_id,
        run_id=run_id,
        candidate_commit_sha=candidate_sha,
        base_commit_sha=env["base_sha"],
        policy_version=1,
        fencing_token=fencing_token,
        suite_digest="a" * 64,
        worker_image="python:3.12-slim@sha256:" + "0" * 64,
        developer_principal_id="builder-1",
    )
    nonce = secrets.token_hex(16)
    key_id = "verify-key" if is_verify else "review-key"
    issuer_id = "verifier-1" if is_verify else "reviewer-1"
    payload = {
        **binding,
        "schema": SCHEMA,
        "domain": "PRODUCTION",
        "type": evidence_type,
        "issuer_id": issuer_id,
        "key_id": key_id,
        "nonce": nonce,
        "result": result,
    }
    secret = env["verify_secret"] if is_verify else env["review_secret"]
    sig = sign_payload(payload, secret)
    with trusted_coordinator_admin_scope():
        env["store"].register_evidence_contract(binding, "verifier-1", "reviewer-1", ["c1"])
        env["store"].record_evidence_receipt(
            evidence_id=evidence_id,
            issue_id="iss-1",
            task_id="task-1",
            attempt_id=attempt_id,
            run_id=run_id,
            candidate_commit_sha=candidate_sha,
            nonce=nonce,
            key_id=key_id,
            signature=sig,
            canonical_payload=payload,
        )
        if admit:
            assert env["store"].admit_evidence_receipt(evidence_id) is True
    return {"evidence_id": evidence_id, "canonical_payload": payload, "signature": sig}


def test_full_bounded_automatic_correction_loop_to_guarded_done(wave4_env: dict) -> None:
    loop: AutomaticCorrectionLoop = wave4_env["loop"]
    exporter: CandidateExporter = wave4_env["exporter"]
    tokens = wave4_env["tokens"]
    base_sha = wave4_env["base_sha"]
    base_blob_sha = wave4_env["base_blob_sha"]
    db: PMDatabase = wave4_env["db"]

    # 1. Admit task
    adm = loop.admit_task(
        job_id="job-1",
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        profile="coding.solve.v1",
        base_commit_sha=base_sha,
        now_epoch=1000.0,
    )
    assert adm["stage"] == "ADMITTED"
    assert db.get_issue("iss-1").current_state == IssueState.STAGED

    # 2. Attempt 1: Begin development & export candidate 1
    dev1 = loop.begin_development(
        "job-1",
        worker_id="worker-1",
        run_id="run-1",
        session_id="sess-1",
        now_epoch=1005.0,
    )
    assert dev1["stage"] == "DEVELOPING"
    assert db.get_issue("iss-1").current_state == IssueState.IN_PROGRESS

    cand1_bytes = b"def solve(payload):\n    return 1\n"
    exp1 = loop.export_candidate_stage(
        "job-1",
        exporter=exporter,
        session_token=tokens["builder"],
        proposal={
            "schema": CANDIDATE_SCHEMA,
            "proposal_id": str(uuid.uuid4()),
            "base_commit_sha": base_sha,
            "files": [
                {
                    "operation": "WRITE",
                    "path": "pkg/solution.py",
                    "expected_base_blob_sha": base_blob_sha,
                    "content_base64": base64.b64encode(cand1_bytes).decode("ascii"),
                }
            ],
        },
        now_epoch=1010.0,
    )
    assert exp1["stage"] == "VERIFYING"
    cand1_sha = exp1["candidate_commit_sha"]
    assert db.get_issue("iss-1").current_state == IssueState.VERIFICATION

    # 3. Verifier rejects candidate 1 -> automatic rework to Attempt 2
    v1_receipt = _record_and_maybe_admit_evidence(
        wave4_env,
        evidence_id="ev-verify-1",
        evidence_type="VERIFICATION_EVIDENCE",
        attempt_id=dev1["attempt_id"],
        run_id="run-1",
        fencing_token=dev1["fencing_token"],
        candidate_sha=cand1_sha,
        result={
            "passed": False,
            "test_count": 1,
            "outcomes": [{"id": "c1", "passed": False, "reason": "<script>alert(1)</script>Wrong output"}],
        },
        admit=False,
    )
    rework1 = loop.record_verification_outcome("job-1", verification_receipt=v1_receipt, now_epoch=1015.0)
    assert rework1["stage"] == "REWORK_PENDING"
    assert rework1["attempt_seq"] == 2
    assert "[stripped]" in rework1["findings"][0]["corrective_requirement"]
    assert db.get_issue("iss-1").current_state == IssueState.REJECTED_REWORK

    # Idempotent replay of the same rejection receipt returns the exact same attempt without creating Attempt 3
    rework1_replay = loop.record_verification_outcome("job-1", verification_receipt=v1_receipt, now_epoch=1016.0)
    assert rework1_replay["replayed"] is True
    assert rework1_replay["next_attempt_id"] == rework1["next_attempt_id"]

    # 4. Attempt 2: Begin development, export candidate 2, pass verification, fail independent review -> Attempt 3
    dev2 = loop.begin_development(
        "job-1",
        worker_id="worker-1",
        run_id="run-2",
        session_id="sess-2",
        now_epoch=1020.0,
    )
    assert dev2["stage"] == "DEVELOPING"
    assert db.get_issue("iss-1").current_state == IssueState.IN_PROGRESS

    cand2_bytes = b"def solve(payload):\n    return payload + 1\n"
    exp2 = loop.export_candidate_stage(
        "job-1",
        exporter=exporter,
        session_token=tokens["builder"],
        proposal={
            "schema": CANDIDATE_SCHEMA,
            "proposal_id": str(uuid.uuid4()),
            "base_commit_sha": base_sha,
            "files": [
                {
                    "operation": "WRITE",
                    "path": "pkg/solution.py",
                    "expected_base_blob_sha": base_blob_sha,
                    "content_base64": base64.b64encode(cand2_bytes).decode("ascii"),
                }
            ],
        },
        now_epoch=1025.0,
    )
    cand2_sha = exp2["candidate_commit_sha"]
    assert cand2_sha != cand1_sha

    v2_receipt = _record_and_maybe_admit_evidence(
        wave4_env,
        evidence_id="ev-verify-2",
        evidence_type="VERIFICATION_EVIDENCE",
        attempt_id=dev2["attempt_id"],
        run_id="run-2",
        fencing_token=dev2["fencing_token"],
        candidate_sha=cand2_sha,
        result={"passed": True, "test_count": 1, "outcomes": [{"id": "c1", "passed": True}]},
        admit=True,
    )
    v2_out = loop.record_verification_outcome("job-1", verification_receipt=v2_receipt, now_epoch=1030.0)
    assert v2_out["stage"] == "REVIEWING"
    assert db.get_issue("iss-1").current_state == IssueState.JUDICIAL_REVIEW

    r2_receipt = _record_and_maybe_admit_evidence(
        wave4_env,
        evidence_id="ev-review-2",
        evidence_type="REVIEW_EVIDENCE",
        attempt_id=dev2["attempt_id"],
        run_id="run-2",
        fencing_token=dev2["fencing_token"],
        candidate_sha=cand2_sha,
        result={
            "verdict": "REJECTED",
            "comments": "Handle negative payload edge case explicitly",
            "findings": [
                {
                    "finding_id": "rev-1",
                    "severity": "HIGH",
                    "affected_path": "pkg/solution.py",
                    "corrective_requirement": "Handle negative payload edge case explicitly",
                }
            ],
        },
        admit=False,
    )
    rework2 = loop.record_review_outcome("job-1", review_receipt=r2_receipt, now_epoch=1035.0)
    assert rework2["stage"] == "REWORK_PENDING"
    assert rework2["attempt_seq"] == 3
    assert db.get_issue("iss-1").current_state == IssueState.REJECTED_REWORK

    # 5. Attempt 3: Final corrected candidate -> verify PASS -> review APPROVED -> AWAITING_REQUIRED_APPROVAL
    dev3 = loop.begin_development(
        "job-1",
        worker_id="worker-1",
        run_id="run-3",
        session_id="sess-3",
        now_epoch=1040.0,
    )
    cand3_bytes = b"def solve(payload):\n    return max(0, payload) + 1\n"
    exp3 = loop.export_candidate_stage(
        "job-1",
        exporter=exporter,
        session_token=tokens["builder"],
        proposal={
            "schema": CANDIDATE_SCHEMA,
            "proposal_id": str(uuid.uuid4()),
            "base_commit_sha": base_sha,
            "files": [
                {
                    "operation": "WRITE",
                    "path": "pkg/solution.py",
                    "expected_base_blob_sha": base_blob_sha,
                    "content_base64": base64.b64encode(cand3_bytes).decode("ascii"),
                }
            ],
        },
        now_epoch=1045.0,
    )
    cand3_sha = exp3["candidate_commit_sha"]

    v3_receipt = _record_and_maybe_admit_evidence(
        wave4_env,
        evidence_id="ev-verify-3",
        evidence_type="VERIFICATION_EVIDENCE",
        attempt_id=dev3["attempt_id"],
        run_id="run-3",
        fencing_token=dev3["fencing_token"],
        candidate_sha=cand3_sha,
        result={"passed": True, "test_count": 1, "outcomes": [{"id": "c1", "passed": True}]},
        admit=True,
    )
    loop.record_verification_outcome("job-1", verification_receipt=v3_receipt, now_epoch=1050.0)

    r3_receipt = _record_and_maybe_admit_evidence(
        wave4_env,
        evidence_id="ev-review-3",
        evidence_type="REVIEW_EVIDENCE",
        attempt_id=dev3["attempt_id"],
        run_id="run-3",
        fencing_token=dev3["fencing_token"],
        candidate_sha=cand3_sha,
        result={"verdict": "APPROVED", "comments": "All requirements satisfied."},
        admit=True,
    )
    rev3_out = loop.record_review_outcome("job-1", review_receipt=r3_receipt, now_epoch=1055.0)
    assert rev3_out["stage"] == "AWAITING_REQUIRED_APPROVAL"
    # Issue is still in JUDICIAL_REVIEW (never auto-completes without separate human approval!)
    assert db.get_issue("iss-1").current_state == IssueState.JUDICIAL_REVIEW

    # 6. Record separate human approval and run CAS integration + guarded completion
    done_out = loop.integrate_and_complete(
        "job-1",
        exporter=exporter,
        merger_id="merger-1",
        merger_session_token=tokens["merger"],
        target_ref="refs/heads/main",
        authorization_ref="appr-1",
        human_approver_principal="tenant-1:human_release_mgr",
        evidence_trust=wave4_env["trust"],
        now_epoch=1060.0,
    )
    assert done_out["stage"] == "COMPLETE"
    assert done_out["integrated_commit_sha"] == cand3_sha
    assert db.get_issue("iss-1").current_state == IssueState.DONE
    assert wave4_env["git"]("rev-parse", "refs/heads/main") == cand3_sha

    # Verify activity projection shows all 3 attempts and stale vs validated reviews
    act = wave4_env["activity"].get_task_activity(tenant_id="tenant-1", issue_or_task_id="iss-1")
    assert len(act["attempts"]) == 3
    assert [a["state"] for a in act["attempts"]] == ["FAILED", "FAILED", "SUCCEEDED"]
    assert act["current_candidate_commit"] == cand3_sha


def test_loop_policy_staleness_pause_cancel_and_uncertainty_escalation(wave4_env: dict) -> None:
    loop: AutomaticCorrectionLoop = wave4_env["loop"]
    db: PMDatabase = wave4_env["db"]
    base_sha = wave4_env["base_sha"]

    # Unsupported profile fails closed and sets blocker_reason
    with pytest.raises(LoopError) as exc_prof:
        loop.admit_task(
            job_id="job-bad-prof",
            tenant_id="tenant-1",
            project_id="proj-1",
            issue_id="iss-1",
            task_id="task-1",
            profile="unsupported.magic.v1",
            base_commit_sha=base_sha,
        )
    assert exc_prof.value.code == "unsupported_profile"
    assert "unsupported_profile" in (db.get_issue("iss-1").blocker_reason or "")

    # Admit valid job
    loop.admit_task(
        job_id="job-ops",
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        profile="coding.solve.v1",
        base_commit_sha=base_sha,
        now_epoch=2000.0,
    )

    # Pause blocks development start
    loop.pause_job("job-ops", actor="tenant-1:operator", reason="Maintenance window")
    with pytest.raises(LoopError) as exc_paused:
        loop.begin_development(
            "job-ops",
            worker_id="worker-1",
            run_id="run-ops-1",
            session_id="sess-ops-1",
            now_epoch=2005.0,
        )
    assert exc_paused.value.code == "job_paused"

    # Resume unblocks
    loop.resume_job("job-ops", actor="tenant-1:operator", now_epoch=2006.0)
    loop.begin_development(
        "job-ops",
        worker_id="worker-1",
        run_id="run-ops-1",
        session_id="sess-ops-1",
        now_epoch=2007.0,
    )

    # Pending cancellation (confirm_stopped=False) projects as CANCEL_REQUESTED, not CANCELLED
    c_req = loop.cancel_job("job-ops", actor="tenant-1:operator", reason="Stop requested", confirm_stopped=False)
    assert c_req["cancellation_state"] == "CANCEL_REQUESTED"
    assert c_req["confirmed_stopped"] is False
    act_pending = wave4_env["activity"].get_task_activity(tenant_id="tenant-1", issue_or_task_id="iss-1")
    assert act_pending["attempts"][0]["state"] == "CANCEL_REQUESTED"

    # Confirmed stop transitions to CANCELLED
    c_done = loop.cancel_job("job-ops", actor="tenant-1:operator", reason="Container stopped", confirm_stopped=True)
    assert c_done["cancellation_state"] == "CANCELED"
    assert c_done["confirmed_stopped"] is True
    act_done = wave4_env["activity"].get_task_activity(tenant_id="tenant-1", issue_or_task_id="iss-1")
    assert act_done["attempts"][0]["state"] == "CANCELLED"
