-- Platinum Lodge Multi-Property Hotel Management System
-- Migration 001: Initial Multi-Tenant Schema & Isolation Model
-- Compatible with PostgreSQL 16+ and SQLite 3.35+

-- 1. Organizations (Top-level legal entities / holding companies)
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    legal_name TEXT NOT NULL,
    tax_identifier TEXT,
    contact_email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'SUSPENDED', 'ARCHIVED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. Properties (Individual hotel properties belonging to an organization)
CREATE TABLE IF NOT EXISTS properties (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    currency TEXT NOT NULL DEFAULT 'USD',
    current_business_date TEXT NOT NULL,
    country_code TEXT NOT NULL,
    city TEXT NOT NULL,
    address TEXT NOT NULL,
    star_rating INTEGER CHECK(star_rating BETWEEN 1 AND 5),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'CLOSED_SEASONAL', 'MAINTENANCE', 'ARCHIVED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, code)
);

-- 3. Users (System principals)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    mfa_enabled INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'DEACTIVATED', 'LOCKED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 4. Memberships (Scoped access control: organization and property level)
CREATE TABLE IF NOT EXISTS memberships (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    property_id TEXT REFERENCES properties(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN (
        'ORG_OWNER', 'ORG_ADMIN', 
        'GENERAL_MANAGER', 'FRONT_DESK', 
        'NIGHT_AUDITOR', 'HOUSEKEEPING_LEAD', 
        'HOUSEKEEPER', 'MAINTENANCE', 'FINANCE'
    )),
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'INVITED', 'REVOKED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(organization_id, property_id, user_id, role)
);

-- 5. Room Types (Categories of accommodation per property)
CREATE TABLE IF NOT EXISTS room_types (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    base_rate_cents INTEGER NOT NULL CHECK(base_rate_cents >= 0),
    max_occupancy INTEGER NOT NULL CHECK(max_occupancy >= 1),
    amenities TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(property_id, code)
);

-- 6. Rate Plans (Pricing and cancellation policies)
CREATE TABLE IF NOT EXISTS rate_plans (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    deposit_required_pct INTEGER NOT NULL DEFAULT 0 CHECK(deposit_required_pct BETWEEN 0 AND 100),
    cancellation_hours INTEGER NOT NULL DEFAULT 24 CHECK(cancellation_hours >= 0),
    is_refundable INTEGER NOT NULL DEFAULT 1,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(property_id, code)
);

-- 7. Rooms (Physical inventory units)
CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_type_id TEXT NOT NULL REFERENCES room_types(id) ON DELETE RESTRICT,
    number TEXT NOT NULL,
    floor INTEGER NOT NULL DEFAULT 1,
    cleaning_status TEXT NOT NULL DEFAULT 'CLEAN' CHECK(cleaning_status IN ('DIRTY', 'CLEANING_IN_PROGRESS', 'CLEAN', 'INSPECTED')),
    readiness_status TEXT NOT NULL DEFAULT 'READY_FOR_CHECKIN' CHECK(readiness_status IN ('READY_FOR_CHECKIN', 'BLOCKED', 'OUT_OF_SERVICE', 'MAINTENANCE_REQUIRED')),
    is_smoking INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(property_id, number)
);

-- 8. Reservations (Stay bookings with optimistic concurrency protection)
CREATE TABLE IF NOT EXISTS reservations (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    guest_name TEXT NOT NULL,
    guest_email TEXT NOT NULL,
    guest_phone TEXT,
    guest_id_number TEXT,
    room_id TEXT REFERENCES rooms(id) ON DELETE RESTRICT,
    room_type_id TEXT NOT NULL REFERENCES room_types(id) ON DELETE RESTRICT,
    rate_plan_id TEXT NOT NULL REFERENCES rate_plans(id) ON DELETE RESTRICT,
    arrival_date TEXT NOT NULL, -- YYYY-MM-DD
    departure_date TEXT NOT NULL, -- YYYY-MM-DD
    adults INTEGER NOT NULL DEFAULT 1 CHECK(adults >= 1),
    rate_cents INTEGER NOT NULL CHECK(rate_cents >= 0),
    deposit_required_cents INTEGER NOT NULL DEFAULT 0 CHECK(deposit_required_cents >= 0),
    deposit_paid_cents INTEGER NOT NULL DEFAULT 0 CHECK(deposit_paid_cents >= 0),
    status TEXT NOT NULL DEFAULT 'CONFIRMED' CHECK(status IN ('CONFIRMED', 'CHECKED_IN', 'CHECKED_OUT', 'CANCELLED', 'NO_SHOW')),
    version INTEGER NOT NULL DEFAULT 1 CHECK(version >= 1), -- Optimistic lock
    idempotency_key TEXT UNIQUE,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 9. Stays (Operational in-house guest records)
CREATE TABLE IF NOT EXISTS stays (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    reservation_id TEXT NOT NULL UNIQUE REFERENCES reservations(id) ON DELETE RESTRICT,
    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE RESTRICT,
    checked_in_at TEXT NOT NULL,
    checked_in_by TEXT NOT NULL REFERENCES users(id),
    checked_out_at TEXT,
    checked_out_by TEXT REFERENCES users(id),
    keycard_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 10. Folios (Financial billing container per reservation / walk-in)
CREATE TABLE IF NOT EXISTS folios (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    reservation_id TEXT REFERENCES reservations(id) ON DELETE RESTRICT,
    folio_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'CLOSED', 'SETTLED')),
    balance_cents INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(property_id, folio_number)
);

