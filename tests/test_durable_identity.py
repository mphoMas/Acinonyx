"""Restart, revocation races and adversarial authority-store acceptance checks."""
import asyncio
import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from mas.iam import MultiTenantIAM, StandardRole
from mas.mcp.protocol import MCPRegistry, JsonRpcRequest
from mas.tools.filesystem import register_filesystem_tools

KEY = "disposable-private-identity-test-key-" * 2
ADMIN = {StandardRole.TENANT_ADMIN.value}


@pytest.fixture
def durable(tmp_path):
    path = tmp_path / "identity" / "iam.sqlite"
    iam = MultiTenantIAM(KEY, db_path=path)
    for tenant in ("alpha", "beta"):
        iam.create_tenant(tenant, tenant)
        iam.register_principal(tenant, "admin", roles=ADMIN)
        iam.register_principal(tenant, "reader")
    return iam, path


def permitted(iam, context):
    return iam.authorize(context, "storage:read", context.tenant_id, f"urn:mas:tenant:{context.tenant_id}:workspace")


def test_new_process_restores_identity_and_preserves_revocation(durable):
    iam, path = durable
    actor = iam.issue_token("alpha", "admin")
    valid = iam.issue_token("alpha", "reader")
    revoked = iam.issue_token("alpha", "reader")
    sid = iam.verify_token(revoked).token_id
    iam.revoke_session(actor, sid)
    script = '''import json,sys
from mas.iam import MultiTenantIAM
p=json.load(sys.stdin)
iam=MultiTenantIAM(p['key'],db_path=p['path'])
assert iam.get_tenant('alpha').name == 'alpha'
assert iam.get_principal('alpha','reader').user_id == 'reader'
assert iam.verify_token(p['valid']).tenant_id == 'alpha'
try:
 iam.verify_token(p['revoked'])
except PermissionError:
 print('restart-and-revocation-confirmed')
else:
 raise AssertionError('revoked token revived')
'''
    result = subprocess.run([sys.executable, "-c", script], input=json.dumps({"key": KEY, "path": str(path), "valid": valid, "revoked": revoked}), text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "restart-and-revocation-confirmed"
    assert valid.encode() not in path.read_bytes()
    assert KEY.encode() not in path.read_bytes()


def test_self_logout_and_revoke_other_principal_require_authority(durable):
    iam, _ = durable
    reader = iam.issue_token("alpha", "reader")
    another = iam.issue_token("alpha", "reader")
    beta = iam.issue_token("beta", "reader")
    with pytest.raises(PermissionError, match="admin authority"):
        iam.revoke_session(reader, iam.verify_token(another).token_id)
    admin = iam.issue_token("alpha", "admin")
    with pytest.raises(PermissionError, match="this tenant"):
        iam.revoke_session(admin, iam.verify_token(beta).token_id)
    assert iam.revoke_session(reader, iam.verify_token(reader).token_id)
    with pytest.raises(PermissionError, match="revoked"):
        iam.verify_token(reader)
    assert iam.verify_token(another)
    assert iam.verify_token(beta)


def test_revocation_reaches_existing_contexts_in_other_instances(durable):
    iam, path = durable
    other = MultiTenantIAM(KEY, db_path=path)
    actor = iam.issue_token("alpha", "admin")
    token = iam.issue_token("alpha", "reader")
    context = other.verify_token(token)
    assert permitted(other, context)
    iam.revoke_session(actor, context.token_id)
    assert not permitted(other, context)
    with pytest.raises(PermissionError):
        other.verify_token(token)


def test_bulk_revocation_does_not_affect_other_tenants(durable):
    iam, path = durable
    admin = iam.issue_token("alpha", "admin")
    tokens = [iam.issue_token("alpha", "reader") for _ in range(5)]
    beta = iam.issue_token("beta", "reader")
    assert iam.revoke_principal_sessions(admin, "reader") == 5
    assert iam.revoke_principal_sessions(admin, "reader") == 0
    restarted = MultiTenantIAM(KEY, db_path=path)
    for token in tokens:
        with pytest.raises(PermissionError):
            restarted.verify_token(token)
    assert restarted.verify_token(beta)
    assert restarted.verify_token(admin)


def test_permission_updates_and_suspension_persist_without_reprovision(durable):
    iam, path = durable
    token = iam.issue_token("alpha", "admin")
    context = iam.verify_token(token)
    iam.register_principal("alpha", "admin", roles=set(), scopes=set())
    assert not permitted(iam, context)
    restarted = MultiTenantIAM(KEY, db_path=path)
    assert restarted.get_principal("alpha", "admin").roles == set()
    with pytest.raises(PermissionError):
        restarted.verify_token(token)
    iam.suspend_tenant("beta")
    with pytest.raises(PermissionError, match="inactive"):
        restarted.issue_token("beta", "reader")
    assert restarted.get_tenant("beta").status.value == "SUSPENDED"


def test_private_key_and_storage_permissions_fail_closed(tmp_path, monkeypatch):
    monkeypatch.delenv("MAS_IAM_SECRET", raising=False)
    with pytest.raises(ValueError, match="configured private"):
        MultiTenantIAM(db_path=tmp_path / "identity.sqlite")
    unsafe = tmp_path / "unsafe"
    unsafe.mkdir(mode=0o755)
    unsafe.chmod(0o755)
    with pytest.raises(PermissionError, match="private"):
        MultiTenantIAM(KEY, db_path=unsafe / "identity.sqlite")
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    target = private / "target"
    target.touch(mode=0o600)
    (private / "linked.sqlite").symlink_to(target)
    with pytest.raises(PermissionError, match="symlink"):
        MultiTenantIAM(KEY, db_path=private / "linked.sqlite")


def test_wrong_key_and_unknown_schema_rejected(durable):
    _, path = durable
    with pytest.raises(PermissionError, match="integrity|mismatch"):
        MultiTenantIAM("different-private-signing-key" * 2, db_path=path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE metadata SET version=99")
    with pytest.raises(PermissionError, match="schema"):
        MultiTenantIAM(KEY, db_path=path)


@pytest.mark.parametrize("attack", ["record", "replay", "tail", "delete"])
def test_tampered_or_selectively_replayed_authority_rejected(durable, attack):
    iam, path = durable
    token = iam.issue_token("alpha", "reader")
    actor = iam.issue_token("alpha", "admin")
    sid = iam.verify_token(token).token_id
    with sqlite3.connect(path) as db:
        old = db.execute("SELECT document,signature FROM records WHERE kind='session' AND id=?", (sid,)).fetchone()
    iam.revoke_session(actor, sid)
    with sqlite3.connect(path) as db:
        if attack == "record":
            db.execute("UPDATE records SET document=replace(document,'true','false') WHERE kind='session' AND id=?", (sid,))
        elif attack == "replay":
            db.execute("UPDATE records SET document=?,signature=? WHERE kind='session' AND id=?", (*old, sid))
        elif attack == "tail":
            db.execute("DELETE FROM audit WHERE seq=(SELECT MAX(seq) FROM audit)")
        else:
            db.execute("DELETE FROM records WHERE kind='session' AND id=?", (sid,))
    with pytest.raises(PermissionError, match="integrity|mismatch|deleted"):
        iam.verify_token(token)


def test_audit_write_failure_rolls_back_revocation(durable):
    iam, path = durable
    actor = iam.issue_token("alpha", "admin")
    token = iam.issue_token("alpha", "reader")
    context = iam.verify_token(token)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER deny_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError, match="audit unavailable"):
        iam.revoke_session(actor, context.token_id)
    assert permitted(iam, context)
    with sqlite3.connect(path) as db:
        db.execute("DROP TRIGGER deny_audit")
    assert iam.revoke_session(actor, context.token_id)
    assert not permitted(iam, context)


def test_backup_restores_revocations_and_never_overwrites(durable, tmp_path):
    iam, _ = durable
    actor = iam.issue_token("alpha", "admin")
    token = iam.issue_token("alpha", "reader")
    iam.revoke_session(actor, iam.verify_token(token).token_id)
    backup = tmp_path / "backup.sqlite"
    iam.backup(backup)
    assert backup.stat().st_mode & 0o777 == 0o600
    restored = MultiTenantIAM(KEY, db_path=backup)
    assert restored.verify_token(actor)
    with pytest.raises(PermissionError):
        restored.verify_token(token)
    with pytest.raises(FileExistsError):
        iam.backup(backup)


def test_concurrent_issuance_and_bulk_revocation_are_serialized(durable):
    iam, path = durable
    actor = iam.issue_token("alpha", "admin")
    instances = [MultiTenantIAM(KEY, db_path=path) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(lambda index: instances[index % 4].issue_token("alpha", "reader"), range(24)))
    assert len({iam.verify_token(token).token_id for token in tokens}) == 24
    assert iam.revoke_principal_sessions(actor, "reader") == 24
    with ThreadPoolExecutor(max_workers=8) as pool:
        def denied(token):
            try:
                instances[0].verify_token(token)
            except PermissionError:
                return True
            return False
        assert all(pool.map(denied, tokens))
    new_token = instances[1].issue_token("alpha", "reader")
    assert iam.verify_token(new_token)


def test_revoked_admin_cannot_finish_previously_started_revocation(durable, monkeypatch):
    iam, path = durable
    actor = iam.issue_token("alpha", "admin")
    victim = iam.issue_token("alpha", "reader")
    actor_sid = iam.verify_token(actor).token_id
    victim_sid = iam.verify_token(victim).token_id
    second = MultiTenantIAM(KEY, db_path=path)
    original = iam._store.revoke_session
    def revoke_actor_first(context, sid, check):
        second.revoke_session(actor, actor_sid)
        return original(context, sid, check)
    monkeypatch.setattr(iam._store, "revoke_session", revoke_actor_first)
    with pytest.raises(PermissionError, match="revoked"):
        iam.revoke_session(actor, victim_sid)
    assert iam.verify_token(victim)


def test_revocation_during_suspended_async_request_blocks_tool(durable, tmp_path):
    iam, path = durable
    other = MultiTenantIAM(KEY, db_path=path)
    actor = other.issue_token("alpha", "admin")
    token = iam.issue_token("alpha", "reader")
    sid = iam.verify_token(token).token_id
    registry = MCPRegistry(iam=iam, tenant_id="alpha", tenant_root=tmp_path / "tenants")
    register_filesystem_tools(registry)
    started, proceed = Event(), Event()
    original = registry.tools["fs_list"].handler
    async def delayed(**args):
        started.set()
        await asyncio.to_thread(proceed.wait, 3)
        return await original(**args)
    registry.tools["fs_list"].handler = delayed
    def request():
        return asyncio.run(registry.handle_request(JsonRpcRequest(id=1, method="tools/call", params={"name": "fs_list"}), bearer_token=token))
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(request)
        assert started.wait(3)
        other.revoke_session(actor, sid)
        proceed.set()
        response = pending.result(timeout=5)
    assert response.error or "Access denied" in response.result["content"][0]["text"]


def test_environment_selects_durable_store_and_outage_never_falls_back(durable, monkeypatch):
    iam, path = durable
    token = iam.issue_token("alpha", "reader")
    monkeypatch.setenv("MAS_IAM_SECRET", KEY)
    monkeypatch.setenv("MAS_IAM_DB_PATH", str(path))
    configured = MultiTenantIAM()
    context = configured.verify_token(token)
    path.unlink()
    assert not permitted(configured, context)
    with pytest.raises(PermissionError):
        configured.verify_token(token)
    assert not path.exists()


def test_simultaneous_cold_start_and_duplicate_tenant_creation(tmp_path):
    path = tmp_path / "identity.sqlite"
    with ThreadPoolExecutor(max_workers=8) as pool:
        instances = list(pool.map(lambda _: MultiTenantIAM(KEY, db_path=path), range(8)))
        def create(iam):
            try:
                iam.create_tenant("alpha", "Alpha")
                return True
            except ValueError:
                return False
        assert sum(pool.map(create, instances)) == 1
    assert all(iam.get_tenant("alpha") for iam in instances)


def test_expired_and_unissued_signed_tokens_are_not_authority(durable):
    import hashlib
    import hmac
    import base64
    iam, _ = durable
    expired = iam.issue_token("alpha", "reader", ttl_seconds=-1)
    with pytest.raises(PermissionError, match="expired"):
        iam.verify_token(expired)
    issued = iam.issue_token("alpha", "reader")
    raw, _ = issued.split(".")
    claims = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    claims["nonce"] = "0" * 64
    raw = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    signed = raw + "." + hmac.new(KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(PermissionError, match="unavailable"):
        iam.verify_token(signed)


def test_http_logout_bulk_revocation_and_restart(durable, tmp_path):
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from mas.dashboard.server import DashboardServer
    from mas.organization.company import ConsultingEnterprise
    iam, path = durable
    admin = iam.issue_token("alpha", "admin")
    reader = iam.issue_token("alpha", "reader")
    second_reader = iam.issue_token("alpha", "reader")
    beta = iam.issue_token("beta", "admin")
    def request(server, endpoint, token, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = Request(f"http://127.0.0.1:{server.server.server_port}{endpoint}", data=data, headers={"Authorization": f"Bearer {token}"})
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    server = DashboardServer(ConsultingEnterprise(), port=0, iam=iam, tenant_id="alpha", tenant_root=tmp_path / "tenants")
    server.start_background()
    try:
        assert request(server, "/api/identity/sessions/revoke", beta, {})[0] == 403
        assert request(server, "/api/identity/principals/revoke-sessions", reader, {"user_id": "admin"})[0] == 403
        assert request(server, "/api/identity/sessions/revoke", reader, {"session_id": []})[0] == 400
        assert request(server, "/api/identity/sessions/revoke", reader, {})[0] == 200
        assert request(server, "/api/pm/projects", reader)[0] == 403
        assert request(server, "/api/pm/projects", second_reader)[0] == 200
        assert request(server, "/api/identity/principals/revoke-sessions", admin, {"user_id": "reader"}) == (200, {"success": True, "result": 1})
    finally:
        server.shutdown()
    restarted = DashboardServer(ConsultingEnterprise(), port=0, iam=MultiTenantIAM(KEY, db_path=path), tenant_id="alpha", tenant_root=tmp_path / "tenants")
    restarted.start_background()
    try:
        assert request(restarted, "/api/pm/projects", second_reader)[0] == 403
        assert request(restarted, "/api/pm/projects", admin)[0] == 200
        path.unlink()
        assert request(restarted, "/api/pm/projects", admin)[0] == 403
    finally:
        restarted.shutdown()


def test_partial_bulk_revoke_failure_rolls_back_every_session(durable):
    iam, path = durable
    actor = iam.issue_token("alpha", "admin")
    tokens = [iam.issue_token("alpha", "reader") for _ in range(3)]
    with sqlite3.connect(path) as db:
        seq = db.execute("SELECT MAX(seq) FROM audit").fetchone()[0]
        db.execute(f"CREATE TRIGGER fail_second_audit BEFORE INSERT ON audit WHEN NEW.seq={seq + 2} BEGIN SELECT RAISE(ABORT, 'partial audit failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        iam.revoke_principal_sessions(actor, "reader")
    assert all(iam.verify_token(token) for token in tokens)
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT MAX(seq) FROM audit").fetchone()[0] == seq
        db.execute("DROP TRIGGER fail_second_audit")
    assert iam.revoke_principal_sessions(actor, "reader") == 3


@pytest.mark.parametrize("operation", ["issuance", "principal_update", "suspension"])
def test_authority_mutations_require_atomic_audit(durable, operation):
    iam, path = durable
    token = iam.issue_token("alpha", "admin")
    with sqlite3.connect(path) as db:
        rows_before = db.execute("SELECT * FROM records ORDER BY kind,id").fetchall()
        db.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'audit unavailable'); END")
    with pytest.raises(sqlite3.IntegrityError):
        if operation == "issuance":
            iam.issue_token("alpha", "reader")
        elif operation == "principal_update":
            iam.register_principal("alpha", "admin", roles=set())
        else:
            iam.suspend_tenant("alpha")
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT * FROM records ORDER BY kind,id").fetchall() == rows_before
    assert iam.verify_token(token)


def test_identity_database_cannot_be_mounted_as_tenant_workspace(tmp_path):
    from mas.tenancy import tenant_scope
    root = tmp_path / "root"
    path = root / "workspaces/tenants/alpha/identity.sqlite"
    iam = MultiTenantIAM(KEY, db_path=path)
    iam.create_tenant("alpha", "Alpha")
    iam.register_principal("alpha", "reader")
    token = iam.issue_token("alpha", "reader")
    with pytest.raises(PermissionError, match="outside tenant workspaces"):
        with tenant_scope(iam, token, "alpha", root):
            raise AssertionError("Identity database exposed")


def test_old_backup_requires_offline_session_fence_before_serving(durable, tmp_path):
    iam, _ = durable
    actor = iam.issue_token("alpha", "admin")
    token = iam.issue_token("alpha", "reader")
    old = tmp_path / "old-backup.sqlite"
    iam.backup(old)
    iam.revoke_session(actor, iam.verify_token(token).token_id)
    restored = MultiTenantIAM(KEY, db_path=old)
    # Authentic full-state rollback cannot be inferred locally: prove this limit.
    assert restored.verify_token(token)
    assert restored.invalidate_all_sessions() == 2
    restarted = MultiTenantIAM(KEY, db_path=old)
    for old_token in (token, actor):
        with pytest.raises(PermissionError):
            restarted.verify_token(old_token)
    assert restarted.invalidate_all_sessions() == 0
    fresh = restarted.issue_token("alpha", "reader")
    assert restarted.verify_token(fresh)


def test_process_death_during_uncommitted_authority_change_recovers(durable):
    iam, path = durable
    token = iam.issue_token("alpha", "admin")
    script = '''import json,sys,os
from mas.iam import MultiTenantIAM
p=json.load(sys.stdin)
iam=MultiTenantIAM(p['key'],db_path=p['path'])
with iam._store.transaction() as db:
 latest=iam._store.validate_audit(db)
 principal=iam._store.read(db,'principal','alpha:admin',latest)
 principal['roles']=[]
 iam._store.save(db,'principal','alpha:admin',principal)
 os._exit(17)
'''
    result = subprocess.run([sys.executable, "-c", script], input=json.dumps({"key": KEY, "path": str(path)}), text=True, capture_output=True, timeout=10)
    assert result.returncode == 17, result.stderr
    recovered = MultiTenantIAM(KEY, db_path=path)
    assert recovered.get_principal("alpha", "admin").roles == ADMIN
    assert permitted(recovered, recovered.verify_token(token))
