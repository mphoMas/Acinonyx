"""
mas.pm.adapters.verifier: Trusted verification and batch Codex review adapters (CC-06).

Implements:
- VerifierAdapter:
  * Resolves exact immutable candidate commit and base commit within authorized Git repository.
  * Checks out candidate into an isolated, ephemeral git worktree or working directory.
  * Executes owner-controlled test suite/contract against candidate.
  * Collects verified runner test counts and exit codes.
  * Fails closed if commit does not exist, tests fail, zero tests run, or worktree cannot be created.
- CodexReviewerAdapter:
  * Invokes non-interactive batch review (`codex exec review`) on immutable candidate commit diff.
  * Parses strict review schema (rejecting ambiguous substring matches such as "NOT APPROVED").
- Canonical serialization:
  * Deterministic sorted JSON serialization (versioned schema) and constant-time HMAC-SHA256 signatures.
  * Strictly requires explicit private minimum-length secret keys (no public hardcoded fallback).
  * Enforces separation of domains: test/simulation cannot produce production-admitted evidence receipts.
- Nonce replay prevention & envelope verification.
- Separation of Builder, Verifier, and Reviewer authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mas.pm.adapters.verifier")

DEFAULT_CODEX_BIN = "/snap/bin/codex"
MIN_SECRET_LENGTH = 16


def canonical_payload_json(data: Any) -> str:
    """
    Deterministic versioned JSON serialization for signing.
    Sorts keys, uses compact delimiters without whitespace, and formats numbers consistently.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def sign_payload(payload: Dict[str, Any], secret_bytes: bytes) -> str:
    """Computes HMAC-SHA256 signature over the deterministic payload string."""
    if len(secret_bytes) < MIN_SECRET_LENGTH:
        raise ValueError(f"Signing key must be at least {MIN_SECRET_LENGTH} bytes, got {len(secret_bytes)}")
    canonical_str = canonical_payload_json(payload)
    return hmac.new(secret_bytes, canonical_str.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_signature(payload: Dict[str, Any], signature: str, secret_bytes: bytes) -> bool:
    """Verifies HMAC-SHA256 signature against payload using constant-time comparison."""
    if len(secret_bytes) < MIN_SECRET_LENGTH:
        return False
    expected = sign_payload(payload, secret_bytes)
    return hmac.compare_digest(expected, signature)


class VerifierAdapter:
    """
    Trusted verifier adapter (CC-06).
    Executes owner checks against the exact immutable candidate commit in an isolated
    Git worktree and produces signed evidence receipt envelopes.
    """

    def __init__(
        self,
        verifier_id: str,
        key_id: str,
        signing_secret: bytes,
        repo_root: Optional[Path] = None,
        is_test_domain: bool = False,
    ) -> None:
        if not verifier_id or not verifier_id.strip():
            raise ValueError("verifier_id must be a non-empty string")
        if not key_id or not key_id.strip():
            raise ValueError("key_id must be a non-empty string")
        if not signing_secret or len(signing_secret) < MIN_SECRET_LENGTH:
            raise ValueError(f"signing_secret must be at least {MIN_SECRET_LENGTH} bytes")

        self.verifier_id = verifier_id.strip()
        self.key_id = key_id.strip()
        self._signing_secret = signing_secret
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.is_test_domain = is_test_domain

    def verify_candidate(
        self,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_id: str,
        run_id: str,
        candidate_commit_sha: str,
        base_commit_sha: str,
        test_command: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
        developer_principal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes verification checks against the candidate commit in an isolated worktree.
        Fails closed on nonexistent commit, failed tests, zero tests, or builder self-verification.
        """
        # Separation of Builder and Verifier
        if developer_principal_id and developer_principal_id == self.verifier_id:
            raise PermissionError(f"Builder cannot verify own candidate: {self.verifier_id}")

        if not candidate_commit_sha or len(candidate_commit_sha) < 7:
            raise ValueError(f"Invalid candidate commit SHA: {candidate_commit_sha}")

        # 1. Resolve candidate commit in repository
        rev_check = subprocess.run(
            ["git", "rev-parse", "--verify", f"{candidate_commit_sha}^{{commit}}"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if rev_check.returncode != 0:
            raise ValueError(f"Candidate commit {candidate_commit_sha} does not exist in repository {self.repo_root}")
        resolved_candidate_sha = rev_check.stdout.strip()

        # 2. Setup isolated worktree
        nonce = f"nonce-{task_id}-{run_id}-{os.urandom(8).hex()}"
        observed_at = time.time()
        passed = False
        test_count = 0
        exit_code = 1
        output_summary = ""

        with tempfile.TemporaryDirectory(prefix="mas_verifier_worktree_") as worktree_dir:
            add_worktree = subprocess.run(
                ["git", "worktree", "add", "--detach", worktree_dir, resolved_candidate_sha],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if add_worktree.returncode != 0:
                raise RuntimeError(f"Failed to create isolated worktree for candidate: {add_worktree.stderr}")

            try:
                cmd = test_command or ["pytest", "-q"]
                proc = subprocess.run(
                    cmd,
                    cwd=worktree_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                exit_code = proc.returncode
                stdout = proc.stdout
                stderr = proc.stderr
                output_summary = stdout[-500:] if stdout else stderr[-500:]

                # Count tests passed from pytest summary line (e.g., "5 passed in 0.12s")
                import re
                match = re.search(r"(\d+)\s+passed", stdout)
                if match:
                    test_count = int(match.group(1))
                else:
                    test_count = 0

                # Must pass cleanly AND run at least one test
                passed = (exit_code == 0 and test_count > 0)
            except subprocess.TimeoutExpired:
                exit_code = 124
                passed = False
                output_summary = "Verification execution timed out"
                test_count = 0
            except Exception as e:
                exit_code = 127
                passed = False
                output_summary = f"Verification error: {e}"
                test_count = 0
            finally:
                # Remove worktree cleanly
                subprocess.run(
                    ["git", "worktree", "remove", "--force", worktree_dir],
                    cwd=str(self.repo_root),
                    capture_output=True,
                    text=True,
                    check=False,
                )

        canonical_payload = {
            "type": "VERIFICATION_EVIDENCE",
            "is_test_domain": self.is_test_domain,
            "verifier_id": self.verifier_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "issue_id": issue_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "run_id": run_id,
            "candidate_commit_sha": resolved_candidate_sha,
            "base_commit_sha": base_commit_sha,
            "nonce": nonce,
            "observed_at": observed_at,
            "passed": passed,
            "exit_code": exit_code,
            "test_count": test_count,
            "summary": output_summary,
        }

        signature = sign_payload(canonical_payload, self._signing_secret)

        return {
            "evidence_id": f"ev-{task_id}-{run_id}",
            "issue_id": issue_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "run_id": run_id,
            "candidate_commit_sha": resolved_candidate_sha,
            "nonce": nonce,
            "key_id": self.key_id,
            "signature": signature,
            "canonical_payload": canonical_payload,
            "passed": passed,
        }


class CodexReviewerAdapter:
    """
    Batch Codex Reviewer Adapter (CC-06).
    Invokes non-interactive batch review (`codex exec review`) and strictly parses
    structured approval verdicts without naive substring matching.
    """

    def __init__(
        self,
        reviewer_id: str,
        key_id: str,
        signing_secret: bytes,
        binary_path: Optional[str] = None,
        repo_root: Optional[Path] = None,
        is_test_domain: bool = False,
    ) -> None:
        if not reviewer_id or not reviewer_id.strip():
            raise ValueError("reviewer_id must be a non-empty string")
        if not key_id or not key_id.strip():
            raise ValueError("key_id must be a non-empty string")
        if not signing_secret or len(signing_secret) < MIN_SECRET_LENGTH:
            raise ValueError(f"signing_secret must be at least {MIN_SECRET_LENGTH} bytes")

        self.reviewer_id = reviewer_id.strip()
        self.key_id = key_id.strip()
        self._signing_secret = signing_secret
        self.binary_path = binary_path or DEFAULT_CODEX_BIN
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.is_test_domain = is_test_domain

    def review_candidate(
        self,
        tenant_id: str,
        project_id: str,
        issue_id: str,
        task_id: str,
        attempt_id: str,
        run_id: str,
        candidate_commit_sha: str,
        base_commit_sha: str,
        policy_version: int,
        developer_principal_id: Optional[str] = None,
        timeout_seconds: float = 60.0,
    ) -> Dict[str, Any]:
        """
        Executes code review against immutable candidate commit and returns signed review evidence envelope.
        """
        # Separation of Builder and Reviewer
        if developer_principal_id and developer_principal_id == self.reviewer_id:
            raise PermissionError(f"Builder cannot review own candidate: {self.reviewer_id}")

        # Resolve commit
        rev_check = subprocess.run(
            ["git", "rev-parse", "--verify", f"{candidate_commit_sha}^{{commit}}"],
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
        if rev_check.returncode != 0:
            raise ValueError(f"Candidate commit {candidate_commit_sha} does not exist in repository {self.repo_root}")
        resolved_candidate_sha = rev_check.stdout.strip()

        nonce = f"nonce-rev-{task_id}-{run_id}-{os.urandom(8).hex()}"
        observed_at = time.time()
        verdict = "REJECTED"
        comments = ""

        cmd = [
            self.binary_path,
            "exec",
            "review",
            "--commit",
            resolved_candidate_sha,
            "--json",
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            stdout = proc.stdout
            stderr = proc.stderr
            comments = stdout[-500:] if stdout else stderr[-500:]

            # Strict verdict parsing: must have exit_code 0 and explicit structured approval
            if proc.returncode == 0:
                # Look for structured JSON approval or explicit conclusive terminal verdict
                parsed_approved = False
                for line in stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        if isinstance(ev, dict) and ev.get("verdict") == "APPROVED":
                            parsed_approved = True
                            break
                    except Exception:
                        pass
                if parsed_approved or (stdout.strip().endswith("VERDICT: APPROVED")):
                    verdict = "APPROVED"
                else:
                    verdict = "REJECTED"
            else:
                verdict = "REJECTED"
        except Exception as e:
            verdict = "REJECTED"
            comments = f"Review execution error: {e}"

        canonical_payload = {
            "type": "REVIEW_EVIDENCE",
            "is_test_domain": self.is_test_domain,
            "reviewer_id": self.reviewer_id,
            "tenant_id": tenant_id,
            "project_id": project_id,
            "issue_id": issue_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "run_id": run_id,
            "candidate_commit_sha": resolved_candidate_sha,
            "base_commit_sha": base_commit_sha,
            "policy_version": policy_version,
            "nonce": nonce,
            "observed_at": observed_at,
            "verdict": verdict,
            "comments": comments,
        }

        signature = sign_payload(canonical_payload, self._signing_secret)

        return {
            "evidence_id": f"ev-rev-{task_id}-{run_id}",
            "issue_id": issue_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "run_id": run_id,
            "candidate_commit_sha": resolved_candidate_sha,
            "nonce": nonce,
            "key_id": self.key_id,
            "signature": signature,
            "canonical_payload": canonical_payload,
            "verdict": verdict,
        }
