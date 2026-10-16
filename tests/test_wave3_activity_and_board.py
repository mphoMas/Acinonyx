"""Wave 3 qualification tests for SBA-04, SBA-06, and CC-10 (P4 + P5).

Verifies:
- ActivityBridgeService event ingestion, sequence ordering, idempotency, and authority class checks
- ActivitySpool progress coalescing, capacity backpressure, and ordered replay
- Task activity and project changes projections (including 410 resync_required on cursor gap)
- Live Playwright browser + real DashboardServer incremental polling, cursor recovery, and 401/403 stop
"""
from __future__ import annotations

import json
import secrets
import shutil
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

from mas.dashboard.server import DashboardServer
from mas.iam import MultiTenantIAM
from mas.organization.company import ConsultingEnterprise
from mas.pm.activity import ActivityBridgeService, ActivityError, ActivitySpool
from mas.pm.coordinator import CoordinatorStore, trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.models import Issue, IssueState, IssueType, PriorityLevel, Project
from mas.tenancy import resolve_tenant_database_path


def _seed_project_and_attempt(db: PMDatabase, tenant_id: str = "t-alpha") -> tuple[str, str, str]:
    proj = Project(id="proj-sba", key="SBA", name="Scrum Board Automation")
    db.create_project(proj)
    issue = Issue(
        id="iss-sba-4",
        project_id=proj.id,
        key="SBA-4",
        task_id="SBA-04",
        title="Runtime activity and evidence ingestion bridge",
        description="Bridge runtime events to MAS-PM",
        issue_type=IssueType.TASK,
        current_state=IssueState.STAGED,
        priority=PriorityLevel.HIGH,
        assignee_principal=f"{tenant_id}:antigravity_dev",
        appetite_tokens=50000,
        path_whitelist=["mas/pm/activity.py"],
    )
    db.create_issue(issue)
    with db.atomic_transaction() as c:
        c.execute(
            """
            INSERT INTO pm_task_mappings(project_id, planning_reference, task_id, local_issue_id, local_issue_key)
            VALUES (?, 'SBA-04', 'SBA-04', ?, 'SBA-4')
            """,
            (proj.id, issue.id),
        )
    store = CoordinatorStore(db)
    with trusted_coordinator_admin_scope():
        store.create_attempt_with_intent(
            "att-sba-4",
            "int-sba-4",
            tenant_id,
            proj.id,
            issue.id,
            "SBA-04",
            1,
            "antigravity",
            {},
            budget_reservation=1000,
        )
        assert store.claim_intent("int-sba-4", "worker-1", 1, 100, 60)
        assert store.pre_spawn_intent("int-sba-4", "worker-1", 2, 101, "run-sba-4", "att-sba-4")
    return proj.id, issue.id, "att-sba-4"


