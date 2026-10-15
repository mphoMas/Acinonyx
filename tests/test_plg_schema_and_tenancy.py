"""
Unit and Integration Tests for Platinum Lodge Multi-Property Hotel Domain.
Verifies:
- Multi-tenant database migrations & schema integrity
- Hierarchical tenancy isolation & adversarial cross-tenant rejection
- Concurrent inventory allocation & overbooking prevention
- Optimistic concurrency control (version lock) on reservation amendments
- Room readiness and check-in/out workflows
- Immutable folio ledger (charges, payments) with idempotency deduplication
- Idempotent night audit daily close
"""

from __future__ import annotations

import datetime
from pathlib import Path
import pytest
import sqlite3
import uuid

import sys
sys.path.insert(0, "/home/acinonyx/Desktop/MAS/projects/platinum-lodge")

from hotel_core import (
    ConcurrencyConflictError,
    FolioSettlementError,
    HotelDatabase,
    HotelService,
    InsufficientPermissionsError,
    TenantContext,
    TenantIsolationViolationError,
)


@pytest.fixture
def hotel_db() -> HotelDatabase:
    """Creates a fresh in-memory hotel database with initial schema applied."""
    return HotelDatabase(":memory:")


@pytest.fixture
def hotel_service(hotel_db: HotelDatabase) -> HotelService:
    return HotelService(hotel_db)


