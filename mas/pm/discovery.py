"""
mas.pm.discovery: Automatic repository project discovery and reconciliation (SBA-02).

Authoritative registry: projects/registry.json.
Synchronizes project identities, paths and branch freshness into MAS-PM.
Preserves dirty working directories, retains existing project history, and
enforces safe path boundaries and uniqueness constraints.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
import subprocess
import threading
import time
from typing import Any, Dict, Optional
import uuid

from mas.pm.db import PMDatabase
from mas.pm.models import Project, ProjectSource
from mas.pm.tools import get_pm_db

logger = logging.getLogger("mas.pm.discovery")

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_FILE = ROOT / "projects" / "registry.json"


class RepositoryRegistryError(Exception):
    """Base exception for repository registry errors."""
    pass


class RegistryValidationError(RepositoryRegistryError):
    """Raised when registry schema, paths, or fields fail validation."""
    pass


class ContradictoryMappingError(RepositoryRegistryError):
    """Raised when a registry mapping contradicts an existing database identity."""
    pass


class GitSyncError(RepositoryRegistryError):
    """Raised when git inspection or branch synchronization fails."""
    pass


class ProjectRegistryDiscovery:
    """Discovers and reconciles repository projects from projects/registry.json."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        registry_file: Optional[Path] = None,
        db: Optional[PMDatabase] = None,
    ) -> None:
        self.repo_root = (repo_root or ROOT).resolve()
        self.registry_file = (registry_file or (self.repo_root / "projects" / "registry.json")).resolve()
        self._db = db
        self._lock = threading.Lock()
        self.last_sync_time: Optional[str] = None
        self.last_sync_revision: Optional[str] = None
        self.last_sync_error: Optional[str] = None
        self.is_stale: bool = False
        self.last_valid_manifest: Optional[dict] = None

    @property
    def db(self) -> PMDatabase:
        if self._db is None:
            self._db = get_pm_db()
        return self._db

    def get_current_git_revision(self) -> Optional[str]:
        """Reads current HEAD commit SHA from local repository object database."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception as exc:
            logger.warning("Failed to determine git revision: %s", exc)
        return None

    def safe_git_fetch(self, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Safely fetches the remote configured branch without touching the working tree.
        Preserves dirty checkout; never performs destructive resets or checkout overrides.
        """
        git_dir = self.repo_root / ".git"
        if not git_dir.exists():
            return {
                "success": True,
                "error": None,
                "dirty_checkout_preserved": True,
                "source_revision": None,
                "remote_ref": None,
            }

        dirty = False
        try:
            status_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            dirty = bool(status_res.stdout.strip())
        except Exception:
            pass

        target_branch = branch
        if not target_branch:
            if self.last_valid_manifest and "repository" in self.last_valid_manifest:
                target_branch = self.last_valid_manifest["repository"].get("configured_branch")
            elif self.registry_file.exists():
                try:
                    reg_data = json.loads(self.registry_file.read_text(encoding="utf-8"))
                    target_branch = reg_data.get("repository", {}).get("configured_branch")
                except Exception:
                    pass
        target_branch = target_branch or "feat/scrum-board-automation"

        try:
            remotes = subprocess.run(
                ["git", "remote"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if "origin" not in remotes.stdout.split():
                return {
                    "success": True,
                    "dirty_checkout_preserved": dirty,
                    "source_revision": self.get_current_git_revision(),
                    "remote_ref": "HEAD",
                }

            fetch_res = subprocess.run(
                ["git", "fetch", "origin", f"+refs/heads/{target_branch}:refs/remotes/origin/sba-discovery"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            if fetch_res.returncode == 0:
                rev_res = subprocess.run(
                    ["git", "rev-parse", "--verify", "refs/remotes/origin/sba-discovery^{commit}"],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if rev_res.returncode == 0 and rev_res.stdout.strip():
                    remote_rev = rev_res.stdout.strip()
                    return {
                        "success": True,
                        "dirty_checkout_preserved": dirty,
                        "source_revision": remote_rev,
                        "remote_ref": "refs/remotes/origin/sba-discovery",
                    }
                return {
                    "success": False,
                    "error": "Failed to verify fetched commit ref",
                    "dirty_checkout_preserved": dirty,
                }
            else:
                return {
                    "success": False,
                    "error": fetch_res.stderr.strip() or "git fetch failed",
                    "dirty_checkout_preserved": dirty,
                }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "dirty_checkout_preserved": dirty,
            }

    def load_and_validate_registry(
        self,
        path: Optional[Path] = None,
        revision: Optional[str] = None,
        registry_data: Optional[dict] = None,
    ) -> dict:
        """
        Loads and strictly validates projects/registry.json per BOARD_CONTRACT_V1.
        Supports reading from a target git revision or local filesystem.
        Rejects unsafe paths (absolute, traversal) and duplicate keys/IDs.
        Validates tree entries strictly against the selected revision in remote mode,
        rejecting blobs and symlinks.
        """
        if registry_data is not None:
            data = copy.deepcopy(registry_data)
        else:
            content = None
            if revision:
                try:
                    cat_res = subprocess.run(
                        ["git", "show", f"{revision}:projects/registry.json"],
                        cwd=str(self.repo_root),
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if cat_res.returncode == 0 and cat_res.stdout:
                        content = cat_res.stdout
                except Exception:
                    pass

            if content is None:
                target_path = (path or self.registry_file).resolve()
                if not target_path.exists():
                    raise RegistryValidationError(f"Registry file not found: {target_path}")
                try:
                    content = target_path.read_text(encoding="utf-8")
                except Exception as exc:
                    raise RegistryValidationError(f"Failed to read registry: {exc}")

            try:
                data = json.loads(content)
            except json.JSONDecodeError as exc:
                raise RegistryValidationError(f"Malformed registry JSON: {exc}")

        if not isinstance(data, dict):
            raise RegistryValidationError("Registry root must be a JSON object")

        if data.get("schema_version") != 1:
            raise RegistryValidationError(
                f"Unsupported schema_version: {data.get('schema_version')}, expected 1"
            )

        repo = data.get("repository")
        if not isinstance(repo, dict):
            raise RegistryValidationError("Registry must contain a 'repository' object")

        repo_id = repo.get("id") or repo.get("github_id")
        if repo_id is None:
            raise RegistryValidationError("Repository metadata missing 'id' or 'github_id'")
        for field in ("owner", "name", "configured_branch"):
            val = repo.get(field)
            if not val or not isinstance(val, str) or not val.strip():
                raise RegistryValidationError(f"Repository metadata missing non-empty '{field}'")

        projects = data.get("projects")
        if not isinstance(projects, list):
            raise RegistryValidationError("Registry must contain a 'projects' list")

        seen_keys: set[str] = set()
        seen_ids: set[str] = set()
        seen_roots: set[str] = set()

        for idx, p in enumerate(projects):
            if not isinstance(p, dict):
                raise RegistryValidationError(f"Project item at index {idx} must be a dictionary")

            raw_id = p.get("project_id")
            if not raw_id or not isinstance(raw_id, str):
                raise RegistryValidationError(f"Project at index {idx} missing 'project_id'")
            try:
                proj_id = str(uuid.UUID(raw_id))
            except Exception:
                raise RegistryValidationError(f"Invalid UUID for project_id: {raw_id}")

            if proj_id in seen_ids:
                raise RegistryValidationError(f"Duplicate project_id in registry: {proj_id}")
            seen_ids.add(proj_id)

            raw_key = p.get("project_key")
            if not raw_key or not isinstance(raw_key, str):
                raise RegistryValidationError(f"Project {proj_id} missing 'project_key'")
            proj_key = raw_key.strip().upper()
            if not proj_key.isalnum() or len(proj_key) < 2 or len(proj_key) > 10:
                raise RegistryValidationError(
                    f"Invalid project_key '{raw_key}' for project {proj_id}; must be 2-10 alphanumeric characters"
                )
            if proj_key in seen_keys:
                raise RegistryValidationError(f"Duplicate project_key in registry: {proj_key}")
            seen_keys.add(proj_key)

            name = p.get("name")
            if not name or not isinstance(name, str) or not name.strip():
                raise RegistryValidationError(f"Project {proj_id} missing non-empty 'name'")

            root_path_str = p.get("root_path")
            if not root_path_str or not isinstance(root_path_str, str):
                raise RegistryValidationError(f"Project {proj_id} missing 'root_path'")

            if root_path_str.startswith("/") or ".." in Path(root_path_str).parts:
                raise RegistryValidationError(
                    f"Unsafe root_path '{root_path_str}' in project {proj_id}: absolute paths and directory traversal forbidden"
                )

            resolved_root = (self.repo_root / root_path_str).resolve()
            if not resolved_root.is_relative_to(self.repo_root):
                raise RegistryValidationError(f"root_path '{root_path_str}' escapes repository boundary")

            norm_root = str(resolved_root)
            if norm_root in seen_roots:
                raise ContradictoryMappingError(f"Duplicate root_path mapping for '{root_path_str}'")
            seen_roots.add(norm_root)

            plan_path_str = p.get("planning_path")
            if not plan_path_str or not isinstance(plan_path_str, str):
                raise RegistryValidationError(f"Project {proj_id} missing 'planning_path'")

            if plan_path_str.startswith("/") or ".." in Path(plan_path_str).parts:
                raise RegistryValidationError(
                    f"Unsafe planning_path '{plan_path_str}' in project {proj_id}: absolute paths and directory traversal forbidden"
                )

            resolved_plan = (self.repo_root / plan_path_str).resolve()
            if not resolved_plan.is_relative_to(self.repo_root):
                raise RegistryValidationError(f"planning_path '{plan_path_str}' escapes repository boundary")

            exists_in_tree = False
            if revision:
                # Inspect revision tree entries strictly without falling back to local filesystem
                root_tree_res = subprocess.run(
                    ["git", "ls-tree", revision, root_path_str],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if root_tree_res.returncode != 0:
                    raise GitSyncError(f"Failed to inspect git tree for revision {revision}")

                root_out = root_tree_res.stdout.strip()
                if root_out:
                    parts = root_out.split()
                    if len(parts) >= 2:
                        mode, obj_type = parts[0], parts[1]
                        if mode == "120000" or obj_type != "tree":
                            raise RegistryValidationError(
                                f"root_path '{root_path_str}' in revision {revision} is a {obj_type} (mode {mode}), not a directory"
                            )
                        plan_tree_res = subprocess.run(
                            ["git", "ls-tree", revision, plan_path_str],
                            cwd=str(self.repo_root),
                            capture_output=True,
                            text=True,
                            check=False,
                        )
                        plan_out = plan_tree_res.stdout.strip()
                        if plan_out:
                            p_parts = plan_out.split()
                            if len(p_parts) >= 2:
                                p_mode, p_type = p_parts[0], p_parts[1]
                                if p_mode == "120000" or p_type != "tree":
                                    raise RegistryValidationError(
                                        f"planning_path '{plan_path_str}' in revision {revision} is a {p_type} (mode {p_mode}), not a directory"
                                    )
                                exists_in_tree = True
                        else:
                            exists_in_tree = False
                else:
                    exists_in_tree = False
            else:
                raw_root = self.repo_root / root_path_str
                raw_plan = self.repo_root / plan_path_str
                if raw_root.is_symlink() or any(p.is_symlink() for p in (raw_root, *raw_root.parents) if p != self.repo_root):
                    raise RegistryValidationError(f"root_path '{root_path_str}' is a symlink, not a directory")
                if raw_plan.is_symlink() or any(p.is_symlink() for p in (raw_plan, *raw_plan.parents) if p != self.repo_root):
                    raise RegistryValidationError(f"planning_path '{plan_path_str}' is a symlink, not a directory")
                if resolved_root.exists() and not resolved_root.is_dir():
                    raise RegistryValidationError(f"root_path '{root_path_str}' is a file, not a directory")
                if resolved_plan.exists() and not resolved_plan.is_dir():
                    raise RegistryValidationError(f"planning_path '{plan_path_str}' is a file, not a directory")

                exists_in_tree = (
                    resolved_root.exists()
                    and resolved_root.is_dir()
                    and resolved_plan.exists()
                    and resolved_plan.is_dir()
                )

            p["exists_on_disk"] = exists_in_tree

        return data

    def reconcile_projects(
        self,
        registry_data: Optional[dict] = None,
        revision: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reconciles validated registry manifest against database atomically.
        - Runs within a single explicit BEGIN IMMEDIATE transaction.
        - Performs all conflict checks within the transaction snapshot.
        - Preserves existing legacy deployment project IDs without destructive re-keying.
        - Persists stable remote UUID mappings via remote_project_id.
        - Rolls back completely if any mutation fails, leaving zero partial records.
        """
        manifest = self.load_and_validate_registry(revision=revision, registry_data=registry_data)
        repo_meta = manifest["repository"]
        repo_id = str(repo_meta.get("id") or repo_meta.get("github_id"))
        repo_owner = repo_meta["owner"]
        repo_name = repo_meta["name"]
        configured_branch = repo_meta["configured_branch"]
        current_rev = revision or self.get_current_git_revision() or "unrecorded"

        created_keys: list[str] = []
        updated_keys: list[str] = []
        unchanged_keys: list[str] = []
        inactivated_keys: list[str] = []
        registered_project_ids: set[str] = set()

        with self._lock:
            with self.db.atomic_transaction() as tx_conn:
                existing_projects = self.db.list_projects(conn=tx_conn)
                existing_sources = self.db.list_project_sources(conn=tx_conn)

                by_id = {p.id: p for p in existing_projects}
                by_key = {p.key: p for p in existing_projects}
                sources_by_proj_id = {s.project_id: s for s in existing_sources}
                sources_by_remote_id = {s.remote_project_id: s for s in existing_sources if s.remote_project_id}

                prevalidated = []
                seen_keys_in_batch: set[str] = set()
                seen_ids_in_batch: set[str] = set()

                for p_def in manifest["projects"]:
                    proj_id = str(uuid.UUID(p_def["project_id"]))
                    proj_key = p_def["project_key"].strip().upper()
                    name = p_def["name"].strip()
                    description = (p_def.get("description") or "").strip()
                    root_path = p_def["root_path"].strip()
                    planning_path = p_def["planning_path"].strip()
                    exists_on_disk = p_def.get("exists_on_disk", True)

                    if proj_key in seen_keys_in_batch or proj_id in seen_ids_in_batch:
                        raise RegistryValidationError(f"Duplicate key '{proj_key}' or ID '{proj_id}' in batch")
                    seen_keys_in_batch.add(proj_key)
                    seen_ids_in_batch.add(proj_id)

                    existing_by_remote = sources_by_remote_id.get(proj_id)
                    existing_by_id = by_id.get(proj_id)
                    existing_by_key = by_key.get(proj_key)

                    if existing_by_remote:
                        actual_id = existing_by_remote.project_id
                        proj_obj = by_id.get(actual_id)
                        if proj_obj and proj_obj.key != proj_key:
                            raise ContradictoryMappingError(
                                f"Remote project {proj_id} mapped to {actual_id} has key '{proj_obj.key}', contradictory to '{proj_key}'"
                            )
                        if existing_by_key and existing_by_key.id != actual_id:
                            raise ContradictoryMappingError(
                                f"Key '{proj_key}' already allocated to project {existing_by_key.id}, not {actual_id}"
                            )
                        action = "update" if (proj_obj and (proj_obj.name != name or proj_obj.description != description)) else "unchanged"
                    elif existing_by_id and existing_by_key and existing_by_id.id != existing_by_key.id:
                        raise ContradictoryMappingError(
                            f"Contradictory mapping: UUID '{proj_id}' allocated to '{existing_by_id.key}', "
                            f"but key '{proj_key}' allocated to project '{existing_by_key.id}'"
                        )
                    elif existing_by_id:
                        if existing_by_id.key != proj_key:
                            raise ContradictoryMappingError(
                                f"Project {proj_id} has key '{existing_by_id.key}' in database, but registry specifies '{proj_key}'"
                            )
                        actual_id = proj_id
                        action = "update" if (existing_by_id.name != name or existing_by_id.description != description) else "unchanged"
                    elif existing_by_key:
                        existing_source = sources_by_proj_id.get(existing_by_key.id)
                        if existing_source and existing_source.root_path != root_path:
                            raise ContradictoryMappingError(
                                f"Contradictory mapping: project '{proj_key}' is bound to path '{existing_source.root_path}', "
                                f"cannot rebind to '{root_path}'"
                            )
                        actual_id = existing_by_key.id
                        action = "update" if (existing_by_key.name != name or existing_by_key.description != description) else "unchanged"
                    else:
                        actual_id = proj_id
                        action = "create"

                    status = "active" if exists_on_disk else "inactive"
                    error_msg = None if exists_on_disk else f"Project directory '{root_path}' not found in revision"

                    prevalidated.append({
                        "actual_id": actual_id,
                        "remote_project_id": proj_id,
                        "proj_key": proj_key,
                        "name": name,
                        "description": description,
                        "root_path": root_path,
                        "planning_path": planning_path,
                        "action": action,
                        "status": status,
                        "error": error_msg,
                    })

                for item in prevalidated:
                    actual_id = item["actual_id"]
                    proj_key = item["proj_key"]
                    action = item["action"]

                    if action == "create":
                        new_proj = Project(
                            id=actual_id,
                            key=proj_key,
                            name=item["name"],
                            description=item["description"],
                            token_budget=5_000_000,
                            tokens_consumed=0,
                        )
                        self.db.create_project(new_proj, conn=tx_conn)
                        created_keys.append(proj_key)
                    elif action == "update":
                        self.db.update_project(
                            actual_id,
                            name=item["name"],
                            description=item["description"],
                            conn=tx_conn,
                        )
                        updated_keys.append(proj_key)
                    else:
                        unchanged_keys.append(proj_key)

                    registered_project_ids.add(actual_id)

                    source = ProjectSource(
                        project_id=actual_id,
                        repository_id=repo_id,
                        repository_owner=repo_owner,
                        repository_name=repo_name,
                        configured_branch=configured_branch,
                        root_path=item["root_path"],
                        planning_path=item["planning_path"],
                        status=item["status"],
                        source_revision=current_rev,
                        last_error=item["error"],
                        is_stale=False,
                        remote_project_id=item["remote_project_id"],
                    )
                    self.db.upsert_project_source(source, conn=tx_conn)

                for s in existing_sources:
                    if s.status == "active" and s.project_id not in registered_project_ids:
                        self.db.mark_project_source_inactive(s.project_id, conn=tx_conn)
                        proj = by_id.get(s.project_id)
                        inactivated_keys.append(proj.key if proj else s.project_id)

                self.last_valid_manifest = manifest
                self.last_sync_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                self.last_sync_revision = current_rev
                self.last_sync_error = None
                self.is_stale = False

        return {
            "status": "healthy",
            "source_revision": current_rev,
            "created": created_keys,
            "updated": updated_keys,
            "unchanged": unchanged_keys,
            "inactivated": inactivated_keys,
            "total_registered": len(registered_project_ids),
        }

    def sync(self, fetch_remote: bool = True) -> Dict[str, Any]:
        """
        High-level synchronization orchestrator:
        1. Optionally fetches remote ref safely (preserving dirty working tree).
        2. If fetch fails, reports failure as stale with error and retains last valid snapshot.
        3. Validates registry from target revision or local file.
        4. Reconciles database records atomically.
        """
        fetch_result = {}
        target_revision = None
        if fetch_remote:
            fetch_result = self.safe_git_fetch()
            if not fetch_result.get("success", False):
                err = fetch_result.get("error", "Remote fetch failed")
                self.last_sync_error = err
                self.is_stale = True
                try:
                    sources = self.db.list_project_sources()
                    for s in sources:
                        self.db.update_project_source_error(s.project_id, error=err, is_stale=True)
                except Exception:
                    pass
                return {
                    "status": "stale",
                    "error": err,
                    "is_stale": True,
                    "last_successful_sync": self.last_sync_time,
                    "source_revision": self.get_current_git_revision(),
                    "fetch": fetch_result,
                }
            target_revision = fetch_result.get("source_revision")

        try:
            manifest = self.load_and_validate_registry(revision=target_revision)
            reconcile_result = self.reconcile_projects(manifest, revision=target_revision)
            reconcile_result["fetch"] = fetch_result
            return reconcile_result
        except Exception as exc:
            self.last_sync_error = str(exc)
            self.is_stale = True
            logger.error("Project discovery synchronization failed: %s", exc)

            try:
                sources = self.db.list_project_sources()
                for s in sources:
                    self.db.update_project_source_error(s.project_id, error=str(exc), is_stale=True)
            except Exception:
                pass

            return {
                "status": "stale",
                "error": str(exc),
                "is_stale": True,
                "last_successful_sync": self.last_sync_time,
                "source_revision": target_revision or self.get_current_git_revision(),
                "fetch": fetch_result,
            }

    def get_projects_with_freshness(self) -> Dict[str, Any]:
        """
        Constructs the response for GET /api/pm/v1/projects per BOARD_CONTRACT_V1.
        Returns registered projects and their source freshness and synchronization metadata.
        """
        sources = {s.project_id: s for s in self.db.list_project_sources()}
        all_projects = self.db.list_projects()

        out_projects = []
        for p in all_projects:
            s = sources.get(p.id)
            if s:
                freshness = {
                    "repository_id": s.repository_id,
                    "remote_project_id": s.remote_project_id,
                    "configured_branch": s.configured_branch,
                    "source_revision": s.source_revision,
                    "last_successful_sync": s.last_successful_sync,
                    "last_error": s.last_error,
                    "is_stale": s.is_stale,
                    "status": s.status,
                }
                out_projects.append({
                    "id": p.id,
                    "key": p.key,
                    "name": p.name,
                    "description": p.description,
                    "token_budget": p.token_budget,
                    "tokens_consumed": p.tokens_consumed,
                    "root_path": s.root_path,
                    "planning_path": s.planning_path,
                    "status": s.status,
                    "source_freshness": freshness,
                })
            else:
                out_projects.append({
                    "id": p.id,
                    "key": p.key,
                    "name": p.name,
                    "description": p.description,
                    "token_budget": p.token_budget,
                    "tokens_consumed": p.tokens_consumed,
                    "status": "unregistered",
                    "source_freshness": None,
                })

        persisted_rev = self.last_sync_revision or self.get_current_git_revision()
        persisted_last_sync = self.last_sync_time
        if not persisted_last_sync and sources:
            recent = max((s.last_successful_sync for s in sources.values() if s.last_successful_sync), default=None)
            if recent:
                persisted_last_sync = recent.isoformat() if hasattr(recent, "isoformat") else str(recent)

        return {
            "projects": out_projects,
            "discovery": {
                "last_sync": persisted_last_sync,
                "source_revision": persisted_rev,
                "is_stale": self.is_stale,
                "error": self.last_sync_error,
            },
        }

    def start_discovery_daemon(self, interval_seconds: int = 30) -> threading.Thread:
        """Starts a background daemon thread that periodically re-synchronizes remote and registry."""
        def _daemon_loop():
            while True:
                time.sleep(interval_seconds)
                self.sync(fetch_remote=True)

        t = threading.Thread(target=_daemon_loop, name="mas-project-discovery", daemon=True)
        t.start()
        return t


def get_project_discovery(
    db: Optional[PMDatabase] = None,
    repo_root: Optional[Path] = None,
) -> ProjectRegistryDiscovery:
    """
    Returns a ProjectRegistryDiscovery instance dynamically bound to the current tenant or explicit DB.
    Never caches request-resolved authority in a process-global singleton.
    """
    from mas.tenancy import current_binding
    binding = current_binding()
    if binding and binding.database and db is None:
        db = PMDatabase(db_path=binding.database)
    return ProjectRegistryDiscovery(db=db, repo_root=repo_root)
