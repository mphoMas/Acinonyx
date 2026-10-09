"""Durable platform IAM adapter for the trusted coding control plane."""
from contextlib import contextmanager
import hashlib
import hmac
import sqlite3

from mas.iam import MultiTenantIAM

ACTIONS = {"owner": "swarm:owner", "requester": "swarm:request", "approver": "swarm:approve"}


class PlatformAuthority:
    def __init__(self, iam: MultiTenantIAM):
        if type(iam) is not MultiTenantIAM or iam.database_path is None:
            raise ValueError("Shared swarm identity requires durable platform IAM")
        self.iam = iam

    @property
    def binding(self):
        return {"mode": "platform", "version": 1, "database": str(self.iam.database_path),
                "key_id": hmac.new(self.iam.signing_secret, b"mas-shared-swarm-authority-v1", hashlib.sha256).hexdigest()}

    @contextmanager
    def guard(self):
        # Always acquire IAM before swarm state. Reserve its writer slot so
        # revocation cannot publish a witness fence or commit between swarm
        # authorization and commit. A read lock alone permits early anchoring.
        # This guard never spans a model request or container execution.
        try:
            with self.iam._store.transaction(write=True) as db:
                self.iam._store.validate_audit(db)
                yield
        except (sqlite3.Error, OSError) as exc:
            raise PermissionError("Platform authority unavailable") from exc

    def authenticate(self, token, roles):
        identity = self.iam.verify_token(token)
        for role in ("owner", "requester", "approver"):
            if role in roles and self.iam.authorize(identity, ACTIONS[role], identity.tenant_id,
                                                   f"urn:mas:tenant:{identity.tenant_id}:swarm"):
                return {"tenant": identity.tenant_id, "subject": identity.principal_id, "role": role}
        raise PermissionError("Platform identity is not authorized for this swarm operation")
