"""
tests/test_gov_03_evidence_provenance.py: Rigorous test suite for GOV-03:
Tamper-evident evidence provenance, immutable evidence triggers, and integrity audits.
"""

import hashlib
import json
import sqlite3
import pytest

from mas.pm.db import PMDatabase
from mas.pm.guards import UnverifiedWorkError, validate_evidence
from mas.pm.models import EvidenceLink, EvidenceType, Issue, IssueState, Project
from mas.security import sign_evidence_provenance, verify_evidence_provenance


@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_pm.db"
    db = PMDatabase(db_path)
    proj = Project(id="proj-gov-03", key="GOV", name="Governance Test")
    db.create_project(proj)
    return db


@pytest.fixture
def test_issue(test_db):
    issue = Issue(
        id="issue-gov-03-test",
        project_id="proj-gov-03",
        key="GOV-101",
        title="Tamper-evident evidence test issue",
        description="Testing GOV-03 evidence provenance",
        issue_type="TASK",
        current_state=IssueState.IN_PROGRESS,
        assignee_principal="security_sre",
        path_whitelist=["tests/", "mas/"],
    )
    return test_db.create_issue(issue)


def test_evidence_auto_signs_provenance(test_db, test_issue):
    """Verifies that attaching evidence automatically generates a valid HMAC provenance signature."""
    ev = EvidenceLink(
        id="ev-001",
        issue_id=test_issue.id,
        evidence_type=EvidenceType.TEST_RUN_LOG,
        content_hash="a" * 64,
        uri="file://tests/sample.log",
        payload={"exit_code": 0},
    )
    saved = test_db.attach_evidence(ev)

    assert "provenance_signature" in saved.payload
    sig = saved.payload["provenance_signature"]
    assert verify_evidence_provenance(
        evidence_id="ev-001",
        issue_id=test_issue.id,
        evidence_type="TEST_RUN_LOG",
        content_hash="a" * 64,
        uri="file://tests/sample.log",
        signature=sig,
    )


def test_sqlite_trigger_prevents_evidence_update(test_db, test_issue):
    """Verifies that direct database updates to evidence records are aborted by SQLite triggers."""
    ev = EvidenceLink(
        id="ev-002",
        issue_id=test_issue.id,
        evidence_type=EvidenceType.TEST_RUN_LOG,
        content_hash="b" * 64,
        uri="file://tests/sample.log",
        payload={"exit_code": 0},
    )
    test_db.attach_evidence(ev)

    # Attempt direct SQL update to tamper with content_hash
    conn = sqlite3.connect(test_db.db_path)
    with pytest.raises(sqlite3.IntegrityError, match="TamperViolationError"):
        conn.execute("UPDATE pm_evidence_links SET content_hash = ? WHERE id = ?", ("c" * 64, "ev-002"))
    conn.close()


def test_sqlite_trigger_prevents_evidence_delete(test_db, test_issue):
    """Verifies that direct database deletions of evidence records are aborted by SQLite triggers."""
    ev = EvidenceLink(
        id="ev-003",
        issue_id=test_issue.id,
        evidence_type=EvidenceType.TEST_RUN_LOG,
        content_hash="d" * 64,
        uri="file://tests/sample.log",
        payload={"exit_code": 0},
    )
    test_db.attach_evidence(ev)

    # Attempt direct SQL delete to destroy evidence
    conn = sqlite3.connect(test_db.db_path)
    with pytest.raises(sqlite3.IntegrityError, match="TamperViolationError"):
        conn.execute("DELETE FROM pm_evidence_links WHERE id = ?", ("ev-003",))
    conn.close()


def test_evidence_integrity_audit_detects_file_tampering(test_db, test_issue, tmp_path):
    """Verifies that file tampering on disk is caught by verify_issue_evidence_integrity."""
    log_file = tmp_path / "run.log"
    log_file.write_text("initial passing test output")
    initial_hash = hashlib.sha256(log_file.read_bytes()).hexdigest()

    ev = EvidenceLink(
        id="ev-004",
        issue_id=test_issue.id,
        evidence_type=EvidenceType.TEST_RUN_LOG,
        content_hash=initial_hash,
        uri=str(log_file),
        payload={"exit_code": 0},
    )
    test_db.attach_evidence(ev)

    # Initial check should pass
    report = test_db.verify_issue_evidence_integrity(test_issue.id, workspace_root=tmp_path)
    assert report["valid"] is True
    assert len(report["anomalies"]) == 0

    # Tamper with the file on disk
    log_file.write_text("tampered test output with defect")
    tampered_report = test_db.verify_issue_evidence_integrity(test_issue.id, workspace_root=tmp_path)
    assert tampered_report["valid"] is False
    assert any("Content hash mismatch" in a for a in tampered_report["anomalies"])


def test_guard_rejects_forged_provenance_signature(test_db, test_issue, tmp_path):
    """Verifies that validate_evidence fails closed when evidence provenance signature is invalid."""
    log_file = tmp_path / "valid.log"
    log_file.write_text("clean test logs")
    h = hashlib.sha256(log_file.read_bytes()).hexdigest()

    # Create evidence with forged provenance signature
    ev = EvidenceLink(
        id="ev-005",
        issue_id=test_issue.id,
        evidence_type=EvidenceType.TEST_RUN_LOG,
        content_hash=h,
        uri=str(log_file),
        payload={"exit_code": 0, "provenance_signature": "forged_bad_signature_123"},
    )
    test_db.attach_evidence(ev)

    # Attach git commit evidence
    ev_git = EvidenceLink(
        id="ev-git",
        issue_id=test_issue.id,
        evidence_type=EvidenceType.GIT_COMMIT,
        content_hash="head",
        uri="git:commit:head",
        payload={},
    )
    test_db.attach_evidence(ev_git)

    with pytest.raises(UnverifiedWorkError, match="provenance signature verification failed"):
        validate_evidence(test_db, test_issue, workspace_root=tmp_path, enforce_git_commit=False)
