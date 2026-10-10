# Architect Planning Guide: Publishing Conversation-Derived Plans into MAS-PM

This guide specifies how Codex, acting as system architect and Scrum master, publishes structured plans derived from CEO conversations directly into the MAS-PM board.

## 1. Operating Model & Authority

```
+-------------------------------------------------------------+
| CEO / Product Authority                                     |
| Discusses project vision, scope boundaries and budget       |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Codex (Architect & Scrum Master)                            |
| 1. Formulates structured plan from conversation             |
| 2. Validates task graph, paths, and dependencies            |
| 3. Publishes via authenticated client/CLI/tool              |
+-------------------------------------------------------------+
                              |
                              | POST /api/pm/v1/projects/{project_id}/plans
                              v
+-------------------------------------------------------------+
| MAS-PM Backend (Deterministic Endpoint)                     |
| 1. Checks tenant authorization & project ownership          |
| 2. Enforces idempotency & optimistic revision locking       |
| 3. Pre-validates complete task graph (cycles, safe paths)   |
| 4. Preserves active runtime work & attached evidence        |
| 5. Atomically commits plan, issues, and mappings            |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Real MAS Board & Runtime Tickets                            |
| New tasks enter BACKLOG column                              |
+-------------------------------------------------------------+
```

### Deterministic Backend Boundary
- **No LLM in the backend:** Free-form natural language interpretation is strictly banned inside the deterministic backend endpoint.
- **Architect's role:** The architect converts conversation into the typed `PlanPublicationRequest` structure.
- **Proposed ownership != Runtime permission:** The `proposed_delivery_owner` field is an advisory recommendation for board transparency; it does not grant runtime execution permissions or assign runtime principals.
- **Proposed budget != Spending grant:** The `proposed_budget_tokens` field does not authorize execution token spend (`appetite_tokens` remains governed by runtime authorization).

---

## 2. API Contract

### Endpoint
`POST /api/pm/v1/projects/{project_id_or_key}/plans`

### Headers
| Header | Value / Description | Required |
|---|---|---|
| `Authorization` | `Bearer <token>` (or `mas_session` Cookie with `X-CSRF-Token`) | Yes |
| `Content-Type` | `application/json` | Yes |
| `Idempotency-Key` | Unique string (e.g., UUID or plan hash) | Recommended |

### Request Payload Shape
```json
{
  "schema_version": 1,
  "plan_id": "plan-hotel-core-v1",
  "revision": 1,
  "expected_previous_revision": null,
  "source_commit": "ba36767b43b679198aa74ba1f39adfa858fa72ea",
  "scope_reference": "CEO-AGREED-HOTEL-BOOKING-SCOPE",
  "tasks": [
    {
      "task_id": "task-core-01",
      "planning_reference": "PLG-01",
      "title": "Booking Engine API Contract",
      "description": "Define API endpoints for booking reservation and availability checks.",
      "type": "TASK",
      "priority": "CRITICAL",
      "parent_task_id": null,
      "dependencies": [],
      "path_whitelist": [
        "projects/platinum-lodge/",
        "workspace/Hotel/"
      ],
      "acceptance_criteria": [
        "Room availability returns valid availability records",
        "Booking creation prevents double-booking race condition"
      ],
      "proposed_delivery_owner": "Codex",
      "reviewer_requirement": "Independent reviewer",
      "proposed_budget_tokens": 50000
    },
    {
      "task_id": "task-core-02",
      "planning_reference": "PLG-02",
      "title": "Payment Processor Gateway Adapter",
      "description": "Implement Stripe/PayGate adapter with idempotent webhook verification.",
      "type": "TASK",
      "priority": "HIGH",
      "parent_task_id": null,
      "dependencies": [
        "PLG-01"
      ],
      "path_whitelist": [
        "projects/platinum-lodge/payments/"
      ],
      "acceptance_criteria": [
        "Signature verification passes webhook validation tests",
        "Replayed webhooks return cached receipt"
      ],
      "proposed_delivery_owner": "Antigravity",
      "reviewer_requirement": "Independent reviewer",
      "proposed_budget_tokens": 75000
    }
  ]
}
```

### Response Payload Shape
```json
{
  "schema_version": 1,
  "success": true,
  "plan_id": "plan-hotel-core-v1",
  "revision": 1,
  "project_id": "3db44a0d-990a-4eed-a100-d33d006269cf",
  "project_key": "PLG",
  "tasks_created": 2,
  "tasks_updated": 0,
  "mappings": [
    {
      "task_id": "task-core-01",
      "planning_reference": "PLG-01",
      "local_issue_id": "d0e1f2a3-...",
      "local_issue_key": "PLG-1",
      "is_new": true
    },
    {
      "task_id": "task-core-02",
      "planning_reference": "PLG-02",
      "local_issue_id": "b4c5d6e7-...",
      "local_issue_key": "PLG-2",
      "is_new": true
    }
  ],
  "changes_requiring_reconciliation": []
}
```

---

## 3. Invocation Methods for the Architect

