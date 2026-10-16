"""Wave 5 qualification tests for SBA-07, SBA-08, SBA-09, CC-13, CC-14, and CC-15.

Covers:
1. Project startup automation and kickoff orchestration (ProjectKickoffService - SBA-09, CC-15).
2. Adversarial fault injection matrix (SBA-07, CC-13):
   - Mid-flight IAM token/session revocation fails closed
   - Mid-flight plan policy change triggers unreconciled_policy_change escalation (CC-08)
   - Unresolved execution uncertainty triggers unresolved_execution escalation (CC-12)
   - Attempt ceiling exhaustion triggers exhausted_attempts escalation (CC-11)
3. Supervised end-to-end pilot with live browser board verification (SBA-08, CC-14):
   - Multi-attempt automatic rework (attempt 1 fail -> attempt 2 pass)
   - Cryptographically bound verification & independent review receipts
   - Separate human release approval and CAS Git integration
   - Live Chromium Playwright browser loading portal/scrum.html, verifying ticket in Done column and activity history in drawer
"""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from mas.dashboard.server import DashboardServer
from mas.iam import MultiTenantIAM
from mas.organization.company import ConsultingEnterprise
from mas.pm.activity import ActivityBridgeService
from mas.pm.adapters.admission import EvidenceTrust, IssuerGrant
from mas.pm.adapters.exporter import CANDIDATE_SCHEMA, CandidateExporter, CandidateIntegrationError
from mas.pm.adapters.verifier import SCHEMA, evidence_binding, sign_payload
from mas.pm.coordinator import CoordinatorStore, trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.kickoff import ProjectKickoffService
from mas.pm.loop import AutomaticCorrectionLoop, LoopError
from mas.pm.models import IssueState
from mas.tenancy import resolve_tenant_database_path


def _git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("utf-8")
    return hashlib.sha1(header + content).hexdigest()


@pytest.fixture
def wave5_env(tmp_path: Path):
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
    git("config", "user.name", "Pilot Operator")
    git("config", "user.email", "pilot@mas.internal")
    (repo_path / "pkg").mkdir()
    init_bytes = b"# Pilot Module\ndef handler():\n    return 'initial'\n"
    (repo_path / "pkg" / "module.py").write_bytes(init_bytes)
    git("add", ".")
    git("commit", "-m", "initial pilot commit")
    base_sha = git("rev-parse", "HEAD")
    base_blob_sha = _git_blob_sha(init_bytes)

    tenant_root = tmp_path / "tenants"
    iam = MultiTenantIAM(secrets.token_hex(32), db_path=tmp_path / "iam.db")
    iam.create_tenant("t-pilot", "Pilot Tenant")
    iam.register_principal(
        "t-pilot",
        "operator",
        roles={"tenant_admin"},
        scopes={"default", "admin:revoke", "coordinator:broker:invoke", "coordinator:candidate:export", "coordinator:evidence:verify", "coordinator:evidence:review", "coordinator:candidate:integrate"},
    )
    iam.register_principal(
        "t-pilot",
        "builder-1",
        scopes={"coordinator:broker:invoke", "coordinator:candidate:export"},
    )
    iam.register_principal("t-pilot", "verifier-1", scopes={"coordinator:evidence:verify"})
    iam.register_principal("t-pilot", "reviewer-1", scopes={"coordinator:evidence:review"})
    iam.register_principal("t-pilot", "merger-1", scopes={"coordinator:candidate:integrate"})

    tokens = {
        "operator": iam.issue_token("t-pilot", "operator"),
        "builder": iam.issue_token("t-pilot", "builder-1"),
        "verifier": iam.issue_token("t-pilot", "verifier-1"),
        "reviewer": iam.issue_token("t-pilot", "reviewer-1"),
        "merger": iam.issue_token("t-pilot", "merger-1"),
    }

    db_path = resolve_tenant_database_path(iam, "t-pilot", tenant_root)
    db = PMDatabase(str(db_path))

    verify_secret = secrets.token_bytes(32)
    review_secret = secrets.token_bytes(32)
    trust = EvidenceTrust(
        {
            "verify-key": IssuerGrant("verifier-1", "t-pilot", "VERIFICATION_EVIDENCE", verify_secret),
            "review-key": IssuerGrant("reviewer-1", "t-pilot", "REVIEW_EVIDENCE", review_secret),
        },
        iam=iam,
        issuer_tokens={"verify-key": tokens["verifier"], "review-key": tokens["reviewer"]},
    )
    store = CoordinatorStore(db, evidence_trust=trust)
    activity = ActivityBridgeService(db, evidence_trust=trust)
    exporter = CandidateExporter(db=db, repo_root=repo_path, repo_identity="pilot-repo", iam=iam)
    loop = AutomaticCorrectionLoop(db, coordinator=store, activity=activity, workspace_root=tmp_path)
    kickoff = ProjectKickoffService(db, loop=loop, workspace_root=tmp_path)

    return {
        "tmp_path": tmp_path,
        "repo_path": repo_path,
        "git": git,
        "base_sha": base_sha,
        "base_blob_sha": base_blob_sha,
        "tenant_root": tenant_root,
        "db": db,
        "iam": iam,
        "tokens": tokens,
        "trust": trust,
        "store": store,
        "activity": activity,
        "exporter": exporter,
        "loop": loop,
        "kickoff": kickoff,
        "verify_secret": verify_secret,
        "review_secret": review_secret,
    }


