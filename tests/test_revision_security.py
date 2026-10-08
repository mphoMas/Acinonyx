"""Adversarial and restore checks for the audited repository revision."""
import hashlib
import json
import secrets
import sqlite3
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import pytest

from mas.dashboard.server import DashboardServer
from mas.iam import MultiTenantIAM
from mas.organization.company import ConsultingEnterprise
from mas.pm.db import PMDatabase
from mas.pm.guards import UnverifiedWorkError, validate_critic_verdicts
from mas.pm.models import CriticVerdict, CriticVerdictType, EvidenceLink, EvidenceType, Issue, IssueState, Project
from mas.security import ExecutionContext, sign_evidence_provenance, sign_verdict_payload
from mas.swarm.store import Store


def test_governance_missing_or_short_keys_fail_closed(monkeypatch):
    monkeypatch.delenv("MAS_VERDICT_SECRET")
    monkeypatch.delenv("MAS_EVIDENCE_SECRET")
    for key in (None, "short"):
        with pytest.raises(ValueError, match="private governance signing key"):
            sign_verdict_payload("issue", "qa", "PASS", 0, secret_key=key)
        with pytest.raises(ValueError, match="private governance signing key"):
            sign_evidence_provenance("ev", "issue", "TEST_RUN_LOG", "hash", "uri", secret_key=key)


def test_default_iam_instances_do_not_share_a_public_key(monkeypatch):
    monkeypatch.delenv("MAS_IAM_SECRET", raising=False)
    first, second = MultiTenantIAM(), MultiTenantIAM()
    for iam in (first, second):
        iam.create_tenant("company", "Company")
        iam.register_principal("company", "developer")
    token = first.issue_token("company", "developer")
    assert first.verify_token(token).principal_id == "developer"
    with pytest.raises(PermissionError, match="signature"):
        second.verify_token(token)
    with pytest.raises(ValueError, match="32 bytes"):
        MultiTenantIAM("short")


@pytest.mark.parametrize("signature", ["sig_fake", "", "f" * 64])
def test_forged_legacy_verdict_never_satisfies_review(tmp_path, signature):
    db = PMDatabase(tmp_path / "pm.db")
    db.create_project(Project(id="p", key="AUD", name="Audit"))
    issue = db.create_issue(Issue(id="i", project_id="p", key="AUD-1", title="Review", current_state=IssueState.VERIFICATION))
    verdict = CriticVerdict(id="v", issue_id="i", reviewer_principal="qa_critic", verdict=CriticVerdictType.PASS, signature=signature)
    # Bypass insertion authentication only to simulate a forged on-disk record.
    db.record_verdict(verdict, enforce_auth=False)
    if not signature:
        with sqlite3.connect(db.db_path) as conn:
            conn.execute("UPDATE pm_critic_verdicts SET signature='' WHERE id='v'")
    with pytest.raises(UnverifiedWorkError, match="signature"):
        validate_critic_verdicts(db, issue, ["qa_critic"])


