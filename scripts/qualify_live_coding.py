"""Bounded live coding qualification, using disposable IAM and PM records.

Invokes a real provider and Docker workers. It cannot grant human approval or
mark PM work complete. This is operator-driven qualification, not an admitted
automatic PM scheduler or a production deployment.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import secrets
import sys
import time
from pathlib import Path

from mas.iam import MultiTenantIAM, StandardRole
from mas.mcp.protocol import JsonRpcRequest, MCPRegistry
from mas.platform.identity import PlatformAuthority
from mas.pm.tools import get_pm_db, register_pm_tools
from mas.swarm.cli import private_write
from mas.swarm.contracts import Limits, SwarmError, digest
from mas.swarm.provider import LiveProvider
from mas.swarm.runtime import CodingSwarm
from mas.swarm.store import Store
from mas.swarm.worker import DockerWorker
from mas.tenancy import tenant_scope

GOAL = (
    "Implement solve(payload). For valid inputs payload is a JSON list of integers "
    "between -1000000 and 1000000 inclusive. Return its arithmetic sum as an integer. "
    "The empty list returns zero. Inputs outside that domain have unspecified behavior; "
    "no extra validation, formats, external packages or side effects are required."
)
CASES = [
    {"id": "empty", "input": [], "expected": 0},
    {"id": "positive", "input": [1, 2, 3], "expected": 6},
    {"id": "mixed", "input": [-4, 10, -6, 3], "expected": 3},
    {"id": "bounds", "input": [-1000000, 1000000, 1], "expected": 1},
]


async def qualify(state_dir: Path, image: str) -> dict:
    # Fail before provisioning or spending if operator configuration is absent.
    provider = LiveProvider(
        os.environ.get("MAS_SWARM_PROVIDER_URL", ""),
        os.environ.get("MAS_SWARM_MODEL", ""),
        os.environ.get("MAS_SWARM_API_KEY", ""),
    )
    await provider.check_model(timeout=20)
    limits = Limits(max_tokens=20000, max_cases=4)
    worker = DockerWorker(image, limits)
    await worker.check()
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=False)
    iam_key = secrets.token_hex(32)
    signing_key = secrets.token_bytes(32)
    private_write(state_dir / "identity.key", iam_key.encode())
    private_write(state_dir / "signing.key", signing_key)
    iam = MultiTenantIAM(iam_key, db_path=state_dir / "identity" / "iam.sqlite")
    iam.create_tenant("qualification", "Disposable live qualification")
    iam.register_principal(
        "qualification", "requester",
        roles={StandardRole.SWARM_REQUESTER.value, StandardRole.DATA_ARCHITECT.value},
    )
    token = iam.issue_token("qualification", "requester", ttl_seconds=1800)
    private_write(state_dir / "requester.token", token.encode())
    swarm_dir = state_dir / "swarm"
    swarm_dir.mkdir(mode=0o700)
    private_write(swarm_dir / "signing.key", signing_key)
    store = Store(swarm_dir / "state.db", signing_key, authority=PlatformAuthority(iam))

    # Real authenticated MCP handlers create an isolated qualification source.
    # No operational project is enrolled, assigned or transitioned by this run.
    tenant_root = state_dir / "tenant-runtime"
    registry = MCPRegistry(iam=iam, tenant_id="qualification", tenant_root=tenant_root)
    register_pm_tools(registry)

    async def call(name, arguments):
        response = await registry.handle_request(
            JsonRpcRequest(method="tools/call", id=1, params={"name": name, "arguments": arguments}),
            bearer_token=token,
        )
        if response.error is not None:
            raise SwarmError("Authenticated PM qualification request failed")
        # Existing MCP wrapper returns Python literal text for these simple
        # create results. Never eval arbitrary content or execute a proposal.
        value = ast.literal_eval(response.result["content"][0]["text"])
        if not isinstance(value, dict) or value.get("status") not in {"CREATED", "EXISTS"}:
            raise SwarmError("Unexpected PM qualification response")
        return value

    await call("pm_create_project", {"key": "LIVEQ", "name": "Live coding qualification", "token_budget": 0})
    created = await call("pm_create_issue", {
        "project_key": "LIVEQ", "title": "Bounded integer-list sum", "description": GOAL,
        "appetite_tokens": 0, "path_whitelist": ["qualification/"],
    })
    with tenant_scope(iam, token, "qualification", tenant_root):
        issue = get_pm_db().get_issue(created["issue_key"])
        if issue is None or issue.description != GOAL:
            raise SwarmError("PM task source did not persist")
        goal, source_id = issue.description, issue.id
    # This separate operator-owned swarm budget does not dispatch or consume the
    # PM task's zero allowance. It is not qualified PM funding integration.
    request_key = "pm_" + source_id
    submitted = store.submit(token, request_key, goal, CASES, limits)
    if store.submit(token, request_key, goal, CASES, limits)["id"] != submitted["id"]:
        raise SwarmError("Duplicate submission did not recover the same run")
    started = time.monotonic()
    result = await CodingSwarm(store, provider, worker).run(token, submitted["id"])
    report = {
        "schema_version": 1,
        "scope": "operator-driven live coding qualification with disposable identities; not production admission",
        "model": provider.model, "image": image,
        "pm_source": {"issue_id": source_id, "issue_key": created["issue_key"], "goal_hash": digest(goal)},
        "run_id": result["id"], "state": result["state"],
        "usage": result["usage"], "elapsed_seconds": round(time.monotonic() - started, 3),
        "candidate_hash": result.get("candidate_hash"),
        "case_outcomes": result.get("evidence", {}).get("results", []),
        "model_review_approved": result.get("review", {}).get("approved"),
        "human_approval": "not_requested_or_granted", "source_exported": False,
        "production_deployed": False,
    }
    if result["state"] != "awaiting_approval":
        report.update(status="failed", failure=result.get("error", "Candidate rejected; inspect private state"))
        return report
    try:
        store.approve(token, result["id"], result["candidate_hash"])
    except (PermissionError, SwarmError):
        report["requester_approval_denied"] = True
    else:
        raise SwarmError("Requester improperly approved qualification candidate")
    store.verify_audit()
    reopened_iam = MultiTenantIAM(iam_key, db_path=iam.database_path)
    reopened = Store(store.path, signing_key, authority=PlatformAuthority(reopened_iam))
    recovered = reopened.get(token, result["id"])
    if recovered != result:
        raise SwarmError("Reopened state differs from verified run")
    if reopened.submit(token, request_key, goal, CASES, limits)["id"] != result["id"]:
        raise SwarmError("Restarted submission did not recover the original run")
    with tenant_scope(reopened_iam, token, "qualification", tenant_root):
        current = get_pm_db().get_issue(created["issue_key"])
        if current is None or current.current_state.value != "BACKLOG" or current.description != goal:
            raise SwarmError("Qualification changed the source PM state")
    report.update(status="passed", signed_audit_verified=True, durable_restart_verified=True,
                  idempotent_recovery_verified=True, pm_source_state="BACKLOG")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True, help="New private directory; must not already exist")
    parser.add_argument("--image", required=True, help="Available digest-pinned worker image")
    parser.add_argument("--report", type=Path, required=True, help="New report file; must not already exist")
    args = parser.parse_args(argv)
    if args.report.exists() or args.state_dir.exists():
        parser.error("Use fresh state and report paths; existing results are preserved")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    try:
        report = asyncio.run(qualify(args.state_dir, args.image))
    except (SwarmError, PermissionError, OSError, ValueError) as error:
        report = {"status": "failed", "error_type": type(error).__name__,
                  "human_approval": "not_requested_or_granted", "production_deployed": False}
    private_write(args.report, (json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