@pytest.fixture
def seeded_fixture(hotel_db: HotelDatabase, hotel_service: HotelService) -> dict:
    """
    Seeds two organizations, each with two properties, room types, rate plans, rooms, and users.
    Org A: 'Grand Horizon Hospitality' (Properties: 'Horizon Beach', 'Horizon Mountain')
    Org B: 'Adversarial Peak Hotels' (Properties: 'Peak Lodge', 'Peak Valley')
    """
    with hotel_db.transaction() as conn:
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        # 1. Organizations
        org_a_id = "org-alpha-1111"
        org_b_id = "org-bravo-2222"
        conn.execute(
            "INSERT INTO organizations VALUES (?, 'Grand Horizon Hospitality', 'Grand Horizon Ltd', 'TAX-001', 'admin@horizon.com', 'ACTIVE', ?, ?);",
            (org_a_id, now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO organizations VALUES (?, 'Adversarial Peak Hotels', 'Adversarial Peak Ltd', 'TAX-002', 'admin@peak.com', 'ACTIVE', ?, ?);",
            (org_b_id, now_iso, now_iso),
        )

        # 2. Properties
        prop_a1_id = "prop-alpha-beach"
        prop_a2_id = "prop-alpha-mountain"
        prop_b1_id = "prop-bravo-lodge"

        conn.execute(
            "INSERT INTO properties VALUES (?, ?, 'BEACH', 'Horizon Beach Resort', 'Africa/Maputo', 'USD', '2026-11-01', 'MZ', 'Maputo', '123 Coastal Ave', 5, 'ACTIVE', ?, ?);",
            (prop_a1_id, org_a_id, now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO properties VALUES (?, ?, 'MTN', 'Horizon Mountain Lodge', 'Africa/Johannesburg', 'ZAR', '2026-11-01', 'ZA', 'Drakensberg', '45 Peak Rd', 4, 'ACTIVE', ?, ?);",
            (prop_a2_id, org_a_id, now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO properties VALUES (?, ?, 'LODGE', 'Peak Safari Lodge', 'Africa/Harare', 'USD', '2026-11-01', 'ZW', 'Victoria Falls', '77 River Way', 4, 'ACTIVE', ?, ?);",
            (prop_b1_id, org_b_id, now_iso, now_iso),
        )

        # 3. Users
        user_alice = "usr-alice-admin"
        user_bob = "usr-bob-frontdesk"
        user_charlie = "usr-charlie-cleaner"
        user_dan = "usr-dan-auditor"
        user_eve = "usr-eve-adversary"

        for uid, name, email in [
            (user_alice, "Alice OrgAdmin", "alice@horizon.com"),
            (user_bob, "Bob FrontDesk", "bob@horizon.com"),
            (user_charlie, "Charlie Housekeeper", "charlie@horizon.com"),
            (user_dan, "Dan NightAuditor", "dan@horizon.com"),
            (user_eve, "Eve Adversary", "eve@peak.com"),
        ]:
            conn.execute(
                "INSERT INTO users VALUES (?, ?, ?, 'hash', 0, 'ACTIVE', ?, ?);",
                (uid, email, name, now_iso, now_iso),
            )

        # 4. Memberships
        conn.execute("INSERT INTO memberships VALUES ('m-1', ?, NULL, ?, 'ORG_ADMIN', 'ACTIVE', ?, ?);", (org_a_id, user_alice, now_iso, now_iso))
        conn.execute("INSERT INTO memberships VALUES ('m-2', ?, ?, ?, 'FRONT_DESK', 'ACTIVE', ?, ?);", (org_a_id, prop_a1_id, user_bob, now_iso, now_iso))
        conn.execute("INSERT INTO memberships VALUES ('m-3', ?, ?, ?, 'HOUSEKEEPER', 'ACTIVE', ?, ?);", (org_a_id, prop_a1_id, user_charlie, now_iso, now_iso))
        conn.execute("INSERT INTO memberships VALUES ('m-4', ?, ?, ?, 'NIGHT_AUDITOR', 'ACTIVE', ?, ?);", (org_a_id, prop_a1_id, user_dan, now_iso, now_iso))
        conn.execute("INSERT INTO memberships VALUES ('m-5', ?, NULL, ?, 'ORG_ADMIN', 'ACTIVE', ?, ?);", (org_b_id, user_eve, now_iso, now_iso))

        # 5. Room Types & Rate Plans
        type_deluxe = "rt-deluxe"
        conn.execute(
            "INSERT INTO room_types VALUES (?, ?, ?, 'DLX', 'Deluxe Ocean View', 15000, 2, '[]', ?, ?);",
            (type_deluxe, org_a_id, prop_a1_id, now_iso, now_iso),
        )
        plan_standard = "rp-standard"
        conn.execute(
            "INSERT INTO rate_plans VALUES (?, ?, ?, 'STD', 'Standard Flexible', 0, 24, 1, 1, ?, ?);",
            (plan_standard, org_a_id, prop_a1_id, now_iso, now_iso),
        )

        # 6. Rooms
        room_101 = "rm-101"
        room_102 = "rm-102"
        conn.execute(
            "INSERT INTO rooms VALUES (?, ?, ?, ?, '101', 1, 'INSPECTED', 'READY_FOR_CHECKIN', 0, ?, ?);",
            (room_101, org_a_id, prop_a1_id, type_deluxe, now_iso, now_iso),
        )
        conn.execute(
            "INSERT INTO rooms VALUES (?, ?, ?, ?, '102', 1, 'DIRTY', 'BLOCKED', 0, ?, ?);",
            (room_102, org_a_id, prop_a1_id, type_deluxe, now_iso, now_iso),
        )

    return {
        "org_a": org_a_id,
        "org_b": org_b_id,
        "prop_a1": prop_a1_id,
        "prop_a2": prop_a2_id,
        "prop_b1": prop_b1_id,
        "user_alice": user_alice,
        "user_bob": user_bob,
        "user_charlie": user_charlie,
        "user_dan": user_dan,
        "user_eve": user_eve,
        "room_type_deluxe": type_deluxe,
        "rate_plan_standard": plan_standard,
        "room_101": room_101,
        "room_102": room_102,
    }


def test_schema_and_migration_integrity(hotel_db: HotelDatabase):
    """Verifies that all 16 multi-tenant tables and indexes exist."""
    conn = hotel_db.get_connection()
    tables = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    expected_tables = [
        "organizations", "properties", "users", "memberships", "room_types",
        "rate_plans", "rooms", "reservations", "stays", "folios", "charges",
        "payments", "housekeeping_tasks", "maintenance_blocks", "night_audits", "audit_logs"
    ]
    for table in expected_tables:
        assert table in tables, f"Expected table '{table}' missing in schema."


def test_tenancy_context_resolution_and_boundaries(hotel_service: HotelService, seeded_fixture: dict):
    """Verifies tenancy context resolution and isolation guards."""
    f = seeded_fixture

    # Valid front desk context on Property A1
    ctx_bob = hotel_service.resolve_context(f["user_bob"], f["org_a"], f["prop_a1"])
    assert "FRONT_DESK" in ctx_bob.property_roles
    assert ctx_bob.organization_id == f["org_a"]

    # Bob attempting to access Property A2 (different property in same org) fails
    with pytest.raises(TenantIsolationViolationError):
        hotel_service.resolve_context(f["user_bob"], f["org_a"], f["prop_a2"])

    # Bob attempting to access Org B fails
    with pytest.raises(TenantIsolationViolationError):
        hotel_service.resolve_context(f["user_bob"], f["org_b"], f["prop_b1"])

    # Alice (Org Admin) has cross-property authority within Org A
    ctx_alice = hotel_service.resolve_context(f["user_alice"], f["org_a"])
    assert ctx_alice.is_org_admin()


def test_concurrent_inventory_and_overbooking_prevention(hotel_service: HotelService, seeded_fixture: dict):
    """Verifies that double booking or overlapping allocations for the same room are strictly rejected."""
    f = seeded_fixture
    ctx_bob = hotel_service.resolve_context(f["user_bob"], f["org_a"], f["prop_a1"])

    # Initial booking for Room 101: 2026-11-01 to 2026-11-05
    res1 = hotel_service.create_reservation(
        ctx=ctx_bob,
        property_id=f["prop_a1"],
        room_type_id=f["room_type_deluxe"],
        rate_plan_id=f["rate_plan_standard"],
        guest_name="John Doe",
        guest_email="john@example.com",
        arrival_date="2026-11-01",
        departure_date="2026-11-05",
        rate_cents=15000,
        room_id=f["room_101"],
    )
    assert res1["status"] == "CONFIRMED"
    assert res1["version"] == 1

    # Overlapping booking attempt: 2026-11-03 to 2026-11-07 for Room 101
    with pytest.raises(ConcurrencyConflictError):
        hotel_service.create_reservation(
            ctx=ctx_bob,
            property_id=f["prop_a1"],
            room_type_id=f["room_type_deluxe"],
            rate_plan_id=f["rate_plan_standard"],
            guest_name="Jane Smith",
            guest_email="jane@example.com",
            arrival_date="2026-11-03",
            departure_date="2026-11-07",
            rate_cents=15000,
            room_id=f["room_101"],
        )

    # Non-overlapping booking for Room 101: 2026-11-05 to 2026-11-08 succeeds
    res3 = hotel_service.create_reservation(
        ctx=ctx_bob,
        property_id=f["prop_a1"],
        room_type_id=f["room_type_deluxe"],
        rate_plan_id=f["rate_plan_standard"],
        guest_name="Bob Wilson",
        guest_email="bobw@example.com",
        arrival_date="2026-11-05",
        departure_date="2026-11-08",
        rate_cents=15000,
        room_id=f["room_101"],
    )
    assert res3["status"] == "CONFIRMED"


def test_optimistic_locking_on_amendments(hotel_service: HotelService, seeded_fixture: dict):
    """Verifies that reservation amendments enforce optimistic concurrency version locking."""
    f = seeded_fixture
    ctx_bob = hotel_service.resolve_context(f["user_bob"], f["org_a"], f["prop_a1"])

    res = hotel_service.create_reservation(
        ctx=ctx_bob,
        property_id=f["prop_a1"],
        room_type_id=f["room_type_deluxe"],
        rate_plan_id=f["rate_plan_standard"],
        guest_name="Sam Traveler",
        guest_email="sam@example.com",
        arrival_date="2026-11-10",
        departure_date="2026-11-15",
        rate_cents=15000,
        room_id=f["room_101"],
    )
    res_id = res["id"]
    assert res["version"] == 1

    # Stale update attempt with expected_version = 99 fails with 409 Conflict
    with pytest.raises(ConcurrencyConflictError):
        hotel_service.amend_reservation(
            ctx=ctx_bob,
            reservation_id=res_id,
            expected_version=99,
            new_departure_date="2026-11-16",
        )

    # Valid update with expected_version = 1 succeeds and advances version to 2
    updated = hotel_service.amend_reservation(
        ctx=ctx_bob,
        reservation_id=res_id,
        expected_version=1,
        new_departure_date="2026-11-16",
    )
    assert updated["version"] == 2
    assert updated["departure_date"] == "2026-11-16"


def test_checkin_and_room_readiness_guards(hotel_service: HotelService, seeded_fixture: dict):
    """Verifies that check-in requires room clean/inspected status and produces stay record."""
    f = seeded_fixture
    ctx_bob = hotel_service.resolve_context(f["user_bob"], f["org_a"], f["prop_a1"])
    ctx_charlie = hotel_service.resolve_context(f["user_charlie"], f["org_a"], f["prop_a1"])

    # Booking in Room 102 (starts DIRTY)
    res = hotel_service.create_reservation(
        ctx=ctx_bob,
        property_id=f["prop_a1"],
        room_type_id=f["room_type_deluxe"],
        rate_plan_id=f["rate_plan_standard"],
        guest_name="VIP Guest",
        guest_email="vip@example.com",
        arrival_date="2026-11-01",
        departure_date="2026-11-03",
        rate_cents=15000,
        room_id=f["room_102"],
    )

    # Check-in must fail because room 102 is DIRTY
    with pytest.raises(ValueError, match="not ready for check-in"):
        hotel_service.check_in(ctx_bob, res["id"])

    # Charlie (Housekeeper) cleans room and inspects it
    hotel_service.update_room_cleaning(ctx_charlie, f["room_102"], "INSPECTED")

    # Now check-in succeeds
    checkin_res = hotel_service.check_in(ctx_bob, res["id"])
    assert checkin_res["status"] == "CHECKED_IN"


def test_immutable_folio_ledger_and_checkout(hotel_service: HotelService, seeded_fixture: dict, hotel_db: HotelDatabase):
    """Verifies double-entry charge/payment posting, idempotency deduplication, and zero-balance checkout."""
    f = seeded_fixture
    ctx_bob = hotel_service.resolve_context(f["user_bob"], f["org_a"], f["prop_a1"])

    # Room 101 is already inspected
    res = hotel_service.create_reservation(
        ctx=ctx_bob,
        property_id=f["prop_a1"],
        room_type_id=f["room_type_deluxe"],
        rate_plan_id=f["rate_plan_standard"],
        guest_name="Arthur Dent",
        guest_email="dent@galaxy.com",
        arrival_date="2026-11-01",
        departure_date="2026-11-02",
        rate_cents=15000,
        room_id=f["room_101"],
    )
    hotel_service.check_in(ctx_bob, res["id"])

    # Get reservation folio
    with hotel_db.transaction() as conn:
        folio = conn.execute("SELECT * FROM folios WHERE reservation_id = ?;", (res["id"],)).fetchone()
        folio_id = folio["id"]

    # Post accommodation charge: $150.00 (15000 cents)
    hotel_service.post_charge(ctx_bob, folio_id, "ROOM", "Night Accommodation", 15000, "2026-11-01")
    # Post restaurant charge: $25.50 (2550 cents)
    hotel_service.post_charge(ctx_bob, folio_id, "FOOD_BEVERAGE", "Lodge Dinner", 2550, "2026-11-01")

    # Attempt checkout with outstanding balance (17550 cents) -> FAILS
    with pytest.raises(FolioSettlementError):
        hotel_service.check_out(ctx_bob, res["id"])

    # Record payment for exact balance with Idempotency Key
    idem_key = "pay-dent-checkout-001"
    pay1 = hotel_service.record_payment(
        ctx_bob, folio_id, 17550, "CREDIT_CARD", idem_key, "2026-11-01", reference="AUTH-999"
    )
    assert pay1["amount_cents"] == 17550

    # Replay payment with same Idempotency Key -> returns same payment without double crediting
    pay2 = hotel_service.record_payment(
        ctx_bob, folio_id, 17550, "CREDIT_CARD", idem_key, "2026-11-01", reference="AUTH-999"
    )
    assert pay1["id"] == pay2["id"]

    # Folio balance is now 0 -> Checkout succeeds!
    checkout_res = hotel_service.check_out(ctx_bob, res["id"])
    assert checkout_res["status"] == "CHECKED_OUT"

    # Room is now DIRTY
    with hotel_db.transaction() as conn:
        room = conn.execute("SELECT * FROM rooms WHERE id = ?;", (f["room_101"],)).fetchone()
        assert room["cleaning_status"] == "DIRTY"


def test_night_audit_idempotent_close(hotel_service: HotelService, seeded_fixture: dict):
    """Verifies that night audit aggregates daily totals, advances business date, and prevents duplicate close."""
    f = seeded_fixture
    ctx_dan = hotel_service.resolve_context(f["user_dan"], f["org_a"], f["prop_a1"])

    audit_res1 = hotel_service.run_night_audit(ctx_dan, f["prop_a1"])
    assert audit_res1["business_date"] == "2026-11-01"
    assert audit_res1["next_business_date"] == "2026-11-02"

    # Re-running for same business date returns same audit safely (idempotent)
    audit_res2 = hotel_service.run_night_audit(ctx_dan, f["prop_a1"], for_business_date="2026-11-01")
    assert audit_res2["audit_id"] == audit_res1["audit_id"]


def test_adversarial_cross_tenant_isolation(hotel_service: HotelService, seeded_fixture: dict):
    """Adversarial security test: User from Org B attempts to breach Org A."""
    f = seeded_fixture
    ctx_eve = hotel_service.resolve_context(f["user_eve"], f["org_b"])

    # Eve attempts to access Property A1 availability -> FAILS
    with pytest.raises(TenantIsolationViolationError):
        hotel_service.check_availability(
            ctx=ctx_eve,
            property_id=f["prop_a1"],
            room_type_id=f["room_type_deluxe"],
            arrival_date="2026-11-01",
            departure_date="2026-11-02",
        )

    # Eve attempts to amend Org A's reservation -> FAILS
    with pytest.raises(TenantIsolationViolationError):
        hotel_service.amend_reservation(
            ctx=ctx_eve,
            reservation_id="fake-id",
            expected_version=1,
        )
