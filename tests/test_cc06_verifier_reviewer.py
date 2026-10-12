import sqlite3
import subprocess

import pytest

from mas.pm.adapters.verifier import (
    CodexReviewerAdapter,
    VerifierAdapter,
    sign_payload,
    verify_signature,
)
from mas.pm.db import PMDatabase
from mas.pm.models import Issue, Project


def test_canonical_json_and_signature_verification():
    payload = {
        "b_field": 123,
        "a_field": "test",
        "nested": {"z": True, "y": False},
    }
    secret = b"test-secret-key-12345-very-long"
    sig = sign_payload(payload, secret)

    # Valid signature passes
    assert verify_signature(payload, sig, secret) is True

    # Tampered payload fails
    tampered = dict(payload, b_field=124)
    assert verify_signature(tampered, sig, secret) is False

    # Short / weak secret fails
    with pytest.raises(ValueError, match="at least 16 bytes"):
        sign_payload(payload, b"short")


def test_separation_of_builder_and_verifier():
    verifier = VerifierAdapter(
        verifier_id="builder-agent-01",
        key_id="test-key-1",
        signing_secret=b"valid-secret-key-12345",
    )

    with pytest.raises(PermissionError, match="Builder cannot verify own candidate"):
        verifier.verify_candidate(
            tenant_id="tenant-1",
            project_id="proj-1",
            issue_id="issue-1",
            task_id="task-1",
            attempt_id="att-1",
            run_id="run-1",
            candidate_commit_sha="c0ffee1234567890abcdef1234567890abcdef12",
            base_commit_sha="b000000000000000000000000000000000000000",
            developer_principal_id="builder-agent-01",
        )


def test_separation_of_builder_and_reviewer():
    reviewer = CodexReviewerAdapter(
        reviewer_id="builder-agent-01",
        key_id="test-key-1",
        signing_secret=b"valid-secret-key-12345",
    )

    with pytest.raises(PermissionError, match="Builder cannot review own candidate"):
        reviewer.review_candidate(
            tenant_id="tenant-1",
            project_id="proj-1",
            issue_id="issue-1",
            task_id="task-1",
            attempt_id="att-1",
            run_id="run-1",
            candidate_commit_sha="c0ffee1234567890abcdef1234567890abcdef12",
            base_commit_sha="b000000000000000000000000000000000000000",
            policy_version=1,
            developer_principal_id="builder-agent-01",
        )


def test_verifier_fails_on_nonexistent_candidate_commit():
    verifier = VerifierAdapter(
        verifier_id="trusted-verifier-01",
        key_id="test-key-1",
        signing_secret=b"valid-secret-key-12345",
    )
    fake_sha = "ffffffffffffffffffffffffffffffffffffffff"
    with pytest.raises(ValueError, match="does not exist in repository"):
        verifier.verify_candidate(
            tenant_id="tenant-1",
            project_id="proj-1",
            issue_id="issue-1",
            task_id="task-1",
            attempt_id="att-1",
            run_id="run-1",
            candidate_commit_sha=fake_sha,
            base_commit_sha="0000000000000000000000000000000000000000",
        )


