#!/usr/bin/env python3
"""Preview/attach published delivery references through MAS-PM, preserving FSM/state."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, help='Actual configured dashboard database')
    parser.add_argument('--apply', action='store_true', help='Attach missing references only; never approve/transition')
    args = parser.parse_args()
    from mas.pm.db import DEFAULT_DB_PATH
    from mas.pm.tools import get_pm_db, pm_attach_evidence
    from mas.tenancy import current_binding
    binding = current_binding()
    path = args.database or (binding.database if binding else Path(DEFAULT_DB_PATH))
    if not Path(path).is_file():
        parser.error('Database missing; verify board configuration. No database created.')
    db = get_pm_db(str(path))
    directory = Path(__file__).parent
    manifest = json.loads((directory / 'DELIVERY_EVIDENCE_LINKS.json').read_text())
    snapshot = json.loads((directory / 'BOARD_RECORDS.json').read_text())
    project = db.get_project_by_key(manifest['project'])
    if not project:
        parser.error('Project missing; reconcile the planning import first.')
    issues = db.list_issues(project.id)
    records = {r['source_key']: r for r in snapshot['records']}
    pending = []
    # Resolve the entire mapping before any mutation; numeric keys alone are not identity.
    for entry in manifest['entries']:
        record = records[entry['source_key']]
        matches = [i for i in issues if i.title == record['title'] or
                   f"[PLG_PLAN_REF:{entry['source_key']}]" in i.description]
        if len(matches) != 1 or matches[0].issue_type.value != record['issue_type']:
            parser.error(f"Missing/ambiguous identity for {entry['source_key']}; reconcile import mapping first.")
        issue = matches[0]
        if not any(e.uri == entry['uri'] and e.content_hash == entry['content_hash']
                   for e in db.get_evidence_links(issue.id)):
            pending.append((issue, entry))
    attached = 0
    if args.apply:
        for issue, entry in pending:
            try:
                pm_attach_evidence(issue.key, entry['evidence_type'], entry['content_hash'], entry['uri'],
                                   payload={**entry['payload'], 'source_key': entry['source_key']}, db=db)
            except (ValueError, PermissionError) as error:
                parser.error(f'Attachment stopped after {attached} links: {error}. Configure authorized governance through normal runtime setup; no bypass performed.')
            attached += 1
    print(json.dumps({'mode':'APPLY' if args.apply else 'PREVIEW','missing_links':len(pending),
                      'attached':attached,'issue_states_or_assignments_changed':False},indent=2))


if __name__ == '__main__':
    main()
