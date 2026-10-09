"""Independently deployed forward-only HTTPS checkpoint witness.

Its administrator, database, signing key and restore policy must be separate
from the MAS coordinator. Writer credentials cannot enroll, delete or rewind.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import ssl
import stat
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mas.audit_anchor import AnchorError, checkpoint, strict_json
from mas.identity_store import IdentityStore


class WitnessStore:
    def __init__(self, path: str | Path, signing_key: bytes):
        if not isinstance(signing_key, bytes) or len(signing_key) < 32:
            raise ValueError("Independent witness signing key must have at least 32 bytes")
        self._store = IdentityStore(path, signing_key)

    def enroll(self, namespace: str, token: str, initial=None):
        """Witness OS administrator only; not exposed through HTTP."""
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", namespace) or not isinstance(token, str) or not 32 <= len(token) <= 4096 or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ValueError("Invalid witness enrollment")
        document = {"tenant_id": namespace, "token_hash": hashlib.sha256(token.encode()).hexdigest(), "checkpoint": checkpoint(initial if initial is not None else {"sequence": 0, "hash": ""})}
        self._store.create_tenant(document)

    def request(self, namespace, token, payload):
        if not isinstance(payload, dict) or payload.get("action") not in {"read", "advance"}:
            raise AnchorError("Invalid witness action")
        keys = {"action", "nonce"} if payload["action"] == "read" else {"action", "nonce", "expected", "target"}
        if set(payload) != keys or not isinstance(payload["nonce"], str) or not re.fullmatch(r"[a-f0-9]{64}", payload["nonce"]):
            raise AnchorError("Invalid witness challenge")
        with self._store.transaction(write=payload["action"] == "advance") as db:
            latest = self._store.validate_audit(db)
            document = self._store.read(db, "tenant", namespace, latest)
            if not document or not hmac.compare_digest(document["token_hash"], hashlib.sha256(token.encode()).hexdigest()):
                raise AnchorError("Witness namespace unavailable or unauthorized")
            current = checkpoint(document["checkpoint"])
            if payload["action"] == "advance":
                expected, target = checkpoint(payload["expected"]), checkpoint(payload["target"])
                if current == target and target["sequence"] > expected["sequence"]:
                    pass  # Exact replay of an acknowledged CAS is idempotent.
                elif current != expected or target["sequence"] <= current["sequence"]:
                    raise AnchorError("Witness conflict or attempted rewind")
                else:
                    document["checkpoint"] = target
                    self._store.save(db, "tenant", namespace, document)
                    current = target
            return {"namespace": namespace, "nonce": payload["nonce"], "checkpoint": current}


class WitnessHandler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.do_handshake()  # Bounded socket timeout, in a request thread.

    def log_message(self, *args):
        pass  # Never log Authorization or request bodies.

    def _reply(self, status, value):
        body = json.dumps(value, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        self.connection.settimeout(3)
        match = re.fullmatch(r"/v1/checkpoints/([a-zA-Z0-9_-]{1,128})", self.path)
        if not match:
            self._reply(404, {"error": "Unknown checkpoint endpoint"})
            return
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or not 32 <= len(auth[7:]) <= 4096:
            self._reply(403, {"error": "Witness authentication required"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192:
                raise ValueError("Request size")
            payload = strict_json(self.rfile.read(length))
            result = self.witness.request(match[1], auth[7:], payload)
            self._reply(200, result)
        except PermissionError:
            self._reply(409, {"error": "Witness rejected the checkpoint or credential"})
        except (ValueError, TypeError):
            self._reply(400, {"error": "Malformed checkpoint request"})
        except Exception:
            self._reply(503, {"error": "Witness unavailable"})


def server(store: WitnessStore, host: str, port: int, context: ssl.SSLContext):
    class WitnessServer(ThreadingHTTPServer):
        def get_request(self):
            connection, address = self.socket.accept()
            connection.settimeout(3)  # Includes TLS handshake and HTTP headers.
            try:
                return context.wrap_socket(connection, server_side=True, do_handshake_on_connect=False), address
            except Exception:
                connection.close()
                raise

    handler = type("BoundWitnessHandler", (WitnessHandler,), {"witness": store})
    return WitnessServer((host, port), handler)


def private_file(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1 or info.st_size > 8192:
            raise ValueError("Witness credential file must be private")
        return os.read(descriptor, 8193)
    finally:
        os.close(descriptor)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Independent forward-only HTTPS audit witness")
    parser.add_argument("--database", required=True)
    parser.add_argument("--key-file", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    enroll = sub.add_parser("enroll")
    enroll.add_argument("--namespace", required=True)
    enroll.add_argument("--token-file", required=True)
    enroll.add_argument("--initial-checkpoint-file")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=9043)
    serve.add_argument("--cert-file", required=True)
    serve.add_argument("--tls-key-file", required=True)
    args = parser.parse_args(argv)
    store = WitnessStore(args.database, private_file(args.key_file))
    if args.command == "enroll":
        initial = strict_json(Path(args.initial_checkpoint_file).read_bytes()) if args.initial_checkpoint_file else None
        store.enroll(args.namespace, private_file(args.token_file).decode().strip(), initial)
    else:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(args.cert_file, args.tls_key_file)
        instance = server(store, args.host, args.port, context)
        try:
            instance.serve_forever()
        finally:
            instance.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