def test_trusted_verifier_real_commit_execution_and_admission(tmp_path):
    secret = b"coordinator-trusted-secret-test-long"
    db = PMDatabase(tmp_path / "coordinator_evidence.db")
    db.create_project(Project(id="p1", key="P1", name="Project 1"))
    db.create_issue(Issue(id="i1", project_id="p1", key="P1-1", title="Task 1"))

    with db.atomic_transaction() as conn:
        conn.execute(
            "INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key) "
            "VALUES ('p1', 'REF-1', 'task-1', 'i1', 'P1-1')"
        )

    from mas.pm.coordinator import trusted_coordinator_admin_scope

    # Get real HEAD commit from repository
    real_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    with trusted_coordinator_admin_scope():
        db.coordinator.create_attempt_with_intent(
            attempt_id="att-1",
            intent_id="intent-1",
            tenant_id="tenant-1",
            project_id="p1",
            issue_id="i1",
            task_id="task-1",
            attempt_seq=1,
            adapter_type="antigravity",
            payload={},
            budget_reservation=500,
        )
        db.coordinator.claim_intent("intent-1", "worker-1", 1, 100.0, 30.0)
        db.coordinator.pre_spawn_intent("intent-1", "worker-1", 2, 101.0, "run-1", "att-1")

        verifier = VerifierAdapter(
            verifier_id="trusted-verifier-01",
            key_id="mas-verifier-key-1",
            signing_secret=secret,
            is_test_domain=False,
        )

        receipt_dict = verifier.verify_candidate(
            tenant_id="tenant-1",
            project_id="p1",
            issue_id="i1",
            task_id="task-1",
            attempt_id="att-1",
            run_id="run-1",
            candidate_commit_sha=real_commit,
            base_commit_sha=real_commit,
            test_command=["python3", "-c", "import sys; print('1 passed in 0.01s'); sys.exit(0)"],
            developer_principal_id="builder-dev-01",
        )

        # 1. Record receipt (enters SUBMITTED)
        receipt = db.coordinator.record_evidence_receipt(
            evidence_id=receipt_dict["evidence_id"],
            issue_id=receipt_dict["issue_id"],
            task_id=receipt_dict["task_id"],
            attempt_id=receipt_dict["attempt_id"],
            run_id=receipt_dict["run_id"],
            candidate_commit_sha=receipt_dict["candidate_commit_sha"],
            nonce=receipt_dict["nonce"],
            key_id=receipt_dict["key_id"],
            signature=receipt_dict["signature"],
            canonical_payload=receipt_dict["canonical_payload"],
        )
        assert receipt.admission_status == "SUBMITTED"

        # 2. Admit receipt with trusted keys
        trusted_keys = {"mas-verifier-key-1": secret}
        admitted = db.coordinator.admit_evidence_receipt(receipt_dict["evidence_id"], trusted_keys=trusted_keys)
        assert admitted is True

        # Verify status in database
        with db._get_connection() as c:
            row = c.execute(
                "SELECT admission_status FROM pm_coordinator_evidence_receipts WHERE evidence_id = ?",
                (receipt_dict["evidence_id"],)
            ).fetchone()
            assert row[0] == "ADMITTED"

        # 3. Test forged signature rejection
        forged_id = "ev-forged-01"
        db.coordinator.record_evidence_receipt(
            evidence_id=forged_id,
            issue_id=receipt_dict["issue_id"],
            task_id=receipt_dict["task_id"],
            attempt_id=receipt_dict["attempt_id"],
            run_id=receipt_dict["run_id"],
            candidate_commit_sha=receipt_dict["candidate_commit_sha"],
            nonce="nonce-forged-unique",
            key_id="mas-verifier-key-1",
            signature="bad-signature-hex",
            canonical_payload=receipt_dict["canonical_payload"],
        )
        with pytest.raises(PermissionError, match="invalid or forged cryptographic signature"):
            db.coordinator.admit_evidence_receipt(forged_id, trusted_keys=trusted_keys)

        # 4. Test replay rejection (same nonce fails UNIQUE constraint)
        replayed_id = "ev-replayed-02"
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed: pm_coordinator_evidence_receipts.nonce"):
            db.coordinator.record_evidence_receipt(
                evidence_id=replayed_id,
                issue_id=receipt_dict["issue_id"],
                task_id=receipt_dict["task_id"],
                attempt_id=receipt_dict["attempt_id"],
                run_id=receipt_dict["run_id"],
                candidate_commit_sha=receipt_dict["candidate_commit_sha"],
                nonce=receipt_dict["nonce"],
                key_id="mas-verifier-key-1",
                signature=receipt_dict["signature"],
                canonical_payload=receipt_dict["canonical_payload"],
            )


def test_test_domain_simulation_rejected_from_production_admission(tmp_path):
    secret = b"coordinator-trusted-secret-test-long"
    db = PMDatabase(tmp_path / "test_domain.db")
    db.create_project(Project(id="p1", key="P1", name="Project 1"))
    db.create_issue(Issue(id="i1", project_id="p1", key="P1-1", title="Task 1"))

    with db.atomic_transaction() as conn:
        conn.execute(
            "INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key) "
            "VALUES ('p1', 'REF-1', 'task-1', 'i1', 'P1-1')"
        )

    from mas.pm.coordinator import trusted_coordinator_admin_scope

    real_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    with trusted_coordinator_admin_scope():
        db.coordinator.create_attempt_with_intent(
            attempt_id="att-2",
            intent_id="intent-2",
            tenant_id="tenant-1",
            project_id="p1",
            issue_id="i1",
            task_id="task-1",
            attempt_seq=1,
            adapter_type="antigravity",
            payload={},
            budget_reservation=500,
        )
        db.coordinator.claim_intent("intent-2", "worker-1", 1, 100.0, 30.0)
        db.coordinator.pre_spawn_intent("intent-2", "worker-1", 2, 101.0, "run-2", "att-2")

        test_verifier = VerifierAdapter(
            verifier_id="test-verifier",
            key_id="mas-verifier-key-1",
            signing_secret=secret,
            is_test_domain=True,  # Test domain flagged!
        )
        receipt_dict = test_verifier.verify_candidate(
            tenant_id="tenant-1",
            project_id="p1",
            issue_id="i1",
            task_id="task-1",
            attempt_id="att-2",
            run_id="run-2",
            candidate_commit_sha=real_commit,
            base_commit_sha=real_commit,
            test_command=["python3", "-c", "import sys; print('1 passed in 0.01s'); sys.exit(0)"],
        )
        db.coordinator.record_evidence_receipt(
            evidence_id=receipt_dict["evidence_id"],
            issue_id=receipt_dict["issue_id"],
            task_id=receipt_dict["task_id"],
            attempt_id=receipt_dict["attempt_id"],
            run_id=receipt_dict["run_id"],
            candidate_commit_sha=receipt_dict["candidate_commit_sha"],
            nonce=receipt_dict["nonce"],
            key_id=receipt_dict["key_id"],
            signature=receipt_dict["signature"],
            canonical_payload=receipt_dict["canonical_payload"],
        )
        trusted_keys = {"mas-verifier-key-1": secret}
        with pytest.raises(PermissionError, match="test-domain simulated evidence cannot be promoted"):
            db.coordinator.admit_evidence_receipt(receipt_dict["evidence_id"], trusted_keys=trusted_keys)