### Method A: Supported Python Client (`PlanPublisherClient`)
```python
from mas.pm.client import PlanPublisherClient
from mas.pm.models import PlanPublicationRequest, PlanTaskDefinition, PriorityLevel

client = PlanPublisherClient(
    base_url="http://127.0.0.1:8080",
    auth_token="<ARCHITECT_BEARER_TOKEN>",
)

request = PlanPublicationRequest(
    plan_id="plan-sba-v1",
    revision=1,
    source_commit="ba36767b",
    scope_reference="CEO-CONVERSATION-2026-10-10",
    tasks=[
        PlanTaskDefinition(
            task_id="t-01",
            planning_reference="SBA-03",
            title="Publish conversation-derived plans into MAS-PM",
            description="Build planning endpoint and architect tool",
            priority=PriorityLevel.CRITICAL,
            path_whitelist=["mas/pm/", "mas/dashboard/"],
            acceptance_criteria=["Contract endpoints tested with 100% pass"],
            proposed_delivery_owner="Antigravity",
        ),
    ],
)

response = client.publish_plan(
    project_id_or_key="SBA",
    plan=request,
    idempotency_key="plan-sba-rev-1",
)
print(f"Published revision {response.revision}: {response.tasks_created} created")
```

### Method B: Supported Command-Line Interface (`mas.pm.publisher_cli`)
Save the structured plan as a JSON file (e.g., `plan.json`) and publish:
```bash
python3 -m mas.pm.publisher_cli \
  --url http://127.0.0.1:8080 \
  --token "$MAS_ARCHITECT_TOKEN" \
  --project SBA \
  --plan-file plan.json \
  --idempotency-key "idem-sba-03-rev1"
```
Or via standard input:
```bash
cat plan.json | python3 -m mas.pm.publisher_cli \
  --url http://127.0.0.1:8080 \
  --token "$MAS_ARCHITECT_TOKEN" \
  --project SBA
```

### Method C: Agent Tool / Function Calling (`pm_publish_plan`)
When running inside an agent session with tool access:
```python
result = pm_publish_plan(
    project_id_or_key="SBA",
    plan={
        "plan_id": "plan-sba-v1",
        "revision": 1,
        "tasks": [...]
    },
    caller_principal="codex-architect",
    idempotency_key="plan-idem-key"
)
```

---

## 4. Idempotency & Concurrency Rules

1. **Idempotency (`Idempotency-Key`):**
   - If a request with the same `Idempotency-Key` and an **identical canonical JSON payload** is received, the server returns the previously generated response without re-executing mutations.
   - If the same key is re-used with a **different payload**, the server immediately rejects the request with HTTP `409 Conflict` (`idempotency_conflict`).
2. **Optimistic Revision Locking (`expected_previous_revision`):**
   - To prevent concurrent architects from overwriting plans, pass `expected_previous_revision: <last_seen_revision>`.
   - If the database has a revision higher than or different from `expected_previous_revision`, the endpoint rejects with HTTP `409 Conflict` (`stale_revision` or `revision_mismatch`).
3. **Atomic Transaction:**
   - The plan record, all issue insertions/updates, task mappings, and dependency updates are applied in a single atomic SQLite transaction. If any step fails, the entire transaction rolls back completely.

---

## 5. Work Preservation & Reconciliation Rules

- **New Tasks:** Always enter `IssueState.BACKLOG`.
- **Active Work Inviolability:**
  - If a task is in `IN_PROGRESS`, `STAGED`, `VERIFICATION`, `JUDICIAL_REVIEW`, or `DONE`, subsequent plan revisions **never** overwrite its `current_state`, assigned principal (`assignee_principal`), tokens consumed (`tokens_spent`), reflexion attempts, or attached evidence (`pm_evidence_links`).
- **Scope & Acceptance Reconciliation:**
  - If a plan revision modifies the `acceptance_criteria` or `path_whitelist` of an active task, the server applies the metadata update but records the change in `changes_requiring_reconciliation`.
  - The response returns `changes_requiring_reconciliation` items with `change_type`, `old_value`, and `new_value` so the architect and coordinator can review and re-stage if necessary.
- **Removed Plan Items:**
  - If a task existed in Revision 1 but is omitted from Revision 2, it is **never** deleted from the database. Its runtime state, history, and evidence are preserved intact.

---

## 6. Pre-Publication Validation Rejections

The endpoint validates the full graph before touching the database. The following conditions cause HTTP `400 Bad Request` rejection:
- **Duplicate Identities:** Duplicate `task_id` or `planning_reference` within the request.
- **Contradictory Mappings:** Reusing an existing `planning_reference` for a completely different `task_id`, or vice versa.
- **Dependency Cycles:** Cyclic dependencies between tasks (e.g., A -> B -> A).
- **Hierarchy Cycles:** Parent-child circular relationships.
- **Unsafe Path Whitelists:** Path traversals (`..`), absolute paths (`/`), null bytes, or wildcards (`*`).
- **Missing References:** Dependencies or parent references that do not exist in the plan or the database.