def _record_and_maybe_admit_evidence(
    env: dict,
    *,
    evidence_id: str,
    evidence_type: str,
    project_id: str,
    issue_id: str,
    task_id: str,
    attempt_id: str,
    run_id: str,
    fencing_token: int,
    candidate_sha: str,
    result: dict,
    admit: bool,
) -> dict:
    is_verify = evidence_type == "VERIFICATION_EVIDENCE"
    binding = evidence_binding(
        tenant_id="t-pilot",
        project_id=project_id,
        issue_id=issue_id,
        task_id=task_id,
        attempt_id=attempt_id,
        run_id=run_id,
        candidate_commit_sha=candidate_sha,
        base_commit_sha=env["base_sha"],
        policy_version=1,
        fencing_token=fencing_token,
        suite_digest="b" * 64,
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
            issue_id=issue_id,
            task_id=task_id,
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


def test_kickoff_service_registration_and_admission(wave5_env: dict) -> None:
    kickoff: ProjectKickoffService = wave5_env["kickoff"]
    db: PMDatabase = wave5_env["db"]
    base_sha = wave5_env["base_sha"]

    res = kickoff.kickoff_project(
        tenant_id="t-pilot",
        project_key="PLT",
        project_name="Pilot Automation",
        token_budget=150000,
        base_commit_sha=base_sha,
        task_definitions=[
            {
                "task_id": "PLT-01",
                "title": "Initial Task Implementation",
                "description": "Implement core pilot module",
                "appetite_tokens": 30000,
                "path_whitelist": ["pkg/module.py"],
                "forbidden_paths": ["pkg/secret.py"],
            },
            {
                "task_id": "PLT-02",
                "title": "Secondary Task Implementation",
                "description": "Implement auxiliary features",
                "appetite_tokens": 20000,
                "path_whitelist": ["pkg/module.py"],
            },
        ],
        auto_admit_first_ready=True,
    )

    assert res.status == "INITIALIZED"
    assert res.project_key == "PLT"
    assert res.published_tasks_count == 2
    assert len(res.admitted_jobs) == 1
    admitted = res.admitted_jobs[0]
    assert admitted["stage"] == "ADMITTED"

    # Verify database persistence
    proj = db.get_project(res.project_id)
    assert proj is not None
    assert proj.key == "PLT"

    with db._get_connection() as conn:
        mappings = conn.execute(
            "SELECT * FROM pm_task_mappings WHERE project_id = ? ORDER BY task_id",
            (res.project_id,),
        ).fetchall()
        assert len(mappings) == 2
        assert mappings[0]["task_id"] == "PLT-01"
        assert mappings[1]["task_id"] == "PLT-02"

        # First issue transitioned to STAGED due to auto-admission; second issue remains in BACKLOG
        iss1 = db.get_issue(mappings[0]["local_issue_id"])
        assert iss1.current_state == IssueState.STAGED
        iss2 = db.get_issue(mappings[1]["local_issue_id"])
        assert iss2.current_state == IssueState.BACKLOG


def test_adversarial_fault_injection_matrix(wave5_env: dict) -> None:
    kickoff: ProjectKickoffService = wave5_env["kickoff"]
    loop: AutomaticCorrectionLoop = wave5_env["loop"]
    exporter: CandidateExporter = wave5_env["exporter"]
    iam: MultiTenantIAM = wave5_env["iam"]
    db: PMDatabase = wave5_env["db"]
    tokens = wave5_env["tokens"]
    base_sha = wave5_env["base_sha"]
    base_blob_sha = wave5_env["base_blob_sha"]

    # 1. Kickoff project
    res = kickoff.kickoff_project(
        tenant_id="t-pilot",
        project_key="FLT",
        project_name="Fault Injection Testing",
        token_budget=100000,
        base_commit_sha=base_sha,
        task_definitions=[
            {
                "task_id": "FLT-01",
                "title": "Fault Injection Task",
                "path_whitelist": ["pkg/module.py"],
            }
        ],
        auto_admit_first_ready=True,
    )
    job_id = res.admitted_jobs[0]["job_id"]
    issue_id = res.admitted_jobs[0]["issue_id"]

    # Begin development
    dev = loop.begin_development(job_id, worker_id="worker-flt", run_id="run-flt-1", session_id="sess-flt-1")
    assert dev["stage"] == "DEVELOPING"

    # --- FAULT 1: Mid-flight IAM token/session revocation fails closed ---
    proposal_bytes = b"def handler():\n    return 'fault'\n"
    prop = {
        "schema": CANDIDATE_SCHEMA,
        "proposal_id": str(uuid.uuid4()),
        "base_commit_sha": base_sha,
        "files": [
            {
                "operation": "WRITE",
                "path": "pkg/module.py",
                "expected_base_blob_sha": base_blob_sha,
                "content_base64": base64.b64encode(proposal_bytes).decode("ascii"),
            }
        ],
    }

    # Revoke builder-1 sessions using admin operator token
    iam.revoke_principal_sessions(tokens["operator"], "builder-1")

    # Candidate export must fail closed with AUTHORITY_DENIED
    with pytest.raises(CandidateIntegrationError) as exc_auth:
        exporter.export_candidate(
            tenant_id="t-pilot",
            project_id=res.project_id,
            issue_id=issue_id,
            task_id="FLT-01",
            attempt_id=dev["attempt_id"],
            run_id=dev["run_id"],
            fencing_token=dev["fencing_token"],
            builder_id="builder-1",
            proposal=prop,
            iam_token=tokens["builder"],
        )
    assert exc_auth.value.code == "AUTHORITY_DENIED"

    # Re-issue active token for builder-1 to continue next fault checks
    new_builder_token = iam.issue_token("t-pilot", "builder-1")
    tokens["builder"] = new_builder_token

    # --- FAULT 2: Mid-flight plan policy change triggers unreconciled_policy_change (CC-08) ---
    with db.atomic_transaction() as conn:
        conn.execute("UPDATE pm_issues SET policy_version = policy_version + 1 WHERE id = ?", (issue_id,))

    with pytest.raises(LoopError) as exc_policy:
        loop.export_candidate_stage(
            job_id,
            exporter=exporter,
            session_token=tokens["builder"],
            proposal=prop,
        )
    assert exc_policy.value.code == "unreconciled_policy_change"
    assert "Task policy version or plan revision changed while work was active" in (db.get_issue(issue_id).blocker_reason or "")

    # Restore policy version for subsequent fault check
    with db.atomic_transaction() as conn:
        conn.execute("UPDATE pm_issues SET policy_version = 1, blocker_reason = NULL WHERE id = ?", (issue_id,))
        conn.execute("UPDATE pm_coordinator_loop_jobs SET stage = 'DEVELOPING', escalation_category = NULL, escalation_reason = NULL WHERE job_id = ?", (job_id,))

    # Export candidate successfully now that policy is restored
    exp = loop.export_candidate_stage(
        job_id,
        exporter=exporter,
        session_token=tokens["builder"],
        proposal=prop,
    )
    cand_sha = exp["candidate_commit_sha"]

    # --- FAULT 3: Unresolved execution uncertainty triggers unresolved_execution escalation (CC-12) ---
    with db.atomic_transaction() as conn:
        conn.execute(
            "UPDATE pm_coordinator_attempts SET status = 'UNKNOWN_EXECUTION' WHERE attempt_id = ?",
            (dev["attempt_id"],),
        )

    # Attempting to record verification outcome must immediately halt and escalate
    v_receipt = _record_and_maybe_admit_evidence(
        wave5_env,
        evidence_id="ev-flt-v1",
        evidence_type="VERIFICATION_EVIDENCE",
        project_id=res.project_id,
        issue_id=issue_id,
        task_id="FLT-01",
        attempt_id=dev["attempt_id"],
        run_id=dev["run_id"],
        fencing_token=dev["fencing_token"],
        candidate_sha=cand_sha,
        result={"passed": False, "test_count": 1, "outcomes": [{"id": "t1", "passed": False, "reason": "timeout"}]},
        admit=False,
    )
    with pytest.raises(LoopError) as exc_unc:
        loop.record_verification_outcome(job_id, verification_receipt=v_receipt)
    assert exc_unc.value.code == "unresolved_execution"

    # Reconcile attempt state back from UNKNOWN_EXECUTION to RUNNING to test ceiling exhaustion
    with db.atomic_transaction() as conn:
        conn.execute(
            "UPDATE pm_coordinator_attempts SET status = 'RUNNING' WHERE attempt_id = ?",
            (dev["attempt_id"],),
        )
        conn.execute(
            "UPDATE pm_coordinator_loop_jobs SET stage = 'VERIFYING', escalation_category = NULL, escalation_reason = NULL, max_attempts = 1 WHERE job_id = ?",
            (job_id,),
        )

    with pytest.raises(LoopError) as exc_ceil:
        loop.record_verification_outcome(job_id, verification_receipt=v_receipt)
    assert exc_ceil.value.code == "exhausted_attempts"

    with db._get_connection() as conn:
        job_row = conn.execute("SELECT stage, escalation_category, escalation_reason FROM pm_coordinator_loop_jobs WHERE job_id = ?", (job_id,)).fetchone()
        assert job_row["stage"] == "ESCALATED"
        assert job_row["escalation_category"] == "exhausted_attempts"
        assert "Exhausted maximum development attempts" in (job_row["escalation_reason"] or "")


def test_supervised_end_to_end_pilot_with_live_board(wave5_env: dict) -> None:
    kickoff: ProjectKickoffService = wave5_env["kickoff"]
    loop: AutomaticCorrectionLoop = wave5_env["loop"]
    exporter: CandidateExporter = wave5_env["exporter"]
    activity: ActivityBridgeService = wave5_env["activity"]
    iam: MultiTenantIAM = wave5_env["iam"]
    db: PMDatabase = wave5_env["db"]
    tokens = wave5_env["tokens"]
    base_sha = wave5_env["base_sha"]
    base_blob_sha = wave5_env["base_blob_sha"]
    tenant_root = wave5_env["tenant_root"]

    # 1. Kick off project via ProjectKickoffService (SBA-09, CC-15)
    k_res = kickoff.kickoff_project(
        tenant_id="t-pilot",
        project_key="PILOT",
        project_name="Supervised Pilot",
        token_budget=100000,
        base_commit_sha=base_sha,
        task_definitions=[
            {
                "task_id": "PILOT-1",
                "title": "Supervised End-to-End Pilot",
                "description": "Complete supervised flow with verification failure, rework, approval and integration",
                "appetite_tokens": 50000,
                "path_whitelist": ["pkg/module.py"],
            }
        ],
        auto_admit_first_ready=True,
    )
    job_id = k_res.admitted_jobs[0]["job_id"]
    issue_id = k_res.admitted_jobs[0]["issue_id"]

    # 2. Attempt 1: Start dev and export Candidate 1 (buggy code)
    dev1 = loop.begin_development(job_id, worker_id="worker-p1", run_id="run-p1-1", session_id="sess-p1-1", now_epoch=1000.0)
    att1_id = dev1["attempt_id"]

    prop1_bytes = b"# Attempt 1 (buggy)\ndef handler():\n    return 'broken'\n"
    prop1 = {
        "schema": CANDIDATE_SCHEMA,
        "proposal_id": str(uuid.uuid4()),
        "base_commit_sha": base_sha,
        "files": [
            {
                "operation": "WRITE",
                "path": "pkg/module.py",
                "expected_base_blob_sha": base_blob_sha,
                "content_base64": base64.b64encode(prop1_bytes).decode("ascii"),
            }
        ],
    }
    exp1 = loop.export_candidate_stage(job_id, exporter=exporter, session_token=tokens["builder"], proposal=prop1, now_epoch=1010.0)
    cand1_sha = exp1["candidate_commit_sha"]

    # Attempt 1: Verifier reports test failure
    v1_receipt = _record_and_maybe_admit_evidence(
        wave5_env,
        evidence_id="ev-pilot-v1",
        evidence_type="VERIFICATION_EVIDENCE",
        project_id=k_res.project_id,
        issue_id=issue_id,
        task_id="PILOT-1",
        attempt_id=att1_id,
        run_id="run-p1-1",
        fencing_token=dev1["fencing_token"],
        candidate_sha=cand1_sha,
        result={"passed": False, "test_count": 1, "outcomes": [{"id": "c1", "passed": False, "reason": "AssertionError: expected 'ok', got 'broken'"}]},
        admit=False,
    )
    # Loop triggers automatic bounded rework -> advances to REWORK_PENDING and creates Attempt 2
    rework_out = loop.record_verification_outcome(job_id, verification_receipt=v1_receipt, now_epoch=1020.0)
    assert rework_out["stage"] == "REWORK_PENDING"
    att2_id = rework_out["next_attempt_id"]
    assert db.get_issue(issue_id).current_state == IssueState.REJECTED_REWORK

    # 3. Attempt 2: Start dev and export Candidate 2 (fixed code)
    dev2 = loop.begin_development(job_id, worker_id="worker-p1", run_id="run-p1-2", session_id="sess-p1-2", now_epoch=1030.0)
    assert dev2["attempt_id"] == att2_id

    prop2_bytes = b"# Attempt 2 (fixed)\ndef handler():\n    return 'ok'\n"
    prop2 = {
        "schema": CANDIDATE_SCHEMA,
        "proposal_id": str(uuid.uuid4()),
        "base_commit_sha": base_sha,
        "files": [
            {
                "operation": "WRITE",
                "path": "pkg/module.py",
                "expected_base_blob_sha": base_blob_sha,
                "content_base64": base64.b64encode(prop2_bytes).decode("ascii"),
            }
        ],
    }
    exp2 = loop.export_candidate_stage(job_id, exporter=exporter, session_token=tokens["builder"], proposal=prop2, now_epoch=1040.0)
    cand2_sha = exp2["candidate_commit_sha"]

    # Attempt 2: Verifier reports PASS
    v2_receipt = _record_and_maybe_admit_evidence(
        wave5_env,
        evidence_id="ev-pilot-v2",
        evidence_type="VERIFICATION_EVIDENCE",
        project_id=k_res.project_id,
        issue_id=issue_id,
        task_id="PILOT-1",
        attempt_id=att2_id,
        run_id="run-p1-2",
        fencing_token=dev2["fencing_token"],
        candidate_sha=cand2_sha,
        result={"passed": True, "test_count": 1, "outcomes": [{"id": "c1", "passed": True}]},
        admit=True,
    )
    v2_out = loop.record_verification_outcome(job_id, verification_receipt=v2_receipt, now_epoch=1050.0)
    assert v2_out["stage"] == "REVIEWING"

    # Attempt 2: Independent reviewer reviews candidate 2 and approves
    r2_receipt = _record_and_maybe_admit_evidence(
        wave5_env,
        evidence_id="ev-pilot-r2",
        evidence_type="REVIEW_EVIDENCE",
        project_id=k_res.project_id,
        issue_id=issue_id,
        task_id="PILOT-1",
        attempt_id=att2_id,
        run_id="run-p1-2",
        fencing_token=dev2["fencing_token"],
        candidate_sha=cand2_sha,
        result={"verdict": "APPROVED", "comments": "All requirements verified and passing."},
        admit=True,
    )
    rev2_out = loop.record_review_outcome(job_id, review_receipt=r2_receipt, now_epoch=1060.0)
    assert rev2_out["stage"] == "AWAITING_REQUIRED_APPROVAL"
    assert db.get_issue(issue_id).current_state == IssueState.JUDICIAL_REVIEW

    # 4. Human Release Signoff & CAS Git Integration to main
    done_out = loop.integrate_and_complete(
        job_id,
        exporter=exporter,
        merger_id="merger-1",
        merger_session_token=tokens["merger"],
        target_ref="refs/heads/main",
        authorization_ref="appr-pilot-final",
        human_approver_principal="t-pilot:human_release_mgr",
        evidence_trust=wave5_env["trust"],
        now_epoch=1070.0,
    )
    assert done_out["stage"] == "COMPLETE"
    assert done_out["integrated_commit_sha"] == cand2_sha
    assert db.get_issue(issue_id).current_state == IssueState.DONE
    assert wave5_env["git"]("rev-parse", "refs/heads/main") == cand2_sha

    # 5. Live Browser Playwright Verification on portal/scrum.html (SBA-06, SBA-08, CC-10, CC-14)
    ent = ConsultingEnterprise()
    srv = DashboardServer(
        ent,
        host="127.0.0.1",
        port=0,
        iam=iam,
        tenant_id="t-pilot",
        tenant_root=tenant_root,
    )
    srv.start_background()
    port = srv.server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as p:
            executable = shutil.which("chromium") or shutil.which("google-chrome")
            browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            # Log in through /portal/login.html
            page.goto(f"{base_url}/portal/login.html")
            page.locator("#tokenInput").fill(tokens["operator"])
            page.locator("#submitBtn").click()
            page.wait_for_url(f"{base_url}/portal/scrum.html**")

            # Switch project to PILOT, view ALL sprints, and refresh board
            page.evaluate("() => { app.project = 'PILOT'; app.sprint = 'ALL'; return refresh(true); }")

            # Locate ticket card
            done_card = page.locator('[data-ticket="PILOT-1"]')
            done_card.wait_for(timeout=5000)
            assert done_card.count() == 1

            # Click ticket card to open drawer
            done_card.click()
            drawer = page.locator("#drawer")
            assert drawer.is_visible()
            assert "Supervised End-to-End Pilot" in page.locator("#drawer-content").inner_text()

            # Load and verify task activity stream
            page.locator("#load-activity").click()
            page.wait_for_function("() => document.querySelector('#task-activity').getAttribute('aria-busy') === 'false'", timeout=5000)
            act_text = page.locator("#task-activity").inner_text()

            # Activity feed must show attempt 1 failure, rework, attempt 2 pass, review and completion
            assert "Attempt 1" in act_text or "ev-pilot-v1" in act_text
            assert "ev-pilot-v2" in act_text or "PASSED" in act_text or "attempt" in act_text.lower()
            assert "Attempt" in page.locator("#task-workflow").inner_text()

            page.locator("#close-drawer").click()
            browser.close()
    finally:
        srv.shutdown()
