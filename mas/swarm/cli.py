"""Local operator CLI. No dashboard, legacy MCP route or autonomous deployment."""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import stat
import sys
from pathlib import Path

from mas.iam import MultiTenantIAM
from mas.platform.identity import PlatformAuthority

from .contracts import Limits, SwarmError, canonical, strict_json
from .provider import LiveProvider
from .runtime import CodingSwarm
from .store import Store
from .worker import DockerWorker


def private_write(path: Path, data: bytes):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def private_read(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise SwarmError("Credentials must be owner-only regular files")
        raw = handle.read(8193)
        if len(raw) > 8192:
            raise SwarmError("Oversized credentials file")
        return raw


def parser():
    result = argparse.ArgumentParser(prog="mas-swarm", description="Supervised Python-function coding swarm")
    result.add_argument("--state-dir", type=Path, default=Path("workspace/scratch/swarm"))
    result.add_argument("--token-file", type=Path)
    result.add_argument("--identity", choices=["local", "platform"], default="local", help="Persisted authority mode; platform requires durable IAM and --token-file")
    sub = result.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--tenant", required=True)
    init.add_argument("--subject", required=True)
    enroll = sub.add_parser("enroll")
    enroll.add_argument("--subject", required=True)
    enroll.add_argument("--role", required=True, choices=["requester", "approver"])
    enroll.add_argument("--out", type=Path, required=True)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("--subject", required=True)
    submit = sub.add_parser("submit")
    submit.add_argument("--request-key", required=True)
    submit.add_argument("--goal", required=True)
    submit.add_argument("--cases", type=Path, required=True)
    for action in ("run", "show", "cancel", "recover", "cleanup", "approve", "export"):
        command = sub.add_parser(action)
        command.add_argument("run_id")
        if action in ("run", "recover", "cleanup"):
            command.add_argument("--image", required=True)
        if action == "approve":
            command.add_argument("--candidate-hash", required=True)
        if action == "export":
            command.add_argument("--out", type=Path, required=True)
    backup = sub.add_parser("backup")
    backup.add_argument("--out", type=Path, required=True)
    sub.add_parser("audit")
    sub.add_parser("provider-check")
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        root = args.state_dir
        authority = None
        if args.identity == "platform":
            if args.token_file is None or args.command in {"enroll", "revoke"}:
                raise SwarmError("Platform mode requires a token file; enrollment/revocation belongs to IAM")
            authority = PlatformAuthority(MultiTenantIAM())
        if args.command == "provider-check":
            provider = LiveProvider(
                os.environ.get("MAS_SWARM_PROVIDER_URL", ""), os.environ.get("MAS_SWARM_MODEL", ""), os.environ.get("MAS_SWARM_API_KEY", "")
            )
            print(canonical(asyncio.run(provider.check_model())))
            return 0
        if args.command == "init":
            if authority:
                actor = authority.authenticate(private_read(args.token_file).decode().strip(), {"owner"})
                if actor["tenant"] != args.tenant or actor["subject"] != args.subject:
                    raise SwarmError("Platform initialization must match authenticated tenant and subject")
            root.mkdir(parents=True, mode=0o700, exist_ok=False)
            private_write(root / "signing.key", secrets.token_bytes(32))
            store = Store(root / "state.db", private_read(root / "signing.key"), authority=authority)
            if authority:
                print("Initialized platform-bound state. Use existing platform token files; no local credential issued.")
                return 0
            token = store.provision(args.tenant, args.subject, "owner")
            private_write(root / "owner.token", token.encode())
            print("Initialized. Private owner credential: " + str(root / "owner.token"))
            return 0
        info = root.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise SwarmError("State directory must be owner-only and cannot be a symlink")
        store = Store(root / "state.db", private_read(root / "signing.key"), authority=authority)
        token = private_read(args.token_file or root / "owner.token").decode().strip()
        if args.command == "enroll":
            with store._tx() as db:
                actor = store._auth(db, token, {"owner"})
            credential = store.provision(actor["tenant"], args.subject, args.role)
            private_write(args.out, credential.encode())
            print("Credential written to " + str(args.out))
        elif args.command == "revoke":
            store.revoke(token, args.subject)
            print("Subject credentials revoked")
        elif args.command == "submit":
            with args.cases.open("rb") as handle:
                raw = handle.read(262145)
            if len(raw) > 262144:
                raise SwarmError("Test suite file too large")
            doc = store.submit(token, args.request_key, args.goal, strict_json(raw))
            print(canonical({"run_id": doc["id"], "state": doc["state"]}))
        elif args.command in {"run", "recover", "cleanup"}:
            doc = store.get(token, args.run_id)
            worker = DockerWorker(args.image, Limits(**doc["request"]["limits"]))
            if args.command == "cleanup":
                store.require_role(token, {"owner"})
                if doc["state"] not in {"failed", "cancelled", "interrupted", "rejected"}:
                    raise SwarmError("Run is not terminal")
                asyncio.run(worker.recover(args.run_id))
                store.record_cleanup(token, args.run_id)
                print("Terminal worker state reconciled")
            elif args.command == "recover":
                # Recovery does not need a model or model credentials.
                async def recover():
                    if doc["state"] not in {"planning", "coding", "verifying", "reviewing"}:
                        raise SwarmError("Run is not active")
                    import time

                    if doc["lease_expires"] > time.time():
                        raise SwarmError("Lease has not expired")
                    with store._tx() as db:
                        store._auth(db, token, {"owner"})
                    await worker.recover(args.run_id)
                    store.interrupt(token, args.run_id)

                asyncio.run(recover())
            else:
                provider = LiveProvider(
                    os.environ.get("MAS_SWARM_PROVIDER_URL", ""),
                    os.environ.get("MAS_SWARM_MODEL", ""),
                    os.environ.get("MAS_SWARM_API_KEY", ""),
                )
                result = asyncio.run(CodingSwarm(store, provider, worker).run(token, args.run_id))
                print(
                    canonical(
                        {
                            "run_id": result["id"],
                            "state": result["state"],
                            "candidate_hash": result.get("candidate_hash"),
                            "usage": result["usage"],
                        }
                    )
                )
                return 0 if result["state"] == "awaiting_approval" else 1
        elif args.command == "show":
            doc = store.get(token, args.run_id)
            # Do not print operator-owned expected results or provider credentials.
            print(canonical({k: v for k, v in doc.items() if k != "request"}))
        elif args.command == "cancel":
            store.cancel(token, args.run_id)
            print("Cancellation recorded")
        elif args.command == "approve":
            store.approve(token, args.run_id, args.candidate_hash)
            print("Human approval recorded for exact candidate; nothing deployed")
        elif args.command == "export":
            with store._tx() as db:
                actor = store._auth(db, token, {"owner", "requester", "approver"})
                doc = store._load(db, args.run_id, actor)
                if doc["state"] != "approved":
                    raise SwarmError("Only human-approved candidates can be exported")
                store._validate_evidence(doc)
                private_write(args.out, doc["source"].encode())
            print("Approved source exported. Execute only in an appropriate sandbox.")
        elif args.command == "backup":
            with store._tx() as db:
                store._auth(db, token, {"owner"})
                private_write(args.out, b"")
                store.backup(args.out)
            print("State backed up; protect and back up signing.key separately")
        elif args.command == "audit":
            with store._tx() as db:
                store._auth(db, token, {"owner"})
            store.verify_audit()
            print("Audit signatures and chain verified")
        return 0
    except (SwarmError, PermissionError, OSError, UnicodeError, ValueError):
        print("Swarm operation rejected or unavailable. Check policy, identity and prerequisites.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Swarm execution cancelled", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
