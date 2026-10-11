"""Regression evidence for immutable policy/candidate bindings and strict requests."""
import hashlib
import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from mas.pm.db import PMDatabase
from mas.pm.guards import UnverifiedWorkError, validate_evidence
from mas.pm.models import EvidenceLink, EvidenceType, Issue, PlanReconciliationRequest, Project


@pytest.fixture
def bound_evidence(tmp_path):
    db = PMDatabase(tmp_path / 'evidence.db')
    db.create_project(Project(id='p', key='BND', name='Bindings'))
    issue = db.create_issue(Issue(id='i', project_id='p', key='BND-1', title='Bindings'))
    log = tmp_path / 'run.log'
    log.write_text('measured test output')
    candidate = 'a' * 40
    for kind, digest, uri, payload in [
        (EvidenceType.GIT_COMMIT, candidate, 'git:commit:' + candidate, {}),
        (EvidenceType.TEST_RUN_LOG, hashlib.sha256(log.read_bytes()).hexdigest(), str(log), {'exit_code': 0}),
    ]:
        db.attach_evidence(EvidenceLink(
            id=kind.value, issue_id=issue.id, evidence_type=kind, content_hash=digest, uri=uri,
            payload={'policy_version': 1, 'candidate_commit_sha': candidate, **payload},
        ))
    return db, issue, tmp_path


@pytest.mark.parametrize('field,value', [
    ('policy_version', 2), ('candidate_commit_sha', 'b' * 40),
    ('exit_code', 1), ('runner_principal', 'different-runner'),
])
def test_payload_relabeling_invalidates_original_signature(bound_evidence, field, value):
    db, issue, root = bound_evidence
    links = deepcopy(db.get_evidence_links(issue.id))
    for link in links:
        link.payload[field] = value
    if field == 'policy_version':
        issue.policy_version = 2
    class TamperedView:
        def get_evidence_links(self, issue_id):
            return links
    with pytest.raises(UnverifiedWorkError, match='signature|Candidate commit mismatch'):
        validate_evidence(TamperedView(), issue, workspace_root=root, enforce_git_commit=False)


@pytest.mark.parametrize('removed', ['policy_version', 'provenance_version', 'candidate_commit_sha'])
def test_unbound_or_legacy_evidence_cannot_verify(bound_evidence, removed):
    db, issue, root = bound_evidence
    links = deepcopy(db.get_evidence_links(issue.id))
    for link in links:
        link.payload.pop(removed, None)
    class LegacyView:
        def get_evidence_links(self, issue_id):
            return links
    with pytest.raises(UnverifiedWorkError):
        validate_evidence(LegacyView(), issue, workspace_root=root, enforce_git_commit=False)


def test_reopen_keeps_bound_signatures_and_policy_history(bound_evidence):
    db, issue, root = bound_evidence
    reopened = PMDatabase(db.db_path)
    validate_evidence(reopened, issue, workspace_root=root, enforce_git_commit=False)
    with reopened.atomic_transaction() as conn:
        conn.execute('UPDATE pm_issues SET policy_version=2 WHERE id=?', (issue.id,))
    with pytest.raises(UnverifiedWorkError, match='stale'):
        validate_evidence(reopened, reopened.get_issue(issue.id), workspace_root=root, enforce_git_commit=False)
    assert all(link.payload['policy_version'] == 1 for link in reopened.get_evidence_links(issue.id))


@pytest.mark.parametrize('payload', [
    {'exit_code': 0}, {'policy_version': 1, 'exit_code': 0},
    {'policy_version': True, 'candidate_commit_sha': 'a' * 40},
])
def test_attachment_cannot_stamp_missing_measurement_binding(bound_evidence, payload):
    db, issue, _ = bound_evidence
    with pytest.raises(ValueError):
        db.attach_evidence(EvidenceLink(id='missing', issue_id=issue.id,
            evidence_type=EvidenceType.TEST_RUN_LOG, content_hash='a' * 64,
            uri='missing.log', payload=payload))
    assert len(db.get_evidence_links(issue.id)) == 2


@pytest.mark.parametrize('field', ['expected_proposal_rev', 'expected_base_policy_version'])
@pytest.mark.parametrize('value', [True, '1', 1.0, None])
def test_reconciliation_json_rejects_coercion(field, value):
    request = {'decision': 'apply', 'expected_proposal_id': 'p',
               'expected_proposal_rev': 1, 'expected_base_policy_version': 1}
    request[field] = value
    with pytest.raises(ValidationError):
        PlanReconciliationRequest.model_validate_json(json.dumps(request))
