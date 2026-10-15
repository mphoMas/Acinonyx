"""
Unit, integration, concurrency, recovery, and boundary tests for GHA-04A Quarantined Receipt Slice.

Verifies:
1. Real subprocess kill before commit leaves 0 rows persisted.
2. Real subprocess kill after commit before response allows fresh-auth recovery of EXISTING receipt.
3. Fresh-auth recovery after token expiry without duplicate mutation.
4. Concurrent identical observations yield 1 CREATED, N EXISTING with same receipt ID.
5. Concurrent conflicting observations preserve existing record and reject conflicting attempt.
6. New attempt with same action ID and distinct observation ID succeeds under shared action contract.
7. Changed contract under same action ID fails with ACTION_CONTRACT_CONFLICT.
8. Cross-tenant isolation blocks foreign write and hides foreign read without disclosure.
9. Foreign/non-enrolled task reference is rejected.
10. Naked TenantContext is rejected without IAM authentication.
11. SQLite triggers prevent UPDATE, DELETE, REPLACE, IGNORE, UPSERT, and authority tampering.
12. Authority guard serializes tenant suspension, principal suspension, session revocation, and connector policy.
13. Check scope and order are validated before transaction; equality is allowed.
14. Bounds (1 MiB JSON, 128 items, 64 artifacts) and quota boundaries are strictly enforced.
15. Zero delivery phase, submission, or budget mutation occurs.
16. Additive migration is idempotent and detects schema/checksum drift.
"""

from __future__ import annotations

import json
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from typing import Any

import pytest

from mas.iam import MultiTenantIAM, StandardRole, TenantContext
from mas.pm.delivery import DeliveryGateError, DeliveryService, delivery_admin_actor
from mas.pm.gateway.models import ConnectorRegistry, GitHubConnectorConfig
from mas.pm.models import Issue, Project
from mas.pm.receipts import (
    MAX_CANONICAL_BYTES,
    get_receipt,
    migrate_receipts,
    record_observation,
)
from mas.tenancy import TenantBinding


def make_brief() -> dict[str, Any]:
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
        "mechanism": "Quarantined receipt slice test fixture",
        "requirements": [{"id": "R1", "rule": "No unsupported completion evidence"}],
        "checks": [
            {"id": "check-a", "requirement_id": "R1", "command": "cmd_a", "expected": "passes", "negative": False},
            {"id": "check-b", "requirement_id": "R1", "command": "cmd_b", "expected": "rejects", "negative": True},
        ],
    }


def make_contract(candidate_sha: str = "a" * 40, check_ids: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "claims": {
            "candidate_sha": candidate_sha,
            "base_sha": "b" * 40,
            "suite_digest": "c" * 64,
            "policy_version": 1,
            "brief_version": 1,
            "source_generation": None,
        },
        "check_ids": check_ids if check_ids is not None else ["check-a", "check-b"],
    }


def make_payload(
    outcome: str = "PASSED",
    items: list[dict[str, str]] | None = None,
    attempt: int = 1,
    repo_id: str = "100",
    owner_id: str = "200",
) -> dict[str, Any]:
    if items is None:
        items = [
            {"check_id": "check-a", "claimed_outcome": outcome},
            {"check_id": "check-b", "claimed_outcome": outcome},
        ]
    return {
        "schema_version": 1,
        "transport_claims": {
            "repository_id": repo_id,
            "repository_owner_id": owner_id,
            "github_run_id": "500",
            "github_run_attempt": attempt,
        },
        "mas_claims": {
            "run_id": "run-1",
            "intent_id": "intent-1",
            "attempt_id": "attempt-1",
            "fence": 1,
        },
        "items": items,
        "artifact_claims": [],
        "limitations": "Quarantined test observation",
    }


