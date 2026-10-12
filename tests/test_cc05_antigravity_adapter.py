import os
import sys
import threading

import pytest

from mas.pm.adapters.antigravity import (
    AntigravityExecutionAdapter,
    sanitize_environment,
)
from mas.pm.worker import AdapterExecutionRequest


def test_antigravity_adapter_model_validation():
    adapter = AntigravityExecutionAdapter(model="gemini-3.8-flash-high", dynamic_model_check=False)
    assert adapter.model == "gemini-3.8-flash-high"
    assert adapter.supports_bounded_stop is True

    with pytest.raises(ValueError, match="not in allowed/available models"):
        AntigravityExecutionAdapter(
            model="nonexistent-model-xyz",
            allowed_models={"gemini-3.8-flash-high"},
            dynamic_model_check=False,
        )


def test_antigravity_adapter_workspace_validation(tmp_path):
    adapter = AntigravityExecutionAdapter(dynamic_model_check=False)
    req = AdapterExecutionRequest(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="issue-1",
        task_id="task-1",
        attempt_id="att-1",
        attempt_seq=1,
        fencing_token=1,
        runtime_type="antigravity",
        prompt="build something",
        workspace_path=str(tmp_path / "nonexistent_dir"),
    )
    res = adapter.execute(req, run_id="run-1")
    assert res.status == "FAILED"
    assert res.exit_code == 1
    assert "Invalid workspace directory" in res.error_details["error"]


def test_antigravity_adapter_sanitizes_environment():
    # Verify that verifier/reviewer secrets are strictly stripped from child process environment
    dirty_env = {
        "PATH": "/usr/bin:/bin",
        "MAS_EVIDENCE_SECRET": "top-secret-signing-key",
        "GITHUB_TOKEN": "ghp_secrettoken123",
        "HTTP_PROXY": "http://127.0.0.1:8080",
        "SSL_CERT_FILE": "/etc/ssl/certs/ca-certificates.crt",
        "CUSTOM_SECRET": "should-be-removed",
    }
    clean = sanitize_environment(dirty_env, extra_vars={"AGY_HEADLESS": "1"})

    assert "MAS_EVIDENCE_SECRET" not in clean
    assert "GITHUB_TOKEN" not in clean
    assert "CUSTOM_SECRET" not in clean
    assert clean["PATH"] == "/usr/bin:/bin"
    assert clean["HTTP_PROXY"] == "http://127.0.0.1:8080"
    assert clean["SSL_CERT_FILE"] == "/etc/ssl/certs/ca-certificates.crt"
    assert clean["AGY_HEADLESS"] == "1"


def test_antigravity_adapter_strips_secret_from_child_process(tmp_path):
    # Test script that checks if MAS_EVIDENCE_SECRET leaked into child
    script_path = tmp_path / "check_leak.py"
    output_file = tmp_path / "env_check.txt"
    script_path.write_text(
        "import os\n"
        "secret = os.environ.get('MAS_EVIDENCE_SECRET', 'NOT_PRESENT')\n"
        "with open('" + str(output_file) + "', 'w') as f:\n"
        "    f.write(secret)\n"
    )

    old_secret = os.environ.get("MAS_EVIDENCE_SECRET")
    os.environ["MAS_EVIDENCE_SECRET"] = "do-not-leak-this-secret"
    try:
        adapter = AntigravityExecutionAdapter(
            simulate_command=[sys.executable, str(script_path)],
            dynamic_model_check=False,
        )
        req = AdapterExecutionRequest(
            tenant_id="tenant-1",
            project_id="proj-1",
            issue_id="issue-1",
            task_id="task-1",
            attempt_id="att-1",
            attempt_seq=1,
            fencing_token=1,
            runtime_type="antigravity",
            prompt="check leak",
            workspace_path=str(tmp_path),
        )
        res = adapter.execute(req, run_id="run-1")
        assert res.exit_code == 0
        assert output_file.read_text().strip() == "NOT_PRESENT"
    finally:
        if old_secret is not None:
            os.environ["MAS_EVIDENCE_SECRET"] = old_secret
        else:
            os.environ.pop("MAS_EVIDENCE_SECRET", None)