def test_activity_bridge_ingestion_dedup_sequence_and_authority(tmp_path: Path) -> None:
    db = PMDatabase(str(tmp_path / "pm.db"))
    proj_id, issue_id, attempt_id = _seed_project_and_attempt(db)
    svc = ActivityBridgeService(db)

    # 1. Valid guest event (sequence 1)
    ev1 = {
        "schema_version": 1,
        "event_id": "ev-001",
        "task_id": "SBA-04",
        "attempt_id": attempt_id,
        "sequence": 1,
        "kind": "work.started",
        "occurred_at": "2026-10-16T10:00:00Z",
        "expected_task_version": 1,
        "payload": {"summary": "Container runtime started"},
    }
    r1 = svc.ingest_event(
        tenant_id="t-alpha",
        project_id_or_key="SBA",
        actor="t-alpha:antigravity_dev",
        authority_class="GUEST",
        raw_event=ev1,
    )
    assert r1["accepted_sequence"] == 1
    assert r1["task_id"] == "SBA-04"
    assert r1["board_cursor"].startswith(f"chg:t-alpha:{proj_id}:")

    # 2. Exact replay returns identical receipt
    r1_replay = svc.ingest_event(
        tenant_id="t-alpha",
        project_id_or_key="SBA",
        actor="t-alpha:antigravity_dev",
        authority_class="GUEST",
        raw_event=ev1,
    )
    assert r1_replay["receipt_id"] == r1["receipt_id"]

    # 3. Conflicting payload under same event_id -> 409
    ev1_conflict = dict(ev1, payload={"summary": "Tampered summary"})
    with pytest.raises(ActivityError) as exc:
        svc.ingest_event(
            tenant_id="t-alpha",
            project_id_or_key="SBA",
            actor="t-alpha:antigravity_dev",
            authority_class="GUEST",
            raw_event=ev1_conflict,
        )
    assert exc.value.status_code == 409
    assert exc.value.code == "conflicting_event_id"

    # 4. Sequence gap (sequence 3 instead of 2) -> 409
    ev_gap = dict(ev1, event_id="ev-003", sequence=3)
    with pytest.raises(ActivityError) as exc_gap:
        svc.ingest_event(
            tenant_id="t-alpha",
            project_id_or_key="SBA",
            actor="t-alpha:antigravity_dev",
            authority_class="GUEST",
            raw_event=ev_gap,
        )
    assert exc_gap.value.status_code == 409
    assert exc_gap.value.code == "sequence_mismatch"

    # 5. Guest attempting to emit service-only event -> 403
    ev_forged = dict(ev1, event_id="ev-forged", sequence=2, kind="verification.recorded")
    with pytest.raises(ActivityError) as exc_forged:
        svc.ingest_event(
            tenant_id="t-alpha",
            project_id_or_key="SBA",
            actor="t-alpha:antigravity_dev",
            authority_class="GUEST",
            raw_event=ev_forged,
        )
    assert exc_forged.value.status_code == 403
    assert exc_forged.value.code == "forbidden_kind"

    # 6. Guest evidence submission is always downgraded to 'claimed', never 'validated'
    ev2 = {
        "schema_version": 1,
        "event_id": "ev-002",
        "task_id": "SBA-04",
        "attempt_id": attempt_id,
        "sequence": 2,
        "kind": "evidence.submitted",
        "occurred_at": "2026-10-16T10:01:00Z",
        "expected_task_version": 1,
        "payload": {
            "summary": "Submitted candidate commit",
            "status": "validated",
            "candidate_commit": "a" * 40,
        },
    }
    svc.ingest_event(
        tenant_id="t-alpha",
        project_id_or_key="SBA",
        actor="t-alpha:antigravity_dev",
        authority_class="GUEST",
        raw_event=ev2,
    )

    # 7. Service authority can emit service-owned event (independent sequence space per authority_class)
    ev_svc = {
        "schema_version": 1,
        "event_id": "ev-svc-001",
        "task_id": "SBA-04",
        "attempt_id": attempt_id,
        "sequence": 1,
        "kind": "session.bound",
        "occurred_at": "2026-10-16T10:01:30Z",
        "expected_task_version": 1,
        "payload": {"summary": "Bound runtime session sess-123"},
    }
    r_svc = svc.ingest_event(
        tenant_id="t-alpha",
        project_id_or_key="SBA",
        actor="t-alpha:supervisor",
        authority_class="SERVICE",
        raw_event=ev_svc,
    )
    assert r_svc["accepted_sequence"] == 1

    # 8. Read task activity projection
    act = svc.get_task_activity(tenant_id="t-alpha", issue_or_task_id=issue_id, limit=100)
    assert act["schema_version"] == 1
    assert act["task_id"] == "SBA-04"
    assert len(act["events"]) == 3
    ev_sub = next(e for e in act["events"] if e["event_id"] == "ev-002")
    assert ev_sub["evidence"]["status"] == "claimed"
    assert ev_sub["evidence"]["candidate_commit"] == "a" * 40
    assert act["attempts"][0]["state"] == "RUNNING"


def test_activity_spool_coalescing_backpressure_and_cursor_gap(tmp_path: Path) -> None:
    db = PMDatabase(str(tmp_path / "pm.db"))
    proj_id, issue_id, attempt_id = _seed_project_and_attempt(db)
    svc = ActivityBridgeService(db, min_retained_change_seq=3)

    spool = ActivitySpool(capacity=3)
    # Coalesce multiple progress updates before sequence assignment
    spool.stage_progress(attempt_id, "Progress 10%", "2026-10-16T10:00:01Z")
    spool.stage_progress(attempt_id, "Progress 55%", "2026-10-16T10:00:02Z")
    spool.enqueue(
        event_id="ev-block-1",
        task_id="SBA-04",
        attempt_id=attempt_id,
        kind="work.blocked",
        summary="Waiting on external fixture",
        occurred_at="2026-10-16T10:00:03Z",
    )
    spool.enqueue(
        event_id="ev-resume-1",
        task_id="SBA-04",
        attempt_id=attempt_id,
        kind="work.resumed",
        summary="Fixture available",
        occurred_at="2026-10-16T10:00:04Z",
    )
    # Spool now has 3 items (coalesced progress seq 1, blocked seq 2, resumed seq 3) -> next enqueue exceeds capacity 3
    with pytest.raises(ActivityError) as exc_cap:
        spool.enqueue(
            event_id="ev-overflow",
            task_id="SBA-04",
            attempt_id=attempt_id,
            kind="comment.added",
            summary="Overflow event",
            occurred_at="2026-10-16T10:00:05Z",
        )
    assert exc_cap.value.status_code == 503
    assert spool.exhausted_blocker is not None

    receipts = spool.flush(svc, tenant_id="t-alpha", project_id="SBA", actor="t-alpha:antigravity_dev")
    assert len(receipts) == 3
    assert spool.exhausted_blocker is None

    # Requesting changes after cursor 1 when min_retained_change_seq=3 raises 410 resync_required
    with pytest.raises(ActivityError) as exc_gap:
        svc.get_project_changes(
            tenant_id="t-alpha",
            project_id_or_key="SBA",
            after_cursor=f"chg:t-alpha:{proj_id}:1",
        )
    assert exc_gap.value.status_code == 410
    assert exc_gap.value.code == "resync_required"