@pytest.fixture
def setup_env(tmp_path):
    from mas.pm.db import PMDatabase

    db_path = tmp_path / "pm.db"
    db = PMDatabase(db_path)

    # Initialize IAM with explicit signing key and durable SQLite identity store
    iam_db_path = tmp_path / "iam.db"
    iam = MultiTenantIAM(signing_secret="0123456789abcdef0123456789abcdef", db_path=iam_db_path)
    iam.create_tenant("tenant-1", "Tenant One")
    iam.register_principal("tenant-1", "user-1", roles={StandardRole.TENANT_ADMIN.value})

    iam.create_tenant("tenant-2", "Tenant Two")
    iam.register_principal("tenant-2", "user-2", roles={StandardRole.TENANT_ADMIN.value})

    # Create project & issue in DB
    db.create_project(Project(id="proj-1", key="P1", name="Project 1", token_budget=10000))
    db.create_issue(Issue(id="issue-1", project_id="proj-1", key="P1-1", title="Task 1", appetite_tokens=1000, path_whitelist=["mas/"]))

    # Enroll in delivery
    delivery_svc = DeliveryService(db)
    from mas.pm.coordinator import trusted_coordinator_admin_scope

    with trusted_coordinator_admin_scope(), delivery_admin_actor("coordinator"):
        delivery_svc.enroll("proj-1", "tenant-1")
        delivery_svc.establish("issue-1", make_brief())

    # Issue token for tenant-1
    token_1 = iam.issue_token("tenant-1", "user-1", ttl_seconds=3600)
    context_1 = iam.verify_token(token_1)
    binding_1 = TenantBinding(iam, context_1, tmp_path / "workspaces" / "tenant-1", db_path)

    # Issue token for tenant-2
    token_2 = iam.issue_token("tenant-2", "user-2", ttl_seconds=3600)
    context_2 = iam.verify_token(token_2)
    binding_2 = TenantBinding(iam, context_2, tmp_path / "workspaces" / "tenant-2", db_path)

    # Connector Registry
    connector_reg = ConnectorRegistry()
    connector_reg.register(
        GitHubConnectorConfig(
            tenant_id="tenant-1",
            project_id="proj-1",
            repository_id="100",
            repository_owner_id="200",
            approved_workflow_repo="octocat/Acinonyx",
            approved_workflow_path=".github/workflows/reusable-delivery-gate.yml",
            approved_workflow_sha="a" * 40,
            status="ACTIVE",
            generation=1,
        )
    )

    return {
        "db": db,
        "db_path": db_path,
        "iam": iam,
        "binding_1": binding_1,
        "binding_2": binding_2,
        "token_1": token_1,
        "token_2": token_2,
        "connector_reg": connector_reg,
        "delivery_svc": delivery_svc,
        "tmp_path": tmp_path,
        "iam_db_path": iam_db_path,
    }


