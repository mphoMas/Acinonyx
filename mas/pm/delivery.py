"""Durable, candidate-bound delivery gates for explicitly enrolled projects.

Metadata screening is not verification. Acceptance reuses the service-owned
EvidenceTrust, while uncertainty and funding remain owned by CoordinatorStore.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_ACTOR: ContextVar[str | None] = ContextVar("delivery_host_actor", default=None)
SHA = r"^[0-9a-f]{40}$"


class DeliveryGateError(ValueError):
    """Required delivery record, phase or version is unavailable."""


class StrictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, revalidate_instances="always")

    @model_validator(mode="after")
    def meaningful_strings(self):
        for name in type(self).model_fields:
            value = getattr(self, name)
            if isinstance(value, str) and name != "limitations" and not value.strip():
                raise ValueError("Nonblank " + name + " required")
        return self


class Requirement(StrictRecord):
    id: str = Field(min_length=1, max_length=80)
    rule: str = Field(min_length=1, max_length=2048)


class AcceptanceCheck(StrictRecord):
    id: str = Field(min_length=1, max_length=80)
    requirement_id: str = Field(min_length=1, max_length=80)
    command: str = Field(min_length=1, max_length=2048)
    expected: str = Field(min_length=1, max_length=2048)
    negative: bool


class DeliveryBrief(StrictRecord):
    base_sha: str = Field(pattern=SHA)
    suite_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy_version: int = Field(ge=1)
    coordinator: str = Field(min_length=1, max_length=128)
    builder: str = Field(min_length=1, max_length=128)
    verifier: str = Field(min_length=1, max_length=128)
    reviewer: str = Field(min_length=1, max_length=128)
    scope: list[str] = Field(min_length=1, max_length=64)
    requirements: list[Requirement] = Field(min_length=1, max_length=64)
    checks: list[AcceptanceCheck] = Field(min_length=1, max_length=128)
    critical: bool
    mechanism: str = Field(min_length=1, max_length=8192)

    @model_validator(mode="after")
    def consistent(self):
        if len({self.builder, self.verifier, self.reviewer, self.coordinator}) != 4:
            raise ValueError("Four distinct assigned principals required")
        reqs = {r.id for r in self.requirements}
        if len(reqs) != len(self.requirements) or len({c.id for c in self.checks}) != len(self.checks):
            raise ValueError("Unique requirement and check identities required")
        if any(c.requirement_id not in reqs for c in self.checks):
            raise ValueError("Unknown requirement in check")
        if any(
            not any(c.requirement_id == r and c.negative for c in self.checks)
            or not any(c.requirement_id == r and not c.negative for c in self.checks)
            for r in reqs
        ):
            raise ValueError("Each requirement needs positive and adverse-case checks")
        for path in self.scope:
            if not path.strip() or path.startswith("/") or "\\" in path or "\x00" in path or ".." in path.split("/") or path == "*":
                raise ValueError("Bounded relative path scope required")
        return self


class CheckObservation(StrictRecord):
    check_id: str = Field(min_length=1, max_length=80)
    outcome: Literal["PASSED", "FAILED", "SKIPPED", "UNAVAILABLE"]
    evidence_ref: str = Field(min_length=1, max_length=1024)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class Submission(StrictRecord):
    run_id: str = Field(min_length=1, max_length=128)
    candidate_sha: str = Field(pattern=SHA)
    observations: list[CheckObservation] = Field(max_length=128)
    closures: dict[str, list[str]] = Field(default_factory=dict, max_length=64)
    limitations: str = Field(max_length=8192)


class Finding(StrictRecord):
    id: str = Field(min_length=1, max_length=80)
    requirement_id: str = Field(min_length=1, max_length=80)
    reproduction: str = Field(min_length=1, max_length=4096)
    impact: str = Field(min_length=1, max_length=2048)
    closure_paths: list[str] = Field(min_length=1, max_length=64)


@contextmanager
def delivery_admin_actor(actor: str):
    """Trusted host-only identity; never derives authority from caller names."""
    from mas.pm.coordinator import is_trusted_coord_admin

    if not is_trusted_coord_admin() or not isinstance(actor, str) or not actor.strip():
        raise PermissionError("Explicit trusted coordinator administration required")
    token = _ACTOR.set(actor)
    try:
        yield
    finally:
        _ACTOR.reset(token)


DDL = """
CREATE TABLE pm_delivery_projects (
 project_id TEXT PRIMARY KEY REFERENCES pm_projects(id), tenant_id TEXT NOT NULL
);
CREATE TABLE pm_delivery_tasks (
 issue_id TEXT PRIMARY KEY REFERENCES pm_issues(id),
 project_id TEXT NOT NULL REFERENCES pm_delivery_projects(project_id), tenant_id TEXT NOT NULL,
 version INTEGER NOT NULL CHECK(version>0), revision INTEGER NOT NULL CHECK(revision>0),
 phase TEXT NOT NULL CHECK(phase IN ('DRAFT','READY','DISPATCHED','EXECUTING','AWAITING_SUBMISSION',
 'READINESS_RETURNED','IN_REVIEW','CHANGES_REQUESTED','RECURRENCE_PAUSED','DISPUTED','ACCEPTED','UNCERTAIN')),
 brief TEXT NOT NULL, reviewer_agreed INTEGER NOT NULL DEFAULT 0,
 builder_agreed INTEGER NOT NULL DEFAULT 0, submission_id INTEGER, paused_phase TEXT
);
CREATE TABLE pm_delivery_dispatches (
 intent_id TEXT PRIMARY KEY REFERENCES pm_coordinator_intents(intent_id),
 issue_id TEXT NOT NULL REFERENCES pm_delivery_tasks(issue_id), version INTEGER NOT NULL
);
CREATE TABLE pm_delivery_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, issue_id TEXT REFERENCES pm_delivery_tasks(issue_id),
 project_id TEXT NOT NULL REFERENCES pm_delivery_projects(project_id),
 actor TEXT NOT NULL, kind TEXT NOT NULL, body TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE pm_delivery_submissions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, issue_id TEXT NOT NULL REFERENCES pm_delivery_tasks(issue_id),
 version INTEGER NOT NULL, candidate TEXT NOT NULL, body TEXT NOT NULL, outcome TEXT NOT NULL,
 actor TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE pm_delivery_findings (
 issue_id TEXT NOT NULL REFERENCES pm_delivery_tasks(issue_id), finding_id TEXT NOT NULL,
 requirement_id TEXT NOT NULL, body TEXT NOT NULL, state TEXT NOT NULL,
 PRIMARY KEY(issue_id,finding_id)
);
CREATE TRIGGER pm_delivery_events_no_update BEFORE UPDATE ON pm_delivery_events
 BEGIN SELECT RAISE(ABORT,'Delivery events are immutable'); END;
