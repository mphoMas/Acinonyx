"""Wave 2 Qualification Suite: P1 Provider Broker, P2 Candidate Exporter & CAS Integration, P3 Repo Verifier."""
from __future__ import annotations

import base64
import json
import secrets
import subprocess
import uuid
from pathlib import Path

import pytest

from mas.iam import MultiTenantIAM
from mas.pm.adapters.admission import EvidenceTrust, IssuerGrant
from mas.pm.adapters.broker import (
    BROKER_SCHEMA,
    BrokerChannelBinding,
    BrokerError,
    MediatedIPCChannel,
    PriceSchedule,
    ProviderBroker,
    ProviderTransport,
    ProviderTransportOutcome,
)
from mas.pm.adapters.exporter import (
    CANDIDATE_SCHEMA,
    CandidateExporter,
    CandidateIntegrationError,
)
from mas.pm.adapters.verifier import (
    CodexReviewerAdapter,
    RepositoryVerificationContract,
    VerifierAdapter,
    evidence_binding,
)
from mas.pm.coordinator import CoordinatorStore, trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.models import Issue, Project


class StubProviderTransport(ProviderTransport):
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.next_outcome: ProviderTransportOutcome | Exception = ProviderTransportOutcome(
            provider_call_id="call-001",
            chunks=('{"schema":"mas-review-v1"}',),
            input_tokens=20,
            output_tokens=15,
            status="SUCCEEDED",
        )
        self.reconcile_outcome: ProviderTransportOutcome | None = None

    def send(
        self,
        *,
        request_id: str,
        provider_id: str,
        model_id: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_output_tokens: int,
        timeout_s: float,
    ) -> ProviderTransportOutcome:
        self.calls.append({
            "request_id": request_id,
            "provider_id": provider_id,
            "model_id": model_id,
            "system_prompt": system_prompt,
            "messages": messages,
            "max_output_tokens": max_output_tokens,
            "timeout_s": timeout_s,
        })
        if isinstance(self.next_outcome, Exception):
            raise self.next_outcome
        return self.next_outcome

    def reconcile(self, *, request_id: str, provider_id: str, model_id: str) -> ProviderTransportOutcome | None:
        return self.reconcile_outcome


@pytest.fixture
def wave2_env(tmp_path: Path):
    # Initialize git repo
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
    (repo_path / "pkg" / "helper.py").write_text("def offset(x):\n    return x + 10\n")
    (repo_path / "pkg" / "main.py").write_text(
        "from pkg.helper import offset\ndef solve(payload):\n    return offset(payload)\n"
    )
    (repo_path / "oracle.py").write_text("# owner oracle\n")
    git("add", ".")
    git("commit", "-m", "initial base")
    base_sha = git("rev-parse", "HEAD")

    # Initialize DB, IAM, and CoordinatorStore
    db = PMDatabase(tmp_path / "pm.db")
    db.create_project(Project(id="proj-1", key="SBA", name="SBA Project", token_budget=100000))
    db.create_issue(
        Issue(
            id="iss-1",
            project_id="proj-1",
            key="SBA-1",
            title="Wave 2 Task",
            appetite_tokens=5000,
            path_whitelist=["pkg/helper.py", "pkg/main.py", "pkg/new_mod.py"],
            forbidden_paths=["pkg/secret.py"],
        )
    )
    with db.atomic_transaction() as c:
        c.execute(
            """
            INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
            VALUES ('proj-1', 'SBA-05', 'task-1', 'iss-1', 'SBA-1')
            """
        )

    iam = MultiTenantIAM(secrets.token_hex(32), db_path=tmp_path / "iam.db")
    iam.create_tenant("tenant-1", "Tenant 1")
    iam.register_principal(
        "tenant-1",
        "builder-1",
        scopes={"coordinator:broker:invoke", "coordinator:candidate:export"},
    )
    iam.register_principal(
        "tenant-1",
        "verifier-1",
        scopes={"coordinator:evidence:verify"},
    )
    iam.register_principal(
        "tenant-1",
        "reviewer-1",
        scopes={"coordinator:evidence:review", "coordinator:broker:invoke"},
    )
    iam.register_principal(
        "tenant-1",
        "merger-1",
        scopes={"coordinator:candidate:integrate"},
    )

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
    with trusted_coordinator_admin_scope():
        store.create_attempt_with_intent(
            "att-1",
            "int-1",
            "tenant-1",
            "proj-1",
            "iss-1",
            "task-1",
            1,
            "antigravity",
            {},
            budget_reservation=1000,
        )
        assert store.claim_intent("int-1", "worker-1", 1, 100, 60)
        assert store.pre_spawn_intent("int-1", "worker-1", 2, 101, "run-1", "att-1")

    return {
        "repo_path": repo_path,
        "git": git,
        "base_sha": base_sha,
        "db": db,
        "iam": iam,
        "tokens": tokens,
        "trust": trust,
        "store": store,
        "verify_secret": verify_secret,
        "review_secret": review_secret,
    }