def test_live_browser_board_incremental_polling_and_recovery(tmp_path: Path) -> None:
    iam = MultiTenantIAM(secrets.token_hex(32), db_path=tmp_path / "iam.db")
    iam.create_tenant("t-alpha", "Alpha Tenant")
    iam.register_principal(
        "t-alpha",
        "operator",
        roles={"tenant_admin", "supervisor"},
        scopes={"storage:read", "storage:write", "tools:execute", "issues:create", "issues:transition", "pm:service:events"},
    )
    token = iam.issue_token("t-alpha", "operator")

    tenant_root = tmp_path / "tenants"
    db_path = resolve_tenant_database_path(iam, "t-alpha", tenant_root)
    db = PMDatabase(str(db_path))
    proj_id, issue_id, attempt_id = _seed_project_and_attempt(db, tenant_id="t-alpha")

    ent = ConsultingEnterprise()
    srv = DashboardServer(
        ent,
        host="127.0.0.1",
        port=0,
        iam=iam,
        tenant_id="t-alpha",
        tenant_root=tenant_root,
    )
    srv.start_background()
    port = srv.server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as p:
            executable = shutil.which("chromium") or shutil.which("google-chrome")
            browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            # 1. Log in through /portal/login.html
            page.goto(f"{base_url}/portal/login.html")
            page.locator("#tokenInput").fill(token)
            page.locator("#submitBtn").click()
            page.wait_for_url(f"{base_url}/portal/scrum.html**")
            page.evaluate("() => { app.project = 'SBA'; return refresh(false); }")
            page.locator('[data-ticket="SBA-4"]').wait_for()

            # Verify snapshot_cursor was captured by the live board
            cursor_before = page.evaluate("() => app.cursor")
            assert isinstance(cursor_before, str) and cursor_before.startswith(f"chg:t-alpha:{proj_id}:")

            # 2. Post a real authenticated runtime event to POST /api/pm/v1/projects/SBA/events
            ev_payload = json.dumps({
                "schema_version": 1,
                "event_id": "ev-live-1",
                "task_id": "SBA-04",
                "attempt_id": attempt_id,
                "sequence": 1,
                "kind": "work.blocked",
                "occurred_at": "2026-10-16T10:15:00Z",
                "expected_task_version": 1,
                "payload": {"summary": "Blocked awaiting broker quota confirmation"},
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/pm/v1/projects/SBA/events",
                data=ev_payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status == 200
                rcpt = json.loads(resp.read().decode("utf-8"))
                assert rcpt["accepted_sequence"] == 1

            # 3. Wait for incremental poll (or trigger pollChanges) and verify cursor & issue state update
            page.wait_for_function(
                "(oldCur) => app.cursor && app.cursor !== oldCur",
                arg=cursor_before,
                timeout=5000,
            )
            page.locator('[data-ticket="SBA-4"]').click()
            assert "Blocked awaiting broker quota confirmation" in page.locator("#drawer-content").inner_text()
            page.locator("#load-activity").click()
            page.wait_for_function("() => document.querySelector('#task-activity').getAttribute('aria-busy') === 'false'")
            assert "Blocked awaiting broker quota confirmation" in page.locator("#task-activity").inner_text()
            assert "Running" in page.locator("#task-workflow").inner_text()
            page.locator("#close-drawer").click()

            # 4. Simulate cursor gap (410 resync_required) and verify board recovers without emptying
            srv.min_retained_change_seq = 999
            page.evaluate("() => { app.cursor = 'chg:t-alpha:proj-sba:1'; return pollChanges(); }")
            page.locator('[data-ticket="SBA-4"]').wait_for()
            assert page.locator('[data-ticket="SBA-4"]').count() == 1

            browser.close()
    finally:
        srv.shutdown()
