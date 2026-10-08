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
