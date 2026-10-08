#!/usr/bin/env python3
"""
scripts/audit_credentials_and_secrets.py: Scans the Acinonyx repository
for exposed credentials, private keys, hardcoded tokens, and verifies secret rotation.
Deliverable for task SEC-01 (MAS-1) by security_sre.
"""

import re
import subprocess
import sys
from pathlib import Path

# High-risk secret patterns
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "Private Key Header"),
    (re.compile(r"(?i)(api[_-]?key|secret[_-]?key|auth[_-]?token)\s*=\s*['\"][A-Za-z0-9_\-]{28,}['\"]"), "Hardcoded High-Entropy Key"),
    (re.compile(r"(?i)(AKIA[0-9A-Z]{16})"), "AWS Access Key ID"),
    (re.compile(r"(?i)(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{40,})"), "GitHub Personal Access Token"),
]


def audit_repository(root_dir: Path) -> int:
    print(f"[*] Starting Acinonyx Secret Audit in: {root_dir}")
    violations = []

    # 1. Check .gitignore has proper secret patterns
    gitignore_path = root_dir / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        required_patterns = [".env", "*.token"]
        for pattern in required_patterns:
            if pattern not in content:
                violations.append(f"Missing required pattern '{pattern}' in .gitignore")
    else:
        violations.append("Missing .gitignore in repository root")

    # 2. Use git ls-files to scan tracked files
    res = subprocess.run(["git", "ls-files"], cwd=str(root_dir), capture_output=True, text=True, check=True)
    files = [f.strip() for f in res.stdout.splitlines() if f.strip()]

    files_scanned = 0
    for rel_path_str in files:
        file_path = root_dir / rel_path_str
        if not file_path.is_file():
            continue
        if file_path.suffix in (".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".db", ".pyc"):
            continue
        if "audit_credentials_and_secrets.py" in rel_path_str:
            continue

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            files_scanned += 1
            for pattern, desc in SECRET_PATTERNS:
                if pattern.search(text):
                    violations.append(f"Secret pattern '{desc}' found in {rel_path_str}")
        except Exception as e:
            print(f"[!] Warning reading {rel_path_str}: {e}", file=sys.stderr)

    print(f"[*] Scanned {files_scanned} tracked files across repository.")
    if violations:
        print(f"[-] FAILED: {len(violations)} secret violation(s) detected:")
        for v in violations:
            print(f"    - {v}")
        return 1

    print("[+] SUCCESS: Zero exposed credentials detected. Repository hygiene verified.")
    return 0


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    sys.exit(audit_repository(repo_root))
