# MAS_PM_BOARD_GAP_ANALYSIS.md
## Forensic Gap Analysis: Documented Requirements vs. Current Implementation for MAS-PM Board

> **Acinonyx Enterprise Systems Engineering Directorate**  
> **Document Reference:** `MAS-GAP-PM-001`  
> **Epic Reference:** `MAS-PM-BOARD-001`  
> **Authority:** Office of the Independent Reviewer, Chief Architect & Platform Engineering  
> **Baseline Commit:** `357dd4e2`  
> **Target Branch:** `Acinonyx_frontier`  
> **Status:** RATIFIED BASELINE GAP ASSESSMENT  

---

### 1. Executive Summary & Review Scope

The mission of `MAS-PM-BOARD-001` is to design, implement, test, and document a fully functional, agent-native project management board for ACINONYX, unifying Kanban continuous flow, optional Scrum goal-planning, Jira-grade issue hierarchies, and MAS cryptographic governance without external proprietary dependencies (e.g. Jira Cloud).

This document establishes the **forensic gap analysis** required by Section 2 of `MAS-PM-BOARD-001`. It evaluates the existing codebase (`mas/pm/`, `mas/dashboard/`, `portal/`, `tests/`) against the requirements, categorizing findings into:
1. **Reusable Foundation:** Components ready for direct reuse.
2. **Missing Capabilities:** Documented features absent from the codebase.
3. **Technical Debt:** Fragile implementations requiring refactoring.
4. **Security & Governance Vulnerabilities:** High and Critical defects that must be remediated as blocking prerequisites.

---

### 2. Comprehensive Requirements vs. Implementation Matrix

| Requirement Area | Documented Requirement (`MAS-PM-BOARD-001` & `MAS_PROJECT_MANAGEMENT_SPEC.md`) | Current Implemented State (`mas/pm/` @ `357dd4e2`) | Gap Severity | Classification |
|---|---|---|---|---|
| **Identity & Authentication** | Execution-context-derived principal identities; caller cannot forge or impersonate reviewers. | `caller_principal` is an untrusted string passed in tool parameters (`pm_transition_issue(caller_principal=...)`). | **CRITICAL** | **Defect (PM-SEC-001)** |
| **Evidence Validation** | Fail-closed on missing, forged, stale, or mismatched artifacts; verify actual Git commits and test outputs. | Local file check only; does not query Git objects (`git rev-parse`); skips verification if URI is not local. | **CRITICAL** | **Defect (PM-SEC-002)** |
| **Concurrency & Atomic WIP** | State checks, column WIP limits, and state transitions must be atomic under multi-agent concurrent execution. | WIP checks occur *prior* to opening the transaction in `fsm.py`, creating a race window. | **CRITICAL** | **Defect (PM-CON-001)** |
| **Filesystem Scope Jailing** | Scope whitelist and forbidden paths enforced against actual modified files in Git changesets. | Checks path string syntax only; does not inspect actual modified files from `git diff`. | **HIGH** | **Defect (PM-SEC-003)** |
| **Sequence Numbering** | Transactional sequence generator for issue keys (`CORE-1`, `CORE-2`) preventing race duplicates. | Uses `COUNT(*) + 1`, which collides under concurrency or after deletions. | **HIGH** | **Defect (PM-DATA-001)** |
| **Transition Guard Completeness** | Every FSM edge guarded; stale critic verdicts must be invalidated upon rework. | Stale `PASS` verdicts persist in DB and allow re-transition to Judicial Review without re-testing. | **HIGH** | **Defect (PM-GOV-001)** |
| **Visual Board UI** | Interactive Kanban board with 7 columns + 2 exceptional states, drag-and-drop with guard bridge. | Only a JSON REST endpoint exists (`/api/pm/board/<key>`); zero visual board UI implemented. | **HIGH** | **Missing Feature** |
| **Backlog & Hierarchy** | Initiatives, Epics, Tasks, Subtasks, Defects with parent-child links, ordering, and search. | Relational tables exist in SQLite, but no visual hierarchy tree, search UI, or dependency graph rendering. | **MEDIUM** | **Missing Feature** |
| **Hybrid Scrum Planning** | Optional Sprint entities (goals, dates, carry-over, backlog selection) without forcing 2-week timeboxes. | Not modeled in schema or DB; only raw continuous Kanban states exist. | **MEDIUM** | **Missing Feature** |
| **Agent Task Claiming** | Atomic claim API for available work evaluating priority, dependencies, appetite, and limits. | Assignment is static text; no atomic claiming protocol or dependency availability resolver. | **MEDIUM** | **Missing Feature** |
| **Human & ChatGPT Visibility** | Read-only authenticated export / inspection interface for human founder and external adviser (ChatGPT). | No dedicated read-only external inspection endpoint or redacted token mechanism. | **MEDIUM** | **Missing Feature** |
| **Flow Telemetry & CFD** | Real-time Cumulative Flow Diagram, cycle time scatterplots, token burn accounting. | Basic CFD snapshot table and cycle time formula exist in `mas/pm/metrics.py`, but no UI charts. | **LOW** | **Technical Debt** |

