#!/usr/bin/env python3
"""Offline delivery manifest and artifact validator CLI.

Performs pure offline claims validation of candidate manifests, artifact archives,
and Git commit trees.
Does NOT accept arbitrary database paths and does NOT perform unauthenticated state mutation.
Publication belongs exclusively to the authenticated coordinator SDK.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mas.pm.delivery_validator import (
    MAX_ARCHIVE_COMPRESSED_SIZE,
    MAX_MANIFEST_JSON_SIZE,
    parse_manifest_json,
    read_file_bounded,
    validate_artifact_archive,
    validate_git_candidate,
    validate_manifest_input,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline delivery manifest and artifact claims validator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--manifest", required=True, type=Path, help="Path to delivery manifest JSON")
    parser.add_argument("--archive", required=True, type=Path, help="Path to evidence zip archive")
    parser.add_argument("--repo", required=True, type=Path, help="Path to trusted Git repository root")
    parser.add_argument(
        "--scope",
        required=False,
        default="",
        help="Optional comma-separated list of allowed relative file paths for scope validation",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Validate file existence
    for path_arg, desc in (
        (args.manifest, "Manifest file"),
        (args.archive, "Archive file"),
        (args.repo, "Git repository"),
    ):
        if not path_arg.exists():
            out = {
                "status": "VALIDATION_FAILED",
                "valid": False,
                "reasons": [f"{desc} not found: {path_arg}"],
            }
            print(json.dumps(out, indent=2))
            return 1

    # 1. Read and strictly revalidate manifest
    try:
        manifest_bytes = read_file_bounded(args.manifest, MAX_MANIFEST_JSON_SIZE)
        manifest_dict = parse_manifest_json(manifest_bytes)
        manifest = validate_manifest_input(manifest_dict)
    except Exception as exc:
        out = {
            "status": "VALIDATION_FAILED",
            "valid": False,
            "reasons": [f"Manifest validation error: {exc}"],
        }
        print(json.dumps(out, indent=2))
        return 1

    # 2. Read and strictly validate artifact archive and observation links
    try:
        archive_bytes = read_file_bounded(args.archive, MAX_ARCHIVE_COMPRESSED_SIZE)
        validate_artifact_archive(archive_bytes, observations=manifest.observations)
    except Exception as exc:
        out = {
            "status": "VALIDATION_FAILED",
            "valid": False,
            "issue_id": manifest.issue_id,
            "candidate_sha": manifest.candidate_sha,
            "reasons": [f"Artifact archive validation error: {exc}"],
        }
        print(json.dumps(out, indent=2))
        return 1

    # 3. Validate Git candidate commit and diff-tree
    try:
        scope = [s.strip() for s in args.scope.split(",") if s.strip()] if args.scope else []
        if not scope and manifest.closures:
            # Flatten closure paths as scope if no explicit scope passed
            for paths in manifest.closures.values():
                scope.extend(paths)
        validate_git_candidate(args.repo, manifest.base_sha, manifest.candidate_sha, scope)
    except Exception as exc:
        out = {
            "status": "VALIDATION_FAILED",
            "valid": False,
            "issue_id": manifest.issue_id,
            "candidate_sha": manifest.candidate_sha,
            "reasons": [f"Git candidate validation error: {exc}"],
        }
        print(json.dumps(out, indent=2))
        return 1

    # Pure claims validation passed
    out = {
        "status": "VALIDATED_CLAIMS",
        "valid": True,
        "issue_id": manifest.issue_id,
        "candidate_sha": manifest.candidate_sha,
        "brief_version": manifest.brief_version,
        "revision": manifest.revision,
        "run_id": manifest.run_id,
        "observations_count": len(manifest.observations),
        "authority_verified": False,
        "note": (
            "Offline claims validation successful. Authority and database binding must be "
            "verified by the coordinator or delivery service before admission."
        ),
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
