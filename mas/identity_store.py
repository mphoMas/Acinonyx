"""Private single-host SQLite identity authority with transactional session audit.

The host owns this database and its signing key. Authentic whole-database rollback
requires an external anchor; row signatures alone cannot detect that operation.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import stat
import time
from contextlib import contextmanager
from pathlib import Path

from mas.audit_anchor import AnchorError


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class IdentityStore:
    def __init__(self, path: str | Path, key: bytes, *, anchor=None):
        if os.name != "posix":
            raise RuntimeError("Durable identity storage requires a POSIX host")
        self.path = Path(path).absolute()
        self._key = key
        self._anchor = anchor
        self._initializing = True
        if self.path.parent.is_symlink() or self.path.is_symlink():
            raise PermissionError("Identity storage cannot be a symlink")
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        parent = self.path.parent.stat()
        if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
            raise PermissionError("Identity storage requires a private owner-only directory")
        if self.path.parent.resolve() != self.path.parent:
            raise PermissionError("Identity storage ancestors cannot be symlinks")
        with self._initialization():
            created = False
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                created = True
            except FileExistsError:
                fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                    raise PermissionError("Identity database must be a private regular file")
            finally:
                os.close(fd)
            with self.transaction() as db:
                tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not tables and created:
                    db.execute("CREATE TABLE metadata(id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER NOT NULL, proof TEXT NOT NULL)")
                    db.execute("CREATE TABLE records(kind TEXT NOT NULL, id TEXT NOT NULL, tenant TEXT NOT NULL, subject TEXT NOT NULL, document TEXT NOT NULL, signature TEXT NOT NULL, PRIMARY KEY(kind,id))")
                    db.execute("CREATE INDEX record_owner ON records(kind,tenant,subject)")
                    db.execute("CREATE TABLE audit(seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, entity_id TEXT NOT NULL, digest TEXT NOT NULL, previous TEXT NOT NULL, signature TEXT NOT NULL)")
                    db.execute("INSERT INTO metadata VALUES(1,1,?)", (self.sign("identity-schema:1"),))
                else:
                    if tables not in ({"metadata", "records", "audit"}, {"metadata", "records", "audit", "anchor_binding"}):
                        raise PermissionError("Unsupported identity database schema")
                    if db.execute("SELECT id,version FROM metadata").fetchall() != [(1, 1)]:
                        raise PermissionError("Identity database key or schema mismatch")
                    self.validate_audit(db)
                self._bind_anchor(db)
        self._initializing = False

    def _bind_anchor(self, db):
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='anchor_binding'").fetchone()
        if exists:
            rows = db.execute("SELECT document,signature FROM anchor_binding").fetchall()
            if self._anchor is None or len(rows) != 1:
                raise AnchorError("An anchored authority requires its configured external witness")
            raw, signature = rows[0]
            if not hmac.compare_digest(self.sign("anchor-binding:" + raw), signature) or json.loads(raw) != self._anchor.binding:
                raise AnchorError("External audit witness binding mismatch")
            self._anchor.verify(self.audit_checkpoint(db))
        elif self._anchor is not None:
            # Attaching never publishes the local history automatically. A witness
            # administrator must enroll this namespace at the reviewed checkpoint.
            self._anchor.verify(self.audit_checkpoint(db))
            db.execute("CREATE TABLE anchor_binding(document TEXT NOT NULL, signature TEXT NOT NULL)")
            raw = canonical(self._anchor.binding)
            db.execute("INSERT INTO anchor_binding VALUES(?,?)", (raw, self.sign("anchor-binding:" + raw)))

    @staticmethod
    def audit_checkpoint(db):
        row = db.execute("SELECT seq,signature FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        return {"sequence": row[0], "hash": row[1]} if row else {"sequence": 0, "hash": ""}

    def export_checkpoint(self):
        with self.transaction(write=False) as db:
            self.validate_audit(db)
            return self.audit_checkpoint(db)

    @contextmanager
    def _initialization(self):
        import fcntl
        lock_path = self.path.with_name(self.path.name + ".initialize.lock")
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
                raise PermissionError("Identity initialization lock must be private")
            deadline = time.monotonic() + 5
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Identity initialization lock unavailable")
                    time.sleep(0.01)
            yield
        finally:
            os.close(descriptor)

    def sign(self, value: str) -> str:
        return hmac.new(self._key, value.encode(), hashlib.sha256).hexdigest()

    @contextmanager
    def transaction(self, *, write=True):
        # Never recreate a removed authority file as an empty identity registry.
        if self.path.is_symlink() or not self.path.is_file():
            raise PermissionError("Identity authority unavailable")
        info = self.path.stat()
        parent = self.path.parent.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1 or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
            raise PermissionError("Identity authority permissions became unsafe")
        db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA busy_timeout=5000")
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            before = None
            if not self._initializing:
                self._bind_anchor(db)
                if self._anchor is not None:
                    self.validate_audit(db)
                    before = self.audit_checkpoint(db)
            yield db
            if before is not None:
                after = self.audit_checkpoint(db)
                if after != before:
                    # Advance the independently retained head BEFORE commit. If
                    # commit crashes/fails, the witness stays ahead and all reads
                    # deny authority. Never rewind the witness to repair a lag.
                    self._anchor.advance(before, after)
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def validate_audit(self, db):
        previous = ""
        latest = {}
        for expected, row in enumerate(db.execute("SELECT seq,kind,entity_id,digest,previous,signature FROM audit ORDER BY seq"), 1):
            seq, kind, entity, digest, prior, signature = row
            raw = canonical([seq, kind, entity, digest, prior])
            if seq != expected or prior != previous or not hmac.compare_digest(self.sign(raw), signature):
                raise PermissionError("Identity audit integrity failure")
            previous = signature
            latest[(kind, entity)] = digest
        # Metadata head stops selective audit-tail truncation, but not restoration
        # of the entire authentic database, including its metadata.
        proof = db.execute("SELECT proof FROM metadata WHERE id=1 AND version=1").fetchone()
        count = db.execute("SELECT COUNT(*) FROM audit").fetchone()[0]
        expected = self.sign(canonical(["identity-head", count, previous])) if count else self.sign("identity-schema:1")
        if proof is None or not hmac.compare_digest(proof[0], expected):
            raise PermissionError("Identity audit head mismatch")
        if self._anchor is not None:
            self._anchor.verify(self.audit_checkpoint(db))
        return latest

    def read(self, db, kind, entity, latest):
        row = db.execute("SELECT tenant,subject,document,signature FROM records WHERE kind=? AND id=?", (kind, entity)).fetchone()
        if row is None:
            if (kind, entity) in latest:
                raise PermissionError("Identity record deleted from authority")
            return None
        tenant, subject, raw, signature = row
        value = canonical([kind, entity, tenant, subject, raw])
        if not hmac.compare_digest(self.sign(value), signature) or latest.get((kind, entity)) != hashlib.sha256(value.encode()).hexdigest():
            raise PermissionError("Identity record integrity failure")
        document = json.loads(raw)
        if document["tenant_id"] != tenant or (kind != "tenant" and document["user_id"] != subject):
            raise PermissionError("Identity record ownership mismatch")
        return document

    def save(self, db, kind, entity, document):
        tenant = document["tenant_id"]
        subject = document.get("user_id", "")
        raw = canonical(document)
        value = canonical([kind, entity, tenant, subject, raw])
        db.execute("INSERT INTO records VALUES(?,?,?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET tenant=excluded.tenant,subject=excluded.subject,document=excluded.document,signature=excluded.signature", (kind, entity, tenant, subject, raw, self.sign(value)))
        prior = db.execute("SELECT seq,signature FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        seq, previous = (prior[0] + 1, prior[1]) if prior else (1, "")
        digest = hashlib.sha256(value.encode()).hexdigest()
        signature = self.sign(canonical([seq, kind, entity, digest, previous]))
        db.execute("INSERT INTO audit VALUES(?,?,?,?,?,?)", (seq, kind, entity, digest, previous, signature))
        db.execute("UPDATE metadata SET proof=? WHERE id=1", (self.sign(canonical(["identity-head", seq, signature])),))

    def get(self, kind, entity):
        with self.transaction(write=False) as db:
            return self.read(db, kind, entity, self.validate_audit(db))

    def create_tenant(self, document):
        with self.transaction() as db:
            latest = self.validate_audit(db)
            if self.read(db, "tenant", document["tenant_id"], latest):
                raise ValueError("Tenant already exists")
            self.save(db, "tenant", document["tenant_id"], document)

    def register_principal(self, document):
        with self.transaction() as db:
            latest = self.validate_audit(db)
            tenant = self.read(db, "tenant", document["tenant_id"], latest)
            if not tenant or tenant["status"] != "ACTIVE":
                raise PermissionError("Tenant is inactive")
            self.read(db, "principal", f"{document['tenant_id']}:{document['user_id']}", latest)
            self._revoke_matching(db, latest, document["tenant_id"], document["user_id"])
            self.save(db, "principal", f"{document['tenant_id']}:{document['user_id']}", document)

    def _revoke_matching(self, db, latest, tenant, user=None):
        query = "SELECT id FROM records WHERE kind='session' AND tenant=?"
        args = [tenant]
        if user is not None:
            query += " AND subject=?"
            args.append(user)
        count = 0
        for (sid,) in db.execute(query, args).fetchall():
            session = self.read(db, "session", sid, latest)
            if not session["revoked"]:
                session["revoked"] = True
                session["revoked_at"] = time.time()
                self.save(db, "session", sid, session)
                count += 1
        return count

    def suspend_tenant(self, tenant_id):
        with self.transaction() as db:
            latest = self.validate_audit(db)
            tenant = self.read(db, "tenant", tenant_id, latest)
            if tenant:
                self._revoke_matching(db, latest, tenant_id)
                tenant["status"] = "SUSPENDED"
                self.save(db, "tenant", tenant_id, tenant)

    def issue_session(self, claims, token_hash):
        with self.transaction() as db:
            latest = self.validate_audit(db)
            tenant = self.read(db, "tenant", claims["tid"], latest)
            principal = self.read(db, "principal", f"{claims['tid']}:{claims['uid']}", latest)
            if not tenant or tenant["status"] != "ACTIVE" or not principal:
                raise PermissionError("Identity changed during token issuance")
            if not set(claims["roles"]) <= set(principal["roles"]) or not set(claims["scopes"]) <= set(principal["scopes"]):
                raise PermissionError("Permissions changed during token issuance")
            session = {"tenant_id": claims["tid"], "user_id": claims["uid"], "expires": claims["exp"], "issued_at": claims["iat"], "token_hash": token_hash, "revoked": False, "revoked_at": None}
            if self.read(db, "session", claims["nonce"], latest):
                raise PermissionError("Duplicate session identifier")
            self.save(db, "session", claims["nonce"], session)

    def _authority(self, db, latest, tenant_id, user_id, sid, *, token_hash=None, expires=None):
        tenant = self.read(db, "tenant", tenant_id, latest)
        principal = self.read(db, "principal", f"{tenant_id}:{user_id}", latest)
        session = self.read(db, "session", sid, latest)
        if not tenant or tenant["status"] != "ACTIVE" or not principal or not session:
            raise PermissionError("Identity or session unavailable")
        if session["tenant_id"] != tenant_id or session["user_id"] != user_id or session["revoked"] or session["expires"] <= time.time():
            raise PermissionError("Session expired or revoked")
        if token_hash is not None and not hmac.compare_digest(session["token_hash"], token_hash):
            raise PermissionError("Token does not match issued session")
        if expires is not None and session["expires"] != expires:
            raise PermissionError("Session expiry mismatch")
        return principal

    def authority(self, tenant_id, user_id, sid, *, token_hash=None, expires=None):
        with self.transaction(write=False) as db:
            return self._authority(db, self.validate_audit(db), tenant_id, user_id, sid, token_hash=token_hash, expires=expires)

    def revoke_session(self, actor, sid, permission_check):
        with self.transaction() as db:
            latest = self.validate_audit(db)
            principal = self._authority(db, latest, actor.tenant_id, actor.principal_id, actor.token_id, expires=actor.expires_at)
            if sid != actor.token_id and not permission_check(principal):
                raise PermissionError("Session revocation requires current tenant admin authority")
            session = self.read(db, "session", sid, latest)
            if not session or session["tenant_id"] != actor.tenant_id:
                raise PermissionError("Session unavailable in this tenant")
            if not session["revoked"]:
                session["revoked"] = True
                session["revoked_at"] = time.time()
                self.save(db, "session", sid, session)
            return True

    def revoke_principal_sessions(self, actor, user_id, permission_check):
        with self.transaction() as db:
            latest = self.validate_audit(db)
            principal = self._authority(db, latest, actor.tenant_id, actor.principal_id, actor.token_id, expires=actor.expires_at)
            if not permission_check(principal):
                raise PermissionError("Session revocation requires current tenant admin authority")
            if not self.read(db, "principal", f"{actor.tenant_id}:{user_id}", latest):
                raise PermissionError("Principal unavailable in this tenant")
            return self._revoke_matching(db, latest, actor.tenant_id, user_id)

    def invalidate_all_sessions(self):
        """Trusted offline restore fence; not an agent or authenticated API endpoint."""
        with self.transaction() as db:
            latest = self.validate_audit(db)
            count = 0
            for (sid,) in db.execute("SELECT id FROM records WHERE kind='session'").fetchall():
                session = self.read(db, "session", sid, latest)
                if not session["revoked"]:
                    session["revoked"] = True
                    session["revoked_at"] = time.time()
                    self.save(db, "session", sid, session)
                    count += 1
            return count

    def backup(self, destination: str | Path):
        target = Path(destination).absolute()
        if target.parent.resolve() != target.parent or target.parent.stat().st_uid != os.getuid() or target.parent.stat().st_mode & 0o077:
            raise PermissionError("Backup requires a private existing directory")
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        try:
            with self.transaction(write=False) as source:
                self.validate_audit(source)
                destination_db = sqlite3.connect(str(target))
                try:
                    source.backup(destination_db)
                finally:
                    destination_db.close()
        except BaseException:
            target.unlink(missing_ok=True)
            raise