---

### 3. Detailed Forensic Findings

#### 3.1 Reusable Architecture & Subsystems
The existing `mas/pm/` subsystem represents a solid foundational core that must be extended rather than rewritten:
* **`mas/pm/models.py`:** Clean Pydantic v2 domain models for `Project`, `Issue`, `TransitionHistory`, `EvidenceLink`, `CriticVerdict`, `BoardState`, `ColumnInfo`, and `CFDSnapshot`.
* **`mas/pm/db.py`:** Robust SQLite database wrapper configured with `WAL` mode, foreign keys enabled, and a 5000ms busy timeout.
* **`mas/pm/metrics.py`:** Working computation of Little's Law metrics, cycle times, lead times, flow efficiency, and CFD state captures.
* **`mas/pm/tools.py`:** Registered MCP tool definitions (`pm_create_project`, `pm_create_issue`, `pm_transition_issue`, `pm_attach_evidence`, `pm_cast_verdict`, `pm_get_board_state`).
* **`mas/dashboard/server.py`:** Working HTTP routing and bearer token middleware with registered `/api/pm/board/` and `/api/pm/issues/` endpoints.

#### 3.2 Analysis of the Six Blocking Remediation Defects

##### Defect PM-SEC-001 (Critical): Unauthenticated Identity Impersonation
* **Location:** `mas/pm/fsm.py`, `mas/pm/tools.py`
* **Vulnerability:** The caller identity is provided directly as an argument:
  ```python
  def transition(self, issue_id_or_key: str, target_state: IssueState, caller_principal: str, ...):
      ...
      assert_separation_of_builder_and_judge(issue, caller_principal)
  ```
  An agent assigned as `senior_engineer` can easily supply `caller_principal="qa_critic"` or `caller_principal="chief_architect"`, completely evading the Separation of Builder and Judge guard.
* **Remediation Required:** Principal identity must be extracted from the authenticated session context (e.g., `ExecutionContext.get_current_principal()`, MCP authenticated token, or agent runtime identity). Supplying a mismatched caller principal must trigger an immediate security exception.

##### Defect PM-SEC-002 (Critical): Loose / Forged Evidence Validation
* **Location:** `mas/pm/guards.py` (`validate_evidence`)
* **Vulnerability:** Evidence checking only verifies exit codes in JSON payloads and SHA-256 for local files that happen to exist. If `uri` points to a Git commit (`git:commit:123`), the commit hash is never verified against the local Git object database (`git cat-file -e`). Furthermore, if a non-existent path is passed with no local file, the integrity check is silently skipped.
* **Remediation Required:** Fail closed on missing, forged, stale, or unverified evidence:
  1. For `GIT_COMMIT`: execute `git rev-parse --verify <hash>` and ensure commit exists on current branch.
  2. For `TEST_RUN_LOG`: enforce that log file exists on disk and its SHA-256 matches `content_hash` exactly.
  3. Validate that test execution timestamp is strictly newer than the last code commit.

##### Defect PM-CON-001 (Critical): Non-Atomic Concurrency Race Windows
* **Location:** `mas/pm/fsm.py` (`transition`) vs `mas/pm/db.py` (`update_issue_state`)
* **Vulnerability:** In `fsm.py`, `validate_wip_limit()` executes queries against the database *before* entering `self.db.update_issue_state()`. If four workers concurrently check `count_issues_in_state("IN_PROGRESS")`, all four see a count of 3, all four pass the guard, and all four transition, resulting in 7 items in progress (violating the limit of 4).
* **Remediation Required:** The entire transition workflow—fetching issue state, evaluating guards, checking column and agent WIP limits, updating state, and logging history—must execute within a single atomic `BEGIN IMMEDIATE` transaction block protected by an internal re-entrant lock.

##### Defect PM-SEC-003 (High): Unchecked Filesystem Scope on Git Changesets
* **Location:** `mas/pm/guards.py` (`validate_scope_jail`)
* **Vulnerability:** `validate_scope_jail()` only validates the string patterns in `path_whitelist` at the time an issue enters `STAGED`. When transitioning from `IN_PROGRESS` to `VERIFICATION`, the system never compares the actual files changed in the git commit against `path_whitelist` or `forbidden_paths`.
* **Remediation Required:** During transition to `VERIFICATION`, execute `git diff-tree --no-commit-id --name-only -r <commit_sha>` and assert that every changed file matches at least one glob in `path_whitelist` and zero globs in `forbidden_paths`.

