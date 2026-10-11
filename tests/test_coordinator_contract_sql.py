"""Execute the proposed contract SQL against the existing PM schema.

These are design checks, not a claim that a coordinator has been implemented.
"""
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlite3
from pathlib import Path

import pytest

from mas.pm.db import PMDatabase
from mas.pm.models import Issue, Project

CONTRACT = (Path(__file__).resolve().parents[1] /
            'projects/scrum-board-automation/planning/CC_02_COORDINATOR_CONTRACT.md').read_text()


def query(section):
    text = CONTRACT.split(section, 1)[1]
    return re.search(r'```sql\n(.*?)```', text, re.S).group(1)


@pytest.fixture
def connection(tmp_path):
    db = PMDatabase(tmp_path / 'pm.db')
    db.create_project(Project(id='p', key='RCE', name='Race'))
    db.create_issue(Issue(id='i', project_id='p', key='RCE-1', title='Race'))
    conn = db._get_connection()
    conn.execute('PRAGMA foreign_keys=ON')
    conn.executescript(query('## 3. Relational Persistence'))
    conn.execute("INSERT INTO pm_task_mappings(project_id,planning_reference,task_id,local_issue_id,local_issue_key) VALUES('p','T-1','task','i','RCE-1')")
    conn.execute("INSERT INTO pm_coordinator_attempts(attempt_id,tenant_id,project_id,issue_id,task_id,attempt_seq,status) VALUES('a','tenant','p','i','task',1,'PENDING')")
    conn.execute("INSERT INTO pm_coordinator_intents(intent_id,tenant_id,project_id,issue_id,task_id,attempt_id,adapter_type,status,payload) VALUES('intent','tenant','p','i','task','a','antigravity','PENDING','{}')")
    conn.commit()
    yield conn
    conn.close()


def params(now=10):
    return {'intent_id': 'intent', 'worker_id': 'worker', 'expected_fencing_token': 1,
            'assigned_fencing_token': 2, 'now_epoch': now, 'lease_timeout_s': 10, 'now_iso': 'test'}


def claim(conn):
    assert conn.execute(query('### 4.1 Compare-And-Swap'), params()).rowcount == 1


def test_concurrent_claim_has_single_winner(connection):
    database_path = connection.execute('PRAGMA database_list').fetchone()[2]
    barrier = Barrier(2)
    def contender():
        with sqlite3.connect(database_path, timeout=3) as conn:
            barrier.wait(timeout=3)
            return conn.execute(query('### 4.1 Compare-And-Swap'), params()).rowcount
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: contender(), range(2)))
    assert sorted(results) == [0, 1]


def test_expired_lease_cannot_spawn(connection):
    claim(connection)
    assert connection.execute(query('### 4.2 Pre-Spawn'), params(21)).rowcount == 0


def test_reaper_prevents_claimed_worker_resurrection(connection):
    claim(connection)
    retired = params(21)
    retired['expected_fencing_token'] = 2
    assert connection.execute(query('### 4.3.1 Atomic'), retired).rowcount == 1
    assert connection.execute(query('### 4.2 Pre-Spawn'), params(21)).rowcount == 0
    assert connection.execute(query('### 4.1 Compare-And-Swap'), params(21)).rowcount == 0


def test_cancelled_generation_rejects_late_completion(connection):
    claim(connection)
    assert connection.execute(query('### 4.2 Pre-Spawn'), params()).rowcount == 1
    connection.execute("UPDATE pm_coordinator_intents SET status='CANCEL_REQUESTED', fencing_token=fencing_token+1, worker_id=NULL WHERE intent_id='intent'")
    assert connection.execute(query('### 4.4 Stale Worker'), params()).rowcount == 0


def test_ownership_mismatch_is_rejected_by_foreign_key(connection):
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO pm_coordinator_intents(intent_id,tenant_id,project_id,issue_id,task_id,attempt_id,adapter_type,status,payload) VALUES('wrong','other-tenant','p','i','task','a','codex','PENDING','{}')")
