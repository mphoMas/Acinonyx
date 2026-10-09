"""Two real tenant stores: authorization, persistence, and tool isolation attacks."""
import asyncio
from dataclasses import replace

import pytest

from mas.iam import MultiTenantIAM, StandardRole
from mas.mcp.protocol import MCPRegistry, JsonRpcRequest
from mas.pm.tools import register_pm_tools
from mas.tenancy import current_binding, tenant_scope
from mas.tools.filesystem import register_filesystem_tools


@pytest.fixture
def tenants(tmp_path):
    iam = MultiTenantIAM(signing_secret="disposable-test-key-" * 3)
    registries, tokens = {}, {}
    for tenant in ("alpha", "beta"):
        iam.create_tenant(tenant, tenant)
        iam.register_principal(tenant, "alice", roles={StandardRole.TENANT_ADMIN.value})
        tokens[tenant] = iam.issue_token(tenant, "alice")
        registry = MCPRegistry(iam=iam, tenant_id=tenant, tenant_root=tmp_path)
        register_filesystem_tools(registry)
        register_pm_tools(registry)
        registries[tenant] = registry
    return iam, registries, tokens, tmp_path


def invoke(registry, token, name, arguments=None, **claims):
    return asyncio.run(registry.handle_request(JsonRpcRequest(
        method="tools/call", id=1, params={"name": name, "arguments": arguments or {}, **claims}
    ), bearer_token=token))


def test_credentials_and_claimed_identity_cannot_cross_tenants(tenants):
    _, registries, tokens, _ = tenants
    assert invoke(registries["beta"], tokens["alpha"], "fs_list").error
    assert invoke(registries["alpha"], None, "fs_list").error
    assert invoke(registries["alpha"], tokens["alpha"], "fs_list", principal="beta:alice").error
    with pytest.raises(PermissionError):
        registries["alpha"].call_tool("fs_list")
    assert current_binding() is None


def test_equal_project_keys_use_separate_persistent_databases(tenants):
    iam, registries, tokens, root = tenants
    for tenant in registries:
        response = invoke(registries[tenant], tokens[tenant], "pm_create_project", {"key": "CORE", "name": tenant})
        assert response.error is None
        response = invoke(registries[tenant], tokens[tenant], "pm_create_issue", {"project_key": "CORE", "title": tenant})
        assert response.error is None
    for tenant in registries:
        # New registry/DB objects simulate request restart; never select global DB.
        fresh = MCPRegistry(iam=iam, tenant_id=tenant, tenant_root=root)
        register_pm_tools(fresh)
        response = invoke(fresh, tokens[tenant], "pm_get_issue", {"issue_key": "CORE-1"})
        assert response.error is None
        assert f"'title': '{tenant}'" in response.result["content"][0]["text"]
    assert (root / "state/tenants/alpha/pm.db").exists()
    assert (root / "state/tenants/beta/pm.db").exists()


@pytest.mark.parametrize("attack", ["absolute", "traversal", "symlink", "state"])
def test_filesystem_cross_tenant_and_private_state_denied(tenants, attack):
    _, registries, tokens, root = tenants
    for tenant in registries:
        assert invoke(registries[tenant], tokens[tenant], "fs_write", {"path": "secret.txt", "content": tenant}).error is None
    alpha = root / "workspaces/tenants/alpha"
    beta = root / "workspaces/tenants/beta/secret.txt"
    (alpha / "link").symlink_to(beta)
    paths = {"absolute": str(beta), "traversal": "../beta/secret.txt", "symlink": "link", "state": str(root / "state/tenants/beta/pm.db")}
    response = invoke(registries["alpha"], tokens["alpha"], "fs_read", {"path": paths[attack]})
    assert "Access denied" in response.result["content"][0]["text"]
    response = invoke(registries["alpha"], tokens["alpha"], "fs_write", {"path": paths[attack], "content": "overwritten"})
    assert "Access denied" in response.result["content"][0]["text"]
    assert beta.read_text() == "beta"


def test_current_roles_suspend_and_forged_context_fail_closed(tenants):
    iam, _, tokens, _ = tenants
    context = iam.verify_token(tokens["alpha"])
    args = ("tools:execute", "alpha", "urn:mas:tenant:alpha:tool:fs_write")
    assert iam.authorize(context, *args)
    assert not iam.authorize(replace(context), *args)
    assert not iam.authorize(context, "tools:execute", "alpha", "urn:mas:tenant:beta:tool:fs_write")
    iam.get_principal("alpha", "alice").roles.clear()
    assert not iam.authorize(context, *args)
    iam.suspend_tenant("alpha")
    with pytest.raises(PermissionError):
        iam.verify_token(tokens["alpha"])


