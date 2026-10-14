#!/usr/bin/env python3
"""Offline delivery manifest and artifact validator CLI.

Validates candidate manifests, artifact archives, Git diffs, and coordinator DB state.
Defaults to validation-only mode; publication requires --publish and authenticated authority.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from mas.pm.db import PMDatabase
from mas.pm.delivery import DeliveryGateError, DeliveryService
from mas.pm.delivery_validator import (
    DeliveryValidatorError,
    publish_submission,
    validate_delivery_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline delivery manifest and artifact validator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--manifest", required=True, type=Path, help="Path to delivery manifest JSON")
    parser.add_argument("--archive", required=True, type=Path, help="Path to evidence zip archive")
    parser.add_argument("--repo", required=True, type=Path, help="Path to trusted Git repository root")
    parser.add_argument("--db", required=True, type=Path, help="Path to coordinator SQLite database file")
    parser.add_argument("--publish", action="store_true", default=False, help="Publish validated submission via DeliveryService.submit")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    for path_arg, desc in (
        (args.manifest, "Manifest file"),
        (args.archive, "Archive file"),
        (args.repo, "Git repository"),
        (args.db, "Database file"),
    ):
        if not path_arg.exists():
            out = {
                "status": "VALIDATION_FAILED",
                "valid": False,
                "reasons": [f"{desc} not found: {path_arg}"],
            }
            print(json.dumps(out, indent=2))
            return 1

    try:
        manifest_bytes = args.manifest.read_bytes()
    except Exception as exc:
        out = {
            "status": "VALIDATION_FAILED",
            "valid": False,
            "reasons": [f"Failed to read manifest file: {exc}"],
        }
        print(json.dumps(out, indent=2))
        return 1

    try:
        conn = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except Exception as exc:
        out = {
            "status": "VALIDATION_FAILED",
            "valid": False,
            "reasons": [f"Failed to open database in read-only mode: {exc}"],
        }
        print(json.dumps(out, indent=2))
        return 1

    try:
        with conn:
            result = validate_delivery_manifest(
                manifest_input=manifest_bytes,
                archive_input=args.archive,
                repo_path=args.repo,
                conn=conn,
            )
    finally:
        conn.close()

    if not result.valid:
        out = {
            "status": "VALIDATION_FAILED",
            "valid": False,
            "issue_id": result.issue_id,
            "candidate_sha": result.candidate_sha,
            "revision": result.revision,
            "reasons": result.reasons,
        }
        print(json.dumps(out, indent=2))
        return 1

    if not args.publish:
        out = {
            "status": "VALIDATED_CLAIMS",
            "valid": True,
            "issue_id": result.issue_id,
            "candidate_sha": result.candidate_sha,
            "revision": result.revision,
            "run_id": result.run_id,
            "reasons": [],
        }
        print(json.dumps(out, indent=2))
        return 0

    # Publish mode: requires PMDatabase and active authority
    try:
        db = PMDatabase(args.db)
        service = DeliveryService(db)
        task = publish_submission(service, result)
        out = {
            "status": task.get("phase", "UNKNOWN"),
            "valid": True,
            "published": True,
            "issue_id": task.get("issue_id", result.issue_id),
            "candidate_sha": result.candidate_sha,
            "revision": task.get("revision", result.revision),
            "reasons": [],
        }
        print(json.dumps(out, indent=2))
        return 0
    except (DeliveryGateError, DeliveryValidatorError, PermissionError) as exc:
        out = {
            "status": "PUBLICATION_FAILED",
            "valid": True,
            "published": False,
            "issue_id": result.issue_id,
            "candidate_sha": result.candidate_sha,
            "revision": result.revision,
            "reasons": [str(exc)],
        }
        print(json.dumps(out, indent=2))
        return 1
    except Exception as exc:
        out = {
            "status": "PUBLICATION_ERROR",
            "valid": True,
            "published": False,
            "issue_id": result.issue_id,
            "reasons": [f"Unexpected error during submission publication: {exc}"],
        }
        print(json.dumps(out, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
