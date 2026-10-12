"""Regressions for forged admission, exact observations and applied-ledger upgrades."""
import json
from pathlib import Path
import sqlite3

import pytest

from mas.pm.coordinator import trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.models import Issue, Project

HISTORY = Path(__file__).parent / 'fixtures/cc03_pre_correction.sql'


@pytest.fixture
def observer_store(tmp_path):
    db = PMDatabase(tmp_path / 'pm.db')
    db.create_project(Project(id='p', key='OBS', name='Observations', token_budget=100))
    db.create_issue(Issue(id='i', project_id='p', key='OBS-1', title='Observation', appetite_tokens=100))
    with db.atomic_transaction() as c:
        c.execute("INSERT INTO pm_task_mappings(project_id,planning_reference,task_id,local_issue_id,local_issue_key) VALUES('p','O-1','task','i','OBS-1')")
    with trusted_coordinator_admin_scope():
        store = db.coordinator
        store.create_attempt_with_intent('a', 'intent', 'tenant', 'p', 'i', 'task', 1, 'antigravity', {}, budget_reservation=10)
        store.claim_intent('intent', 'worker', 1, 1, 100)
        store.pre_spawn_intent('intent', 'worker', 2, 2, 'run')
        store.cancel_intent('intent')
        yield db, store


@pytest.mark.parametrize('change', [
    {'exit_code': 0}, {'tokens_spent': 9}, {'observed_status': 'EXITED'},
])
@pytest.mark.parametrize('receipt_id', [None, 'receipt'])
def test_changed_termination_replay_rejected_without_rebilling(observer_store, change, receipt_id):
    db, store = observer_store
    original = dict(intent_id='intent', run_id='run', exit_code=-15, tokens_spent=2,
                    observed_status='KILLED', receipt_id=receipt_id)
    assert store.record_authoritative_termination(**original)
    assert store.record_authoritative_termination(**original)
    with pytest.raises(sqlite3.IntegrityError, match='Conflicting'):
        store.record_authoritative_termination(**{**original, **change})
    assert db.get_project('p').tokens_consumed == 2
    with db._get_connection() as c:
        observation = c.execute('SELECT * FROM pm_coordinator_termination_observations').fetchone()
        payload = json.loads(observation['canonical_payload'])
        assert payload['task_id'] == 'task'
        assert payload['attempt_id'] == 'a'
        assert payload['tokens_spent'] == 2
        assert c.execute('SELECT COUNT(*) FROM pm_coordinator_evidence_receipts').fetchone()[0] == 0


def test_forged_receipt_cannot_be_promoted_even_by_admin(observer_store):
    db, store = observer_store
    store.record_evidence_receipt('fake', 'i', 'task', 'a', 'run', 'a'*40,
                                  'nonce', 'unknown-key', 'forged', {'fake': True})
    with pytest.raises(PermissionError, match='admission is disabled'):
        store.admit_evidence_receipt('fake')
    with db._get_connection() as c:
        assert c.execute("SELECT admission_status FROM pm_coordinator_evidence_receipts WHERE evidence_id='fake'").fetchone()[0] == 'SUBMITTED'


def historical_database(path):
    with sqlite3.connect(path) as conn:
        conn.executescript(HISTORY.read_text())


def test_upgrade_preserves_history_and_old_ledger_then_reopens(tmp_path):
    path = tmp_path / 'history.db'
    historical_database(path)
    with sqlite3.connect(path) as c:
        original_ledger = c.execute('SELECT * FROM pm_schema_migrations').fetchall()
        assert original_ledger[0][0] == 2026101201
        receipts_before = c.execute('SELECT evidence_id,signature,canonical_payload FROM pm_coordinator_evidence_receipts').fetchall()
    db = PMDatabase(path)
    with db._get_connection() as c:
        assert c.execute('SELECT * FROM pm_schema_migrations WHERE version=2026101201').fetchall()[0][:] == original_ledger[0]
        checksum = c.execute('SELECT checksum FROM pm_schema_migrations WHERE version=2026101202').fetchone()[0]
        assert len(checksum) == 64
        assert c.execute('SELECT evidence_id,signature,canonical_payload FROM pm_coordinator_evidence_receipts').fetchall()[0][:] == receipts_before[0]
        assert c.execute('SELECT admission_status FROM pm_coordinator_evidence_receipts').fetchone()[0] == 'SUBMITTED'
        assert c.execute('SELECT COUNT(*) FROM pm_coordinator_events').fetchone()[0] == 1
        assert c.execute('PRAGMA foreign_key_check').fetchall() == []
        assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert any(r['table']=='pm_coordinator_intents' and r['from']=='attempt_id'
                   for r in c.execute('PRAGMA foreign_key_list(pm_coordinator_runs)'))
    PMDatabase(path)


def test_corrective_migration_failure_restores_prior_schema_and_rows(tmp_path, monkeypatch):
    path = tmp_path / 'rollback.db'
    historical_database(path)
    connect = sqlite3.connect
    class FailingConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if 'CREATE TABLE IF NOT EXISTS pm_coordinator_termination_observations' in sql:
                raise sqlite3.OperationalError('injected migration failure')
            return super().execute(sql, *args, **kwargs)
    def failing_connect(*args, **kwargs):
        kwargs['factory'] = FailingConnection
        return connect(*args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(sqlite3, 'connect', failing_connect)
        with pytest.raises(sqlite3.OperationalError, match='injected'):
            PMDatabase(path)
    with connect(path) as c:
        assert c.execute('SELECT version FROM pm_schema_migrations').fetchall() == [(2026101201,)]
        assert 'admission_status' not in {r[1] for r in c.execute('PRAGMA table_info(pm_coordinator_evidence_receipts)')}
        assert c.execute('SELECT COUNT(*) FROM pm_coordinator_events').fetchone()[0] == 1
        assert c.execute('SELECT signature FROM pm_coordinator_evidence_receipts').fetchone()[0] == 'historical-signature'
    PMDatabase(path)
