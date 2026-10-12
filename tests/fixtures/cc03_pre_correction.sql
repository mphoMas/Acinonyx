-- Generated from actual 284cb877 -> 9c2de7a8 schema; disposable test data only.
BEGIN TRANSACTION;
CREATE TABLE pm_cfd_snapshots (
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    project_id TEXT NOT NULL,
                    backlog_count INTEGER NOT NULL,
                    refined_count INTEGER NOT NULL,
                    staged_count INTEGER NOT NULL,
                    in_progress_count INTEGER NOT NULL,
                    verification_count INTEGER NOT NULL,
                    judicial_review_count INTEGER NOT NULL,
                    done_count INTEGER NOT NULL
                );
CREATE TABLE pm_coordinator_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    attempt_seq INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED', 'UNKNOWN_EXECUTION', 'CANCELED')),
                    fencing_token INTEGER NOT NULL DEFAULT 1,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    finished_at TIMESTAMP,
                    budget_tokens_allocated INTEGER NOT NULL DEFAULT 0,
                    budget_tokens_spent INTEGER NOT NULL DEFAULT 0,
                    candidate_commit_sha TEXT,
                    failure_reason TEXT,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                    FOREIGN KEY(project_id, task_id, issue_id)
                        REFERENCES pm_task_mappings(project_id, task_id, local_issue_id),
                    FOREIGN KEY(project_id, issue_id) REFERENCES pm_issues(project_id, id),
                    CONSTRAINT uq_attempt_identity UNIQUE (attempt_id, issue_id, task_id, project_id, tenant_id),
                    CONSTRAINT uq_issue_attempt_seq UNIQUE (issue_id, attempt_seq)
                );
INSERT INTO "pm_coordinator_attempts" VALUES('history-attempt','tenant','history-project','history-issue','history-task',1,'RUNNING',1,'2026-10-12 07:13:05',NULL,0,0,NULL,NULL);
CREATE TABLE pm_coordinator_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    cursor_seq INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    event_payload JSON NOT NULL,
                    emitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(run_id) REFERENCES pm_coordinator_runs(run_id) ON DELETE CASCADE,
                    CONSTRAINT uq_run_cursor UNIQUE (run_id, cursor_seq)
                );
INSERT INTO "pm_coordinator_events" VALUES(1,'history-run',1,'note','{}','2026-10-12 07:13:05');
CREATE TABLE pm_coordinator_evidence_receipts (
                    evidence_id TEXT PRIMARY KEY,
                    issue_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    candidate_commit_sha TEXT NOT NULL,
                    nonce TEXT NOT NULL UNIQUE,
                    key_id TEXT NOT NULL,
                    signature TEXT NOT NULL,
                    canonical_payload JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                    FOREIGN KEY(attempt_id) REFERENCES pm_coordinator_attempts(attempt_id) ON DELETE CASCADE,
                    FOREIGN KEY(run_id) REFERENCES pm_coordinator_runs(run_id) ON DELETE CASCADE
                );
INSERT INTO "pm_coordinator_evidence_receipts" VALUES('history-receipt','history-issue','history-task','history-attempt','history-run','historical-candidate','historical-nonce','historical-key','historical-signature','{}','2026-10-12 07:13:05');
CREATE TABLE pm_coordinator_intents (
                    intent_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    adapter_type TEXT NOT NULL CHECK(adapter_type IN ('antigravity', 'codex', 'synthetic')),
                    status TEXT NOT NULL CHECK(status IN ('PENDING', 'CLAIMED', 'PROCESSING', 'COMPLETED', 'FAILED', 'UNKNOWN_EXECUTION', 'CANCELED', 'CANCEL_REQUESTED')),
                    fencing_token INTEGER NOT NULL DEFAULT 1,
                    worker_id TEXT,
                    lease_expires_at REAL,
                    lease_heartbeat_at REAL,
                    payload JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                    FOREIGN KEY(attempt_id, issue_id, task_id, project_id, tenant_id)
                        REFERENCES pm_coordinator_attempts(attempt_id, issue_id, task_id, project_id, tenant_id),
                    CONSTRAINT uq_intent_issue_attempt UNIQUE (issue_id, attempt_id, adapter_type)
                );
