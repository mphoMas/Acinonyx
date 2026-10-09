# Candidate validation — 9 October 2026

Executed against this static frontend candidate:

- Node 24: 6 unit tests passed. Covers stable retry references, context isolation/version invalidation, calendar-date validation including leap dates, HTML escaping and launch/housekeeping scope, and minimum text/control-boundary contrast.
- Chromium through Python Playwright: 36 browser checks passed; no JavaScript page errors. Five views at 320/360/768/1440px without document horizontal overflow; eight exceptional interface states; stable preview draft reference; Escape retains original property/draft; discard clears draft/previous records; housekeeping visibility; reduced-motion responsive check; native modal backwards keyboard focus; skip-link keyboard navigation; 200% CSS-zoom overflow smoke check (not a substitute for manual browser zoom qualification).

These checks verify specific frontend behavior only. They do not verify backend authorization, real reservations, payment processing, reconciliation, durable idempotency, operational continuity or staff productivity. The operation-reference helper is in-memory; nothing is persisted or sent to a service. No full screen-reader audit, Portuguese translation acceptance, comprehensive WCAG qualification, production performance measurement or independent QA sign-off has occurred. Test output does not close dependent tickets or permit release.

Reproduce using commands in DELIVERY_REGISTER.md. Browser runner uses installed Chromium at /usr/bin/chromium and needs Python Playwright. No dependency was added to the backend runtime.


## Lifecycle iteration

Fixed mismatched heading/state/metric styles, separated warning colours for dirty/inspection rooms, and strengthened input/select/button boundary contrast. Reviewed the actual Chromium screenshots: [mobile Today](evidence/today-360.png) and [desktop Today](evidence/today-1440.png). Screenshots contain fictional data and demonstrate frontend design only. Reproduce images with `PLG_SCREENSHOT_DIR=/your/scratch/directory` when running the browser checks.
