"""Private, disposable test keys; never production credentials."""
import secrets
import pytest

@pytest.fixture(autouse=True)
def governance_test_keys(monkeypatch):
    monkeypatch.setenv("MAS_VERDICT_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("MAS_EVIDENCE_SECRET", secrets.token_hex(32))


@pytest.fixture(autouse=True)
def isolated_default_pm_database(tmp_path, monkeypatch):
    """Integration tests must not mutate the checkout's operational PM database."""
    import mas.pm.db as database
    import mas.pm.tools as tools
    monkeypatch.setattr(database, "DEFAULT_DB_PATH", tmp_path / "pm-default.db")
    monkeypatch.setattr(tools, "DEFAULT_DB_PATH", tmp_path / "pm-default.db")
    monkeypatch.setattr(tools, "_GLOBAL_DB", None)


@pytest.fixture(scope='session')
def coordinator_test_image():
    """Resolve test setup once; execution always uses the actual immutable image ID.

    An explicitly configured digest/ID never falls back to a different image.
    Offline evidence tests do not depend on this fixture or on Docker availability.
    """
    import json
    import os
    import re
    import subprocess

    configured = os.environ.get('MAS_COORDINATOR_TEST_IMAGE')
    if configured and not re.fullmatch(r'(?:[a-zA-Z0-9./:_-]+@)?sha256:[0-9a-f]{64}', configured):
        pytest.fail('MAS_COORDINATOR_TEST_IMAGE must be an immutable image ID or repository digest', pytrace=False)
    selector = configured or 'python:3.12-slim'
    try:
        probe = subprocess.run(['docker', '--host=unix:///var/run/docker.sock', 'image', 'inspect', selector],
                               capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        pytest.fail('Required container infrastructure unavailable: Docker client/daemon response', pytrace=False)
    if probe.returncode:
        pytest.fail('Required coordinator test image unavailable; no image or host fallback', pytrace=False)
    try:
        records = json.loads(probe.stdout)
        image_id = records[0]['Id'] if isinstance(records, list) and len(records) == 1 else None
    except (ValueError, KeyError, TypeError):
        image_id = None
    if not isinstance(image_id, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', image_id):
        pytest.fail('Docker returned an invalid immutable image identity', pytrace=False)
    if configured and configured.startswith('sha256:') and image_id != configured:
        pytest.fail('Configured image identity mismatch', pytrace=False)
    return image_id
