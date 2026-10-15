"""
Platinum Lodge Core Domain Engine:
Multi-tenancy isolation, concurrent-safe inventory, immutable folio ledger,
and role-based security boundaries.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, Generator, List, Optional, Set
import uuid


class HotelSecurityError(Exception):
    """Base exception for hotel domain security errors."""
    pass


class TenantIsolationViolationError(HotelSecurityError):
    """Raised when an operation attempts cross-tenant or unauthorized property access."""
    pass


class InsufficientPermissionsError(HotelSecurityError):
    """Raised when an authenticated principal lacks required role/capabilities."""
    pass


class ConcurrencyConflictError(Exception):
    """Raised on version mismatch or concurrent allocation conflict."""
    pass


class FolioSettlementError(Exception):
    """Raised when attempting checkout with outstanding folio balance."""
    pass


@dataclass(frozen=True)
class TenantContext:
    user_id: str
    organization_id: str
    property_id: Optional[str] = None
    org_roles: Set[str] = field(default_factory=set)
    property_roles: Set[str] = field(default_factory=set)

    def is_org_admin(self) -> bool:
        return bool({"ORG_OWNER", "ORG_ADMIN"} & self.org_roles)

    def has_role(self, *roles: str) -> bool:
        if self.is_org_admin():
            return True
        allowed = set(roles)
        return bool(allowed & self.property_roles)


class HotelDatabase:
    """Manages SQLite / PostgreSQL connections and executes migrations with re-entrant transactions."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._lock = threading.RLock()
        self._local = threading.local()
        self._conn: Optional[sqlite3.Connection] = None
        if db_path == ":memory:":
            self._conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON;")
            self.apply_migrations(self._conn)

    def get_connection(self) -> sqlite3.Connection:
        if self._conn:
            return self._conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextlib.contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        with self._lock:
            conn = self.get_connection()
            depth = getattr(self._local, "tx_depth", 0)
            self._local.tx_depth = depth + 1

            if depth == 0:
                conn.execute("BEGIN IMMEDIATE;")
            else:
                conn.execute(f"SAVEPOINT sp_{depth};")

            try:
                yield conn
                if depth == 0:
                    conn.commit()
                else:
                    conn.execute(f"RELEASE SAVEPOINT sp_{depth};")
            except Exception:
                if depth == 0:
                    conn.rollback()
                else:
                    conn.execute(f"ROLLBACK TO SAVEPOINT sp_{depth};")
                raise
            finally:
                self._local.tx_depth -= 1

    def apply_migrations(self, conn: sqlite3.Connection) -> None:
        migration_file = Path(__file__).parent / "migrations" / "001_initial_multitenant_schema.sql"
        if migration_file.exists():
            sql = migration_file.read_text(encoding="utf-8")
        else:
            alt_path = Path("/home/acinonyx/Desktop/MAS/projects/platinum-lodge/migrations/001_initial_multitenant_schema.sql")
            sql = alt_path.read_text(encoding="utf-8")
        conn.executescript(sql)


