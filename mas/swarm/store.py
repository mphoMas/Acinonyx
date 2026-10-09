"""SQLite authoritative state, identity, provenance and transactional audit.

This is a trusted local control plane. Its database/key are never accessible to
agents. It is not a remote authentication server or an external audit ledger.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager, nullcontext
from pathlib import Path

from mas.platform.identity import PlatformAuthority

from .contracts import Limits, SwarmError, canonical, cases_contract, digest, identifier, strict_json, text

ACTIVE = {"planning", "coding", "verifying", "reviewing"}
TRANSITIONS = {
    "queued": {"planning", "cancelled"},
    "planning": {"coding", "failed", "cancelled", "interrupted"},
    "coding": {"verifying", "failed", "cancelled", "interrupted"},
    "verifying": {"reviewing", "rejected", "failed", "cancelled", "interrupted"},
    "reviewing": {"awaiting_approval", "rejected", "failed", "cancelled", "interrupted"},
    "awaiting_approval": {"approved", "cancelled"},
}


class Store:
    def __init__(self, path: str | Path, signing_key: bytes, *, authority: PlatformAuthority | None = None):
        if not isinstance(signing_key, bytes) or len(signing_key) < 32:
            raise SwarmError("A private signing key of at least 32 bytes is required")
        if authority is not None and type(authority) is not PlatformAuthority:
            raise SwarmError("Unsupported swarm identity authority")
        if authority and Path(path).absolute() == authority.iam.database_path:
            raise SwarmError("Identity and swarm state require separate databases")
        self._authority = authority
        self.path, self._key = str(path), signing_key
        with self._reading() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS metadata(version INTEGER NOT NULL);
                INSERT INTO metadata SELECT 2 WHERE NOT EXISTS(SELECT 1 FROM metadata);
                CREATE TABLE IF NOT EXISTS principals(
                    token_hash TEXT PRIMARY KEY, tenant TEXT NOT NULL, subject TEXT NOT NULL,
                    role TEXT NOT NULL, expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0,
                    signature TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS runs(
                    id TEXT PRIMARY KEY, tenant TEXT NOT NULL, request_key TEXT NOT NULL,
                    document TEXT NOT NULL, signature TEXT NOT NULL,
                    UNIQUE(tenant, request_key));
                CREATE TABLE IF NOT EXISTS audit(
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, signature TEXT NOT NULL);
            """)
            if db.execute("SELECT version FROM metadata").fetchall() != [(2,)]:
                raise SwarmError("Unsupported state schema version")
        with self._tx() as db:
            pass

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=5000")
        return db

    @contextmanager
    def _reading(self):
        db = self._connect()
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def _tx(self):
        with self._authority.guard() if self._authority else nullcontext():
            db = self._connect()
            try:
                db.execute("BEGIN IMMEDIATE")
                self._check_authority(db)
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise
            finally:
                db.close()

    def _check_authority(self, db):
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='authority_binding'").fetchone()
        expected = self._authority.binding if self._authority else {"mode": "local", "version": 1}
        self._check_audit(db)
        binding_events = [strict_json(raw) for (raw,) in db.execute("SELECT event FROM audit ORDER BY seq")
                          if strict_json(raw).get("action") == "bind_authority"]
        if exists:
            rows = db.execute("SELECT document,signature FROM authority_binding").fetchall()
            if len(rows) != 1:
                raise SwarmError("Missing swarm authority binding")
            raw, signature = rows[0]
            if not hmac.compare_digest(self._sign("authority-binding:" + raw), signature) or strict_json(raw) != expected:
                raise SwarmError("Swarm identity authority differs from persisted binding")
            if not binding_events or binding_events[-1].get("binding_hash") != digest(expected):
                raise SwarmError("Swarm authority binding history mismatch")
        else:
            if binding_events:
                raise SwarmError("Swarm authority binding was removed")
            if self._authority and (db.execute("SELECT 1 FROM principals LIMIT 1").fetchone() or db.execute("SELECT 1 FROM runs LIMIT 1").fetchone()):
                raise SwarmError("Existing local identity requires reviewed migration; use fresh platform-bound state")
            db.execute("CREATE TABLE authority_binding(document TEXT NOT NULL, signature TEXT NOT NULL)")
            raw = canonical(expected)
            db.execute("INSERT INTO authority_binding VALUES(?,?)", (raw, self._sign("authority-binding:" + raw)))
            self._audit(db, {"action": "bind_authority", "binding_hash": digest(expected)})


    def _sign(self, value: str):
        return hmac.new(self._key, value.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _token_hash(token):
        if not isinstance(token, str) or not 32 <= len(token) <= 256:
            raise PermissionError("Missing or invalid identity")
        return hashlib.sha256(token.encode()).hexdigest()

    def _auth(self, db, token: str, roles: set[str]):
        self._check_authority(db)
        if self._authority:
            self._check_audit(db)
            return self._authority.authenticate(token, roles)
        token_hash = self._token_hash(token)
        row = db.execute(
            "SELECT tenant,subject,role,expires,revoked,signature FROM principals WHERE token_hash=?", (token_hash,)
        ).fetchone()
        if not row:
            raise PermissionError("Identity expired, revoked or unauthorized")
        principal = {"token_hash": token_hash, "tenant": row[0], "subject": row[1], "role": row[2], "expires": row[3], "revoked": row[4]}
        if not hmac.compare_digest(self._sign(canonical(principal)), row[5]):
            raise SwarmError("Identity integrity failure")
        self._check_audit(db)
        latest = None
        for (raw,) in db.execute("SELECT event FROM audit ORDER BY seq DESC"):
            event = strict_json(raw)
            if event.get("token_hash") == token_hash and "principal_hash" in event:
                latest = event["principal_hash"]
                break
        if latest != digest(principal):
            raise SwarmError("Identity history mismatch")
        if row[4] or row[3] <= time.time() or row[2] not in roles:
            raise PermissionError("Identity expired, revoked or unauthorized")
        return {"tenant": row[0], "subject": row[1], "role": row[2]}

    def provision(self, tenant: str, subject: str, role: str, *, ttl: float = 86400) -> str:
        """Trusted OS administrator only; intentionally not an agent/API tool."""
        if self._authority:
            raise SwarmError("Provision credentials through platform IAM")
        identifier(tenant)
        identifier(subject)
        if role not in {"owner", "requester", "approver"} or type(ttl) not in (int, float) or not 0 < ttl <= 604800:
            raise SwarmError("Invalid enrollment")
        token = secrets.token_urlsafe(32)
        principal = {
            "token_hash": self._token_hash(token),
            "tenant": tenant,
            "subject": subject,
            "role": role,
            "expires": time.time() + ttl,
            "revoked": 0,
        }
        with self._tx() as db:
            db.execute(
                "INSERT INTO principals(token_hash,tenant,subject,role,expires,revoked,signature) VALUES(?,?,?,?,?,?,?)",
                (*principal.values(), self._sign(canonical(principal))),
            )
            self._audit(
                db,
                {
                    "action": "enroll",
                    "tenant": tenant,
                    "subject": subject,
                    "role": role,
                    "token_hash": principal["token_hash"],
                    "principal_hash": digest(principal),
                },
            )
        return token

    def revoke(self, owner_token: str, subject: str):
        if self._authority:
            raise SwarmError("Revoke platform sessions through platform IAM")
        with self._tx() as db:
            actor = self._auth(db, owner_token, {"owner"})
            rows = db.execute(
                "SELECT token_hash,tenant,subject,role,expires,revoked,signature FROM principals WHERE tenant=? AND subject=?",
                (actor["tenant"], subject),
            ).fetchall()
            for row in rows:
                principal = dict(zip(("token_hash", "tenant", "subject", "role", "expires", "revoked"), row[:6], strict=True))
                if not hmac.compare_digest(self._sign(canonical(principal)), row[6]):
                    raise SwarmError("Identity integrity failure")
                principal["revoked"] = 1
                db.execute(
                    "UPDATE principals SET revoked=1,signature=? WHERE token_hash=?",
                    (self._sign(canonical(principal)), principal["token_hash"]),
                )
                self._audit(
                    db,
                    {
                        "action": "revoke_identity",
                        "token_hash": principal["token_hash"],
                        "principal_hash": digest(principal),
                        "tenant": actor["tenant"],
                    },
                )
            self._audit(db, {"action": "revoke", **actor, "target": subject})

    def require_role(self, token: str, roles: set[str]):
        with self._tx() as db:
            return self._auth(db, token, roles)

    def record_cleanup(self, owner_token: str, run_id: str):
        with self._tx() as db:
            actor = self._auth(db, owner_token, {"owner"})
            doc = self._load(db, run_id, actor)
            if doc["state"] not in {"failed", "cancelled", "interrupted", "rejected"}:
                raise SwarmError("Cleanup requires a non-releasable terminal run")
            self._save(db, doc, actor, "worker_reconciliation")

    def _audit(self, db, event: dict):
        self._check_audit(db)
        previous = db.execute("SELECT signature FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        raw = canonical({**event, "time": time.time(), "previous": previous[0] if previous else ""})
        db.execute("INSERT INTO audit(event,signature) VALUES(?,?)", (raw, self._sign(raw)))

    def verify_audit(self):
        with self._reading() as db:
            self._check_audit(db)

    def _check_audit(self, db):
        previous = ""
        for raw, signature in db.execute("SELECT event,signature FROM audit ORDER BY seq"):
            if not hmac.compare_digest(self._sign(raw), signature) or strict_json(raw)["previous"] != previous:
                raise SwarmError("Audit integrity failure")
            previous = signature

    def _load(self, db, run_id: str, actor: dict):
        identifier(run_id)
        row = db.execute("SELECT document,signature FROM runs WHERE id=? AND tenant=?", (run_id, actor["tenant"])).fetchone()
        if not row:
            raise PermissionError("Run unavailable in this tenant")
        raw, signature = row
        if not hmac.compare_digest(self._sign(raw), signature):
            raise SwarmError("Run integrity failure")
        document = strict_json(raw)
        if document["id"] != run_id or document["tenant"] != actor["tenant"]:
            raise SwarmError("Run identity mismatch")
        latest = None
        for (event_raw,) in db.execute("SELECT event FROM audit ORDER BY seq DESC"):
            event = strict_json(event_raw)
            if event.get("run_id") == run_id and "document_hash" in event:
                latest = event["document_hash"]
                break
        if latest != digest(document):
            raise SwarmError("Run history mismatch; signed snapshots cannot be selectively replayed")
        return document

    def _save(self, db, doc: dict, actor: dict, action: str):
        doc["version"] += 1
        raw = canonical(doc)
        db.execute("UPDATE runs SET document=?,signature=? WHERE id=? AND tenant=?", (raw, self._sign(raw), doc["id"], doc["tenant"]))
        self._audit(
            db,
            {
                "action": action,
                "run_id": doc["id"],
                "tenant": doc["tenant"],
                "actor": actor["subject"],
                "state": doc["state"],
                "version": doc["version"],
                "document_hash": digest(doc),
            },
        )

    def submit(self, token: str, request_key: str, goal: str, cases: list, limits: Limits | None = None):
        limits = limits or Limits()
        identifier(request_key)
        text(goal, "goal")
        tests = cases_contract(cases, limits)
        request = {"goal": goal, "cases": tests, "limits": limits.__dict__}
        with self._tx() as db:
            actor = self._auth(db, token, {"owner", "requester"})
            existing = db.execute("SELECT id FROM runs WHERE tenant=? AND request_key=?", (actor["tenant"], request_key)).fetchone()
            if existing:
                doc = self._load(db, existing[0], actor)
                if doc["request_hash"] != digest(request):
                    raise SwarmError("Idempotency key reused with a different request")
                return doc
            doc = {
                "id": uuid.uuid4().hex,
                "tenant": actor["tenant"],
                "submitted_by": actor["subject"],
                "state": "queued",
                "version": 0,
                "request": request,
                "request_hash": digest(request),
                "usage": {"calls": 0, "tokens": 0, "reserved": 0},
                "created": time.time(),
            }
            raw = canonical(doc)
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?)", (doc["id"], doc["tenant"], request_key, raw, self._sign(raw)))
            self._audit(db, {"action": "submit", "run_id": doc["id"], **actor, "document_hash": digest(doc)})
            return doc

    def get(self, token: str, run_id: str):
        with self._tx() as db:
            actor = self._auth(db, token, {"owner", "requester", "approver"})
            return self._load(db, run_id, actor)

    def claim(self, token: str, run_id: str, image: str, *, provider: dict | None = None):
        with self._tx() as db:
            actor = self._auth(db, token, {"owner", "requester"})
            doc = self._load(db, run_id, actor)
            if doc["state"] != "queued":
                raise SwarmError("Run already claimed or terminal; no implicit replay")
            doc.update(
                state="planning",
                lease=uuid.uuid4().hex,
                image=image,
                provider=provider,
                lease_expires=time.time() + doc["request"]["limits"]["deadline_seconds"] + 30,
            )
            self._save(db, doc, actor, "claim")
            return doc

    def transition(self, token: str, run_id: str, lease: str, state: str, **updates):
        with self._tx() as db:
            actor = self._auth(db, token, {"owner", "requester"})
            doc = self._load(db, run_id, actor)
            if doc.get("lease") != lease or doc.get("lease_expires", 0) < time.time():
                raise SwarmError("Execution lease lost or expired")
            if state not in TRANSITIONS.get(doc["state"], set()) or state == "approved":
                raise SwarmError("Invalid state transition")
            if set(updates) - {"plan", "source", "candidate_hash", "evidence", "review", "error"}:
                raise SwarmError("Forbidden coordinator update")
            doc.update(updates, state=state)
            if state == "awaiting_approval":
                self._validate_evidence(doc)
            self._save(db, doc, actor, "transition")
            return doc

    def reserve(self, token: str, run_id: str, lease: str, amount: int):
        with self._tx() as db:
            actor = self._auth(db, token, {"owner", "requester"})
            doc = self._load(db, run_id, actor)
            usage = doc["usage"]
            if (
                doc.get("lease") != lease
                or doc["state"] not in ACTIVE
                or doc["lease_expires"] <= time.time()
                or type(amount) is not int
                or amount <= 0
                or usage["reserved"]
                or usage["calls"] >= 3
                or usage["tokens"] + amount > doc["request"]["limits"]["max_tokens"]
            ):
                raise SwarmError("Model call or token budget unavailable")
            usage.update(calls=usage["calls"] + 1, reserved=amount)
            self._save(db, doc, actor, "reserve_usage")

    def settle(self, token: str, run_id: str, lease: str, amount: int):
        with self._tx() as db:
            actor = self._auth(db, token, {"owner", "requester"})
            doc = self._load(db, run_id, actor)
            usage = doc["usage"]
            if doc.get("lease") != lease or doc["state"] not in ACTIVE or not usage["reserved"]:
                raise SwarmError("No valid usage reservation")
            if type(amount) is not int or not 0 <= amount <= usage["reserved"]:
                raise SwarmError("Provider usage exceeds reservation or is invalid")
            usage.update(tokens=usage["tokens"] + amount, reserved=0)
            self._save(db, doc, actor, "settle_usage")

    def cancel(self, token: str, run_id: str):
        with self._tx() as db:
            actor = self._auth(db, token, {"owner", "requester"})
            doc = self._load(db, run_id, actor)
            if "cancelled" not in TRANSITIONS.get(doc["state"], set()):
                raise SwarmError("Cannot cancel a terminal run")
            doc["state"] = "cancelled"
            self._save(db, doc, actor, "cancel")

    def interrupt(self, token: str, run_id: str):
        """After expired lease and worker cleanup; failed work is never auto-replayed."""
        with self._tx() as db:
            actor = self._auth(db, token, {"owner"})
            doc = self._load(db, run_id, actor)
            if doc["state"] not in ACTIVE or doc["lease_expires"] > time.time():
                raise SwarmError("Run has no expired active lease")
            doc["state"] = "interrupted"
            self._save(db, doc, actor, "recover")

    @staticmethod
    def _validate_evidence(doc):
        evidence = doc.get("evidence", {})
        tests = doc["request"]["cases"]
        if (
            not doc.get("source")
            or doc.get("candidate_hash") != digest(doc["source"])
            or evidence.get("candidate_hash") != doc["candidate_hash"]
            or evidence.get("run_id") != doc["id"]
            or evidence.get("provider") != doc.get("provider")
            or evidence.get("image") != doc["image"]
            or evidence.get("suite_hash") != digest(tests)
            or evidence.get("results") != [{"id": t["id"], "passed": True, "status": "passed"} for t in tests]
            or doc.get("review", {}).get("approved") is not True
            or any(type(r.get("passed")) is not bool for r in evidence.get("results", []))
            or doc["usage"]["reserved"] != 0
            or doc["usage"]["calls"] != 3
        ):
            raise SwarmError("Missing, failing or mismatched verification evidence")

    def approve(self, token: str, run_id: str, candidate_hash: str, *, max_age: float = 3600):
        if type(max_age) not in (int, float) or not 0 < max_age <= 3600:
            raise SwarmError("Invalid approval freshness limit")
        self.verify_audit()
        with self._tx() as db:
            actor = self._auth(db, token, {"owner", "approver"})
            doc = self._load(db, run_id, actor)
            self._validate_evidence(doc)
            if (
                doc["state"] != "awaiting_approval"
                or candidate_hash != doc["candidate_hash"]
                or actor["subject"] == doc["submitted_by"]
                or not 0 <= time.time() - doc["evidence"].get("finished", 0) <= max_age
            ):
                raise SwarmError("Approval requires fresh evidence, exact candidate and a separate human")
            doc.update(state="approved", approved_by=actor["subject"], approved_at=time.time())
            self._save(db, doc, actor, "human_approval")
            return doc

    def backup(self, target: str | Path):
        """Trusted operator backup; key must be backed up separately and securely."""
        with self._reading() as source, sqlite3.connect(str(target)) as destination:
            source.backup(destination)
