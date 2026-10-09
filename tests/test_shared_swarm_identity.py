"""Shared platform/swarm authority at real store and CLI boundaries."""
import json
import secrets
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from mas.iam import MultiTenantIAM, StandardRole
from mas.platform.identity import PlatformAuthority
from mas.swarm.cli import main, private_write
from mas.swarm.contracts import SwarmError, digest
from mas.swarm.store import Store

CASES = [{"id": "identity", "input": 1, "expected": 1}]
IMAGE = "sha256:" + "a" * 64
SOURCE = "def solve(payload): return payload"
KEY = "durable-shared-authority-private-test-key" * 2


@pytest.fixture
def setup(tmp_path):
    iam = MultiTenantIAM(KEY, db_path=tmp_path / "identity" / "authority.sqlite")
    tokens = {}
    for tenant in ("alpha", "beta"):
        iam.create_tenant(tenant, tenant)
        for subject, role in (("admin", StandardRole.TENANT_ADMIN), ("owner", StandardRole.SWARM_OWNER),
                              ("writer", StandardRole.SWARM_REQUESTER), ("reviewer", StandardRole.SWARM_APPROVER),
                              ("reader", StandardRole.READ_ONLY)):
            iam.register_principal(tenant, subject, roles={role.value})
            tokens[tenant, subject] = iam.issue_token(tenant, subject)
    store = Store(tmp_path / "runs.sqlite", secrets.token_bytes(32), authority=PlatformAuthority(iam))
    return iam, store, tokens


def ready(store, token):
    doc = store.submit(token, "identity", "Return input unchanged", CASES)
    doc = store.claim(token, doc["id"], IMAGE, provider={"model": "fixture"})
    for state in ("coding", "verifying", "reviewing"):
        store.reserve(token, doc["id"], doc["lease"], 100)
        store.settle(token, doc["id"], doc["lease"], 50)
        doc = store.transition(token, doc["id"], doc["lease"], state)
    return store.transition(token, doc["id"], doc["lease"], "awaiting_approval", source=SOURCE, candidate_hash=digest(SOURCE),
                            review={"approved": True, "reason": "test fixture"}, evidence={"run_id": doc["id"], "candidate_hash": digest(SOURCE),
                            "suite_hash": digest(CASES), "image": IMAGE, "provider": doc["provider"],
                            "results": [{"id": "identity", "passed": True, "status": "passed"}], "finished": time.time()})


def test_same_platform_session_authorizes_swarm_and_platform(setup):
    iam, store, tokens = setup
    token = tokens["alpha", "writer"]
    identity = iam.verify_token(token)
    assert iam.authorize(identity, "swarm:request", "alpha", "urn:mas:tenant:alpha:swarm")
    doc = store.submit(token, "shared", "Return input unchanged", CASES)
    assert (doc["tenant"], doc["submitted_by"]) == ("alpha", "writer")
    assert store.get(tokens["alpha", "reviewer"], doc["id"])["id"] == doc["id"]
    with pytest.raises((PermissionError, SwarmError)):
        store.get(tokens["beta", "owner"], doc["id"])


@pytest.mark.parametrize("subject", ["reader", "admin", "reviewer"])
def test_no_implicit_swarm_submission_from_unrelated_roles(setup, subject):
    _, store, tokens = setup
    with pytest.raises(PermissionError):
        store.submit(tokens["alpha", subject], "denied", "Return input", CASES)


def test_separate_human_approval_and_role_enforcement(setup):
    _, store, tokens = setup
    doc = ready(store, tokens["alpha", "writer"])
    with pytest.raises(PermissionError):
        store.approve(tokens["alpha", "writer"], doc["id"], doc["candidate_hash"])
    assert store.approve(tokens["alpha", "reviewer"], doc["id"], doc["candidate_hash"])["approved_by"] == "reviewer"


def test_owner_cannot_approve_own_submission(setup):
    _, store, tokens = setup
    doc = ready(store, tokens["alpha", "owner"])
    with pytest.raises(SwarmError, match="separate human"):
        store.approve(tokens["alpha", "owner"], doc["id"], doc["candidate_hash"])


