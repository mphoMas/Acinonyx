# MAS Issue Contracts, Dependencies & Acceptance Gates Specification

**Author:** `chief_architect`  
**Deliverable for:** `PM-03` (`MAS-9`)  
**Scope:** `mas/pm/`, `docs/`, `templates/`  
**Reviewer:** `product_lead`  
**Status:** Approved & Implemented

---

## 1. Issue Contract Schema

Every task ingested into MAS-PM must conform to the formal contract defined in `work_queue/tasks.json`:

```json
{
  "id": "ALLOCATION_ID",
  "title": "Clear Technical Objective",
  "priority": "CRITICAL | HIGH | MEDIUM | LOW",
  "dependencies": ["PREREQUISITE_ID_1"],
  "scope": ["path/to/whitelist/"],
  "assignee_principal": "authenticated_agent_role",
  "reviewer_principal": "independent_critic_role",
  "status": "BACKLOG",
  "acceptance": [
    "Test evidence",
    "Verifiable git commit",
    "Independent reviewer approval"
  ],
  "appetite_tokens": 50000,
  "appetite_timeout_s": 1800,
  "forbidden_paths": [".env", ".env.*", "**/secrets/**"]
}
```

---

## 2. Acceptance Gates Lifecycle

```
[BACKLOG] ──(Gate 1: Appetite)──► [REFINED]
    │
    ▼ (Gate 2: Scope Jail Whitelist)
[STAGED] ──(Gate 3: WIP Capacity & Circuit Breaker)──► [IN_PROGRESS]
    │
    ▼ (Gate 4: Git Commit Diff & Test Log Hash)
[VERIFICATION] ──(Gate 5: Unanimous Critic PASS & Separation of Duties)──► [JUDICIAL_REVIEW]
    │
    ▼ (Gate 6: Chief Architect Ratification)
[DONE]
```

1. **Gate 1 (Appetite):** Validates finite token budget (`appetite_tokens > 0`) and timeout (`appetite_timeout_s > 0`).
2. **Gate 2 (Scope Jail):** Validates normalized path whitelist without `..` directory traversal escapes.
3. **Gate 3 (WIP Capacity):** Enforces Little's Law WIP ceiling (`IN_PROGRESS <= 4`, `agent active <= 1`).
4. **Gate 4 (Empirical Evidence):** Requires verified `GIT_COMMIT` and `TEST_RUN_LOG` with zero non-zero exit codes.
5. **Gate 5 (Judicial Review):** Enforces separation of builder and judge; requires unanimous PASS from stage 4 critics.
6. **Gate 6 (Final Ratification):** Chief Architect signs off with formal `CriticVerdict`.
