"""Process enforcement with private fixtures; signed receipts are fixture data,
not claims that live provider/browser work executed. Existing runtime suites
qualify execution independently.
"""

import secrets
import sqlite3
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from mas.iam import MultiTenantIAM
from mas.pm.adapters.admission import EvidenceTrust, IssuerGrant
from mas.pm.adapters.verifier import evidence_binding, signed_envelope
from mas.pm.coordinator import trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.delivery import DeliveryBrief, DeliveryGateError, DeliveryService, delivery_admin_actor
from mas.pm.models import Issue, Project
from mas.pm.worker import CoordinatorAdmissionEngine
from mas.tenancy import tenant_scope


@contextmanager
def actor(name):
    with trusted_coordinator_admin_scope(), delivery_admin_actor(name):
        yield


def brief():
    return {
        "base_sha": "b" * 40,
        "suite_digest": "d" * 64,
        "policy_version": 1,
        "coordinator": "coordinator",
        "builder": "builder",
        "verifier": "verifier",
        "reviewer": "reviewer",
        "scope": ["mas/"],
        "critical": True,
        "mechanism": "Qualified synthetic boundary; current policy checked atomically",
        "requirements": [{"id": "R1", "rule": "No unsupported completion evidence"}],
        "checks": [
            {"id": "positive", "requirement_id": "R1", "command": "trusted check", "expected": "passes", "negative": False},
            {
                "id": "negative",
                "requirement_id": "R1",
                "command": "trusted adverse check",
                "expected": "rejects forged data",
                "negative": True,
            },
        ],
    }


@pytest.fixture
def env(tmp_path):
    db = PMDatabase(tmp_path / "pm.db")
    db.create_project(Project(id="p", key="G", name="Gate Project", token_budget=10000))
    db.create_issue(Issue(id="i", project_id="p", key="G-1", title="Task", appetite_tokens=1000, path_whitelist=["mas/"]))
    with db.atomic_transaction() as c:
        c.execute(
            "INSERT INTO pm_task_mappings(project_id,planning_reference,task_id,local_issue_id,local_issue_key) VALUES('p','G-1','task','i','G-1')"
        )
    service = DeliveryService(db)
    with actor("coordinator"):
        service.enroll("p", "default")
        service.establish("i", brief())
    return db, service


def state(service):
    with actor("coordinator"):
        return service.get("i")


def ready(service):
    with actor("reviewer"):
        service.agree("i", state(service)["revision"], role="reviewer", rationale="Mechanism reviewed")
    with actor("builder"):
        service.agree("i", state(service)["revision"], role="builder", rationale="Checks and scope understood")


def execute(db, service, suffix="1"):
    with trusted_coordinator_admin_scope():
        intent = CoordinatorAdmissionEngine(db).admit_task(
            "i", budget_reservation=100, attempt_id="a" + suffix, intent_id="intent" + suffix
        )
        assert db.coordinator.claim_intent(intent.intent_id, "worker", 1, 100, 30)
        assert db.coordinator.pre_spawn_intent(intent.intent_id, "worker", 2, 101, "run" + suffix)
        assert db.coordinator.complete_intent(intent.intent_id, "worker", 2, 102, "a" * 40, 1, 0)
    assert state(service)["phase"] == "AWAITING_SUBMISSION"
    return "run" + suffix


def submit(service, run="run1", closures=None, observations=None):
    data = {
        "run_id": run,
        "candidate_sha": "a" * 40,
        "limitations": "Private fixture; no live provider",
        "closures": closures or {},
        "observations": observations
        if observations is not None
        else [{"check_id": x, "outcome": "PASSED", "evidence_ref": "fixture://" + x, "digest": "c" * 64} for x in ["positive", "negative"]],
    }
    with actor("builder"):
        return service.submit("i", state(service)["revision"], data)


def finding(identity="F1", requirement="R1"):
    return {
        "id": identity,
        "requirement_id": requirement,
        "reproduction": "Adverse probe reproduced the existing invariant violation",
        "impact": "Unsupported completion can escape",
        "closure_paths": ["mas/pm/coordinator.py", "mas/pm/adapters/admission.py"],
    }


