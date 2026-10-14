-- DESIGN FIXTURE ONLY. Not a production migration or runtime schema.
-- Fixture-owned parents model existing immutable tenant/project/issue ownership.
PRAGMA foreign_keys=ON;
CREATE TABLE fixture_tasks (
 tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL,
 PRIMARY KEY(tenant_id,project_id,issue_id)
);
CREATE TABLE proposed_actions (
 tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL,
 action_id TEXT NOT NULL, contract_digest TEXT NOT NULL CHECK(length(contract_digest)=64),
 contract_json TEXT NOT NULL,
 PRIMARY KEY(tenant_id,project_id,issue_id,action_id),
 FOREIGN KEY(tenant_id,project_id,issue_id) REFERENCES fixture_tasks(tenant_id,project_id,issue_id)
);
CREATE TABLE proposed_receipts (
 receipt_id TEXT NOT NULL PRIMARY KEY CHECK(length(receipt_id)=69 AND substr(receipt_id,1,5)='rcpt_' AND substr(receipt_id,6) NOT GLOB '*[^0-9a-f]*'),
 tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL,
 action_id TEXT NOT NULL, observation_id TEXT NOT NULL,
 payload_digest TEXT NOT NULL CHECK(length(payload_digest)=64),
 payload_json TEXT NOT NULL, admitted_at TEXT NOT NULL,
 authority_verified INTEGER NOT NULL DEFAULT 0 CHECK(authority_verified=0),
 UNIQUE(tenant_id,project_id,issue_id,action_id,observation_id),
 UNIQUE(receipt_id,tenant_id,project_id,issue_id),
 FOREIGN KEY(tenant_id,project_id,issue_id,action_id)
 REFERENCES proposed_actions(tenant_id,project_id,issue_id,action_id)
);
CREATE TABLE proposed_items (
 receipt_id TEXT NOT NULL, tenant_id TEXT NOT NULL, project_id TEXT NOT NULL, issue_id TEXT NOT NULL,
 check_id TEXT NOT NULL, claimed_outcome TEXT NOT NULL CHECK(claimed_outcome IN ('PASSED','FAILED','SKIPPED','UNAVAILABLE')),
 PRIMARY KEY(receipt_id,check_id),
 FOREIGN KEY(receipt_id,tenant_id,project_id,issue_id)
 REFERENCES proposed_receipts(receipt_id,tenant_id,project_id,issue_id)
);
CREATE TRIGGER actions_no_update BEFORE UPDATE ON proposed_actions BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER actions_no_delete BEFORE DELETE ON proposed_actions BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER receipts_no_update BEFORE UPDATE ON proposed_receipts BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER receipts_no_delete BEFORE DELETE ON proposed_receipts BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER items_no_update BEFORE UPDATE ON proposed_items BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER items_no_delete BEFORE DELETE ON proposed_items BEGIN SELECT RAISE(ABORT,'immutable'); END;

-- REPLACE implicitly deletes without delete triggers when recursive_triggers=OFF.
-- Refuse any insertion that conflicts with immutable logical or physical identity.
CREATE TRIGGER actions_no_replace BEFORE INSERT ON proposed_actions
WHEN EXISTS(SELECT 1 FROM proposed_actions WHERE tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND issue_id=NEW.issue_id AND action_id=NEW.action_id)
BEGIN SELECT RAISE(ABORT,'immutable: existing action'); END;
CREATE TRIGGER receipts_no_replace BEFORE INSERT ON proposed_receipts
WHEN EXISTS(SELECT 1 FROM proposed_receipts WHERE receipt_id=NEW.receipt_id OR (tenant_id=NEW.tenant_id AND project_id=NEW.project_id AND issue_id=NEW.issue_id AND action_id=NEW.action_id AND observation_id=NEW.observation_id))
BEGIN SELECT RAISE(ABORT,'immutable: existing receipt'); END;
CREATE TRIGGER items_no_replace BEFORE INSERT ON proposed_items
WHEN EXISTS(SELECT 1 FROM proposed_items WHERE receipt_id=NEW.receipt_id AND check_id=NEW.check_id)
BEGIN SELECT RAISE(ABORT,'immutable: existing item'); END;
