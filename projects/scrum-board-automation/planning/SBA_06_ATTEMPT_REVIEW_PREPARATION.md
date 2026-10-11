# SBA-06 attempt and review frontend preparation

Delivered by Codex, 11 October 2026, on the existing SBA branch. Scope: `portal/scrum.html`, frontend browser tests and planning documentation.

The task drawer now presents server-provided attempts and reviews alongside activity and evidence. Unknown execution, cancellation requests and completed execution have distinct descriptions. Claimed reviews cannot become validated approval, and reviews bound to a previous candidate are visibly stale. No dispatch, approval or task movement is performed by these new sections.

Malformed, unavailable and empty responses are distinct; missing attempt/review interfaces remain visibly unavailable. Text is rendered safely, and delayed responses cannot overwrite a newly opened drawer. Read-only presentation works at a narrow viewport in controlled browser checks.

Verification: `python -m pytest tests/test_scrum_board_actions.py -q` using the existing project environment: **23 passed in 33.98 seconds**. `ruff check tests/test_scrum_board_actions.py` and `git diff --check` passed. These tests execute Chromium against controlled HTTP fixtures. They do not establish live provider, deployed backend, cryptographic admission or end-to-end workflow acceptance. No full repository gate was run for this frontend-only preparation.

Antigravity next: review the proposed fields and state mappings in `SBA_06_FRONTEND_SPEC.md`, agree the interface, and implement tenant-scoped read responses with admitted evidence and candidate bindings. Existing CC-02/SBA-03 review gates remain unchanged. Polling, pagination, comments and live runtime integration are still pending; SBA-06 is not marked DONE.