def reject(service, f=None):
    with actor("reviewer"):
        return service.reject("i", state(service)["revision"], [f or finding()])


@pytest.mark.parametrize("path", ["engine", "attempt", "intent", "combined"])
def test_missing_agreement_blocks_every_admission_path(env, path):
    db, service = env
    with trusted_coordinator_admin_scope(), pytest.raises(DeliveryGateError, match="Agreed"):
        if path == "engine":
            CoordinatorAdmissionEngine(db).admit_task("i", budget_reservation=10)
        elif path == "attempt":
            db.coordinator.create_attempt("a", "default", "p", "i", "task", 1)
        elif path == "intent":
            db.coordinator.create_intent("i1", "default", "p", "i", "task", "unknown", "synthetic", {})
        else:
            db.coordinator.create_attempt_with_intent("a", "i1", "default", "p", "i", "task", 1, "synthetic", {}, 10)
    with db.atomic_transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM pm_coordinator_intents").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM pm_coordinator_reservations").fetchone()[0] == 0
    assert state(service)["phase"] == "DRAFT"


def test_enrollment_requires_existing_execution_resolved(tmp_path):
    db = PMDatabase(tmp_path / "p.db")
    db.create_project(Project(id="p", key="P", name="P"))
    db.create_issue(Issue(id="i", project_id="p", key="P-1", title="Task", appetite_tokens=100))
    with db.atomic_transaction() as c:
        c.execute(
            "INSERT INTO pm_task_mappings(project_id,planning_reference,task_id,local_issue_id,local_issue_key) VALUES('p','P-1','task','i','P-1')"
        )
    with actor("coordinator"):
        db.coordinator.create_attempt_with_intent("a", "intent", "default", "p", "i", "task", 1, "synthetic", {}, 10)
        with pytest.raises(DeliveryGateError, match="Resolve existing"):
            DeliveryService(db).enroll("p", "default")


def test_role_separation_and_stale_agreement(env):
    _, s = env
    with actor("builder"), pytest.raises(PermissionError, match="assigned reviewer"):
        s.agree("i", 1, role="reviewer", rationale="Self approval")
    with actor("reviewer"):
        s.agree("i", 1, role="reviewer", rationale="Checked")
        with pytest.raises(DeliveryGateError, match="Stale"):
            s.agree("i", 1, role="reviewer", rationale="Duplicate")
    invalid = brief()
    invalid["reviewer"] = "builder"
    with pytest.raises(ValidationError, match="distinct"):
        DeliveryBrief.model_validate(invalid)


def test_readiness_returns_persist_and_cannot_be_formal_rejected(env):
    db, s = env
    ready(s)
    execute(db, s)
    assert submit(s, observations=[])["phase"] == "READINESS_RETURNED"
    with actor("reviewer"), pytest.raises(DeliveryGateError, match="Only readiness"):
        s.reject("i", state(s)["revision"], [finding()])
    reopened = DeliveryService(PMDatabase(db.db_path))
    assert state(reopened)["phase"] == "READINESS_RETURNED"
    assert submit(reopened)["phase"] == "IN_REVIEW"
    with actor("coordinator"):
        events = s.events("i")
    assert [e["kind"] for e in events].count("READINESS_RETURNED") == 1
    assert [e["kind"] for e in events].count("IN_REVIEW") == 1


