"""Candidate-specific trusted evidence, recovery and hostile envelope qualification."""
import json
import secrets
import sqlite3
import subprocess

import pytest

from mas.pm.adapters.admission import EvidenceTrust, IssuerGrant
from mas.pm.adapters.verifier import (
    CodexReviewerAdapter, VerificationContract, VerifierAdapter, evidence_binding,
    sign_payload, signed_envelope, verify_signature,
)
from mas.pm.coordinator import CoordinatorStore, trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.models import Issue, Project

# Offline provenance fixtures need a syntactically pinned identity, not a real image.
IMAGE = 'sha256:' + 'a' * 64


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / 'repo'
    path.mkdir()
    def git(*args):
        return subprocess.run(['git', '-C', str(path), *args], check=True, capture_output=True, text=True).stdout.strip()
    git('init')
    git('config', 'user.name', 'Test Builder')
    git('config', 'user.email', 'fixture@example.invalid')
    (path / 'candidate.py').write_text('def solve(payload):\n    return payload + 1\n')
    git('add', '.')
    git('commit', '-m', 'candidate')
    return path, git


@pytest.fixture
def contract():
    return VerificationContract('candidate.py', json.dumps([{'id':'one', 'input':1, 'expected':2}]), IMAGE)


@pytest.fixture
def runtime_contract(coordinator_test_image):
    return VerificationContract('candidate.py', json.dumps([{'id':'one', 'input':1, 'expected':2}]), coordinator_test_image)


@pytest.fixture
def admitted_store(tmp_path, contract):
    db = PMDatabase(tmp_path / 'pm.db')
    db.create_project(Project(id='p', key='P', name='Project', token_budget=1000))
    db.create_issue(Issue(id='i', project_id='p', key='P-1', title='Task'))
    with db.atomic_transaction() as c:
        c.execute("INSERT INTO pm_task_mappings(project_id,planning_reference,task_id,local_issue_id,local_issue_key) VALUES ('p','REF','task','i','P-1')")
    key = secrets.token_bytes(32)
    review_key = secrets.token_bytes(32)
    from mas.iam import MultiTenantIAM
    iam_secret = secrets.token_hex(32)
    iam = MultiTenantIAM(iam_secret, db_path=tmp_path/'iam.db')
    iam.create_tenant('tenant','Tenant')
    issuer_tokens = {}
    for subject, scope in [('verifier','coordinator:evidence:verify'), ('reviewer','coordinator:evidence:review')]:
        iam.register_principal('tenant',subject,scopes={scope})
        issuer_tokens['verify-key' if subject == 'verifier' else 'review-key'] = iam.issue_token('tenant',subject)
    trust = EvidenceTrust({'verify-key': IssuerGrant('verifier', 'tenant', 'VERIFICATION_EVIDENCE', key),
                           'review-key': IssuerGrant('reviewer', 'tenant', 'REVIEW_EVIDENCE', review_key)}, iam=iam, issuer_tokens=issuer_tokens)
    trust._fixture_secret = iam_secret
    store = CoordinatorStore(db, evidence_trust=trust)
    with trusted_coordinator_admin_scope():
        store.create_attempt_with_intent('a', 'intent', 'tenant', 'p', 'i', 'task', 1, 'synthetic', {}, budget_reservation=100)
        assert store.claim_intent('intent', 'worker', 1, 100, 30)
        assert store.pre_spawn_intent('intent', 'worker', 2, 101, 'run', 'a')
        assert store.complete_intent('intent', 'worker', 2, 102, 'a'*40, 1, 0)
        binding = evidence_binding(tenant_id='tenant', project_id='p', issue_id='i', task_id='task',
            attempt_id='a', run_id='run', candidate_commit_sha='a'*40, base_commit_sha='b'*40,
            policy_version=1, fencing_token=2, suite_digest=contract.suite_digest,
            worker_image=IMAGE, developer_principal_id='builder')
        store.register_evidence_contract(binding, 'verifier', 'reviewer', ['one'])
        yield db, store, binding, key, review_key