@pytest.mark.parametrize("change", ["revoke", "suspend", "roles"])
def test_authority_changes_immediately_block_existing_swarm_sessions(setup, change):
    iam, store, tokens = setup
    token = tokens["alpha", "writer"]
    doc = store.submit(token, "shared", "Return input", CASES)
    if change == "revoke":
        iam.revoke_session(tokens["alpha", "admin"], iam.verify_token(token).token_id)
    elif change == "suspend":
        iam.suspend_tenant("alpha")
    else:
        iam.register_principal("alpha", "writer", roles={StandardRole.READ_ONLY.value})
    with pytest.raises(PermissionError):
        store.get(token, doc["id"])
    with pytest.raises(PermissionError):
        store.claim(token, doc["id"], IMAGE)


def test_bound_store_rejects_disabled_wrong_or_modified_authority(setup, tmp_path):
    iam, store, _ = setup
    with pytest.raises(SwarmError):
        Store(store.path, store._key)
    other = MultiTenantIAM(KEY, db_path=tmp_path / "other" / "iam.sqlite")
    with pytest.raises(SwarmError):
        Store(store.path, store._key, authority=PlatformAuthority(other))
    with sqlite3.connect(store.path) as db:
        db.execute("UPDATE authority_binding SET document=?", ('{"mode":"local","version":1}',))
    with pytest.raises(SwarmError):
        Store(store.path, store._key, authority=PlatformAuthority(iam))


def test_local_credentials_cannot_authenticate_or_be_enrolled_in_platform_mode(setup):
    _, store, tokens = setup
    for token in ("", secrets.token_urlsafe(32)):
        with pytest.raises(PermissionError):
            store.submit(token, "denied", "Return input", CASES)
    with pytest.raises(SwarmError):
        store.provision("alpha", "new", "owner")
    with pytest.raises(SwarmError):
        store.revoke(tokens["alpha", "owner"], "writer")


def test_existing_local_state_requires_reviewed_migration(setup, tmp_path):
    iam, _, _ = setup
    local = Store(tmp_path / "local.sqlite", secrets.token_bytes(32))
    token = local.provision("alpha", "writer", "requester")
    local.submit(token, "old", "Return input", CASES)
    with pytest.raises(SwarmError):
        Store(local.path, local._key, authority=PlatformAuthority(iam))
    assert local.get(token, local.submit(token, "old", "Return input", CASES)["id"])


def test_shared_authority_requires_durable_separate_databases(setup):
    iam, _, _ = setup
    with pytest.raises(ValueError):
        PlatformAuthority(MultiTenantIAM(KEY))
    with pytest.raises(SwarmError):
        Store(iam.database_path, secrets.token_bytes(32), authority=PlatformAuthority(iam))


def test_revocation_cannot_commit_between_authorization_and_swarm_commit(setup):
    iam, store, tokens = setup
    token = tokens["alpha", "writer"]
    started, finished = Event(), Event()
    independent = MultiTenantIAM(KEY, db_path=iam.database_path)
    def revoke():
        started.set()
        independent.revoke_session(tokens["alpha", "admin"], independent.verify_token(token).token_id)
        finished.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with store._tx() as db:
            assert store._auth(db, token, {"requester"})["subject"] == "writer"
            future = pool.submit(revoke)
            assert started.wait(2)
            assert not finished.wait(.15)
        future.result(timeout=3)
    with pytest.raises(PermissionError):
        store.require_role(token, {"requester"})


def test_cli_platform_init_submit_revoke_and_downgrade(setup, tmp_path, monkeypatch, capsys):
    iam, _, tokens = setup
    monkeypatch.setenv("MAS_IAM_DB_PATH", str(iam.database_path))
    monkeypatch.setenv("MAS_IAM_SECRET", KEY)
    root = tmp_path / "cli"
    owner, writer = tmp_path / "owner.token", tmp_path / "writer.token"
    private_write(owner, tokens["alpha", "owner"].encode())
    private_write(writer, tokens["alpha", "writer"].encode())
    prefix = ["--identity", "platform", "--state-dir", str(root)]
    assert main(prefix + ["--token-file", str(owner), "init", "--tenant", "alpha", "--subject", "owner"]) == 0
    assert not (root / "owner.token").exists()
    cases = tmp_path / "cases.json"
    cases.write_text(json.dumps(CASES))
    capsys.readouterr()
    assert main(prefix + ["--token-file", str(writer), "submit", "--request-key", "cli", "--goal", "Return input", "--cases", str(cases)]) == 0
    run = json.loads(capsys.readouterr().out)["run_id"]
    assert main(["--state-dir", str(root), "--token-file", str(writer), "show", run]) == 1
    assert main(prefix + ["--token-file", str(owner), "revoke", "--subject", "writer"]) == 1
    iam.revoke_session(tokens["alpha", "admin"], iam.verify_token(tokens["alpha", "writer"]).token_id)
    assert main(prefix + ["--token-file", str(writer), "show", run]) == 1


