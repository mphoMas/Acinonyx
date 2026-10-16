"""Trusted candidate export and compare-and-swap Git integration (CC-09 P2).

Implements mas-candidate-integration-v1:
- Guests produce bounded WRITE/DELETE file proposals, never trusted commit claims.
- Trusted host exporter constructs Git blobs, trees, and commits using an isolated
  GIT_INDEX_FILE without touching the operator's working tree or running hooks.
- Compare-and-swap (CAS) target ref integration requires current verification,
  independent review, and separate human/policy authorization bound to the exact
  candidate commit SHA.
"""
from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mas.pm.adapters.broker import migrate_live_loop
from mas.pm.adapters.verifier import BINDING_FIELDS, SCHEMA, resolve_commit, verify_signature
from mas.swarm.contracts import canonical, digest, strict_json
from mas.swarm.process import run_process

CANDIDATE_SCHEMA = "mas-candidate-integration-v1"
MAX_EXPORT_FILES = 256
MAX_EXPORT_BYTES = 2 * 1024 * 1024  # 2 MiB
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
SHA40_RE = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_SEGMENTS = frozenset({
    ".git", ".ssh", ".aws", ".codex", ".env", ".mas-runtime", "__pycache__",
})
FORBIDDEN_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore")
FORBIDDEN_FILENAMES = frozenset({"id_rsa", "id_ed25519", "id_ecdsa", ".env", ".netrc"})
FRONTEND_PREFIXES = ("portal/", "frontend/", "ui/")