INSERT INTO "pm_coordinator_intents" VALUES('history-intent','tenant','history-project','history-issue','history-task','history-attempt','antigravity','PROCESSING',1,NULL,NULL,NULL,'{}','2026-10-12 07:13:05','2026-10-12 07:13:05');
CREATE TABLE pm_coordinator_reservations (
                    reservation_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    attempt_id TEXT NOT NULL,
                    authorization_ref TEXT NOT NULL,
                    amount INTEGER NOT NULL CHECK(amount >= 0),
                    settled_amount INTEGER NOT NULL DEFAULT 0 CHECK(settled_amount >= 0),
                    status TEXT NOT NULL CHECK(status IN ('HELD', 'SETTLED', 'RELEASED')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    settled_at TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                    FOREIGN KEY(attempt_id) REFERENCES pm_coordinator_attempts(attempt_id) ON DELETE CASCADE
                );
CREATE TABLE pm_coordinator_runs (
                    run_id TEXT PRIMARY KEY,
                    intent_id TEXT NOT NULL REFERENCES pm_coordinator_intents(intent_id),
                    attempt_id TEXT NOT NULL,
                    fencing_token INTEGER NOT NULL,
                    runtime_session_id TEXT,
                    process_pid INTEGER,
                    process_pgid INTEGER,
                    status TEXT NOT NULL CHECK(status IN ('SPAWNING', 'STREAMING', 'EXITED', 'INTERRUPTED', 'KILLED')),
                    exit_code INTEGER,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    FOREIGN KEY(attempt_id) REFERENCES pm_coordinator_attempts(attempt_id) ON DELETE CASCADE,
                    CONSTRAINT uq_physical_dispatch UNIQUE (intent_id, fencing_token)
                );
INSERT INTO "pm_coordinator_runs" VALUES('history-run','history-intent','history-attempt',1,NULL,NULL,NULL,'SPAWNING',NULL,'2026-10-12 07:13:05',NULL);
CREATE TABLE pm_critic_verdicts (
                    id TEXT PRIMARY KEY,
                    issue_id TEXT NOT NULL,
                    reviewer_principal TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    findings JSON NOT NULL,
                    signature TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, rework_cycle INTEGER DEFAULT 0, commit_sha TEXT,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
CREATE TABLE pm_dependencies (
                    blocker_id TEXT NOT NULL,
                    blocked_id TEXT NOT NULL,
                    PRIMARY KEY(blocker_id, blocked_id),
                    FOREIGN KEY(blocker_id) REFERENCES pm_issues(id) ON DELETE CASCADE,
                    FOREIGN KEY(blocked_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
CREATE TABLE pm_evidence_links (
                    id TEXT PRIMARY KEY,
                    issue_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    uri TEXT NOT NULL,
                    payload JSON,
                    linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
CREATE TABLE pm_idempotency_keys (
                    tenant_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    response_code INTEGER NOT NULL,
                    response_body TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (tenant_id, action, idempotency_key)
                );
CREATE TABLE pm_issues (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    key TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    issue_type TEXT NOT NULL,
                    current_state TEXT NOT NULL,
                    parent_id TEXT,
                    assignee_principal TEXT,
                    appetite_tokens INTEGER NOT NULL DEFAULT 50000,
                    appetite_timeout_s INTEGER NOT NULL DEFAULT 1800,
                    tokens_spent INTEGER NOT NULL DEFAULT 0,
                    reflexion_attempts INTEGER NOT NULL DEFAULT 0,
                    path_whitelist JSON,
                    forbidden_paths JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, priority TEXT DEFAULT 'MEDIUM', sprint_id TEXT, rework_cycle INTEGER DEFAULT 0, blocker_reason TEXT, task_id TEXT, planning_reference TEXT, acceptance_criteria JSON, proposed_delivery_owner TEXT, reviewer_requirement TEXT, proposed_budget_tokens INTEGER DEFAULT 0, staged_acceptance_criteria JSON, staged_path_whitelist JSON, staged_reviewer_requirement TEXT, staged_reviewer_action TEXT, policy_version INTEGER NOT NULL DEFAULT 1, staged_proposal_id TEXT, staged_proposal_rev INTEGER, has_pending_reconciliation INTEGER DEFAULT 0,
                    FOREIGN KEY(project_id) REFERENCES pm_projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(parent_id) REFERENCES pm_issues(id) ON DELETE SET NULL
                );
INSERT INTO "pm_issues" VALUES('history-issue','history-project','HST-1','History','','TASK','BACKLOG',NULL,NULL,100,1800,0,0,'[]','[]','2026-10-12T07:13:05.009452+00:00','2026-10-12T07:13:05.009452+00:00','MEDIUM',NULL,0,NULL,NULL,NULL,'[]',NULL,NULL,0,NULL,NULL,NULL,NULL,1,NULL,NULL,0);
CREATE TABLE pm_plans (
                    project_id TEXT NOT NULL REFERENCES pm_projects(id) ON DELETE CASCADE,
                    plan_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    source_commit TEXT,
                    scope_reference TEXT,
                    published_by TEXT NOT NULL,
                    tasks_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT pk_pm_plans PRIMARY KEY (project_id, plan_id, revision)
                );
CREATE TABLE pm_project_sequences (
                    project_key TEXT PRIMARY KEY,
                    last_sequence INTEGER NOT NULL DEFAULT 0
                );
CREATE TABLE pm_project_sources (
                    project_id TEXT PRIMARY KEY,
                    repository_id TEXT NOT NULL,
                    repository_owner TEXT NOT NULL,
                    repository_name TEXT NOT NULL,
                    configured_branch TEXT NOT NULL,
                    root_path TEXT NOT NULL,
                    planning_path TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    source_revision TEXT,
                    last_successful_sync TIMESTAMP,
                    last_error TEXT,
                    is_stale INTEGER NOT NULL DEFAULT 0,
                    remote_project_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES pm_projects(id) ON DELETE CASCADE
                );
CREATE TABLE pm_projects (
                    id TEXT PRIMARY KEY,
                    key TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    token_budget INTEGER NOT NULL DEFAULT 5000000,
                    tokens_consumed INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
INSERT INTO "pm_projects" VALUES('history-project','HST','Historical fixture','',100,0,'2026-10-12T07:13:05.009210+00:00','2026-10-12T07:13:05.009210+00:00');
CREATE TABLE pm_reconciliation_audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    issue_id TEXT NOT NULL,
                    issue_key TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    proposal_id TEXT,
                    proposal_rev INTEGER,
                    base_policy_version INTEGER NOT NULL,
                    resulting_policy_version INTEGER NOT NULL,
                    before_policy JSON NOT NULL,
                    after_policy JSON NOT NULL,
                    evidence_invalidated_count INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
CREATE TABLE pm_schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
INSERT INTO "pm_schema_migrations" VALUES(2026101201,'cc_03_coordinator_state','cc03_sha256_composite_ownership_v1','2026-10-12 07:13:05');
CREATE TABLE pm_sessions (
                    token_hash TEXT PRIMARY KEY,
                    csrf_token TEXT NOT NULL,
                    principal TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    permitted_actions JSON NOT NULL,
                    iam_token_hash TEXT,
                    iam_session_id TEXT,
                    iam_expires_at REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at REAL NOT NULL,
                    is_revoked INTEGER NOT NULL DEFAULT 0
                , issued_roles JSON, issued_scopes JSON);
CREATE TABLE pm_sprints (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    goal TEXT,
                    state TEXT NOT NULL CHECK(state IN ('FUTURE', 'ACTIVE', 'CLOSED')),
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES pm_projects(id) ON DELETE CASCADE
                );
CREATE TABLE pm_task_mappings (
                    project_id TEXT NOT NULL REFERENCES pm_projects(id) ON DELETE CASCADE,
                    planning_reference TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    local_issue_id TEXT NOT NULL REFERENCES pm_issues(id) ON DELETE CASCADE,
                    local_issue_key TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, legacy_task_id TEXT,
                    CONSTRAINT pk_task_mapping PRIMARY KEY (project_id, planning_reference),
                    CONSTRAINT uq_task_mapping_task_id UNIQUE (project_id, task_id),
                    CONSTRAINT uq_task_mapping_local_issue UNIQUE (project_id, local_issue_id),
                    CONSTRAINT uq_task_mapping_local_key UNIQUE (project_id, local_issue_key)
                );
INSERT INTO "pm_task_mappings" VALUES('history-project','H-1','history-task','history-issue','HST-1','2026-10-12 07:13:05','2026-10-12 07:13:05',NULL);
CREATE TABLE pm_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id TEXT NOT NULL,
                    from_state TEXT NOT NULL,
                    to_state TEXT NOT NULL,
                    triggered_by TEXT NOT NULL,
                    reason TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(issue_id) REFERENCES pm_issues(id) ON DELETE CASCADE
                );
CREATE INDEX idx_project_sources_status ON pm_project_sources(status);
CREATE INDEX idx_pm_sessions_principal ON pm_sessions(principal);
CREATE INDEX idx_pm_sessions_revoked ON pm_sessions(is_revoked);
CREATE INDEX idx_pm_plans_project_rev ON pm_plans(project_id, revision);
CREATE INDEX idx_idempotency_tenant_action ON pm_idempotency_keys(tenant_id, action);
CREATE INDEX idx_pm_recon_audits_issue ON pm_reconciliation_audits(issue_id);
CREATE INDEX idx_pm_recon_audits_project ON pm_reconciliation_audits(project_id);
CREATE INDEX idx_issues_state ON pm_issues(current_state);
CREATE INDEX idx_issues_project ON pm_issues(project_id);
CREATE INDEX idx_issues_assignee ON pm_issues(assignee_principal);
CREATE INDEX idx_issues_sprint ON pm_issues(sprint_id);
CREATE INDEX idx_transitions_issue ON pm_transitions(issue_id);
CREATE INDEX idx_evidence_issue ON pm_evidence_links(issue_id);
CREATE INDEX idx_project_sources_remote_id ON pm_project_sources(remote_project_id);
CREATE INDEX idx_verdicts_issue ON pm_critic_verdicts(issue_id);
CREATE INDEX idx_issues_task_id ON pm_issues(project_id, task_id);
CREATE INDEX idx_issues_planning_ref ON pm_issues(project_id, planning_reference);
CREATE TRIGGER trg_prevent_evidence_update
                BEFORE UPDATE ON pm_evidence_links
                BEGIN
                    SELECT RAISE(ABORT, 'TamperViolationError: Evidence records are immutable and cannot be updated.');
                END;
CREATE TRIGGER trg_prevent_evidence_delete
                BEFORE DELETE ON pm_evidence_links
                BEGIN
                    SELECT RAISE(ABORT, 'TamperViolationError: Evidence records are immutable and cannot be deleted.');
                END;
CREATE TRIGGER trg_prevent_self_review
                BEFORE INSERT ON pm_critic_verdicts
                BEGIN
                SELECT CASE
                        WHEN NEW.reviewer_principal = (SELECT assignee_principal FROM pm_issues WHERE id = NEW.issue_id)
                        THEN RAISE(ABORT, 'SeparationOfDutiesViolation: Issue assignee cannot record a review verdict on their own work.')
                    END;
                END;
CREATE INDEX idx_task_mappings_legacy ON pm_task_mappings(legacy_task_id);
CREATE UNIQUE INDEX uq_coord_mapping_identity
                ON pm_task_mappings(project_id, task_id, local_issue_id);
CREATE UNIQUE INDEX uq_coord_issue_project
                ON pm_issues(project_id, id);
CREATE INDEX idx_coord_attempts_issue ON pm_coordinator_attempts(issue_id);
CREATE INDEX idx_coord_attempts_task ON pm_coordinator_attempts(task_id);
CREATE INDEX idx_coord_intents_status ON pm_coordinator_intents(status, lease_expires_at);
CREATE INDEX idx_coord_intents_task ON pm_coordinator_intents(task_id);
CREATE INDEX idx_coord_runs_attempt ON pm_coordinator_runs(attempt_id);
CREATE INDEX idx_coord_runs_intent ON pm_coordinator_runs(intent_id);
CREATE INDEX idx_coord_events_run ON pm_coordinator_events(run_id, cursor_seq);
CREATE INDEX idx_coord_evidence_issue ON pm_coordinator_evidence_receipts(issue_id);
CREATE INDEX idx_coord_reservations_project ON pm_coordinator_reservations(project_id, status);
CREATE INDEX idx_coord_reservations_attempt ON pm_coordinator_reservations(attempt_id);
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('pm_coordinator_events',1);
COMMIT;