def test_real_subprocess_kill_before_commit(setup_env):
    """Subprocess killed before commit leaves 0 actions, 0 receipts, 0 items persisted."""
    db_path = str(setup_env["db_path"])

    child_code = f"""
import sqlite3, signal, time, os
conn = sqlite3.connect("{db_path}", timeout=5.0)
conn.execute("PRAGMA foreign_keys=ON;")
conn.execute("BEGIN IMMEDIATE;")
conn.execute("INSERT INTO pm_delivery_actions VALUES('tenant-1', 'proj-1', 'issue-1', 'act-kill-before', '{'a'*64}', '{{}}')")
print("READY", flush=True)
time.sleep(30)
"""
    proc = subprocess.Popen([sys.executable, "-c", child_code], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ready_line = proc.stdout.readline()
    assert "READY" in ready_line

    # Terminate uncommitted process with SIGKILL
    proc.send_signal(signal.SIGKILL)
    proc.wait()

    # Verify 0 rows persisted
    db = setup_env["db"]
    conn = db._get_connection()
    try:
        count = conn.execute("SELECT count(*) FROM pm_delivery_actions WHERE action_id='act-kill-before'").fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_real_subprocess_kill_after_commit_before_response_and_recovery(setup_env):
    """Subprocess killed immediately after commit allows fresh-auth recovery of EXISTING receipt."""
    db_path = str(setup_env["db_path"])
    iam_db_path = str(setup_env["iam_db_path"])
    token_1 = setup_env["token_1"]

    child_code = f"""
import os, signal, sys, json
from mas.iam import MultiTenantIAM
from mas.pm.db import PMDatabase
from mas.pm.receipts import record_observation, canonical_json, sha256_digest
from mas.tenancy import TenantBinding

iam = MultiTenantIAM(signing_secret="0123456789abcdef0123456789abcdef", db_path="{iam_db_path}")
ctx = iam.verify_token("{token_1}")
binding = TenantBinding(iam, ctx, sys.argv[0], "{db_path}")

contract = json.loads('''{json.dumps(make_contract())}''')
payload = json.loads('''{json.dumps(make_payload())}''')

db = PMDatabase("{db_path}")

with db.atomic_transaction() as conn:
    owner = ["tenant-1", "proj-1", "issue-1"]
    act_hash = sha256_digest({{"owner": owner, "contract": contract}})
    pay_hash = sha256_digest(payload)
    conn.execute("INSERT INTO pm_delivery_actions VALUES(?,?,?,?,?,?)", (*owner, "act-post-kill", act_hash, canonical_json(contract)))
    rcpt = "rcpt_" + sha256_digest({{"owner": owner, "action_id": "act-post-kill", "observation_id": "obs-post-kill", "payload_digest": pay_hash}})
    conn.execute("INSERT INTO pm_delivery_receipts VALUES(?,?,?,?,?,?,?,?,?,0)", (rcpt, *owner, "act-post-kill", "obs-post-kill", pay_hash, canonical_json(payload), "2026-10-15T10:00:00Z"))
    for item in payload["items"]:
        conn.execute("INSERT INTO pm_delivery_items VALUES(?,?,?,?,?,?)", (rcpt, *owner, item["check_id"], item["claimed_outcome"]))

# Transaction committed above. Now simulate sudden kill before response was returned
os.kill(os.getpid(), signal.SIGKILL)
"""
    proc = subprocess.run([sys.executable, "-c", child_code], capture_output=True)
    assert proc.returncode == -signal.SIGKILL or proc.returncode == 137

    # Recover using fresh authentication and supported record_observation
    iam = setup_env["iam"]
    fresh_token = iam.issue_token("tenant-1", "user-1", ttl_seconds=3600)
    fresh_ctx = iam.verify_token(fresh_token)
    fresh_binding = TenantBinding(iam, fresh_ctx, setup_env["tmp_path"], setup_env["db_path"])

    result = record_observation(
        fresh_binding,
        "act-post-kill",
        "obs-post-kill",
        make_contract(),
        make_payload(),
        issue_id="issue-1",
        db=setup_env["db"],
    )

    assert result["status"] == "EXISTING"
    assert result["receipt_id"].startswith("rcpt_")
    assert result["authority_verified"] is False
    assert result["source_authority_verified"] is False

    # Check DB has exactly 1 receipt and 1 action
    conn = setup_env["db"]._get_connection()
    try:
        assert conn.execute("SELECT count(*) FROM pm_delivery_actions WHERE action_id='act-post-kill'").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM pm_delivery_receipts WHERE action_id='act-post-kill'").fetchone()[0] == 1
    finally:
        conn.close()


def test_fresh_auth_recovery_after_token_expiry(setup_env):
    """Observation recorded with expiring token recovers EXISTING receipt with fresh token."""
    iam = setup_env["iam"]
    short_token = iam.issue_token("tenant-1", "user-1", ttl_seconds=1)
    short_ctx = iam.verify_token(short_token)
    short_binding = TenantBinding(iam, short_ctx, setup_env["tmp_path"], setup_env["db_path"])

    first = record_observation(
        short_binding,
        "act-exp",
        "obs-exp",
        make_contract(),
        make_payload(),
        issue_id="issue-1",
        db=setup_env["db"],
    )
    assert first["status"] == "CREATED"

    # Wait for short token to expire
    time.sleep(1.2)

    # Calling with expired token must be rejected
    with pytest.raises(PermissionError, match="Session token expired|Session expired"):
        record_observation(
            short_binding,
            "act-exp",
            "obs-exp",
            make_contract(),
            make_payload(),
            issue_id="issue-1",
            db=setup_env["db"],
        )

    # Fresh token recovers EXISTING
    fresh_token = iam.issue_token("tenant-1", "user-1", ttl_seconds=3600)
    fresh_ctx = iam.verify_token(fresh_token)
    fresh_binding = TenantBinding(iam, fresh_ctx, setup_env["tmp_path"], setup_env["db_path"])

    second = record_observation(
        fresh_binding,
        "act-exp",
        "obs-exp",
        make_contract(),
        make_payload(),
        issue_id="issue-1",
        db=setup_env["db"],
    )
    assert second["status"] == "EXISTING"
    assert second["receipt_id"] == first["receipt_id"]


def test_concurrent_identical_observations(setup_env):
    """Concurrent identical observation requests yield 1 CREATED, N EXISTING with same receipt ID."""
    results = []
    errors = []

    def worker():
        try:
            res = record_observation(
                setup_env["binding_1"],
                "act-concurrent-same",
                "obs-concurrent-same",
                make_contract(),
                make_payload(),
                issue_id="issue-1",
                db=setup_env["db"],
            )
            results.append(res)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(results) == 5
    statuses = [r["status"] for r in results]
    assert statuses.count("CREATED") == 1
    assert statuses.count("EXISTING") == 4
    # All receipt IDs must be identical
    receipt_ids = {r["receipt_id"] for r in results}
    assert len(receipt_ids) == 1

    conn = setup_env["db"]._get_connection()
    try:
        assert conn.execute("SELECT count(*) FROM pm_delivery_actions WHERE action_id='act-concurrent-same'").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM pm_delivery_receipts WHERE action_id='act-concurrent-same'").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM pm_delivery_items WHERE receipt_id=?", (list(receipt_ids)[0],)).fetchone()[0] == 2
    finally:
        conn.close()