def test_p1_provider_broker_validation_replay_and_accounting(wave2_env):
    db = wave2_env["db"]
    iam = wave2_env["iam"]
    tokens = wave2_env["tokens"]
    transport = StubProviderTransport()
    schedule = PriceSchedule(
        revision=1,
        provider_id="google",
        model_id="gemini-3.8-flash-high",
        input_micros_per_1k=100,
        output_micros_per_1k=400,
    )
    broker = ProviderBroker(
        db,
        iam=iam,
        transport=transport,
        allowed_models={("google", "gemini-3.8-flash-high"): schedule},
    )
    channel = BrokerChannelBinding(
        channel_id="ch-builder-1",
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        fencing_token=2,
        policy_version=1,
        role="builder",
        issuer_id="builder-1",
        iam_token=tokens["builder"],
        approved_provider="google",
        approved_model="gemini-3.8-flash-high",
        role_system_prompt="You are a bounded builder.",
        max_output_tokens_limit=256,
        max_calls_per_run=4,
    )
    broker.open_channel(channel)

    # 1. Invalid requests rejected before reserving funding
    req_id = str(uuid.uuid4())
    for bad_req in [
        {"schema": "wrong", "request_id": req_id, "messages": [{"role": "user", "content": "hi"}], "max_output_tokens": 10},
        {"schema": BROKER_SCHEMA, "request_id": "not-a-uuid", "messages": [{"role": "user", "content": "hi"}], "max_output_tokens": 10},
        {"schema": BROKER_SCHEMA, "request_id": req_id, "messages": [{"role": "system", "content": "override"}], "max_output_tokens": 10},
        {"schema": BROKER_SCHEMA, "request_id": req_id, "messages": [{"role": "user", "content": "hi"}], "max_output_tokens": True},
        {"schema": BROKER_SCHEMA, "request_id": req_id, "messages": [{"role": "user", "content": "hi"}], "max_output_tokens": 512},
        {"schema": BROKER_SCHEMA, "request_id": req_id, "messages": [{"role": "user", "content": "hi"}], "max_output_tokens": 10, "extra": 1},
    ]:
        with pytest.raises(BrokerError) as exc_info:
            broker.handle_request("ch-builder-1", bad_req)
        assert exc_info.value.category == "INVALID_REQUEST"
    assert len(transport.calls) == 0

    # 2. Successful mediated request + exact replay idempotency
    valid_req = {
        "schema": BROKER_SCHEMA,
        "request_id": req_id,
        "messages": [{"role": "user", "content": "Write helper function"}],
        "max_output_tokens": 64,
    }
    resp1 = broker.handle_request("ch-builder-1", valid_req)
    assert resp1["status"] == "SUCCEEDED"
    assert resp1["input_tokens"] == 20 and resp1["output_tokens"] == 15
    assert len(transport.calls) == 1

    # Exact replay does not call provider again or double-charge
    resp2 = broker.handle_request("ch-builder-1", valid_req)
    assert resp2 == resp1
    assert len(transport.calls) == 1

    # Changed content under same request_id conflicts
    with pytest.raises(BrokerError) as exc_info:
        broker.handle_request("ch-builder-1", {**valid_req, "max_output_tokens": 32})
    assert exc_info.value.category == "INVALID_REQUEST"

    # IPC line channel wrapper
    ipc = MediatedIPCChannel(broker, "ch-builder-1")
    ipc_out = json.loads(ipc.process_line(json.dumps(valid_req)).decode("utf-8"))
    assert ipc_out["receipt_id"] == resp1["receipt_id"]


