"""Adversarial checks for the actual no-mount execution boundary."""
import json
import subprocess
import threading
import time

import pytest

from mas.pm.adapters.antigravity import AntigravityExecutionAdapter, sanitize_environment, sanitize_payload
from mas.pm.adapters.boundary import ContainerBoundary, snapshot_workspace
from mas.pm.worker import AdapterExecutionRequest
from mas.swarm.contracts import OutputLimitError, SwarmError


@pytest.fixture(scope='module')
def image():
    probe = subprocess.run(['docker', '--host=unix:///var/run/docker.sock', 'image', 'inspect', 'python:3.12-slim', '--format', '{{.Id}}'], capture_output=True, text=True)
    if probe.returncode:
        pytest.skip('Pinned local Python execution image/Docker unavailable')
    return probe.stdout.strip()


def request(tmp_path, **changes):
    values = dict(tenant_id='tenant', project_id='project', issue_id='issue', task_id='task',
                  attempt_id='attempt', attempt_seq=1, fencing_token=1, runtime_type='antigravity',
                  prompt='fixture', workspace_path=str(tmp_path), path_whitelist=['source.py'], timeout_seconds=10)
    values.update(changes)
    return AdapterExecutionRequest(**values)


def adapter(image, command):
    return AntigravityExecutionAdapter(image=image, simulate_command=['python', '-c', command])


def test_environment_and_redaction():
    env = sanitize_environment({'HOME': '/secret/home', 'MAS_EVIDENCE_SECRET': 'secret', 'HTTPS_PROXY': 'https://proxy', 'SSL_CERT_FILE': '/ca'}, {'AGY_HEADLESS': '1'})
    assert 'HOME' not in env and 'MAS_EVIDENCE_SECRET' not in env
    assert env['HTTPS_PROXY'] == 'https://proxy' and env['SSL_CERT_FILE'] == '/ca'
    with pytest.raises(ValueError):
        sanitize_environment({}, {'MAS_EVIDENCE_SECRET': 'injected'})
    assert 'abc123' not in sanitize_payload('token=abc123')


def test_model_discovery_cannot_be_disabled(image):
    with pytest.raises(PermissionError, match='cannot be disabled'):
        AntigravityExecutionAdapter(image=image, dynamic_model_check=False)


def test_missing_cli_never_fabricates_model(image):
    with pytest.raises(SwarmError):
        AntigravityExecutionAdapter(image=image, binary_path='/missing/agy', allowed_models={'gemini-3.8-flash-high'})


@pytest.mark.parametrize('paths', [[], ['../outside'], ['/etc/passwd'], ['.git/config'], ['directory']])
def test_snapshot_rejects_unsafe_scope(tmp_path, paths):
    (tmp_path / 'directory').mkdir()
    with pytest.raises(ValueError):
        snapshot_workspace(tmp_path, paths)


def test_snapshot_rejects_symlinks(tmp_path):
    (tmp_path / 'source.py').symlink_to('/etc/passwd')
    with pytest.raises(ValueError, match='symlinks'):
        snapshot_workspace(tmp_path, ['source.py'])


def test_real_container_has_no_host_credentials_or_mounts(tmp_path, image, monkeypatch):
    marker = tmp_path / 'host-secret'
    marker.write_text('private fixture')
    monkeypatch.setenv('MAS_EVIDENCE_SECRET', 'private-test-key')
    code, out, _ = ContainerBoundary(image).run(['python', '-c',
        "import os,json; print(json.dumps({'secret':os.getenv('MAS_EVIDENCE_SECRET'),'home':os.getenv('HOME'),'host':os.path.exists("+repr(str(marker))+"),'socket':os.path.exists('/var/run/docker.sock')}))"])
    assert code == 0
    assert json.loads(out) == {'secret': None, 'home': '/tmp/home', 'host': False, 'socket': False}


def test_natural_parent_exit_leaves_no_orphan_boundary(tmp_path, image):
    boundary = ContainerBoundary(image)
    code, out, _ = boundary.run(['python', '-c',
        "import subprocess,sys; subprocess.Popen([sys.executable,'-c',\"import time; time.sleep(1); print('LATE_WRITE',flush=True)\"]); print('PARENT_DONE',flush=True)"])
    assert code == 0 and b'PARENT_DONE' in out and b'LATE_WRITE' not in out
    containers = subprocess.run(['docker', '--host=unix:///var/run/docker.sock', 'ps', '--all', '--quiet', '--filter', 'name=mas-coordinator-'], capture_output=True, text=True, check=True)
    assert containers.stdout.strip() == ''


def test_timeout_and_cancel_cleanup(image):
    boundary = ContainerBoundary(image)
    with pytest.raises(TimeoutError):
        boundary.run(['python', '-c', 'import time; time.sleep(20)'], timeout=.2)
    stop = threading.Event()
    timer = threading.Timer(.2, stop.set)
    timer.start()
    try:
        with pytest.raises(InterruptedError):
            boundary.run(['python', '-c', 'import time; time.sleep(20)'], stop=stop)
    finally:
        timer.join()
    containers = subprocess.run(['docker', '--host=unix:///var/run/docker.sock', 'ps', '--all', '--quiet', '--filter', 'name=mas-coordinator-'], capture_output=True, text=True, check=True)
    assert containers.stdout.strip() == ''


def test_single_line_output_is_bounded(image):
    with pytest.raises(OutputLimitError):
        ContainerBoundary(image, output_limit=4096).run(['python', '-c', "print('x'*100000)"])


@pytest.mark.parametrize('value', [float('inf'), float('-inf'), float('nan'), True, 0, -1, '1'])
def test_deadlines_reject_invalid_values(image, value):
    with pytest.raises(ValueError):
        ContainerBoundary(image).run(['python', '-c', 'pass'], timeout=value)


def test_runtime_result_is_measured_untrusted_observation(tmp_path, image):
    (tmp_path / 'source.py').write_text('pass')
    command = "import json; print(json.dumps({'session_id':'s'})); print(json.dumps({'type':'RESULT','tokens_billed':2,'candidate_commit_sha':'a'*40}))"
    events = []
    res = adapter(image, command).execute(request(tmp_path), 'run', lambda kind, value: events.append(value))
    assert res.status == 'SUCCEEDED' and res.tokens_billed == 2
    assert events[0]['domain'] == 'TEST'


@pytest.mark.parametrize('result', [
    {}, {'tokens_billed': True, 'candidate_commit_sha': 'a'*40},
    {'tokens_billed': -1, 'candidate_commit_sha': 'a'*40},
    {'tokens_billed': 10001, 'candidate_commit_sha': 'a'*40},
    {'tokens_billed': 1, 'candidate_commit_sha': 'HEAD'},
])
def test_unmeasured_or_invalid_runtime_never_settles(tmp_path, image, result):
    (tmp_path / 'source.py').write_text('pass')
    command = 'import json; print(json.dumps({"session_id":"s"})); print('+repr(json.dumps({'type':'RESULT', **result}))+')'
    res = adapter(image, command).execute(request(tmp_path), 'run')
    assert res.status == 'UNKNOWN_EXECUTION' and res.tokens_billed is None


def test_missing_image_has_no_host_execution_fallback(tmp_path):
    before = time.monotonic()
    with pytest.raises(SwarmError):
        ContainerBoundary('sha256:'+'0'*64).run(['python', '-c', "raise RuntimeError('must not run on host')"])
    assert time.monotonic() - before < 30