def receipt(store, binding, key, *, role='VERIFICATION_EVIDENCE', result=None, domain='PRODUCTION', mutate=None):
    obj = signed_envelope(binding, role, 'verifier' if role == 'VERIFICATION_EVIDENCE' else 'reviewer',
        'verify-key' if role == 'VERIFICATION_EVIDENCE' else 'review-key', key, domain,
        result or ({'passed': True, 'test_count':1, 'outcomes':[{'id':'one','passed':True}]} if role == 'VERIFICATION_EVIDENCE' else {'verdict':'APPROVED','comments':'Checked'}))
    if mutate:
        mutate(obj['canonical_payload'])
        obj['signature'] = sign_payload(obj['canonical_payload'], key)
    store.record_evidence_receipt(**obj)
    return obj['evidence_id']


def test_valid_evidence_then_independent_review_and_exact_replay(admitted_store):
    db, store, binding, key, review_key = admitted_store
    review = receipt(store, binding, review_key, role='REVIEW_EVIDENCE')
    with pytest.raises(PermissionError, match='verified evidence'):
        store.admit_evidence_receipt(review)
    verification = receipt(store, binding, key)
    assert store.admit_evidence_receipt(verification)
    assert store.admit_evidence_receipt(verification)
    assert store.admit_evidence_receipt(review)
    # Trust is not inferred from the environment or from persisted ADMITTED labels.
    with pytest.raises(PermissionError, match='disabled'):
        CoordinatorStore(db).admit_evidence_receipt(verification)


@pytest.mark.parametrize('field,value', [
    ('tenant_id','other'), ('project_id','other'), ('issue_id','other'), ('task_id','other'),
    ('attempt_id','other'), ('run_id','other'), ('candidate_commit_sha','c'*40),
    ('base_commit_sha','c'*40), ('policy_version',2), ('fencing_token',3),
    ('suite_digest','c'*64), ('worker_image','sha256:'+'c'*64),
    ('developer_principal_id','verifier'), ('issuer_id','builder'), ('key_id','other'),
    ('type','UNKNOWN_EVIDENCE'), ('schema','old'), ('domain','TEST'), ('domain',False),
])
def test_signed_wrong_binding_never_admitted(admitted_store, field, value):
    db, store, binding, key, _ = admitted_store
    ident = receipt(store, binding, key, mutate=lambda p: p.update({field:value}))
    with pytest.raises((ValueError, PermissionError)):
        store.admit_evidence_receipt(ident)
    with db._get_connection() as c:
        assert c.execute('SELECT admission_status FROM pm_coordinator_evidence_receipts WHERE evidence_id=?', (ident,)).fetchone()[0] == 'SUBMITTED'


@pytest.mark.parametrize('result', [
    {'passed':False,'test_count':1,'outcomes':[{'id':'one','passed':True}]},
    {'passed':True,'test_count':0,'outcomes':[]},
    {'passed':True,'test_count':True,'outcomes':[{'id':'one','passed':True}]},
    {'passed':True,'test_count':1,'outcomes':[{'id':'one','passed':False}]},
    {'passed':True,'test_count':1,'outcomes':[{'id':'wrong','passed':True}]},
    {'passed':True,'test_count':1,'outcomes':[{'id':'one','passed':True}],'extra':'claim'},
])
def test_failed_or_fabricated_results_rejected(admitted_store, result):
    _, store, binding, key, _ = admitted_store
    ident = receipt(store, binding, key, result=result)
    with pytest.raises(ValueError):
        store.admit_evidence_receipt(ident)