def test_p1_provider_broker_overspend_and_revocation_holds_liability(wave2_env):
    db = wave2_env["db"]
    iam = wave2_env["iam"]
    tokens = wave2_env["tokens"]
    transport = StubProviderTransport()
    # Provider reports usage (400 + 400 = 800) exceeding the request sub-reservation ceiling
    transport.next_outcome = ProviderTransportOutcome(
        provider_call_id="call-overspend",
        chunks=("large usage",),
        input_tokens=400,
        output_tokens=400,
        status="SUCCEEDED",
    )
    schedule = PriceSchedule(1, "google", "gemini-3.8-flash-high", 100, 400)
    broker = ProviderBroker(
        db,
        iam=iam,
        transport=transport,
        allowed_models={("google", "gemini-3.8-flash-high"): schedule},
    )
    channel = BrokerChannelBinding(
        channel_id="ch-overspend",
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        fencing_token=2,
        policy_version=1,
        role="builder",
        issuer_id="builder-1",
        iam_token=tokens["builder"],
        approved_provider="google",
        approved_model="gemini-3.8-flash-high",
        role_system_prompt="System prompt",
        max_output_tokens_limit=128,
    )
    broker.open_channel(channel)

    req = {
        "schema": BROKER_SCHEMA,
        "request_id": str(uuid.uuid4()),
        "messages": [{"role": "user", "content": "Hello"}],
        "max_output_tokens": 32,
    }
    with pytest.raises(BrokerError) as exc_info:
        broker.handle_request("ch-overspend", req)
    assert exc_info.value.category == "BUDGET_EXHAUSTED"

    # Verify real usage was recorded without clamping and escalation was emitted
    with db._get_connection() as c:
        row = c.execute(
            "SELECT status, input_tokens, output_tokens FROM pm_coordinator_broker_requests WHERE request_id = ?",
            (req["request_id"],),
        ).fetchone()
        assert row["status"] == "UNKNOWN_PROVIDER_EXECUTION"
        assert row["input_tokens"] == 400 and row["output_tokens"] == 400
        esc = c.execute("SELECT * FROM pm_coordinator_escalations WHERE issue_id = 'iss-1'").fetchone()
        assert esc is not None and esc["held_liabilities"] == 800

    # Further calls on halted channel are blocked immediately
    with pytest.raises(BrokerError) as exc_info:
        broker.handle_request("ch-overspend", {**req, "request_id": str(uuid.uuid4())})
    assert exc_info.value.category == "BUDGET_EXHAUSTED"


