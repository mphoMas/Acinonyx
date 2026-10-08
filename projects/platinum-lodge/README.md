# Platinum Lodge Hotel Management System

A working local web application for Platinum Lodge, Matola, Mozambique. Node.js 24 serves the interface and API; SQLite stores hotel records. No package installation, external account, or default password is required.

## Start

From this project directory, run:

```sh
npm start
```

Open **http://127.0.0.1:3000** on the machine running the application. On first use, create a manager account with a password of at least 10 characters. Add the hotel's confirmed rooms, capacities, rates, venues, and staff accounts in Rooms, Events, and Settings. The real hotel workspace starts empty. The application binds to loopback by default.

Select **Explore demo workspace** to try the workflows without changing hotel records. Each demo uses a separate temporary database. Demo guests, 24 rooms, three venue names, and rates are fictional. The advertised 100-room property is not treated as a verified inventory. Signing out or restarting discards that demo. Actual hotel records survive restarts.

## Implemented

- Operational dashboard with occupancy, arrivals, departures, receipts, and activity.
- Reservations with guest/company details, agreed rates, overlap and capacity validation, cancellation, no-show handling, room moves, and stay amendments.
- Reception check-in and check-out. Check-in requires a clean, unblocked room; check-out requires a settled account and marks the room dirty.
- Separate occupancy, cleaning, and maintenance status; housekeeping inspection approved by reception or a manager.
- Guest accounts, accommodation charges, additional charges, partial payments, manager refunds, CSV exports, and printable statements.
- Restaurant, bar, and poolside sales; room charges post atomically to checked-in guest accounts.
- Venue configuration, provisional/confirmed event bookings, schedule/capacity checks, deposits, cancellation, and printable event instructions.
- Maintenance issue register and room blocks; rooms with active/future bookings cannot be blocked.
- Staff roles enforced by the server, account deactivation, password changes, and an audit trail. Housekeeping and maintenance cannot fetch guest identities or financial records.
- Image gallery with the collected hotel image references, source and permission fields, and administrator uploads for JPEG, PNG, and WebP files up to 4 MB.
- English/Portuguese navigation and primary form labels, MZN formatting, local Matola dates, and responsive layouts. Some explanatory text remains in English.
- SQLite transactions and integer-cent monetary values. Booking, payment, charge, refund, and dining POST endpoints support persistent idempotency keys.

The application is an initial operational release, not a claim that every item in the earlier draft specification is delivered.

## Images

Ten remote photographs reference the Hotels.com/Expedia listing for Platinum Lodge, Matola. The workspace network policy blocked downloading their originals. Images require internet access and degrade to placeholders if the source cannot be reached. Reuse permission has not been established. Replace these reference images with approved hotel originals through Property gallery before publication. Sources remain in `assets/reference/image-manifest.json`.

## Data and backups

Actual records live in `data/hotel.sqlite`, with SQLite WAL files while the server runs. Uploaded images live in `data/uploads`. These paths are excluded from source control and distribution.

Create a consistent, verified database-and-image backup while the application is running:

```sh
node scripts/backup.mjs /path/to/backup-folder
```

To restore: stop the application, preserve the existing `data` directory separately, create a fresh `data` directory, and copy the backup's `hotel.sqlite` and `uploads` directory into it. Restart and sign in with the backed-up staff credentials. Sessions are intentionally not restored. The Settings JSON export is for reviewing operational records; it is not a complete account/database backup.

Backups contain sensitive guest information and password hashes. Store them with restricted access and schedule recurring backups in the deployment environment.

## Checks

```sh
npm run check
npm test
```

Browser checks passed for navigation, reservations, check-in, charges, payments, check-out, housekeeping, dining, image uploads, Portuguese navigation, and mobile overflow. External reference images were blocked during browser verification; local uploads were verified.

Tests cover setup, authentication, role restrictions, overbooking, housekeeping, dining transfers, balances, event conflicts/capacity, idempotent financial retries, refunds, amendments, atomic validation, demo isolation, and persistence across restarts.

## Deployment and remaining scope

This build runs locally and has not been published to Sites: the required publishing helpers were not installed in the execution environment. SQLite/Node hosting must support a persistent disk. A hosted Sites version would require porting server storage to D1 and uploads to R2; a static upload would lose shared hotel operations.

For a managed server, set `PORT`, `HOST`, and optionally `DATA_DIR`. Configure HTTPS through a reverse proxy and set `SECURE_COOKIE=1`. The default loopback binding should be retained until deployment is configured. The application does not include MFA, a password-recovery email service, granular per-action approval limits, automatic scheduled backups, high-availability hosting, or a formal production security review.

Payments record money already received or refunded; they do not move funds. Tax invoices, local statutory guest-registration rules, tax calculations, earned-revenue accounting, nightly posting/night audit, cashier-shift reconciliation, company credit billing, bulk/group room allocations, cancellation fee policies, staff assignment schedules, stock control, kitchen ticketing, online booking/channel management, and accounting/payment/message integrations remain future work. Event deposits are tracked separately from guest payments; event refunds must currently be handled and reconciled outside the application.

Accommodation is charged for the agreed stay when a reservation is created. Reports label these as booking charges rather than earned revenue. Cancellation/no-show reverses all booking charges with a traceable adjustment; deposits are refunded separately. Financial records are not deleted.

Session tokens are HttpOnly/SameSite cookies backed by server memory and expire after eight hours. Restarting the application signs staff out. Passwords use salted scrypt hashes. Cross-origin mutations are rejected and CSV exports neutralise spreadsheet formula prefixes.
