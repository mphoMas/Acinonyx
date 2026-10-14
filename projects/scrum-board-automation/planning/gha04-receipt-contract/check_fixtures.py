"""Executable reference fixtures, NOT an application or runtime acceptance suite.

Checks proposed SQLite ownership/immutability and identity/transaction examples.
No imports of MAS, external calls, migrations or production writes.
Run: python3 .../check_fixtures.py
Antigravity must separately implement supported-service and real process-kill tests.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

SCHEMA = Path(__file__).with_name("proposed_schema.sql").read_text()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def contract():
    return {"schema_version": 1, "claims": {"candidate_sha": "a" * 40,
            "base_sha": "b" * 40, "suite_digest": "c" * 64, "policy_version": 1,
            "brief_version": 1, "source_generation": None}, "check_ids": ["test-a"]}


def observation(outcome="PASSED"):
    return {"schema_version": 1, "transport_claims": {"repository_id": "100",
            "github_run_id": "200", "github_run_attempt": 1},
            "mas_claims": {"run_id": "run1", "intent_id": "intent1", "attempt_id": "attempt1", "fence": 2},
            "items": [{"check_id": "test-a", "claimed_outcome": outcome}],
            "artifact_claims": [], "limitations": "No independently verified evidence"}


def store_example(conn, tenant, action_id, observation_id, action, payload):
    """Reference SQL flow only. Deliberately has no authentication/runtime API."""
    owner = (tenant, "p", "i")
    action_hash, payload_hash = digest(action), digest(payload)
    conn.execute("BEGIN IMMEDIATE")
    try:
        prior = conn.execute("SELECT contract_digest FROM proposed_actions WHERE tenant_id=? AND project_id=? AND issue_id=? AND action_id=?", (*owner, action_id)).fetchone()
        if prior and prior[0] != action_hash:
            raise ValueError("ACTION_CONTRACT_CONFLICT")
        existing = conn.execute("SELECT receipt_id,payload_digest FROM proposed_receipts WHERE tenant_id=? AND project_id=? AND issue_id=? AND action_id=? AND observation_id=?", (*owner, action_id, observation_id)).fetchone()
        if existing:
            if existing[1] != payload_hash:
                raise ValueError("OBSERVATION_CONFLICT")
            conn.rollback()
            return existing[0], "EXISTING"
        if not prior:
            conn.execute("INSERT INTO proposed_actions VALUES(?,?,?,?,?,?)", (*owner, action_id, action_hash, canonical(action)))
        receipt = "rcpt_" + digest({"owner": owner, "action_id": action_id, "observation_id": observation_id, "payload_digest": payload_hash})
        conn.execute("INSERT INTO proposed_receipts VALUES(?,?,?,?,?,?,?,?,?,0)", (receipt, *owner, action_id, observation_id, payload_hash, canonical(payload), "fixture-time"))
        for item in payload["items"]:
            conn.execute("INSERT INTO proposed_items VALUES(?,?,?,?,?,?)", (receipt, *owner, item["check_id"], item["claimed_outcome"]))
        conn.commit()
        return receipt, "CREATED"
    except BaseException:
        conn.rollback()
        raise


class ContractFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "fixture.db"
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.executescript(SCHEMA)
        self.conn.executemany("INSERT INTO fixture_tasks VALUES(?,?,?)", [("A", "p", "i"), ("B", "p", "i")])

    def tearDown(self):
        self.conn.close()
        self.temp.cleanup()

    def test_duplicate_observation_recovers_receipt_after_reopen(self):
        first = store_example(self.conn, "A", "action1", "obs1", contract(), observation())
        self.conn.close()
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.execute("PRAGMA foreign_keys=ON")
        second = store_example(self.conn, "A", "action1", "obs1", contract(), observation())
        self.assertEqual(first[0], second[0])
        self.assertEqual(second[1], "EXISTING")
        self.assertEqual(self.conn.execute("SELECT count(*) FROM proposed_receipts").fetchone()[0], 1)

    def test_same_observation_conflict_preserves_existing_content(self):
        store_example(self.conn, "A", "action1", "obs1", contract(), observation())
        with self.assertRaisesRegex(ValueError, "OBSERVATION_CONFLICT"):
            store_example(self.conn, "A", "action1", "obs1", contract(), observation("FAILED"))
        self.assertEqual(self.conn.execute("SELECT claimed_outcome FROM proposed_items").fetchone()[0], "PASSED")

    def test_new_attempt_can_report_different_outcome(self):
        first = store_example(self.conn, "A", "action1", "obs1", contract(), observation())
        payload = observation("FAILED")
        payload["transport_claims"]["github_run_attempt"] = 2
        second = store_example(self.conn, "A", "action1", "obs2", contract(), payload)
        self.assertNotEqual(first[0], second[0])
        self.assertEqual(self.conn.execute("SELECT count(*) FROM proposed_actions").fetchone()[0], 1)

    def test_changed_contract_requires_new_action(self):
        store_example(self.conn, "A", "action1", "obs1", contract(), observation())
        changed = contract()
        changed["claims"]["candidate_sha"] = "d" * 40
        with self.assertRaisesRegex(ValueError, "ACTION_CONTRACT_CONFLICT"):
            store_example(self.conn, "A", "action1", "obs2", changed, observation())
        self.assertEqual(self.conn.execute("SELECT count(*) FROM proposed_receipts").fetchone()[0], 1)

    def test_other_tenant_item_cannot_reference_receipt(self):
        receipt, _ = store_example(self.conn, "A", "action1", "obs1", contract(), observation())
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO proposed_items VALUES(?,?,?,?,?,?)", (receipt, "B", "p", "i", "test-b", "PASSED"))

    def test_immutable_untrusted_content(self):
        store_example(self.conn, "A", "action1", "obs1", contract(), observation())
        for table in ["proposed_actions", "proposed_receipts", "proposed_items"]:
            with self.assertRaises(sqlite3.IntegrityError):
                self.conn.execute(f"DELETE FROM {table}")
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE proposed_receipts SET authority_verified=1")

    def test_item_failure_rolls_back_action_and_receipt(self):
        bad = observation("UNKNOWN")
        with self.assertRaises(sqlite3.IntegrityError):
            store_example(self.conn, "A", "action1", "obs1", contract(), bad)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM proposed_actions").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM proposed_receipts").fetchone()[0], 0)

    def test_canonical_order_and_nonfinite(self):
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))
        with self.assertRaises(ValueError):
            digest({"bad": float("nan")})


if __name__ == "__main__":
    unittest.main(verbosity=2)
