import sys
import threading

import pytest

from mas.pm.adapters.antigravity import AntigravityExecutionAdapter
from mas.pm.worker import AdapterExecutionRequest


def test_antigravity_adapter_model_validation():
    # Valid model succeeds initialization
    adapter = AntigravityExecutionAdapter(model="gemini-3.8-flash-high")
    assert adapter.model == "gemini-3.8-flash-high"
    assert adapter.supports_bounded_stop is True

    # Invalid / unvalidated model fails fast without silent substitution
    with pytest.raises(ValueError, match="not in allowed/available models"):
        AntigravityExecutionAdapter(model="nonexistent-model-xyz")


def test_antigravity_adapter_workspace_validation(tmp_path):
    adapter = AntigravityExecutionAdapter()
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


def test_antigravity_adapter_simulated_success(tmp_path):
    # Script that outputs stream-json events with early session_id, token usage, and candidate sha
    script_path = tmp_path / "fake_agy_success.py"
    script_path.write_text(
        "import json, sys\n"
        "print(json.dumps({'type': 'INIT', 'session_id': 'sess-12345'}), flush=True)\n"
        "print(json.dumps({'type': 'PROGRESS', 'message': 'working'}), flush=True)\n"
        "print(json.dumps({'type': 'RESULT', 'candidate_commit_sha': 'c0ffee1234567890abcdef1234567890abcdef12', 'tokens_billed': 150}), flush=True)\n"
        "sys.exit(0)\n"
    )

    adapter = AntigravityExecutionAdapter(
        simulate_command=[sys.executable, str(script_path)]
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
        simulate_command=[sys.executable, str(script_path)]
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


def test_antigravity_adapter_cancellation_and_process_cleanup(tmp_path):
    # Script spawns child and sleeps forever
    marker_file = tmp_path / "late_write.txt"
    script_path = tmp_path / "fake_agy_stall.py"
    script_path.write_text(
        "import time, sys, os\n"
        "try:\n"
        "    time.sleep(10)\n"
        "    with open('" + str(marker_file) + "', 'w') as f:\n"
        "        f.write('late')\n"
        "except BaseException:\n"
        "    pass\n"
    )

    adapter = AntigravityExecutionAdapter(
        simulate_command=[sys.executable, str(script_path)]
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
        prompt="stall task",
        workspace_path=str(tmp_path),
        timeout_seconds=5.0,
    )

    stop_evt = threading.Event()
    # Trigger stop after 0.2s
    threading.Timer(0.2, stop_evt.set).start()

    res = adapter.execute(req, run_id="run-1", stop_event=stop_evt)
    assert res.status == "CANCELED"
    assert res.exit_code == 130
    assert not marker_file.exists()


def test_antigravity_adapter_deadline_timeout(tmp_path):
    script_path = tmp_path / "fake_agy_sleep.py"
    script_path.write_text(
        "import time\n"
        "time.sleep(10)\n"
    )

    adapter = AntigravityExecutionAdapter(
        simulate_command=[sys.executable, str(script_path)]
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
        prompt="sleep task",
        workspace_path=str(tmp_path),
        timeout_seconds=0.3,
    )

    res = adapter.execute(req, run_id="run-1")
    assert res.status == "TIMEOUT"
    assert res.exit_code == 124
