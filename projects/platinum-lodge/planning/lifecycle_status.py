#!/usr/bin/env python3
"""Report PLG readiness through MAS-PM public read APIs; never assign/transition."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def summarize(database, plan):
    project = database.get_project_by_key(plan['project_key'])
    if project is None:
        raise ValueError('PLG is missing in this database. Verify configured board/import first.')
    issues = {issue.key: issue for issue in database.list_issues(project.id)}
    result = {'project': project.key, 'record_count': len(issues),
              'states': dict(Counter(issue.current_state.value for issue in issues.values())),
              'note': 'Dependency clearance alone does not establish assignment, allowance, review or release readiness.',
              'epics': []}
    for epic in plan['epics']:
        packages = []
        for task in (t for t in plan['tasks'] if t['epic'] == epic['code']):
            issue = issues.get(task['key'])
            if issue is None:
                packages.append({'key': task['key'], 'state': 'MISSING', 'dependency_status': 'UNAVAILABLE'})
                continue
            blockers = database.get_dependencies(issue.key)
            unresolved = [b.key for b in blockers if b.current_state.value != 'DONE']
            packages.append({'key': issue.key, 'title': issue.title, 'state': issue.current_state.value,
                             'planning_owner': task['owner'], 'assignee': issue.assignee_principal,
                             'execution_allowance_tokens': issue.appetite_tokens,
                             'unresolved_blockers': unresolved,
                             'dependency_status': 'BLOCKED' if unresolved else 'CLEAR'})
        result['epics'].append({'key': epic['key'], 'code': epic['code'], 'gate': epic['gate'],
                                'packages': packages})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, help='Actual configured MAS-PM database; never guess a tenant path')
    args = parser.parse_args()
    from mas.pm.db import DEFAULT_DB_PATH
    from mas.pm.tools import get_pm_db
    from mas.tenancy import current_binding
    binding = current_binding()
    path = args.database or (binding.database if binding else Path(DEFAULT_DB_PATH))
    if not Path(path).is_file():
        parser.error('Database does not exist; no database was created. Verify the dashboard configuration.')
    plan = json.loads((Path(__file__).parent / 'BACKLOG.json').read_text())
    database = get_pm_db(str(path))  # Existing tenant checks remain enforced by the public API.
    report = summarize(database, plan)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
