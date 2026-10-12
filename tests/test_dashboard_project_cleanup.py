"""Reversible fixture cleanup must preserve real projects, work and evidence."""
from pathlib import Path

from mas.pm.db import PMDatabase
from mas.pm.models import Issue, Project
from scripts.cleanup_dashboard_projects import cleanup


def test_cleanup_archives_only_unused_fixtures_and_preserves_rows(tmp_path):
    path = tmp_path / 'pm.db'
    db = PMDatabase(path)
    for key in ('DP1', 'DP2', 'DP3', 'REAL'):
        db.create_project(Project(id=key, key=key, name='Dashboard Project'))
    db.create_issue(Issue(id='fixture', project_id='DP1', key='DP1-1', title='Board Test Issue'))
    db.create_issue(Issue(id='active', project_id='DP2', key='DP2-1', title='Board Test Issue', current_state='IN_PROGRESS'))
    db.create_issue(Issue(id='real', project_id='DP3', key='DP3-1', title='Customer work'))
    preview = cleanup(path)
    assert [p['key'] for p in preview['candidates']] == ['DP1']
    assert len(db.list_projects()) == 4
    applied = cleanup(path, apply=True)
    assert applied['archived'] == 1
    assert Path(applied['backup']).is_file()
    assert Path(applied['backup']).stat().st_mode & 0o077 == 0
    assert {p.key for p in db.list_projects()} == {'DP2', 'DP3', 'REAL'}
    assert len(db.list_projects(include_archived=True)) == 4
    assert db.get_issue('fixture').title == 'Board Test Issue'
    assert cleanup(path, apply=True)['archived'] == 0
    # Reversible archival: removing the marker restores visibility, no data import needed.
    with db.atomic_transaction() as conn:
        conn.execute('DELETE FROM pm_project_archives WHERE project_id=?', ('DP1',))
    assert len(db.list_projects()) == 4
