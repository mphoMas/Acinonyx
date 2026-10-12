#!/usr/bin/env python3
"""Archive unused dashboard test fixtures; never delete projects or tickets.

Dry run by default. --apply makes a private SQLite backup first.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sqlite3


def candidates(conn):
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    found = []
    for project in conn.execute("SELECT id,key,name FROM pm_projects"):
        pid, key, name = project
        if name != 'Dashboard Project' or not re.fullmatch(r'DP[0-9]{1,5}', key):
            continue
        if 'pm_project_archives' in tables and conn.execute('SELECT 1 FROM pm_project_archives WHERE project_id=?', (pid,)).fetchone():
            continue
        protected = False
        for table in ('pm_project_sources', 'pm_plans', 'pm_task_mappings', 'pm_sprints', 'pm_coordinator_attempts'):
            if table in tables and conn.execute(f'SELECT 1 FROM {table} WHERE project_id=? LIMIT 1', (pid,)).fetchone():
                protected = True
        issues = conn.execute('SELECT id,title,current_state,assignee_principal,tokens_spent FROM pm_issues WHERE project_id=?', (pid,)).fetchall()
        if len(issues) > 1:
            protected = True
        for issue in issues:
            iid, title, state, assignee, spent = issue
            if title != 'Board Test Issue' or state != 'BACKLOG' or assignee or spent:
                protected = True
            for table in ('pm_evidence_links', 'pm_critic_verdicts'):
                if table in tables and conn.execute(f'SELECT 1 FROM {table} WHERE issue_id=? LIMIT 1', (iid,)).fetchone():
                    protected = True
            if 'pm_dependencies' in tables and conn.execute('SELECT 1 FROM pm_dependencies WHERE blocker_id=? OR blocked_id=? LIMIT 1', (iid, iid)).fetchone():
                protected = True
        if not protected:
            found.append({'id': pid, 'key': key, 'name': name, 'issue_count': len(issues)})
    return found


def cleanup(db_path, apply=False):
    path = Path(db_path).resolve()
    if not path.is_file():
        raise ValueError(f'Database does not exist: {path}')
    conn = sqlite3.connect(f'{path.as_uri()}?mode=rw', uri=True, timeout=5)
    try:
        selected = candidates(conn)
        result = {'database': str(path), 'apply': apply, 'candidates': selected, 'archived': 0}
        if not apply or not selected:
            return result
        backup_path = path.with_name(path.name + '.before-fixture-cleanup-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.bak')
        fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with sqlite3.connect(backup_path) as backup:
            conn.backup(backup)
        conn.execute('BEGIN IMMEDIATE')
        try:
            # Re-evaluate eligibility under the write lock.
            selected = candidates(conn)
            conn.execute('CREATE TABLE IF NOT EXISTS pm_project_archives(project_id TEXT PRIMARY KEY, reason TEXT NOT NULL, archived_at TEXT NOT NULL)')
            now = datetime.now(timezone.utc).isoformat()
            conn.executemany('INSERT INTO pm_project_archives(project_id,reason,archived_at) VALUES(?,?,?)',
                             [(p['id'], 'unused_dashboard_test_fixture', now) for p in selected])
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        result.update(candidates=selected, archived=len(selected), backup=str(backup_path))
        return result
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, help='Exact database used by the dashboard')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(cleanup(args.db, args.apply), indent=2))
