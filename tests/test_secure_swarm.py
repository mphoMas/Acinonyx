"""Security/state regressions and real-container integration.

The TLS provider fixture scripts model proposals; it is not evidence of live
model quality. Docker tests really execute the proposed code in containers.
"""

import asyncio
import json
import os
import secrets
import sqlite3
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from mas.swarm.cli import main, private_read, private_write
from mas.swarm.contracts import CandidateError, Limits, SwarmError, canonical, cases_contract, digest, strict_json
from mas.swarm.process import run_process
from mas.swarm.provider import LiveProvider
from mas.swarm.runtime import CodingSwarm
from mas.swarm.store import Store
from mas.swarm.worker import DockerWorker

CASES = [
    {"id": "positive", "input": [1, 2, 3], "expected": 6},
    {"id": "empty", "input": [], "expected": 0},
    {"id": "negative", "input": [-7, 2], "expected": -5},
]
SOURCE = "def solve(payload):\n    return sum(payload)\n"
IMAGE = os.environ.get("MAS_SWARM_TEST_IMAGE", "")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.db"
        self.key = secrets.token_bytes(32)
        self.store = Store(self.path, self.key)
        self.owner = self.store.provision("acme", "owner", "owner")
        self.requester = self.store.provision("acme", "developer", "requester")
        self.approver = self.store.provision("acme", "release_manager", "approver")
        self.foreign = self.store.provision("other", "owner", "owner")
        self.doc = self.store.submit(self.requester, "task-1", "Sum a list of numbers", CASES)

    def tearDown(self):
        self.tmp.cleanup()

    def ready(self):
        doc = self.store.claim(self.requester, self.doc["id"], "sha256:" + "a" * 64)
        for stage in ("coding", "verifying", "reviewing"):
            self.store.reserve(self.requester, doc["id"], doc["lease"], 100)
            self.store.settle(self.requester, doc["id"], doc["lease"], 75)
            doc = self.store.transition(self.requester, doc["id"], doc["lease"], stage)
        return self.store.transition(
            self.requester,
            doc["id"],
            doc["lease"],
            "awaiting_approval",
            source=SOURCE,
            candidate_hash=digest(SOURCE),
            review={"approved": True, "reason": "Reviewed"},
            evidence={
                "run_id": doc["id"],
                "candidate_hash": digest(SOURCE),
                "suite_hash": digest(CASES),
                "image": doc["image"],
                "results": [{"id": c["id"], "passed": True, "status": "passed"} for c in CASES],
                "finished": time.time(),
            },
        )

    def test_cross_tenant_and_anonymous_denied(self):
        for token in (self.foreign, "", secrets.token_urlsafe(32)):
            with self.assertRaises(PermissionError):
                self.store.get(token, self.doc["id"])
        with self.assertRaises(PermissionError):
            self.store.submit(self.approver, "other", "Goal", CASES)

    def test_idempotency_binds_request_and_detaches_mutable_input(self):
        self.assertEqual(self.store.submit(self.requester, "task-1", "Sum a list of numbers", CASES)["id"], self.doc["id"])
        with self.assertRaises(SwarmError):
            self.store.submit(self.requester, "task-1", "Different goal", CASES)
        self.doc["request"]["cases"][0]["expected"] = 999
        self.assertEqual(self.store.get(self.requester, self.doc["id"])["request"]["cases"][0]["expected"], 6)

    def test_revocation_and_expiration_rechecked(self):
        self.store.revoke(self.owner, "developer")
        with self.assertRaises(PermissionError):
            self.store.get(self.requester, self.doc["id"])
        expired = self.store.provision("acme", "expired", "requester", ttl=0.001)
        with patch("mas.swarm.store.time.time", return_value=time.time() + 1), self.assertRaises(PermissionError):
            self.store.get(expired, self.doc["id"])

    def test_only_one_claim_wins(self):
        errors = []

        def claim():
            try:
                self.store.claim(self.requester, self.doc["id"], "image")
            except SwarmError:
                errors.append(True)

        threads = [threading.Thread(target=claim) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(errors), 3)

    def test_invalid_transition_budget_and_lease(self):
        doc = self.store.claim(self.requester, self.doc["id"], "image")
        for state, lease in (("approved", doc["lease"]), ("coding", "spoof"), ("awaiting_approval", doc["lease"])):
            with self.assertRaises(SwarmError):
                self.store.transition(self.requester, doc["id"], lease, state)
        for amount in (-1, True, 0, 100000):
            with self.assertRaises(SwarmError):
                self.store.reserve(self.requester, doc["id"], doc["lease"], amount)
        self.store.reserve(self.requester, doc["id"], doc["lease"], 100)
        with self.assertRaises(SwarmError):
            self.store.settle(self.requester, doc["id"], doc["lease"], 101)
        self.assertEqual(self.store.get(self.requester, doc["id"])["usage"]["reserved"], 100)

    def test_human_approval_requires_exact_fresh_candidate_and_distinct_identity(self):
        doc = self.ready()
        with self.assertRaises(PermissionError):
            self.store.approve(self.requester, doc["id"], doc["candidate_hash"])
        with self.assertRaises(SwarmError):
            self.store.approve(self.approver, doc["id"], "wrong")
        with patch("mas.swarm.store.time.time", return_value=time.time() + 3601), self.assertRaises(SwarmError):
            self.store.approve(self.approver, doc["id"], doc["candidate_hash"])
        approved = self.store.approve(self.approver, doc["id"], doc["candidate_hash"])
        self.assertEqual(approved["state"], "approved")
        with self.assertRaises(SwarmError):
            self.store.approve(self.approver, doc["id"], doc["candidate_hash"])

    def test_empty_and_duplicate_tests_invalid(self):
        for cases in ([], [CASES[0], CASES[0]], [{"id": "x", "input": 0}]):
            with self.assertRaises(SwarmError):
                cases_contract(cases, Limits())

    def test_failed_audit_insert_rolls_back_transition(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TRIGGER refuse_audit BEFORE INSERT ON audit BEGIN SELECT RAISE(ABORT,'disk unavailable'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.claim(self.requester, self.doc["id"], "image")
        self.assertEqual(self.store.get(self.requester, self.doc["id"])["state"], "queued")

    def test_tampered_candidate_or_evidence_never_approves(self):
        doc = self.ready()
        with sqlite3.connect(self.path) as db:
            raw = db.execute("SELECT document FROM runs WHERE id=?", (doc["id"],)).fetchone()[0]
            altered = strict_json(raw)
            altered["source"] = "def solve(x): return 99"
            db.execute("UPDATE runs SET document=? WHERE id=?", (canonical(altered), doc["id"]))
        with self.assertRaises(SwarmError):
            self.store.approve(self.approver, doc["id"], doc["candidate_hash"])

    def test_tampered_audit_blocks_state_mutation(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE audit SET event='{}' WHERE seq=1")
        with self.assertRaises(SwarmError):
            self.store.claim(self.requester, self.doc["id"], "image")
        with self.assertRaises(SwarmError):
            self.store.get(self.requester, self.doc["id"])
        with sqlite3.connect(self.path) as db:
            raw = db.execute("SELECT document FROM runs WHERE id=?", (self.doc["id"],)).fetchone()[0]
        self.assertEqual(strict_json(raw)["state"], "queued")

    def test_identity_role_tampering_denied(self):
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE principals SET role='owner' WHERE subject='developer'")
        with self.assertRaises(SwarmError):
            self.store.get(self.requester, self.doc["id"])
        with sqlite3.connect(self.path) as db:
            raw = db.execute("SELECT document FROM runs WHERE id=?", (self.doc["id"],)).fetchone()[0]
        self.assertEqual(strict_json(raw)["state"], "queued")

    def test_identity_role_tampering_and_old_revocation_record_replay_denied(self):
        with sqlite3.connect(self.path) as db:
            old = db.execute("SELECT revoked,signature FROM principals WHERE subject='developer'").fetchone()
        self.store.revoke(self.owner, "developer")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE principals SET revoked=?,signature=? WHERE subject='developer'", old)
        with self.assertRaises(SwarmError):
            self.store.get(self.requester, self.doc["id"])

    def test_authentic_old_run_document_cannot_be_replayed(self):
        with sqlite3.connect(self.path) as db:
            old = db.execute("SELECT document,signature FROM runs WHERE id=?", (self.doc["id"],)).fetchone()
        self.store.claim(self.requester, self.doc["id"], "image")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE runs SET document=?,signature=? WHERE id=?", (*old, self.doc["id"]))
        with self.assertRaises(SwarmError):
            self.store.claim(self.requester, self.doc["id"], "image")

    def test_backup_restore_and_expired_lease_recovery(self):
        doc = self.store.claim(self.requester, self.doc["id"], "image")
        self.store.reserve(self.requester, doc["id"], doc["lease"], 100)
        backup = Path(self.tmp.name) / "backup.db"
        self.store.backup(backup)
        restored = Store(backup, self.key)
        self.assertEqual(restored.get(self.requester, doc["id"])["usage"]["reserved"], 100)
        with self.assertRaises(SwarmError):
            restored.interrupt(self.owner, doc["id"])
        with patch("mas.swarm.store.time.time", return_value=doc["lease_expires"] + 1):
            restored.interrupt(self.owner, doc["id"])
        self.assertEqual(restored.get(self.owner, doc["id"])["state"], "interrupted")
        with self.assertRaises(SwarmError):
            restored.claim(self.requester, doc["id"], "image")
        restored.verify_audit()

    def test_strict_json_and_policy_limits(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(SwarmError):
                strict_json(raw)
        for value in (-1, float("inf"), True, 601):
            with self.assertRaises(SwarmError):
                Limits(deadline_seconds=value)
        with self.assertRaises(SwarmError):
            DockerWorker("python:latest", Limits())
        with self.assertRaises(SwarmError):
            LiveProvider("http://localhost/v1", "model", "key")
        with self.assertRaises(SwarmError):
            Store(self.path, b"default")


class ProcessTests(unittest.IsolatedAsyncioTestCase):
    async def test_output_limit_and_descendant_timeout(self):
        import sys

        with self.assertRaises(SwarmError):
            await asyncio.wait_for(run_process([sys.executable, "-c", "print('x'*1000000)"], output_limit=256), timeout=5)
        start = time.monotonic()
        with self.assertRaises(asyncio.TimeoutError):
            await run_process([sys.executable, "-c", "import os,time; os.fork(); time.sleep(30)"], timeout=0.15)
        self.assertLess(time.monotonic() - start, 2)


class CLITests(unittest.TestCase):
    def test_private_credentials_and_cli_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "control"
            self.assertEqual(main(["--state-dir", str(root), "init", "--tenant", "company", "--subject", "ceo"]), 0)
            credential = root / "approver.token"
            self.assertEqual(
                main(["--state-dir", str(root), "enroll", "--subject", "release", "--role", "approver", "--out", str(credential)]), 0
            )
            self.assertEqual(credential.stat().st_mode & 0o777, 0o600)
            credential.chmod(0o644)
            with self.assertRaises(SwarmError):
                private_read(credential)
            link = root / "link"
            link.symlink_to(root / "signing.key")
            with self.assertRaises(OSError):
                private_read(link)
            with self.assertRaises(FileExistsError):
                private_write(root / "signing.key", b"overwrite")


@unittest.skipUnless(IMAGE, "Set MAS_SWARM_TEST_IMAGE to run actual Docker integration")
class DockerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.worker = DockerWorker(IMAGE, replace(Limits(), worker_seconds=3))
        self.run_id = "test-" + secrets.token_hex(12)

    async def test_real_execution_and_type_sensitive_results(self):
        self.assertEqual(await self.worker.evaluate(SOURCE, [2, 3], self.run_id), 5)
        self.assertNotEqual(canonical(True), canonical(1))

    async def test_filesystem_and_environment_isolation(self):
        secret = "host-only-canary"
        with patch.dict(os.environ, {"SWARM_HOST_SECRET": secret}):
            self.worker = DockerWorker(IMAGE, self.worker.limits)
            result = await self.worker.evaluate(
                """import os
def solve(x):
    return {'secret':os.getenv('SWARM_HOST_SECRET'),'host':os.path.exists('/workspace'),
            'socket':os.path.exists('/var/run/docker.sock'),'uid':os.getuid()}
""",
                None,
                self.run_id,
            )
        self.assertEqual(result, {"secret": None, "host": False, "socket": False, "uid": 65534})
        with self.assertRaises(SwarmError):
            await self.worker.evaluate("def solve(x):\n open('/etc/swarm-escape','w').write('x')\n return 1", None, self.run_id)

    async def test_no_network_output_overflow_timeout_and_cleanup(self):
        result = await self.worker.evaluate(
            """import socket
def solve(x):
    try:
        socket.create_connection(('1.1.1.1',443),timeout=0.1)
        return 'escaped'
    except OSError:
        return 'blocked'
""",
            None,
            self.run_id,
        )
        self.assertEqual(result, "blocked")
        with self.assertRaises(SwarmError):
            await self.worker.evaluate("def solve(x): return 'x'*100000", None, self.run_id)
        with self.assertRaises(CandidateError):
            await self.worker.evaluate("import os,time\ndef solve(x):\n os.fork()\n time.sleep(30)", None, self.run_id)
        rc, out, _ = await self.worker._docker("ps", "--all", "--quiet", "--filter", f"label=acinonyx.swarm.run={self.run_id}")
        self.assertEqual((rc, out), (0, b""))

    async def test_memory_exhaustion_rejected_and_container_removed(self):
        with self.assertRaises(CandidateError):
            await self.worker.evaluate("def solve(x): return len(bytearray(256 * 1024 * 1024))", None, self.run_id)
        rc, out, _ = await self.worker._docker("ps", "--all", "--quiet", "--filter", f"label=acinonyx.swarm.run={self.run_id}")
        self.assertEqual((rc, out), (0, b""))

    async def test_cancellation_removes_container(self):
        for delay in (0.01, 0.3, 1):
            run_id = "cancel-" + secrets.token_hex(8)
            task = asyncio.create_task(self.worker.evaluate("import time\ndef solve(x): time.sleep(30)", None, run_id))
            await asyncio.sleep(delay)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            rc, out, _ = await self.worker._docker("ps", "--all", "--quiet", "--filter", f"label=acinonyx.swarm.run={run_id}")
            self.assertEqual((rc, out), (0, b""))


@unittest.skipUnless(IMAGE, "Set MAS_SWARM_TEST_IMAGE for workflow integration")
class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        cert, key = root / "cert.pem", root / "tls.key"
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=IP:127.0.0.1",
            ],
            check=True,
            capture_output=True,
        )
        self.source, self.review_approved, self.outage, self.delay = SOURCE, True, False, 0
        self.usage = {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100}
        self.extra_fields = False
        self.redirect = False
        self.get_count = 0
        self.seen = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                fixture.get_count += 1
                payload = canonical({"data": [{"id": "scripted-test-fixture"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fixture.seen.append(body)
                if fixture.redirect:
                    self.send_response(302)
                    self.send_header("Location", "/v1/redirected")
                    self.end_headers()
                    return
                time.sleep(fixture.delay)
                if fixture.outage:
                    self.send_response(503)
                    self.end_headers()
                    return
                system = body["messages"][0]["content"]
                if "Design a bounded" in system:
                    content = {"plan": "Sum numbers with Python sum, including empty and negative inputs"}
                elif "Implement Python" in system:
                    content = {"source": fixture.source}
                    if fixture.extra_fields:
                        content["approved"] = True
                else:
                    content = {"approved": fixture.review_approved, "reason": "Fixture review; no model-quality claim"}
                payload = canonical(
                    {
                        "choices": [{"finish_reason": "stop", "message": {"content": canonical(content)}}],
                        "usage": fixture.usage,
                    }
                ).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                try:
                    self.wfile.write(payload)
                except (BrokenPipeError, ssl.SSLError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        self.server.socket = tls.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.env = patch.dict(os.environ, {"SSL_CERT_FILE": str(cert), "NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"})
        self.env.start()
        self.store = Store(root / "state.db", secrets.token_bytes(32))
        self.owner = self.store.provision("company", "owner", "owner")
        self.approver = self.store.provision("company", "other-human", "approver")
        self.provider = LiveProvider(f"https://127.0.0.1:{self.server.server_port}/v1", "scripted-test-fixture", "fixture-not-a-secret")
        self.worker = DockerWorker(IMAGE, Limits())
        self.swarm = CodingSwarm(self.store, self.provider, self.worker)
        self.doc = self.store.submit(self.owner, "sum", "Sum a list of numbers", CASES)

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def use_platform_identity(self):
        from mas.iam import MultiTenantIAM, StandardRole
        from mas.platform.identity import PlatformAuthority
        self.iam = MultiTenantIAM("shared-live-fixture-private-identity-key" * 2, db_path=Path(self.tmp.name) / "iam" / "identity.sqlite")
        self.iam.create_tenant("company", "Company")
        for subject, role in (("owner", StandardRole.SWARM_OWNER), ("other-human", StandardRole.SWARM_APPROVER),
                              ("admin", StandardRole.TENANT_ADMIN)):
            self.iam.register_principal("company", subject, roles={role.value})
        self.owner = self.iam.issue_token("company", "owner")
        self.approver = self.iam.issue_token("company", "other-human")
        self.admin = self.iam.issue_token("company", "admin")
        self.store = Store(Path(self.tmp.name) / "platform-state.db", secrets.token_bytes(32), authority=PlatformAuthority(self.iam))
        self.swarm = CodingSwarm(self.store, self.provider, self.worker)
        self.doc = self.store.submit(self.owner, "shared-sum", "Sum a list of numbers", CASES)

    async def test_platform_identity_runs_real_workers_and_separate_approval(self):
        self.use_platform_identity()
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "awaiting_approval")
        self.assertEqual(self.store.approve(self.approver, result["id"], result["candidate_hash"])["state"], "approved")

    async def test_platform_revocation_stops_live_request_and_preserves_uncertain_usage(self):
        self.use_platform_identity()
        self.delay = 2
        processes = []
        original = asyncio.create_subprocess_exec
        async def track(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            return process
        with patch("asyncio.create_subprocess_exec", track):
            task = asyncio.create_task(self.swarm.run(self.owner, self.doc["id"]))
            try:
                async with asyncio.timeout(5):
                    while not self.seen:
                        await asyncio.sleep(.02)
                self.iam.revoke_session(self.admin, self.iam.verify_token(self.owner).token_id)
                with self.assertRaises(asyncio.CancelledError):
                    await asyncio.wait_for(task, 3)
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
        self.assertTrue(processes)
        self.assertTrue(all(process.returncode is not None for process in processes))
        doc = self.store.get(self.approver, self.doc["id"])
        self.assertIn(doc["state"], {"planning", "coding", "verifying", "reviewing"})
        self.assertGreater(doc["usage"]["reserved"], 0)
        self.assertNotIn("evidence", doc)
        with self.assertRaises(SwarmError):
            self.store.approve(self.approver, doc["id"], "a" * 64)
        rc, output, _ = await self.worker._docker("ps", "--all", "--quiet", "--filter", f"label=acinonyx.swarm.run={doc['id']}")
        self.assertEqual((rc, output), (0, b""))

    async def test_workflow_uses_actual_containers_and_separate_human_approval(self):
        start = time.monotonic()
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "awaiting_approval", result)
        self.assertEqual(result["usage"], {"calls": 3, "tokens": 300, "reserved": 0})
        self.assertEqual(len(result["evidence"]["results"]), len(CASES))
        with self.assertRaises(SwarmError):
            self.store.approve(self.owner, result["id"], result["candidate_hash"])
        approved = self.store.approve(self.approver, result["id"], result["candidate_hash"])
        self.assertEqual(approved["state"], "approved")
        self.store.verify_audit()
        # Expected answers never enter model context or the candidate environment.
        for request in self.seen:
            self.assertNotIn('"expected"', canonical(request["messages"]))
        self.assertLess(time.monotonic() - start, 30)

    async def test_broken_candidate_and_fabricated_exit_success_rejected(self):
        self.source = "import os\ndef solve(payload): os._exit(0)"
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "rejected")
        self.assertEqual(result["usage"]["calls"], 2)
        with self.assertRaises(SwarmError):
            self.store.approve(self.approver, result["id"], result["candidate_hash"])

    async def test_reviewer_rejection_blocks_release(self):
        self.review_approved = False
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "rejected")

    async def test_provider_outage_never_synthesizes_success(self):
        self.outage = True
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "failed")
        self.assertNotIn("evidence", result)
        self.assertGreater(result["usage"]["reserved"], 0)

    async def test_remote_cancellation_kills_provider_and_records_terminal_state(self):
        self.delay = 2
        task = asyncio.create_task(self.swarm.run(self.owner, self.doc["id"]))
        await asyncio.sleep(0.3)
        self.store.cancel(self.owner, self.doc["id"])
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.store.get(self.owner, self.doc["id"])["state"], "cancelled")

    async def test_missing_worker_fails_closed(self):
        swarm = CodingSwarm(self.store, self.provider, DockerWorker("sha256:" + "f" * 64, Limits()))
        result = await swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "failed")
        self.assertEqual(self.seen, [])

    async def test_requested_model_unavailable_never_substitutes(self):
        self.provider.model = "unavailable-model"
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "failed")
        self.assertEqual(self.seen, [])

    async def test_untrusted_agent_cannot_add_release_authority(self):
        self.extra_fields = True
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "failed")
        self.assertNotIn("evidence", result)

    async def test_provider_usage_overrun_keeps_reservation_and_fails(self):
        self.usage = {"prompt_tokens": 99980, "completion_tokens": 20, "total_tokens": 100000}
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "failed")
        self.assertGreater(result["usage"]["reserved"], 0)

    async def test_provider_thinking_overhead_is_fully_charged(self):
        self.usage = {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 125}
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "awaiting_approval")
        self.assertEqual(result["usage"]["tokens"], 375)

    async def test_underreported_usage_is_rejected(self):
        self.usage = {"prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 99}
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "failed")
        self.assertGreater(result["usage"]["reserved"], 0)

    async def test_provider_redirect_is_not_followed(self):
        self.redirect = True
        result = await self.swarm.run(self.owner, self.doc["id"])
        self.assertEqual(result["state"], "failed")
        self.assertEqual(self.get_count, 1)  # Only model discovery, no redirected request.

    async def test_expired_run_recovery_removes_actual_orphan_without_replay(self):
        doc = self.store.claim(self.owner, self.doc["id"], IMAGE)
        rc, container, _ = await self.worker._docker(
            "create",
            "--label",
            f"acinonyx.swarm.run={doc['id']}",
            "--network=none",
            "--read-only",
            "--user=65534:65534",
            "--cap-drop=ALL",
            "--pids-limit=32",
            "--memory=64m",
            IMAGE,
            "python",
            "-c",
            "import time; time.sleep(30)",
        )
        self.assertEqual(rc, 0)
        container = container.decode().strip()
        try:
            rc, _, _ = await self.worker._docker("start", container)
            self.assertEqual(rc, 0)
            with patch("mas.swarm.runtime.time.time", return_value=doc["lease_expires"] + 1):
                await self.swarm.recover(self.owner, doc["id"])
            self.assertEqual(self.store.get(self.owner, doc["id"])["state"], "interrupted")
            rc, out, _ = await self.worker._docker("ps", "--all", "--quiet", "--filter", f"label=acinonyx.swarm.run={doc['id']}")
            self.assertEqual((rc, out), (0, b""))
            self.assertEqual(self.seen, [])
        finally:
            await self.worker.recover(doc["id"])


if __name__ == "__main__":
    unittest.main()
