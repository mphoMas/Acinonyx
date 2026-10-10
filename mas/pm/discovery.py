"""
mas.pm.discovery: Automatic repository project discovery and reconciliation (SBA-02).

Authoritative registry: projects/registry.json.
Synchronizes project identities, paths and branch freshness into MAS-PM.
Preserves dirty working directories, retains existing project history, and
enforces safe path boundaries and uniqueness constraints.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import subprocess
import threading
import time
from typing import Any, Dict, List, Optional
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
                "success": False,
                "error": "Not a git repository",
                "dirty_checkout_preserved": True,
            }

        # Check for dirty working tree to guarantee preservation
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

        target_branch = branch or "feat/scrum-board-automation"
        try:
            fetch_res = subprocess.run(
                ["git", "fetch", "origin", target_branch],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            if fetch_res.returncode == 0:
                rev = self.get_current_git_revision()
                return {
                    "success": True,
                    "dirty_checkout_preserved": dirty,
                    "source_revision": rev,
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

    def load_and_validate_registry(self, path: Optional[Path] = None) -> dict:
        """
        Loads and strictly validates projects/registry.json per BOARD_CONTRACT_V1.
        Rejects unsafe paths (absolute, traversal), duplicate keys/IDs, and invalid schemas.
        """
        target_path = (path or self.registry_file).resolve()
        if not target_path.exists():
            raise RegistryValidationError(f"Registry file not found: {target_path}")

        try:
            content = target_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RegistryValidationError(f"Malformed registry JSON: {exc}")

        if not isinstance(data, dict):
            raise RegistryValidationError("Registry root must be a JSON object")

        if data.get("schema_version") != 1:
            raise RegistryValidationError(
                f"Unsupported registry schema_version: {data.get('schema_version')}; expected 1"
            )

        repo_meta = data.get("repository")
        if not isinstance(repo_meta, dict):
            raise RegistryValidationError("Registry missing 'repository' metadata block")
        for req_field in ("id", "owner", "name", "configured_branch"):
            if not repo_meta.get(req_field) or not isinstance(repo_meta[req_field], str):
                raise RegistryValidationError(f"Missing required repository field '{req_field}'")

        projects = data.get("projects")
        if not isinstance(projects, list):
            raise RegistryValidationError("'projects' must be a list of project definitions")

        seen_ids: set[str] = set()
        seen_keys: set[str] = set()
        seen_roots: set[str] = set()

        for idx, p in enumerate(projects):
            if not isinstance(p, dict):
                raise RegistryValidationError(f"Project item at index {idx} must be an object")

            # Validate project_id UUID format
            raw_id = p.get("project_id")
            if not raw_id or not isinstance(raw_id, str):
                raise RegistryValidationError(f"Project at index {idx} missing 'project_id'")
            try:
                val_uuid = uuid.UUID(raw_id)
                proj_id = str(val_uuid)
            except ValueError:
                raise RegistryValidationError(f"Invalid UUID for project_id: {raw_id}")

            if proj_id in seen_ids:
                raise RegistryValidationError(f"Duplicate project_id in registry: {proj_id}")
            seen_ids.add(proj_id)

            # Validate project_key
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

            # Validate name
            name = p.get("name")
            if not name or not isinstance(name, str) or not name.strip():
                raise RegistryValidationError(f"Project {proj_id} missing non-empty 'name'")

            # Validate root_path (safe path check)
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
            if not resolved_root.exists() or not resolved_root.is_dir():
                raise RegistryValidationError(f"root_path directory does not exist: {root_path_str}")

            norm_root = str(resolved_root)
            if norm_root in seen_roots:
                raise ContradictoryMappingError(f"Duplicate root_path mapping for '{root_path_str}'")
            seen_roots.add(norm_root)

            # Validate planning_path (safe path check)
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
            if not resolved_plan.exists() or not resolved_plan.is_dir():
                raise RegistryValidationError(f"planning_path directory does not exist: {plan_path_str}")

        return data

    def reconcile_projects(self, registry_data: Optional[dict] = None) -> Dict[str, Any]:
        """
        Reconciles validated registry manifest against database.
        - Preserves existing IDs, issues, and review history for existing projects.
        - Idempotently creates missing projects.
        - Inactivates missing or removed sources without deleting tasks or history.
        - Rejects contradictory identity mappings.
        """
        manifest = registry_data or self.load_and_validate_registry()
        repo_meta = manifest["repository"]
        repo_id = repo_meta["id"]
        repo_owner = repo_meta["owner"]
        repo_name = repo_meta["name"]
        configured_branch = repo_meta["configured_branch"]
        current_rev = self.get_current_git_revision() or "unrecorded"

        created_keys: list[str] = []
        updated_keys: list[str] = []
        unchanged_keys: list[str] = []
        inactivated_keys: list[str] = []

        registered_project_ids: set[str] = set()

        with self._lock:
            for p_def in manifest["projects"]:
                proj_id = str(uuid.UUID(p_def["project_id"]))
                proj_key = p_def["project_key"].strip().upper()
                name = p_def["name"].strip()
                description = (p_def.get("description") or "").strip()
                root_path = p_def["root_path"].strip()
                planning_path = p_def["planning_path"].strip()

                registered_project_ids.add(proj_id)

                # Check database by ID first (the immutable anchor)
                existing_by_id = self.db.get_project(proj_id)
                existing_by_key = self.db.get_project_by_key(proj_key)

                if existing_by_id:
                    # Project already exists with this exact UUID
                    if existing_by_id.key != proj_key:
                        raise ContradictoryMappingError(
                            f"Project {proj_id} has key '{existing_by_id.key}' in database, but registry specifies '{proj_key}'"
                        )
                    # Check if name or description was updated
                    if existing_by_id.name != name or existing_by_id.description != description:
                        self.db.update_project(proj_id, name=name, description=description)
                        updated_keys.append(proj_key)
                    else:
                        unchanged_keys.append(proj_key)
                elif existing_by_key:
                    # Key exists, but ID differs
                    raise ContradictoryMappingError(
                        f"Contradictory mapping: key '{proj_key}' already allocated to project {existing_by_key.id}, "
                        f"cannot reassign to {proj_id}"
                    )
                else:
                    # Brand new project to register
                    new_proj = Project(
                        id=proj_id,
                        key=proj_key,
                        name=name,
                        description=description,
                        token_budget=5_000_000,
                        tokens_consumed=0,
                    )
                    self.db.create_project(new_proj)
                    created_keys.append(proj_key)

                # Upsert project source metadata
                source = ProjectSource(
                    project_id=proj_id,
                    repository_id=repo_id,
                    repository_owner=repo_owner,
                    repository_name=repo_name,
                    configured_branch=configured_branch,
                    root_path=root_path,
                    planning_path=planning_path,
                    status="active",
                    source_revision=current_rev,
                    last_error=None,
                    is_stale=False,
                )
                self.db.upsert_project_source(source)

            # Inactivate projects previously active in DB that are no longer in registry
            existing_sources = self.db.list_project_sources()
            for s in existing_sources:
                if s.status == "active" and s.project_id not in registered_project_ids:
                    self.db.mark_project_source_inactive(s.project_id)
                    proj = self.db.get_project(s.project_id)
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

    def sync(self, fetch_remote: bool = False) -> Dict[str, Any]:
        """
        High-level synchronization orchestrator:
        1. Optionally fetches remote ref safely (preserving dirty working tree).
        2. Validates registry.
        3. Reconciles database records.
        4. If registry is invalid, retains last valid snapshot in DB and marks state stale.
        """
        fetch_result = {}
        if fetch_remote:
            fetch_result = self.safe_git_fetch()

        try:
            manifest = self.load_and_validate_registry()
            reconcile_result = self.reconcile_projects(manifest)
            reconcile_result["fetch"] = fetch_result
            return reconcile_result
        except Exception as exc:
            self.last_sync_error = str(exc)
            self.is_stale = True
            logger.error("Project discovery synchronization failed: %s", exc)

            # Retain last valid snapshot in database by marking sources stale rather than removing
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
                "source_revision": self.get_current_git_revision(),
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

        persisted_last_sync = self.last_sync_time
        if not persisted_last_sync and sources:
            sync_times = [s.last_successful_sync for s in sources.values() if s.last_successful_sync]
            if sync_times:
                persisted_last_sync = max(sync_times)

        persisted_rev = self.last_sync_revision or self.get_current_git_revision()
        if not persisted_rev and sources:
            revs = [s.source_revision for s in sources.values() if s.source_revision]
            if revs:
                persisted_rev = revs[0]

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
        """Starts a background daemon thread that periodically re-synchronizes the registry."""
        def _daemon_loop():
            prev_mtime = self.registry_file.stat().st_mtime_ns if self.registry_file.exists() else None
            while True:
                time.sleep(interval_seconds)
                curr_mtime = self.registry_file.stat().st_mtime_ns if self.registry_file.exists() else None
                # Resync on mtime change or interval
                if curr_mtime != prev_mtime:
                    self.sync()
                    prev_mtime = curr_mtime

        t = threading.Thread(target=_daemon_loop, name="mas-project-discovery", daemon=True)
        t.start()
        return t


_GLOBAL_DISCOVERY: Optional[ProjectRegistryDiscovery] = None


def get_project_discovery() -> ProjectRegistryDiscovery:
    """Singleton getter for ProjectRegistryDiscovery."""
    global _GLOBAL_DISCOVERY
    if _GLOBAL_DISCOVERY is None:
        _GLOBAL_DISCOVERY = ProjectRegistryDiscovery()
    return _GLOBAL_DISCOVERY