def test_p2_p3_export_repo_verify_review_and_cas_integration(wave2_env, coordinator_test_image):
    repo_path = wave2_env["repo_path"]
    git = wave2_env["git"]
    base_sha = wave2_env["base_sha"]
    db = wave2_env["db"]
    iam = wave2_env["iam"]
    tokens = wave2_env["tokens"]
    trust = wave2_env["trust"]
    store = wave2_env["store"]
    verify_secret = wave2_env["verify_secret"]
    review_secret = wave2_env["review_secret"]

    exporter = CandidateExporter(
        db=db,
        repo_root=repo_path,
        repo_identity="mphoMas/Acinonyx",
        iam=iam,
    )

    # Make the operator working tree dirty to prove export never touches or resets it!
    (repo_path / "pkg" / "helper.py").write_text("# dirty operator edit in checkout\n")
    base_helper_blob = git("rev-parse", f"{base_sha}:pkg/helper.py")

    # 1. Reject forbidden paths, frontend paths, oracle paths, and base blob mismatch
    for bad_file, expected_code in [
        ({"path": "../escape.py", "operation": "WRITE", "expected_base_blob_sha": None, "content_base64": ""}, "INVALID_PATH"),
        ({"path": ".git/config", "operation": "WRITE", "expected_base_blob_sha": None, "content_base64": ""}, "FORBIDDEN_PATH"),
        ({"path": "portal/scrum.html", "operation": "WRITE", "expected_base_blob_sha": None, "content_base64": ""}, "SCOPE_VIOLATION"),
        ({"path": "oracle.py", "operation": "WRITE", "expected_base_blob_sha": None, "content_base64": ""}, "ORACLE_PROTECTED"),
        ({"path": "pkg/helper.py", "operation": "WRITE", "expected_base_blob_sha": "0" * 40, "content_base64": ""}, "BASE_BLOB_CONFLICT"),
        ({"path": "PKG/HELPER.PY", "operation": "WRITE", "expected_base_blob_sha": None, "content_base64": ""}, "SCOPE_VIOLATION"),
    ]:
        with pytest.raises(CandidateIntegrationError) as exc_info:
            exporter.export_candidate(
                tenant_id="tenant-1",
                project_id="proj-1",
                issue_id="iss-1",
                task_id="task-1",
                attempt_id="att-1",
                run_id="run-1",
                fencing_token=2,
                builder_id="builder-1",
                iam_token=tokens["builder"],
                oracle_paths={"oracle.py"},
                proposal={
                    "schema": CANDIDATE_SCHEMA,
                    "proposal_id": str(uuid.uuid4()),
                    "base_commit_sha": base_sha,
                    "files": [bad_file],
                },
            )
        assert exc_info.value.code == expected_code

    # 2. Export valid multi-file candidate
    new_helper_code = b"def offset(x):\n    return x * 2 + 5\n"
    proposal_id = str(uuid.uuid4())
    valid_proposal = {
        "schema": CANDIDATE_SCHEMA,
        "proposal_id": proposal_id,
        "base_commit_sha": base_sha,
        "files": [
            {
                "path": "pkg/helper.py",
                "operation": "WRITE",
                "expected_base_blob_sha": base_helper_blob,
                "content_base64": base64.b64encode(new_helper_code).decode("ascii"),
            }
        ],
    }
    export_receipt = exporter.export_candidate(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        fencing_token=2,
        builder_id="builder-1",
        iam_token=tokens["builder"],
        oracle_paths={"oracle.py"},
        proposal=valid_proposal,
    )
    cand_sha = export_receipt["candidate_commit_sha"]
    assert cand_sha != base_sha
    # Dirty checkout was preserved untouched!
    assert (repo_path / "pkg" / "helper.py").read_text() == "# dirty operator edit in checkout\n"
    assert git("rev-parse", "HEAD") == base_sha

    # Exact replay returns identical receipt
    replay_receipt = exporter.export_candidate(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        fencing_token=2,
        builder_id="builder-1",
        iam_token=tokens["builder"],
        oracle_paths={"oracle.py"},
        proposal=valid_proposal,
    )
    assert replay_receipt == export_receipt

    # Complete coordinator execution intent with candidate SHA
    with trusted_coordinator_admin_scope():
        assert store.complete_intent("int-1", "worker-1", 2, 105, cand_sha, 35, 0)

    # 3. Verify multi-file repository candidate using RepositoryVerificationContract (P3) in real Docker!
    repo_contract = RepositoryVerificationContract(
        source_paths=("pkg/helper.py", "pkg/main.py"),
        entrypoint_path="pkg/main.py",
        cases_json=json.dumps([
            {"id": "case_3", "input": 3, "expected": 11},
            {"id": "case_10", "input": 10, "expected": 25},
        ]),
        worker_image=coordinator_test_image,
    )
    binding = evidence_binding(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        candidate_commit_sha=cand_sha,
        base_commit_sha=base_sha,
        policy_version=1,
        fencing_token=2,
        suite_digest=repo_contract.suite_digest,
        worker_image=coordinator_test_image,
        developer_principal_id="builder-1",
    )
    with trusted_coordinator_admin_scope():
        store.register_evidence_contract(binding, "verifier-1", "reviewer-1", ["case_3", "case_10"])

    verifier = VerifierAdapter(
        "verifier-1",
        "verify-key",
        verify_secret,
        repo_root=repo_path,
        contract=repo_contract,
    )
    ver_env = verifier.verify_candidate(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        candidate_commit_sha=cand_sha,
        base_commit_sha=base_sha,
        developer_principal_id="builder-1",
        policy_version=1,
        fencing_token=2,
    )
    assert ver_env["canonical_payload"]["result"]["passed"] is True
    with trusted_coordinator_admin_scope():
        store.record_evidence_receipt(**ver_env)
        assert store.admit_evidence_receipt(ver_env["evidence_id"])

    # 4. Mediated review via ProviderBroker (P1 + P3)
    transport = StubProviderTransport()
    review_json = json.dumps({
        "schema": "mas-review-v1",
        "binding": binding,
        "verdict": "APPROVED",
        "comments": "Multi-file candidate verified and clean.",
    })
    transport.next_outcome = ProviderTransportOutcome(
        provider_call_id="call-rev-1",
        chunks=(review_json,),
        input_tokens=40,
        output_tokens=25,
        status="SUCCEEDED",
    )
    schedule = PriceSchedule(1, "openai", "codex-reviewer-v1", 100, 300)
    broker = ProviderBroker(
        db,
        iam=iam,
        transport=transport,
        allowed_models={("openai", "codex-reviewer-v1"): schedule},
    )
    rev_channel = BrokerChannelBinding(
        channel_id="ch-reviewer-1",
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        fencing_token=2,
        policy_version=1,
        role="reviewer",
        issuer_id="reviewer-1",
        iam_token=tokens["reviewer"],
        approved_provider="openai",
        approved_model="codex-reviewer-v1",
        role_system_prompt="You are an independent code reviewer.",
        max_output_tokens_limit=1024,
    )
    broker.open_channel(rev_channel)

    reviewer = CodexReviewerAdapter(
        "reviewer-1",
        "review-key",
        review_secret,
        image=coordinator_test_image,
        repo_root=repo_path,
        broker_channel=(broker, "ch-reviewer-1"),
    )
    rev_env = reviewer.review_candidate(binding=binding)
    with trusted_coordinator_admin_scope():
        store.record_evidence_receipt(**rev_env)
        assert store.admit_evidence_receipt(rev_env["evidence_id"])

    # 5. Compare-and-swap Git integration (P2):
    # Builder self-merge is blocked
    with pytest.raises(CandidateIntegrationError) as exc_info:
        exporter.integrate_candidate(
            integration_id="intg-bad",
            tenant_id="tenant-1",
            project_id="proj-1",
            issue_id="iss-1",
            task_id="task-1",
            attempt_id="att-1",
            run_id="run-1",
            fencing_token=2,
            policy_version=1,
            merger_id="builder-1",
            authorization_ref="ceo-approval-001",
            target_ref="refs/heads/main",
            expected_target_sha=base_sha,
            candidate_commit_sha=cand_sha,
            iam_token=tokens["builder"],
            evidence_trust=trust,
        )
    assert exc_info.value.code == "AUTHORITY_DENIED"

    # Authorized merger integrates candidate via CAS
    intg_res = exporter.integrate_candidate(
        integration_id="intg-1",
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        fencing_token=2,
        policy_version=1,
        merger_id="merger-1",
        authorization_ref="ceo-approval-001",
        target_ref="refs/heads/main",
        expected_target_sha=base_sha,
        candidate_commit_sha=cand_sha,
        iam_token=tokens["merger"],
        evidence_trust=trust,
    )
    assert intg_res["status"] == "CONFIRMED"
    assert git("rev-parse", "refs/heads/main") == cand_sha