-- 11. Charges (Immutable double-entry debits posted to a folio)
CREATE TABLE IF NOT EXISTS charges (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    folio_id TEXT NOT NULL REFERENCES folios(id) ON DELETE RESTRICT,
    department TEXT NOT NULL CHECK(department IN ('ROOM', 'TAX', 'FOOD_BEVERAGE', 'SPA', 'PARKING', 'MISC', 'REVERSAL')),
    description TEXT NOT NULL,
    amount_cents INTEGER NOT NULL, -- Negative for corrections/reversals
    currency TEXT NOT NULL,
    business_date TEXT NOT NULL,
    posted_by TEXT NOT NULL REFERENCES users(id),
    reversal_of_id TEXT REFERENCES charges(id),
    created_at TEXT NOT NULL
);

-- 12. Payments (Immutable credit records posted to a folio with idempotency)
CREATE TABLE IF NOT EXISTS payments (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    folio_id TEXT NOT NULL REFERENCES folios(id) ON DELETE RESTRICT,
    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
    currency TEXT NOT NULL,
    method TEXT NOT NULL CHECK(method IN ('CASH', 'CREDIT_CARD', 'DEBIT_CARD', 'BANK_TRANSFER', 'VOUCHER')),
    reference TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'CAPTURED' CHECK(status IN ('PENDING', 'AUTHORIZED', 'CAPTURED', 'REFUNDED', 'FAILED')),
    business_date TEXT NOT NULL,
    captured_by TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL
);

-- 13. Housekeeping Tasks (Unit of cleaning work per room)
CREATE TABLE IF NOT EXISTS housekeeping_tasks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    assigned_to_user_id TEXT REFERENCES users(id),
    priority TEXT NOT NULL DEFAULT 'MEDIUM' CHECK(priority IN ('URGENT', 'HIGH', 'MEDIUM', 'LOW')),
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'VERIFIED')),
    cleaning_status TEXT NOT NULL CHECK(cleaning_status IN ('DIRTY', 'CLEANING_IN_PROGRESS', 'CLEAN', 'INSPECTED')),
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 14. Maintenance Blocks (Out-of-service periods blocking inventory)
CREATE TABLE IF NOT EXISTS maintenance_blocks (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    room_id TEXT NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    start_date TEXT NOT NULL, -- YYYY-MM-DD
    end_date TEXT NOT NULL,   -- YYYY-MM-DD
    active INTEGER NOT NULL DEFAULT 1,
    created_by TEXT NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 15. Night Audits (Idempotent daily business-day close records)
CREATE TABLE IF NOT EXISTS night_audits (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    business_date TEXT NOT NULL,
    closed_at TEXT NOT NULL,
    closed_by TEXT NOT NULL REFERENCES users(id),
    total_room_revenue_cents INTEGER NOT NULL DEFAULT 0,
    total_tax_cents INTEGER NOT NULL DEFAULT 0,
    total_payments_cents INTEGER NOT NULL DEFAULT 0,
    balanced INTEGER NOT NULL DEFAULT 1,
    UNIQUE(property_id, business_date)
);

-- 16. Audit Logs (Immutable security and operational event log)
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    property_id TEXT REFERENCES properties(id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    details TEXT NOT NULL, -- JSON string
    ip_address TEXT,
    correlation_id TEXT,
    created_at TEXT NOT NULL
);

-- Performance and Tenancy Indexes
CREATE INDEX IF NOT EXISTS idx_properties_org ON properties(organization_id);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_memberships_prop ON memberships(organization_id, property_id);
CREATE INDEX IF NOT EXISTS idx_rooms_prop ON rooms(property_id);
CREATE INDEX IF NOT EXISTS idx_reservations_dates ON reservations(property_id, arrival_date, departure_date);
CREATE INDEX IF NOT EXISTS idx_reservations_room ON reservations(room_id);
CREATE INDEX IF NOT EXISTS idx_charges_folio ON charges(folio_id);
CREATE INDEX IF NOT EXISTS idx_payments_folio ON payments(folio_id);
CREATE INDEX IF NOT EXISTS idx_tasks_prop_status ON housekeeping_tasks(property_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_prop ON audit_logs(property_id, created_at);