def test_concurrent_request_contexts_do_not_bleed(tenants):
    iam, _, tokens, root = tenants
    async def work(tenant):
        with tenant_scope(iam, tokens[tenant], tenant, root):
            before = current_binding()
            await asyncio.sleep(0.01)
            assert current_binding() is before
            return before.identity.tenant_id
    async def run():
        return await asyncio.gather(*(work(tenant) for tenant in ["alpha", "beta"] * 10))
    assert asyncio.run(run()) == ["alpha", "beta"] * 10
    assert current_binding() is None


def test_unsupported_handlers_and_cached_foreign_db_are_denied(tenants):
    iam, registries, tokens, root = tenants
    from mas.pm.db import PMDatabase
    with tenant_scope(iam, tokens["beta"], "beta", root):
        foreign = PMDatabase()
    registries["alpha"].register_tool("gcs_read", "unsupported", {}, lambda: "secret", allow_default=True)
    assert invoke(registries["alpha"], tokens["alpha"], "gcs_read").error
    with tenant_scope(iam, tokens["alpha"], "alpha", root):
        with pytest.raises(PermissionError):
            foreign.get_project_by_key("CORE")
        with pytest.raises(PermissionError):
            PMDatabase(foreign.db_path)


def test_read_only_token_cannot_write(tenants):
    iam, registries, _, _ = tenants
    iam.register_principal("alpha", "reader")
    token = iam.issue_token("alpha", "reader")
    assert invoke(registries["alpha"], token, "fs_list").error is None
    assert invoke(registries["alpha"], token, "fs_write", {"path": "bad", "content": "bad"}).error
    assert invoke(registries["alpha"], token, "pm_create_project", {"key": "CORE", "name": "bad"}).error


def test_workspace_symlink_and_newline_tenant_names_rejected(tmp_path):
    iam = MultiTenantIAM()
    (tmp_path / "tenants").mkdir()
    (tmp_path / "outside").mkdir()
    (tmp_path / "tenants/alpha").symlink_to(tmp_path / "outside", target_is_directory=True)
    with pytest.raises(PermissionError):
        iam.get_isolated_sandbox_path("alpha", str(tmp_path))
    with pytest.raises(ValueError):
        iam.create_tenant("alpha\n", "bad")


def test_python_mounts_only_current_workspace_even_if_global_sandbox_disabled(tenants, monkeypatch):
    iam, _, tokens, root = tenants
    from mas.tools import executor
    from mas.config import CONFIG
    monkeypatch.setattr(CONFIG, "sandbox_python", False)
    monkeypatch.setattr(executor.shutil, "which", lambda _: "/usr/bin/bwrap")
    with tenant_scope(iam, tokens["alpha"], "alpha", root):
        command, _ = executor._build_command_and_env("print(1)")
        mounts = [command[i + 1] for i, value in enumerate(command) if value == "--bind-try"]
        assert mounts == [str(root / "workspaces/tenants/alpha")]
        assert str(root / "state/tenants/alpha") not in command
        monkeypatch.setattr(executor.shutil, "which", lambda _: None)
        with pytest.raises(RuntimeError, match="host execution refused"):
            executor._build_command_and_env("print(1)")


def test_pm_helpers_cannot_replace_authenticated_principal(tenants):
    iam, _, tokens, root = tenants
    from mas.pm.tools import pm_transition_issue, pm_cast_verdict
    with tenant_scope(iam, tokens["alpha"], "alpha", root):
        with pytest.raises(PermissionError, match="Impersonation"):
            pm_transition_issue("CORE-1", "ACTIVE", "beta:alice")
        with pytest.raises(PermissionError, match="Impersonation"):
            pm_cast_verdict("CORE-1", "beta:alice", "APPROVED")


def test_client_authenticates_each_request_and_denies_unscoped_resources(tenants):
    _, registries, tokens, _ = tenants
    from mas.mcp.transport import MCPClient
    async def run():
        client = MCPClient(registries["alpha"], bearer_token=tokens["alpha"])
        assert (await client.initialize())["serverInfo"]["name"] == "mas-mcp"
        assert await client.list_tools()
        assert "Empty directory" in await client.call_tool("fs_list")
        with pytest.raises(RuntimeError, match="lacks tenant isolation"):
            await client.read_resource("secret://beta")
    asyncio.run(run())


