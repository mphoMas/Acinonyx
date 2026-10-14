"""Integration tests for GHA-03 Authentication Gateway & Observation Ingestion.

Covers all 22 acceptance scenarios (TC-01 through TC-22) plus binding implementation conditions:
- Real signed RS256 cryptography (no mock verification)
- Duplicate key rejection in header and payload JSON
- Nonfinite numbers and boolean NumericDate rejection
- Strict 8192-byte JWT length and segment formatting
- Coordinate binding (run_id and integer run_attempt conversion)
- Independent request bounds (18 MiB request, 16 MiB base64, 12 MiB decoded archive, 1 MiB manifest)
- Strict base64 decoding and actual validate_artifact_archive integration
- Ephemeral witness context restrictions (cannot invoke submit, accept, or coordinate)
- Action ownership alignment (builder challenges, coordinator resolves)
- Recheck of tenant and connector status at validation completion
- JWKS cache lifecycle (TTL/cooldown equality, single-flight concurrency, failed-fetch throttling, oversized responses)
- Zero database writes verified against PMDatabase
- Redacted security audit logging
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import threading
import time
import zipfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from mas.iam import MultiTenantIAM, StandardRole
from mas.pm.coordinator import trusted_coordinator_admin_scope
from mas.pm.db import PMDatabase
from mas.pm.delivery import DeliveryService, delivery_admin_actor
from mas.pm.delivery_validator import DeliveryManifest, ManifestObservation
from mas.pm.gateway import (
    GITHUB_JWKS_URL,
    GatewayError,
    GatewayObservationValidator,
    GitHubConnectorConfig,
    JWKSCache,
    WitnessObservationValidationResponse,
)
from mas.pm.models import Issue, Project


@contextmanager
def actor(name: str):
    with trusted_coordinator_admin_scope(), delivery_admin_actor(name):
        yield

HEX40_DEFAULT = "15e9f7634f191b29a28bfdf911925b42d71329a1"
SHA256_DEFAULT = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def int_to_b64url(val: int) -> str:
    byte_len = (val.bit_length() + 7) // 8
    return b64url_encode(val.to_bytes(byte_len, byteorder="big"))


class KeyFixture:
    def __init__(self, kid: str = "test-key-1", key_size: int = 2048, public_exponent: int = 65537) -> None:
        self.kid = kid
        self.private_key = rsa.generate_private_key(public_exponent=public_exponent, key_size=key_size)
        self.public_key = self.private_key.public_key()
        nums = self.public_key.public_numbers()
        self.n_b64 = int_to_b64url(nums.n)
        self.e_b64 = int_to_b64url(nums.e)

    def to_jwk(self) -> dict[str, str]:
        return {
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": self.kid,
            "n": self.n_b64,
            "e": self.e_b64,
        }


def make_jwt(
    payload: dict[str, Any] | None = None,
    *,
    key_fixture: KeyFixture,
    kid: str | None = None,
    alg: str = "RS256",
    extra_headers: dict[str, Any] | None = None,
    raw_header_json: str | None = None,
    raw_payload_json: str | None = None,
    corrupt_signature: bool = False,
    override_clock: float | None = None,
) -> str:
    current_time = override_clock if override_clock is not None else time.time()

    if raw_header_json is not None:
        header_bytes = raw_header_json.encode("utf-8")
    else:
        header = {"alg": alg, "kid": kid if kid is not None else key_fixture.kid, "typ": "JWT"}
        if extra_headers:
            header.update(extra_headers)
        header_bytes = json.dumps(header).encode("utf-8")

    if raw_payload_json is not None:
        payload_bytes = raw_payload_json.encode("utf-8")
    else:
        default_payload = {
            "iss": "https://token.actions.githubusercontent.com",
            "aud": "mas-coordinator-delivery",
            "sub": "repo:octocat/Acinonyx:pull_request",
            "repository": "octocat/Acinonyx",
            "repository_id": "987654321",
            "repository_owner": "octocat",
            "repository_owner_id": "12345678",
            "run_id": "1029384756",
            "run_attempt": "1",
            "job_workflow_ref": f"octocat/Acinonyx/.github/workflows/reusable-delivery-gate.yml@{HEX40_DEFAULT}",
            "job_workflow_sha": HEX40_DEFAULT,
            "workflow_ref": "octocat/Acinonyx/.github/workflows/ci.yml@refs/pull/42/merge",
            "workflow_sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            "event_name": "pull_request",
            "ref": "refs/pull/42/merge",
            "sha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
            "runner_environment": "github-hosted",
            "iat": current_time,
            "nbf": current_time,
            "exp": current_time + 600.0,
            "jti": "550e8400-e29b-41d4-a716-446655440000",
        }
        if payload is not None:
            default_payload.update(payload)
        payload_bytes = json.dumps(default_payload).encode("utf-8")

    h_b64 = b64url_encode(header_bytes)
    p_b64 = b64url_encode(payload_bytes)
    signed_data = f"{h_b64}.{p_b64}".encode("ascii")

    sig = key_fixture.private_key.sign(signed_data, padding.PKCS1v15(), hashes.SHA256())
    if corrupt_signature:
        sig = bytearray(sig)
        sig[0] ^= 0xFF
        sig = bytes(sig)
    s_b64 = b64url_encode(sig)

    return f"{h_b64}.{p_b64}.{s_b64}"


def make_zip_bytes(files: dict[str, bytes]) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return bio.getvalue()


@pytest.fixture
def mock_clock():
    current_time = [1792064100.0]

    def get_time():
        return current_time[0]

    def advance(seconds: float):
        current_time[0] += seconds

    return get_time, advance


@pytest.fixture
def key_pair():
    return KeyFixture("test-key-1")


@pytest.fixture
def gateway_setup(tmp_path: Path, mock_clock, key_pair):
    get_time, advance_clock = mock_clock

    # In-memory JWKS response
    jwks_data = {"keys": [key_pair.to_jwk()]}
    jwks_bytes = json.dumps(jwks_data).encode("utf-8")

    fetch_call_count = [0]

    def stub_fetcher(url: str) -> bytes:
        fetch_call_count[0] += 1
        if url != GITHUB_JWKS_URL:
            raise GatewayError("Unexpected URL", status_code=503, code="JWKS_UNAVAILABLE")
        return jwks_bytes

    jwks_cache = JWKSCache(clock=get_time, fetcher=stub_fetcher)

    # MultiTenantIAM setup
    iam_db_path = tmp_path / "iam.db"
    iam = MultiTenantIAM(signing_secret="0123456789abcdef0123456789abcdef", db_path=iam_db_path)
    iam.create_tenant("tenant-alpha", "Alpha Corp")
    iam.register_principal("tenant-alpha", "builder-1", roles={StandardRole.OPERATOR.value})

    # PMDatabase setup
    pm_db_path = tmp_path / "pm.db"
    pm_db = PMDatabase(pm_db_path)
    pm_db.create_project(Project(id="proj-1", key="P1", name="Project 1", token_budget=10000))
    pm_db.create_issue(Issue(id="issue-1", project_id="proj-1", key="P1-1", title="Task 1", appetite_tokens=1000, path_whitelist=["mas/"]))

    # Enroll in delivery
    delivery_svc = DeliveryService(pm_db)
    with actor("coordinator-1"):
        delivery_svc.enroll("proj-1", "tenant-alpha")

    # Connector registry
    config = GitHubConnectorConfig(
        tenant_id="tenant-alpha",
        project_id="proj-1",
        repository_id="987654321",
        repository_owner_id="12345678",
        approved_workflow_repo="octocat/Acinonyx",
        approved_workflow_path=".github/workflows/reusable-delivery-gate.yml",
        approved_workflow_sha=HEX40_DEFAULT,
    )
    connector_registry = {("987654321", "12345678"): config}

    audit_events: list[dict[str, Any]] = []

    def audit_logger(event: dict[str, Any]) -> None:
        audit_events.append(event)

    validator = GatewayObservationValidator(
        connector_registry=connector_registry,
        iam=iam,
        jwks_cache=jwks_cache,
        clock=get_time,
        audit_logger=audit_logger,
    )

    return {
        "validator": validator,
        "key_pair": key_pair,
        "connector_config": config,
        "connector_registry": connector_registry,
        "iam": iam,
        "pm_db": pm_db,
        "delivery_svc": delivery_svc,
        "get_time": get_time,
        "advance_clock": advance_clock,
        "audit_events": audit_events,
        "fetch_call_count": fetch_call_count,
    }


def make_valid_manifest(
    tenant_id: str = "tenant-alpha",
    project_id: str = "proj-1",
    issue_id: str = "issue-1",
    fencing_token: int = 1,
    observations: list[ManifestObservation] | None = None,
) -> DeliveryManifest:
    if observations is None:
        observations = [
            ManifestObservation(
                check_id="check-1",
                outcome="PASSED",
                evidence_ref="inline:test-pass",
                digest=SHA256_DEFAULT,
                size=0,
            )
        ]
    return DeliveryManifest(
        schema_version="mas-delivery-manifest-v1",
        tenant_id=tenant_id,
        project_id=project_id,
        issue_id=issue_id,
        brief_version=1,
        policy_version=1,
        revision=1,
        run_id="run-coord-1",
        intent_id="intent-1",
        attempt_id="attempt-1",
        fencing_token=fencing_token,
        candidate_sha=HEX40_DEFAULT,
        base_sha=HEX40_DEFAULT,
        suite_digest=SHA256_DEFAULT,
        observations=observations,
    )


def count_db_rows(pm_db: PMDatabase) -> dict[str, int]:
    with pm_db.atomic_transaction() as c:
        tasks = c.execute("SELECT COUNT(*) FROM pm_delivery_tasks").fetchone()[0]
        subs = c.execute("SELECT COUNT(*) FROM pm_delivery_submissions").fetchone()[0]
        events = c.execute("SELECT COUNT(*) FROM pm_delivery_events").fetchone()[0]
    return {"tasks": tasks, "submissions": subs, "events": events}


# ==============================================================================
# Acceptance Tests TC-01 to TC-22
# ==============================================================================


def test_tc01_wrong_issuer(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    t = make_jwt({"iss": "https://evil-issuer.com"}, key_fixture=kp, override_clock=gateway_setup["get_time"]())
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_ISSUER"


def test_tc02_wrong_audience(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    t = make_jwt({"aud": "wrong-audience"}, key_fixture=kp, override_clock=gateway_setup["get_time"]())
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_AUDIENCE"


def test_tc03_unsupported_algorithms(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    # Algorithm none
    t_none = make_jwt(key_fixture=kp, alg="none", override_clock=gateway_setup["get_time"]())
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_none}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "UNSUPPORTED_ALGORITHM"

    # Algorithm HS256
    t_hs256 = make_jwt(key_fixture=kp, alg="HS256", override_clock=gateway_setup["get_time"]())
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_hs256}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "UNSUPPORTED_ALGORITHM"


def test_tc04_malformed_header_extra_keys_or_missing_kid(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    # Extra header key (e.g. jku)
    t_extra = make_jwt(key_fixture=kp, extra_headers={"jku": "https://evil.com"}, override_clock=gateway_setup["get_time"]())
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_extra}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_JWT_HEADER"

    # Missing kid
    t_nokid = make_jwt(key_fixture=kp, raw_header_json='{"alg": "RS256", "typ": "JWT"}', override_clock=gateway_setup["get_time"]())
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_nokid}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_JWT_HEADER"


def test_tc05_corrupted_rsa_signature(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    t = make_jwt(key_fixture=kp, corrupt_signature=True, override_clock=gateway_setup["get_time"]())
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_SIGNATURE"


def test_tc06_expired_token(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    # exp older than now - 30s
    t = make_jwt({"iat": now - 300.0, "nbf": now - 300.0, "exp": now - 60.0}, key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "TOKEN_EXPIRED"


def test_tc07_future_token_nbf(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    # nbf more than 30s in future
    t = make_jwt({"nbf": now + 120.0, "iat": now, "exp": now + 600.0}, key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "TOKEN_FUTURE"


def test_tc08_token_issued_in_future_iat(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    # iat more than 30s in future
    t = make_jwt({"iat": now + 120.0, "nbf": now, "exp": now + 600.0}, key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "TOKEN_ISSUED_IN_FUTURE"


def test_tc09_negative_or_excessive_lifetime(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    # exp <= iat
    t_neg = make_jwt({"iat": now, "nbf": now, "exp": now - 10.0}, key_fixture=kp, override_clock=now)
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_neg}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_TOKEN_LIFETIME"

    # exp - iat > 900s
    t_excess = make_jwt({"iat": now, "nbf": now, "exp": now + 3600.0}, key_fixture=kp, override_clock=now)
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_excess}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_TOKEN_LIFETIME"


def test_tc10_token_age_exceeded(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()

    # Issued 950s ago with a 1000s lifetime: nominally exp is at now + 50s, but age (now - iat) = 950s > 900s
    t_old = make_jwt(
        {"iat": now - 950.0, "nbf": now - 950.0, "exp": now + 50.0},
        key_fixture=kp,
        override_clock=now - 950.0,
    )
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_old}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "TOKEN_AGE_EXCEEDED"


def test_tc11_jwks_unknown_kid_throttling(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()

    # Prime cache with initial valid call
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    t_valid = make_jwt(key_fixture=kp, override_clock=now)
    v.validate_submission(f"Bearer {t_valid}", req)
    initial_fetches = gateway_setup["fetch_call_count"][0]

    # Present unknown kid while cache is fresh (< 300s since last fetch)
    t_unknown = make_jwt(key_fixture=kp, kid="unknown-kid-xyz", override_clock=now)
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_unknown}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "UNKNOWN_KEY_THROTTLED"

    # Verify no additional HTTP fetch was made
    assert gateway_setup["fetch_call_count"][0] == initial_fetches


def test_tc12_jwks_endpoint_outage_fails_closed(tmp_path: Path, mock_clock, key_pair):
    get_time, _ = mock_clock

    def failing_fetcher(url: str) -> bytes:
        raise TimeoutError("Network timeout connecting to GitHub JWKS")

    cache = JWKSCache(clock=get_time, fetcher=failing_fetcher)
    iam = MultiTenantIAM(signing_secret="0123456789abcdef0123456789abcdef", db_path=tmp_path / "iam.db")
    iam.create_tenant("tenant-alpha", "Alpha Corp")

    config = GitHubConnectorConfig(
        tenant_id="tenant-alpha",
        project_id="proj-1",
        repository_id="987654321",
        repository_owner_id="12345678",
        approved_workflow_repo="octocat/Acinonyx",
        approved_workflow_path=".github/workflows/reusable-delivery-gate.yml",
        approved_workflow_sha=HEX40_DEFAULT,
    )
    validator = GatewayObservationValidator({("987654321", "12345678"): config}, iam, cache, clock=get_time)

    t = make_jwt(key_fixture=key_pair, override_clock=get_time())
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        validator.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 503
    assert exc.value.code == "JWKS_UNAVAILABLE"


def test_tc13_unenrolled_repository_id(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    t = make_jwt({"repository_id": "99999999"}, key_fixture=kp, override_clock=gateway_setup["get_time"]())
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "REPOSITORY_NOT_ENROLLED"


def test_tc14_mismatched_repository_owner_id(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    t = make_jwt({"repository_owner_id": "87654321"}, key_fixture=kp, override_clock=gateway_setup["get_time"]())
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "REPOSITORY_NOT_ENROLLED"


def test_tc15_mutable_workflow_ref_used(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    t = make_jwt(
        {"job_workflow_ref": "octocat/Acinonyx/.github/workflows/reusable-delivery-gate.yml@refs/heads/main"},
        key_fixture=kp,
        override_clock=gateway_setup["get_time"](),
    )
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "WORKFLOW_NOT_PINNED"


def test_tc16_unapproved_workflow_path_or_sha(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    # Wrong SHA
    unapproved_sha = "0000000000000000000000000000000000000000"
    t_sha = make_jwt(
        {
            "job_workflow_sha": unapproved_sha,
            "job_workflow_ref": f"octocat/Acinonyx/.github/workflows/reusable-delivery-gate.yml@{unapproved_sha}",
        },
        key_fixture=kp,
        override_clock=now,
    )
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_sha}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "WORKFLOW_UNAPPROVED"

    # Wrong path
    t_path = make_jwt(
        {"job_workflow_ref": f"octocat/Acinonyx/.github/workflows/wrong-file.yml@{HEX40_DEFAULT}"},
        key_fixture=kp,
        override_clock=now,
    )
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_path}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "WORKFLOW_UNAPPROVED"


def test_tc17_disallowed_event_caller_ref_or_environment(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    # Disallowed event
    t_evt = make_jwt({"event_name": "issue_comment"}, key_fixture=kp, override_clock=now)
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_evt}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "CONDITION_DISALLOWED"

    # Disallowed caller ref for pull_request
    t_ref = make_jwt({"ref": "refs/heads/feature-branch"}, key_fixture=kp, override_clock=now)
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_ref}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "CONDITION_DISALLOWED"

    # Disallowed runner environment
    t_env = make_jwt({"runner_environment": "untrusted-self-hosted"}, key_fixture=kp, override_clock=now)
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_env}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "CONDITION_DISALLOWED"


def test_tc18_client_role_and_extra_fields_rejected(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    t = make_jwt(key_fixture=kp, override_clock=now)

    # Request body with extra field 'role'
    req_spoof = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
        "role": "builder",
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req_spoof)
    assert exc.value.status_code == 422
    assert exc.value.code == "EXTRA_FIELDS_FORBIDDEN"


def test_tc19_witness_role_cannot_submit_delivery_or_accept(gateway_setup):
    delivery_svc = gateway_setup["delivery_svc"]

    # Establish a delivery task
    brief = {
        "base_sha": HEX40_DEFAULT,
        "suite_digest": SHA256_DEFAULT,
        "policy_version": 1,
        "coordinator": "coord-1",
        "builder": "builder-1",
        "verifier": "verifier-1",
        "reviewer": "reviewer-1",
        "scope": ["mas/"],
        "critical": True,
        "mechanism": "Qualified synthetic boundary; current policy checked atomically",
        "requirements": [{"id": "REQ-1", "rule": "No unsupported completion evidence"}],
        "checks": [
            {"id": "chk-1", "requirement_id": "REQ-1", "command": "test", "expected": "pass", "negative": False},
            {"id": "chk-neg", "requirement_id": "REQ-1", "command": "test-neg", "expected": "fail", "negative": True},
        ],
    }
    with actor("coord-1"):
        delivery_svc.establish("issue-1", brief)

    # Verify that a witness actor cannot invoke submit()
    with actor("gha-witness:987654321:1029384756"):
        with pytest.raises(PermissionError) as exc:
            delivery_svc.submit(
                "issue-1",
                1,
                {
                    "run_id": "run-1",
                    "candidate_sha": HEX40_DEFAULT,
                    "closures": {},
                    "limitations": "none",
                    "observations": [
                        {
                            "check_id": "chk-1",
                            "outcome": "PASSED",
                            "evidence_ref": "inline:pass",
                            "digest": SHA256_DEFAULT,
                        }
                    ],
                },
            )
        assert "Caller is not assigned builder" in str(exc.value)

        # Verify witness cannot invoke accept()
        with pytest.raises(PermissionError) as exc:
            delivery_svc.accept(
                "issue-1",
                1,
                verification_id="ver-1",
                review_id="rev-1",
            )
        assert ("Trusted verification/review service required" in str(exc.value) or
                "Caller is not assigned reviewer" in str(exc.value))


def test_tc20_tenant_revoked_or_suspended_in_iam(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    iam = gateway_setup["iam"]
    now = gateway_setup["get_time"]()

    # Suspend tenant in IAM
    iam.suspend_tenant("tenant-alpha")

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "TENANT_REVOKED"


def test_tc21_oversized_payload_rejected(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()

    # 1. Oversized JWT (> 8192 bytes)
    big_claims = {"padding": "x" * 8500}
    t_big = make_jwt(big_claims, key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_big}", req)
    assert exc.value.status_code == 413
    assert exc.value.code == "PAYLOAD_TOO_LARGE"

    # 2. Oversized Request Body (> 18 MiB)
    t_valid = make_jwt(key_fixture=kp, override_clock=now)
    huge_body = b'{"data": "' + b"x" * (19 * 1024 * 1024) + b'"}'
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t_valid}", huge_body)
    assert exc.value.status_code == 413
    assert exc.value.code == "PAYLOAD_TOO_LARGE"


def test_tc22_valid_submission_validated_with_zero_database_mutation(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    pm_db = gateway_setup["pm_db"]
    now = gateway_setup["get_time"]()

    # Create zip archive for observation
    zip_bytes = make_zip_bytes({"test_report.txt": b"all tests passed"})
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
    report_digest = hashlib.sha256(b"all tests passed").hexdigest()

    manifest = make_valid_manifest(
        observations=[
            ManifestObservation(
                check_id="check-unit",
                outcome="PASSED",
                evidence_ref="test_report.txt",
                digest=report_digest,
                size=len(b"all tests passed"),
            )
        ]
    )

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": manifest.model_dump(),
        "artifact_archive_base64": zip_b64,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    # Count rows before
    counts_before = count_db_rows(pm_db)

    # Validate submission
    resp = v.validate_submission(f"Bearer {t}", req)

    # Verify structured response
    assert isinstance(resp, WitnessObservationValidationResponse)
    assert resp.status == "VALIDATED_UNTRUSTED_OBSERVATION"
    assert resp.transport_authenticated is True
    assert resp.authority_verified is False
    assert resp.artifacts_validated is True
    assert resp.tenant_id == "tenant-alpha"
    assert resp.project_id == "proj-1"
    assert resp.issue_id == "issue-1"
    assert resp.artifact_digest == hashlib.sha256(zip_bytes).hexdigest()
    assert resp.observation_count == 1
    assert resp.github_run_id == "1029384756"
    assert resp.github_run_attempt == 1

    # Verify zero database mutation
    counts_after = count_db_rows(pm_db)
    assert counts_before == counts_after


# ==============================================================================
# Additional Acceptance & Edge Case Tests
# ==============================================================================


def test_duplicate_keys_in_jwt_header_rejected(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    raw_header = '{"alg": "RS256", "kid": "test-key-1", "alg": "RS256"}'
    t = make_jwt(key_fixture=kp, raw_header_json=raw_header, override_clock=gateway_setup["get_time"]())
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_JWT_HEADER"


def test_duplicate_keys_in_jwt_payload_rejected(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    raw_payload = f'{{"iss": "https://token.actions.githubusercontent.com", "iss": "other", "aud": "mas-coordinator-delivery", "repository_id": "987654321", "repository_owner_id": "12345678", "job_workflow_ref": "octocat/Acinonyx/.github/workflows/reusable-delivery-gate.yml@{HEX40_DEFAULT}", "job_workflow_sha": "{HEX40_DEFAULT}", "event_name": "pull_request", "ref": "refs/pull/42/merge", "runner_environment": "github-hosted", "run_id": "1029384756", "run_attempt": "1", "iat": {now}, "exp": {now + 600.0}}}'
    t = make_jwt(key_fixture=kp, raw_payload_json=raw_payload, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_JWT_PAYLOAD"


def test_nonfinite_numeric_date_rejected(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    raw_payload = f'{{"iss": "https://token.actions.githubusercontent.com", "aud": "mas-coordinator-delivery", "repository_id": "987654321", "repository_owner_id": "12345678", "job_workflow_ref": "octocat/Acinonyx/.github/workflows/reusable-delivery-gate.yml@{HEX40_DEFAULT}", "job_workflow_sha": "{HEX40_DEFAULT}", "event_name": "pull_request", "ref": "refs/pull/42/merge", "runner_environment": "github-hosted", "run_id": "1029384756", "run_attempt": "1", "iat": {now}, "exp": NaN}}'
    t = make_jwt(key_fixture=kp, raw_payload_json=raw_payload, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_JWT_PAYLOAD"


def test_boolean_numeric_date_rejected(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    t = make_jwt({"exp": True}, key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 401
    assert exc.value.code == "INVALID_CLAIM_TYPE"


def test_coordinate_mismatch_run_id_or_attempt(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    t = make_jwt(key_fixture=kp, override_clock=now)

    # Mismatched run_id
    req_bad_run = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "9999999999",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req_bad_run)
    assert exc.value.status_code == 400
    assert exc.value.code == "COORDINATE_MISMATCH"

    # Mismatched run_attempt
    req_bad_att = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 2,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req_bad_att)
    assert exc.value.status_code == 400
    assert exc.value.code == "COORDINATE_MISMATCH"


def test_artifact_archive_required_when_observations_reference_files(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()

    # Observation references a file, but artifact_archive_base64 is None
    manifest = make_valid_manifest(
        observations=[
            ManifestObservation(
                check_id="check-file",
                outcome="PASSED",
                evidence_ref="reports/test.xml",
                digest=SHA256_DEFAULT,
                size=10,
            )
        ]
    )
    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": manifest.model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 400
    assert exc.value.code == "ARTIFACTS_REQUIRED"


def test_invalid_base64_archive_rejected(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "artifact_archive_base64": "!!!not_valid_base64!!!",
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 400
    assert exc.value.code == "INVALID_BASE64_PAYLOAD"


def test_revocation_during_processing_detected(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    iam = gateway_setup["iam"]
    now = gateway_setup["get_time"]()
    t = make_jwt(key_fixture=kp, override_clock=now)

    # Mock validate_artifact_archive to simulate slow processing during which tenant is revoked
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "artifact_archive_base64": base64.b64encode(make_zip_bytes({"f.txt": b"1"})).decode("ascii"),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    original_validate = v.token_verifier.verify_token

    def slow_verify(*args, **kwargs):
        res = original_validate(*args, **kwargs)
        # Suspend tenant mid-flight
        iam.suspend_tenant("tenant-alpha")
        return res

    v.token_verifier.verify_token = slow_verify
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)
    assert exc.value.status_code == 403
    assert exc.value.code == "TENANT_REVOKED"


def test_jwks_cache_ttl_and_cooldown_equality_boundaries(mock_clock, key_pair):
    get_time, advance_clock = mock_clock

    fetches = [0]

    def stub_fetcher(url: str) -> bytes:
        fetches[0] += 1
        return json.dumps({"keys": [key_pair.to_jwk()]}).encode("utf-8")

    cache = JWKSCache(clock=get_time, fetcher=stub_fetcher, cache_ttl=86400.0, unknown_kid_cooldown=300.0)

    # 1. Cold cache: fetches on first access
    k1 = cache.get_key("test-key-1")
    assert k1 is not None
    assert fetches[0] == 1

    # 2. Fresh cache: exactly at 86399s (< 86400s), does not fetch
    advance_clock(86399.0)
    assert cache.get_key("test-key-1") is not None
    assert fetches[0] == 1

    # 3. Expired cache: exactly at 86400s (>= 86400s), triggers fetch
    advance_clock(1.0)
    assert cache.get_key("test-key-1") is not None
    assert fetches[0] == 2

    # 4. Unknown kid cooldown: at 299s (< 300s), throttled
    advance_clock(299.0)
    with pytest.raises(GatewayError) as exc:
        cache.get_key("nonexistent-key")
    assert exc.value.code == "UNKNOWN_KEY_THROTTLED"
    assert fetches[0] == 2

    # 5. Unknown kid cooldown: at exactly 300s (>= 300s), eligible to fetch
    advance_clock(1.0)
    with pytest.raises(GatewayError) as exc:
        cache.get_key("nonexistent-key")
    assert exc.value.code == "UNKNOWN_KEY_ID"
    assert fetches[0] == 3


def test_jwks_single_flight_concurrency(mock_clock, key_pair):
    get_time, _ = mock_clock

    fetches = [0]

    def slow_fetcher(url: str) -> bytes:
        fetches[0] += 1
        return json.dumps({"keys": [key_pair.to_jwk()]}).encode("utf-8")

    cache = JWKSCache(clock=get_time, fetcher=slow_fetcher)

    # Run 10 threads trying to get the key concurrently
    results = [None] * 10
    exceptions = [None] * 10

    def worker(idx: int):
        try:
            results[idx] = cache.get_key("test-key-1")
        except Exception as e:
            exceptions[idx] = e

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify all threads received the public key
    for r in results:
        assert r is not None
    for e in exceptions:
        assert e is None

    # Verify only ONE fetch was executed across all concurrent threads
    assert fetches[0] == 1


def test_repeated_valid_token_stateless_success_with_zero_db_mutation(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    pm_db = gateway_setup["pm_db"]
    now = gateway_setup["get_time"]()

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    counts_0 = count_db_rows(pm_db)

    # First validation succeeds
    resp1 = v.validate_submission(f"Bearer {t}", req)
    assert resp1.status == "VALIDATED_UNTRUSTED_OBSERVATION"
    counts_1 = count_db_rows(pm_db)
    assert counts_0 == counts_1

    # Second validation of exact same token also succeeds in this stateless slice
    resp2 = v.validate_submission(f"Bearer {t}", req)
    assert resp2.status == "VALIDATED_UNTRUSTED_OBSERVATION"
    counts_2 = count_db_rows(pm_db)
    assert counts_0 == counts_2


def test_security_audit_logging_redacts_tokens_and_bodies(gateway_setup):
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    audit_events = gateway_setup["audit_events"]
    now = gateway_setup["get_time"]()

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    v.validate_submission(f"Bearer {t}", req)

    # Verify an audit log was generated
    assert len(audit_events) > 0
    event = audit_events[-1]
    assert event["event"] == "OBSERVATION_VALIDATED"
    # Verify no raw bearer token in audit event
    assert "Bearer" not in str(event)
    assert t not in str(event)


# ==============================================================================
# GHA-03 REWORK CORRECTION REGRESSION TESTS (B1, B2, B3)
# ==============================================================================


def test_rework_b1_connector_replacement_during_artifact_validation_rejected(gateway_setup):
    """B1: Replace frozen connector entry during real artifact validation with status='REVOKED', generation=2.
    Must be rejected with 403 CONNECTOR_REVOKED.
    """
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    cfg = gateway_setup["connector_config"]
    reg = gateway_setup["connector_registry"]
    now = gateway_setup["get_time"]()

    zip_bytes = make_zip_bytes({"test_report.txt": b"test content"})
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
    report_digest = hashlib.sha256(b"test content").hexdigest()

    manifest = make_valid_manifest(
        observations=[
            ManifestObservation(
                check_id="CHK-01",
                outcome="PASSED",
                evidence_ref="test_report.txt",
                digest=report_digest,
            )
        ]
    )

    repo_coord = (cfg.repository_id, cfg.repository_owner_id)

    def hook(stage: str):
        if stage == "artifact_validation":
            revoked_cfg = cfg.model_copy(update={"status": "REVOKED", "generation": 2})
            reg[repo_coord] = revoked_cfg

    v.on_validation_stage = hook

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": manifest.model_dump(),
        "artifact_archive_base64": zip_b64,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 403
    assert exc.value.code == "CONNECTOR_REVOKED"
    env = exc.value.to_envelope()
    assert env["code"] == "CONNECTOR_REVOKED"


def test_rework_b1_connector_removal_during_artifact_validation_rejected(gateway_setup):
    """B1: Remove connector entry during real artifact validation.
    Must be rejected with 403 CONNECTOR_REMOVED.
    """
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    cfg = gateway_setup["connector_config"]
    reg = gateway_setup["connector_registry"]
    now = gateway_setup["get_time"]()

    zip_bytes = make_zip_bytes({"test_report.txt": b"test content"})
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
    report_digest = hashlib.sha256(b"test content").hexdigest()

    manifest = make_valid_manifest(
        observations=[
            ManifestObservation(
                check_id="CHK-01",
                outcome="PASSED",
                evidence_ref="test_report.txt",
                digest=report_digest,
            )
        ]
    )

    repo_coord = (cfg.repository_id, cfg.repository_owner_id)

    def hook(stage: str):
        if stage == "artifact_validation":
            reg.pop(repo_coord, None)

    v.on_validation_stage = hook

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": manifest.model_dump(),
        "artifact_archive_base64": zip_b64,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 403
    assert exc.value.code == "CONNECTOR_REMOVED"


def test_rework_b1_connector_generation_change_during_validation_rejected(gateway_setup):
    """B1: Generation changed (e.g. from 1 to 2) during validation must be rejected."""
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    cfg = gateway_setup["connector_config"]
    reg = gateway_setup["connector_registry"]
    now = gateway_setup["get_time"]()

    zip_bytes = make_zip_bytes({"test_report.txt": b"test content"})
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
    report_digest = hashlib.sha256(b"test content").hexdigest()

    manifest = make_valid_manifest(
        observations=[
            ManifestObservation(
                check_id="CHK-01",
                outcome="PASSED",
                evidence_ref="test_report.txt",
                digest=report_digest,
            )
        ]
    )

    repo_coord = (cfg.repository_id, cfg.repository_owner_id)

    def hook(stage: str):
        if stage == "artifact_validation":
            new_cfg = cfg.model_copy(update={"generation": 2})
            reg[repo_coord] = new_cfg

    v.on_validation_stage = hook

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": manifest.model_dump(),
        "artifact_archive_base64": zip_b64,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 403
    assert exc.value.code == "CONNECTOR_GENERATION_CHANGED"


def test_rework_b1_connector_authority_change_during_validation_rejected(gateway_setup):
    """B1: Authority configuration mutated (tenant_id / workflow sha changed) during validation."""
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    cfg = gateway_setup["connector_config"]
    reg = gateway_setup["connector_registry"]
    now = gateway_setup["get_time"]()

    zip_bytes = make_zip_bytes({"test_report.txt": b"test content"})
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
    report_digest = hashlib.sha256(b"test content").hexdigest()

    manifest = make_valid_manifest(
        observations=[
            ManifestObservation(
                check_id="CHK-01",
                outcome="PASSED",
                evidence_ref="test_report.txt",
                digest=report_digest,
            )
        ]
    )

    repo_coord = (cfg.repository_id, cfg.repository_owner_id)

    def hook(stage: str):
        if stage == "artifact_validation":
            new_cfg = cfg.model_copy(update={"tenant_id": "tenant-other"})
            reg[repo_coord] = new_cfg

    v.on_validation_stage = hook

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": manifest.model_dump(),
        "artifact_archive_base64": zip_b64,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 403
    assert exc.value.code == "CONNECTOR_AUTHORITY_CHANGED"


def test_rework_b2_two_mib_closure_nested_manifest_dict_and_json_rejected(gateway_setup):
    """B2: Reproduced review defect: manifest with ~2 MiB closure path must be rejected
    on dict route, json route, and direct model validation.
    """
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()

    two_mb_path = "mas/" + "a" * (2 * 1024 * 1024)
    manifest_dict = make_valid_manifest().model_dump()
    manifest_dict["closures"] = {"F-01": [two_mb_path]}

    t = make_jwt(key_fixture=kp, override_clock=now)

    # 1. Dict route
    req_dict = {
        "manifest": manifest_dict,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc_dict:
        v.validate_submission(f"Bearer {t}", req_dict)

    assert exc_dict.value.status_code == 413
    assert exc_dict.value.code == "PAYLOAD_TOO_LARGE"

    # 2. JSON route (serialized JSON bytes)
    req_json = json.dumps(req_dict).encode("utf-8")
    with pytest.raises(GatewayError) as exc_json:
        v.validate_submission(f"Bearer {t}", req_json)

    assert exc_json.value.status_code == 413
    assert exc_json.value.code == "PAYLOAD_TOO_LARGE"

    # 3. Direct model validation
    from mas.pm.gateway.models import WitnessObservationSubmissionRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        WitnessObservationSubmissionRequest.model_validate(req_dict)


def test_rework_b2_manifest_size_exact_boundaries(gateway_setup):
    """B2: Exact boundary test for 1 MiB manifest size limit."""
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    t = make_jwt(key_fixture=kp, override_clock=now)

    target_limit = 1048576  # 1 MiB

    # 1. Exact 1 MiB passes
    base_m = make_valid_manifest().model_dump()
    base_m["closures"] = {"F-01": ["mas/"]}
    current_len = len(json.dumps(base_m).encode("utf-8"))
    needed = target_limit - current_len
    base_m["closures"] = {"F-01": ["mas/" + "a" * needed]}
    assert len(json.dumps(base_m).encode("utf-8")) == target_limit

    req_exact = {
        "manifest": base_m,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    resp = v.validate_submission(f"Bearer {t}", req_exact)
    assert resp.status == "VALIDATED_UNTRUSTED_OBSERVATION"

    # 2. 1 MiB + 1 byte fails
    base_m_over = make_valid_manifest().model_dump()
    base_m_over["closures"] = {"F-01": ["mas/" + "a" * (needed + 1)]}
    assert len(json.dumps(base_m_over).encode("utf-8")) == target_limit + 1
    req_over = {
        "manifest": base_m_over,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req_over)
    assert exc.value.status_code == 413
    assert exc.value.code == "PAYLOAD_TOO_LARGE"


def test_rework_b2_oversized_dict_and_json_envelopes_rejected(gateway_setup):
    """B2: Oversized envelopes (> 18 MiB) rejected across dict and json representations."""
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    t = make_jwt(key_fixture=kp, override_clock=now)

    # 1. Dict route > 18 MiB
    huge_dict = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
        "padding": "x" * (19 * 1024 * 1024),
    }
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", huge_dict)
    assert exc.value.status_code == 413
    assert exc.value.code == "PAYLOAD_TOO_LARGE"

    # 2. JSON route > 18 MiB
    huge_json = b'{"data": "' + b"x" * (19 * 1024 * 1024) + b'"}'
    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", huge_json)
    assert exc.value.status_code == 413
    assert exc.value.code == "PAYLOAD_TOO_LARGE"


def test_rework_b2_valid_12_mib_archive_envelope_accepted(gateway_setup):
    """B2: Valid archive with normal manifest fits inside 18 MiB envelope and is accepted."""
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    t = make_jwt(key_fixture=kp, override_clock=now)

    raw_file = b"Valid report content line\n"
    report_digest = hashlib.sha256(raw_file).hexdigest()

    manifest = make_valid_manifest(
        observations=[
            ManifestObservation(
                check_id="CHK-01",
                outcome="PASSED",
                evidence_ref="test_report.txt",
                digest=report_digest,
            )
        ]
    )

    zip_bytes = make_zip_bytes({"test_report.txt": raw_file})
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")

    req = {
        "manifest": manifest.model_dump(),
        "artifact_archive_base64": zip_b64,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    resp = v.validate_submission(f"Bearer {t}", req)
    assert resp.status == "VALIDATED_UNTRUSTED_OBSERVATION"
    assert resp.artifacts_validated is True


def test_rework_b3_public_errors_and_envelope_never_leak_sentinel_or_exceptions(gateway_setup):
    """B3: Inject an internal dependency failure with message '/private/host/keys SECRET_SENTINEL'.
    Verify public GatewayError.to_envelope() contains stable code/message and ZERO sentinel text.
    """
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()

    sentinel = "/private/host/keys SECRET_SENTINEL"

    def bad_verify(_token):
        raise RuntimeError(sentinel)

    v.token_verifier.verify_token = bad_verify

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 500
    assert exc.value.code == "INTERNAL_ERROR"

    envelope = exc.value.to_envelope()
    assert envelope["status"] == "ERROR"
    assert envelope["code"] == "INTERNAL_ERROR"
    assert envelope["message"] == "An internal gateway error occurred during observation validation."
    assert sentinel not in str(envelope)
    assert "/private/host/keys" not in str(envelope)
    assert "SECRET_SENTINEL" not in str(envelope)
    assert sentinel not in exc.value.message


def test_rework_b3_sentinels_across_jwks_parsing_schema_archive_handlers(gateway_setup):
    """B3: Test injected sentinels across JWKS, parsing, schema, and archive handlers.
    None must ever leak into the public error envelope.
    """
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    sentinel = "/secret/root/store SENSITIVE_DATA_12345"

    # 1. JWKS fetcher error
    orig_fetcher = v.jwks_cache._fetcher
    def bad_fetcher(_url):
        raise RuntimeError(f"Connection error to {sentinel}")

    v.jwks_cache._fetcher = bad_fetcher
    try:
        t = make_jwt(key_fixture=kp, kid="new-uncached-kid", override_clock=now)
        req = {
            "manifest": make_valid_manifest().model_dump(),
            "fencing_token": 1,
            "github_run_id": "1029384756",
            "github_run_attempt": 1,
        }
        with pytest.raises(GatewayError) as exc_jwks:
            v.validate_submission(f"Bearer {t}", req)

        env_jwks = exc_jwks.value.to_envelope()
        assert env_jwks["code"] == "JWKS_UNAVAILABLE"
        assert sentinel not in str(env_jwks)
        assert sentinel not in exc_jwks.value.message
    finally:
        v.jwks_cache._fetcher = orig_fetcher
        v.jwks_cache._last_failed_at = 0.0

    # 2. JSON parsing error with embedded sentinel
    bad_json = f'{{"manifest": "{sentinel}", broken_json: '.encode("utf-8")
    t_valid = make_jwt(key_fixture=kp, override_clock=now)
    with pytest.raises(GatewayError) as exc_json:
        v.validate_submission(f"Bearer {t_valid}", bad_json)

    env_json = exc_json.value.to_envelope()
    assert env_json["code"] == "INVALID_REQUEST_BODY"
    assert sentinel not in str(env_json)

    # 3. Schema validation with sensitive input in unexpected field
    hostile_req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
        "injected_sensitive_field": sentinel,
    }
    with pytest.raises(GatewayError) as exc_schema:
        v.validate_submission(f"Bearer {t_valid}", hostile_req)

    env_schema = exc_schema.value.to_envelope()
    assert env_schema["code"] == "EXTRA_FIELDS_FORBIDDEN"
    assert sentinel not in str(env_schema)

    # 4. Archive validation error with embedded sentinel
    import mas.pm.gateway.validator as gv_mod
    orig_val = gv_mod.validate_artifact_archive

    def bad_val(_archive_bytes, observations=None):
        from mas.pm.delivery_validator import DeliveryValidatorError
        raise DeliveryValidatorError(f"Corrupt entry at {sentinel}")

    gv_mod.validate_artifact_archive = bad_val
    try:
        zip_bytes = make_zip_bytes({"test_report.txt": b"content"})
        zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
        req_arch = {
            "manifest": make_valid_manifest(
                observations=[
                    ManifestObservation(
                        check_id="CHK-01",
                        outcome="PASSED",
                        evidence_ref="test_report.txt",
                        digest=hashlib.sha256(b"content").hexdigest(),
                    )
                ]
            ).model_dump(),
            "artifact_archive_base64": zip_b64,
            "fencing_token": 1,
            "github_run_id": "1029384756",
            "github_run_attempt": 1,
        }
        with pytest.raises(GatewayError) as exc_arch:
            v.validate_submission(f"Bearer {t_valid}", req_arch)

        env_arch = exc_arch.value.to_envelope()
        assert env_arch["code"] == "INVALID_ARTIFACT_ARCHIVE"
        assert sentinel not in str(env_arch)
        assert sentinel not in exc_arch.value.message
    finally:
        gv_mod.validate_artifact_archive = orig_val


def test_connector_registry_thread_safe_operations():
    """Verify ConnectorRegistry synchronization, mapping protocols, and snapshot behavior."""
    from mas.pm.gateway.models import ConnectorRegistry, GitHubConnectorConfig

    cfg1 = GitHubConnectorConfig(
        tenant_id="tenant-1",
        project_id="proj-1",
        repository_id="111",
        repository_owner_id="222",
        approved_workflow_repo="org/repo",
        approved_workflow_path=".github/workflows/gate.yml",
        approved_workflow_sha=HEX40_DEFAULT,
        generation=1,
    )
    reg = ConnectorRegistry({("111", "222"): cfg1})
    assert len(reg) == 1
    assert ("111", "222") in reg
    assert reg.get(("111", "222")) == cfg1
    assert reg[("111", "222")] == cfg1

    # Replacement
    cfg2 = cfg1.model_copy(update={"generation": 2, "status": "REVOKED"})
    reg.register(cfg2)
    assert reg.get(("111", "222")).generation == 2
    assert reg.get(("111", "222")).status == "REVOKED"

    # Snapshot isolation
    snap = reg.snapshot()
    assert snap[("111", "222")] == cfg2
    cfg3 = cfg1.model_copy(update={"generation": 3})
    reg[("111", "222")] = cfg3
    assert snap[("111", "222")].generation == 2
    assert reg.get(("111", "222")).generation == 3

    # Removal
    removed = reg.remove(("111", "222"))
    assert removed == cfg3
    assert ("111", "222") not in reg
    assert reg.get(("111", "222")) is None


def test_rework2_b1_event_and_ref_mutation_rejected_same_generation(gateway_setup):
    """B1: Replace connector entry during artifact validation with permitted_events=[] and permitted_ref_patterns={}
    preserving generation (1). Must be rejected with 403 CONNECTOR_AUTHORITY_CHANGED.
    """
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    cfg = gateway_setup["connector_config"]
    reg = gateway_setup["connector_registry"]
    now = gateway_setup["get_time"]()

    zip_bytes = make_zip_bytes({"test_report.txt": b"test content"})
    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")
    report_digest = hashlib.sha256(b"test content").hexdigest()

    manifest = make_valid_manifest(
        observations=[
            ManifestObservation(
                check_id="CHK-01",
                outcome="PASSED",
                evidence_ref="test_report.txt",
                digest=report_digest,
            )
        ]
    )

    repo_coord = (cfg.repository_id, cfg.repository_owner_id)

    # 1. Mutate permitted_events to empty list preserving generation 1
    def hook_events(stage: str):
        if stage == "artifact_validation":
            mutated_cfg = cfg.model_copy(update={"permitted_events": [], "permitted_ref_patterns": {}})
            reg[repo_coord] = mutated_cfg

    v.on_validation_stage = hook_events

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": manifest.model_dump(),
        "artifact_archive_base64": zip_b64,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 403
    assert exc.value.code == "CONNECTOR_AUTHORITY_CHANGED"
    env = exc.value.to_envelope()
    assert env["code"] == "CONNECTOR_AUTHORITY_CHANGED"

    # Reset registry to original config before running part 2
    reg[repo_coord] = cfg

    # 2. Mutate permitted_ref_patterns preserving generation 1
    def hook_refs(stage: str):
        if stage == "artifact_validation":
            mutated_cfg = cfg.model_copy(
                update={"permitted_ref_patterns": {"pull_request": r"^refs/heads/strictly_main$"}}
            )
            reg[repo_coord] = mutated_cfg

    v.on_validation_stage = hook_refs

    with pytest.raises(GatewayError) as exc2:
        v.validate_submission(f"Bearer {t}", req)

    assert exc2.value.status_code == 403
    assert exc2.value.code == "CONNECTOR_AUTHORITY_CHANGED"


def test_rework2_b1_monotonic_generation_enforced_on_registry_update():
    """B1: Monotonically advancing generation is strictly enforced on ConnectorRegistry.update() and __setitem__."""
    from mas.pm.gateway.models import ConnectorRegistry, GitHubConnectorConfig

    cfg1 = GitHubConnectorConfig(
        tenant_id="tenant-1",
        project_id="proj-1",
        repository_id="111",
        repository_owner_id="222",
        approved_workflow_repo="org/repo",
        approved_workflow_path=".github/workflows/gate.yml",
        approved_workflow_sha=HEX40_DEFAULT,
        generation=1,
    )
    repo_coord = (cfg1.repository_id, cfg1.repository_owner_id)
    reg = ConnectorRegistry({repo_coord: cfg1})

    # Same generation update rejected
    cfg_same = cfg1.model_copy(update={"status": "REVOKED", "generation": 1})
    with pytest.raises(ValueError, match="Monotonically advancing generation required"):
        reg.update(cfg_same)

    # Subscript assignment also rejected for same generation
    with pytest.raises(ValueError, match="Monotonically advancing generation required"):
        reg[repo_coord] = cfg_same

    # Existing policy strictly preserved
    snap = reg.get_snapshot(repo_coord)
    assert snap is not None
    assert snap.generation == 1
    assert snap.status == "ACTIVE"

    # Lower generation update rejected
    cfg_lower = cfg1.model_copy(update={"generation": 0})
    with pytest.raises(ValueError, match="Monotonically advancing generation required"):
        reg.update(cfg_lower)

    # Monotonically advancing generation (generation=2) accepted
    cfg_adv = cfg1.model_copy(update={"generation": 2, "status": "REVOKED"})
    reg.update(cfg_adv)
    snap2 = reg.get_snapshot(repo_coord)
    assert snap2 is not None
    assert snap2.generation == 2
    assert snap2.status == "REVOKED"


def test_rework2_b1_caller_in_place_mutation_isolated_from_registry():
    """B1: In-place mutation of caller configuration objects does not alter stored registry snapshots."""
    from mas.pm.gateway.models import ConnectorRegistry, GitHubConnectorConfig

    cfg = GitHubConnectorConfig(
        tenant_id="tenant-1",
        project_id="proj-1",
        repository_id="333",
        repository_owner_id="444",
        approved_workflow_repo="org/repo",
        approved_workflow_path=".github/workflows/gate.yml",
        approved_workflow_sha=HEX40_DEFAULT,
        generation=1,
    )
    repo_coord = (cfg.repository_id, cfg.repository_owner_id)
    reg = ConnectorRegistry()
    reg.register(cfg)

    initial_digest = reg.get_snapshot(repo_coord).canonical_digest

    # In-place mutations on caller objects
    cfg.permitted_events.append("unapproved_event")
    cfg.permitted_ref_patterns["unapproved_event"] = ".*"

    stored_snap = reg.get_snapshot(repo_coord)
    assert "unapproved_event" not in stored_snap.permitted_events
    assert "unapproved_event" not in stored_snap.permitted_ref_patterns_dict
    assert stored_snap.canonical_digest == initial_digest

    # Stored snapshot is immutable
    with pytest.raises(Exception):
        stored_snap.status = "REVOKED"  # FrozenInstanceError


def test_rework2_b2_sensitive_input_sentinel_in_validation_errors_excluded_from_diagnostics_and_audit(gateway_setup):
    """B2: Supply github_run_attempt='RAW_PAYLOAD_SECRET_SENTINEL'.
    Request must be rejected with 422 INVALID_MANIFEST_STRUCTURE.
    Neither the diagnostic nor the audit log must contain the raw sentinel.
    """
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    audit_events: list[dict[str, Any]] = []

    v.audit_logger = lambda evt: audit_events.append(evt)

    sentinel = "RAW_PAYLOAD_SECRET_SENTINEL"
    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": sentinel,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_MANIFEST_STRUCTURE"

    # 1. Private diagnostic must NOT contain raw input sentinel
    assert sentinel not in (exc.value.diagnostic or "")
    assert "field=github_run_attempt" in (exc.value.diagnostic or "")
    assert "error=" in (exc.value.diagnostic or "")

    # 2. Public error envelope must NOT contain raw sentinel
    env = exc.value.to_envelope()
    assert sentinel not in str(env)
    assert sentinel not in exc.value.message

    # 3. Audit logger callback must NEVER receive the raw sentinel
    assert len(audit_events) == 1
    audit_log_str = str(audit_events)
    assert sentinel not in audit_log_str


def test_rework2_b2_sensitive_input_in_nested_manifest_fields_excluded_from_diagnostics_and_audit(gateway_setup):
    """B2: Supply invalid nested manifest field containing a secret sentinel.
    Verify neither diagnostic nor audit log leaks the secret.
    """
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    audit_events: list[dict[str, Any]] = []

    v.audit_logger = lambda evt: audit_events.append(evt)

    sentinel = "SECRET_NESTED_SENTINEL_OUTCOME"
    manifest_dict = make_valid_manifest().model_dump()
    manifest_dict["observations"][0]["outcome"] = sentinel

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": manifest_dict,
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 422
    assert exc.value.code == "INVALID_MANIFEST_STRUCTURE"
    assert sentinel not in (exc.value.diagnostic or "")
    assert sentinel not in str(exc.value.to_envelope())
    assert sentinel not in str(audit_events)


def test_rework2_b2_audit_callback_exception_logging_does_not_echo_secret(gateway_setup, caplog):
    """B2: Configured audit callback raises an exception with a secret message.
    Logging must NOT echo the exception message text.
    """
    import logging

    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()

    secret = "TOP_SECRET_AUDIT_CALLBACK_FAIL"

    def exploding_logger(_evt):
        raise RuntimeError(f"Audit backend down: {secret}")

    v.audit_logger = exploding_logger

    t = make_jwt(key_fixture=kp, override_clock=now)
    # Valid request
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with caplog.at_level(logging.WARNING):
        resp = v.validate_submission(f"Bearer {t}", req)

    assert resp.status == "VALIDATED_UNTRUSTED_OBSERVATION"
    # Ensure secret is NOT in caplog
    assert secret not in caplog.text
    assert "Audit logging callback failed: RuntimeError" in caplog.text


def test_rework2_b2_dependency_exception_diagnostic_is_input_free(gateway_setup):
    """B2: Dependency exception details (database/system paths/sentinels) are excluded from diagnostics."""
    v = gateway_setup["validator"]
    kp = gateway_setup["key_pair"]
    now = gateway_setup["get_time"]()
    audit_events: list[dict[str, Any]] = []
    v.audit_logger = lambda evt: audit_events.append(evt)

    secret = "/var/secrets/creds.json TOP_SECRET_DB_KEY"

    def exploding_iam(_tenant_id):
        raise ConnectionError(f"Connection failed to {secret}")

    v.iam.get_tenant = exploding_iam

    t = make_jwt(key_fixture=kp, override_clock=now)
    req = {
        "manifest": make_valid_manifest().model_dump(),
        "fencing_token": 1,
        "github_run_id": "1029384756",
        "github_run_attempt": 1,
    }

    with pytest.raises(GatewayError) as exc:
        v.validate_submission(f"Bearer {t}", req)

    assert exc.value.status_code == 500
    assert exc.value.code == "INTERNAL_ERROR"
    assert exc.value.diagnostic == "ConnectionError: error_occurred"
    assert secret not in (exc.value.diagnostic or "")
    assert secret not in str(exc.value.to_envelope())
    assert secret not in str(audit_events)