def post(server, path, payload, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(f"http://127.0.0.1:{server.server.server_port}{path}", data=json.dumps(payload).encode(), headers=headers)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    return opener.open(request, timeout=3)


def test_dashboard_without_configured_token_denies_mutation(monkeypatch):
    monkeypatch.delenv("MAS_DASHBOARD_TOKEN", raising=False)
    server = DashboardServer(ConsultingEnterprise(), port=0)
    server.start_background()
    try:
        with pytest.raises(urllib.error.HTTPError) as failure:
            post(server, "/api/dispatch", {"enabled": True})
        assert failure.value.code == 401
        assert not server.enterprise.is_live_dispatch_enabled()
    finally:
        server.shutdown()


def test_dashboard_token_cannot_claim_another_reviewer(monkeypatch):
    monkeypatch.setenv("MAS_DASHBOARD_PRINCIPAL", "qa_critic")
    server = DashboardServer(ConsultingEnterprise(), port=0, auth_token="private-fixture-token")
    server.start_background()
    try:
        with pytest.raises(urllib.error.HTTPError) as failure:
            post(server, "/api/pm/verdicts", {"issue_key": "AUD-1", "verdict": "PASS", "reviewer_principal": "chief_architect"}, "private-fixture-token")
        assert failure.value.code == 403
    finally:
        server.shutdown()


def test_concurrent_dashboards_do_not_exchange_credentials_or_state():
    first = DashboardServer(ConsultingEnterprise(name="First"), port=0, auth_token="fixture-first-token")
    second = DashboardServer(ConsultingEnterprise(name="Second"), port=0, auth_token="fixture-second-token")
    first.start_background()
    second.start_background()
    try:
        for server, own, other in ((first, "fixture-first-token", "fixture-second-token"), (second, "fixture-second-token", "fixture-first-token")):
            with pytest.raises(urllib.error.HTTPError) as failure:
                post(server, "/api/dispatch", {"enabled": False}, other)
            assert failure.value.code == 401
            with post(server, "/api/dispatch", {"enabled": False}, own) as response:
                assert response.status == 200
            assert server.server.RequestHandlerClass.enterprise is server.enterprise
        first.server.RequestHandlerClass.cio_audit_report = {"canary": "first"}
        assert second.server.RequestHandlerClass.cio_audit_report is None
    finally:
        first.shutdown()
        second.shutdown()


def test_pm_backup_restores_evidence_verdict_and_immutability(tmp_path):
    db = PMDatabase(tmp_path / "original.db")
    db.create_project(Project(id="p", key="RST", name="Restore"))
    issue = db.create_issue(Issue(id="i", project_id="p", key="RST-1", title="Restore", current_state=IssueState.VERIFICATION))
    log = tmp_path / "evidence.log"
    log.write_text("trusted test fixture")
    db.attach_evidence(EvidenceLink(id="e", issue_id="i", evidence_type=EvidenceType.TEST_RUN_LOG, content_hash=hashlib.sha256(log.read_bytes()).hexdigest(), uri=str(log), payload={"exit_code": 0}))
    with ExecutionContext.scope("qa_critic"):
        db.record_verdict(CriticVerdict(id="v", issue_id="i", reviewer_principal="qa_critic", verdict=CriticVerdictType.PASS))
    with sqlite3.connect(db.db_path) as source, sqlite3.connect(tmp_path / "restored.db") as destination:
        source.backup(destination)
    restored = PMDatabase(tmp_path / "restored.db")
    assert restored.get_issue("RST-1").current_state == IssueState.VERIFICATION
    assert restored.verify_issue_evidence_integrity("i")["valid"]
    validate_critic_verdicts(restored, issue, ["qa_critic"])
    with sqlite3.connect(restored.db_path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM pm_evidence_links WHERE id='e'")


def test_swarm_concurrent_idempotent_submissions_restore_consistently(tmp_path):
    key = secrets.token_bytes(32)
    store = Store(tmp_path / "state.db", key)
    owner = store.provision("company", "owner", "owner")
    cases = [{"id": "zero", "input": [], "expected": 0}]
    def submit(index):
        return store.submit(owner, f"request-{index % 8}", "Sum", cases)["id"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(submit, range(32)))
    assert len(set(ids)) == 8
    for run_id in set(ids):
        store.cancel(owner, run_id)
    store.backup(tmp_path / "backup.db")
    restored = Store(tmp_path / "backup.db", key)
    restored.verify_audit()
    for run_id in set(ids):
        assert restored.get(owner, run_id)["state"] == "cancelled"


def test_pm_configured_path_survives_process_restart(tmp_path):
    import os
    import subprocess
    import sys
    root = str(__import__("pathlib").Path(__file__).resolve().parents[1])
    target = tmp_path / "persistent.db"
    environment = {**os.environ, "MAS_PM_DB_PATH": str(target), "PYTHONPATH": root}
    create = "from mas.pm.db import PMDatabase; from mas.pm.models import Project; PMDatabase().create_project(Project(id='p',key='RST',name='Persistent'))"
    read = "from mas.pm.db import PMDatabase; print(PMDatabase().get_project_by_key('RST').name)"
    subprocess.run([sys.executable, "-c", create], env=environment, cwd=tmp_path, check=True, capture_output=True, timeout=10)
    restored = subprocess.run([sys.executable, "-c", read], env=environment, cwd=tmp_path, check=True, capture_output=True, text=True, timeout=10)
    assert restored.stdout.strip() == "Persistent"
    assert target.is_file()
    assert not (tmp_path / "mas_pm.db").exists()


def test_failed_required_bus_audit_prevents_dispatch():
    import asyncio
    asyncio.run(_failed_required_bus_audit_prevents_dispatch())


async def _failed_required_bus_audit_prevents_dispatch():
    from unittest.mock import Mock
    from mas.core.event_bus import EventBus
    from mas.core.message import Message, MessageMetadata
    bus = EventBus()
    bus._audit = Mock()
    bus._audit.append_message.side_effect = OSError("audit storage unavailable")
    received = []
    async def subscriber(message):
        received.append(message)
    bus.subscribe("sink", subscriber, topic="audit.regression")
    with pytest.raises(OSError, match="audit storage unavailable"):
        await bus.publish(Message(sender="source", recipient="sink", content="work", metadata=MessageMetadata(topic="audit.regression")))
    assert received == []
    assert bus.get_history() == []
    assert bus._published_count == 0
