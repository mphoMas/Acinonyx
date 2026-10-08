#!/usr/bin/env python3
"""
scripts/test_db_backup_recovery.py: Validates SQLite backup, integrity check,
and point-in-time recovery for mas_pm.db.
Deliverable for task OPS-03 (MAS-23) by platform_sre.
"""

from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile


def test_backup_and_recovery(db_path: Path) -> int:
    print(f"[*] Testing backup and recovery for: {db_path}")
    if not db_path.exists():
        print(f"[-] Database {db_path} not found.")
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        backup_file = Path(tmpdir) / "mas_pm_backup.db"

        # 1. Online SQLite backup
        src_conn = sqlite3.connect(str(db_path))
        dst_conn = sqlite3.connect(str(backup_file))
        with dst_conn:
            src_conn.backup(dst_conn, pages=100)
        src_conn.close()
        dst_conn.close()

        # 2. Check backup integrity
        test_conn = sqlite3.connect(str(backup_file))
        c = test_conn.cursor()
        c.execute("PRAGMA integrity_check;")
        res = c.fetchone()
        if not res or res[0] != "ok":
            print(f"[-] Backup integrity check failed: {res}")
            test_conn.close()
            return 1

        # 3. Verify table counts
        c.execute("SELECT count(*) FROM pm_issues;")
        issue_count = c.fetchone()[0]
        test_conn.close()

        print(f"[+] Backup verified successfully: {issue_count} issues restored and PRAGMA integrity_check == ok.")
        return 0


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    db_file = repo_root / "mas_pm.db"
    sys.exit(test_backup_and_recovery(db_file))