def test_concurrent_conflicting_observations(setup_env):
    """Concurrent conflicting observations preserve existing record and reject conflicting attempt."""
    outcomes = ["PASSED", "FAILED"]
    results = []
    errors = []

    def worker(outcome):
        try:
            res = record_observation(
                setup_env["binding_1"],
                "act-concurrent-conflict",
                "obs-concurrent-conflict",
                make_contract(),
                make_payload(outcome=outcome),
                issue_id="issue-1",
                db=setup_env["db"],
            )
            results.append(res)
        except Exception as e:
            errors.append(e)

    t1 = threading.Thread(target=worker, args=(outcomes[0],))
    t2 = threading.Thread(target=worker, args=(outcomes[1],))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # One succeeds with CREATED, the other must fail with OBSERVATION_CONFLICT
    assert len(results) == 1
    assert results[0]["status"] == "CREATED"
    assert len(errors) == 1
    assert "OBSERVATION_CONFLICT" in str(errors[0])

    # Check original row intact in DB
    receipt = get_receipt(setup_env["binding_1"], results[0]["receipt_id"], db=setup_env["db"])
    assert receipt is not None
    assert receipt["receipt_id"] == results[0]["receipt_id"]


def test_new_attempt_same_action_different_observation(setup_env):
    """New attempt can report a different outcome for the same immutable action contract."""
    first = record_observation(
        setup_env["binding_1"],
        "act-multi-attempt",
        "obs-attempt-1",
        make_contract(),
        make_payload(outcome="FAILED", attempt=1),
        issue_id="issue-1",
        db=setup_env["db"],
    )
    assert first["status"] == "CREATED"

    second = record_observation(
        setup_env["binding_1"],
        "act-multi-attempt",
        "obs-attempt-2",
        make_contract(),
        make_payload(outcome="PASSED", attempt=2),
        issue_id="issue-1",
        db=setup_env["db"],
    )
    assert second["status"] == "CREATED"
    assert first["receipt_id"] != second["receipt_id"]

    conn = setup_env["db"]._get_connection()
    try:
        assert conn.execute("SELECT count(*) FROM pm_delivery_actions WHERE action_id='act-multi-attempt'").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM pm_delivery_receipts WHERE action_id='act-multi-attempt'").fetchone()[0] == 2
    finally:
        conn.close()