@pytest.mark.parametrize('sql', [
    "UPDATE pm_issues SET policy_version=2 WHERE id='i'",
    "UPDATE pm_issues SET has_pending_reconciliation=1 WHERE id='i'",
    "UPDATE pm_coordinator_intents SET fencing_token=3 WHERE intent_id='intent'",
    "UPDATE pm_coordinator_intents SET status='UNKNOWN_EXECUTION' WHERE intent_id='intent'",
    "UPDATE pm_coordinator_attempts SET candidate_commit_sha='changed' WHERE attempt_id='a'",
    "UPDATE pm_coordinator_runs SET exit_code=1 WHERE run_id='run'",
])
def test_stale_execution_policy_or_fence_rejected(admitted_store, sql):
    db, store, binding, key, _ = admitted_store
    ident = receipt(store, binding, key)
    with db.atomic_transaction() as c:
        c.execute(sql)
    with pytest.raises(ValueError):
        store.admit_evidence_receipt(ident)


def test_caller_keys_forgery_and_manifest_replacement_rejected(admitted_store):
    _, store, binding, key, _ = admitted_store
    ident = receipt(store, binding, key)
    with pytest.raises(PermissionError, match='overrides'):
        store.admit_evidence_receipt(ident, {'verify-key':key})
    with pytest.raises(ValueError, match='cannot be replaced'):
        store.register_evidence_contract({**binding, 'policy_version':2}, 'verifier', 'reviewer', ['one'])
    forged = receipt(store, binding, secrets.token_bytes(32))
    with pytest.raises(PermissionError, match='signature'):
        store.admit_evidence_receipt(forged)


def test_reopen_preserves_contract_and_trust_remains_service_owned(admitted_store):
    db, store, binding, key, _ = admitted_store
    ident = receipt(store, binding, key)
    assert store.admit_evidence_receipt(ident)
    reopened = PMDatabase(db.db_path)
    with reopened._get_connection() as c:
        assert c.execute('SELECT COUNT(*) FROM pm_coordinator_evidence_contracts').fetchone()[0] == 1
        assert c.execute('PRAGMA foreign_key_check').fetchall() == []
    with pytest.raises(PermissionError, match='disabled'):
        reopened.coordinator.admit_evidence_receipt(ident)


def test_unsigned_duplicate_keys_and_nonce_replay_rejected(admitted_store):
    db, store, binding, key, _ = admitted_store
    ident = receipt(store, binding, key)
    with db.atomic_transaction() as c:
        c.execute('UPDATE pm_coordinator_evidence_receipts SET canonical_payload=? WHERE evidence_id=?', ('{"type":"VERIFICATION_EVIDENCE","type":"UNKNOWN_EVIDENCE"}', ident))
    with pytest.raises(RuntimeError):
        store.admit_evidence_receipt(ident)
    with db._get_connection() as c:
        obj = c.execute('SELECT nonce FROM pm_coordinator_evidence_receipts WHERE evidence_id=?', (ident,)).fetchone()
    with pytest.raises(sqlite3.IntegrityError):
        store.record_evidence_receipt('other','i','task','a','run','a'*40,obj['nonce'],'verify-key','bad',{})


def test_signature_requires_private_key_and_detects_tamper():
    key = secrets.token_bytes(32)
    payload = {'value':1}
    assert verify_signature(payload, sign_payload(payload,key), key)
    assert not verify_signature({'value':2}, sign_payload(payload,key), key)
    with pytest.raises(ValueError):
        sign_payload({}, b'public-development-key')


def verify(repo, contract, **changes):
    path, git = repo
    args = dict(tenant_id='tenant',project_id='p',issue_id='i',task_id='task',attempt_id='a',run_id='run',
                candidate_commit_sha=git('rev-parse','HEAD'),base_commit_sha=git('rev-parse','HEAD'),
                developer_principal_id='builder', policy_version=1,fencing_token=2)
    args.update(changes)
    return VerifierAdapter('verifier','verify-key',secrets.token_bytes(32),path,contract=contract).verify_candidate(**args)