def test_http_tenant_credentials_isolate_reads_writes_and_unsupported_routes(tenants):
    import json
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from mas.dashboard.server import DashboardServer
    from mas.organization.company import ConsultingEnterprise
    iam, registries, tokens, root = tenants
    servers = []
    def request(server, path, token=None, body=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        data = json.dumps(body).encode() if body is not None else None
        req = Request(f"http://127.0.0.1:{server.server.server_port}{path}", data=data, headers=headers)
        try:
            with urlopen(req, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)
    try:
        for tenant in registries:
            assert invoke(registries[tenant], tokens[tenant], "pm_create_project", {"key": "CORE", "name": tenant}).error is None
            server = DashboardServer(ConsultingEnterprise(name=tenant), port=0, iam=iam, tenant_id=tenant, tenant_root=root)
            server.start_background()
            servers.append(server)
        for tenant, server in zip(registries, servers):
            status, payload = request(server, "/api/pm/projects", tokens[tenant])
            assert status == 200
            assert [item["name"] for item in payload["projects"]] == [tenant]
            assert request(server, "/api/pm/projects")[0] == 403
            other = "beta" if tenant == "alpha" else "alpha"
            assert request(server, "/api/pm/projects", tokens[other])[0] == 403
            assert request(server, "/api/events", tokens[tenant])[0] == 403
            assert request(server, "/portal/snapshot.json", tokens[tenant])[0] == 403
            assert request(server, "/api/dispatch", tokens[tenant], {"enabled": True})[0] == 403
            status, _ = request(server, "/api/pm/issues/create", tokens[tenant], {"project_key": "CORE", "title": tenant})
            assert status == 200
            status, payload = request(server, "/api/pm/issues/CORE", tokens[tenant])
            assert status == 200
            assert [item["title"] for item in payload] == [tenant]
        iam.register_principal("alpha", "reader")
        token = iam.issue_token("alpha", "reader")
        assert request(servers[0], "/api/pm/issues/create", token, {"project_key": "CORE", "title": "bad"})[0] == 403
    finally:
        for server in servers:
            server.shutdown()


def test_real_python_worker_cannot_read_other_tenant_or_state(tenants):
    iam, registries, tokens, root = tenants
    from mas.tools.executor import register_default_tools
    register_default_tools(registries["alpha"])
    invoke(registries["beta"], tokens["beta"], "fs_write", {"path": "secret", "content": "beta-secret"})
    code = f"""from pathlib import Path
for path in [{str(root / 'workspaces/tenants/beta/secret')!r}, {str(root / 'state/tenants/alpha/pm.db')!r}]:
    try:
        print(Path(path).read_text())
    except (FileNotFoundError, PermissionError):
        print('DENIED')
Path({str(root / 'workspaces/tenants/alpha/proof')!r}).write_text('own-workspace')
"""
    response = invoke(registries["alpha"], tokens["alpha"], "run_python", {"code": code})
    assert response.error is None
    assert response.result["content"][0]["text"].strip() == "DENIED\nDENIED"
    assert (root / "workspaces/tenants/alpha/proof").read_text() == "own-workspace"
    iam.register_principal("alpha", "operator", roles={StandardRole.OPERATOR.value})
    operator = iam.issue_token("alpha", "operator")
    response = invoke(registries["alpha"], operator, "run_python", {"code": "print(1)"})
    assert response.error or "denied" in response.result["content"][0]["text"].lower()


def test_symlink_swap_after_precheck_cannot_leak_or_overwrite(tenants, monkeypatch):
    iam, _, tokens, root = tenants
    from mas.tools import filesystem
    foreign = root / "foreign"
    foreign.write_text("private")
    with tenant_scope(iam, tokens["alpha"], "alpha", root):
        victim = current_binding().workspace / "victim"
        victim.write_text("local")
        original = filesystem._is_path_safe
        def swap(path):
            safe = original(path)
            victim.unlink(missing_ok=True)
            victim.symlink_to(foreign)
            return safe
        monkeypatch.setattr(filesystem, "_is_path_safe", swap)
        result = asyncio.run(filesystem.fs_read_file(str(victim)))
        assert "private" not in result
        victim.unlink()
        victim.write_text("local")
        result = asyncio.run(filesystem.fs_write_file(str(victim), "overwritten"))
        assert "SUCCESS" not in result
        assert foreign.read_text() == "private"


def test_parallel_tenant_issue_writes_keep_sequences_and_data_separate(tenants):
    from concurrent.futures import ThreadPoolExecutor
    _, registries, tokens, _ = tenants
    for tenant in registries:
        assert invoke(registries[tenant], tokens[tenant], "pm_create_project", {"key": "CORE", "name": tenant}).error is None
    def create(item):
        tenant, index = item
        return invoke(registries[tenant], tokens[tenant], "pm_create_issue", {"project_key": "CORE", "title": f"{tenant}-{index}"})
    work = [(tenant, index) for index in range(12) for tenant in registries]
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = list(pool.map(create, work))
    assert all(response.error is None for response in responses)
    for tenant in registries:
        response = invoke(registries[tenant], tokens[tenant], "pm_list_issues", {"project_key": "CORE"})
        assert response.error is None
        text = response.result["content"][0]["text"]
        assert text.count("'title':") == 12
        assert ("beta-" if tenant == "alpha" else "alpha-") not in text
