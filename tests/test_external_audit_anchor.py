"""External HTTPS witness acceptance: rollback, forks, crashes and transport attacks."""
import hashlib
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from mas.audit_anchor import AnchorError, HTTPAuditAnchor
from mas.audit_witness import WitnessStore
from mas.iam import MultiTenantIAM, StandardRole

KEY = "private-coordinator-test-key-" * 2
WITNESS_KEY = b"independently-owned-witness-test-key-" * 2
NAMESPACE = "test-authority"
ADMIN = {StandardRole.TENANT_ADMIN.value}


@pytest.fixture(scope="module")
def tls(tmp_path_factory):
    root = tmp_path_factory.mktemp("witness-tls")
    cert, key = root / "cert.pem", root / "tls.key"
    result = subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(cert), "-days", "1", "-subj", "/CN=127.0.0.1", "-addext", "subjectAltName=IP:127.0.0.1"], capture_output=True, timeout=10)
    assert result.returncode == 0
    key.chmod(0o600)
    return cert, key


@pytest.fixture
def witness(tmp_path, tls, monkeypatch):
    cert, tls_key = tls
    monkeypatch.setenv("SSL_CERT_FILE", str(cert))
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    path = tmp_path / "independent-witness" / "state.sqlite"
    store = WitnessStore(path, WITNESS_KEY)
    writer = secrets.token_urlsafe(48)
    store.enroll(NAMESPACE, writer)
    processes = []
    script = '''import json,sys,ssl
from pathlib import Path
from mas.audit_witness import WitnessStore,server
p=json.load(sys.stdin)
context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(p['cert'],p['tls_key'])
witness=server(WitnessStore(p['database'],p['key'].encode()),'127.0.0.1',p['port'],context)
if p.get('mode','normal')!='normal':
 def attack(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  mode=p['mode']
  if mode=='redirect':
   self.send_response(307)
   self.send_header('Location','/v1/checkpoints/exfil')
   self.end_headers()
   with open(p['ready']+'.requests','a') as output:
    output.write('request\\n')
   return
  reply={'namespace':'test-authority','nonce':body['nonce'],'checkpoint':{'sequence':0,'hash':''}}
  if mode=='wrong_namespace':
   reply['namespace']='different'
  raw=json.dumps(reply).encode()
  if mode=='oversized':
   raw=b'x'*8192
  if mode=='duplicate':
   raw=b'{"nonce":"a","nonce":"b"}'
  if mode=='nonfinite':
   raw=b'{"checkpoint":NaN}'
  self.send_response(200)
  self.send_header('Content-Length',str(len(raw)))
  self.end_headers()
  if mode=='slow':
   import time
   for value in raw:
    self.wfile.write(bytes([value]))
    self.wfile.flush()
    time.sleep(0.15)
  else:
   self.wfile.write(raw)
 witness.RequestHandlerClass.do_POST=attack
Path(p['ready']).write_text(str(witness.server_port))
witness.serve_forever()
'''
    def start(port=0, mode="normal"):
        ready = tmp_path / ("ready-" + secrets.token_hex(4))
        process = subprocess.Popen([sys.executable, "-c", script], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        processes.append(process)
        process.stdin.write(json.dumps({"database": str(path), "key": WITNESS_KEY.decode(), "cert": str(cert), "tls_key": str(tls_key), "ready": str(ready), "port": port, "mode": mode}))
        process.stdin.close()
        deadline = time.monotonic() + 5
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists(), process.stderr.read() if process.poll() is not None else "Witness startup timed out"
        process.ready_file = ready
        return process, int(ready.read_text())
    try:
        process, port = start()
        anchor = HTTPAuditAnchor(f"https://127.0.0.1:{port}", NAMESPACE, writer)
        yield {"store": store, "path": path, "token": writer, "anchor": anchor, "process": process, "start": start, "port": port, "root": tmp_path, "cert": cert}
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            process.stderr.close()


def populated(witness):
    path = witness["root"] / "coordinator" / "iam.sqlite"
    iam = MultiTenantIAM(KEY, db_path=path, anchor=witness["anchor"])
    iam.create_tenant("alpha", "Alpha")
    iam.register_principal("alpha", "admin", roles=ADMIN)
    iam.register_principal("alpha", "reader")
    admin = iam.issue_token("alpha", "admin")
    reader = iam.issue_token("alpha", "reader")
    return iam, path, admin, reader


def test_full_identity_backup_rollback_cannot_revive_revoked_credentials(witness):
    iam, path, admin, reader = populated(witness)
    before = witness["root"] / "old.sqlite"
    iam.backup(before)
    sid = iam.verify_token(reader).token_id
    context = iam.verify_token(reader)
    iam.revoke_session(admin, sid)
    shutil.copyfile(before, path)
    with pytest.raises(AnchorError, match="external audit witness"):
        iam.verify_token(reader)
    assert not iam.authorize(context, "storage:read", "alpha", "urn:mas:tenant:alpha:workspace")
    with pytest.raises(AnchorError):
        MultiTenantIAM(KEY, db_path=path, anchor=witness["anchor"])


def test_known_current_backup_and_independent_witness_restart_work(witness):
    iam, path, admin, reader = populated(witness)
    iam.revoke_session(admin, iam.verify_token(reader).token_id)
    backup = witness["root"] / "current.sqlite"
    iam.backup(backup)
    witness["process"].terminate()
    witness["process"].wait(timeout=5)
    witness["start"](witness["port"])
    restored = MultiTenantIAM(KEY, db_path=backup, anchor=witness["anchor"])
    assert restored.verify_token(admin)
    with pytest.raises(PermissionError):
        restored.verify_token(reader)


def test_witness_outage_never_uses_a_cached_checkpoint(witness):
    iam, _, _, reader = populated(witness)
    context = iam.verify_token(reader)
    witness["process"].terminate()
    witness["process"].wait(timeout=5)
    with pytest.raises(AnchorError):
        iam.verify_token(reader)
    assert not iam.authorize(context, "storage:read", "alpha", "urn:mas:tenant:alpha:workspace")


def test_witness_downgrade_and_binding_change_rejected(witness):
    iam, path, _, _ = populated(witness)
    with pytest.raises(AnchorError, match="requires.*witness"):
        MultiTenantIAM(KEY, db_path=path)
    witness["store"].enroll("other-authority", witness["token"], iam.audit_checkpoint())
    other = HTTPAuditAnchor(witness["anchor"].url, "other-authority", witness["token"])
    with pytest.raises(AnchorError, match="binding"):
        MultiTenantIAM(KEY, db_path=path, anchor=other)


def test_preexisting_unanchored_instance_cannot_bypass_later_attachment(witness):
    path = witness["root"] / "coordinator" / "iam.sqlite"
    old = MultiTenantIAM(KEY, db_path=path)
    MultiTenantIAM(KEY, db_path=path, anchor=witness["anchor"])
    with pytest.raises(AnchorError):
        old.create_tenant("alpha", "Alpha")


def test_namespace_has_no_remote_reset_enroll_or_rewind(witness):
    store, token = witness["store"], witness["token"]
    read = {"action": "read", "nonce": "a" * 64}
    start = store.request(NAMESPACE, token, read)["checkpoint"]
    newer = {"sequence": 2, "hash": "b" * 64}
    response = store.request(NAMESPACE, token, {"action": "advance", "nonce": "a" * 64, "expected": start, "target": newer})
    assert response["checkpoint"] == newer
    with pytest.raises(ValueError, match="already exists"):
        store.enroll(NAMESPACE, token)
    with pytest.raises(AnchorError):
        store.request(NAMESPACE, token, {"action": "advance", "nonce": "a" * 64, "expected": newer, "target": start})
    with pytest.raises(AnchorError):
        store.request(NAMESPACE, token, {"action": "reset", "nonce": "a" * 64})
    with pytest.raises(AnchorError):
        HTTPAuditAnchor(witness["anchor"].url, "unregistered", token).verify(start)


def test_competing_checkpoint_forks_allow_only_one(witness):
    store, token = witness["store"], witness["token"]
    old = {"sequence": 0, "hash": ""}
    def advance(index):
        try:
            return store.request(NAMESPACE, token, {"action": "advance", "nonce": "a" * 64, "expected": old, "target": {"sequence": 1, "hash": hashlib.sha256(str(index).encode()).hexdigest()}})
        except AnchorError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(value is not None for value in pool.map(advance, range(8))) == 1


def test_wrong_credential_and_stale_nonce_responses_fail(witness, monkeypatch):
    anchor = witness["anchor"]
    with pytest.raises(AnchorError):
        HTTPAuditAnchor(anchor.url, NAMESPACE, "wrong-credential-" * 4).verify({"sequence": 0, "hash": ""})
    def replay(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout=json.dumps({"namespace": NAMESPACE, "nonce": "0" * 64, "checkpoint": {"sequence": 0, "hash": ""}}), stderr="")
    monkeypatch.setattr(subprocess, "run", replay)
    with pytest.raises(AnchorError, match="freshness"):
        anchor.verify({"sequence": 0, "hash": ""})


def test_audit_failure_does_not_publish_a_new_anchor(witness):
    iam, path, admin, reader = populated(witness)
    before = iam.audit_checkpoint()
    with sqlite3.connect(path) as db:
        db.execute("CREATE TRIGGER audit_failure BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT, 'audit failed'); END")
    with pytest.raises(sqlite3.IntegrityError):
        iam.revoke_session(admin, iam.verify_token(reader).token_id)
    witness["anchor"].verify(before)
    assert iam.verify_token(reader)


def test_commit_failure_after_anchor_advance_quarantines_old_authority(witness, monkeypatch):
    iam, path, admin, reader = populated(witness)
    sid = iam.verify_token(reader).token_id
    before = iam.audit_checkpoint()
    original_connect = sqlite3.connect
    class FailCommit(sqlite3.Connection):
        def commit(self):
            if self.total_changes:
                raise sqlite3.OperationalError("Injected disk failure at commit")
            return super().commit()
    def connect(database, *args, **kwargs):
        if str(database).startswith(path.as_uri()):
            kwargs["factory"] = FailCommit
        return original_connect(database, *args, **kwargs)
    monkeypatch.setattr(sqlite3, "connect", connect)
    with pytest.raises(sqlite3.OperationalError, match="disk failure"):
        iam.revoke_session(admin, sid)
    current = witness["store"].request(NAMESPACE, witness["token"], {"action": "read", "nonce": "a" * 64})["checkpoint"]
    assert current["sequence"] > before["sequence"]
    with pytest.raises(AnchorError):
        iam.verify_token(reader)
    with pytest.raises(AnchorError):
        MultiTenantIAM(KEY, db_path=path, anchor=witness["anchor"])


@pytest.mark.parametrize("phase", ["before_publish", "after_publish"])
def test_actual_process_death_on_either_side_of_witness_publication(witness, phase):
    iam, path, admin, reader = populated(witness)
    sid = iam.verify_token(reader).token_id
    before = iam.audit_checkpoint()
    script = """import json,sys,os
from mas.iam import MultiTenantIAM
from mas.audit_anchor import HTTPAuditAnchor
p=json.load(sys.stdin)
anchor=HTTPAuditAnchor(p['url'],p['namespace'],p['writer'])
iam=MultiTenantIAM(p['key'],db_path=p['database'],anchor=anchor)
original=anchor.advance
def crash(expected,target):
 if p['phase']=='after_publish':
  original(expected,target)
 os._exit(17)
anchor.advance=crash
iam.revoke_session(p['admin'],p['sid'])
"""
    result = subprocess.run([sys.executable, "-c", script], input=json.dumps({"url": witness["anchor"].url, "namespace": NAMESPACE, "writer": witness["token"], "key": KEY, "database": str(path), "phase": phase, "admin": admin, "sid": sid}), text=True, capture_output=True, timeout=15)
    assert result.returncode == 17, result.stderr
    if phase == "before_publish":
        witness["anchor"].verify(before)
        assert iam.verify_token(reader)  # No revocation was acknowledged.
    else:
        with pytest.raises(AnchorError):
            iam.verify_token(reader)
        with pytest.raises(AnchorError):
            MultiTenantIAM(KEY, db_path=path, anchor=witness["anchor"])


def test_advancement_ack_loss_is_quarantined_without_rewind(witness, monkeypatch):
    iam, _, admin, reader = populated(witness)
    sid = iam.verify_token(reader).token_id
    original = witness["anchor"].advance
    def lost_ack(expected, target):
        original(expected, target)
        raise AnchorError("Injected acknowledgement loss")
    monkeypatch.setattr(witness["anchor"], "advance", lost_ack)
    with pytest.raises(AnchorError, match="acknowledgement loss"):
        iam.revoke_session(admin, sid)
    with pytest.raises(AnchorError):
        iam.verify_token(reader)


def test_anchoring_an_existing_authority_requires_reviewed_enrollment(witness):
    path = witness["root"] / "legacy" / "iam.sqlite"
    old = MultiTenantIAM(KEY, db_path=path)
    old.create_tenant("alpha", "Alpha")
    initial = old.audit_checkpoint()
    with pytest.raises(AnchorError):
        MultiTenantIAM(KEY, db_path=path, anchor=witness["anchor"])
    witness["store"].enroll("reviewed-existing", witness["token"], initial)
    anchor = HTTPAuditAnchor(witness["anchor"].url, "reviewed-existing", witness["token"])
    upgraded = MultiTenantIAM(KEY, db_path=path, anchor=anchor)
    assert upgraded.get_tenant("alpha")
    with pytest.raises(AnchorError):
        old.get_tenant("alpha")


def test_transport_does_not_import_from_an_untrusted_working_directory(witness, tmp_path, monkeypatch):
    malicious = tmp_path / "untrusted"
    (malicious / "mas").mkdir(parents=True)
    marker = tmp_path / "imported-malicious-code"
    (malicious / "mas/__init__.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('unsafe import')")
    monkeypatch.chdir(malicious)
    witness["anchor"].verify({"sequence": 0, "hash": ""})
    assert not marker.exists()


@pytest.mark.parametrize("url", ["http://127.0.0.1:9043", "https://user:pass@example.org", "https://example.org?a=b", "https://example.org/#x", "https://example.org/path"])
def test_insecure_or_ambiguous_witness_urls_rejected(url):
    with pytest.raises(ValueError):
        HTTPAuditAnchor(url, NAMESPACE, "private-test-token-" * 3)


@pytest.mark.parametrize("mode", ["wrong_namespace", "oversized", "duplicate", "nonfinite", "redirect"])
def test_malformed_or_redirected_witness_responses_are_rejected(witness, mode):
    process, port = witness["start"](mode=mode)
    anchor = HTTPAuditAnchor(f"https://127.0.0.1:{port}", NAMESPACE, witness["token"])
    with pytest.raises(AnchorError):
        anchor.verify({"sequence": 0, "hash": ""})
    if mode == "redirect":
        assert process.ready_file.with_name(process.ready_file.name + ".requests").read_text().count("request") == 1


def test_untrusted_tls_certificate_is_not_bypassed(witness, monkeypatch):
    monkeypatch.setenv("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")
    with pytest.raises(AnchorError):
        witness["anchor"].verify({"sequence": 0, "hash": ""})


def test_slow_stream_is_killed_at_total_deadline(witness, monkeypatch):
    _, port = witness["start"](mode="slow")
    anchor = HTTPAuditAnchor(f"https://127.0.0.1:{port}", NAMESPACE, witness["token"], timeout=0.5)
    original = subprocess.Popen
    workers = []
    def capture(*args, **kwargs):
        process = original(*args, **kwargs)
        workers.append(process)
        return process
    monkeypatch.setattr(subprocess, "Popen", capture)
    start = time.monotonic()
    with pytest.raises(AnchorError):
        anchor.verify({"sequence": 0, "hash": ""})
    assert time.monotonic() - start < 2
    assert len(workers) == 1 and workers[0].poll() is not None


def test_partial_anchor_settings_do_not_silently_disable_anchoring(tmp_path, monkeypatch):
    monkeypatch.setenv("MAS_IAM_ANCHOR_URL", "https://witness.example.org")
    monkeypatch.delenv("MAS_IAM_ANCHOR_NAMESPACE", raising=False)
    monkeypatch.delenv("MAS_IAM_ANCHOR_TOKEN", raising=False)
    with pytest.raises(ValueError, match="requires URL"):
        MultiTenantIAM(KEY, db_path=tmp_path / "iam.sqlite")


def test_http_pm_api_denies_rollback_without_exposing_shared_routes(witness):
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    from mas.dashboard.server import DashboardServer
    from mas.organization.company import ConsultingEnterprise
    iam, path, admin, reader = populated(witness)
    old = witness["root"] / "old-http.sqlite"
    iam.backup(old)
    server = DashboardServer(ConsultingEnterprise(), port=0, iam=iam, tenant_id="alpha", tenant_root=witness["root"] / "tenant-work")
    server.start_background()
    def status():
        request = Request(f"http://127.0.0.1:{server.server.server_port}/api/pm/projects", headers={"Authorization": f"Bearer {reader}"})
        try:
            with urlopen(request, timeout=10) as response:
                return response.status
        except HTTPError as error:
            return error.code
    try:
        assert status() == 200
        iam.revoke_session(admin, iam.verify_token(reader).token_id)
        shutil.copyfile(old, path)
        assert status() == 403
    finally:
        server.shutdown()
    assert not server._thread.is_alive()


def test_stalled_tls_handshake_does_not_block_other_clients(witness):
    import socket
    from urllib.parse import urlsplit

    client = witness["anchor"]
    origin = urlsplit(client.url)
    with socket.create_connection((origin.hostname, origin.port), timeout=2) as stalled:
        client.verify({"sequence": 0, "hash": ""})
        stalled.settimeout(5)
        assert stalled.recv(1) == b""