def test_p1_broker_output_limit_duplicate_sending_and_stale_fence(wave2_env):
    db = wave2_env["db"]
    iam = wave2_env["iam"]
    tokens = wave2_env["tokens"]
    transport = StubProviderTransport()
    schedule = PriceSchedule(1, "google", "gemini-3.8-flash-high", 100, 400)
    broker = ProviderBroker(
        db,
        iam=iam,
        transport=transport,
        allowed_models={("google", "gemini-3.8-flash-high"): schedule},
    )
    channel = BrokerChannelBinding(
        channel_id="ch-adv",
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        fencing_token=2,
        policy_version=1,
        role="builder",
        issuer_id="builder-1",
        iam_token=tokens["builder"],
        approved_provider="google",
        approved_model="gemini-3.8-flash-high",
        role_system_prompt="System prompt",
        max_output_tokens_limit=128,
    )
    broker.open_channel(channel)

    # 1. Output stream exceeding 16 KiB raises OUTPUT_LIMIT
    transport.next_outcome = ProviderTransportOutcome(
        provider_call_id="call-big",
        chunks=("A" * 9000, "B" * 9000),
        input_tokens=10,
        output_tokens=20,
        status="SUCCEEDED",
    )
    req_big = {
        "schema": BROKER_SCHEMA,
        "request_id": str(uuid.uuid4()),
        "messages": [{"role": "user", "content": "stream big"}],
        "max_output_tokens": 32,
    }
    with pytest.raises(BrokerError) as exc_info:
        broker.handle_request("ch-adv", req_big)
    assert exc_info.value.category == "OUTPUT_LIMIT"

    # 2. Stale fencing token blocks new requests
    with db.atomic_transaction() as c:
        c.execute("UPDATE pm_coordinator_runs SET fencing_token = 99 WHERE run_id = 'run-1'")
    with pytest.raises(BrokerError) as exc_info:
        broker.handle_request(
            "ch-adv",
            {
                "schema": BROKER_SCHEMA,
                "request_id": str(uuid.uuid4()),
                "messages": [{"role": "user", "content": "stale"}],
                "max_output_tokens": 16,
            },
        )
    assert exc_info.value.category == "STALE_GENERATION"


