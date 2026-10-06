"""
tests/test_multi_tenant_iam.py: Test suite for Enterprise Multi-Tenant IAM.
Validates tenant boundaries, HMAC token issuance/verification, PBAC/RBAC authorization,
and filesystem jail path safety.
"""

import os
import time
import pytest
from mas.iam import (
    MultiTenantIAM,
    TenantStatus,
    StandardRole,
    TenantContext,
    default_iam,
)


@pytest.fixture
def iam():
    return MultiTenantIAM(signing_secret="test-secret-key-12345")


def test_tenant_lifecycle(iam):
    tenant = iam.create_tenant(
        tenant_id="tenant-acme",
        name="Acme Corp",
        allowed_scopes={"data:read", "models:invoke"},
    )
    assert tenant.tenant_id == "tenant-acme"
    assert tenant.status == TenantStatus.ACTIVE

    # Duplicate creation raises ValueError
    with pytest.raises(ValueError, match="already exists"):
        iam.create_tenant("tenant-acme", "Acme Again")

    # Invalid character in tenant_id raises ValueError
    with pytest.raises(ValueError, match="Invalid tenant_id"):
        iam.create_tenant("tenant/bad..id", "Bad Tenant")


def test_principal_registration_and_token_flow(iam):
    iam.create_tenant("tenant-beta", "Beta Analytics")
    principal = iam.register_principal(
        tenant_id="tenant-beta",
        user_id="alice",
        roles={StandardRole.DATA_ARCHITECT.value},
        scopes={"custom:scope"},
        email="alice@beta.com",
    )
    assert principal.user_id == "alice"
    assert principal.tenant_id == "tenant-beta"

    # Issue token
    token = iam.issue_token("tenant-beta", "alice", ttl_seconds=60)
    assert "." in token

    # Verify valid token
    ctx = iam.verify_token(token)
    assert ctx.tenant_id == "tenant-beta"
    assert ctx.principal_id == "alice"
    assert StandardRole.DATA_ARCHITECT.value in ctx.roles
    assert "custom:scope" in ctx.scopes

    # Tampered token fails
    parts = token.split(".")
    tampered = f"{parts[0]}xyz.{parts[1]}"
    with pytest.raises(PermissionError, match="Invalid cryptographic token signature"):
        iam.verify_token(tampered)


def test_expired_token_rejected(iam):
    iam.create_tenant("tenant-gamma", "Gamma Labs")
    iam.register_principal("tenant-gamma", "bob")
    # Issue already expired token
    token = iam.issue_token("tenant-gamma", "bob", ttl_seconds=-10)
    with pytest.raises(PermissionError, match="Token has expired"):
        iam.verify_token(token)


def test_strict_multi_tenant_isolation_and_rbac(iam):
    iam.create_tenant("tenant-alpha", "Alpha Corp")
    iam.create_tenant("tenant-omega", "Omega Corp")

    iam.register_principal(
        "tenant-alpha", "admin_alpha", roles={StandardRole.TENANT_ADMIN.value}
    )
    iam.register_principal(
        "tenant-alpha", "auditor_alpha", roles={StandardRole.SECURITY_AUDITOR.value}
    )

    token_admin = iam.issue_token("tenant-alpha", "admin_alpha")
    ctx_admin = iam.verify_token(token_admin)

    token_auditor = iam.issue_token("tenant-alpha", "auditor_alpha")
    ctx_auditor = iam.verify_token(token_auditor)

    # 1. Tenant Admin can execute tools in their own tenant
    assert iam.authorize(
        ctx_admin,
        action="tools:execute",
        resource_tenant_id="tenant-alpha",
        resource_urn="urn:mas:tenant:tenant-alpha:tool:fs_read",
    ) is True

    # 2. Strict Cross-Tenant Denial: Admin of Alpha CANNOT touch Omega resources
    assert iam.authorize(
        ctx_admin,
        action="tools:execute",
        resource_tenant_id="tenant-omega",
        resource_urn="urn:mas:tenant:tenant-omega:tool:fs_read",
    ) is False

    # 3. Security Auditor can read audit and storage, but CANNOT execute tools
    assert iam.authorize(
        ctx_auditor,
        action="audit:read",
        resource_tenant_id="tenant-alpha",
        resource_urn="urn:mas:tenant:tenant-alpha:audit:log",
    ) is True
    assert iam.authorize(
        ctx_auditor,
        action="tools:execute",
        resource_tenant_id="tenant-alpha",
        resource_urn="urn:mas:tenant:tenant-alpha:tool:run_python",
    ) is False


def test_isolated_sandbox_directory(iam, tmp_path):
    base_dir = str(tmp_path / "workspace")
    jail_path = iam.get_isolated_sandbox_path("tenant-xyz", base_dir)

    assert os.path.exists(jail_path)
    assert jail_path.endswith(os.path.join("tenants", "tenant-xyz"))

    # Directory traversal prevention
    with pytest.raises(ValueError):
        iam.get_isolated_sandbox_path("../../etc", base_dir)
