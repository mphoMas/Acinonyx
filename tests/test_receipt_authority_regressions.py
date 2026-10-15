"""Existing GHA-04A review reproductions through the supported service boundary."""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from mas.iam import StandardRole, TenantContext
from mas.pm.gateway.models import ConnectorRegistry
from mas.pm.receipts import DeliveryReceiptService
from mas.tenancy import TenantBinding
from test_gha_receipt_slice import make_contract, make_payload

pytest_plugins = ("test_gha_receipt_slice",)


def service(env):
    return DeliveryReceiptService(
        env["db"], env["connector_reg"], connector_key=("100", "200"),
        tenant_id="tenant-1", project_id="proj-1",
    )


def record(svc, env, *, contract=None, payload=None):
    return svc.record_observation(
        env["binding_1"], "action", "observation",
        make_contract() if contract is None else contract,
        make_payload() if payload is None else payload, issue_id="issue-1",
    )


def assert_empty(env):
    with env["db"]._get_connection() as conn:
        for table in ("pm_delivery_actions", "pm_delivery_receipts", "pm_delivery_items"):
            assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


def test_profile_requires_explicit_trusted_configuration(setup_env):
    with pytest.raises(ValueError):
        DeliveryReceiptService(setup_env["db"])
    with pytest.raises(ValueError):
        DeliveryReceiptService(setup_env["db"], setup_env["connector_reg"])
    with pytest.raises(ValueError):
        DeliveryReceiptService(setup_env["db"], setup_env["connector_reg"], trusted_local=True)
    svc = DeliveryReceiptService(setup_env["db"], trusted_local=True)
    assert record(svc, setup_env)["authority_verified"] is False


@pytest.mark.parametrize("mutation", ["revoked", "removed", "wrong_tenant", "wrong_project"])
def test_current_connector_guards_both_write_and_historical_read(setup_env, mutation):
    env = setup_env
    svc = service(env)
    receipt = record(svc, env)
    config = env["connector_reg"].get_snapshot(("100", "200"))
    if mutation == "removed":
        env["connector_reg"].remove(("100", "200"))
    else:
        changes = {"generation": 2}
        changes.update({"revoked": {"status": "REVOKED"}, "wrong_tenant": {"tenant_id": "tenant-2"},
                        "wrong_project": {"project_id": "other"}}[mutation])
        # Build a fresh registry snapshot through the supported configuration model.
        from mas.pm.gateway.models import GitHubConnectorConfig
        fields = {key: getattr(config, key) for key in GitHubConnectorConfig.model_fields}
        fields["permitted_events"] = list(fields["permitted_events"])
        fields["permitted_ref_patterns"] = dict(fields["permitted_ref_patterns"])
        fields.update(changes)
        env["connector_reg"].update(GitHubConnectorConfig(**fields))
    with pytest.raises(PermissionError):
        record(svc, env)
    with pytest.raises(PermissionError):
        svc.get_receipt(env["binding_1"], receipt["receipt_id"])


@pytest.mark.parametrize("change", ["omit_owner", "omit_transport", "different_repository"])
def test_client_claims_cannot_disable_or_select_connector(setup_env, change):
    env = setup_env
    payload = make_payload()
    if change == "omit_owner":
        del payload["transport_claims"]["repository_owner_id"]
    elif change == "omit_transport":
        del payload["transport_claims"]
    else:
        payload["transport_claims"]["repository_id"] = "999"
    with pytest.raises((ValueError, PermissionError)):
        record(service(env), env, payload=payload)
    assert_empty(env)