def test_real_candidate_measured_outside_container(repo, runtime_contract):
    evidence = verify(repo, runtime_contract)
    assert evidence['canonical_payload']['result'] == {'passed':True,'test_count':1,'outcomes':[{'id':'one','passed':True}]}


@pytest.mark.parametrize('source', [
    "def solve(payload):\n print('1 passed in 0.01s')\n return 999\n",
    "import os\ndef solve(payload):\n return os.environ.get('MAS_EVIDENCE_SECRET')\n",
    "def solve(payload):\n return 999\n",
])
def test_faked_stdout_bad_output_and_secret_reads_do_not_pass(repo, runtime_contract, source):
    path, git = repo
    (path/'candidate.py').write_text(source)
    git('add','.')
    git('commit','-m','adversarial candidate')
    assert verify(repo, runtime_contract)['canonical_payload']['result']['passed'] is False


def test_arbitrary_test_command_and_builder_self_verification_forbidden(repo, contract):
    with pytest.raises(PermissionError, match='stdout summaries'):
        verify(repo, contract, test_command=['python','-c',"print('1 passed')"])
    with pytest.raises(PermissionError, match='builder'):
        verify(repo, contract, developer_principal_id='verifier')
    with pytest.raises(PermissionError):
        verify(repo, contract, developer_principal_id=None)


@pytest.mark.parametrize('changes', [{'candidate_commit_sha':'f'*40}, {'base_commit_sha':'f'*40}, {'candidate_commit_sha':'HEAD'}])
def test_exact_candidate_and_base_must_exist(repo, contract, changes):
    with pytest.raises(ValueError):
        verify(repo, contract, **changes)


def test_strict_final_reviewer_schema(admitted_store):
    _, _, binding, _, _ = admitted_store
    good = {'schema':'mas-review-v1','binding':binding,'verdict':'APPROVED','comments':'checked'}
    assert CodexReviewerAdapter.parse_final(json.dumps(good), binding)['verdict'] == 'APPROVED'
    for raw in ['NOT APPROVED', 'VERDICT: APPROVED', json.dumps(good)+'\n'+json.dumps({**good,'verdict':'REJECTED'}), json.dumps({'verdict':'APPROVED'}), json.dumps({**good,'binding':{**binding,'policy_version':2}})]:
        with pytest.raises((RuntimeError, ValueError)):
            CodexReviewerAdapter.parse_final(raw, binding)


def test_cc06_upgrade_demotes_old_admission_without_reusing_cc03_ledger(tmp_path):
    path = tmp_path/'old.db'
    db = PMDatabase(path)
    with db.atomic_transaction() as c:
        original = c.execute('SELECT checksum FROM pm_schema_migrations WHERE version=2026101202').fetchone()[0]
        c.execute('DELETE FROM pm_schema_migrations WHERE version=2026101203')
        c.execute('DROP TABLE pm_coordinator_evidence_contracts')
    reopened = PMDatabase(path)
    with reopened._get_connection() as c:
        assert c.execute('SELECT checksum FROM pm_schema_migrations WHERE version=2026101202').fetchone()[0] == original
        assert c.execute('SELECT COUNT(*) FROM pm_schema_migrations WHERE version=2026101203').fetchone()[0] == 1


def test_issuer_revocation_survives_restart_and_blocks_review(admitted_store):
    db, store, binding, key, review_key = admitted_store
    verified = receipt(store, binding, key)
    assert store.admit_evidence_receipt(verified)
    trust = store._evidence_trust
    trust._iam.register_principal('tenant','admin',roles={'tenant_admin'})
    token = trust._iam.issue_token('tenant','admin')
    trust._iam.revoke_principal_sessions(token, 'verifier')
    review = receipt(store, binding, review_key, role='REVIEW_EVIDENCE')
    with pytest.raises(PermissionError):
        store.admit_evidence_receipt(review)
    from mas.iam import MultiTenantIAM
    restarted = MultiTenantIAM(trust._fixture_secret, db_path=trust._iam.database_path)
    with pytest.raises(PermissionError):
        restarted.verify_token(trust._tokens['verify-key'])


