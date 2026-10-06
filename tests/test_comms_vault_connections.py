"""Regression tests: CommsVault connections are committed and always closed."""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from mas.memory.comms_vault import CommsVault


class TestCommsVaultConnections(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = CommsVault(db_path=Path(self.tmp.name) / "vault.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_connection_closed_after_with_block(self):
        with self.vault.get_connection() as conn:
            conn.execute("SELECT 1")
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_connection_closed_when_body_raises(self):
        with self.assertRaises(RuntimeError):
            with self.vault.get_connection() as conn:
                raise RuntimeError("boom")
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")

    def test_writes_are_committed_and_rolled_back(self):
        with self.vault.get_connection() as conn:
            conn.execute("CREATE TABLE t (v INTEGER)")
            conn.execute("INSERT INTO t VALUES (1)")
        with self.assertRaises(RuntimeError):
            with self.vault.get_connection() as conn:
                conn.execute("INSERT INTO t VALUES (2)")
                raise RuntimeError("rollback")
        with self.vault.get_connection() as conn:
            rows = [r[0] for r in conn.execute("SELECT v FROM t")]
        self.assertEqual(rows, [1])

    def test_database_file_created(self):
        self.assertTrue(os.path.exists(self.vault.db_path))


if __name__ == "__main__":
    unittest.main()