CREATE TRIGGER pm_delivery_events_no_delete BEFORE DELETE ON pm_delivery_events
 BEGIN SELECT RAISE(ABORT,'Delivery events are immutable'); END;
CREATE TRIGGER pm_delivery_submissions_no_update BEFORE UPDATE ON pm_delivery_submissions
 BEGIN SELECT RAISE(ABORT,'Delivery submissions are immutable'); END;
CREATE TRIGGER pm_delivery_submissions_no_delete BEFORE DELETE ON pm_delivery_submissions
 BEGIN SELECT RAISE(ABORT,'Delivery submissions are immutable'); END;
"""


def migrate(db):
    """Separate content-checksummed additive migration; old identities untouched."""
    checksum = hashlib.sha256(DDL.encode()).hexdigest()
    statements = []
    statement = ""
    for line in DDL.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            statements.append(statement.strip())
            statement = ""
    with db.atomic_transaction() as conn:
        row = conn.execute("SELECT checksum FROM pm_schema_migrations WHERE version=2026101301").fetchone()
        if row:
            if row["checksum"] != checksum:
                raise DeliveryGateError("Delivery migration checksum mismatch")
            for stmt in statements:
                name = stmt.split()[2]
                observed = conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (name,)).fetchone()

                def normalize(sql):
                    return re.sub(r"\s+", "", sql).rstrip(";").lower()

                if not observed or normalize(observed["sql"]) != normalize(stmt):
                    raise DeliveryGateError("Delivery migration schema mismatch: " + name)
            return
        for stmt in statements:
            conn.execute(stmt)
        conn.execute("INSERT INTO pm_schema_migrations(version,name,checksum) VALUES(2026101301,'delivery_gate_v1',?)", (checksum,))


def _brief(row):
    return DeliveryBrief.model_validate(json.loads(row["brief"]))


def _fresh(conn, row):
    issue = conn.execute("SELECT * FROM pm_issues WHERE id=? AND project_id=?", (row["issue_id"], row["project_id"])).fetchone()
    brief = _brief(row)
    if not issue or issue["policy_version"] != brief.policy_version or issue["has_pending_reconciliation"]:
        raise DeliveryGateError("Stale delivery brief or pending plan reconciliation")
    if set(json.loads(issue["path_whitelist"])) != set(brief.scope):
        raise DeliveryGateError("Delivery scope no longer matches issue")
    return brief


def require_dispatch(conn, issue_id, tenant_id, *, intent_id=None):
    issue = conn.execute("SELECT project_id FROM pm_issues WHERE id=?", (issue_id,)).fetchone()
    if not issue:
        raise DeliveryGateError("Unknown delivery issue")
    enrolled = conn.execute("SELECT tenant_id FROM pm_delivery_projects WHERE project_id=?", (issue["project_id"],)).fetchone()
    if not enrolled:
        return None
    from mas.pm.coordinator import is_trusted_coord_admin
    from mas.tenancy import current_binding

    binding = current_binding()
    if not is_trusted_coord_admin():
        if binding is None:
            raise PermissionError("Authenticated delivery dispatch required")
        binding.require("delivery:dispatch")
    if tenant_id != enrolled["tenant_id"]:
        raise PermissionError("Delivery tenant mismatch")
    row = conn.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
    allowed = "DISPATCHED" if intent_id else "READY"
    if not row or row["phase"] != allowed or not row["reviewer_agreed"] or not row["builder_agreed"]:
        raise DeliveryGateError("Agreed, ready delivery brief required")
    _fresh(conn, row)
    if intent_id:
        dispatch = conn.execute(
            "SELECT version FROM pm_delivery_dispatches WHERE intent_id=? AND issue_id=?", (intent_id, issue_id)
        ).fetchone()
        if not dispatch or dispatch["version"] != row["version"]:
            raise DeliveryGateError("Missing or stale delivery dispatch binding")
    return row


def record_dispatch(conn, issue_id, tenant_id, intent_id):
    row = require_dispatch(conn, issue_id, tenant_id)
    if row:
        conn.execute("INSERT INTO pm_delivery_dispatches VALUES(?,?,?)", (intent_id, issue_id, row["version"]))
        conn.execute("UPDATE pm_delivery_tasks SET phase='DISPATCHED',revision=revision+1 WHERE issue_id=?", (issue_id,))
        _event(conn, row, "supervisor", "DISPATCH_ADMITTED", {"intent_id": intent_id})


def execution_phase(conn, issue_id, phase, body):
    row = conn.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
    if row:
        conn.execute("UPDATE pm_delivery_tasks SET phase=?,revision=revision+1 WHERE issue_id=?", (phase, issue_id))
        _event(conn, row, "supervisor", "EXECUTION_" + phase, body)


def require_execution(conn, issue_id, tenant_id, intent_id):
    enrolled = conn.execute(
        "SELECT p.tenant_id FROM pm_delivery_projects p JOIN pm_issues i ON i.project_id=p.project_id WHERE i.id=?", (issue_id,)
    ).fetchone()
    if not enrolled:
        return
    row = conn.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
    dispatch = conn.execute("SELECT version FROM pm_delivery_dispatches WHERE intent_id=? AND issue_id=?", (intent_id, issue_id)).fetchone()
    if (
        enrolled["tenant_id"] != tenant_id
        or not row
        or row["phase"] != "EXECUTING"
        or not dispatch
        or dispatch["version"] != row["version"]
    ):
        raise DeliveryGateError("Current delivery execution authorization unavailable")
    _fresh(conn, row)


def require_review(conn, issue_id, candidate):
    row = conn.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
    enrolled = conn.execute(
        "SELECT 1 FROM pm_delivery_projects p JOIN pm_issues i ON i.project_id=p.project_id WHERE i.id=?", (issue_id,)
    ).fetchone()
    if not enrolled:
        return None
    if not row or row["phase"] not in {"IN_REVIEW", "ACCEPTED"}:
        raise DeliveryGateError("Readiness-admitted candidate required before review evidence")
    _fresh(conn, row)
    submission = conn.execute("SELECT * FROM pm_delivery_submissions WHERE id=?", (row["submission_id"],)).fetchone()
    if not submission or submission["version"] != row["version"] or submission["candidate"] != candidate:
        raise DeliveryGateError("Review candidate mismatch")
    return row


def require_accepted(conn, issue_id, store):
    row = conn.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
    enrolled = conn.execute(
        "SELECT 1 FROM pm_delivery_projects p JOIN pm_issues i ON i.project_id=p.project_id WHERE i.id=?", (issue_id,)
    ).fetchone()
    if enrolled:
        if not row or row["phase"] != "ACCEPTED":
            raise DeliveryGateError("Independent delivery acceptance required before DONE")
        _fresh(conn, row)
        event = conn.execute(
            "SELECT body FROM pm_delivery_events WHERE issue_id=? AND kind='ACCEPTED' ORDER BY id DESC LIMIT 1", (issue_id,)
        ).fetchone()
        if not event or store._evidence_trust is None:
            raise DeliveryGateError("Current trusted acceptance evidence unavailable")
        evidence = json.loads(event["body"])
        for key in ("verification_id", "review_id"):
            store._evidence_trust._admit_in_transaction(store, evidence[key], conn)


def _event(conn, row, actor, kind, body):
    conn.execute(
        "INSERT INTO pm_delivery_events(issue_id,project_id,actor,kind,body) VALUES(?,?,?,?,?)",
        (row["issue_id"], row["project_id"], actor, kind, json.dumps(body, sort_keys=True)),
    )


class DeliveryService:
    def __init__(self, db):
        self.db = db

    def _actor(self, tenant, action):
        from mas.pm.coordinator import is_trusted_coord_admin
        from mas.tenancy import current_binding

        binding = current_binding()
        if binding:
            if binding.identity.tenant_id != tenant:
                raise PermissionError("Cross-tenant delivery operation")
            binding.require("storage:read" if action == "read" else "storage:write")
            binding.require("delivery:read")
            binding.require("delivery:" + action)
            return binding.identity.principal_id
        if is_trusted_coord_admin() and _ACTOR.get():
            return _ACTOR.get()
        raise PermissionError("Authenticated delivery actor required")

    def enroll(self, project_id, tenant_id):
        actor = self._actor(tenant_id, "coordinate")
        with self.db.atomic_transaction() as c:
            old = c.execute("SELECT tenant_id FROM pm_delivery_projects WHERE project_id=?", (project_id,)).fetchone()
            if old:
                if old["tenant_id"] != tenant_id:
                    raise PermissionError("Project already belongs to another delivery tenant")
                return
            if c.execute(
                "SELECT 1 FROM pm_coordinator_intents WHERE project_id=? AND status NOT IN ('COMPLETED','FAILED','CANCELED')", (project_id,)
            ).fetchone():
                raise DeliveryGateError("Resolve existing execution before enrollment")
            if c.execute("SELECT 1 FROM pm_coordinator_reservations WHERE project_id=? AND status='HELD'", (project_id,)).fetchone():
                raise DeliveryGateError("Resolve existing funding holds before enrollment")
            c.execute("INSERT INTO pm_delivery_projects VALUES(?,?)", (project_id, tenant_id))
            c.execute(
                "INSERT INTO pm_delivery_events(project_id,actor,kind,body) VALUES(?,?,?,?)",
                (project_id, actor, "PROJECT_ENROLLED", json.dumps({"tenant_id": tenant_id})),
            )

    def _load(self, c, issue_id, revision, action, role=None, *, fresh=True):
        if type(revision) is not int or revision < 1:
            raise DeliveryGateError("Explicit integer CAS revision required")
        row = c.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
        if not row:
            raise DeliveryGateError("Missing delivery brief")
        actor = self._actor(row["tenant_id"], action)
        if row["revision"] != revision:
            raise DeliveryGateError("Stale delivery revision")
        brief = _fresh(c, row) if fresh else _brief(row)
        if role and actor != getattr(brief, role):
            raise PermissionError("Caller is not assigned " + role)
        return row, brief, actor

    def establish(self, issue_id, brief, *, expected_revision=None, reason="Initial brief"):
        brief = DeliveryBrief.model_validate(brief).model_copy(deep=True)
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 4096:
            raise DeliveryGateError("Brief decision reason required")
        with self.db.atomic_transaction() as c:
            issue = c.execute("SELECT * FROM pm_issues WHERE id=?", (issue_id,)).fetchone()
            if not issue:
                raise DeliveryGateError("Unknown issue")
            project = c.execute("SELECT * FROM pm_delivery_projects WHERE project_id=?", (issue["project_id"],)).fetchone()
            if not project:
                raise DeliveryGateError("Enroll project first")
            actor = self._actor(project["tenant_id"], "coordinate")
            if actor != brief.coordinator:
                raise PermissionError("Only assigned coordinator may establish brief")
            old = c.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
            if old:
                self._load(c, issue_id, expected_revision, "coordinate", "coordinator", fresh=False)
                if old["phase"] not in {"DRAFT", "READY", "CHANGES_REQUESTED", "RECURRENCE_PAUSED", "READINESS_RETURNED"}:
                    raise DeliveryGateError("Cannot change active or accepted brief")
                if brief.builder != _brief(old).builder or brief.reviewer != _brief(old).reviewer or brief.verifier != _brief(old).verifier:
                    raise DeliveryGateError("Assigned roles immutable within this delivery")
            elif expected_revision is not None:
                raise DeliveryGateError("No previous revision exists")
            if c.execute(
                "SELECT 1 FROM pm_coordinator_intents WHERE issue_id=? AND status IN ('PENDING','CLAIMED','PROCESSING','CANCEL_REQUESTED','UNKNOWN_EXECUTION')",
                (issue_id,),
            ).fetchone():
                raise DeliveryGateError("Unresolved execution prohibits new brief")
            # Scope changes with open findings require explicit disposition before replacement.
            if (
                old
                and c.execute(
                    "SELECT 1 FROM pm_delivery_findings WHERE issue_id=? AND state NOT IN ('CLOSED','WITHDRAWN')", (issue_id,)
                ).fetchone()
            ):
                raise DeliveryGateError("Resolve findings before replacing requirement baseline")
            version = old["version"] + 1 if old else 1
            revision = old["revision"] + 1 if old else 1
            doc = brief.model_dump_json()
            c.execute(
                """INSERT INTO pm_delivery_tasks(issue_id,project_id,tenant_id,version,revision,phase,brief)
                VALUES(?,?,?,?,?,'DRAFT',?) ON CONFLICT(issue_id) DO UPDATE SET version=excluded.version,
                revision=excluded.revision,phase='DRAFT',brief=excluded.brief,reviewer_agreed=0,builder_agreed=0,submission_id=NULL""",
                (issue_id, issue["project_id"], project["tenant_id"], version, revision, doc),
            )
            row = c.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
            _fresh(c, row)
            _event(
                c,
                row,
                actor,
                "BRIEF_ESTABLISHED" if not old else "SCOPE_CHANGED",
                {"version": version, "brief": json.loads(doc), "reason": reason},
            )
        return self.get(issue_id)

    def agree(self, issue_id, revision, *, role, rationale):
        if role not in {"builder", "reviewer"} or not isinstance(rationale, str) or not rationale.strip() or len(rationale) > 4096:
            raise DeliveryGateError("Assigned agreement and rationale required")
        action = "submit" if role == "builder" else "review"
        with self.db.atomic_transaction() as c:
            row, _, actor = self._load(c, issue_id, revision, action, role)
            if row["phase"] != "DRAFT":
                raise DeliveryGateError("Brief agreement only in DRAFT")
            column = "builder_agreed" if role == "builder" else "reviewer_agreed"
            c.execute(f"UPDATE pm_delivery_tasks SET {column}=1,revision=revision+1 WHERE issue_id=?", (issue_id,))
            c.execute("UPDATE pm_delivery_tasks SET phase='READY' WHERE issue_id=? AND builder_agreed=1 AND reviewer_agreed=1", (issue_id,))
            _event(c, row, actor, "BRIEF_AGREED", {"role": role, "rationale": rationale})
        return self.get(issue_id)

    def submit(self, issue_id, revision, submission):
        submission = Submission.model_validate(submission).model_copy(deep=True)
        with self.db.atomic_transaction() as c:
            row, brief, actor = self._load(c, issue_id, revision, "submit", "builder")
            if row["phase"] not in {"AWAITING_SUBMISSION", "READINESS_RETURNED"}:
                raise DeliveryGateError("Successful execution required before submission")
            run = c.execute(
                """SELECT a.candidate_commit_sha,a.status,r.status AS run_status,r.exit_code,d.version,i.status AS intent_status,i.fencing_token,r.fencing_token AS run_fence
                FROM pm_coordinator_runs r JOIN pm_coordinator_attempts a ON a.attempt_id=r.attempt_id
                JOIN pm_delivery_dispatches d ON d.intent_id=r.intent_id
                JOIN pm_coordinator_intents i ON i.intent_id=r.intent_id
                WHERE r.run_id=? AND a.issue_id=? AND a.tenant_id=?""",
                (submission.run_id, issue_id, row["tenant_id"]),
            ).fetchone()
            if (
                not run
                or run["version"] != row["version"]
                or run["intent_status"] != "COMPLETED"
                or run["fencing_token"] != run["run_fence"]
                or run["status"] != "SUCCEEDED"
                or run["run_status"] != "EXITED"
                or run["exit_code"] != 0
                or run["candidate_commit_sha"] != submission.candidate_sha
            ):
                raise DeliveryGateError("Submission is not bound to successful current execution")
            observed = [o.check_id for o in submission.observations]
            if len(set(observed)) != len(observed) or any(k not in {x.id for x in brief.checks} for k in observed):
                raise DeliveryGateError("Duplicate or unknown check observations")
            open_findings = c.execute(
                "SELECT * FROM pm_delivery_findings WHERE issue_id=? AND state NOT IN ('CLOSED','WITHDRAWN')", (issue_id,)
            ).fetchall()
            missing = []
            if set(observed) != {x.id for x in brief.checks} or any(o.outcome != "PASSED" for o in submission.observations):
                missing.append("Missing or nonpassing check observations")
            if set(submission.closures) != {f["finding_id"] for f in open_findings}:
                missing.append("Incomplete finding closure coverage")
            for f in open_findings:
                required = json.loads(f["body"])["closure_paths"]
                if not set(required).issubset(set(submission.closures.get(f["finding_id"], []))):
                    missing.append("Incomplete related-path closure")
            outcome = "READINESS_RETURNED" if missing else "IN_REVIEW"
            sid = c.execute(
                "INSERT INTO pm_delivery_submissions(issue_id,version,candidate,body,outcome,actor) VALUES(?,?,?,?,?,?)",
                (issue_id, row["version"], submission.candidate_sha, submission.model_dump_json(), outcome, actor),
            ).lastrowid
            c.execute("UPDATE pm_delivery_tasks SET phase=?,revision=revision+1,submission_id=? WHERE issue_id=?", (outcome, sid, issue_id))
            _event(c, row, actor, outcome, {"submission_id": sid, "reasons": missing})
        return self.get(issue_id)

    def reject(self, issue_id, revision, findings):
        if not isinstance(findings, list) or not 1 <= len(findings) <= 64:
            raise DeliveryGateError("Explicit blocking findings required")
        findings = [Finding.model_validate(f) for f in findings]
        if len({f.id for f in findings}) != len(findings):
            raise DeliveryGateError("Unique findings required")
        with self.db.atomic_transaction() as c:
            row, brief, actor = self._load(c, issue_id, revision, "review", "reviewer")
            if row["phase"] != "IN_REVIEW":
                raise DeliveryGateError("Only readiness-admitted work may be formally rejected")
            if any(f.requirement_id not in {r.id for r in brief.requirements} for f in findings):
                raise DeliveryGateError("New requirement must be recorded as scope change, not rejection")
            current = c.execute("SELECT body FROM pm_delivery_submissions WHERE id=?", (row["submission_id"],)).fetchone()
            closures = json.loads(current["body"])["closures"]
            previous = c.execute("SELECT * FROM pm_delivery_findings WHERE issue_id=?", (issue_id,)).fetchall()
            recurring = any(p["finding_id"] in closures and p["requirement_id"] == f.requirement_id for p in previous for f in findings)
            for f in findings:
                old = next((p for p in previous if p["finding_id"] == f.id), None)
                if old and old["requirement_id"] != f.requirement_id:
                    raise DeliveryGateError("Finding identity cannot change requirement")
                c.execute(
                    "INSERT INTO pm_delivery_findings VALUES(?,?,?,?, 'OPEN') ON CONFLICT(issue_id,finding_id) DO UPDATE SET body=excluded.body,state='OPEN'",
                    (issue_id, f.id, f.requirement_id, f.model_dump_json()),
                )
            phase = "RECURRENCE_PAUSED" if recurring else "CHANGES_REQUESTED"
            c.execute("UPDATE pm_delivery_tasks SET phase=?,revision=revision+1 WHERE issue_id=?", (phase, issue_id))
            _event(
                c,
                row,
                actor,
                "REJECTED",
                {"submission_id": row["submission_id"], "findings": [f.model_dump() for f in findings], "recurring": recurring},
            )
        return self.get(issue_id)

    def resume(self, issue_id, revision, *, design_plan):
        if not isinstance(design_plan, str) or not design_plan.strip() or len(design_plan) > 8192:
            raise DeliveryGateError("Concrete correction/design plan required")
        with self.db.atomic_transaction() as c:
            row, _, actor = self._load(c, issue_id, revision, "coordinate", "coordinator")
            if row["phase"] not in {"CHANGES_REQUESTED", "RECURRENCE_PAUSED"}:
                raise DeliveryGateError("Correction decision not applicable")
            last_decision = c.execute(
                "SELECT kind FROM pm_delivery_events WHERE issue_id=? AND kind IN ('REJECTED','SCOPE_REQUESTED','SCOPE_DECLINED') ORDER BY id DESC LIMIT 1",
                (issue_id,),
            ).fetchone()
            if last_decision and last_decision["kind"] == "SCOPE_REQUESTED":
                raise DeliveryGateError("Resolve pending scope proposal before correction resumes")
            c.execute("UPDATE pm_delivery_tasks SET phase='READY',revision=revision+1 WHERE issue_id=?", (issue_id,))
            _event(
                c, row, actor, "DESIGN_REASSESSED" if row["phase"] == "RECURRENCE_PAUSED" else "CORRECTION_PLANNED", {"plan": design_plan}
            )
        return self.get(issue_id)

    def challenge(self, issue_id, revision, finding_id, reason):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 4096:
            raise DeliveryGateError("Challenge evidence/reason required")
        with self.db.atomic_transaction() as c:
            row, _, actor = self._load(c, issue_id, revision, "submit", "builder")
            if (
                row["phase"] not in {"CHANGES_REQUESTED", "RECURRENCE_PAUSED"}
                or not c.execute(
                    "SELECT 1 FROM pm_delivery_findings WHERE issue_id=? AND finding_id=? AND state='OPEN'", (issue_id, finding_id)
                ).fetchone()
            ):
                raise DeliveryGateError("Open blocking finding required")
            c.execute(
                "UPDATE pm_delivery_tasks SET phase='DISPUTED',paused_phase=?,revision=revision+1 WHERE issue_id=?",
                (row["phase"], issue_id),
            )
            _event(c, row, actor, "CHALLENGED", {"finding_id": finding_id, "reason": reason})
        return self.get(issue_id)

    def resolve_challenge(self, issue_id, revision, finding_id, *, upheld, reason):
        if type(upheld) is not bool or not isinstance(reason, str) or not reason.strip() or len(reason) > 4096:
            raise DeliveryGateError("Explicit challenge disposition required")
        with self.db.atomic_transaction() as c:
            row, _, actor = self._load(c, issue_id, revision, "coordinate", "coordinator")
            if row["phase"] != "DISPUTED":
                raise DeliveryGateError("No pending challenge")
            last = c.execute(
                "SELECT body FROM pm_delivery_events WHERE issue_id=? AND kind='CHALLENGED' ORDER BY id DESC LIMIT 1", (issue_id,)
            ).fetchone()
            if not last or json.loads(last["body"])["finding_id"] != finding_id:
                raise DeliveryGateError("Challenge identity mismatch")
            if not upheld:
                c.execute("UPDATE pm_delivery_findings SET state='WITHDRAWN' WHERE issue_id=? AND finding_id=?", (issue_id, finding_id))
            c.execute("UPDATE pm_delivery_tasks SET phase=?,revision=revision+1 WHERE issue_id=?", (row["paused_phase"], issue_id))
            _event(c, row, actor, "CHALLENGE_RESOLVED", {"finding_id": finding_id, "upheld": upheld, "reason": reason})
        return self.get(issue_id)

    def accept(self, issue_id, revision, *, verification_id, review_id):
        trust = self.db.coordinator._evidence_trust
        if trust is None:
            raise PermissionError("Trusted verification/review service required")
        with self.db.atomic_transaction() as c:
            row, brief, actor = self._load(c, issue_id, revision, "review", "reviewer")
            if row["phase"] != "IN_REVIEW":
                raise DeliveryGateError("Readiness-admitted candidate required")
            submission = json.loads(
                c.execute("SELECT body FROM pm_delivery_submissions WHERE id=?", (row["submission_id"],)).fetchone()["body"]
            )
            # Full existing admission validation is repeated under the gate transaction.
            if verification_id == review_id:
                raise DeliveryGateError("Distinct verification and review receipts required")
            manifest_row = c.execute(
                "SELECT manifest FROM pm_coordinator_evidence_contracts WHERE run_id=?", (submission["run_id"],)
            ).fetchone()
            if not manifest_row or set(json.loads(manifest_row["manifest"])["case_ids"]) != {x.id for x in brief.checks}:
                raise DeliveryGateError("Evidence suite must cover the agreed checks")
            for eid, role, principal in [
                (verification_id, "VERIFICATION_EVIDENCE", brief.verifier),
                (review_id, "REVIEW_EVIDENCE", brief.reviewer),
            ]:
                trust._admit_in_transaction(self.db.coordinator, eid, c)
                receipt = c.execute("SELECT canonical_payload FROM pm_coordinator_evidence_receipts WHERE evidence_id=?", (eid,)).fetchone()
                payload = json.loads(receipt["canonical_payload"])
                if (
                    payload["type"] != role
                    or payload["issuer_id"] != principal
                    or payload["developer_principal_id"] != brief.builder
                    or payload["run_id"] != submission["run_id"]
                    or payload["candidate_commit_sha"] != submission["candidate_sha"]
                    or payload["base_commit_sha"] != brief.base_sha
                    or payload["policy_version"] != brief.policy_version
                    or payload["suite_digest"] != brief.suite_digest
                ):
                    raise DeliveryGateError("Trusted evidence does not match delivery assignment")
            c.execute("UPDATE pm_delivery_findings SET state='CLOSED' WHERE issue_id=? AND state='OPEN'", (issue_id,))
            c.execute("UPDATE pm_delivery_tasks SET phase='ACCEPTED',revision=revision+1 WHERE issue_id=?", (issue_id,))
            _event(
                c,
                row,
                actor,
                "ACCEPTED",
                {"verification_id": verification_id, "review_id": review_id, "candidate": submission["candidate_sha"]},
            )
        return self.get(issue_id)

    def get(self, issue_id):
        with self.db.atomic_transaction() as c:
            row = c.execute("SELECT * FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
            if not row:
                raise DeliveryGateError("Missing brief")
            self._actor(row["tenant_id"], "read")
            return dict(row)

    def events(self, issue_id):
        with self.db.atomic_transaction() as c:
            row = c.execute("SELECT tenant_id FROM pm_delivery_tasks WHERE issue_id=?", (issue_id,)).fetchone()
            if not row:
                raise DeliveryGateError("Missing brief")
            self._actor(row["tenant_id"], "read")
            return [dict(x) for x in c.execute("SELECT * FROM pm_delivery_events WHERE issue_id=? ORDER BY id", (issue_id,))]

    def reconcile_execution(self, issue_id, revision, *, reason):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 4096:
            raise DeliveryGateError("Reconciliation reason required")
        with self.db.atomic_transaction() as c:
            row, _, actor = self._load(c, issue_id, revision, "coordinate", "coordinator")
            if row["phase"] not in {"UNCERTAIN", "DISPATCHED", "EXECUTING"}:
                raise DeliveryGateError("Execution reconciliation not applicable")
            if c.execute(
                "SELECT 1 FROM pm_coordinator_intents WHERE issue_id=? AND status NOT IN ('COMPLETED','FAILED','CANCELED')", (issue_id,)
            ).fetchone():
                raise DeliveryGateError("Execution is not authoritatively terminal")
            if c.execute("SELECT 1 FROM pm_coordinator_reservations WHERE issue_id=? AND status='HELD'", (issue_id,)).fetchone():
                raise DeliveryGateError("Funding hold remains unresolved")
            c.execute("UPDATE pm_delivery_tasks SET phase='READY',revision=revision+1 WHERE issue_id=?", (issue_id,))
            _event(c, row, actor, "EXECUTION_RECONCILED", {"reason": reason})
        return self.get(issue_id)

    def request_scope_change(self, issue_id, revision, *, proposal):
        if not isinstance(proposal, str) or not proposal.strip() or len(proposal) > 8192:
            raise DeliveryGateError("Explicit scope proposal required")
        with self.db.atomic_transaction() as c:
            row, _, actor = self._load(c, issue_id, revision, "review", "reviewer")
            if row["phase"] != "IN_REVIEW":
                raise DeliveryGateError("Scope proposal requires current review")
            c.execute("UPDATE pm_delivery_tasks SET phase='CHANGES_REQUESTED',revision=revision+1 WHERE issue_id=?", (issue_id,))
            _event(c, row, actor, "SCOPE_REQUESTED", {"proposal": proposal, "submission_id": row["submission_id"]})
        return self.get(issue_id)

    def resume_review(self, issue_id, revision, *, reason):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 4096:
            raise DeliveryGateError("Review-resumption reason required")
        with self.db.atomic_transaction() as c:
            row, _, actor = self._load(c, issue_id, revision, "coordinate", "coordinator")
            if row["phase"] not in {"CHANGES_REQUESTED", "RECURRENCE_PAUSED"}:
                raise DeliveryGateError("No resolved finding dispute to resume")
            if c.execute("SELECT 1 FROM pm_delivery_findings WHERE issue_id=? AND state='OPEN'", (issue_id,)).fetchone():
                raise DeliveryGateError("Unresolved blockers require correction")
            disposition = c.execute(
                "SELECT body,kind FROM pm_delivery_events WHERE issue_id=? AND kind IN ('CHALLENGE_RESOLVED','SCOPE_REQUESTED') ORDER BY id DESC LIMIT 1",
                (issue_id,),
            ).fetchone()
            if not disposition or disposition["kind"] != "CHALLENGE_RESOLVED" or json.loads(disposition["body"])["upheld"]:
                raise DeliveryGateError("Overturned finding required; new scope cannot be skipped")
            c.execute("UPDATE pm_delivery_tasks SET phase='IN_REVIEW',revision=revision+1 WHERE issue_id=?", (issue_id,))
            _event(c, row, actor, "REVIEW_RESUMED", {"reason": reason})
        return self.get(issue_id)

    def metrics(self, issue_id):
        events = self.events(issue_id)
        kinds = [e["kind"] for e in events]
        admitted = kinds.count("IN_REVIEW")
        return {
            "readiness_returns": kinds.count("READINESS_RETURNED"),
            "formal_submissions": admitted,
            "rejections": kinds.count("REJECTED"),
            "recurrence_pauses": sum(json.loads(e["body"]).get("recurring", False) for e in events if e["kind"] == "REJECTED"),
            "scope_requests": kinds.count("SCOPE_REQUESTED"),
            "design_reassessments": kinds.count("DESIGN_REASSESSED"),
            "challenges": kinds.count("CHALLENGED"),
            "overturned_findings": sum(not json.loads(e["body"])["upheld"] for e in events if e["kind"] == "CHALLENGE_RESOLVED"),
            "acceptances": kinds.count("ACCEPTED"),
        }

    def decline_scope_change(self, issue_id, revision, *, reason):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 4096:
            raise DeliveryGateError("Explicit scope disposition required")
        with self.db.atomic_transaction() as c:
            row, _, actor = self._load(c, issue_id, revision, "coordinate", "coordinator")
            last = c.execute(
                "SELECT kind FROM pm_delivery_events WHERE issue_id=? AND kind IN ('SCOPE_REQUESTED','SCOPE_DECLINED','REJECTED') ORDER BY id DESC LIMIT 1",
                (issue_id,),
            ).fetchone()
            if row["phase"] != "CHANGES_REQUESTED" or not last or last["kind"] != "SCOPE_REQUESTED":
                raise DeliveryGateError("No pending scope proposal")
            if c.execute("SELECT 1 FROM pm_delivery_findings WHERE issue_id=? AND state='OPEN'", (issue_id,)).fetchone():
                raise DeliveryGateError("Existing blockers cannot be waived as scope disposition")
            c.execute("UPDATE pm_delivery_tasks SET phase='IN_REVIEW',revision=revision+1 WHERE issue_id=?", (issue_id,))
            _event(c, row, actor, "SCOPE_DECLINED", {"reason": reason})
        return self.get(issue_id)