def test_changed_contract_requires_new_action(setup_env):
    """Changed contract with the same action ID raises ACTION_CONTRACT_CONFLICT."""
    first = record_observation(
        setup_env["binding_1"],
        "act-changed-contract",
        "obs-1",
        make_contract(candidate_sha="a" * 40),
        make_payload(),
        issue_id="issue-1",
        db=setup_env["db"],
    )
    assert first["status"] == "CREATED"

    changed_contract = make_contract(candidate_sha="d" * 40)
    with pytest.raises(ValueError, match="ACTION_CONTRACT_CONFLICT"):
        record_observation(
            setup_env["binding_1"],
            "act-changed-contract",
            "obs-2",
            changed_contract,
            make_payload(),
            issue_id="issue-1",
            db=setup_env["db"],
        )

    # Original action and receipt intact
    conn = setup_env["db"]._get_connection()
    try:
        assert conn.execute("SELECT count(*) FROM pm_delivery_actions WHERE action_id='act-changed-contract'").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM pm_delivery_receipts WHERE action_id='act-changed-contract'").fetchone()[0] == 1
    finally:
        conn.close()


def test_cross_tenant_isolation(setup_env):
    """Tenant B cannot write to Tenant A task, and reading Tenant A receipt returns None."""
    # Tenant A writes receipt
    first = record_observation(
        setup_env["binding_1"],
        "act-tenant-iso",
        "obs-1",
        make_contract(),
        make_payload(),
        issue_id="issue-1",
        db=setup_env["db"],
    )
    receipt_id = first["receipt_id"]

    # Tenant B tries to write to issue-1 owned by tenant-1
    with pytest.raises(PermissionError, match="Cross-tenant delivery task access forbidden"):
        record_observation(
            setup_env["binding_2"],
            "act-tenant-iso-b",
            "obs-b",
            make_contract(),
            make_payload(),
            issue_id="issue-1",
            db=setup_env["db"],
        )

    # Tenant B tries to read Tenant A's receipt -> returns None (no disclosure)
    res = get_receipt(setup_env["binding_2"], receipt_id, db=setup_env["db"])
    assert res is None

    # Tenant A reads own receipt -> succeeds
    res_a = get_receipt(setup_env["binding_1"], receipt_id, db=setup_env["db"])
    assert res_a is not None
    assert res_a["receipt_id"] == receipt_id
    assert res_a["tenant_id"] == "tenant-1"


def test_foreign_task_not_enrolled(setup_env):
    """Referencing an issue not enrolled in pm_delivery_tasks fails."""
    with pytest.raises(KeyError, match="Enrolled delivery task not found"):
        record_observation(
            setup_env["binding_1"],
            "act-nonexistent",
            "obs-1",
            make_contract(),
            make_payload(),
            issue_id="issue-nonexistent",
            db=setup_env["db"],
        )


def test_naked_tenant_context_rejected(setup_env):
    """Passing raw TenantContext without IAM authentication is rejected."""
    naked_ctx = TenantContext(
        tenant_id="tenant-1",
        principal_id="user-1",
        roles=frozenset({StandardRole.TENANT_ADMIN.value}),
        scopes=frozenset({"storage:*"}),
        token_id="fake-token",
        expires_at=time.time() + 3600,
    )
    with pytest.raises(PermissionError, match="Naked TenantContext cannot be accepted as proof of IAM authentication"):
        record_observation(
            naked_ctx,
            "act-naked",
            "obs-naked",
            make_contract(),
            make_payload(),
            issue_id="issue-1",
            db=setup_env["db"],
        )

    with pytest.raises(PermissionError, match="Naked TenantContext cannot be accepted as proof of IAM authentication"):
        get_receipt(naked_ctx, "rcpt_" + "0" * 64, db=setup_env["db"])