def test_antigravity_adapter_simulated_success(tmp_path):
    script_path = tmp_path / "fake_agy_success.py"
    script_path.write_text(
        "import json, sys\n"
        "print(json.dumps({'type': 'INIT', 'session_id': 'sess-12345'}), flush=True)\n"
        "print(json.dumps({'type': 'PROGRESS', 'message': 'working'}), flush=True)\n"
        "print(json.dumps({'type': 'RESULT', 'candidate_commit_sha': 'c0ffee1234567890abcdef1234567890abcdef12', 'tokens_billed': 150}), flush=True)\n"
        "sys.exit(0)\n"
    )

    adapter = AntigravityExecutionAdapter(
        simulate_command=[sys.executable, str(script_path)],
        dynamic_model_check=False,
    )

    req = AdapterExecutionRequest(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="issue-1",
        task_id="task-1",
        attempt_id="att-1",
        attempt_seq=1,
        fencing_token=1,
        runtime_type="antigravity",
        prompt="do task",
        workspace_path=str(tmp_path),
    )

    emitted_events = []
    def on_event(ev_type, ev_data):
        emitted_events.append((ev_type, ev_data))

    res = adapter.execute(req, run_id="run-1", emit_event=on_event)

    assert res.status == "SUCCEEDED"
    assert res.exit_code == 0
    assert res.runtime_session_id == "sess-12345"
    assert res.candidate_commit_sha == "c0ffee1234567890abcdef1234567890abcdef12"
    assert res.tokens_billed == 150
    assert len(emitted_events) == 3


def test_antigravity_adapter_simulated_failure(tmp_path):
    script_path = tmp_path / "fake_agy_fail.py"
    script_path.write_text(
        "import json, sys\n"
        "print(json.dumps({'type': 'INIT', 'session_id': 'sess-fail'}), flush=True)\n"
        "sys.stderr.write('fatal runtime error\\n')\n"
        "sys.exit(2)\n"
    )

    adapter = AntigravityExecutionAdapter(
        simulate_command=[sys.executable, str(script_path)],
        dynamic_model_check=False,
    )

    req = AdapterExecutionRequest(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="issue-1",
        task_id="task-1",
        attempt_id="att-1",
        attempt_seq=1,
        fencing_token=1,
        runtime_type="antigravity",
        prompt="do task",
        workspace_path=str(tmp_path),
    )

    res = adapter.execute(req, run_id="run-1")
    assert res.status == "FAILED"
    assert res.exit_code == 2
    assert res.runtime_session_id == "sess-fail"
    assert res.candidate_commit_sha is None
    assert "fatal runtime error" in res.error_details["stderr"]


def test_antigravity_adapter_descendant_termination_on_cancellation(tmp_path):
    # Script spawns an uncooperative background child process that ignores SIGTERM
    marker_file = tmp_path / "late_write.txt"
    script_path = tmp_path / "spawn_uncooperative_child.py"
    script_path.write_text(
        "import subprocess, sys, time, signal\n"
        "child_code = '''\n"
        "import time, signal\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "time.sleep(2)\n"
        "with open('" + str(marker_file) + "', 'w') as f:\n"
        "    f.write('late write')\n"
        "'''\n"
        "proc = subprocess.Popen([sys.executable, '-c', child_code])\n"
        "time.sleep(10)\n"
    )

    adapter = AntigravityExecutionAdapter(
        simulate_command=[sys.executable, str(script_path)],
        dynamic_model_check=False,
    )

    req = AdapterExecutionRequest(
        tenant_id="tenant-1",
        project_id="proj-1",
        issue_id="issue-1",
        task_id="task-1",
        attempt_id="att-1",
        attempt_seq=1,
        fencing_token=1,
        runtime_type="antigravity",
        prompt="spawn descendant",
        workspace_path=str(tmp_path),
        timeout_seconds=5.0,
    )

    stop_evt = threading.Event()
    # Trigger stop signal after 0.2s
    threading.Timer(0.2, stop_evt.set).start()

    res = adapter.execute(req, run_id="run-1", stop_event=stop_evt)
    assert res.status == "CANCELED"
    assert res.exit_code == 130

    # Wait to ensure child was truly killed by SIGKILL escalation and could not write file
    import time
    time.sleep(2.5)
    assert not marker_file.exists(), "Descendant process survived and performed late file write!"
