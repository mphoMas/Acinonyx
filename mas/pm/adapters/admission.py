"""Service-owned evidence trust and durable immutable job contracts.

No environment-key fallback or per-receipt trust override exists. Registry injection
is a trusted service startup operation; the default coordinator admits nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType

from mas.pm.adapters.verifier import BINDING_FIELDS, SCHEMA, evidence_binding, verify_signature
from mas.swarm.contracts import canonical, strict_json


@dataclass(frozen=True)
class IssuerGrant:
    issuer_id: str
    tenant_id: str
    role: str
    secret: bytes = field(repr=False)

    def __post_init__(self):
        if self.role not in {'VERIFICATION_EVIDENCE', 'REVIEW_EVIDENCE'} or not self.issuer_id or not self.tenant_id:
            raise ValueError('Invalid issuer authority')
        if not isinstance(self.secret, bytes) or len(self.secret) < 32:
            raise ValueError('Private issuer key must contain at least 32 bytes')


class EvidenceTrust:
    def __init__(self, grants, *, iam, issuer_tokens):
        if not grants or any(not isinstance(k, str) or not k or not isinstance(v, IssuerGrant) for k, v in grants.items()):
            raise ValueError('Explicit service issuer grants required')
        # A builder cannot be both verifier and reviewer for one tenant/key configuration.
        principals = [(g.tenant_id, g.issuer_id) for g in grants.values()]
        if len({g.secret for g in grants.values()}) != len(grants) or len(set(principals)) != len(principals):
            raise ValueError('Distinct issuer principals required')
        from mas.iam import MultiTenantIAM
        if not isinstance(iam, MultiTenantIAM) or set(issuer_tokens) != set(grants):
            raise ValueError('Every issuer requires platform IAM session authority')
        self.grants = MappingProxyType(dict(grants))
        self._iam = iam
        self._tokens = MappingProxyType(dict(issuer_tokens))

    def _require_issuer(self, key_id):
        grant = self.grants.get(key_id)
        if grant is None:
            raise PermissionError('Untrusted evidence issuer key')
        context = self._iam.verify_token(self._tokens[key_id])
        action = 'coordinator:evidence:verify' if grant.role == 'VERIFICATION_EVIDENCE' else 'coordinator:evidence:review'
        if context.principal_id != grant.issuer_id or context.tenant_id != grant.tenant_id or not self._iam.authorize(
                context, action, grant.tenant_id, f'urn:mas:tenant:{grant.tenant_id}:coordinator:evidence'):
            raise PermissionError('Issuer session or role authority unavailable')
        return grant

    def admit(self, store, evidence_id):
        from mas.pm.coordinator import is_trusted_coord_admin
        from mas.tenancy import current_binding
        store._validate_tenant_authority()
        binding = current_binding()
        if not is_trusted_coord_admin():
            binding.require('coordinator:evidence:admit')
        with store.db.atomic_transaction() as conn:
            return self._admit_in_transaction(store, evidence_id, conn)

    def _admit_in_transaction(self, store, evidence_id, conn):
        row = conn.execute('SELECT * FROM pm_coordinator_evidence_receipts WHERE evidence_id=?', (evidence_id,)).fetchone()
        if not row:
            raise ValueError('Evidence receipt not found')
        grant = self._require_issuer(row['key_id'])
        payload = strict_json(row['canonical_payload'])
        fields = BINDING_FIELDS | {'schema', 'domain', 'type', 'issuer_id', 'key_id', 'nonce', 'result'}
        if not isinstance(payload, dict) or set(payload) != fields:
            raise ValueError('Strict versioned evidence envelope required')
        if payload.get('type') == 'REVIEW_EVIDENCE':
            from mas.pm.delivery import require_review
            require_review(conn, payload.get('issue_id'), payload.get('candidate_commit_sha'))
        if payload['schema'] != SCHEMA or payload['domain'] != 'PRODUCTION' or payload['type'] != grant.role:
            raise PermissionError('Unknown or untrusted evidence schema/domain/role')
        if payload['issuer_id'] != grant.issuer_id or payload['tenant_id'] != grant.tenant_id or payload['key_id'] != row['key_id']:
            raise PermissionError('Issuer authority does not match envelope')
        if not verify_signature(payload, row['signature'], grant.secret):
            raise PermissionError('Invalid evidence signature')
        expected_binding = evidence_binding(**{k: payload[k] for k in BINDING_FIELDS})
        store._validate_tenant_authority(payload['tenant_id'])
        for key in ('issue_id', 'task_id', 'attempt_id', 'run_id', 'candidate_commit_sha', 'nonce'):
            if payload[key] != row[key]:
                raise ValueError('Receipt envelope mismatch')
        contract = conn.execute('SELECT manifest FROM pm_coordinator_evidence_contracts WHERE run_id=?', (payload['run_id'],)).fetchone()
        if not contract:
            raise PermissionError('Missing owner-controlled evidence contract')
        manifest = strict_json(contract['manifest'])
        if manifest['binding'] != expected_binding:
            raise ValueError('Evidence does not match immutable job contract')
        if grant.issuer_id != manifest['verifier_id' if grant.role == 'VERIFICATION_EVIDENCE' else 'reviewer_id']:
            raise PermissionError('Issuer is not assigned to this verification job')
        if payload['developer_principal_id'] in {manifest['verifier_id'], manifest['reviewer_id']} or manifest['verifier_id'] == manifest['reviewer_id']:
            raise PermissionError('Builder/verifier/reviewer separation violated')
        current = conn.execute('''SELECT a.tenant_id,a.project_id,a.issue_id,a.task_id,a.candidate_commit_sha,
            a.status AS attempt_status,r.status AS run_status,r.exit_code,r.fencing_token AS run_fence,
            i.status AS intent_status,i.fencing_token AS intent_fence,q.policy_version,q.has_pending_reconciliation
            FROM pm_coordinator_runs r JOIN pm_coordinator_attempts a ON a.attempt_id=r.attempt_id
            JOIN pm_coordinator_intents i ON i.intent_id=r.intent_id AND i.attempt_id=a.attempt_id
            JOIN pm_issues q ON q.id=a.issue_id AND q.project_id=a.project_id WHERE r.run_id=? AND a.attempt_id=?''',
            (payload['run_id'], payload['attempt_id'])).fetchone()
        if not current:
            raise ValueError('Run/attempt ownership unavailable')
        if any(current[k] != payload[k] for k in ('tenant_id', 'project_id', 'issue_id', 'task_id', 'candidate_commit_sha', 'policy_version')):
            raise ValueError('Current ownership, candidate or policy mismatch')
        if current['run_fence'] != payload['fencing_token'] or current['intent_fence'] != payload['fencing_token'] or current['has_pending_reconciliation']:
            raise ValueError('Stale generation or pending reconciliation')
        if current['attempt_status'] != 'SUCCEEDED' or current['run_status'] != 'EXITED' or current['exit_code'] != 0 or current['intent_status'] != 'COMPLETED':
            raise ValueError('Execution is not confirmed successful')
        result = payload['result']
        if grant.role == 'VERIFICATION_EVIDENCE':
            if not isinstance(result, dict) or set(result) != {'passed', 'test_count', 'outcomes'}:
                raise ValueError('Invalid verification result schema')
            outcomes = result['outcomes']
            if result['passed'] is not True or type(result['test_count']) is not int or result['test_count'] != len(manifest['case_ids']):
                raise ValueError('Failed, zero or unmeasured tests')
            if not isinstance(outcomes, list) or len(outcomes) != len(manifest['case_ids']):
                raise ValueError('Incomplete measured outcomes')
            if any(not isinstance(item, dict) or set(item) != {'id', 'passed'} or item['passed'] is not True for item in outcomes):
                raise ValueError('Failed or malformed measured outcomes')
            if [item['id'] for item in outcomes] != manifest['case_ids']:
                raise ValueError('Measured suite does not match owner contract')
        else:
            if not isinstance(result, dict) or set(result) != {'verdict', 'comments'} or result['verdict'] != 'APPROVED' or not isinstance(result['comments'], str) or len(result['comments']) > 8192:
                raise ValueError('Rejected or malformed review result')
            # A review cannot approve without a current admitted verifier receipt.
            verifications = conn.execute('SELECT canonical_payload,signature FROM pm_coordinator_evidence_receipts WHERE run_id=? AND admission_status=\'ADMITTED\'', (payload['run_id'],)).fetchall()
            verified = False
            for v in verifications:
                p = strict_json(v['canonical_payload'])
                if p.get('type') != 'VERIFICATION_EVIDENCE' or p.get('issuer_id') != manifest['verifier_id']:
                    continue
                verification_grant = self._require_issuer(p.get('key_id'))
                if verification_grant.role == 'VERIFICATION_EVIDENCE' and verify_signature(p, v['signature'],
                        verification_grant.secret) and p.get('schema') == SCHEMA and p.get('domain') == 'PRODUCTION' and p.get('tenant_id') == verification_grant.tenant_id and {k: p.get(k) for k in BINDING_FIELDS} == expected_binding:
                    r = p.get('result')
                    if isinstance(r, dict) and set(r) == {'passed', 'test_count', 'outcomes'} and r['passed'] is True and type(r['test_count']) is int and r['test_count'] == len(manifest['case_ids']):
                        outcomes = r['outcomes']
                        verified = isinstance(outcomes, list) and len(outcomes) == len(manifest['case_ids']) and all(
                            isinstance(item, dict) and set(item) == {'id', 'passed'} and item['passed'] is True and item['id'] == expected
                            for item, expected in zip(outcomes, manifest['case_ids']))
                        if verified:
                            break
            if not verified:
                raise PermissionError('Current independently verified evidence required before review admission')
        conn.execute("UPDATE pm_coordinator_evidence_receipts SET admission_status='ADMITTED' WHERE evidence_id=?", (evidence_id,))
        return True


def register_contract(store, binding, verifier_id, reviewer_id, case_ids):
    from mas.pm.coordinator import is_trusted_coord_admin
    store._validate_tenant_authority(binding.get('tenant_id'))
    if not is_trusted_coord_admin():
        raise PermissionError('Evidence job configuration requires trusted service administrator')
    binding = evidence_binding(**binding)
    if not isinstance(verifier_id, str) or not verifier_id or not isinstance(reviewer_id, str) or not reviewer_id or len({verifier_id, reviewer_id, binding['developer_principal_id']}) != 3:
        raise ValueError('Three distinct durable principals required')
    if not isinstance(case_ids, list) or not 1 <= len(case_ids) <= 32 or len(set(case_ids)) != len(case_ids) or any(not isinstance(k, str) or not k for k in case_ids):
        raise ValueError('Explicit nonempty owner case IDs required')
    manifest = canonical({'binding': binding, 'verifier_id': verifier_id, 'reviewer_id': reviewer_id, 'case_ids': case_ids})
    with store.db.atomic_transaction() as conn:
        prior = conn.execute('SELECT manifest FROM pm_coordinator_evidence_contracts WHERE run_id=?', (binding['run_id'],)).fetchone()
        if prior:
            if prior['manifest'] != manifest:
                raise ValueError('Immutable evidence job cannot be replaced')
            return
        conn.execute('INSERT INTO pm_coordinator_evidence_contracts(run_id,manifest) VALUES (?,?)', (binding['run_id'], manifest))