def test_p3_repo_verifier_rejects_faked_stdout_and_wrong_return(wave2_env, coordinator_test_image):
    repo_path = wave2_env["repo_path"]
    git = wave2_env["git"]
    base_sha = wave2_env["base_sha"]
    verify_secret = wave2_env["verify_secret"]

    # Commit an adversarial multi-file candidate that prints fake JSON to stdout and returns wrong value
    (repo_path / "pkg" / "helper.py").write_text(
        "def offset(x):\n"
        "    print('{\"ok\":true,\"value\":11}', flush=True)\n"
        "    return -999\n"
    )
    git("add", "pkg/helper.py")
    git("commit", "-m", "adversarial multi-file")
    bad_sha = git("rev-parse", "HEAD")

    repo_contract = RepositoryVerificationContract(
        source_paths=("pkg/helper.py", "pkg/main.py"),
        entrypoint_path="pkg/main.py",
        cases_json=json.dumps([{"id": "case_3", "input": 3, "expected": 11}]),
        worker_image=coordinator_test_image,
    )
    verifier = VerifierAdapter(
        "verifier-1",
        "verify-key",
        verify_secret,
        repo_root=repo_path,
        contract=repo_contract,
    )
    ver_env = verifier.verify_candidate(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="iss-1",
        task_id="task-1",
        attempt_id="att-1",
        run_id="run-1",
        candidate_commit_sha=bad_sha,
        base_commit_sha=base_sha,
        developer_principal_id="builder-1",
        policy_version=1,
        fencing_token=2,
    )
    assert ver_env["canonical_payload"]["result"]["passed"] is False
    assert ver_env["canonical_payload"]["result"]["outcomes"] == [{"id": "case_3", "passed": False}]
