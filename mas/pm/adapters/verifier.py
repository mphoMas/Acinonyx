"""Candidate-bound verification with host-owned expectations and strict signed results.

Supported contract: a Git-owned Python solve(payload) function evaluated in the
existing no-egress Docker worker. Arbitrary shell/pytest stdout is not evidence.
Repository-wide test runners and provider-connected review need separate qualification.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mas.pm.adapters.boundary import ContainerBoundary, finite_timeout
from mas.swarm.contracts import CandidateError, Limits, SwarmError, canonical, cases_contract, digest, strict_json
from mas.swarm.process import run_process
from mas.swarm.worker import DockerWorker

MIN_SECRET_LENGTH = 32
SCHEMA = 'mas-coordinator-evidence-v1'
BINDING_FIELDS = {'tenant_id', 'project_id', 'issue_id', 'task_id', 'attempt_id', 'run_id',
                  'candidate_commit_sha', 'base_commit_sha', 'policy_version', 'fencing_token',
                  'suite_digest', 'worker_image', 'developer_principal_id'}


def canonical_payload_json(data: Any) -> str:
    return canonical(data)


def sign_payload(payload, secret_bytes):
    if not isinstance(secret_bytes, bytes) or len(secret_bytes) < MIN_SECRET_LENGTH:
        raise ValueError('Signing key must be at least 32 bytes')
    return hmac.new(secret_bytes, canonical(payload).encode(), hashlib.sha256).hexdigest()


def verify_signature(payload, signature, secret_bytes):
    if not isinstance(signature, str) or not re.fullmatch('[0-9a-f]{64}', signature):
        return False
    try:
        return hmac.compare_digest(sign_payload(payload, secret_bytes), signature)
    except (ValueError, SwarmError):
        return False


def resolve_commit(repo: Path, sha: str) -> str:
    if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{40}', sha):
        raise ValueError('Exact immutable 40-character commit SHA required')
    code, out, _ = asyncio.run(run_process(['git', '-C', str(repo), 'rev-parse', '--verify', sha+'^{commit}'],
                                         timeout=10, output_limit=1024))
    if code or out.decode().strip() != sha:
        raise ValueError('Commit does not exist in authorized repository')
    return sha


@dataclass(frozen=True)
class VerificationContract:
    """Trusted operator configuration; immutable copy of expected results stays on host."""
    source_path: str
    cases_json: str
    worker_image: str

    def __post_init__(self):
        path = Path(self.source_path)
        if path.is_absolute() or '..' in path.parts or not self.source_path.endswith('.py'):
            raise ValueError('Invalid contract source path')
        validated = cases_contract(strict_json(self.cases_json), Limits())
        object.__setattr__(self, 'cases_json', canonical(validated))
        ContainerBoundary(self.worker_image)

    @property
    def suite_digest(self):
        return digest({'source_path': self.source_path, 'cases': strict_json(self.cases_json)})


def evidence_binding(**values):
    if set(values) != BINDING_FIELDS:
        raise ValueError('Incomplete evidence binding')
    for key, value in values.items():
        if key in {'policy_version', 'fencing_token'}:
            if type(value) is not int or value <= 0:
                raise ValueError('Invalid policy or generation')
        elif not isinstance(value, str) or not value.strip() or len(value) > 256:
            raise ValueError('Invalid evidence identity')
    for field in ('candidate_commit_sha', 'base_commit_sha'):
        if not re.fullmatch('[0-9a-f]{40}', values[field]):
            raise ValueError('Exact immutable commit required')
    if not re.fullmatch('[0-9a-f]{64}', values['suite_digest']):
        raise ValueError('Invalid suite digest')
    ContainerBoundary(values['worker_image'])
    return values


def signed_envelope(binding, role, issuer, key_id, secret, domain, result):
    import secrets
    payload = {'schema': SCHEMA, 'domain': domain, 'type': role, **binding,
               'issuer_id': issuer, 'key_id': key_id, 'nonce': secrets.token_hex(32), 'result': result}
    return {'evidence_id': 'ev-'+secrets.token_hex(16),
            **{key: binding[key] for key in ('issue_id', 'task_id', 'attempt_id', 'run_id', 'candidate_commit_sha')},
            'nonce': payload['nonce'], 'key_id': key_id, 'signature': sign_payload(payload, secret),
            'canonical_payload': payload}


class VerifierAdapter:
    def __init__(self, verifier_id, key_id, signing_secret, repo_root=None, is_test_domain=False,
                 contract: VerificationContract | None = None):
        sign_payload({}, signing_secret)
        if not verifier_id or not key_id or type(is_test_domain) is not bool:
            raise ValueError('Explicit verifier identity/key/domain required')
        self.verifier_id, self.key_id, self._secret = verifier_id, key_id, signing_secret
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.contract, self.is_test_domain = contract, is_test_domain

    def verify_candidate(self, tenant_id, project_id, issue_id, task_id, attempt_id, run_id,
                         candidate_commit_sha, base_commit_sha, test_command=None, timeout_seconds=30,
                         developer_principal_id=None, policy_version=1, fencing_token=1):
        if not developer_principal_id or developer_principal_id == self.verifier_id:
            raise PermissionError('Distinct durable builder identity required; builder cannot verify own candidate')
        if test_command is not None:
            raise PermissionError('Arbitrary commands and stdout summaries are not trusted test evidence')
        if self.contract is None:
            raise PermissionError('Owner-controlled verification contract required')
        timeout = finite_timeout(timeout_seconds, 30)
        resolve_commit(self.repo_root, candidate_commit_sha)
        resolve_commit(self.repo_root, base_commit_sha)
        # Git tree mode check prevents symlink source substitution.
        code, raw, _ = asyncio.run(run_process(['git', '-C', str(self.repo_root), 'ls-tree', candidate_commit_sha,
                                              '--', self.contract.source_path], timeout=10, output_limit=2048))
        if code or not raw.startswith(b'100644 blob ') and not raw.startswith(b'100755 blob '):
            raise ValueError('Candidate source must be a regular Git blob')
        code, source, _ = asyncio.run(run_process(['git', '-C', str(self.repo_root), 'show',
            candidate_commit_sha+':'+self.contract.source_path], timeout=10, output_limit=8192))
        if code:
            raise ValueError('Candidate source unavailable')
        binding = evidence_binding(tenant_id=tenant_id, project_id=project_id, issue_id=issue_id,
            task_id=task_id, attempt_id=attempt_id, run_id=run_id, candidate_commit_sha=candidate_commit_sha,
            base_commit_sha=base_commit_sha, policy_version=policy_version, fencing_token=fencing_token,
            suite_digest=self.contract.suite_digest, worker_image=self.contract.worker_image,
            developer_principal_id=developer_principal_id)
        async def evaluate():
            limits = Limits(worker_seconds=min(timeout, 5))
            worker = DockerWorker(self.contract.worker_image, limits)
            await worker.check()
            outcomes = []
            for case in strict_json(self.contract.cases_json):
                try:
                    actual = await worker.evaluate(source.decode('utf-8'), case['input'], run_id)
                    passed = canonical(actual) == canonical(case['expected'])
                except CandidateError:
                    passed = False
                outcomes.append({'id': case['id'], 'passed': passed})
            return outcomes
        async def bounded_evaluate():
            return await asyncio.wait_for(evaluate(), timeout)
        outcomes = asyncio.run(bounded_evaluate())
        result = {'passed': all(item['passed'] for item in outcomes),
                  'test_count': len(outcomes), 'outcomes': outcomes}
        return signed_envelope(binding, 'VERIFICATION_EVIDENCE', self.verifier_id, self.key_id,
                               self._secret, 'TEST' if self.is_test_domain else 'PRODUCTION', result)


class CodexReviewerAdapter:
    def __init__(self, reviewer_id, key_id, signing_secret, *, image, binary_path='/usr/local/bin/codex',
                 repo_root=None, is_test_domain=False):
        sign_payload({}, signing_secret)
        if not reviewer_id or not key_id or type(is_test_domain) is not bool:
            raise ValueError('Explicit reviewer identity/key/domain required')
        self.reviewer_id, self.key_id, self._secret = reviewer_id, key_id, signing_secret
        self.boundary = ContainerBoundary(image)
        self.binary_path = binary_path
        self.repo_root = (repo_root or Path.cwd()).resolve()
        self.is_test_domain = is_test_domain

    @staticmethod
    def parse_final(raw, binding):
        # One strict final object only. JSON event streams, quoted approvals, conflicting
        # verdicts and textual suffixes cannot approve a candidate.
        payload = strict_json(raw)
        if not isinstance(payload, dict) or set(payload) != {'schema', 'binding', 'verdict', 'comments'}:
            raise ValueError('Invalid final reviewer schema')
        if payload['schema'] != 'mas-review-v1' or evidence_binding(**payload['binding']) != binding:
            raise ValueError('Reviewer result does not match candidate contract')
        if payload['verdict'] not in {'APPROVED', 'REJECTED'} or not isinstance(payload['comments'], str) or len(payload['comments']) > 8192:
            raise ValueError('Invalid reviewer verdict')
        return {'verdict': payload['verdict'], 'comments': payload['comments']}

    def review_candidate(self, *, binding, timeout_seconds=30):
        binding = evidence_binding(**binding)
        if binding['developer_principal_id'] == self.reviewer_id:
            raise PermissionError('Builder cannot review own candidate')
        resolve_commit(self.repo_root, binding['candidate_commit_sha'])
        resolve_commit(self.repo_root, binding['base_commit_sha'])
        # Immutable diff is data inside the container; no repository/home/socket mounts.
        code, diff, _ = asyncio.run(run_process(['git', '-C', str(self.repo_root), 'diff',
            binding['base_commit_sha'], binding['candidate_commit_sha'], '--'], timeout=10, output_limit=32768))
        if code:
            raise ValueError('Review diff unavailable')
        prompt = canonical({'required_schema': 'mas-review-v1', 'binding': binding, 'diff': diff.decode('utf-8')})
        code, out, _ = self.boundary.run([self.binary_path, 'exec', prompt], timeout=timeout_seconds)
        if code:
            raise SwarmError('Reviewer execution failed')
        result = self.parse_final(out, binding)
        return signed_envelope(binding, 'REVIEW_EVIDENCE', self.reviewer_id, self.key_id,
            self._secret, 'TEST' if self.is_test_domain else 'PRODUCTION', result)
