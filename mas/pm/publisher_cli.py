"""
mas.pm.publisher_cli: Command-line tool for publishing plans into MAS-PM.
Enables architects and operators to publish plans directly from structured JSON or YAML files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from mas.pm.client import PlanPublisherClient
from mas.pm.plans import PlanError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish a structured conversation-derived plan into MAS-PM."
    )
    parser.add_argument(
        "--project",
        "-p",
        required=True,
        help="Project ID or Key (e.g. SBA, PLG, or UUID)",
    )
    parser.add_argument(
        "--plan-file",
        "-f",
        required=True,
        help="Path to plan JSON file (or '-' for stdin)",
    )
    parser.add_argument(
        "--idempotency-key",
        "-k",
        help="Optional idempotency key (reuses cached result on identical payload)",
    )
    parser.add_argument(
        "--server-url",
        default=os.environ.get("MAS_SERVER_URL", "http://127.0.0.1:8000"),
        help="MAS server URL (default: http://127.0.0.1:8000 or $MAS_SERVER_URL)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("MAS_AUTH_TOKEN"),
        help="Bearer authentication token (or $MAS_AUTH_TOKEN)",
    )
    parser.add_argument(
        "--tenant",
        default=os.environ.get("MAS_TENANT_ID", "default"),
        help="Tenant ID (default: default or $MAS_TENANT_ID)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    # Load plan content
    if args.plan_file == "-":
        plan_content = sys.stdin.read()
    else:
        plan_path = Path(args.plan_file)
        if not plan_path.exists():
            print(f"Error: Plan file not found: {plan_path}", file=sys.stderr)
            return 1
        plan_content = plan_path.read_text(encoding="utf-8")

    try:
        plan_data = json.loads(plan_content)
    except Exception as e:
        print(f"Error parsing plan JSON: {e}", file=sys.stderr)
        return 1

    client = PlanPublisherClient(
        base_url=args.server_url,
        auth_token=args.token,
        tenant_id=args.tenant,
    )

    try:
        response = client.publish_plan(
            project_id_or_key=args.project,
            plan=plan_data,
            idempotency_key=args.idempotency_key,
        )

        if args.json:
            print(json.dumps(response.model_dump(), indent=2))
        else:
            print("==================================================")
            print("MAS-PM Plan Published Successfully")
            print("==================================================")
            print(f"Project:      {response.project_key} ({response.project_id})")
            print(f"Plan ID:      {response.plan_id}")
            print(f"Revision:     {response.revision}")
            print(f"Commit Ref:   {response.source_commit or 'None'}")
            print(f"Scope Ref:    {response.scope_reference or 'None'}")
            print(f"Tasks:        {response.tasks_created} created, {response.tasks_updated} updated")
            print(f"Board Cursor: {response.board_cursor}")
            print("--------------------------------------------------")
            print("Issue Mappings:")
            for m in response.mappings:
                print(f"  [{m.planning_reference}] {m.task_id} -> {m.local_issue_key} ({m.local_issue_id})")

            if response.changes_requiring_reconciliation:
                print("--------------------------------------------------")
                print("WARNING: Changes Requiring Reconciliation:")
                for r in response.changes_requiring_reconciliation:
                    print(f"  * {r.issue_key} ({r.current_state}): {r.change_type} - {r.description}")
            print("==================================================")

        return 0

    except PlanError as e:
        print(f"Plan Publication Error [{e.code}]: {e.message}", file=sys.stderr)
        return 2
    except PermissionError as e:
        print(f"Authentication/Authorization Error: {e}", file=sys.stderr)
        return 3
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    sys.exit(main())
