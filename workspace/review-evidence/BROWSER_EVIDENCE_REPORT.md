# SBA-05 Browser Authentication & Tenant Portal Evidence

**Execution Timestamp:** 2026-10-10 21:54:26 UTC
**Host / Port:** 127.0.0.1:45195

### Verified Interaction Sequence

- 1. Unauthenticated /portal/scrum.html redirected to /portal/login.html (302)
- 2. Authenticated via /api/pm/v1/session/login; received session cookie
- 3. Cookie attributes verified: HttpOnly=True, SameSite=Lax
- 4. Board rendered live issues SBA-1 and SBA-2 from tenant-scoped PM database
- 5. In-browser session query returned principal=tenant_evidence:browser_operator, tenant=tenant_evidence
- 6. Logout with CSRF token succeeded (200)
- 7. Post-logout /api/pm/projects returned HTTP 403 (Forbidden/Unauthorized)
- 8. Inactive test sessions revoked through IAM administration

### Screenshots Captured

- `01_portal_login_page.png` (Unprivileged public login bootstrap)
- `02_scrum_board_authenticated.png` (Live tenant-scoped board rendering)