class HotelService:
    """High-level service orchestrating multi-property hotel operations with tenancy guards."""

    def __init__(self, db: HotelDatabase) -> None:
        self.db = db

    # ---------------------------------------------------------
    # Tenancy & Context Guards
    # ---------------------------------------------------------
    def resolve_context(
        self,
        user_id: str,
        organization_id: str,
        property_id: Optional[str] = None,
    ) -> TenantContext:
        """Resolves authenticated principal memberships and constructs a validated TenantContext."""
        with self.db.transaction() as conn:
            user_row = conn.execute(
                "SELECT * FROM users WHERE id = ? AND status = 'ACTIVE';", (user_id,)
            ).fetchone()
            if not user_row:
                raise InsufficientPermissionsError(f"User '{user_id}' does not exist or is inactive.")

            # Fetch org-level memberships
            org_memberships = conn.execute(
                "SELECT role FROM memberships WHERE user_id = ? AND organization_id = ? AND property_id IS NULL AND status = 'ACTIVE';",
                (user_id, organization_id),
            ).fetchall()
            org_roles = {row["role"] for row in org_memberships}

            # Fetch property-level memberships if property_id provided
            prop_roles: Set[str] = set()
            if property_id:
                prop_row = conn.execute(
                    "SELECT organization_id FROM properties WHERE id = ?;", (property_id,)
                ).fetchone()
                if not prop_row:
                    raise TenantIsolationViolationError(f"Property '{property_id}' not found.")
                if prop_row["organization_id"] != organization_id:
                    raise TenantIsolationViolationError(
                        f"Property '{property_id}' does not belong to organization '{organization_id}'."
                    )

                prop_memberships = conn.execute(
                    "SELECT role FROM memberships WHERE user_id = ? AND organization_id = ? AND property_id = ? AND status = 'ACTIVE';",
                    (user_id, organization_id, property_id),
                ).fetchall()
                prop_roles = {row["role"] for row in prop_memberships}

                # If user has no property role and is not org admin, deny access
                if not prop_roles and not ({"ORG_OWNER", "ORG_ADMIN"} & org_roles):
                    raise TenantIsolationViolationError(
                        f"User '{user_id}' has no active membership in property '{property_id}'."
                    )
            else:
                # Org-level access requires at least one org membership or property membership
                if not org_roles:
                    any_prop = conn.execute(
                        "SELECT 1 FROM memberships WHERE user_id = ? AND organization_id = ? AND status = 'ACTIVE' LIMIT 1;",
                        (user_id, organization_id),
                    ).fetchone()
                    if not any_prop:
                        raise TenantIsolationViolationError(
                            f"User '{user_id}' has no membership in organization '{organization_id}'."
                        )

            return TenantContext(
                user_id=user_id,
                organization_id=organization_id,
                property_id=property_id,
                org_roles=org_roles,
                property_roles=prop_roles,
            )

    def _assert_property_scope(self, ctx: TenantContext, property_id: str) -> None:
        """Enforces that property belongs to context's organization, and user has property authority."""
        with self.db.transaction() as conn:
            prop = conn.execute("SELECT organization_id FROM properties WHERE id = ?;", (property_id,)).fetchone()
            if not prop:
                raise TenantIsolationViolationError(f"Property '{property_id}' not found.")
            if prop["organization_id"] != ctx.organization_id:
                raise TenantIsolationViolationError(
                    f"Cross-organization property access denied: property belongs to '{prop['organization_id']}', caller from '{ctx.organization_id}'."
                )

        if ctx.property_id and ctx.property_id != property_id and not ctx.is_org_admin():
            raise TenantIsolationViolationError(
                f"Tenant context property '{ctx.property_id}' does not match target property '{property_id}'."
            )

    # ---------------------------------------------------------
    # Reservations & Concurrency Protection
    # ---------------------------------------------------------
    def check_availability(
        self,
        ctx: TenantContext,
        property_id: str,
        room_type_id: str,
        arrival_date: str,
        departure_date: str,
    ) -> List[Dict[str, Any]]:
        """Finds rooms of room_type_id not occupied or blocked during date range."""
        self._assert_property_scope(ctx, property_id)
        with self.db.transaction() as conn:
            query = """
                SELECT r.* FROM rooms r
                WHERE r.property_id = ? AND r.room_type_id = ?
                  AND r.readiness_status != 'OUT_OF_SERVICE'
                  AND r.id NOT IN (
                      -- Occupied by active reservation
                      SELECT res.room_id FROM reservations res
                      WHERE res.property_id = ?
                        AND res.room_id IS NOT NULL
                        AND res.status IN ('CONFIRMED', 'CHECKED_IN')
                        AND NOT (res.departure_date <= ? OR res.arrival_date >= ?)
                  )
                  AND r.id NOT IN (
                      -- Blocked by active maintenance
                      SELECT mb.room_id FROM maintenance_blocks mb
                      WHERE mb.property_id = ?
                        AND mb.active = 1
                        AND NOT (mb.end_date <= ? OR mb.start_date >= ?)
                  );
            """
            rows = conn.execute(
                query,
                (
                    property_id,
                    room_type_id,
                    property_id,
                    arrival_date,
                    departure_date,
                    property_id,
                    arrival_date,
                    departure_date,
                ),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_reservation(
        self,
        ctx: TenantContext,
        property_id: str,
        room_type_id: str,
        rate_plan_id: str,
        guest_name: str,
        guest_email: str,
        arrival_date: str,
        departure_date: str,
        rate_cents: int,
        room_id: Optional[str] = None,
        adults: int = 1,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a reservation with atomic availability check and idempotency deduplication."""
        self._assert_property_scope(ctx, property_id)
        if not ctx.has_role("FRONT_DESK", "GENERAL_MANAGER"):
            raise InsufficientPermissionsError("Front desk or manager role required to create reservations.")

        with self.db.transaction() as conn:
            if idempotency_key:
                existing = conn.execute(
                    "SELECT * FROM reservations WHERE idempotency_key = ? AND property_id = ?;",
                    (idempotency_key, property_id),
                ).fetchone()
                if existing:
                    return dict(existing)

            available_rooms = self.check_availability(
                ctx, property_id, room_type_id, arrival_date, departure_date
            )
            if not available_rooms:
                raise ConcurrencyConflictError(
                    f"No available rooms of type '{room_type_id}' for dates {arrival_date} to {departure_date}."
                )

            selected_room_id = room_id or available_rooms[0]["id"]

            if not any(r["id"] == selected_room_id for r in available_rooms):
                raise ConcurrencyConflictError(
                    f"Room '{selected_room_id}' is already booked or blocked for the requested dates."
                )

            res_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            conn.execute(
                """
                INSERT INTO reservations (
                    id, organization_id, property_id, guest_name, guest_email,
                    room_id, room_type_id, rate_plan_id, arrival_date, departure_date,
                    adults, rate_cents, deposit_required_cents, deposit_paid_cents,
                    status, version, idempotency_key, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 'CONFIRMED', 1, ?, ?, ?);
                """,
                (
                    res_id,
                    ctx.organization_id,
                    property_id,
                    guest_name,
                    guest_email,
                    selected_room_id,
                    room_type_id,
                    rate_plan_id,
                    arrival_date,
                    departure_date,
                    adults,
                    rate_cents,
                    idempotency_key,
                    now_iso,
                    now_iso,
                ),
            )

            folio_id = str(uuid.uuid4())
            folio_num = f"FOL-{now_iso[:10].replace('-', '')}-{res_id[:6].upper()}"
            conn.execute(
                """
                INSERT INTO folios (id, organization_id, property_id, reservation_id, folio_number, status, balance_cents, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'OPEN', 0, ?, ?);
                """,
                (folio_id, ctx.organization_id, property_id, res_id, folio_num, now_iso, now_iso),
            )

            self._record_audit(
                conn,
                ctx,
                action="RESERVATION_CREATED",
                resource_type="reservations",
                resource_id=res_id,
                details={"guest": guest_name, "room_id": selected_room_id, "dates": f"{arrival_date}..{departure_date}"},
            )

            row = conn.execute("SELECT * FROM reservations WHERE id = ?;", (res_id,)).fetchone()
            return dict(row)

    def amend_reservation(
        self,
        ctx: TenantContext,
        reservation_id: str,
        expected_version: int,
        new_arrival_date: Optional[str] = None,
        new_departure_date: Optional[str] = None,
        new_room_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Amends reservation dates/room with strict optimistic concurrency control."""
        with self.db.transaction() as conn:
            res = conn.execute(
                "SELECT * FROM reservations WHERE id = ? AND organization_id = ?;",
                (reservation_id, ctx.organization_id),
            ).fetchone()
            if not res:
                raise TenantIsolationViolationError(f"Reservation '{reservation_id}' not found.")

            self._assert_property_scope(ctx, res["property_id"])

            if res["version"] != expected_version:
                raise ConcurrencyConflictError(
                    f"Optimistic lock conflict: reservation version is {res['version']}, expected {expected_version}."
                )

            target_arrival = new_arrival_date or res["arrival_date"]
            target_departure = new_departure_date or res["departure_date"]
            target_room = new_room_id or res["room_id"]

            avail_rooms = self.check_availability(
                ctx, res["property_id"], res["room_type_id"], target_arrival, target_departure
            )
            if target_room != res["room_id"] and not any(r["id"] == target_room for r in avail_rooms):
                raise ConcurrencyConflictError(f"Target room '{target_room}' is not available.")

            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            conn.execute(
                """
                UPDATE reservations
                SET arrival_date = ?, departure_date = ?, room_id = ?, version = version + 1, updated_at = ?
                WHERE id = ? AND version = ?;
                """,
                (target_arrival, target_departure, target_room, now_iso, reservation_id, expected_version),
            )

            self._record_audit(
                conn,
                ctx,
                action="RESERVATION_AMENDED",
                resource_type="reservations",
                resource_id=reservation_id,
                details={"new_version": expected_version + 1, "dates": f"{target_arrival}..{target_departure}"},
            )

            updated = conn.execute("SELECT * FROM reservations WHERE id = ?;", (reservation_id,)).fetchone()
            return dict(updated)

    def check_in(self, ctx: TenantContext, reservation_id: str) -> Dict[str, Any]:
        """Performs atomic check-in: verifies room clean/inspected status and creates stay record."""
        with self.db.transaction() as conn:
            res = conn.execute(
                "SELECT * FROM reservations WHERE id = ? AND organization_id = ?;",
                (reservation_id, ctx.organization_id),
            ).fetchone()
            if not res:
                raise TenantIsolationViolationError(f"Reservation '{reservation_id}' not found.")

            self._assert_property_scope(ctx, res["property_id"])
            if not ctx.has_role("FRONT_DESK", "GENERAL_MANAGER"):
                raise InsufficientPermissionsError("Front desk or manager role required for check-in.")

            if res["status"] != "CONFIRMED":
                raise ValueError(f"Cannot check in reservation with status '{res['status']}'.")

            room = conn.execute("SELECT * FROM rooms WHERE id = ?;", (res["room_id"],)).fetchone()
            if room["cleaning_status"] not in ("CLEAN", "INSPECTED") or room["readiness_status"] != "READY_FOR_CHECKIN":
                raise ValueError(
                    f"Room '{room['number']}' is not ready for check-in (cleaning: {room['cleaning_status']}, readiness: {room['readiness_status']})."
                )

            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            stay_id = str(uuid.uuid4())

            conn.execute(
                """
                INSERT INTO stays (id, organization_id, property_id, reservation_id, room_id, checked_in_at, checked_in_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (stay_id, ctx.organization_id, res["property_id"], reservation_id, res["room_id"], now_iso, ctx.user_id, now_iso, now_iso),
            )

            conn.execute(
                "UPDATE reservations SET status = 'CHECKED_IN', updated_at = ? WHERE id = ?;",
                (now_iso, reservation_id),
            )

            self._record_audit(
                conn,
                ctx,
                action="GUEST_CHECKED_IN",
                resource_type="reservations",
                resource_id=reservation_id,
                details={"stay_id": stay_id, "room": room["number"]},
            )

            return {"stay_id": stay_id, "reservation_id": reservation_id, "status": "CHECKED_IN"}

    def check_out(self, ctx: TenantContext, reservation_id: str) -> Dict[str, Any]:
        """Performs check-out: enforces zero folio balance and marks room DIRTY."""
        with self.db.transaction() as conn:
            res = conn.execute(
                "SELECT * FROM reservations WHERE id = ? AND organization_id = ?;",
                (reservation_id, ctx.organization_id),
            ).fetchone()
            if not res:
                raise TenantIsolationViolationError(f"Reservation '{reservation_id}' not found.")

            self._assert_property_scope(ctx, res["property_id"])

            folio = conn.execute(
                "SELECT * FROM folios WHERE reservation_id = ? AND status = 'OPEN';",
                (reservation_id,),
            ).fetchone()
            if folio and folio["balance_cents"] != 0:
                raise FolioSettlementError(
                    f"Cannot check out: folio balance is {folio['balance_cents']} cents (must be 0)."
                )

            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            conn.execute(
                "UPDATE stays SET checked_out_at = ?, checked_out_by = ?, updated_at = ? WHERE reservation_id = ?;",
                (now_iso, ctx.user_id, now_iso, reservation_id),
            )
            conn.execute(
                "UPDATE reservations SET status = 'CHECKED_OUT', updated_at = ? WHERE id = ?;",
                (now_iso, reservation_id),
            )
            if folio:
                conn.execute("UPDATE folios SET status = 'SETTLED', updated_at = ? WHERE id = ?;", (now_iso, folio["id"]))

            conn.execute(
                "UPDATE rooms SET cleaning_status = 'DIRTY', readiness_status = 'BLOCKED', updated_at = ? WHERE id = ?;",
                (now_iso, res["room_id"]),
            )

            self._record_audit(
                conn,
                ctx,
                action="GUEST_CHECKED_OUT",
                resource_type="reservations",
                resource_id=reservation_id,
                details={"room_id": res["room_id"], "folio_settled": True},
            )

            return {"reservation_id": reservation_id, "status": "CHECKED_OUT"}

    # ---------------------------------------------------------
    # Folio Ledger (Immutable Double-Entry)
    # ---------------------------------------------------------
    def post_charge(
        self,
        ctx: TenantContext,
        folio_id: str,
        department: str,
        description: str,
        amount_cents: int,
        business_date: str,
    ) -> Dict[str, Any]:
        """Appends an immutable charge debit and updates folio balance."""
        with self.db.transaction() as conn:
            folio = conn.execute("SELECT * FROM folios WHERE id = ?;", (folio_id,)).fetchone()
            if not folio:
                raise TenantIsolationViolationError(f"Folio '{folio_id}' not found.")
            if folio["organization_id"] != ctx.organization_id:
                raise TenantIsolationViolationError("Cross-tenant folio access denied.")
            self._assert_property_scope(ctx, folio["property_id"])

            charge_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            conn.execute(
                """
                INSERT INTO charges (id, organization_id, property_id, folio_id, department, description, amount_cents, currency, business_date, posted_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'USD', ?, ?, ?);
                """,
                (charge_id, ctx.organization_id, folio["property_id"], folio_id, department, description, amount_cents, business_date, ctx.user_id, now_iso),
            )

            conn.execute(
                "UPDATE folios SET balance_cents = balance_cents + ?, updated_at = ? WHERE id = ?;",
                (amount_cents, now_iso, folio_id),
            )

            return {"charge_id": charge_id, "amount_cents": amount_cents}

    def record_payment(
        self,
        ctx: TenantContext,
        folio_id: str,
        amount_cents: int,
        method: str,
        idempotency_key: str,
        business_date: str,
        reference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Records an immutable credit payment with idempotency protection and updates folio balance."""
        with self.db.transaction() as conn:
            existing = conn.execute(
                "SELECT * FROM payments WHERE idempotency_key = ?;", (idempotency_key,)
            ).fetchone()
            if existing:
                return dict(existing)

            folio = conn.execute("SELECT * FROM folios WHERE id = ?;", (folio_id,)).fetchone()
            if not folio:
                raise TenantIsolationViolationError(f"Folio '{folio_id}' not found.")
            if folio["organization_id"] != ctx.organization_id:
                raise TenantIsolationViolationError("Cross-tenant folio access denied.")
            self._assert_property_scope(ctx, folio["property_id"])

            payment_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            conn.execute(
                """
                INSERT INTO payments (id, organization_id, property_id, folio_id, amount_cents, currency, method, reference, idempotency_key, status, business_date, captured_by, created_at)
                VALUES (?, ?, ?, ?, ?, 'USD', ?, ?, ?, 'CAPTURED', ?, ?, ?);
                """,
                (payment_id, ctx.organization_id, folio["property_id"], folio_id, amount_cents, method, reference, idempotency_key, business_date, ctx.user_id, now_iso),
            )

            conn.execute(
                "UPDATE folios SET balance_cents = balance_cents - ?, updated_at = ? WHERE id = ?;",
                (amount_cents, now_iso, folio_id),
            )

            row = conn.execute("SELECT * FROM payments WHERE id = ?;", (payment_id,)).fetchone()
            return dict(row)

    # ---------------------------------------------------------
    # Housekeeping & Room Inspections
    # ---------------------------------------------------------
    def update_room_cleaning(
        self,
        ctx: TenantContext,
        room_id: str,
        cleaning_status: str,
    ) -> Dict[str, Any]:
        """Allows housekeeper to update cleaning state."""
        with self.db.transaction() as conn:
            room = conn.execute("SELECT * FROM rooms WHERE id = ?;", (room_id,)).fetchone()
            if not room:
                raise TenantIsolationViolationError(f"Room '{room_id}' not found.")
            if room["organization_id"] != ctx.organization_id:
                raise TenantIsolationViolationError("Cross-tenant room access denied.")
            self._assert_property_scope(ctx, room["property_id"])

            if not ctx.has_role("HOUSEKEEPER", "HOUSEKEEPING_LEAD", "GENERAL_MANAGER"):
                raise InsufficientPermissionsError("Housekeeping role required.")

            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            readiness = "READY_FOR_CHECKIN" if cleaning_status == "INSPECTED" else "BLOCKED"

            conn.execute(
                "UPDATE rooms SET cleaning_status = ?, readiness_status = ?, updated_at = ? WHERE id = ?;",
                (cleaning_status, readiness, now_iso, room_id),
            )

            self._record_audit(
                conn,
                ctx,
                action="ROOM_CLEANING_UPDATED",
                resource_type="rooms",
                resource_id=room_id,
                details={"cleaning_status": cleaning_status, "readiness": readiness},
            )

            return {"room_id": room_id, "cleaning_status": cleaning_status, "readiness_status": readiness}

    # ---------------------------------------------------------
    # Night Audit (Daily Business Close)
    # ---------------------------------------------------------
    def run_night_audit(
        self,
        ctx: TenantContext,
        property_id: str,
        for_business_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs the idempotent daily close, aggregates room charges, and advances business date."""
        self._assert_property_scope(ctx, property_id)
        if not ctx.has_role("NIGHT_AUDITOR", "GENERAL_MANAGER"):
            raise InsufficientPermissionsError("Night auditor or manager role required.")

        with self.db.transaction() as conn:
            prop = conn.execute("SELECT * FROM properties WHERE id = ?;", (property_id,)).fetchone()
            target_date = for_business_date or prop["current_business_date"]

            existing = conn.execute(
                "SELECT * FROM night_audits WHERE property_id = ? AND business_date = ?;",
                (property_id, target_date),
            ).fetchone()
            if existing:
                return {
                    "audit_id": existing["id"],
                    "business_date": existing["business_date"],
                    "next_business_date": prop["current_business_date"],
                    "total_revenue_cents": existing["total_room_revenue_cents"],
                    "total_payments_cents": existing["total_payments_cents"],
                }

            charges_sum = conn.execute(
                "SELECT COALESCE(SUM(amount_cents), 0) AS total FROM charges WHERE property_id = ? AND business_date = ?;",
                (property_id, target_date),
            ).fetchone()["total"]

            payments_sum = conn.execute(
                "SELECT COALESCE(SUM(amount_cents), 0) AS total FROM payments WHERE property_id = ? AND business_date = ?;",
                (property_id, target_date),
            ).fetchone()["total"]

            audit_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            conn.execute(
                """
                INSERT INTO night_audits (id, organization_id, property_id, business_date, closed_at, closed_by, total_room_revenue_cents, total_tax_cents, total_payments_cents, balanced)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, 1);
                """,
                (audit_id, ctx.organization_id, property_id, target_date, now_iso, ctx.user_id, charges_sum, payments_sum),
            )

            d = date.fromisoformat(target_date) + timedelta(days=1)
            next_date = d.isoformat()
            conn.execute(
                "UPDATE properties SET current_business_date = ?, updated_at = ? WHERE id = ?;",
                (next_date, now_iso, property_id),
            )

            self._record_audit(
                conn,
                ctx,
                action="NIGHT_AUDIT_COMPLETED",
                resource_type="night_audits",
                resource_id=audit_id,
                details={"business_date": target_date, "next_date": next_date, "revenue": charges_sum},
            )

            return {
                "audit_id": audit_id,
                "business_date": target_date,
                "next_business_date": next_date,
                "total_revenue_cents": charges_sum,
                "total_payments_cents": payments_sum,
            }

    # ---------------------------------------------------------
    # Internal Audit Logger
    # ---------------------------------------------------------
    def _record_audit(
        self,
        conn: sqlite3.Connection,
        ctx: TenantContext,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Dict[str, Any],
    ) -> None:
        log_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        conn.execute(
            """
            INSERT INTO audit_logs (id, organization_id, property_id, actor_id, action, resource_type, resource_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (log_id, ctx.organization_id, ctx.property_id, ctx.user_id, action, resource_type, resource_id, json.dumps(details), now_iso),
        )