def test_sqlite_triggers_block_mutation_and_replace(setup_env):
    """Triggers prevent UPDATE, DELETE, REPLACE, IGNORE, UPSERT on receipts and actions."""
    res = record_observation(
        setup_env["binding_1"],
        "act-triggers",
        "obs-triggers",
        make_contract(),
        make_payload(),
        issue_id="issue-1",
        db=setup_env["db"],
    )
    receipt_id = res["receipt_id"]
    conn = setup_env["db"]._get_connection()
    try:
        # UPDATE blocked
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE pm_delivery_receipts SET authority_verified=1 WHERE receipt_id=?", (receipt_id,))

        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE pm_delivery_actions SET contract_json='{}' WHERE action_id='act-triggers'")

        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("UPDATE pm_delivery_items SET claimed_outcome='FAILED' WHERE receipt_id=?", (receipt_id,))

        # DELETE blocked
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("DELETE FROM pm_delivery_items WHERE receipt_id=?", (receipt_id,))

        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("DELETE FROM pm_delivery_receipts WHERE receipt_id=?", (receipt_id,))

        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute("DELETE FROM pm_delivery_actions WHERE action_id='act-triggers'")

        # REPLACE blocked
        receipt_row = conn.execute("SELECT * FROM pm_delivery_receipts WHERE receipt_id=?", (receipt_id,)).fetchone()
        with pytest.raises(sqlite3.IntegrityError, match="immutable: existing receipt"):
            conn.execute(
                "INSERT OR REPLACE INTO pm_delivery_receipts VALUES(?,?,?,?,?,?,?,?,?,?)",
                tuple(receipt_row),
            )

        # IGNORE blocked
        with pytest.raises(sqlite3.IntegrityError, match="immutable: existing receipt"):
            conn.execute(
                "INSERT OR IGNORE INTO pm_delivery_receipts VALUES(?,?,?,?,?,?,?,?,?,?)",
                tuple(receipt_row),
            )

        # ON CONFLICT DO UPDATE blocked
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            conn.execute(
                "INSERT INTO pm_delivery_receipts SELECT * FROM pm_delivery_receipts WHERE receipt_id=? "
                "ON CONFLICT(receipt_id) DO UPDATE SET payload_json='tampered'",
                (receipt_id,),
            )
    finally:
        conn.close()


def test_authority_guard_revocation_ordering(setup_env):
    """Authority guard serializes tenant suspension, principal suspension, session revocation, connector status."""
    iam = setup_env["iam"]
    token = iam.issue_token("tenant-1", "user-1", ttl_seconds=3600)
    ctx = iam.verify_token(token)
    binding = TenantBinding(iam, ctx, setup_env["tmp_path"], setup_env["db_path"])

    # 1. Normal record succeeds
    res1 = record_observation(
        binding,
        "act-auth-1",
        "obs-auth-1",
        make_contract(),
        make_payload(),
        issue_id="issue-1",
        db=setup_env["db"],
    )
    assert res1["status"] == "CREATED"

    # 2. Revoke session -> subsequent operations blocked
    iam.revoke_session(token, ctx.token_id)
    with pytest.raises(PermissionError, match="Session is revoked|Session expired, revoked or unavailable"):
        record_observation(
            binding,
            "act-auth-2",
            "obs-auth-2",
            make_contract(),
            make_payload(),
            issue_id="issue-1",
            db=setup_env["db"],
        )

    # 3. New session, then suspend principal -> blocked
    token_p = iam.issue_token("tenant-1", "user-1", ttl_seconds=3600)
    ctx_p = iam.verify_token(token_p)
    binding_p = TenantBinding(iam, ctx_p, setup_env["tmp_path"], setup_env["db_path"])

    iam.suspend_principal("tenant-1", "user-1")
    with pytest.raises(PermissionError, match="Principal is suspended|Principal suspended"):
        record_observation(
            binding_p,
            "act-auth-3",
            "obs-auth-3",
            make_contract(),
            make_payload(),
            issue_id="issue-1",
            db=setup_env["db"],
        )

    # 4. Suspend tenant -> blocked
    iam.register_principal("tenant-1", "user-alt", roles={StandardRole.TENANT_ADMIN.value})
    token_t = iam.issue_token("tenant-1", "user-alt", ttl_seconds=3600)
    ctx_t = iam.verify_token(token_t)
    binding_t = TenantBinding(iam, ctx_t, setup_env["tmp_path"], setup_env["db_path"])

    iam.suspend_tenant("tenant-1")
    with pytest.raises(PermissionError, match="Tenant is suspended"):
        record_observation(
            binding_t,
            "act-auth-4",
            "obs-auth-4",
            make_contract(),
            make_payload(),
            issue_id="issue-1",
            db=setup_env["db"],
        )


