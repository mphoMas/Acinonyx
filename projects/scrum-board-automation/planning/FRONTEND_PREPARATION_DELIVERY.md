# Unblocked frontend preparation

Login: structured error messages, focused alert, busy state, bounded 15-second request, same-origin credentials, no API redirect following, token visibility toggle and remasking after submit. Credential remains in page memory for retry, cleared on successful login; no URL/browser-storage persistence.

Board checks: assert expected project name and exact visible ticket keys. A negative test removes an expected ticket and confirms the acceptance assertion fails; successful login alone cannot establish board population.

Activity/evidence: read-only drawer preparation with explicit backend unavailable/identity missing/empty states, escaped plain-text rendering and unverified status for unsupported evidence claims. Endpoint response shape remains an integration proposal in SBA_06_FRONTEND_SPEC.md.

Scope: frontend only. Rejected backend findings remain outstanding. Controlled browser fixtures are not live IAM/Antigravity evidence, and no task is marked DONE.

Verification: 11 controlled-response browser tests passed in 14.63s; Ruff and diff checks passed. Login and pending activity drawer screenshots captured and visually inspected outside checkout. These results do not certify the rejected backend or actual live activity feed.