@pytest.mark.parametrize("operation", ["read", "write"])
@pytest.mark.parametrize("change", ["expiry", "permission", "revocation"])
def test_full_authorization_repeated_after_guard_wait(setup_env, monkeypatch, operation, change):
    import mas.iam as iam_module
    import mas.pm.receipts as receipts
    env = setup_env
    svc = service(env)
    receipt = record(svc, env)
    original_guard = receipts.get_authority_guard
    original_time = iam_module.time.time

    @contextmanager
    def delayed_guard():
        if change == "expiry":
            monkeypatch.setattr(iam_module.time, "time", lambda: env["binding_1"].identity.expires_at + 1)
        elif change == "permission":
            env["iam"].register_principal("tenant-1", "user-1", roles={StandardRole.READ_ONLY.value})
        else:
            env["iam"].invalidate_all_sessions()
        with original_guard():
            yield

    monkeypatch.setattr(receipts, "get_authority_guard", delayed_guard)
    with pytest.raises(PermissionError):
        if operation == "read":
            svc.get_receipt(env["binding_1"], receipt["receipt_id"])
        else:
            record(svc, env)
    monkeypatch.setattr(iam_module.time, "time", original_time)


def test_database_must_match_trusted_binding(setup_env):
    env = setup_env
    binding = replace(env["binding_1"], database=Path(env["tmp_path"]) / "other.db")
    with pytest.raises(PermissionError):
        service(env).record_observation(binding, "a", "o", make_contract(), make_payload(), issue_id="issue-1")
    assert_empty(env)


def test_constructed_identity_cannot_authorize_service(setup_env):
    env = setup_env
    identity = env["binding_1"].identity
    forged = TenantContext(**identity.__dict__)
    binding = TenantBinding(env["iam"], forged, env["tmp_path"], env["db_path"])
    with pytest.raises(PermissionError):
        service(env).record_observation(binding, "a", "o", make_contract(), make_payload(), issue_id="issue-1")
    assert_empty(env)


@pytest.mark.parametrize("location", ["root", "claims", "transport", "mas", "item", "artifact"])
def test_unknown_fields_are_rejected_recursively(setup_env, location):
    contract, payload = make_contract(), make_payload()
    payload["artifact_claims"] = [{"digest": "d" * 64}]
    target = {"root": payload, "claims": contract["claims"], "transport": payload["transport_claims"],
              "mas": payload["mas_claims"], "item": payload["items"][0], "artifact": payload["artifact_claims"][0]}[location]
    target["unexpected"] = "untrusted"
    with pytest.raises(ValueError):
        record(service(setup_env), setup_env, contract=contract, payload=payload)
    assert_empty(setup_env)


@pytest.mark.parametrize("change", ["contract_bool", "payload_bool", "sha", "digest", "fence_bool", "attempt_bool",
                                   "check_id", "limitations", "source_generation", "artifact_url"])
def test_invalid_types_formats_and_field_limits_refused(setup_env, change):
    contract, payload = make_contract(), make_payload()
    if change == "contract_bool":
        contract["schema_version"] = True
    elif change == "payload_bool":
        payload["schema_version"] = True
    elif change == "sha":
        contract["claims"]["candidate_sha"] = "not-a-sha"
    elif change == "digest":
        payload["artifact_claims"] = [{"digest": "z" * 64}]
    elif change == "fence_bool":
        payload["mas_claims"]["fence"] = True
    elif change == "attempt_bool":
        payload["transport_claims"]["github_run_attempt"] = True
    elif change == "check_id":
        contract["check_ids"] = ["x" * 129]
    elif change == "limitations":
        payload["limitations"] = "x" * 8193
    elif change == "source_generation":
        contract["claims"]["source_generation"] = False
    else:
        payload["artifact_claims"] = [{"digest": "d" * 64, "url": "https://untrusted.test"}]
    with pytest.raises(ValueError):
        record(service(setup_env), setup_env, contract=contract, payload=payload)
    assert_empty(setup_env)


def test_supported_digest_claim_and_nullable_generation_roundtrip(setup_env):
    payload = make_payload()
    payload["artifact_claims"] = [{"digest": "d" * 64}]
    svc = service(setup_env)
    receipt = record(svc, setup_env, payload=payload)
    stored = svc.get_receipt(setup_env["binding_1"], receipt["receipt_id"])
    assert stored["payload"] == payload
    assert stored["contract"] == make_contract()
    assert stored["source_authority_verified"] is False


def test_arbitrary_registry_implementation_is_not_admitted(setup_env):
    with pytest.raises(ValueError):
        DeliveryReceiptService(setup_env["db"], {}, connector_key=("100", "200"), tenant_id="tenant-1", project_id="proj-1")
    assert isinstance(setup_env["connector_reg"], ConnectorRegistry)


