"""
mas.pm.db: Embedded SQLite persistence layer for the MAS Project Management Engine.
Enforces WAL mode, foreign keys, 5000ms busy timeout, and atomic transactions.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, List, Optional

from mas.pm.models import (
    CriticVerdict,
    CriticVerdictType,
    EvidenceLink,
    EvidenceType,
    Issue,
    IssueState,
    IssueType,
    Project,
)

DEFAULT_DB_PATH = Path("mas_pm.db")


class PMDatabase:
    """Thread-safe SQLite database manager for MAS-PM."""

    def __init__(self, db_path: Optional[Path | str] = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._lock = threading.Lock()
        self.init_schema()

    def _get_connection(self) -> sqlite3.Connection:
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

                # Indices
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_state ON pm_issues(current_state);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_project ON pm_issues(project_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_assignee ON pm_issues(assignee_principal);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_transitions_issue ON pm_transitions(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_issue ON pm_evidence_links(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_verdicts_issue ON pm_critic_verdicts(issue_id);")
        finally:
            conn.close()

    # --- Project Operations ---

    def create_project(self, project: Project) -> Project:
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute(
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
            conn.close()

    def get_project_by_key(self, key: str) -> Optional[Project]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM pm_projects WHERE key = ?", (key.upper(),))
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
            conn.close()

    # --- Issue Operations ---

    def create_issue(self, issue: Issue) -> Issue:
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute(
                    """
                    INSERT INTO pm_issues (
                        id, project_id, key, title, description, issue_type, current_state,
                        parent_id, assignee_principal, appetite_tokens, appetite_timeout_s,
                        tokens_spent, reflexion_attempts, path_whitelist, forbidden_paths,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        issue.id,
                        issue.project_id,
                        issue.key,
                        issue.title,
                        issue.description,
                        issue.issue_type.value if hasattr(issue.issue_type, "value") else str(issue.issue_type),
                        issue.current_state.value if hasattr(issue.current_state, "value") else str(issue.current_state),
                        issue.parent_id,
                        issue.assignee_principal,
                        issue.appetite_tokens,
                        issue.appetite_timeout_s,
                        issue.tokens_spent,
                        issue.reflexion_attempts,
                        json.dumps(issue.path_whitelist),
                        json.dumps(issue.forbidden_paths),
                        now,
                        now,
                    ),
                )
            issue.created_at = now
            issue.updated_at = now
            return issue
        finally:
            conn.close()

    def get_issue(self, issue_id_or_key: str) -> Optional[Issue]:
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT * FROM pm_issues WHERE id = ? OR key = ?",
                (issue_id_or_key, issue_id_or_key.upper()),
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._row_to_issue(row)
        finally:
            conn.close()

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

    def count_issues_in_state(self, project_id: str, state: str) -> int:
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT COUNT(*) as cnt FROM pm_issues WHERE project_id = ? AND current_state = ?",
                (project_id, state),
            )
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0
        finally:
            conn.close()

    def count_agent_active_issues(self, assignee_principal: str) -> int:
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT COUNT(*) as cnt FROM pm_issues WHERE assignee_principal = ? AND current_state = 'IN_PROGRESS'",
                (assignee_principal,),
            )
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0
        finally:
            conn.close()

    def update_issue_state(
        self,
        issue_id: str,
        new_state: str,
        triggered_by: str,
        reason: str = "",
        increment_reflexion: bool = False,
    ) -> None:
        """Atomic state update with transition audit log."""
        with self.atomic_transaction() as conn:
            cur = conn.execute("SELECT current_state, reflexion_attempts FROM pm_issues WHERE id = ?", (issue_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"Issue {issue_id} not found")
            old_state = row["current_state"]
            reflexion = row["reflexion_attempts"]
            if increment_reflexion:
                reflexion += 1

            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                UPDATE pm_issues
                SET current_state = ?, reflexion_attempts = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_state, reflexion, now, issue_id),
            )
            conn.execute(
                """
                INSERT INTO pm_transitions (issue_id, from_state, to_state, triggered_by, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (issue_id, old_state, new_state, triggered_by, reason, now),
            )

    def next_issue_key(self, project_key: str) -> str:
        """Computes the next incremental issue key for a project (e.g. CORE-1, CORE-2)."""
        conn = self._get_connection()
        try:
            cur = conn.execute(
                "SELECT COUNT(*) as cnt FROM pm_issues WHERE key LIKE ?",
                (f"{project_key.upper()}-%",),
            )
            row = cur.fetchone()
            count = int(row["cnt"]) if row else 0
            return f"{project_key.upper()}-{count + 1}"
        finally:
            conn.close()

    # --- Evidence Operations ---

    def attach_evidence(self, evidence: EvidenceLink) -> EvidenceLink:
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
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

    # --- Critic Verdict Operations ---

    def record_verdict(self, verdict: CriticVerdict) -> CriticVerdict:
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
            with conn:
                conn.execute(
                    """
                    INSERT INTO pm_critic_verdicts (id, issue_id, reviewer_principal, verdict, findings, signature, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        verdict.id,
                        verdict.issue_id,
                        verdict.reviewer_principal,
                        verdict.verdict.value if hasattr(verdict.verdict, "value") else str(verdict.verdict),
                        json.dumps(verdict.findings),
                        verdict.signature,
                        now,
                    ),
                )
            verdict.timestamp = now
            return verdict
        finally:
            conn.close()

    def get_verdicts(self, issue_id: str) -> List[CriticVerdict]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM pm_critic_verdicts WHERE issue_id = ? ORDER BY timestamp ASC", (issue_id,))
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
                        timestamp=str(r["timestamp"]),
                    )
                )
            return results
        finally:
            conn.close()

    def _row_to_issue(self, row: sqlite3.Row) -> Issue:
        path_whitelist = json.loads(row["path_whitelist"]) if row["path_whitelist"] else []
        forbidden_paths = json.loads(row["forbidden_paths"]) if row["forbidden_paths"] else []
        return Issue(
            id=row["id"],
            project_id=row["project_id"],
            key=row["key"],
            title=row["title"],
            description=row["description"] or "",
            issue_type=IssueType(row["issue_type"]),
            current_state=IssueState(row["current_state"]),
            parent_id=row["parent_id"],
            assignee_principal=row["assignee_principal"],
            appetite_tokens=row["appetite_tokens"],
            appetite_timeout_s=row["appetite_timeout_s"],
            tokens_spent=row["tokens_spent"],
            reflexion_attempts=row["reflexion_attempts"],
            path_whitelist=path_whitelist,
            forbidden_paths=forbidden_paths,
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