def test_recursive_requirement_failure_pauses_even_with_new_finding_id(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    reject(s)
    with actor("coordinator"):
        s.resume("i", state(s)["revision"], design_plan="Inspect every receipt admission entry point")
    execute(db, s, "2")
    submit(s, "run2", {"F1": ["mas/pm/coordinator.py", "mas/pm/adapters/admission.py"]})
    assert reject(s, finding("F2"))["phase"] == "RECURRENCE_PAUSED"
    reopened = PMDatabase(db.db_path)
    assert state(DeliveryService(reopened))["phase"] == "RECURRENCE_PAUSED"
    with trusted_coordinator_admin_scope(), pytest.raises(DeliveryGateError):
        CoordinatorAdmissionEngine(reopened).admit_task("i", budget_reservation=10)
    with actor("builder"), pytest.raises(PermissionError):
        s.resume("i", state(s)["revision"], design_plan="Skip review")
    with actor("coordinator"):
        s.resume("i", state(s)["revision"], design_plan="Rebuild authority boundary; reviewer checks original and related paths")
    assert state(s)["phase"] == "READY"


def test_incomplete_related_paths_return_before_review(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    reject(s)
    with actor("coordinator"):
        s.resume("i", state(s)["revision"], design_plan="Full boundary repair")
    execute(db, s, "2")
    assert submit(s, "run2", {"F1": ["mas/pm/coordinator.py"]})["phase"] == "READINESS_RETURNED"


def test_challenge_is_recorded_and_does_not_accept(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    reject(s)
    with actor("builder"):
        s.challenge("i", state(s)["revision"], "F1", "Requirement applies to another supported profile; here is the contract")
    with trusted_coordinator_admin_scope(), pytest.raises(DeliveryGateError):
        CoordinatorAdmissionEngine(db).admit_task("i", budget_reservation=10)
    with actor("coordinator"):
        s.resolve_challenge("i", state(s)["revision"], "F1", upheld=False, reason="Reviewer scope mistake; evidence preserved")
    assert state(s)["phase"] == "CHANGES_REQUESTED"
    with actor("coordinator"):
        assert any(e["kind"] == "REJECTED" for e in s.events("i"))
        assert any(e["kind"] == "CHALLENGE_RESOLVED" for e in s.events("i"))


def test_new_requirement_cannot_be_disguised_as_original_rejection(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    with actor("reviewer"), pytest.raises(DeliveryGateError, match="scope change"):
        s.reject("i", state(s)["revision"], [finding(requirement="NEW")])
    assert state(s)["phase"] == "IN_REVIEW"


def test_stale_policy_blocks_launch_before_effect(env):
    db, s = env
    ready(s)
    with trusted_coordinator_admin_scope():
        i = CoordinatorAdmissionEngine(db).admit_task("i", budget_reservation=10)
        assert db.coordinator.claim_intent(i.intent_id, "worker", 1, 100, 30)
        with db.atomic_transaction() as c:
            c.execute("UPDATE pm_issues SET policy_version=2 WHERE id=?", ("i",))
        with pytest.raises(DeliveryGateError, match="Stale"):
            db.coordinator.pre_spawn_intent(i.intent_id, "worker", 2, 101, "run")
    with db.atomic_transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM pm_coordinator_runs").fetchone()[0] == 0
        assert c.execute("SELECT status FROM pm_coordinator_reservations").fetchone()[0] == "HELD"


@pytest.mark.parametrize("mutate", [lambda x: x.update(candidate_sha="f" * 40), lambda x: x.update(run_id="missing")])
def test_submission_cannot_name_unexecuted_candidate(env, mutate):
    db, s = env
    ready(s)
    execute(db, s)
    data = {"run_id": "run1", "candidate_sha": "a" * 40, "observations": [], "limitations": ""}
    mutate(data)
    with actor("builder"), pytest.raises(DeliveryGateError, match="bound"):
        s.submit("i", state(s)["revision"], data)


def test_uncertain_execution_cannot_resume_or_release_funding(env):
    db, s = env
    ready(s)
    with trusted_coordinator_admin_scope():
        i = CoordinatorAdmissionEngine(db).admit_task("i", budget_reservation=10)
        db.coordinator.claim_intent(i.intent_id, "worker", 1, 100, 30)
        db.coordinator.pre_spawn_intent(i.intent_id, "worker", 2, 101, "run1")
        db.coordinator.record_execution_interrupted(i.intent_id, "worker", 2)
    assert state(s)["phase"] == "UNCERTAIN"
    with actor("coordinator"), pytest.raises(DeliveryGateError, match="terminal"):
        s.reconcile_execution("i", state(s)["revision"], reason="Assume stop")
    with db.atomic_transaction() as c:
        assert c.execute("SELECT status FROM pm_coordinator_reservations").fetchone()[0] == "HELD"


def test_append_only_evidence_and_history_preserved_on_reopen(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    with db.atomic_transaction() as c:
        before = c.execute("SELECT version,checksum FROM pm_schema_migrations WHERE version<2026101301").fetchall()
    for table in ["pm_delivery_events", "pm_delivery_submissions"]:
        for action in ["UPDATE " + table + " SET id=id", "DELETE FROM " + table]:
            with pytest.raises(sqlite3.IntegrityError, match="immutable"), db.atomic_transaction() as c:
                c.execute(action)
    PMDatabase(db.db_path)
    with db.atomic_transaction() as c:
        assert [tuple(x) for x in before] == [
            tuple(x) for x in c.execute("SELECT version,checksum FROM pm_schema_migrations WHERE version<2026101301")
        ]


def test_concurrent_agreement_has_one_cas_winner(env):
    db, s = env

    def agree():
        with actor("reviewer"):
            try:
                DeliveryService(PMDatabase(db.db_path)).agree("i", 1, role="reviewer", rationale="Checked design")
                return True
            except DeliveryGateError:
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: agree(), range(2))) == [False, True]


def test_done_and_missing_trust_cannot_bypass_review(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    with actor("reviewer"), pytest.raises(PermissionError, match="Trusted"):
        s.accept("i", state(s)["revision"], verification_id="fake", review_id="fake2")
    with pytest.raises(DeliveryGateError, match="acceptance"):
        db.update_issue_state("i", "DONE", "fixture")


def test_live_tenant_authority_revocation_wrong_role_and_unbound(tmp_path):
    secret = secrets.token_hex(32)
    iam = MultiTenantIAM(secret, db_path=tmp_path / "iam.db")
    iam.create_tenant("t", "Tenant")
    iam.register_principal("t", "coordinator", scopes={"storage:*", "delivery:*"})
    token = iam.issue_token("t", "coordinator")
    root = tmp_path / "tenants"
    with tenant_scope(iam, token, "t", root):
        db = PMDatabase()
        db.create_project(Project(id="p", key="P", name="P"))
        db.create_issue(Issue(id="i", project_id="p", key="P-1", title="Task", path_whitelist=["mas/"]))
        s = DeliveryService(db)
        s.enroll("p", "t")
        s.establish("i", brief())
        with pytest.raises(PermissionError, match="assigned reviewer"):
            s.agree("i", 1, role="reviewer", rationale="Impersonate")
    with pytest.raises(PermissionError):
        s.get("i")
    iam.revoke_session(token, iam.verify_token(token).token_id)
    with pytest.raises(PermissionError):
        with tenant_scope(iam, token, "t", root):
            s.get("i")


@pytest.mark.parametrize("case", ["valid", "different_suite", "revoked_reviewer"])
def test_acceptance_requires_current_independent_signed_receipts(env, tmp_path, case):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    iam = MultiTenantIAM(secrets.token_hex(32))
    iam.create_tenant("default", "Tenant")
    grants = {}
    tokens = {}
    for principal, role, action in [("verifier", "VERIFICATION_EVIDENCE", "verify"), ("reviewer", "REVIEW_EVIDENCE", "review")]:
        iam.register_principal("default", principal, scopes={"coordinator:evidence:" + action})
        tokens[principal] = iam.issue_token("default", principal)
        grants[principal] = IssuerGrant(principal, "default", role, secrets.token_bytes(32))
    trust = EvidenceTrust(grants, iam=iam, issuer_tokens=tokens)
    db.coordinator._evidence_trust = trust
    binding = evidence_binding(
        tenant_id="default",
        project_id="p",
        issue_id="i",
        task_id="task",
        attempt_id="a1",
        run_id="run1",
        candidate_commit_sha="a" * 40,
        base_commit_sha="b" * 40,
        policy_version=1,
        fencing_token=2,
        suite_digest=("f" if case == "different_suite" else "d") * 64,
        worker_image="sha256:" + "e" * 64,
        developer_principal_id="builder",
    )
    with trusted_coordinator_admin_scope():
        db.coordinator.register_evidence_contract(binding, "verifier", "reviewer", ["positive", "negative"])
        receipts = []
        for principal in ["verifier", "reviewer"]:
            result = (
                {"passed": True, "test_count": 2, "outcomes": [{"id": x, "passed": True} for x in ["positive", "negative"]]}
                if principal == "verifier"
                else {"verdict": "APPROVED", "comments": "Independent fixture review"}
            )
            receipt = signed_envelope(binding, grants[principal].role, principal, principal, grants[principal].secret, "PRODUCTION", result)
            db.coordinator.record_evidence_receipt(**receipt)
            receipts.append(receipt["evidence_id"])
    if case == "revoked_reviewer":
        iam.revoke_session(tokens["reviewer"], iam.verify_token(tokens["reviewer"]).token_id)
    if case != "valid":
        with actor("reviewer"), pytest.raises((PermissionError, DeliveryGateError)):
            s.accept("i", state(s)["revision"], verification_id=receipts[0], review_id=receipts[1])
        assert state(s)["phase"] == "IN_REVIEW"
        with db.atomic_transaction() as c:
            assert c.execute("SELECT COUNT(*) FROM pm_coordinator_evidence_receipts WHERE admission_status='ADMITTED'").fetchone()[0] == 0
        return
    with actor("reviewer"):
        assert s.accept("i", state(s)["revision"], verification_id=receipts[0], review_id=receipts[1])["phase"] == "ACCEPTED"
    with trusted_coordinator_admin_scope():
        db.update_issue_state("i", "DONE", "fixture")
    iam.revoke_session(tokens["reviewer"], iam.verify_token(tokens["reviewer"]).token_id)
    # Existing ADMITTED label cannot retain acceptance after issuer revocation.
    with trusted_coordinator_admin_scope(), pytest.raises(PermissionError):
        db.update_issue_state("i", "DONE", "fixture")


@pytest.mark.parametrize(
    "field,value", [("policy_version", True), ("policy_version", "1"), ("critical", "yes"), ("scope", ["../escape"]), ("base_sha", "HEAD")]
)
def test_contract_inputs_are_strict_and_bounded(field, value):
    data = brief()
    data[field] = value
    with pytest.raises(ValidationError):
        DeliveryBrief.model_validate(data)


def test_scope_change_is_separate_from_rejection_and_requires_new_agreement(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    with actor("reviewer"):
        s.request_scope_change("i", state(s)["revision"], proposal="Add explicitly approved R2 with its own checks")
    with actor("coordinator"):
        assert s.metrics("i")["rejections"] == 0
        assert s.metrics("i")["scope_requests"] == 1
        with pytest.raises(DeliveryGateError, match="Overturned"):
            s.resume_review("i", state(s)["revision"], reason="Skip newly requested scope")
        changed = brief()
        changed["requirements"].append({"id": "R2", "rule": "New approved requirement"})
        changed["checks"].append(
            {"id": "r2-positive", "requirement_id": "R2", "command": "trusted check", "expected": "new positive case", "negative": False}
        )
        changed["checks"].append(
            {"id": "r2-negative", "requirement_id": "R2", "command": "trusted check", "expected": "new negative case", "negative": True}
        )
        s.establish("i", changed, expected_revision=state(s)["revision"], reason="Scope addition recorded as new work")
    assert state(s)["phase"] == "DRAFT"
    assert state(s)["version"] == 2
    with trusted_coordinator_admin_scope(), pytest.raises(DeliveryGateError):
        CoordinatorAdmissionEngine(db).admit_task("i", budget_reservation=10)


def test_scope_refresh_after_policy_change_is_possible_without_bypass(env):
    db, s = env
    ready(s)
    with db.atomic_transaction() as c:
        c.execute("UPDATE pm_issues SET policy_version=2 WHERE id='i'")
    changed = brief()
    changed["policy_version"] = 2
    with actor("coordinator"):
        s.establish("i", changed, expected_revision=state(s)["revision"], reason="Approved issue policy changed")
    assert state(s)["phase"] == "DRAFT"


def test_overturned_review_can_resume_same_candidate_without_fake_correction(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    reject(s)
    with actor("builder"):
        s.challenge("i", state(s)["revision"], "F1", "The reproduction contradicted the agreed requirement")
    with actor("coordinator"):
        s.resolve_challenge("i", state(s)["revision"], "F1", upheld=False, reason="Recorded reviewer error")
        s.resume_review("i", state(s)["revision"], reason="Independent review resumes on unchanged candidate")
        metrics = s.metrics("i")
    assert state(s)["phase"] == "IN_REVIEW"
    assert metrics["formal_submissions"] == 1
    assert metrics["rejections"] == 1
    assert metrics["overturned_findings"] == 1


def test_enrolled_project_cannot_create_done_issue(env):
    db, _ = env
    from mas.pm.models import IssueState

    with pytest.raises(DeliveryGateError, match="pre-completed"):
        db.create_issue(Issue(id="fake-done", project_id="p", key="G-2", title="False completion", current_state=IssueState.DONE))


def test_atomic_rollback_does_not_leave_dispatch_or_hold(env):
    db, s = env
    ready(s)
    with trusted_coordinator_admin_scope(), pytest.raises(RuntimeError):
        with db.atomic_transaction() as c:
            db.coordinator.create_attempt("a", "default", "p", "i", "task", 1, conn=c)
            db.coordinator.create_intent("intent", "default", "p", "i", "task", "a", "synthetic", {}, conn=c)
            raise RuntimeError("Injected crash before commit")
    assert state(s)["phase"] == "READY"
    with db.atomic_transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM pm_delivery_dispatches").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM pm_coordinator_intents").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM pm_delivery_events WHERE kind='DISPATCH_ADMITTED'").fetchone()[0] == 0


def test_migration_checksum_tamper_rejected_without_changing_old_ledger(env):
    db, _ = env
    with db.atomic_transaction() as c:
        c.execute("UPDATE pm_schema_migrations SET checksum='tampered' WHERE version=2026101301")
    with pytest.raises(DeliveryGateError, match="checksum"):
        PMDatabase(db.db_path)


def test_current_tenant_session_revoked_during_binding_fails(tmp_path):
    iam = MultiTenantIAM(secrets.token_hex(32))
    iam.create_tenant("t", "Tenant")
    iam.register_principal("t", "coordinator", scopes={"storage:*", "delivery:*"})
    token = iam.issue_token("t", "coordinator")
    with tenant_scope(iam, token, "t", tmp_path / "tenants"):
        db = PMDatabase()
        db.create_project(Project(id="p", key="P", name="Project"))
        db.create_issue(Issue(id="i", project_id="p", key="P-1", title="Task", path_whitelist=["mas/"]))
        s = DeliveryService(db)
        s.enroll("p", "t")
        s.establish("i", brief())
        iam.revoke_session(token, iam.verify_token(token).token_id)
        with pytest.raises(PermissionError):
            s.get("i")


def test_cross_tenant_read_is_denied_even_with_same_project_id(tmp_path):
    iam = MultiTenantIAM(secrets.token_hex(32))
    for tenant in ["one", "two"]:
        iam.create_tenant(tenant, tenant)
        iam.register_principal(tenant, "coordinator", scopes={"storage:*", "delivery:*"})
    token1 = iam.issue_token("one", "coordinator")
    token2 = iam.issue_token("two", "coordinator")
    with tenant_scope(iam, token1, "one", tmp_path / "tenants"):
        db = PMDatabase()
        db.create_project(Project(id="p", key="P", name="Project"))
        db.create_issue(Issue(id="i", project_id="p", key="P-1", title="Task", path_whitelist=["mas/"]))
        s = DeliveryService(db)
        s.enroll("p", "one")
        s.establish("i", brief())
    with tenant_scope(iam, token2, "two", tmp_path / "tenants"), pytest.raises(PermissionError):
        s.get("i")


def test_applied_migration_does_not_mask_missing_enforcement_trigger(env):
    db, _ = env
    with db.atomic_transaction() as c:
        c.execute("DROP TRIGGER pm_delivery_events_no_delete")
    with pytest.raises(DeliveryGateError, match="schema mismatch"):
        PMDatabase(db.db_path)


def test_real_historical_schema_upgrade_preserves_data(tmp_path):
    from pathlib import Path

    path = tmp_path / "historical.db"
    with sqlite3.connect(path) as c:
        c.executescript(Path("tests/fixtures/cc03_pre_correction.sql").read_text())
        before = c.execute("SELECT COUNT(*) FROM pm_issues").fetchone()[0]
    db = PMDatabase(path)
    with db.atomic_transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM pm_issues").fetchone()[0] == before
        assert c.execute("SELECT COUNT(*) FROM pm_delivery_projects").fetchone()[0] == 0
        assert c.execute("SELECT COUNT(*) FROM pm_schema_migrations WHERE version=2026101301").fetchone()[0] == 1
    PMDatabase(path)


def test_readiness_returns_cannot_be_hidden_from_metrics(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s, observations=[])
    submit(s, observations=[])
    submit(s)
    with actor("coordinator"):
        metrics = s.metrics("i")
    assert metrics["readiness_returns"] == 2
    assert metrics["formal_submissions"] == 1
    assert metrics["rejections"] == 0


@pytest.mark.parametrize("revision", [True, "1", 1.5, None])
def test_revision_types_cannot_bypass_cas(env, revision):
    _, s = env
    with actor("reviewer"), pytest.raises(DeliveryGateError, match="integer"):
        s.agree("i", revision, role="reviewer", rationale="Checked")


def test_host_actor_requires_explicit_trusted_authority():
    with pytest.raises(PermissionError):
        with delivery_admin_actor("reviewer"):
            pass


@pytest.mark.parametrize("launched", [False, True])
def test_cancellation_updates_gate_and_preserves_truthful_accounting(env, launched):
    db, s = env
    ready(s)
    with trusted_coordinator_admin_scope():
        intent = CoordinatorAdmissionEngine(db).admit_task("i", budget_reservation=10)
        if launched:
            assert db.coordinator.claim_intent(intent.intent_id, "worker", 1, 100, 30)
            assert db.coordinator.pre_spawn_intent(intent.intent_id, "worker", 2, 101, "run")
        assert db.coordinator.cancel_intent(intent.intent_id)
        current = db.coordinator.get_intent(intent.intent_id)
    assert current.status == ("CANCEL_REQUESTED" if launched else "CANCELED")
    assert state(s)["phase"] == "UNCERTAIN"
    with db.atomic_transaction() as c:
        assert c.execute("SELECT status FROM pm_coordinator_reservations").fetchone()[0] == ("HELD" if launched else "RELEASED")
    with actor("coordinator"):
        if launched:
            with pytest.raises(DeliveryGateError):
                s.reconcile_execution("i", state(s)["revision"], reason="No termination confirmation")
        else:
            assert s.reconcile_execution("i", state(s)["revision"], reason="Unlaunched cancellation confirmed")["phase"] == "READY"


def test_constructed_model_cannot_bypass_strict_contract_validation(env):
    _, s = env
    forged = DeliveryBrief.model_validate(brief()).model_copy(update={"policy_version": True})
    with actor("coordinator"), pytest.raises(ValidationError):
        s.establish("i", forged, expected_revision=state(s)["revision"], reason="Forged bool policy")


def test_scope_request_cannot_use_ordinary_correction_resume(env):
    db, s = env
    ready(s)
    execute(db, s)
    submit(s)
    with actor("reviewer"):
        s.request_scope_change("i", state(s)["revision"], proposal="Additional acceptance requirement proposed")
    with actor("coordinator"), pytest.raises(DeliveryGateError, match="scope proposal"):
        s.resume("i", state(s)["revision"], design_plan="Ignore outstanding scope decision")