def test_delivery_wrapper_uses_startup_policy_for_reads_and_writes(setup_env):
    from mas.pm.delivery import DeliveryService
    from mas.pm.receipt_access import ReceiptAccess
    env = setup_env
    svc = DeliveryService(env["db"], receipt_access=ReceiptAccess(
        env["connector_reg"], ("100", "200"), "tenant-1", "proj-1"))
    result = record(svc, env)
    env["connector_reg"].remove(("100", "200"))
    with pytest.raises(PermissionError):
        svc.get_receipt(env["binding_1"], result["receipt_id"])
    with pytest.raises(PermissionError):
        record(svc, env)
    unconfigured = DeliveryService(env["db"])
    with pytest.raises(PermissionError):
        unconfigured.get_receipt(env["binding_1"], result["receipt_id"])


def test_principal_permission_changes_share_authority_guard(setup_env):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from mas.authority import get_authority_guard
    started, finished = Event(), Event()

    def change_permissions():
        started.set()
        setup_env["iam"].register_principal("tenant-1", "user-1", roles={StandardRole.READ_ONLY.value})
        finished.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        with get_authority_guard():
            future = pool.submit(change_permissions)
            assert started.wait(2)
            assert not finished.wait(0.1)
        future.result(timeout=5)
    assert finished.is_set()
    with pytest.raises(PermissionError):
        record(service(setup_env), setup_env)


def test_exact_item_artifact_and_identifier_limits_are_accepted(setup_env):
    contract = make_contract(check_ids=[f"check-{n:03d}" for n in range(128)])
    payload = make_payload(items=[{"check_id": cid, "claimed_outcome": "PASSED"} for cid in contract["check_ids"]])
    payload["artifact_claims"] = [{"digest": f"{n:064x}"} for n in range(64)]
    payload["limitations"] = "x" * 8192
    svc = service(setup_env)
    result = svc.record_observation(setup_env["binding_1"], "a" * 128, "o" * 128, contract, payload, issue_id="issue-1")
    stored = svc.get_receipt(setup_env["binding_1"], result["receipt_id"])
    assert len(stored["items"]) == 128
    assert len(stored["payload"]["artifact_claims"]) == 64


@pytest.mark.parametrize("change", ["tuple_items", "tuple_checks", "nan", "infinite", "negative_version"])
def test_python_inputs_cannot_coerce_or_hide_invalid_shapes(setup_env, change):
    contract, payload = make_contract(), make_payload()
    if change == "tuple_items":
        payload["items"] = tuple(payload["items"])
    elif change == "tuple_checks":
        contract["check_ids"] = tuple(contract["check_ids"])
    elif change == "nan":
        contract["claims"]["policy_version"] = float("nan")
    elif change == "infinite":
        payload["mas_claims"]["fence"] = float("inf")
    else:
        contract["claims"]["brief_version"] = -1
    with pytest.raises(ValueError):
        record(service(setup_env), setup_env, contract=contract, payload=payload)
    assert_empty(setup_env)


@pytest.mark.parametrize("field", ["action", "observation"])
def test_correlation_identifiers_reject_trailing_newlines(setup_env, field):
    with pytest.raises(ValueError):
        service(setup_env).record_observation(
            setup_env["binding_1"], "action\n" if field == "action" else "action",
            "observation\n" if field == "observation" else "observation",
            make_contract(), make_payload(), issue_id="issue-1")
    assert_empty(setup_env)


def test_registry_key_cannot_alias_another_repository(setup_env):
    from mas.pm.gateway.models import GitHubConnectorConfig
    env = setup_env
    env["connector_reg"][("100", "200")] = GitHubConnectorConfig(
        tenant_id="tenant-1", project_id="proj-1", repository_id="999", repository_owner_id="200",
        approved_workflow_repo="other/repository", approved_workflow_path=".github/workflows/ci.yml",
        approved_workflow_sha="a" * 40, generation=2)
    with pytest.raises(PermissionError):
        record(service(env), env)
    assert_empty(env)
