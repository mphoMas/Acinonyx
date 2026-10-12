"""
mas.pm.db: Embedded SQLite persistence layer for the MAS Project Management Engine.
Enforces WAL mode, foreign keys, 5000ms busy timeout, and atomic transactions.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from mas.pm.models import (
    CriticVerdict,
    CriticVerdictType,
    EvidenceLink,
    EvidenceType,
    Issue,
    IssueState,
    IssueType,
    PriorityLevel,
    Project,
    ProjectSource,
    Sprint,
    SprintState,
    TaskMapping,
    PlanRecord,
    ReconciliationAuditRecord,
)

DEFAULT_DB_PATH = Path(os.environ.get("MAS_PM_DB_PATH", "mas_pm.db"))


class PMDatabase:
    """Thread-safe SQLite database manager for MAS-PM."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        from mas.tenancy import current_binding
        binding = current_binding()
        self.db_path = Path(db_path) if db_path else (binding.database if binding else DEFAULT_DB_PATH)
        if binding and self.db_path.resolve() != binding.database.resolve():
            raise PermissionError("Database belongs to another tenant")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.init_schema()
        from mas.pm.coordinator import CoordinatorStore
        self.coordinator = CoordinatorStore(self)

    def _get_connection(self) -> sqlite3.Connection:
        from mas.tenancy import current_binding
        binding = current_binding()
        if binding:
            binding.require("storage:read")
            if self.db_path.resolve() != binding.database.resolve():
                raise PermissionError("Database belongs to another tenant")
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=5.0,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode by default; manual transactions with BEGIN
        )
        conn.row_factory = sqlite3.Row
        with conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    @contextmanager
    def atomic_transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Executes a block within an atomic BEGIN IMMEDIATE transaction.
        Satisfies Condition 1 of Adversarial Review: prevents concurrent write race conditions.
        """
        conn = self._get_connection()
        with self._lock:
            conn.execute("BEGIN IMMEDIATE;")
            try:
                yield conn
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

    def init_schema(self) -> None:
        """Initializes all relational tables and indices."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_projects (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    token_budget INTEGER NOT NULL DEFAULT 5000000,
                    tokens_consumed INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_issues (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    key TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    issue_type TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    parent_id TEXT,
                    assignee_principal TEXT,
                    appetite_tokens INTEGER NOT NULL DEFAULT 50000,
                    appetite_timeout_s INTEGER NOT NULL DEFAULT 1800,
                    tokens_spent INTEGER NOT NULL DEFAULT 0,
                    reflexion_attempts INTEGER NOT NULL DEFAULT 0,
                    path_whitelist JSON,
                    forbidden_paths JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES pm_projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(parent_id) REFERENCES pm_issues(id) ON DELETE SET NULL
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    triggered_by TEXT NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_evidence_links (
                    id TEXT PRIMARY KEY,
                    issue_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    uri TEXT NOT NULL,
                    payload JSON,
                    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_critic_verdicts (
                    id TEXT PRIMARY KEY,
                    issue_id TEXT NOT NULL,
                    reviewer_principal TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    findings JSON NOT NULL,
                    signature TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_dependencies (
                    blocker_id TEXT NOT NULL,
                    blocked_id TEXT NOT NULL,
                    PRIMARY KEY(blocker_id, blocked_id),
                    FOREIGN KEY(blocker_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                    FOREIGN KEY(blocked_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_cfd_snapshots (
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    project_id TEXT NOT NULL,
                    backlog_count INTEGER NOT NULL,
                    refined_count INTEGER NOT NULL,
                    staged_count INTEGER NOT NULL,
                    in_progress_count INTEGER NOT NULL,
                    verification_count INTEGER NOT NULL,
                    judicial_review_count INTEGER NOT NULL,
                    done_count INTEGER NOT NULL
                );
                """)

                # PM-DATA-001: Transactional Sequence Table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_project_sequences (
                    project_key TEXT PRIMARY KEY,
                    last_sequence INTEGER NOT NULL DEFAULT 0
                );
                """)

                # Hybrid Scrum: Sprints Table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_sprints (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    goal TEXT,
                    state TEXT NOT NULL CHECK(state IN ('FUTURE', 'ACTIVE', 'CLOSED')),
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES pm_projects(id) ON DELETE CASCADE
                );
                """)

                # SBA-02: Repository project sources
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_project_sources (
                    project_id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    repository_owner TEXT NOT NULL,
                    repository_name TEXT NOT NULL,
                    configured_branch TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    planning_path TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    source_revision TEXT,
                    last_successful_sync TIMESTAMP,
                    last_error TEXT,
                    is_stale INTEGER NOT NULL DEFAULT 0,
                    remote_project_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES pm_projects(id) ON DELETE CASCADE
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_project_sources_status ON pm_project_sources(status);")

                # SBA-01 / SBA-02: Deployment task mappings
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_task_mappings (
                    project_id TEXT NOT NULL REFERENCES pm_projects(id) ON DELETE CASCADE,
                    planning_reference TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    local_issue_id TEXT NOT NULL REFERENCES pm_issues(id) ON DELETE CASCADE,
                    local_issue_key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT pk_task_mapping PRIMARY KEY (project_id, planning_reference),
                    CONSTRAINT uq_task_mapping_task_id UNIQUE (project_id, task_id),
                    CONSTRAINT uq_task_mapping_local_issue UNIQUE (project_id, local_issue_id),
                    CONSTRAINT uq_task_mapping_local_key UNIQUE (project_id, local_issue_key)
                );
                """)

                # SBA-05: Authenticated browser sessions
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_sessions (
                    token_hash TEXT PRIMARY KEY,
                    csrf_token TEXT NOT NULL,
                    principal TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    permitted_actions JSON NOT NULL,
                    iam_token_hash TEXT,
                    iam_session_id TEXT,
                    iam_expires_at REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at REAL NOT NULL,
                    is_revoked INTEGER NOT NULL DEFAULT 0
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_sessions_principal ON pm_sessions(principal);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_sessions_revoked ON pm_sessions(is_revoked);")

                # SBA-03: Plan publication and optimistic concurrency
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_plans (
                    project_id TEXT NOT NULL REFERENCES pm_projects(id) ON DELETE CASCADE,
                    plan_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    source_commit TEXT,
                    scope_reference TEXT,
                    published_by TEXT NOT NULL,
                    tasks_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT pk_pm_plans PRIMARY KEY (project_id, plan_id, revision)
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_plans_project_rev ON pm_plans(project_id, revision);")

                # SBA-03: Idempotency keys scoped to (tenant_id, action, idempotency_key)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_idempotency_keys (
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_code INTEGER NOT NULL,
                    response_body TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tenant_id, action, idempotency_key)
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_idempotency_tenant_action ON pm_idempotency_keys(tenant_id, action);")

                # Migrations for existing tables
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN priority TEXT DEFAULT 'MEDIUM';")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN sprint_id TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN rework_cycle INTEGER DEFAULT 0;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN blocker_reason TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN task_id TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN planning_reference TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN acceptance_criteria JSON;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN proposed_delivery_owner TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN reviewer_requirement TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN proposed_budget_tokens INTEGER DEFAULT 0;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN staged_acceptance_criteria JSON;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN staged_path_whitelist JSON;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN staged_reviewer_requirement TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN staged_reviewer_action TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN policy_version INTEGER NOT NULL DEFAULT 1;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN staged_proposal_id TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN staged_proposal_rev INTEGER;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN has_pending_reconciliation INTEGER DEFAULT 0;")
                except sqlite3.OperationalError:
                    pass

                # SBA-03: Durable reconciliation audit trail
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_reconciliation_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    issue_key TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    proposal_id TEXT,
                    proposal_rev INTEGER,
                    base_policy_version INTEGER NOT NULL,
                    resulting_policy_version INTEGER NOT NULL,
                    before_policy JSON NOT NULL,
                    after_policy JSON NOT NULL,
                    evidence_invalidated_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_recon_audits_issue ON pm_reconciliation_audits(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pm_recon_audits_project ON pm_reconciliation_audits(project_id);")
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN sprint_id TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN rework_cycle INTEGER DEFAULT 0;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_issues ADD COLUMN blocker_reason TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_critic_verdicts ADD COLUMN rework_cycle INTEGER DEFAULT 0;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_critic_verdicts ADD COLUMN commit_sha TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_sessions ADD COLUMN iam_session_id TEXT;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_sessions ADD COLUMN iam_expires_at REAL;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_sessions ADD COLUMN issued_roles JSON;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_sessions ADD COLUMN issued_scopes JSON;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_project_sources ADD COLUMN remote_project_id TEXT;")
                except sqlite3.OperationalError:
                    pass

                # Indices
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_state ON pm_issues(current_state);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_project ON pm_issues(project_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_assignee ON pm_issues(assignee_principal);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_sprint ON pm_issues(sprint_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_transitions_issue ON pm_transitions(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_issue ON pm_evidence_links(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_project_sources_remote_id ON pm_project_sources(remote_project_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_verdicts_issue ON pm_critic_verdicts(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_task_id ON pm_issues(project_id, task_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_planning_ref ON pm_issues(project_id, planning_reference);")

                # GOV-03: Immutable evidence triggers
                conn.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_prevent_evidence_update
                BEFORE UPDATE ON pm_evidence_links
                BEGIN
                    SELECT RAISE(ABORT, 'TamperViolationError: Evidence records are immutable and cannot be updated.');
                END;
                """)
                conn.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_prevent_evidence_delete
                BEFORE DELETE ON pm_evidence_links
                BEGIN
                    SELECT RAISE(ABORT, 'TamperViolationError: Evidence records are immutable and cannot be deleted.');
                END;
                """)

                # GOV-04: Separation of duties persistence trigger (prevent self-review)
                conn.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_prevent_self_review
                BEFORE INSERT ON pm_critic_verdicts
                BEGIN
                SELECT CASE
                        WHEN NEW.reviewer_principal = (SELECT assignee_principal FROM pm_issues WHERE id = NEW.issue_id)
                        THEN RAISE(ABORT, 'SeparationOfDutiesViolation: Issue assignee cannot record a review verdict on their own work.')
                    END;
                END;
                """)

                # CC-02 / CC-03: Additive column migration for pm_task_mappings using PRAGMA inspection
                cols = [r[1] for r in conn.execute("PRAGMA table_info(pm_task_mappings);").fetchall()]
                if "legacy_task_id" not in cols:
                    conn.execute("ALTER TABLE pm_task_mappings ADD COLUMN legacy_task_id TEXT;")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_task_mappings_legacy ON pm_task_mappings(legacy_task_id);")

                # Schema versioning ledger table
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """)
        finally:
            conn.close()

        # Run CC-03 versioned migration
        self.migrate_coordinator_schema()

    def migrate_coordinator_schema(self) -> None:
        """
        Executes CC-03 transactional migration in an atomic BEGIN IMMEDIATE block.
        Inspects existing tables, upgrades old CC-03 schemas, rebuilds tables with validated
        temporary tables for composite foreign keys, verifies foreign_key_check and integrity_check,
        computes migration checksum, and commits atomically.
        """
        CC_03_VERSION = 2026101201
        CC_03_NAME = "cc_03_coordinator_state"
        CC_03_CHECKSUM = "cc03_sha256_composite_ownership_v1"

        conn = self._get_connection()
        with self._lock:
            # Disable foreign keys outside transaction so dropping table during rebuild does not trigger cascade deletion
            conn.execute("PRAGMA foreign_keys=OFF;")
            conn.execute("BEGIN IMMEDIATE;")
            try:
                # 1. Recheck ledger under lock
                applied = conn.execute(
                    "SELECT version, checksum FROM pm_schema_migrations WHERE version = ?",
                    (CC_03_VERSION,),
                ).fetchone()
                if applied:
                    if applied["checksum"] != CC_03_CHECKSUM:
                        raise sqlite3.DatabaseError(
                            f"Migration checksum mismatch: recorded '{applied['checksum']}', expected '{CC_03_CHECKSUM}'"
                        )
                    conn.execute("COMMIT;")
                    conn.execute("PRAGMA foreign_keys=ON;")
                    return

                existing_tables = {
                    r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
                }

                # CC-02 / CC-03: Mapping and issue identity indices
                conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_coord_mapping_identity
                ON pm_task_mappings(project_id, task_id, local_issue_id);
                """)
                conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_coord_issue_project
                ON pm_issues(project_id, id);
                """)

                # 2. pm_coordinator_attempts
                if "pm_coordinator_attempts" not in existing_tables:
                    conn.execute("""
                    CREATE TABLE pm_coordinator_attempts (
                        attempt_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        issue_id TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        attempt_seq INTEGER NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN_EXECUTION', 'CANCELED')),
                        fencing_token INTEGER NOT NULL DEFAULT 1,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        finished_at TIMESTAMP,
                        budget_tokens_allocated INTEGER NOT NULL DEFAULT 0,
                        budget_tokens_spent INTEGER NOT NULL DEFAULT 0,
                        candidate_commit_sha TEXT,
                        failure_reason TEXT,
                        FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                        FOREIGN KEY(project_id, task_id, issue_id)
                            REFERENCES pm_task_mappings(project_id, task_id, local_issue_id),
                        FOREIGN KEY(project_id, issue_id) REFERENCES pm_issues(project_id, id),
                        CONSTRAINT uq_attempt_identity UNIQUE (attempt_id, issue_id, task_id, project_id, tenant_id),
                        CONSTRAINT uq_issue_attempt_seq UNIQUE (issue_id, attempt_seq)
                    );
                    """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_attempts_issue ON pm_coordinator_attempts(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_attempts_task ON pm_coordinator_attempts(task_id);")

                # 3. pm_coordinator_intents: ensure uq_intent_attempt_pair exists
                if "pm_coordinator_intents" not in existing_tables:
                    conn.execute("""
                    CREATE TABLE pm_coordinator_intents (
                        intent_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        project_id TEXT NOT NULL,
                        issue_id TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        attempt_id TEXT NOT NULL,
                        adapter_type TEXT NOT NULL CHECK(adapter_type IN ('antigravity', 'codex', 'synthetic')),
                        status TEXT NOT NULL CHECK(status IN ('PENDING', 'CLAIMED', 'PROCESSING', 'COMPLETED', 'FAILED', 'UNKNOWN_EXECUTION', 'CANCELED', 'CANCEL_REQUESTED')),
                        fencing_token INTEGER NOT NULL DEFAULT 1,
                        worker_id TEXT,
                        lease_expires_at REAL,
                        lease_heartbeat_at REAL,
                        payload JSON NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                        FOREIGN KEY(attempt_id, issue_id, task_id, project_id, tenant_id)
                            REFERENCES pm_coordinator_attempts(attempt_id, issue_id, task_id, project_id, tenant_id),
                        CONSTRAINT uq_intent_issue_attempt UNIQUE (issue_id, attempt_id, adapter_type),
                        CONSTRAINT uq_intent_attempt_pair UNIQUE (intent_id, attempt_id)
                    );
                    """)
                else:
                    # Check if uq_intent_attempt_pair unique index or constraint exists
                    intent_indices = [
                        r[1] for r in conn.execute("PRAGMA index_list(pm_coordinator_intents);").fetchall()
                    ]
                    has_pair_uq = False
                    for idx_name in intent_indices:
                        idx_info = [
                            r[2] for r in conn.execute(f"PRAGMA index_info({idx_name});").fetchall()
                        ]
                        if idx_info == ["intent_id", "attempt_id"]:
                            has_pair_uq = True
                            break
                    if not has_pair_uq:
                        conn.execute("""
                        CREATE UNIQUE INDEX IF NOT EXISTS uq_intent_attempt_pair
                        ON pm_coordinator_intents(intent_id, attempt_id);
                        """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_intents_status ON pm_coordinator_intents(status, lease_expires_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_intents_task ON pm_coordinator_intents(task_id);")

                # 4. pm_coordinator_runs: must have composite FK (intent_id, attempt_id) -> pm_coordinator_intents(intent_id, attempt_id)
                rebuild_runs = False
                if "pm_coordinator_runs" not in existing_tables:
                    rebuild_runs = True
                else:
                    from collections import defaultdict
                    fk_groups = defaultdict(list)
                    for fk in conn.execute("PRAGMA foreign_key_list(pm_coordinator_runs);").fetchall():
                        fk_groups[fk["id"]].append(fk)
                    has_composite_intent_attempt_fk = False
                    for fks in fk_groups.values():
                        if fks[0]["table"] == "pm_coordinator_intents":
                            from_cols = {f["from"] for f in fks}
                            if {"intent_id", "attempt_id"}.issubset(from_cols):
                                has_composite_intent_attempt_fk = True
                                break
                    if not has_composite_intent_attempt_fk:
                        rebuild_runs = True

                if rebuild_runs:
                    if "pm_coordinator_runs" in existing_tables:
                        # Check for contradictory ownership before rebuilding
                        mismatched = conn.execute("""
                            SELECT r.run_id, r.intent_id, r.attempt_id, i.attempt_id AS actual_att
                            FROM pm_coordinator_runs r
                            JOIN pm_coordinator_intents i ON r.intent_id = i.intent_id
                            WHERE r.attempt_id != i.attempt_id
                        """).fetchall()
                        if mismatched:
                            raise sqlite3.IntegrityError(
                                f"Cannot migrate pm_coordinator_runs: contradictory attempt ownership detected: {mismatched}"
                            )

                    conn.execute("""
                    CREATE TABLE IF NOT EXISTS pm_coordinator_runs_new (
                        run_id TEXT PRIMARY KEY,
                        intent_id TEXT NOT NULL,
                        attempt_id TEXT NOT NULL,
                        fencing_token INTEGER NOT NULL,
                        runtime_session_id TEXT,
                        process_pid INTEGER,
                        process_pgid INTEGER,
                        status TEXT NOT NULL CHECK(status IN ('SPAWNING', 'STREAMING', 'EXITED', 'INTERRUPTED', 'KILLED')),
                        exit_code INTEGER,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ended_at TIMESTAMP,
                        FOREIGN KEY(intent_id, attempt_id)
                            REFERENCES pm_coordinator_intents(intent_id, attempt_id) ON DELETE CASCADE,
                        CONSTRAINT uq_physical_dispatch UNIQUE (intent_id, fencing_token)
                    );
                    """)
                    if "pm_coordinator_runs" in existing_tables:
                        old_cols = {
                            r[1] for r in conn.execute("PRAGMA table_info(pm_coordinator_runs);").fetchall()
                        }
                        runtime_session_expr = "runtime_session_id" if "runtime_session_id" in old_cols else "NULL"
                        pid_expr = "process_pid" if "process_pid" in old_cols else ("pid" if "pid" in old_cols else "NULL")
                        pgid_expr = "process_pgid" if "process_pgid" in old_cols else "NULL"
                        ended_expr = "ended_at" if "ended_at" in old_cols else ("finished_at" if "finished_at" in old_cols else "NULL")

                        conn.execute(f"""
                        INSERT INTO pm_coordinator_runs_new (
                            run_id, intent_id, attempt_id, fencing_token, runtime_session_id,
                            process_pid, process_pgid, status, exit_code, started_at, ended_at
                        )
                        SELECT run_id, intent_id, attempt_id, fencing_token, {runtime_session_expr},
                               {pid_expr}, {pgid_expr}, status, exit_code, started_at, {ended_expr}
                        FROM pm_coordinator_runs;
                        """)
                        conn.execute("DROP TABLE pm_coordinator_runs;")
                    conn.execute("ALTER TABLE pm_coordinator_runs_new RENAME TO pm_coordinator_runs;")

                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_runs_attempt ON pm_coordinator_runs(attempt_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_runs_intent ON pm_coordinator_runs(intent_id);")

                # 5. pm_coordinator_events
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_coordinator_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    cursor_seq INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_payload JSON NOT NULL,
                    emitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(run_id) REFERENCES pm_coordinator_runs(run_id) ON DELETE CASCADE,
                    CONSTRAINT uq_run_cursor UNIQUE (run_id, cursor_seq)
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_events_run ON pm_coordinator_events(run_id, cursor_seq);")

                # 6. pm_coordinator_evidence_receipts: ensure admission_status column exists
                if "pm_coordinator_evidence_receipts" not in existing_tables:
                    conn.execute("""
                    CREATE TABLE pm_coordinator_evidence_receipts (
                        evidence_id TEXT PRIMARY KEY,
                        issue_id TEXT NOT NULL,
                        task_id TEXT NOT NULL,
                        attempt_id TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        candidate_commit_sha TEXT NOT NULL,
                        nonce TEXT NOT NULL UNIQUE,
                        key_id TEXT NOT NULL,
                        signature TEXT NOT NULL,
                        canonical_payload JSON NOT NULL,
                        admission_status TEXT NOT NULL DEFAULT 'SUBMITTED' CHECK(admission_status IN ('SUBMITTED', 'ADMITTED', 'REJECTED')),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                        FOREIGN KEY(attempt_id) REFERENCES pm_coordinator_attempts(attempt_id) ON DELETE CASCADE,
                        FOREIGN KEY(run_id) REFERENCES pm_coordinator_runs(run_id) ON DELETE CASCADE
                    );
                    """)
                else:
                    receipt_cols = [
                        r[1] for r in conn.execute("PRAGMA table_info(pm_coordinator_evidence_receipts);").fetchall()
                    ]
                    if "admission_status" not in receipt_cols:
                        conn.execute("ALTER TABLE pm_coordinator_evidence_receipts ADD COLUMN admission_status TEXT NOT NULL DEFAULT 'SUBMITTED';")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_evidence_issue ON pm_coordinator_evidence_receipts(issue_id);")

                # 7. pm_coordinator_reservations
                conn.execute("""
                CREATE TABLE IF NOT EXISTS pm_coordinator_reservations (
                    reservation_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    authorization_ref TEXT NOT NULL,
                    amount INTEGER NOT NULL CHECK(amount >= 0),
                    settled_amount INTEGER NOT NULL DEFAULT 0 CHECK(settled_amount >= 0),
                    status TEXT NOT NULL CHECK(status IN ('HELD', 'SETTLED', 'RELEASED')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settled_at TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                    FOREIGN KEY(attempt_id) REFERENCES pm_coordinator_attempts(attempt_id) ON DELETE CASCADE
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_reservations_project ON pm_coordinator_reservations(project_id, status);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_coord_reservations_attempt ON pm_coordinator_reservations(attempt_id);")

                # 8. Foreign key integrity and PRAGMA integrity checks
                fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()
                if fk_violations:
                    raise sqlite3.IntegrityError(f"Foreign key integrity check failed after migration: {fk_violations}")

                integrity = conn.execute("PRAGMA integrity_check;").fetchone()
                if not integrity or integrity[0] != "ok":
                    raise sqlite3.DatabaseError(f"Integrity check failed: {integrity}")

                # 9. Record migration in ledger
                conn.execute(
                    """
                    INSERT INTO pm_schema_migrations (version, name, checksum)
                    VALUES (?, ?, ?)
                    """,
                    (CC_03_VERSION, CC_03_NAME, CC_03_CHECKSUM),
                )
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()


    # --- Project Operations ---

    def create_project(self, project: Project, conn: Optional[sqlite3.Connection] = None) -> Project:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                """
                INSERT INTO pm_projects (id, key, name, description, token_budget, tokens_consumed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project.id,
                    project.key.upper(),
                    project.name,
                    project.description,
                    project.token_budget,
                    project.tokens_consumed,
                    now,
                    now,
                ),
            )
            project.created_at = now
            project.updated_at = now
            return project
        finally:
            if manage_conn:
                c.close()

    def get_project_by_key(self, key: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Project]:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            cur = c.execute("SELECT * FROM pm_projects WHERE key = ?", (key.upper(),))
            row = cur.fetchone()
            if not row:
                return None
            return Project(
                id=row["id"],
                key=row["key"],
                name=row["name"],
                description=row["description"] or "",
                token_budget=row["token_budget"],
                tokens_consumed=row["tokens_consumed"],
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
        finally:
            if manage_conn:
                c.close()

    def get_project(self, project_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Project]:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            cur = c.execute("SELECT * FROM pm_projects WHERE id = ?", (project_id,))
            row = cur.fetchone()
            if not row:
                return None
            return Project(
                id=row["id"],
                key=row["key"],
                name=row["name"],
                description=row["description"] or "",
                token_budget=row["token_budget"],
                tokens_consumed=row["tokens_consumed"],
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )
        finally:
            if manage_conn:
                c.close()

    def list_projects(self, conn: Optional[sqlite3.Connection] = None, *, include_archived: bool = False) -> List[Project]:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            archived = c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pm_project_archives'").fetchone()
            query = "SELECT * FROM pm_projects"
            if archived and not include_archived:
                query += " WHERE NOT EXISTS (SELECT 1 FROM pm_project_archives a WHERE a.project_id=pm_projects.id)"
            cur = c.execute(query + " ORDER BY created_at ASC")
            rows = cur.fetchall()
            return [
                Project(
                    id=row["id"],
                    key=row["key"],
                    name=row["name"],
                    description=row["description"] or "",
                    token_budget=row["token_budget"],
                    tokens_consumed=row["tokens_consumed"],
                    created_at=str(row["created_at"]),
                    updated_at=str(row["updated_at"]),
                )
                for row in rows
            ]
        finally:
            if manage_conn:
                c.close()

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        token_budget: Optional[int] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[Project]:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            now = datetime.now(timezone.utc).isoformat()
            updates = ["updated_at = ?"]
            params: list[Any] = [now]
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if token_budget is not None:
                updates.append("token_budget = ?")
                params.append(token_budget)
            params.append(project_id)
            c.execute(
                f"UPDATE pm_projects SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            return self.get_project(project_id, conn=c)
        finally:
            if manage_conn:
                c.close()

    # --- Project Source Operations (SBA-02) ---

    @staticmethod
    def _source_from_row(row: sqlite3.Row) -> ProjectSource:
        keys = row.keys()
        return ProjectSource(
            project_id=row["project_id"],
            repository_id=row["repository_id"],
            repository_owner=row["repository_owner"],
            repository_name=row["repository_name"],
            configured_branch=row["configured_branch"],
            root_path=row["root_path"],
            planning_path=row["planning_path"],
            status=row["status"],
            source_revision=row["source_revision"],
            last_successful_sync=str(row["last_successful_sync"]) if row["last_successful_sync"] else None,
            last_error=row["last_error"],
            is_stale=bool(row["is_stale"]),
            remote_project_id=row["remote_project_id"] if "remote_project_id" in keys else None,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def upsert_project_source(self, source: ProjectSource, conn: Optional[sqlite3.Connection] = None) -> ProjectSource:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                """
                INSERT INTO pm_project_sources (
                    project_id, repository_id, repository_owner, repository_name, configured_branch,
                    root_path, planning_path, status, source_revision, last_successful_sync,
                    last_error, is_stale, remote_project_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    repository_id = excluded.repository_id,
                    repository_owner = excluded.repository_owner,
                    repository_name = excluded.repository_name,
                    configured_branch = excluded.configured_branch,
                    root_path = excluded.root_path,
                    planning_path = excluded.planning_path,
                    status = excluded.status,
                    source_revision = excluded.source_revision,
                    last_successful_sync = excluded.last_successful_sync,
                    last_error = excluded.last_error,
                    is_stale = excluded.is_stale,
                    remote_project_id = excluded.remote_project_id,
                    updated_at = excluded.updated_at
                """,
                (
                    source.project_id,
                    source.repository_id,
                    source.repository_owner,
                    source.repository_name,
                    source.configured_branch,
                    source.root_path,
                    source.planning_path,
                    source.status,
                    source.source_revision,
                    source.last_successful_sync or now,
                    source.last_error,
                    1 if source.is_stale else 0,
                    source.remote_project_id,
                    source.created_at or now,
                    now,
                ),
            )
            source.updated_at = now
            return source
        finally:
            if manage_conn:
                c.close()

    def get_project_source(self, project_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[ProjectSource]:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            cur = c.execute("SELECT * FROM pm_project_sources WHERE project_id = ?", (project_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._source_from_row(row)
        finally:
            if manage_conn:
                c.close()

    def get_project_source_by_remote_id(self, remote_project_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[ProjectSource]:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            cur = c.execute("SELECT * FROM pm_project_sources WHERE remote_project_id = ?", (remote_project_id,))
            row = cur.fetchone()
            if not row:
                return None
            return self._source_from_row(row)
        finally:
            if manage_conn:
                c.close()

    def list_project_sources(self, conn: Optional[sqlite3.Connection] = None) -> List[ProjectSource]:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            cur = c.execute("SELECT * FROM pm_project_sources ORDER BY created_at ASC")
            rows = cur.fetchall()
            return [self._source_from_row(row) for row in rows]
        finally:
            if manage_conn:
                c.close()

    def mark_project_source_inactive(self, project_id: str, conn: Optional[sqlite3.Connection] = None) -> None:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                "UPDATE pm_project_sources SET status = 'inactive', updated_at = ? WHERE project_id = ?",
                (now, project_id),
            )
        finally:
            if manage_conn:
                c.close()

    def update_project_source_error(self, project_id: str, error: str, is_stale: bool = True, conn: Optional[sqlite3.Connection] = None) -> None:
        manage_conn = conn is None
        c = self._get_connection() if manage_conn else conn
        try:
            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                "UPDATE pm_project_sources SET last_error = ?, is_stale = ?, updated_at = ? WHERE project_id = ?",
                (error, 1 if is_stale else 0, now, project_id),
            )
        finally:
            if manage_conn:
                c.close()

    # --- Task Mapping Operations (SBA-01 / SBA-02 / SBA-03) ---

    def upsert_task_mapping(
        self,
        mapping: TaskMapping,
        conn: Optional[sqlite3.Connection] = None,
    ) -> TaskMapping:
        now = datetime.now(timezone.utc).isoformat()
        def _execute(c: sqlite3.Connection) -> None:
            c.execute(
                """
                INSERT INTO pm_task_mappings (
                    project_id, planning_reference, task_id, local_issue_id, local_issue_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, planning_reference) DO UPDATE SET
                    task_id = excluded.task_id,
                    local_issue_id = excluded.local_issue_id,
                    local_issue_key = excluded.local_issue_key,
                    updated_at = excluded.updated_at
                """,
                (
                    mapping.project_id,
                    mapping.planning_reference,
                    mapping.task_id,
                    mapping.local_issue_id,
                    mapping.local_issue_key,
                    mapping.created_at or now,
                    now,
                ),
            )
            mapping.updated_at = now

        if conn is not None:
            _execute(conn)
        else:
            with self.atomic_transaction() as c:
                _execute(c)
        return mapping

    def get_task_mapping(
        self,
        project_id: str,
        planning_reference: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[TaskMapping]:
        def _execute(c: sqlite3.Connection) -> Optional[TaskMapping]:
            cur = c.execute(
                "SELECT * FROM pm_task_mappings WHERE project_id = ? AND planning_reference = ?",
                (project_id, planning_reference),
            )
            row = cur.fetchone()
            if not row:
                return None
            return TaskMapping(
                project_id=row["project_id"],
                planning_reference=row["planning_reference"],
                task_id=row["task_id"],
                local_issue_id=row["local_issue_id"],
                local_issue_key=row["local_issue_key"],
                legacy_task_id=row["legacy_task_id"] if "legacy_task_id" in row.keys() else None,
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )

        if conn is not None:
            return _execute(conn)
        c = self._get_connection()
        try:
            return _execute(c)
        finally:
            c.close()

    def get_task_mapping_by_task_id(
        self,
        project_id: str,
        task_id: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[TaskMapping]:
        def _execute(c: sqlite3.Connection) -> Optional[TaskMapping]:
            cur = c.execute(
                "SELECT * FROM pm_task_mappings WHERE project_id = ? AND task_id = ?",
                (project_id, task_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return TaskMapping(
                project_id=row["project_id"],
                planning_reference=row["planning_reference"],
                task_id=row["task_id"],
                local_issue_id=row["local_issue_id"],
                local_issue_key=row["local_issue_key"],
                legacy_task_id=row["legacy_task_id"] if "legacy_task_id" in row.keys() else None,
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
            )

        if conn is not None:
            return _execute(conn)
        c = self._get_connection()
        try:
            return _execute(c)
        finally:
            c.close()

    def list_task_mappings(
        self,
        project_id: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[TaskMapping]:
        def _execute(c: sqlite3.Connection) -> List[TaskMapping]:
            cur = c.execute(
                "SELECT * FROM pm_task_mappings WHERE project_id = ? ORDER BY planning_reference ASC",
                (project_id,),
            )
            rows = cur.fetchall()
            return [
                TaskMapping(
                    project_id=row["project_id"],
                    planning_reference=row["planning_reference"],
                    task_id=row["task_id"],
                    local_issue_id=row["local_issue_id"],
                    local_issue_key=row["local_issue_key"],
                    legacy_task_id=row["legacy_task_id"] if "legacy_task_id" in row.keys() else None,
                    created_at=str(row["created_at"]),
                    updated_at=str(row["updated_at"]),
                )
                for row in rows
            ]

        if conn is not None:
            return _execute(conn)
        c = self._get_connection()
        try:
            return _execute(c)
        finally:
            c.close()

    # --- Issue Operations ---

    def create_issue(self, issue: Issue, conn: Optional[sqlite3.Connection] = None) -> Issue:
        now = datetime.now(timezone.utc).isoformat()
        def _execute(c: sqlite3.Connection) -> None:
            c.execute(
                """
                INSERT INTO pm_issues (
                    id, project_id, key, title, description, issue_type, current_state,
                    priority, sprint_id, parent_id, assignee_principal, appetite_tokens, appetite_timeout_s,
                    tokens_spent, reflexion_attempts, rework_cycle, blocker_reason, path_whitelist, forbidden_paths,
                    task_id, planning_reference, acceptance_criteria, proposed_delivery_owner, reviewer_requirement,
                    proposed_budget_tokens, staged_acceptance_criteria, staged_path_whitelist, staged_reviewer_requirement,
                    staged_reviewer_action, policy_version, staged_proposal_id, staged_proposal_rev,
                    has_pending_reconciliation, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    issue.id,
                    issue.project_id,
                    issue.key,
                    issue.title,
                    issue.description,
                    issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type),
                    issue.current_state.value if hasattr(issue.current_state, "value") else str(issue.current_state),
                    issue.priority.value if hasattr(issue.priority, "value") else str(issue.priority),
                    issue.sprint_id,
                    issue.parent_id,
                    issue.assignee_principal,
                    issue.appetite_tokens,
                    issue.appetite_timeout_s,
                    issue.tokens_spent,
                    issue.reflexion_attempts,
                    issue.rework_cycle,
                    issue.blocker_reason,
                    json.dumps(issue.path_whitelist),
                    json.dumps(issue.forbidden_paths),
                    issue.task_id,
                    issue.planning_reference,
                    json.dumps(issue.acceptance_criteria),
                    issue.proposed_delivery_owner,
                    issue.reviewer_requirement,
                    issue.proposed_budget_tokens if issue.proposed_budget_tokens is not None else 0,
                    json.dumps(issue.staged_acceptance_criteria) if issue.staged_acceptance_criteria is not None else None,
                    json.dumps(issue.staged_path_whitelist) if issue.staged_path_whitelist is not None else None,
                    issue.staged_reviewer_requirement,
                    issue.staged_reviewer_action,
                    issue.policy_version or 1,
                    issue.staged_proposal_id,
                    issue.staged_proposal_rev,
                    1 if issue.has_pending_reconciliation else 0,
                    issue.created_at or now,
                    now,
                ),
            )
            issue.created_at = issue.created_at or now
            issue.updated_at = now

        if conn is not None:
            _execute(conn)
        else:
            with self.atomic_transaction() as c:
                _execute(c)
        return issue

    def get_issue(self, issue_id_or_key: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Issue]:
        def _execute(c: sqlite3.Connection) -> Optional[Issue]:
            cur = c.execute(
                "SELECT * FROM pm_issues WHERE id = ? OR key = ?",
                (issue_id_or_key, issue_id_or_key.upper()),
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_issue(row)

        if conn is not None:
            return _execute(conn)
        c = self._get_connection()
        try:
            return _execute(c)
        finally:
            c.close()

    def update_issue_from_plan(
        self,
        issue_id: str,
        title: str,
        description: str,
        issue_type: IssueType,
        priority: PriorityLevel,
        parent_id: Optional[str],
        path_whitelist: List[str],
        acceptance_criteria: List[str],
        proposed_delivery_owner: Optional[str],
        reviewer_requirement: Optional[str],
        proposed_budget_tokens: Optional[int],
        staged_acceptance_criteria: Optional[List[str]] = None,
        staged_path_whitelist: Optional[List[str]] = None,
        staged_reviewer_requirement: Optional[str] = None,
        staged_reviewer_action: Optional[str] = None,
        staged_proposal_id: Optional[str] = None,
        staged_proposal_rev: Optional[int] = None,
        has_pending_reconciliation: bool = False,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """Updates plan-defined fields of an issue, preserving runtime state, tokens, and active assignment."""
        def _execute(c: sqlite3.Connection) -> None:
            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                """
                UPDATE pm_issues
                SET title = ?, description = ?, issue_type = ?, priority = ?, parent_id = ?,
                    path_whitelist = ?, acceptance_criteria = ?, proposed_delivery_owner = ?,
                    reviewer_requirement = ?, proposed_budget_tokens = ?,
                    staged_acceptance_criteria = ?, staged_path_whitelist = ?,
                    staged_reviewer_requirement = ?, staged_reviewer_action = ?,
                    staged_proposal_id = ?, staged_proposal_rev = ?,
                    has_pending_reconciliation = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    title,
                    description,
                    issue_type.value if hasattr(issue_type, "value") else str(issue_type),
                    priority.value if hasattr(priority, "value") else str(priority),
                    parent_id,
                    json.dumps(path_whitelist),
                    json.dumps(acceptance_criteria),
                    proposed_delivery_owner,
                    reviewer_requirement,
                    proposed_budget_tokens,
                    json.dumps(staged_acceptance_criteria) if staged_acceptance_criteria is not None else None,
                    json.dumps(staged_path_whitelist) if staged_path_whitelist is not None else None,
                    staged_reviewer_requirement,
                    staged_reviewer_action,
                    staged_proposal_id,
                    staged_proposal_rev,
                    1 if has_pending_reconciliation else 0,
                    now,
                    issue_id,
                ),
            )

        if conn is not None:
            _execute(conn)
        else:
            with self.atomic_transaction() as c:
                _execute(c)

    def list_issues(self, project_id: Optional[str] = None, state: Optional[str] = None) -> List[Issue]:
        conn = self._get_connection()
        try:
            query = "SELECT * FROM pm_issues WHERE 1=1"
            params: List[Any] = []
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            if state:
                query += " AND current_state = ?"
                params.append(state)
            query += " ORDER BY created_at ASC"
            cur = conn.execute(query, params)
            return [self._row_to_issue(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def count_issues_in_state(self, project_id: str, state: str, conn: Optional[sqlite3.Connection] = None) -> int:
        c = conn or self._get_connection()
        try:
            cur = c.execute(
                "SELECT COUNT(*) as cnt FROM pm_issues WHERE project_id = ? AND current_state = ?",
                (project_id, state),
            )
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0
        finally:
            if conn is None:
                c.close()

    def count_agent_active_issues(self, assignee_principal: str, conn: Optional[sqlite3.Connection] = None) -> int:
        c = conn or self._get_connection()
        try:
            cur = c.execute(
                "SELECT COUNT(*) as cnt FROM pm_issues WHERE assignee_principal = ? AND current_state = 'IN_PROGRESS'",
                (assignee_principal,),
            )
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0
        finally:
            if conn is None:
                c.close()

    def update_issue_state(
        self,
        issue_id: str,
        new_state: str,
        triggered_by: str,
        reason: str = "",
        increment_reflexion: bool = False,
        increment_rework_cycle: bool = False,
        blocker_reason: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """Atomic state update with transition audit log and rework cycle tracking."""
        def _execute_update(c: sqlite3.Connection) -> None:
            cur = c.execute(
                "SELECT current_state, reflexion_attempts, rework_cycle FROM pm_issues WHERE id = ?",
                (issue_id,),
            )
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Issue {issue_id} not found")
            old_state = row["current_state"]
            reflexion = row["reflexion_attempts"]
            rework = row["rework_cycle"] if "rework_cycle" in row.keys() else 0
            if increment_reflexion:
                reflexion += 1
            if increment_rework_cycle:
                rework += 1

            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                """
                UPDATE pm_issues
                SET current_state = ?, reflexion_attempts = ?, rework_cycle = ?, blocker_reason = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_state, reflexion, rework, blocker_reason, now, issue_id),
            )
            c.execute(
                """
                INSERT INTO pm_transitions (issue_id, from_state, to_state, triggered_by, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (issue_id, old_state, new_state, triggered_by, reason, now),
            )

        if conn is not None:
            _execute_update(conn)
        else:
            with self.atomic_transaction() as c:
                _execute_update(c)

    def update_issue_assignee(
        self,
        issue_id: str,
        assignee_principal: Optional[str],
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """Atomic issue assignee update."""
        def _execute_update(c: sqlite3.Connection) -> None:
            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                """
                UPDATE pm_issues
                SET assignee_principal = ?, updated_at = ?
                WHERE id = ? OR key = ?
                """,
                (assignee_principal, now, issue_id, issue_id),
            )

        if conn is not None:
            _execute_update(conn)
        else:
            with self.atomic_transaction() as c:
                _execute_update(c)

    def next_issue_key(self, project_key: str, conn: Optional[sqlite3.Connection] = None) -> str:
        """
        PM-DATA-001: Computes the next incremental sequence issue key using atomic transaction.
        """
        pkey = project_key.upper()
        def _allocate(c: sqlite3.Connection) -> str:
            cur_max = c.execute(
                """
                SELECT COALESCE(MAX(CAST(SUBSTR(key, INSTR(key, '-') + 1) AS INTEGER)), 0) AS max_seq
                FROM pm_issues
                WHERE key LIKE ? || '-%';
                """,
                (pkey,),
            )
            row_max = cur_max.fetchone()
            max_existing = int(row_max["max_seq"]) if row_max else 0

            c.execute(
                """
                INSERT INTO pm_project_sequences (project_key, last_sequence)
                VALUES (?, ?)
                ON CONFLICT(project_key) DO UPDATE SET
                    last_sequence = MAX(last_sequence, excluded.last_sequence);
                """,
                (pkey, max_existing),
            )
            cur = c.execute(
                """
                UPDATE pm_project_sequences
                SET last_sequence = last_sequence + 1
                WHERE project_key = ?
                RETURNING last_sequence;
                """,
                (pkey,),
            )
            row = cur.fetchone()
            seq = int(row["last_sequence"]) if row else (max_existing + 1)
            return f"{pkey}-{seq}"

        if conn is not None:
            return _allocate(conn)
        with self.atomic_transaction() as c:
            return _allocate(c)

    # --- Plan Record & Idempotency Operations (SBA-03) ---

    def create_plan_record(self, record: PlanRecord, conn: Optional[sqlite3.Connection] = None) -> PlanRecord:
        def _execute(c: sqlite3.Connection) -> None:
            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                """
                INSERT INTO pm_plans (
                    project_id, plan_id, revision, source_commit, scope_reference,
                    published_by, tasks_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.project_id,
                    record.plan_id,
                    record.revision,
                    record.source_commit,
                    record.scope_reference,
                    record.published_by,
                    record.tasks_count,
                    record.created_at or now,
                ),
            )
            record.created_at = record.created_at or now

        if conn is not None:
            _execute(conn)
        else:
            with self.atomic_transaction() as c:
                _execute(c)
        return record

    def get_latest_plan_revision(
        self,
        project_id: str,
        plan_id: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[PlanRecord]:
        def _execute(c: sqlite3.Connection) -> Optional[PlanRecord]:
            cur = c.execute(
                """
                SELECT * FROM pm_plans
                WHERE project_id = ? AND plan_id = ?
                ORDER BY revision DESC
                LIMIT 1
                """,
                (project_id, plan_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            return PlanRecord(
                project_id=row["project_id"],
                plan_id=row["plan_id"],
                revision=int(row["revision"]),
                source_commit=row["source_commit"],
                scope_reference=row["scope_reference"],
                published_by=row["published_by"],
                tasks_count=int(row["tasks_count"]),
                created_at=str(row["created_at"]),
            )

        if conn is not None:
            return _execute(conn)
        c = self._get_connection()
        try:
            return _execute(c)
        finally:
            c.close()

    def get_idempotency_record(
        self,
        tenant_id: str,
        action: str,
        idempotency_key: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> Optional[Dict[str, Any]]:
        def _execute(c: sqlite3.Connection) -> Optional[Dict[str, Any]]:
            cur = c.execute(
                """
                SELECT * FROM pm_idempotency_keys
                WHERE tenant_id = ? AND action = ? AND idempotency_key = ?
                """,
                (tenant_id, action, idempotency_key),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "tenant_id": row["tenant_id"],
                "action": row["action"],
                "idempotency_key": row["idempotency_key"],
                "request_hash": row["request_hash"],
                "response_code": int(row["response_code"]),
                "response_body": row["response_body"],
                "created_at": str(row["created_at"]),
            }

        if conn is not None:
            return _execute(conn)
        c = self._get_connection()
        try:
            return _execute(c)
        finally:
            c.close()

    def save_idempotency_record(
        self,
        tenant_id: str,
        action: str,
        idempotency_key: str,
        request_hash: str,
        response_code: int,
        response_body: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        def _execute(c: sqlite3.Connection) -> None:
            now = datetime.now(timezone.utc).isoformat()
            c.execute(
                """
                INSERT INTO pm_idempotency_keys (
                    tenant_id, action, idempotency_key, request_hash, response_code, response_body, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, action, idempotency_key) DO UPDATE SET
                    request_hash = excluded.request_hash,
                    response_code = excluded.response_code,
                    response_body = excluded.response_body
                """,
                (tenant_id, action, idempotency_key, request_hash, response_code, response_body, now),
            )

        if conn is not None:
            _execute(conn)
        else:
            with self.atomic_transaction() as c:
                _execute(c)

    # --- Dependency Operations (PM-07) ---

    def add_dependency(
        self,
        blocker_id_or_key: str,
        blocked_id_or_key: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> None:
        """
        PM-07: Registers a directed dependency edge.
        The blocked issue cannot enter active execution until blocker issue is in DONE state.
        """
        def _execute(c: sqlite3.Connection) -> None:
            cur1 = c.execute("SELECT id FROM pm_issues WHERE id = ? OR key = ?", (blocker_id_or_key, blocker_id_or_key.upper()))
            row1 = cur1.fetchone()
            if not row1:
                raise ValueError(f"Blocker issue '{blocker_id_or_key}' not found.")
            blocker_id = row1["id"]

            cur2 = c.execute("SELECT id FROM pm_issues WHERE id = ? OR key = ?", (blocked_id_or_key, blocked_id_or_key.upper()))
            row2 = cur2.fetchone()
            if not row2:
                raise ValueError(f"Blocked issue '{blocked_id_or_key}' not found.")
            blocked_id = row2["id"]

            if blocker_id == blocked_id:
                raise ValueError("An issue cannot depend on itself.")

            c.execute(
                """
                INSERT INTO pm_dependencies (blocker_id, blocked_id)
                VALUES (?, ?)
                ON CONFLICT(blocker_id, blocked_id) DO NOTHING;
                """,
                (blocker_id, blocked_id),
            )

        if conn is not None:
            _execute(conn)
        else:
            with self.atomic_transaction() as c:
                _execute(c)

    def get_dependencies(
        self,
        issue_id_or_key: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Issue]:
        """PM-07: Returns all blocker issues that this issue depends on."""
        query = """
            SELECT b.* FROM pm_issues b
            JOIN pm_dependencies d ON b.id = d.blocker_id
            JOIN pm_issues i ON d.blocked_id = i.id
            WHERE i.id = ? OR i.key = ?
            ORDER BY b.key ASC
        """
        def _execute(c: sqlite3.Connection) -> List[Issue]:
            cur = c.execute(query, (issue_id_or_key, issue_id_or_key.upper()))
            return [self._row_to_issue(r) for r in cur.fetchall()]

        if conn is not None:
            return _execute(conn)
        conn = self._get_connection()
        return _execute(conn)

    def get_unresolved_dependencies(
        self,
        issue_id_or_key: str,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[Issue]:
        """PM-07: Returns all blocker issues that are not yet in DONE state."""
        deps = self.get_dependencies(issue_id_or_key, conn=conn)
        return [d for d in deps if d.current_state != IssueState.DONE]

    # --- Evidence Operations ---

    def attach_evidence(self, evidence: EvidenceLink) -> EvidenceLink:
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
            # Attachment is a claim, not proof of execution under today's policy.
            # Callers must supply the policy they actually measured.
            if type(evidence.payload.get("policy_version")) is not int or evidence.payload["policy_version"] < 1:
                raise ValueError("Evidence requires an explicit positive integer policy_version")
            ev_type = evidence.evidence_type.value if hasattr(evidence.evidence_type, "value") else str(evidence.evidence_type)
            if ev_type == "GIT_COMMIT":
                candidate = evidence.content_hash or evidence.uri.removeprefix("git:commit:")
                supplied = evidence.payload.get("candidate_commit_sha", candidate)
                if supplied != candidate:
                    raise ValueError("Git evidence candidate binding contradicts its immutable reference")
                evidence.payload["candidate_commit_sha"] = candidate
            if ev_type == "TEST_RUN_LOG" and not (
                isinstance(evidence.payload.get("candidate_commit_sha"), str)
                and evidence.payload["candidate_commit_sha"].strip()
            ):
                raise ValueError("Test evidence requires an explicit candidate_commit_sha")
            if evidence.payload.get("provenance_signature") and evidence.payload.get("provenance_version") != 2:
                raise ValueError("Legacy signatures cannot admit new evidence; retain legacy records as history")
            evidence.payload["provenance_version"] = 2
            if not evidence.payload.get("provenance_signature"):
                from mas.security import sign_evidence_provenance
                ev_type_val = evidence.evidence_type.value if hasattr(evidence.evidence_type, "value") else str(evidence.evidence_type)
                evidence.payload["provenance_signature"] = sign_evidence_provenance(
                    evidence_id=evidence.id,
                    issue_id=evidence.issue_id,
                    evidence_type=ev_type_val,
                    content_hash=evidence.content_hash,
                    uri=evidence.uri,
                    binding_payload=evidence.payload,
                )
            else:
                from mas.security import verify_evidence_provenance
                if not verify_evidence_provenance(
                    evidence.id, evidence.issue_id, ev_type, evidence.content_hash, evidence.uri,
                    evidence.payload["provenance_signature"], binding_payload=evidence.payload,
                ):
                    raise ValueError("Evidence signature does not match its bound payload")
            with conn:
                conn.execute(
                    """
                    INSERT INTO pm_evidence_links (id, issue_id, evidence_type, content_hash, uri, payload, linked_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        evidence.id,
                        evidence.issue_id,
                        evidence.evidence_type.value if hasattr(evidence.evidence_type, "value") else str(evidence.evidence_type),
                        evidence.content_hash,
                        evidence.uri,
                        json.dumps(evidence.payload),
                        now,
                    ),
                )
            evidence.linked_at = now
            return evidence
        finally:
            conn.close()

    def get_evidence_links(self, issue_id: str) -> List[EvidenceLink]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM pm_evidence_links WHERE issue_id = ? ORDER BY linked_at ASC", (issue_id,))
            results = []
            for r in cur.fetchall():
                payload = json.loads(r["payload"]) if r["payload"] else {}
                results.append(
                    EvidenceLink(
                        id=r["id"],
                        issue_id=r["issue_id"],
                        evidence_type=EvidenceType(r["evidence_type"]),
                        content_hash=r["content_hash"],
                        uri=r["uri"],
                        payload=payload,
                        linked_at=str(r["linked_at"]),
                    )
                )
            return results
        finally:
            conn.close()

    def verify_issue_evidence_integrity(self, issue_id: str, workspace_root: Optional[Any] = None) -> dict[str, Any]:
        """
        GOV-03: Audits evidence provenance and integrity for an issue.
        Verifies HMAC signatures and content hashes against disk/git.
        """
        import hashlib
        from pathlib import Path
        from mas.security import verify_evidence_provenance

        links = self.get_evidence_links(issue_id)
        report: dict[str, Any] = {
            "issue_id": issue_id,
            "total_links": len(links),
            "valid": True,
            "items": [],
            "anomalies": [],
        }
        root = (workspace_root or Path.cwd()).resolve()

        for lnk in links:
            ev_type_val = lnk.evidence_type.value if hasattr(lnk.evidence_type, "value") else str(lnk.evidence_type)
            item_status = {"id": lnk.id, "type": ev_type_val, "uri": lnk.uri, "signature_valid": False, "hash_valid": True}

            sig = lnk.payload.get("provenance_signature")
            if sig:
                item_status["signature_valid"] = verify_evidence_provenance(
                    evidence_id=lnk.id,
                    issue_id=lnk.issue_id,
                    evidence_type=ev_type_val,
                    content_hash=lnk.content_hash,
                    uri=lnk.uri,
                    signature=sig,
                    binding_payload=lnk.payload if lnk.payload.get("provenance_version") == 2 else None,
                )
                if not item_status["signature_valid"]:
                    report["valid"] = False
                    report["anomalies"].append(f"Provenance signature mismatch for evidence {lnk.id}")
            else:
                item_status["signature_valid"] = False
                report["valid"] = False
                report["anomalies"].append(f"Missing provenance signature for evidence {lnk.id}")

            if lnk.evidence_type == EvidenceType.TEST_RUN_LOG:
                clean_uri = lnk.uri.replace("file://", "")
                p = Path(clean_uri)
                if not p.is_absolute():
                    p = root / p
                if not p.is_file():
                    report["valid"] = False
                    item_status["hash_valid"] = False
                    report["anomalies"].append(f"Evidence file '{clean_uri}' does not exist on disk")
                else:
                    calc = hashlib.sha256(p.read_bytes()).hexdigest()
                    if calc.lower() != lnk.content_hash.lower():
                        report["valid"] = False
                        item_status["hash_valid"] = False
                        report["anomalies"].append(
                            f"Content hash mismatch for {clean_uri}: recorded={lnk.content_hash}, calculated={calc}"
                        )

            report["items"].append(item_status)

        return report

    # --- Critic Verdict Operations ---

    def record_verdict(self, verdict: CriticVerdict, enforce_auth: bool = True) -> CriticVerdict:
        conn = self._get_connection()
        try:
            if enforce_auth:
                from mas.security import ExecutionContext
                auth_principal = ExecutionContext.resolve_authenticated_principal()
                if auth_principal != verdict.reviewer_principal:
                    raise PermissionError(
                        f"UnauthorizedVerdictError: Authenticated principal '{auth_principal}' "
                        f"cannot record verdict for reviewer '{verdict.reviewer_principal}'."
                    )
                cur = conn.execute("SELECT key, assignee_principal FROM pm_issues WHERE id = ?", (verdict.issue_id,))
                issue_row = cur.fetchone()
                if issue_row and issue_row["assignee_principal"]:
                    if issue_row["assignee_principal"] == verdict.reviewer_principal:
                        raise PermissionError(
                            f"SeparationOfDutiesError: Assignee '{issue_row['assignee_principal']}' "
                            f"cannot record a review verdict on their own issue {issue_row['key']}."
                        )

            now = datetime.now(timezone.utc).isoformat()
            if verdict.rework_cycle == 0:
                cur = conn.execute("SELECT rework_cycle FROM pm_issues WHERE id = ?", (verdict.issue_id,))
                row = cur.fetchone()
                if row and "rework_cycle" in row.keys() and row["rework_cycle"] is not None:
                    verdict.rework_cycle = int(row["rework_cycle"])

            verdict_val = verdict.verdict.value if hasattr(verdict.verdict, "value") else str(verdict.verdict)
            if not verdict.signature or verdict.signature.startswith("unsigned:"):
                from mas.security import sign_verdict_payload
                verdict.signature = sign_verdict_payload(
                    issue_id=verdict.issue_id,
                    reviewer_principal=verdict.reviewer_principal,
                    verdict_value=verdict_val,
                    rework_cycle=verdict.rework_cycle,
                    commit_sha=verdict.commit_sha,
                    findings=verdict.findings,
                )

            with conn:
                conn.execute(
                    """
                    INSERT INTO pm_critic_verdicts (
                        id, issue_id, reviewer_principal, verdict, findings, signature, rework_cycle, commit_sha, timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        verdict.id,
                        verdict.issue_id,
                        verdict.reviewer_principal,
                        verdict_val,
                        json.dumps(verdict.findings),
                        verdict.signature,
                        verdict.rework_cycle,
                        verdict.commit_sha,
                        now,
                    ),
                )
            verdict.timestamp = now
            return verdict
        finally:
            conn.close()

    def get_verdicts(self, issue_id: str, rework_cycle: Optional[int] = None) -> List[CriticVerdict]:
        conn = self._get_connection()
        try:
            if rework_cycle is not None:
                cur = conn.execute(
                    "SELECT * FROM pm_critic_verdicts WHERE issue_id = ? AND rework_cycle = ? ORDER BY timestamp ASC",
                    (issue_id, rework_cycle),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM pm_critic_verdicts WHERE issue_id = ? ORDER BY timestamp ASC",
                    (issue_id,),
                )
            results = []
            for r in cur.fetchall():
                findings = json.loads(r["findings"]) if r["findings"] else {}
                results.append(
                    CriticVerdict(
                        id=r["id"],
                        issue_id=r["issue_id"],
                        reviewer_principal=r["reviewer_principal"],
                        verdict=CriticVerdictType(r["verdict"]),
                        findings=findings,
                        signature=r["signature"],
                        rework_cycle=int(r["rework_cycle"]) if ("rework_cycle" in r.keys() and r["rework_cycle"] is not None) else 0,
                        commit_sha=r["commit_sha"] if "commit_sha" in r.keys() else None,
                        timestamp=str(r["timestamp"]),
                    )
                )
            return results
        finally:
            conn.close()

    # --- Sprint Operations (Scrum Layer) ---

    def create_sprint(self, sprint: Sprint) -> Sprint:
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute(
                    """
                    INSERT INTO pm_sprints (id, project_id, name, goal, state, start_date, end_date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sprint.id,
                        sprint.project_id,
                        sprint.name,
                        sprint.goal,
                        sprint.state.value if hasattr(sprint.state, "value") else str(sprint.state),
                        sprint.start_date,
                        sprint.end_date,
                        now,
                    ),
                )
            sprint.created_at = now
            return sprint
        finally:
            conn.close()

    def get_sprint(self, sprint_id: str) -> Optional[Sprint]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM pm_sprints WHERE id = ?", (sprint_id,))
            row = cur.fetchone()
            if not row:
                return None
            return Sprint(
                id=row["id"],
                project_id=row["project_id"],
                name=row["name"],
                goal=row["goal"] or "",
                state=SprintState(row["state"]),
                start_date=row["start_date"],
                end_date=row["end_date"],
                created_at=str(row["created_at"]),
            )
        finally:
            conn.close()

    def list_sprints(self, project_id: str) -> List[Sprint]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM pm_sprints WHERE project_id = ? ORDER BY created_at ASC", (project_id,))
            results = []
            for row in cur.fetchall():
                results.append(
                    Sprint(
                        id=row["id"],
                        project_id=row["project_id"],
                        name=row["name"],
                        goal=row["goal"] or "",
                        state=SprintState(row["state"]),
                        start_date=row["start_date"],
                        end_date=row["end_date"],
                        created_at=str(row["created_at"]),
                    )
                )
            return results
        finally:
            conn.close()

    def update_sprint_state(self, sprint_id: str, state: SprintState) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    "UPDATE pm_sprints SET state = ? WHERE id = ?",
                    (state.value if hasattr(state, "value") else str(state), sprint_id),
                )
        finally:
            conn.close()

    def assign_issue_to_sprint(self, issue_id: str, sprint_id: Optional[str]) -> None:
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute(
                    "UPDATE pm_issues SET sprint_id = ?, updated_at = ? WHERE id = ?",
                    (sprint_id, now, issue_id),
                )
        finally:
            conn.close()

    def _row_to_issue(self, row: sqlite3.Row) -> Issue:
        path_whitelist = json.loads(row["path_whitelist"]) if row["path_whitelist"] else []
        forbidden_paths = json.loads(row["forbidden_paths"]) if row["forbidden_paths"] else []
        acceptance_criteria = (
            json.loads(row["acceptance_criteria"])
            if ("acceptance_criteria" in row.keys() and row["acceptance_criteria"])
            else []
        )
        staged_acceptance_criteria = (
            json.loads(row["staged_acceptance_criteria"])
            if ("staged_acceptance_criteria" in row.keys() and row["staged_acceptance_criteria"])
            else None
        )
        staged_path_whitelist = (
            json.loads(row["staged_path_whitelist"])
            if ("staged_path_whitelist" in row.keys() and row["staged_path_whitelist"])
            else None
        )
        staged_reviewer_requirement = row["staged_reviewer_requirement"] if "staged_reviewer_requirement" in row.keys() else None
        staged_reviewer_action = row["staged_reviewer_action"] if "staged_reviewer_action" in row.keys() else None
        policy_version = int(row["policy_version"]) if ("policy_version" in row.keys() and row["policy_version"] is not None) else 1
        staged_proposal_id = row["staged_proposal_id"] if "staged_proposal_id" in row.keys() else None
        staged_proposal_rev = int(row["staged_proposal_rev"]) if ("staged_proposal_rev" in row.keys() and row["staged_proposal_rev"] is not None) else None
        has_pending_reconciliation = bool(row["has_pending_reconciliation"]) if "has_pending_reconciliation" in row.keys() else False

        return Issue(
            id=row["id"],
            project_id=row["project_id"],
            key=row["key"],
            title=row["title"],
            description=row["description"] or "",
            issue_type=IssueType(row["issue_type"]),
            current_state=IssueState(row["current_state"]),
            priority=PriorityLevel(row["priority"]) if ("priority" in row.keys() and row["priority"]) else PriorityLevel.MEDIUM,
            sprint_id=row["sprint_id"] if "sprint_id" in row.keys() else None,
            parent_id=row["parent_id"],
            assignee_principal=row["assignee_principal"],
            appetite_tokens=row["appetite_tokens"],
            appetite_timeout_s=row["appetite_timeout_s"],
            tokens_spent=row["tokens_spent"],
            reflexion_attempts=row["reflexion_attempts"],
            rework_cycle=int(row["rework_cycle"]) if ("rework_cycle" in row.keys() and row["rework_cycle"] is not None) else 0,
            blocker_reason=row["blocker_reason"] if "blocker_reason" in row.keys() else None,
            path_whitelist=path_whitelist,
            forbidden_paths=forbidden_paths,
            task_id=row["task_id"] if "task_id" in row.keys() else None,
            planning_reference=row["planning_reference"] if "planning_reference" in row.keys() else None,
            acceptance_criteria=acceptance_criteria,
            proposed_delivery_owner=row["proposed_delivery_owner"] if "proposed_delivery_owner" in row.keys() else None,
            reviewer_requirement=row["reviewer_requirement"] if "reviewer_requirement" in row.keys() else None,
            proposed_budget_tokens=row["proposed_budget_tokens"] if "proposed_budget_tokens" in row.keys() else None,
            staged_acceptance_criteria=staged_acceptance_criteria,
            staged_path_whitelist=staged_path_whitelist,
            staged_reviewer_requirement=staged_reviewer_requirement,
            staged_reviewer_action=staged_reviewer_action,
            policy_version=policy_version,
            staged_proposal_id=staged_proposal_id,
            staged_proposal_rev=staged_proposal_rev,
            has_pending_reconciliation=has_pending_reconciliation,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def record_reconciliation_audit(
        self,
        audit: ReconciliationAuditRecord,
        conn: Optional[sqlite3.Connection] = None,
    ) -> ReconciliationAuditRecord:
        """Records an immutable reconciliation audit log entry."""
        def _execute(c: sqlite3.Connection) -> None:
            now = datetime.now(timezone.utc).isoformat()
            cur = c.execute(
                """
                INSERT INTO pm_reconciliation_audits (
                    tenant_id, project_id, issue_id, issue_key, decision, actor,
                    proposal_id, proposal_rev, base_policy_version, resulting_policy_version,
                    before_policy, after_policy, evidence_invalidated_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit.tenant_id,
                    audit.project_id,
                    audit.issue_id,
                    audit.issue_key,
                    audit.decision,
                    audit.actor,
                    audit.proposal_id,
                    audit.proposal_rev,
                    audit.base_policy_version,
                    audit.resulting_policy_version,
                    json.dumps(audit.before_policy),
                    json.dumps(audit.after_policy),
                    audit.evidence_invalidated_count,
                    audit.created_at or now,
                ),
            )
            audit.id = cur.lastrowid
            audit.created_at = audit.created_at or now

        if conn is not None:
            _execute(conn)
        else:
            with self.atomic_transaction() as c:
                _execute(c)
        return audit

    def list_reconciliation_audits(
        self,
        issue_id: Optional[str] = None,
        project_id: Optional[str] = None,
        conn: Optional[sqlite3.Connection] = None,
    ) -> List[ReconciliationAuditRecord]:
        """Lists reconciliation audit records for an issue or project."""
        c = conn or self._get_connection()
        try:
            query = "SELECT * FROM pm_reconciliation_audits WHERE 1=1"
            params: List[Any] = []
            if issue_id:
                query += " AND issue_id = ?"
                params.append(issue_id)
            if project_id:
                query += " AND project_id = ?"
                params.append(project_id)
            query += " ORDER BY created_at ASC, id ASC"
            cur = c.execute(query, params)
            rows = cur.fetchall()
            results: List[ReconciliationAuditRecord] = []
            for r in rows:
                results.append(ReconciliationAuditRecord(
                    id=r["id"],
                    tenant_id=r["tenant_id"],
                    project_id=r["project_id"],
                    issue_id=r["issue_id"],
                    issue_key=r["issue_key"],
                    decision=r["decision"],
                    actor=r["actor"],
                    proposal_id=r["proposal_id"],
                    proposal_rev=r["proposal_rev"],
                    base_policy_version=r["base_policy_version"],
                    resulting_policy_version=r["resulting_policy_version"],
                    before_policy=json.loads(r["before_policy"]),
                    after_policy=json.loads(r["after_policy"]),
                    evidence_invalidated_count=r["evidence_invalidated_count"],
                    created_at=str(r["created_at"]),
                ))
            return results
        finally:
            if conn is None:
                c.close()