def test_tenant_writer_cannot_admit_and_revoked_admitter_loses_authority(admitted_store):
    from mas.tenancy import TenantBinding, _binding
    db, store, binding, key, _ = admitted_store
    ident = receipt(store, binding, key)
    iam = store._evidence_trust._iam
    for subject, scopes in [('writer',{'storage:read','storage:write'}),
                            ('admitter',{'storage:read','storage:write','coordinator:evidence:admit'})]:
        iam.register_principal('tenant', subject, scopes=scopes)
        token = iam.issue_token('tenant',subject)
        context = iam.verify_token(token)
        marker = _binding.set(TenantBinding(iam, context, db.db_path.parent, db.db_path))
        try:
            with trusted_coordinator_admin_scope(False):
                if subject == 'writer':
                    with pytest.raises(PermissionError):
                        store.admit_evidence_receipt(ident)
                else:
                    assert store.admit_evidence_receipt(ident)
                    iam.register_principal('tenant','admin',roles={'tenant_admin'})
                    iam.revoke_principal_sessions(iam.issue_token('tenant','admin'),'admitter')
                    with pytest.raises(PermissionError):
                        store.admit_evidence_receipt(ident)
        finally:
            _binding.reset(marker)


def test_upgrade_demotes_unjustified_cc06_receipts_preserving_bytes(admitted_store):
    db, store, binding, key, _ = admitted_store
    ident = receipt(store, binding, key)
    assert store.admit_evidence_receipt(ident)
    with db.atomic_transaction() as c:
        before = c.execute('SELECT signature,canonical_payload FROM pm_coordinator_evidence_receipts WHERE evidence_id=?',(ident,)).fetchone()
        c.execute('DROP TABLE pm_coordinator_evidence_contracts')
        c.execute('DELETE FROM pm_schema_migrations WHERE version=2026101203')
    upgraded = PMDatabase(db.db_path)
    with upgraded._get_connection() as c:
        after = c.execute('SELECT signature,canonical_payload,admission_status FROM pm_coordinator_evidence_receipts WHERE evidence_id=?',(ident,)).fetchone()
        assert tuple(after)[:2] == tuple(before)
        assert after['admission_status'] == 'SUBMITTED'
        assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    PMDatabase(db.db_path)


def test_symlink_candidate_source_is_not_executed(repo, contract):
    path, git = repo
    (path/'candidate.py').unlink()
    (path/'candidate.py').symlink_to('/etc/passwd')
    git('add','.')
    git('commit','-m','symlink candidate')
    with pytest.raises(ValueError, match='regular Git blob'):
        verify(repo, contract)


def test_stored_admission_label_cannot_turn_signed_failure_into_review_approval(admitted_store):
    db, store, binding, key, review_key = admitted_store
    failed = receipt(store, binding, key, result={'passed':False,'test_count':1,'outcomes':[{'id':'one','passed':False}]})
    with db.atomic_transaction() as c:
        c.execute("UPDATE pm_coordinator_evidence_receipts SET admission_status='ADMITTED' WHERE evidence_id=?",(failed,))
    review = receipt(store, binding, review_key, role='REVIEW_EVIDENCE')
    with pytest.raises(PermissionError, match='verified evidence'):
        store.admit_evidence_receipt(review)


def test_shared_signing_key_cannot_impersonate_independent_roles(admitted_store):
    _, store, _, key, _ = admitted_store
    trust = store._evidence_trust
    with pytest.raises(ValueError, match='Distinct'):
        EvidenceTrust({'verify-key':IssuerGrant('verifier','tenant','VERIFICATION_EVIDENCE',key),
                       'review-key':IssuerGrant('reviewer','tenant','REVIEW_EVIDENCE',key)},
                       iam=trust._iam, issuer_tokens=trust._tokens)
