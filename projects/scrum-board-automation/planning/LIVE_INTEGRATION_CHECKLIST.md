# Board live integration checks — pending backend

These are required future checks, not passing results. Use disposable tenant/project fixtures and actual IAM, cookie/CSRF handlers and PM persistence. Do not weaken enforcement to satisfy frontend tests.

1. Sign in through the served portal; verify cookie security, CSRF bootstrap, protected page delivery and session response. No token in URLs/storage/logs.
2. Load registered SBA/PLG from actual project discovery; repeat synchronization without duplicate project/task records. Confirm source revision and freshness.
3. Create an issue through the real browser. Reload and reopen database to verify persistence. Missing scope/budget remains unready rather than preapproved.
4. Prepare a scoped, budget-authorized test task using supported APIs; request permitted FSM transitions through the real drawer. Verify server-resolved actor and exact returned state.
5. Forge caller/tenant, omit/alter CSRF and use revoked/expired session: server denies every attempt without state/evidence mutation. No invalid Bearer fallback to cookies.
6. Revoke underlying IAM session while browser remains open; next page/read/write/poll denies it. Verify browser session cannot resurrect access.
7. Simulate authority outage and stale snapshot/cursor; show errors and recover without invented state, duplicate events or history loss.
8. Actual Antigravity posts attributable activity/comments/evidence; board reflects persisted changes within five seconds on healthy connectivity. Agent-controlled PASS and Git commit alone cannot reach DONE.
9. Restart services between event acknowledgement and reading; history and cursor remain consistent. Inject failures and concurrent writes to prove atomic rollback.
10. Review the exact candidate independently and run the full CEO-to-plan-to-agent-to-board workflow before release approval.

Current controlled browser tests cover frontend request construction and user-visible handling only. They cannot validate this checklist's server security or real runtime behavior.