def test_connector_policy_revocation_blocks_admission(setup_env):
    """Revoking connector policy prevents observation admission under that repository."""
    conn_reg = setup_env["connector_reg"]
    # Mark connector suspended
    conn_reg.update(
        GitHubConnectorConfig(
            tenant_id="tenant-1",
            project_id="proj-1",
            repository_id="100",
            repository_owner_id="200",
            approved_workflow_repo="octocat/Acinonyx",
            approved_workflow_path=".github/workflows/reusable-delivery-gate.yml",
            approved_workflow_sha="a" * 40,
            status="REVOKED",
            generation=2,
        )
    )

    with pytest.raises(PermissionError, match="Connector policy is not registered or not active"):
        record_observation(
            setup_env["binding_1"],
            "act-conn-revoked",
            "obs-1",
            make_contract(),
            make_payload(),
            issue_id="issue-1",
            db=setup_env["db"],
            connector_registry=conn_reg,
        )


def test_check_scope_and_ordering_validation(setup_env):
    """Refuses unsorted, duplicate, and unknown check IDs before transaction; allows equality."""
    binding = setup_env["binding_1"]
    db = setup_env["db"]

    # 1. Unsorted contract checks -> rejected
    c_unsorted = make_contract(check_ids=["check-b", "check-a"])
    with pytest.raises(ValueError, match="check_ids must be strictly sorted and unique"):
        record_observation(binding, "a1", "o1", c_unsorted, make_payload(), issue_id="issue-1", db=db)

    # 2. Duplicate contract checks -> rejected
    c_dups = make_contract(check_ids=["check-a", "check-a"])
    with pytest.raises(ValueError, match="check_ids must be strictly sorted and unique"):
        record_observation(binding, "a1", "o1", c_dups, make_payload(), issue_id="issue-1", db=db)

    # 3. Unsorted payload item checks -> rejected
    p_unsorted = make_payload(items=[
        {"check_id": "check-b", "claimed_outcome": "PASSED"},
        {"check_id": "check-a", "claimed_outcome": "PASSED"},
    ])
    with pytest.raises(ValueError, match="item check_ids must be strictly sorted and unique"):
        record_observation(binding, "a1", "o1", make_contract(), p_unsorted, issue_id="issue-1", db=db)

    # 4. Unknown item check -> rejected
    p_unknown = make_payload(items=[
        {"check_id": "check-unknown", "claimed_outcome": "PASSED"},
    ])
    with pytest.raises(ValueError, match="item check_ids must be subset of contract check_ids"):
        record_observation(binding, "a1", "o1", make_contract(), p_unknown, issue_id="issue-1", db=db)

    # 5. Invalid claimed_outcome -> rejected
    p_bad_outcome = make_payload(items=[
        {"check_id": "check-a", "claimed_outcome": "INVALID_STATE"},
    ])
    with pytest.raises(ValueError, match="invalid claimed_outcome"):
        record_observation(binding, "a1", "o1", make_contract(), p_bad_outcome, issue_id="issue-1", db=db)

    # 6. Equality with contract set -> allowed
    p_equal = make_payload(items=[
        {"check_id": "check-a", "claimed_outcome": "PASSED"},
        {"check_id": "check-b", "claimed_outcome": "PASSED"},
    ])
    res = record_observation(binding, "act-check-equal", "o1", make_contract(), p_equal, issue_id="issue-1", db=db)
    assert res["status"] == "CREATED"


