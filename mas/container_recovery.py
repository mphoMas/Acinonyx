"""Durable container operation ownership and conservative Docker recovery.

An empty daemon listing cannot retire a create whose acknowledgement was lost.
Keep that tombstone until its owned object is observed and removed. The journal
contains no credentials and never settles funding or grants a workflow retry.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from mas.swarm.contracts import SwarmError, canonical, strict_json


class ContainerJournal:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get('MAS_CONTAINER_JOURNAL_PATH', '.mas-runtime/container-recovery.sqlite'))
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise SwarmError('Container journal must be a private host-owned regular path')
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        if self.path.stat().st_uid != os.getuid() or self.path.stat().st_mode & 0o077:
            raise SwarmError('Container journal must be private to the supervisor user')
        with self._tx() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS container_journal_meta(
                id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, controller TEXT NOT NULL)''')
            db.execute('INSERT OR IGNORE INTO container_journal_meta VALUES(1,1,?)', (uuid.uuid4().hex,))
            row = db.execute('SELECT * FROM container_journal_meta WHERE id=1').fetchone()
            if row['version'] != 1:
                raise SwarmError('Unsupported container journal schema')
            self.controller = row['controller']
            db.execute('''CREATE TABLE IF NOT EXISTS container_runs(
                run_key TEXT PRIMARY KEY, namespace TEXT NOT NULL, tenant TEXT NOT NULL,
                principal TEXT NOT NULL, run_id TEXT NOT NULL, generation INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('ACTIVE','BLOCKED')))''')
            db.execute('''CREATE TABLE IF NOT EXISTS container_operations(
                operation_id TEXT PRIMARY KEY, run_key TEXT NOT NULL REFERENCES container_runs(run_key),
                name TEXT NOT NULL UNIQUE, generation INTEGER NOT NULL, image TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PREPARED','CREATING','CREATED','STARTING',
                    'UNKNOWN_CREATE','CLEANUP_PENDING','CLOSED')),
                container_id TEXT, create_confirmed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')

    @contextmanager
    def _tx(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def run_key(namespace, tenant, run_id):
        return hashlib.sha256(canonical([namespace, tenant, run_id]).encode()).hexdigest()

    def prepare(self, namespace, run_id, image, *, tenant='local', principal='local', generation=1):
        if namespace not in {'coordinator', 'swarm'} or any(not isinstance(v, str) or not v or len(v) > 256 for v in (tenant, principal, run_id)):
            raise SwarmError('Invalid trusted container identity')
        if not isinstance(image, str) or not re.fullmatch(r'(?:[a-zA-Z0-9./:_-]+@)?sha256:[0-9a-f]{64}', image):
            raise SwarmError('Immutable recovery image required')
        if type(generation) is not int or generation < 1:
            raise SwarmError('Invalid container generation')
        key = self.run_key(namespace, tenant, run_id)
        operation = uuid.uuid4().hex
        name = 'mas-'+namespace+'-'+operation
        with self._tx() as db:
            prior = db.execute('SELECT * FROM container_runs WHERE run_key=?', (key,)).fetchone()
            if prior:
                if principal != prior['principal']:
                    raise SwarmError('Container run belongs to another principal')
                if generation < prior['generation']:
                    raise SwarmError('Stale container generation')
                if generation == prior['generation'] and (prior['state'] != 'ACTIVE' or prior['principal'] != principal):
                    raise SwarmError('Container run is blocked or belongs to another principal')
                if generation > prior['generation']:
                    if db.execute("SELECT 1 FROM container_operations WHERE run_key=? AND state!='CLOSED'", (key,)).fetchone():
                        raise SwarmError('Unresolved container operations prohibit a new generation')
                    db.execute("UPDATE container_runs SET generation=?,principal=?,state='ACTIVE' WHERE run_key=?", (generation, principal, key))
            else:
                db.execute("INSERT INTO container_runs VALUES(?,?,?,?,?,?,'ACTIVE')", (key, namespace, tenant, principal, run_id, generation))
            db.execute("INSERT INTO container_operations(operation_id,run_key,name,generation,image,state) VALUES(?,?,?,?,?,'PREPARED')", (operation, key, name, generation, image))
        return self.get(operation)

    def get(self, operation):
        with self._tx() as db:
            row = db.execute('SELECT o.*,r.namespace,r.tenant,r.principal,r.run_id FROM container_operations o JOIN container_runs r USING(run_key) WHERE operation_id=?', (operation,)).fetchone()
            if not row:
                raise SwarmError('Unknown container operation')
            return dict(row)

    def _active_transition(self, operation, before, after):
        with self._tx() as db:
            changed = db.execute('''UPDATE container_operations SET state=?,updated_at=CURRENT_TIMESTAMP
                WHERE operation_id=? AND state=? AND EXISTS(SELECT 1 FROM container_runs r
                WHERE r.run_key=container_operations.run_key AND r.state='ACTIVE'
                  AND r.generation=container_operations.generation)''', (after, operation, before)).rowcount
            if changed != 1:
                raise SwarmError('Container authority revoked or stale; launch denied')

    def begin_create(self, operation):
        self._active_transition(operation, 'PREPARED', 'CREATING')

    def begin_start(self, operation):
        self._active_transition(operation, 'CREATED', 'STARTING')

    def confirm_create(self, operation, container_id):
        if not re.fullmatch(r'[0-9a-f]{64}', container_id):
            raise SwarmError('Invalid daemon container identity')
        with self._tx() as db:
            row = db.execute('SELECT * FROM container_operations WHERE operation_id=?', (operation,)).fetchone()
            if row['container_id'] and row['container_id'] != container_id:
                raise SwarmError('Container identity changed')
            if row['state'] == 'CLOSED':
                return
            # A late ACK never restores revoked start authority.
            state = 'CREATED' if row['state'] == 'CREATING' else 'CLEANUP_PENDING'
            db.execute('UPDATE container_operations SET container_id=?,create_confirmed=1,state=?,updated_at=CURRENT_TIMESTAMP WHERE operation_id=?', (container_id, state, operation))

    def retire(self, operation, *, uncertain=False):
        with self._tx() as db:
            row = db.execute('SELECT * FROM container_operations WHERE operation_id=?', (operation,)).fetchone()
            if row['state'] == 'CLOSED':
                return
            if uncertain:
                db.execute("UPDATE container_runs SET state='BLOCKED' WHERE run_key=?", (row['run_key'],))
            state = 'CLOSED' if row['state'] == 'PREPARED' else ('CLEANUP_PENDING' if row['create_confirmed'] else 'UNKNOWN_CREATE')
            db.execute('UPDATE container_operations SET state=?,updated_at=CURRENT_TIMESTAMP WHERE operation_id=?', (state, operation))

    def cancel_run(self, namespace, tenant, run_id):
        key = self.run_key(namespace, tenant, run_id)
        with self._tx() as db:
            db.execute("UPDATE container_runs SET state='BLOCKED' WHERE run_key=?", (key,))
            db.execute("UPDATE container_operations SET state=CASE WHEN state='PREPARED' THEN 'CLOSED' WHEN create_confirmed=1 THEN 'CLEANUP_PENDING' ELSE 'UNKNOWN_CREATE' END WHERE run_key=? AND state!='CLOSED'", (key,))

    def close(self, operation):
        with self._tx() as db:
            row = db.execute('SELECT * FROM container_operations WHERE operation_id=?', (operation,)).fetchone()
            if not row['create_confirmed'] and row['state'] != 'CLOSED':
                raise SwarmError('Empty snapshot cannot resolve an unacknowledged create')
            db.execute("UPDATE container_operations SET state='CLOSED',updated_at=CURRENT_TIMESTAMP WHERE operation_id=?", (operation,))

    def records(self, *, namespace=None, tenant=None, run_id=None, pending_only=False, limit=None):
        with self._tx() as db:
            clauses, args = [], []
            for field, value in [('namespace', namespace), ('tenant', tenant), ('run_id', run_id)]:
                if value is not None:
                    clauses.append('r.'+field+'=?')
                    args.append(value)
            if pending_only:
                clauses.append("o.state IN ('UNKNOWN_CREATE','CLEANUP_PENDING')")
            query = 'SELECT o.*,r.namespace,r.tenant,r.principal,r.run_id FROM container_operations o JOIN container_runs r USING(run_key)'
            query += (' WHERE '+' AND '.join(clauses) if clauses else '') + ' ORDER BY o.updated_at,o.operation_id'
            if limit is not None:
                if type(limit) is not int or not 1 <= limit <= 1000:
                    raise SwarmError('Invalid recovery batch limit')
                query += ' LIMIT ?'
                args.append(limit)
            rows = db.execute(query, args).fetchall()
            return [dict(row) for row in rows]


class DurableContainerOperation:
    def __init__(self, journal, docker, record):
        self.journal, self.docker, self.record = journal, docker, record
        self.operation = record['operation_id']
        self.name = record['name']

    @property
    def labels(self):
        return {'mas.runtime.controller': self.journal.controller,
                'mas.runtime.operation': self.operation,
                'mas.runtime.run': self.record['run_key'],
                'mas.runtime.generation': str(self.record['generation'])}

    async def _inspect(self):
        rc, out, _ = await self.docker('ps', '--all', '--quiet', '--no-trunc', '--filter', f'name=^/{self.name}$')
        if rc:
            raise SwarmError('Docker recovery authority unavailable')
        ids = out.decode().split()
        if not ids:
            return None
        if len(ids) != 1 or not re.fullmatch(r'[0-9a-f]{64}', ids[0]):
            raise SwarmError('Ambiguous recovery container identity')
        template = '{"Id":{{json .Id}},"Name":{{json .Name}},"Image":{{json .Image}},"Config":{"Labels":{{json .Config.Labels}}}}'
        rc, raw, _ = await self.docker('inspect', '--format', template, ids[0])
        if rc:
            status, remaining, _ = await self.docker('ps', '--all', '--quiet', '--filter', f'name=^/{self.name}$')
            if status == 0 and not remaining.strip():
                return None
            raise SwarmError('Recovery inspect unavailable')
        data = strict_json(raw)
        if not isinstance(data, dict):
            raise SwarmError('Invalid recovery inspection')
        info = data
        if info.get('Id') != ids[0] or info.get('Name') != '/'+self.name or info.get('Image') is None or any(
                ((info.get('Config') or {}).get('Labels') or {}).get(k) != v for k, v in self.labels.items()):
            raise SwarmError('Container ownership mismatch; refusing removal')
        expected_image = self.record['image']
        if not expected_image.startswith('sha256:'):
            rc, raw, _ = await self.docker('image', 'inspect', expected_image, '--format', '{{.Id}}')
            if rc:
                raise SwarmError('Recovery image identity unavailable')
            expected_image = raw.decode().strip()
        if info['Image'] != expected_image:
            raise SwarmError('Recovery image identity mismatch')
        current = self.journal.get(self.operation)
        if current['container_id'] and current['container_id'] != ids[0]:
            raise SwarmError('Container ID changed; refusing removal')
        return ids[0]

    async def create(self, args, authority_check=None):
        self._authorize(authority_check)
        self.journal.begin_create(self.operation)
        labels = [item for k, v in self.labels.items() for item in ('--label', k+'='+v)]
        creation = asyncio.create_task(self.docker('create', *labels, *args))
        try:
            try:
                rc, out, _ = await asyncio.shield(creation)
            except asyncio.CancelledError:
                self.journal.retire(self.operation, uncertain=True)
                # Join the bounded control call; if it times out the tombstone survives.
                rc, out, _ = await asyncio.shield(creation)
                if rc == 0:
                    self.journal.confirm_create(self.operation, out.decode().strip())
                raise
            if rc:
                raise SwarmError('Container creation not confirmed')
            self.journal.confirm_create(self.operation, out.decode().strip())
        except BaseException:
            self.journal.retire(self.operation, uncertain=True)
            raise

    def _authorize(self, authority_check):
        if authority_check:
            try:
                if authority_check() is False:
                    raise PermissionError('Denied')
            except PermissionError as exc:
                self.journal.retire(self.operation, uncertain=True)
                raise SwarmError('Container start authority unavailable') from exc

    def allow_start(self, authority_check=None):
        self._authorize(authority_check)
        self.journal.begin_start(self.operation)

    async def cleanup(self):
        self.journal.retire(self.operation)
        current = self.journal.get(self.operation)
        if current['state'] == 'CLOSED':
            return
        try:
            container = await self._inspect()
            if container:
                self.journal.confirm_create(self.operation, container)
                await self.docker('rm', '--force', container)
                # A competing janitor may already have removed this exact ID.
                # A successful daemon absence check, not rm's exit alone, is proof.
                if await self._inspect() is not None:
                    raise SwarmError('Owned container removal not confirmed')
            self.journal.close(self.operation)
        except BaseException:
            self.journal.retire(self.operation, uncertain=True)
            raise


async def reconcile_pending(journal, docker, *, namespace=None, tenant=None, run_id=None):
    """One conservative janitor pass; caller owns host recovery authority.

    Only retired journal records are processed. Absent unknown creates stay pending.
    Repeated passes are necessary; neither this method nor a quiet period settles funding.
    """
    outcomes = []
    for record in journal.records(namespace=namespace, tenant=tenant, run_id=run_id, pending_only=True, limit=100):
        operation = DurableContainerOperation(journal, docker, record)
        try:
            await operation.cleanup()
            outcome = 'CLOSED'
        except (OSError, TimeoutError, SwarmError):
            outcome = 'UNRESOLVED'
        outcomes.append({'operation_id': record['operation_id'], 'state': outcome})
    return outcomes