class CandidateIntegrationError(RuntimeError):
    """Deterministic error raised during candidate export or CAS Git integration."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _run_git(
    repo_root: Path,
    args: list[str],
    *,
    data: bytes = b"",
    extra_env: dict[str, str] | None = None,
    timeout: float = 15.0,
    output_limit: int = 65536,
) -> tuple[int, bytes, bytes]:
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "LANG": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    if extra_env:
        env.update(extra_env)
    cmd = [
        "git",
        "-C",
        str(repo_root),
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "credential.helper=",
        *args,
    ]
    return asyncio.run(run_process(cmd, data=data, timeout=timeout, output_limit=output_limit, env=env))


def _validate_candidate_path(
    raw_path: Any,
    *,
    path_whitelist: list[str],
    forbidden_paths: list[str],
    oracle_paths: set[str],
    runtime_type: str,
    allow_frontend: bool = False,
) -> str:
    if not isinstance(raw_path, str) or not raw_path or "\x00" in raw_path or "\\" in raw_path:
        raise CandidateIntegrationError("INVALID_PATH", "Path must be a non-empty POSIX string without backslashes")
    if raw_path.startswith("/") or raw_path.endswith("/"):
        raise CandidateIntegrationError("INVALID_PATH", "Absolute or directory-trailing paths are forbidden")
    p = Path(raw_path)
    parts = p.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise CandidateIntegrationError("INVALID_PATH", "Traversal or ambiguous path segments are forbidden")
    for part in parts:
        if part in FORBIDDEN_SEGMENTS or part.startswith(".env."):
            raise CandidateIntegrationError("FORBIDDEN_PATH", f"Credential or control segment '{part}' is forbidden")
    filename = parts[-1]
    if filename in FORBIDDEN_FILENAMES or filename.lower().endswith(FORBIDDEN_SUFFIXES):
        raise CandidateIntegrationError("FORBIDDEN_PATH", f"Key store or credential file '{filename}' is forbidden")

    norm = p.as_posix()
    if norm in oracle_paths:
        raise CandidateIntegrationError("ORACLE_PROTECTED", f"Path '{norm}' is an external verification oracle")

    # Enforce delivery ownership boundary (Antigravity cannot self-expand into Codex frontend paths)
    if runtime_type == "antigravity" and not allow_frontend:
        if any(norm.startswith(prefix) for prefix in FRONTEND_PREFIXES):
            raise CandidateIntegrationError(
                "SCOPE_VIOLATION",
                f"Antigravity runtime cannot modify Codex-owned frontend path '{norm}'",
            )

    # Check forbidden_paths
    for forb in forbidden_paths:
        forb_norm = forb.strip("/")
        if norm == forb_norm or norm.startswith(forb_norm + "/"):
            raise CandidateIntegrationError("FORBIDDEN_PATH", f"Path '{norm}' is in forbidden_paths")

    # Check admitted path_whitelist
    if not path_whitelist:
        raise CandidateIntegrationError("SCOPE_VIOLATION", "Task has empty path_whitelist")
    allowed = False
    for allow_entry in path_whitelist:
        allow_norm = allow_entry.strip("/")
        if norm == allow_norm or norm.startswith(allow_norm + "/"):
            allowed = True
            break
    if not allowed:
        raise CandidateIntegrationError("SCOPE_VIOLATION", f"Path '{norm}' is outside admitted path_whitelist")

    return norm


def _read_base_tree_entries(repo_root: Path, base_commit_sha: str) -> dict[str, tuple[str, str, str]]:
    """Returns mapping of path -> (mode, obj_type, sha) for the entire base commit tree."""
    code, out, err = _run_git(
        repo_root,
        ["ls-tree", "-r", "--full-tree", base_commit_sha],
        output_limit=65536,
    )
    if code != 0:
        raise CandidateIntegrationError("INVALID_BASE", f"Unable to inspect base tree: {err.decode(errors='replace')}")
    entries: dict[str, tuple[str, str, str]] = {}
    for line in out.decode("utf-8").splitlines():
        if not line.strip():
            continue
        meta, path = line.split("\t", 1)
        mode, obj_type, sha = meta.split(" ")
        entries[path] = (mode, obj_type, sha)
    return entries


@dataclass(frozen=True)
class CandidateExporter:
    """Trusted host service that builds immutable Git candidates and performs CAS ref integration."""
    db: Any
    repo_root: Path
    repo_identity: str
    exporter_id: str = "trusted-exporter"
    iam: Any = None
    allowed_target_refs: frozenset[str] = frozenset({"refs/heads/main"})
    protected_blocked_refs: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        migrate_live_loop(self.db)
        object.__setattr__(self, "repo_root", Path(self.repo_root).resolve(strict=True))

    def _verify_iam_principal(self, iam_token: str | None, expected_principal: str, tenant_id: str, action: str) -> None:
        if self.iam is None:
            return
        if not iam_token:
            raise CandidateIntegrationError("AUTHORITY_DENIED", "Missing IAM session token")
        try:
            ctx = self.iam.verify_token(iam_token)
            if (
                ctx.principal_id != expected_principal
                or ctx.tenant_id != tenant_id
                or not self.iam.authorize(
                    ctx,
                    action,
                    tenant_id,
                    f"urn:mas:tenant:{tenant_id}:coordinator:candidate",
                )
            ):
                raise CandidateIntegrationError("AUTHORITY_DENIED", f"Principal '{expected_principal}' lacks '{action}'")
        except CandidateIntegrationError:
            raise
        except Exception as exc:
            raise CandidateIntegrationError("AUTHORITY_DENIED", f"IAM session verification failed: {exc}") from exc

    def export_candidate(
        self,
        *,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_id: str,
        run_id: str,
        fencing_token: int,
        builder_id: str,
        proposal: dict[str, Any] | str | bytes,
        iam_token: str | None = None,
        oracle_paths: set[str] | None = None,
        allow_frontend: bool = False,
    ) -> dict[str, Any]:
        """Validates a mas-candidate-integration-v1 proposal and creates an immutable Git commit."""
        self._verify_iam_principal(iam_token, builder_id, tenant_id, "coordinator:candidate:export")

        if isinstance(proposal, (str, bytes)):
            try:
                parsed = strict_json(proposal)
            except Exception as exc:
                raise CandidateIntegrationError("INVALID_PROPOSAL", f"Invalid JSON proposal: {exc}") from exc
        elif isinstance(proposal, dict):
            parsed = strict_json(canonical(proposal))
        else:
            raise CandidateIntegrationError("INVALID_PROPOSAL", "Proposal must be a JSON object")

        if not isinstance(parsed, dict) or set(parsed.keys()) != {
            "schema",
            "proposal_id",
            "base_commit_sha",
            "files",
        }:
            raise CandidateIntegrationError(
                "INVALID_PROPOSAL",
                "Proposal must contain exact mas-candidate-integration-v1 keys",
            )
        if parsed["schema"] != CANDIDATE_SCHEMA:
            raise CandidateIntegrationError("INVALID_PROPOSAL", "Unsupported candidate integration schema")

        proposal_id = parsed["proposal_id"]
        if not isinstance(proposal_id, str) or not UUID_RE.fullmatch(proposal_id):
            raise CandidateIntegrationError("INVALID_PROPOSAL", "proposal_id must be a valid lowercase UUID")

        base_commit_sha = parsed["base_commit_sha"]
        if not isinstance(base_commit_sha, str) or not SHA40_RE.fullmatch(base_commit_sha):
            raise CandidateIntegrationError("INVALID_BASE", "base_commit_sha must be a 40-character hex SHA")

        try:
            resolve_commit(self.repo_root, base_commit_sha)
        except ValueError as exc:
            raise CandidateIntegrationError("INVALID_BASE", str(exc)) from exc

        files = parsed["files"]
        if not isinstance(files, list) or not 1 <= len(files) <= MAX_EXPORT_FILES:
            raise CandidateIntegrationError("INVALID_PROPOSAL", "files must be a non-empty list of at most 256 items")

        # Compute canonical proposal digest for idempotency
        proposal_digest = digest({
            "schema": CANDIDATE_SCHEMA,
            "proposal_id": proposal_id,
            "base_commit_sha": base_commit_sha,
            "files": files,
            "attempt_id": attempt_id,
            "run_id": run_id,
            "fencing_token": fencing_token,
            "builder_id": builder_id,
        })

        # Step 1: Validate coordinator attempt/run/issue authority & check idempotency
        with self.db.atomic_transaction() as conn:
            existing = conn.execute(
                "SELECT * FROM pm_coordinator_candidate_exports WHERE proposal_id = ?",
                (proposal_id,),
            ).fetchone()
            if existing is not None:
                if existing["proposal_digest"] != proposal_digest:
                    raise CandidateIntegrationError(
                        "CONFLICTING_REPLAY",
                        "Changed proposal content or binding under existing proposal_id",
                    )
                return strict_json(existing["receipt_json"])

            row = conn.execute(
                """
                SELECT a.tenant_id, a.project_id, a.issue_id, a.task_id, a.status AS attempt_status,
                       r.status AS run_status, r.fencing_token AS run_fence,
                       i.adapter_type, i.status AS intent_status, i.fencing_token AS intent_fence,
                       q.policy_version, q.has_pending_reconciliation, q.path_whitelist, q.forbidden_paths
                FROM pm_coordinator_runs r
                JOIN pm_coordinator_attempts a ON a.attempt_id = r.attempt_id
                JOIN pm_coordinator_intents i ON i.intent_id = r.intent_id AND i.attempt_id = a.attempt_id
                JOIN pm_issues q ON q.id = a.issue_id AND q.project_id = a.project_id
                WHERE r.run_id = ? AND a.attempt_id = ?
                """,
                (run_id, attempt_id),
            ).fetchone()
            if not row:
                raise CandidateIntegrationError("AUTHORITY_DENIED", "Run or attempt ownership not found")
            if (
                row["tenant_id"] != tenant_id
                or row["project_id"] != project_id
                or row["issue_id"] != issue_id
                or row["task_id"] != task_id
            ):
                raise CandidateIntegrationError("AUTHORITY_DENIED", "Coordinator ownership mismatch")
            if row["run_fence"] != fencing_token or row["intent_fence"] != fencing_token:
                raise CandidateIntegrationError("STALE_GENERATION", "Fencing token is stale")
            if row["has_pending_reconciliation"]:
                raise CandidateIntegrationError("POLICY_CHANGED", "Issue has pending policy reconciliation")
            if row["intent_status"] in {"CANCELED", "CANCEL_REQUESTED"} or row["attempt_status"] == "CANCELED":
                raise CandidateIntegrationError("AUTHORITY_DENIED", "Attempt or intent is canceled")

            policy_version = int(row["policy_version"])
            runtime_type = str(row["adapter_type"])
            path_whitelist = json.loads(row["path_whitelist"]) if row["path_whitelist"] else []
            forbidden_paths = json.loads(row["forbidden_paths"]) if row["forbidden_paths"] else []

        # Step 2: Inspect base tree and validate all file entries and byte limits
        base_entries = _read_base_tree_entries(self.repo_root, base_commit_sha)
        base_lower_map = {k.lower(): k for k in base_entries}

        seen_paths: set[str] = set()
        seen_lower: set[str] = set()
        decoded_operations: list[tuple[str, str, bytes | None]] = []
        total_decoded_bytes = 0
        artifact_hasher = hashlib.sha256()

        for item in files:
            if not isinstance(item, dict) or set(item.keys()) != {
                "path",
                "operation",
                "expected_base_blob_sha",
                "content_base64",
            }:
                raise CandidateIntegrationError(
                    "INVALID_PROPOSAL",
                    "Each file entry must contain exact keys {'path', 'operation', 'expected_base_blob_sha', 'content_base64'}",
                )
            norm_path = _validate_candidate_path(
                item["path"],
                path_whitelist=path_whitelist,
                forbidden_paths=forbidden_paths,
                oracle_paths=oracle_paths or set(),
                runtime_type=runtime_type,
                allow_frontend=allow_frontend,
            )
            lower_path = norm_path.lower()
            if norm_path in seen_paths or lower_path in seen_lower:
                raise CandidateIntegrationError(
                    "DUPLICATE_OR_ALIAS_PATH",
                    f"Duplicate or case-alias path '{norm_path}' in proposal",
                )
            if lower_path in base_lower_map and base_lower_map[lower_path] != norm_path:
                raise CandidateIntegrationError(
                    "DUPLICATE_OR_ALIAS_PATH",
                    f"Path '{norm_path}' collides by case with existing path '{base_lower_map[lower_path]}'",
                )
            seen_paths.add(norm_path)
            seen_lower.add(lower_path)

            op = item["operation"]
            if op not in {"WRITE", "DELETE"}:
                raise CandidateIntegrationError("INVALID_OPERATION", "operation must be 'WRITE' or 'DELETE'")

            expected_blob = item["expected_base_blob_sha"]
            if expected_blob is not None and (
                not isinstance(expected_blob, str) or not SHA40_RE.fullmatch(expected_blob)
            ):
                raise CandidateIntegrationError(
                    "INVALID_BASE_BLOB",
                    "expected_base_blob_sha must be a 40-char hex SHA or null",
                )

            base_info = base_entries.get(norm_path)
            if base_info is not None:
                mode, obj_type, actual_blob_sha = base_info
                if obj_type != "blob" or mode not in {"100644", "100755"}:
                    raise CandidateIntegrationError(
                        "FORBIDDEN_MODE",
                        f"Base entry '{norm_path}' is not a regular blob (mode={mode}, type={obj_type})",
                    )
                if expected_blob is None or expected_blob != actual_blob_sha:
                    raise CandidateIntegrationError(
                        "BASE_BLOB_CONFLICT",
                        f"Expected base blob '{expected_blob}' does not match actual '{actual_blob_sha}' for '{norm_path}'",
                    )
            else:
                if op == "DELETE":
                    raise CandidateIntegrationError("BASE_BLOB_CONFLICT", f"Cannot DELETE non-existent file '{norm_path}'")
                if expected_blob is not None:
                    raise CandidateIntegrationError(
                        "BASE_BLOB_CONFLICT",
                        f"New file '{norm_path}' expected null base blob, got '{expected_blob}'",
                    )

            content_b64 = item["content_base64"]
            if op == "DELETE":
                if content_b64 is not None:
                    raise CandidateIntegrationError("INVALID_PROPOSAL", "DELETE operation must have null content_base64")
                decoded_operations.append((norm_path, "DELETE", None))
                artifact_hasher.update(f"DELETE:{norm_path}\n".encode("utf-8"))
            else:
                if not isinstance(content_b64, str):
                    raise CandidateIntegrationError("INVALID_PROPOSAL", "WRITE operation requires string content_base64")
                try:
                    raw_bytes = base64.b64decode(content_b64.encode("ascii"), validate=True)
                except (binascii.Error, ValueError) as exc:
                    raise CandidateIntegrationError("INVALID_BASE64", f"Invalid base64 for '{norm_path}': {exc}") from exc
                total_decoded_bytes += len(raw_bytes)
                if total_decoded_bytes > MAX_EXPORT_BYTES:
                    raise CandidateIntegrationError("SIZE_LIMIT_EXCEEDED", "Total decoded candidate content exceeds 2 MiB")
                decoded_operations.append((norm_path, "WRITE", raw_bytes))
                blob_digest = hashlib.sha256(raw_bytes).hexdigest()
                artifact_hasher.update(f"WRITE:{norm_path}:{blob_digest}\n".encode("utf-8"))

        artifact_digest = artifact_hasher.hexdigest()

        # Step 3: Construct Git blobs, tree, and commit in an isolated temporary index
        with tempfile.TemporaryDirectory(prefix="mas-cand-idx-") as tmp_dir:
            tmp_index = str(Path(tmp_dir) / "index")
            idx_env = {"GIT_INDEX_FILE": tmp_index}

            code, _, err = _run_git(self.repo_root, ["read-tree", base_commit_sha], extra_env=idx_env)
            if code != 0:
                raise CandidateIntegrationError("EXPORT_FAILED", f"git read-tree failed: {err.decode(errors='replace')}")

            for norm_path, op, raw_bytes in sorted(decoded_operations, key=lambda x: x[0]):
                if op == "DELETE":
                    code, _, err = _run_git(
                        self.repo_root,
                        ["update-index", "--force-remove", "--", norm_path],
                        extra_env=idx_env,
                    )
                    if code != 0:
                        raise CandidateIntegrationError("EXPORT_FAILED", f"git update-index remove failed for {norm_path}")
                else:
                    assert raw_bytes is not None
                    code, blob_out, err = _run_git(
                        self.repo_root,
                        ["hash-object", "-w", "--stdin"],
                        data=raw_bytes,
                        extra_env=idx_env,
                    )
                    if code != 0:
                        raise CandidateIntegrationError("EXPORT_FAILED", f"git hash-object failed for {norm_path}")
                    blob_sha = blob_out.decode("utf-8").strip()
                    code, _, err = _run_git(
                        self.repo_root,
                        ["update-index", "--add", "--cacheinfo", f"100644,{blob_sha},{norm_path}"],
                        extra_env=idx_env,
                    )
                    if code != 0:
                        raise CandidateIntegrationError("EXPORT_FAILED", f"git update-index add failed for {norm_path}")

            code, tree_out, err = _run_git(self.repo_root, ["write-tree"], extra_env=idx_env)
            if code != 0:
                raise CandidateIntegrationError("EXPORT_FAILED", f"git write-tree failed: {err.decode(errors='replace')}")
            tree_sha = tree_out.decode("utf-8").strip()

            commit_env = {
                **idx_env,
                "GIT_AUTHOR_NAME": f"MAS Exporter ({builder_id})",
                "GIT_AUTHOR_EMAIL": f"{builder_id}@mas.internal",
                "GIT_AUTHOR_DATE": "2026-10-16T00:00:00Z",
                "GIT_COMMITTER_NAME": f"MAS Exporter ({self.exporter_id})",
                "GIT_COMMITTER_EMAIL": f"{self.exporter_id}@mas.internal",
                "GIT_COMMITTER_DATE": "2026-10-16T00:00:00Z",
            }
            commit_msg = f"mas-candidate({task_id}): proposal {proposal_id} from {builder_id}\n"
            code, commit_out, err = _run_git(
                self.repo_root,
                ["commit-tree", tree_sha, "-p", base_commit_sha, "-m", commit_msg],
                extra_env=commit_env,
            )
            if code != 0:
                raise CandidateIntegrationError("EXPORT_FAILED", f"git commit-tree failed: {err.decode(errors='replace')}")
            candidate_commit_sha = commit_out.decode("utf-8").strip()

        # Compute immutable diff digest
        code, diff_bytes, err = _run_git(
            self.repo_root,
            ["diff", base_commit_sha, candidate_commit_sha, "--"],
            output_limit=MAX_EXPORT_BYTES + 65536,
        )
        if code != 0:
            raise CandidateIntegrationError("EXPORT_FAILED", "Failed to compute candidate diff digest")
        diff_digest = hashlib.sha256(diff_bytes).hexdigest()

        created_iso = datetime.now(timezone.utc).isoformat()
        receipt = {
            "schema": CANDIDATE_SCHEMA,
            "proposal_id": proposal_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "issue_id": issue_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "run_id": run_id,
            "fencing_token": fencing_token,
            "policy_version": policy_version,
            "builder_id": builder_id,
            "exporter_id": self.exporter_id,
            "repo_identity": self.repo_identity,
            "base_commit_sha": base_commit_sha,
            "candidate_commit_sha": candidate_commit_sha,
            "tree_sha": tree_sha,
            "proposal_digest": proposal_digest,
            "diff_digest": diff_digest,
            "artifact_digest": artifact_digest,
            "files_count": len(decoded_operations),
            "total_bytes": total_decoded_bytes,
            "created_at": created_iso,
        }

        with self.db.atomic_transaction() as conn:
            conn.execute(
                """
                INSERT INTO pm_coordinator_candidate_exports (
                    proposal_id, tenant_id, project_id, issue_id, task_id,
                    attempt_id, run_id, fencing_token, policy_version,
                    builder_id, exporter_id, repo_identity, base_commit_sha,
                    candidate_commit_sha, tree_sha, proposal_digest, diff_digest,
                    artifact_digest, files_count, total_bytes, receipt_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    tenant_id,
                    project_id,
                    issue_id,
                    task_id,
                    attempt_id,
                    run_id,
                    fencing_token,
                    policy_version,
                    builder_id,
                    self.exporter_id,
                    self.repo_identity,
                    base_commit_sha,
                    candidate_commit_sha,
                    tree_sha,
                    proposal_digest,
                    diff_digest,
                    artifact_digest,
                    len(decoded_operations),
                    total_decoded_bytes,
                    canonical(receipt),
                    created_iso,
                ),
            )
            conn.execute(
                """
                UPDATE pm_coordinator_attempts
                SET candidate_commit_sha = ?
                WHERE attempt_id = ?
                """,
                (candidate_commit_sha, attempt_id),
            )

        return receipt

    def integrate_candidate(
        self,
        *,
        integration_id: str,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_id: str,
        run_id: str,
        fencing_token: int,
        policy_version: int,
        merger_id: str,
        authorization_ref: str,
        target_ref: str,
        expected_target_sha: str,
        candidate_commit_sha: str,
        iam_token: str | None = None,
        evidence_trust: Any = None,
    ) -> dict[str, Any]:
        """Performs compare-and-swap (CAS) Git ref integration for a verified, reviewed, and human-authorized candidate."""
        if not isinstance(integration_id, str) or not integration_id.strip():
            raise CandidateIntegrationError("INVALID_INTEGRATION", "integration_id required")
        if not isinstance(authorization_ref, str) or not authorization_ref.strip():
            raise CandidateIntegrationError("AUTHORIZATION_REQUIRED", "Separate human/policy authorization_ref required")
        if target_ref in self.protected_blocked_refs:
            raise CandidateIntegrationError("PROTECTED_BRANCH_REJECTED", f"Target ref '{target_ref}' is branch-protected")
        if target_ref not in self.allowed_target_refs:
            raise CandidateIntegrationError("UNAPPROVED_REF", f"Target ref '{target_ref}' is not in allowed_target_refs")
        if not SHA40_RE.fullmatch(expected_target_sha) or not SHA40_RE.fullmatch(candidate_commit_sha):
            raise CandidateIntegrationError("INVALID_SHA", "Exact 40-char expected_target_sha and candidate_commit_sha required")

        self._verify_iam_principal(iam_token, merger_id, tenant_id, "coordinator:candidate:integrate")
        resolve_commit(self.repo_root, candidate_commit_sha)
        resolve_commit(self.repo_root, expected_target_sha)

        # Ensure candidate_commit_sha is a descendant of expected_target_sha (fast-forward / exact parent)
        code, _, _ = _run_git(
            self.repo_root,
            ["merge-base", "--is-ancestor", expected_target_sha, candidate_commit_sha],
        )
        if code != 0:
            raise CandidateIntegrationError(
                "TARGET_ADVANCED_REVALIDATION_REQUIRED",
                "Candidate commit is not a fast-forward descendant of expected_target_sha; revalidation required",
            )

        now_iso = datetime.now(timezone.utc).isoformat()

        with self.db.atomic_transaction() as conn:
            existing = conn.execute(
                "SELECT * FROM pm_coordinator_integrations WHERE integration_id = ?",
                (integration_id,),
            ).fetchone()
            if existing is not None:
                if (
                    existing["candidate_commit_sha"] != candidate_commit_sha
                    or existing["expected_target_sha"] != expected_target_sha
                    or existing["target_ref"] != target_ref
                ):
                    raise CandidateIntegrationError("CONFLICTING_REPLAY", "Conflicting parameters for integration_id")
                if existing["status"] == "CONFIRMED":
                    return {
                        "integration_id": integration_id,
                        "status": "CONFIRMED",
                        "target_ref": target_ref,
                        "confirmed_target_sha": existing["confirmed_target_sha"],
                        "candidate_commit_sha": candidate_commit_sha,
                    }
                if existing["status"] in {"INTENDED", "UNKNOWN_INTEGRATION"}:
                    # Reconcile actual git ref state before retrying!
                    code, ref_out, _ = _run_git(self.repo_root, ["rev-parse", "--verify", target_ref])
                    current_ref_sha = ref_out.decode("utf-8").strip() if code == 0 else None
                    if current_ref_sha == candidate_commit_sha:
                        conn.execute(
                            """
                            UPDATE pm_coordinator_integrations
                            SET status = 'CONFIRMED', confirmed_target_sha = ?, updated_at = ?
                            WHERE integration_id = ?
                            """,
                            (candidate_commit_sha, now_iso, integration_id),
                        )
                        return {
                            "integration_id": integration_id,
                            "status": "CONFIRMED",
                            "target_ref": target_ref,
                            "confirmed_target_sha": candidate_commit_sha,
                            "candidate_commit_sha": candidate_commit_sha,
                        }
                    if existing["status"] == "UNKNOWN_INTEGRATION":
                        raise CandidateIntegrationError(
                            "UNKNOWN_INTEGRATION",
                            "Integration state remains uncertain; manual ref reconciliation required",
                        )

            # Verify exported candidate record & separation of duties
            exp_row = conn.execute(
                """
                SELECT * FROM pm_coordinator_candidate_exports
                WHERE attempt_id = ? AND run_id = ? AND candidate_commit_sha = ?
                """,
                (attempt_id, run_id, candidate_commit_sha),
            ).fetchone()
            if not exp_row:
                raise CandidateIntegrationError("UNTRACKED_CANDIDATE", "Candidate was not constructed by trusted exporter")
            if exp_row["builder_id"] == merger_id:
                raise CandidateIntegrationError("AUTHORITY_DENIED", "Builder cannot merge own candidate")
            if authorization_ref in {exp_row["builder_id"], merger_id}:
                raise CandidateIntegrationError("AUTHORIZATION_REQUIRED", "Self-authorization is forbidden")

            # Verify current issue policy & generation
            cur_row = conn.execute(
                """
                SELECT q.policy_version, q.has_pending_reconciliation,
                       r.fencing_token AS run_fence, i.fencing_token AS intent_fence
                FROM pm_coordinator_runs r
                JOIN pm_coordinator_attempts a ON a.attempt_id = r.attempt_id
                JOIN pm_coordinator_intents i ON i.intent_id = r.intent_id AND i.attempt_id = a.attempt_id
                JOIN pm_issues q ON q.id = a.issue_id AND q.project_id = a.project_id
                WHERE r.run_id = ? AND a.attempt_id = ?
                """,
                (run_id, attempt_id),
            ).fetchone()
            if not cur_row:
                raise CandidateIntegrationError("AUTHORITY_DENIED", "Run or attempt record missing")
            if (
                cur_row["policy_version"] != policy_version
                or cur_row["has_pending_reconciliation"]
                or cur_row["run_fence"] != fencing_token
                or cur_row["intent_fence"] != fencing_token
            ):
                raise CandidateIntegrationError("STALE_GENERATION", "Policy version or fencing token is stale")

            # Verify current ADMITTED verification and review receipts for this exact candidate_commit_sha
            receipts = conn.execute(
                """
                SELECT key_id, signature, canonical_payload
                FROM pm_coordinator_evidence_receipts
                WHERE run_id = ? AND candidate_commit_sha = ? AND admission_status = 'ADMITTED'
                """,
                (run_id, candidate_commit_sha),
            ).fetchall()
            has_verified = False
            has_reviewed = False
            for rcpt in receipts:
                p = strict_json(rcpt["canonical_payload"])
                if (
                    p.get("schema") != SCHEMA
                    or p.get("domain") != "PRODUCTION"
                    or p.get("candidate_commit_sha") != candidate_commit_sha
                    or p.get("policy_version") != policy_version
                    or p.get("fencing_token") != fencing_token
                ):
                    continue
                if evidence_trust is not None:
                    grant = evidence_trust._require_issuer(rcpt["key_id"])
                    if not verify_signature(p, rcpt["signature"], grant.secret):
                        continue
                if p.get("type") == "VERIFICATION_EVIDENCE" and p.get("result", {}).get("passed") is True:
                    has_verified = True
                elif p.get("type") == "REVIEW_EVIDENCE" and p.get("result", {}).get("verdict") == "APPROVED":
                    if p.get("issuer_id") != exp_row["builder_id"]:
                        has_reviewed = True

            if not (has_verified and has_reviewed):
                raise CandidateIntegrationError(
                    "EVIDENCE_REQUIRED",
                    "Current admitted verification and independent review receipts are required for exact candidate",
                )

            tree_sha = exp_row["tree_sha"]
            if existing is None:
                conn.execute(
                    """
                    INSERT INTO pm_coordinator_integrations (
                        integration_id, tenant_id, project_id, issue_id, task_id,
                        attempt_id, run_id, fencing_token, policy_version,
                        merger_id, authorization_ref, repo_identity, target_ref,
                        expected_target_sha, candidate_commit_sha, tree_sha,
                        status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'INTENDED', ?, ?)
                    """,
                    (
                        integration_id,
                        tenant_id,
                        project_id,
                        issue_id,
                        task_id,
                        attempt_id,
                        run_id,
                        fencing_token,
                        policy_version,
                        merger_id,
                        authorization_ref,
                        self.repo_identity,
                        target_ref,
                        expected_target_sha,
                        candidate_commit_sha,
                        tree_sha,
                        now_iso,
                        now_iso,
                    ),
                )

        # Re-verify IAM right before git mutation
        self._verify_iam_principal(iam_token, merger_id, tenant_id, "coordinator:candidate:integrate")

        # Check current target_ref SHA before CAS
        code, cur_ref_out, _ = _run_git(self.repo_root, ["rev-parse", "--verify", target_ref])
        cur_ref_sha = cur_ref_out.decode("utf-8").strip() if code == 0 else None
        if cur_ref_sha != expected_target_sha:
            with self.db.atomic_transaction() as conn:
                conn.execute(
                    """
                    UPDATE pm_coordinator_integrations
                    SET status = 'CONFLICT', error_reason = 'Target ref advanced', updated_at = ?
                    WHERE integration_id = ?
                    """,
                    (datetime.now(timezone.utc).isoformat(), integration_id),
                )
            raise CandidateIntegrationError(
                "TARGET_ADVANCED_REVALIDATION_REQUIRED",
                f"Target ref '{target_ref}' is at '{cur_ref_sha}', expected '{expected_target_sha}'",
            )

        # Perform atomic compare-and-swap via git update-ref
        code, _, err = _run_git(
            self.repo_root,
            ["update-ref", target_ref, candidate_commit_sha, expected_target_sha],
        )
        # Re-read target_ref to confirm
        v_code, v_out, _ = _run_git(self.repo_root, ["rev-parse", "--verify", target_ref])
        confirmed_sha = v_out.decode("utf-8").strip() if v_code == 0 else None

        updated_iso = datetime.now(timezone.utc).isoformat()
        if code == 0 and confirmed_sha == candidate_commit_sha:
            with self.db.atomic_transaction() as conn:
                conn.execute(
                    """
                    UPDATE pm_coordinator_integrations
                    SET status = 'CONFIRMED', confirmed_target_sha = ?, updated_at = ?
                    WHERE integration_id = ?
                    """,
                    (candidate_commit_sha, updated_iso, integration_id),
                )
            return {
                "integration_id": integration_id,
                "status": "CONFIRMED",
                "target_ref": target_ref,
                "confirmed_target_sha": candidate_commit_sha,
                "candidate_commit_sha": candidate_commit_sha,
            }

        with self.db.atomic_transaction() as conn:
            conn.execute(
                """
                UPDATE pm_coordinator_integrations
                SET status = 'UNKNOWN_INTEGRATION',
                    error_reason = ?,
                    updated_at = ?
                WHERE integration_id = ?
                """,
                (err.decode(errors="replace")[:500], updated_iso, integration_id),
            )
        raise CandidateIntegrationError("UNKNOWN_INTEGRATION", "Git update-ref outcome uncertain; intent held")


import json  # noqa: E402

__all__ = [
    "CANDIDATE_SCHEMA",
    "CandidateExporter",
    "CandidateIntegrationError",
]
