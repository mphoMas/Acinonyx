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
    PriorityLevel,
    Project,
    Sprint,
    SprintState,
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
                    conn.execute("ALTER TABLE pm_critic_verdicts ADD COLUMN rework_cycle INTEGER DEFAULT 0;")
                except sqlite3.OperationalError:
                    pass
                try:
                    conn.execute("ALTER TABLE pm_critic_verdicts ADD COLUMN commit_sha TEXT;")
                except sqlite3.OperationalError:
                    pass

                # Indices
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_state ON pm_issues(current_state);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_project ON pm_issues(project_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_assignee ON pm_issues(assignee_principal);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_sprint ON pm_issues(sprint_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_transitions_issue ON pm_transitions(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_evidence_issue ON pm_evidence_links(issue_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_verdicts_issue ON pm_critic_verdicts(issue_id);")

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

    def get_project(self, project_id: str) -> Optional[Project]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM pm_projects WHERE id = ?", (project_id,))
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

    def list_projects(self) -> List[Project]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM pm_projects ORDER BY created_at ASC")
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
                        priority, sprint_id, parent_id, assignee_principal, appetite_tokens, appetite_timeout_s,
                        tokens_spent, reflexion_attempts, rework_cycle, blocker_reason, path_whitelist, forbidden_paths,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def next_issue_key(self, project_key: str) -> str:
        """
        PM-DATA-001: Computes the next incremental sequence issue key using atomic transaction.
        """
        pkey = project_key.upper()
        with self.atomic_transaction() as conn:
            conn.execute(
                """
                INSERT INTO pm_project_sequences (project_key, last_sequence)
                VALUES (?, 0)
                ON CONFLICT(project_key) DO NOTHING;
                """,
                (pkey,),
            )
            cur = conn.execute(
                """
                UPDATE pm_project_sequences
                SET last_sequence = last_sequence + 1
                WHERE project_key = ?
                RETURNING last_sequence;
                """,
                (pkey,),
            )
            row = cur.fetchone()
            seq = int(row["last_sequence"]) if row else 1
            return f"{pkey}-{seq}"

    # --- Evidence Operations ---

    def attach_evidence(self, evidence: EvidenceLink) -> EvidenceLink:
        conn = self._get_connection()
        try:
            now = datetime.now(timezone.utc).isoformat()
            if not evidence.payload.get("provenance_signature"):
                from mas.security import sign_evidence_provenance
                ev_type_val = evidence.evidence_type.value if hasattr(evidence.evidence_type, "value") else str(evidence.evidence_type)
                evidence.payload["provenance_signature"] = sign_evidence_provenance(
                    evidence_id=evidence.id,
                    issue_id=evidence.issue_id,
                    evidence_type=ev_type_val,
                    content_hash=evidence.content_hash,
                    uri=evidence.uri,
                )
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

    def verify_issue_evidence_integrity(self, issue_id: str, workspace_root: Optional[Any] = None) -> Dict[str, Any]:
        """
        GOV-03: Audits evidence provenance and integrity for an issue.
        Verifies HMAC signatures and content hashes against disk/git.
        """
        import hashlib
        from pathlib import Path
        from mas.security import verify_evidence_provenance

        links = self.get_evidence_links(issue_id)
        report: Dict[str, Any] = {
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
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