def test_same_session_works_at_real_platform_mcp_and_swarm_then_revokes(setup, tmp_path):
    import asyncio
    from mas.mcp.protocol import MCPRegistry, JsonRpcRequest
    from mas.pm.tools import register_pm_tools
    iam, store, tokens = setup
    iam.register_principal("alpha", "writer", roles={StandardRole.SWARM_REQUESTER.value, StandardRole.DATA_ARCHITECT.value})
    token = iam.issue_token("alpha", "writer")
    registry = MCPRegistry(iam=iam, tenant_id="alpha", tenant_root=tmp_path / "tenant-runtime")
    register_pm_tools(registry)
    def invoke():
        return asyncio.run(registry.handle_request(JsonRpcRequest(method="tools/call", id=1,
                           params={"name": "pm_create_project", "arguments": {"key": "SHARED", "name": "Shared"}}), bearer_token=token))
    assert invoke().error is None
    doc = store.submit(token, "shared-mcp", "Return input", CASES)
    iam.revoke_session(tokens["alpha", "admin"], iam.verify_token(token).token_id)
    assert invoke().error is not None
    with pytest.raises(PermissionError):
        store.get(token, doc["id"])


def test_reopened_authority_and_store_share_current_revocation(setup):
    iam, store, tokens = setup
    token = tokens["alpha", "writer"]
    doc = store.submit(token, "restart", "Return input", CASES)
    fresh_iam = MultiTenantIAM(KEY, db_path=iam.database_path)
    fresh_store = Store(store.path, store._key, authority=PlatformAuthority(fresh_iam))
    assert fresh_store.get(token, doc["id"])["id"] == doc["id"]
    iam.revoke_principal_sessions(tokens["alpha", "admin"], "writer")
    for instance in (store, fresh_store):
        with pytest.raises(PermissionError):
            instance.get(token, doc["id"])


def test_expired_or_unavailable_platform_authority_never_falls_back(setup):
    iam, store, _ = setup
    token = iam.issue_token("alpha", "writer", ttl_seconds=.05)
    time.sleep(.08)
    with pytest.raises(PermissionError):
        store.require_role(token, {"requester"})
    iam.database_path.rename(iam.database_path.with_suffix(".offline"))
    with pytest.raises(PermissionError):
        store.require_role(token, {"requester"})


def test_cli_export_rechecks_shared_authority(setup, tmp_path, monkeypatch):
    import shutil
    iam, store, tokens = setup
    doc = ready(store, tokens["alpha", "writer"])
    store.approve(tokens["alpha", "reviewer"], doc["id"], doc["candidate_hash"])
    root = tmp_path / "export-cli"
    root.mkdir(mode=0o700)
    shutil.copyfile(store.path, root / "state.db")
    private_write(root / "signing.key", store._key)
    credential = tmp_path / "exporter.token"
    private_write(credential, tokens["alpha", "writer"].encode())
    monkeypatch.setenv("MAS_IAM_DB_PATH", str(iam.database_path))
    monkeypatch.setenv("MAS_IAM_SECRET", KEY)
    prefix = ["--identity", "platform", "--state-dir", str(root), "--token-file", str(credential)]
    output = tmp_path / "approved.py"
    assert main(prefix + ["export", doc["id"], "--out", str(output)]) == 0
    assert output.read_text() == SOURCE
    iam.revoke_session(tokens["alpha", "admin"], iam.verify_token(tokens["alpha", "writer"]).token_id)
    denied = tmp_path / "denied.py"
    assert main(prefix + ["export", doc["id"], "--out", str(denied)]) == 1
    assert not denied.exists()


def test_removed_binding_cannot_downgrade_even_empty_platform_store(setup):
    iam, store, _ = setup
    with sqlite3.connect(store.path) as db:
        db.execute("DROP TABLE authority_binding")
    for authority in (None, PlatformAuthority(iam)):
        with pytest.raises(SwarmError, match="binding was removed"):
            Store(store.path, store._key, authority=authority)