##### Defect PM-DATA-001 (High): Race-Prone Issue Key Allocation
* **Location:** `mas/pm/db.py` (`next_issue_key`)
* **Vulnerability:** Issue keys are generated via `SELECT COUNT(*) FROM pm_issues WHERE key LIKE 'CORE-%'`. If issues are deleted, or two issues are inserted concurrently, duplicate keys (`CORE-3`, `CORE-3`) are generated, violating database uniqueness constraints and crashing agent turns.
* **Remediation Required:** Create a dedicated relational table `pm_project_sequences (project_key TEXT PRIMARY KEY, last_sequence INTEGER)` and update it using atomic SQL:
  ```sql
  UPDATE pm_project_sequences SET last_sequence = last_sequence + 1 
  WHERE project_key = ? RETURNING last_sequence;
  ```

##### Defect PM-GOV-001 (High): Stale Critic Verdicts Persisting After Rework
* **Location:** `mas/pm/db.py`, `mas/pm/guards.py`, `mas/pm/fsm.py`
* **Vulnerability:** When an issue in `VERIFICATION` is rejected to `REJECTED_REWORK` and subsequently moved back to `IN_PROGRESS` for fixes, the previous `PASS` verdicts in `pm_critic_verdicts` remain intact. When the issue re-enters `JUDICIAL_REVIEW`, `validate_critic_verdicts()` reads the stale verdicts from the previous run and permits release without re-audit.
* **Remediation Required:** Any transition to `REJECTED_REWORK` or re-entry to `IN_PROGRESS` must invalidate all existing verdicts (e.g. marking `is_stale = 1` or recording the `rework_cycle`), and `validate_critic_verdicts()` must only consider verdicts recorded during the current cycle.

---

### 4. Canonical Interface Host Assessment: `portal/` vs `mas/dashboard/`

Section 5 of `MAS-PM-BOARD-001` mandates assessing whether the existing dashboard or research portal should host the visual board and selecting **one canonical interface**:

| Evaluation Dimension | Option 1: Standalone `mas/dashboard/` | Option 2: Integrated `portal/` (Living Portal) | Winner & Rationale |
|---|---|---|---|
| **Design Consistency** | Basic dark theme, separate CSS architecture. | Rich, curated design system (`portal/css/`), typography (Outfit/JetBrains Mono), toast notifications, and HUD. | **`portal/`** (Prevents aesthetic fragmentation) |
| **Information Architecture** | Disjoint URL (`http://localhost:8000`), separate tabs. | Unified single-pane-of-glass: Founder and agents navigate Research, Architecture, Topology, and Board in one place. | **`portal/`** (Zero context switching) |
| **Component Reusability** | Few reusable components; would require recreating modals, toasts, and drawers. | Existing `ToastManager`, `Modal` abstractions, and keyboard shortcuts (`Ctrl+J`, `Ctrl+K`, `?`). | **`portal/`** (Reuses proven UI primitives) |
| **API & Backend Coupling** | Hosted directly by `mas/dashboard/server.py`. | Served by `mas/dashboard/server.py` as static route `/` or `/portal/`. | **Unified** (Dashboard server serves Portal) |

**Architectural Decision:** **`portal/` is selected as the Canonical Interface.** The Project Management Board will be implemented as a first-class navigation view (`nav-board`) inside `portal/`, served directly by `mas/dashboard/server.py`.

---

### 5. Actionable Remediation Backlog

In compliance with Section 3 and Section 9 of `MAS-PM-BOARD-001`, the following 7 issues are registered in the MAS-PM backlog:

1. **`PM-SEC-001` (Critical):** Derive agent and reviewer identities from authenticated execution context; prohibit caller-supplied identity impersonation.
2. **`PM-SEC-002` (Critical):** Fail closed on missing, forged, stale, or mismatched evidence; verify real execution artifacts.
3. **`PM-CON-001` (Critical):** Make state checks, WIP checks, and transitions atomic under concurrent workers.
4. **`PM-SEC-003` (High):** Enforce scope whitelist and forbidden paths against actual file operations and changed files.
5. **`PM-DATA-001` (High):** Replace `COUNT(*) + 1` issue numbering with transactional sequence allocation.
6. **`PM-GOV-001` (High):** Enforce guards for every FSM transition and invalidate stale approvals after rework.
7. **`MAS-PM-BOARD-001` (High, Epic):** Design and Implement the Native Scrum/Kanban Project Management Board.

---

*Authored by Project ACINONYX Architecture & Independent Review Directorate.*  
*Companion Deliverables: [MAS_PM_BOARD_ARCHITECTURE.md](file:///home/acinonyx/Desktop/MAS/MAS_PM_BOARD_ARCHITECTURE.md) | [MAS_PM_BOARD_UX_SPEC.md](file:///home/acinonyx/Desktop/MAS/MAS_PM_BOARD_UX_SPEC.md) | [MAS_PM_BOARD_IMPLEMENTATION_PLAN.md](file:///home/acinonyx/Desktop/MAS/MAS_PM_BOARD_IMPLEMENTATION_PLAN.md)*
