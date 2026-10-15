"""Qualification tooling must fail without spending or overwriting evidence."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def qualification():
    path = Path(__file__).resolve().parents[1] / "scripts" / "qualify_live_coding.py"
    spec = importlib.util.spec_from_file_location("live_coding_qualification", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_provider_configuration_refuses_before_state_creation(qualification, tmp_path, monkeypatch):
    for name in ("MAS_SWARM_PROVIDER_URL", "MAS_SWARM_MODEL", "MAS_SWARM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    report, state = tmp_path / "report.json", tmp_path / "private-state"
    assert qualification.main(["--state-dir", str(state), "--report", str(report),
                               "--image", "sha256:" + "a" * 64]) == 1
    assert not state.exists()
    result = json.loads(report.read_text())
    assert result["status"] == "failed"
    assert result["production_deployed"] is False
    assert result["human_approval"] == "not_requested_or_granted"


@pytest.mark.parametrize("existing", ["report", "state"])
def test_existing_evidence_is_preserved_without_provider_calls(qualification, tmp_path, monkeypatch, existing):
    def forbidden(*args, **kwargs):
        pytest.fail("Must refuse existing paths before invoking qualification")

    monkeypatch.setattr(qualification, "qualify", forbidden)
    report, state = tmp_path / "report.json", tmp_path / "state"
    if existing == "report":
        report.write_text("original evidence")
    else:
        state.mkdir()
        (state / "original").write_text("original state")
    with pytest.raises(SystemExit) as error:
        qualification.main(["--state-dir", str(state), "--report", str(report),
                            "--image", "sha256:" + "a" * 64])
    assert error.value.code == 2
    if existing == "report":
        assert report.read_text() == "original evidence"
    else:
        assert (state / "original").read_text() == "original state"
        assert not report.exists()
