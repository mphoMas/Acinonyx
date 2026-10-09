"""Import the approved planning snapshot through MAS-PM APIs; never dispatch work.

Run from the target repository root. Default is a read-only preview against an
existing DB; --apply creates only missing project/issues/dependency edges.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from mas.pm.tools import get_pm_db, pm_create_issue, pm_create_project


def validate(data):
    if data.get('schema_version') != 1 or data.get('project_key') != 'PLG':
        raise ValueError('Unexpected planning snapshot')
    records = data['records']
    bykey = {r['source_key']: r for r in records}
    if len(bykey) != len(records) or len({r['title'] for r in records}) != len(records):
        raise ValueError('Duplicate planning reference or title')
    visiting, visited = set(), set()
    def visit(key):
        if key in visiting:
            raise ValueError('Cyclic planning dependencies')
        if key in visited:
            return
        if key not in bykey:
            raise ValueError('Unknown planning reference')
        visiting.add(key)
        r = bykey[key]
        for dep in r['dependencies'] + ([r['parent_source_key']] if r['parent_source_key'] else []):
            visit(dep)
        visiting.remove(key)
        visited.add(key)
    for r in records:
        if r['appetite_tokens'] != 0:
            raise ValueError('Planning import cannot allocate execution tokens')
        for path in r['path_whitelist'] + r['forbidden_paths']:
            if Path(path).is_absolute() or '..' in Path(path).parts:
                raise ValueError('Unsafe file scope')
        visit(r['source_key'])
    return records


def sync(data, *, db, apply=False):
    records = validate(data)
    project = db.get_project_by_key(data['project_key'])
    if project and project.name != data['project_name']:
        raise ValueError('PLG already identifies a different project; refusing import')
    issues = db.list_issues(project.id) if project else []
    found = {}
    # Resolve every existing identity before performing any mutations.
    for r in records:
        matches = [i for i in issues if i.title == r['title'] or
                   f"[PLG_PLAN_REF:{r['source_key']}]" in i.description]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous existing record: {r['source_key']}")
        if matches:
            i = matches[0]
            if i.issue_type.value != r['issue_type']:
                raise ValueError(f"Existing type differs: {i.key}")
            found[r['source_key']] = i
    source_by_id = {i.id: k for k, i in found.items()}
    for r in records:
        if r['source_key'] in found:
            i = found[r['source_key']]
            if source_by_id.get(i.parent_id) != r['parent_source_key']:
                raise ValueError(f"Existing hierarchy differs: {i.key}")
    if not apply:
        return {'mode': 'PREVIEW', 'project': data['project_key'],
                'missing_records': [r['source_key'] for r in records if r['source_key'] not in found],
                'existing_records': len(found), 'planned_edges': sum(len(r['dependencies']) for r in records)}
    if not project:
        pm_create_project(data['project_key'], data['project_name'],
                          data['project_description'], token_budget=0, db=db)
    created = []
    pending = [r for r in records if r['source_key'] not in found]
    while pending:
        ready = [r for r in pending if not r['parent_source_key'] or r['parent_source_key'] in found]
        if not ready:
            raise ValueError('Cannot resolve planning hierarchy')
        for r in ready:
            result = pm_create_issue(
                data['project_key'], r['title'],
                r['description'] + f"\n[PLG_PLAN_REF:{r['source_key']}]",
                issue_type=r['issue_type'], priority=r['priority'],
                parent_key=found[r['parent_source_key']].key if r['parent_source_key'] else None,
                assignee_principal=None, appetite_tokens=0,
                appetite_timeout_s=r['appetite_timeout_s'],
                path_whitelist=r['path_whitelist'], forbidden_paths=r['forbidden_paths'], db=db)
            found[r['source_key']] = db.get_issue(result['issue_key'])
            created.append(result['issue_key'])
            pending.remove(r)
    added_edges = 0
    for r in records:
        issue = found[r['source_key']]
        existing_edges = {d.id for d in db.get_dependencies(issue.key)}
        for dep in r['dependencies']:
            if found[dep].id not in existing_edges:
                db.add_dependency(found[dep].key, issue.key)
                added_edges += 1
    return {'mode': 'APPLIED', 'project': data['project_key'], 'created': created,
            'added_dependencies': added_edges, 'mapped_records': len(found),
            'key_mapping': {k: i.key for k, i in found.items()},
            'preserved_existing_state_assignees_evidence': True,
            'new_records': 'BACKLOG, no runtime assignee, zero execution appetite'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--database', type=Path, default=ROOT / 'mas_pm.db')
    args = parser.parse_args()
    data = json.loads(Path(__file__).with_name('BOARD_RECORDS.json').read_text())
    validate(data)
    # Do not create a database merely to preview a new desktop installation.
    if not args.apply and not args.database.exists():
        print(json.dumps({'mode': 'PREVIEW', 'project': 'PLG', 'database_exists': False,
                          'missing_records': len(data['records']),
                          'planned_edges': sum(len(r['dependencies']) for r in data['records'])}, indent=2))
        return
    print(json.dumps(sync(data, db=get_pm_db(str(args.database)), apply=args.apply), indent=2))


if __name__ == '__main__':
    main()