def test_limits_and_receipt_quota_boundaries(setup_env):
    """Enforces 1 MiB JSON, 128 items, 64 artifacts, and project receipt quota."""
    binding = setup_env["binding_1"]
    db = setup_env["db"]

    # 1. Combined canonical JSON > 1 MiB -> rejected
    oversized_payload = make_payload()
    oversized_payload["limitations"] = "x" * (MAX_CANONICAL_BYTES + 100)
    with pytest.raises(ValueError, match="Request bounds exceeded: combined canonical JSON exceeds"):
        record_observation(binding, "act-oversized", "o1", make_contract(), oversized_payload, issue_id="issue-1", db=db)

    # 2. Items > 128 -> rejected
    check_ids_129 = [f"chk-{i:03d}" for i in range(129)]
    contract_129 = make_contract(check_ids=check_ids_129)
    payload_129 = make_payload(items=[{"check_id": cid, "claimed_outcome": "PASSED"} for cid in check_ids_129])
    with pytest.raises(ValueError, match="items count 129 exceeds limit 128"):
        record_observation(binding, "act-129", "o1", contract_129, payload_129, issue_id="issue-1", db=db)

    # 3. Artifacts > 64 -> rejected
    payload_65_art = make_payload()
    payload_65_art["artifact_claims"] = [{"digest": "a" * 64} for _ in range(65)]
    with pytest.raises(ValueError, match="artifact_claims count 65 exceeds limit 64"):
        record_observation(binding, "act-65-art", "o1", make_contract(), payload_65_art, issue_id="issue-1", db=db)

    # 4. Quota cap: verify receipt creation stops at cap, but existing receipt retrieves
    from mas.pm import receipts
    orig_quota = receipts.MAX_RECEIPTS_PER_PROJECT
    try:
        receipts.MAX_RECEIPTS_PER_PROJECT = 2
        r1 = record_observation(binding, "act-q1", "obs-1", make_contract(), make_payload(), issue_id="issue-1", db=db)
        assert r1["status"] == "CREATED"

        r2 = record_observation(binding, "act-q2", "obs-1", make_contract(), make_payload(), issue_id="issue-1", db=db)
        assert r2["status"] == "CREATED"

        # Third admission exceeds quota
        with pytest.raises(ValueError, match="PROJECT_RECEIPT_QUOTA_EXCEEDED"):
            record_observation(binding, "act-q3", "obs-1", make_contract(), make_payload(), issue_id="issue-1", db=db)

        # Existing retrieval at cap is preserved
        r1_dup = record_observation(binding, "act-q1", "obs-1", make_contract(), make_payload(), issue_id="issue-1", db=db)
        assert r1_dup["status"] == "EXISTING"
        assert r1_dup["receipt_id"] == r1["receipt_id"]

        fetched = get_receipt(binding, r1["receipt_id"], db=db)
        assert fetched is not None
        assert fetched["receipt_id"] == r1["receipt_id"]
    finally:
        receipts.MAX_RECEIPTS_PER_PROJECT = orig_quota


def test_no_delivery_phase_or_budget_mutation(setup_env):
    """Observation recording strictly preserves delivery task phase, revision, and budget."""
    db = setup_env["db"]
    conn = db._get_connection()
    try:
        task_before = conn.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id='issue-1'").fetchone()
        proj_before = conn.execute("SELECT * FROM pm_projects WHERE id='proj-1'").fetchone()
    finally:
        conn.close()

    res = record_observation(
        setup_env["binding_1"],
        "act-no-mutation",
        "obs-1",
        make_contract(),
        make_payload(),
        issue_id="issue-1",
        db=db,
    )
    assert res["status"] == "CREATED"

    conn = db._get_connection()
    try:
        task_after = conn.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id='issue-1'").fetchone()
        proj_after = conn.execute("SELECT * FROM pm_projects WHERE id='proj-1'").fetchone()

        assert task_after["phase"] == task_before["phase"]
        assert task_after["revision"] == task_before["revision"]
        assert proj_after["tokens_consumed"] == proj_before["tokens_consumed"]
        assert proj_after["token_budget"] == proj_before["token_budget"]
    finally:
        conn.close()


def test_delivery_service_integration(setup_env):
    """DeliveryService exposes record_observation and get_receipt methods."""
    delivery_svc = setup_env["delivery_svc"]
    binding = setup_env["binding_1"]

    res = delivery_svc.record_observation(
        binding,
        "act-deliv-svc",
        "obs-1",
        make_contract(),
        make_payload(),
        issue_id="issue-1",
    )
    assert res["status"] == "CREATED"

    fetched = delivery_svc.get_receipt(binding, res["receipt_id"])
    assert fetched is not None
    assert fetched["receipt_id"] == res["receipt_id"]
    assert len(fetched["items"]) == 2


def test_migration_idempotence_and_drift_detection(setup_env):
    """Receipt migration is idempotent and aborts on drift."""
    db = setup_env["db"]

    # Re-running migration is idempotent
    migrate_receipts(db)

    # Tampering with a table definition raises schema mismatch
    conn = db._get_connection()
    try:
        conn.execute("UPDATE pm_schema_migrations SET checksum='tampered' WHERE version=2026101401")
    finally:
        conn.close()

    with pytest.raises(DeliveryGateError, match="Receipt migration checksum mismatch"):
        migrate_receipts(db)
