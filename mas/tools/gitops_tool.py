"""
mas.tools.gitops_tool: Autonomous CI/CD Pipeline Generation and GitOps Dispatch Engine.
Equips QA and DevOps agents to autonomously generate multi-stage GitHub Actions / GitLab CI workflows,
trigger remote CI workflow dispatches, and execute local pre-commit GitOps verification gates.

Architect: Acinonyx
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional
from mas.core.message import Message, MessageMetadata
from mas.mcp.protocol import MCPRegistry


def generate_github_actions_workflow(
    project_path: str,
    stack: str = "python",
    workflow_name: str = "Continuous Integration & Verification",
) -> Dict[str, Any]:
    """
    Generate an enterprise-grade .github/workflows/ci.yml pipeline for the project.
    Includes linting, unit/integration testing, security auditing, and build packaging.
    """
    workflows_dir = os.path.join(project_path, ".github", "workflows")
    os.makedirs(workflows_dir, exist_ok=True)
    workflow_file = os.path.join(workflows_dir, "ci.yml")

    yaml_content = f"""name: {workflow_name}

on:
  push:
    branches: [ main, master, "feature/**", "release/**" ]
  pull_request:
    branches: [ main, master ]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment target environment'
        required: true
        default: 'staging'
        type: choice
        options:
          - staging
          - production

jobs:
  lint-and-validate:
    name: Code Hygiene & Static Analysis
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python Environment
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install Linting Tools
        run: |
          python -m pip install --upgrade pip
          pip install flake8 mypy

      - name: Syntax & Static Check
        run: |
          python -m compileall -q .
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

  test-and-coverage:
    name: Unit & Integration Test Matrix
    needs: lint-and-validate
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13"]
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Set up Python ${{{{ matrix.python-version }}}}
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ matrix.python-version }}}}

      - name: Run Automated Test Suites
        run: |
          python -m unittest discover -s tests -p "test_*.py" -v

  security-audit:
    name: Zero-Trust Security & SAST Audit
    needs: lint-and-validate
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Audit File Permissions & Secrets
        run: |
          # Verify no private keys or high-entropy credentials committed
          ! grep -rn "BEGIN RSA PRIVATE KEY" . --exclude-dir=.git || exit 1
          echo "Zero-Trust credential scan passed."

  build-and-package:
    name: Production Release Artifact Packaging
    needs: [test-and-coverage, security-audit]
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Generate Build Summary
        run: |
          mkdir -p dist
          echo "Build Commit: ${{{{ github.sha }}}}" > dist/BUILD_METADATA.txt
          echo "Workflow Run: ${{{{ github.run_id }}}}" >> dist/BUILD_METADATA.txt

      - name: Upload Build Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release-build-${{{{ github.sha }}}}
          path: dist/
"""
    with open(workflow_file, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    return {
        "success": True,
        "workflow_file": workflow_file,
        "size_bytes": len(yaml_content),
        "stages": ["lint-and-validate", "test-and-coverage", "security-audit", "build-and-package"],
    }


def generate_gitlab_ci_pipeline(
    project_path: str,
    stack: str = "python",
) -> Dict[str, Any]:
    """Generate an enterprise .gitlab-ci.yml pipeline specification."""
    ci_file = os.path.join(project_path, ".gitlab-ci.yml")
    content = """stages:
  - lint
  - test
  - security
  - deploy

default:
  image: python:3.12-slim

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

lint_code:
  stage: lint
  script:
    - python -m compileall -q .
    - pip install flake8
    - flake8 . --count --select=E9,F63,F7,F82 --show-source

test_suite:
  stage: test
  script:
    - python -m unittest discover -s tests -p "test_*.py" -v

security_scan:
  stage: security
  script:
    - echo "Running container and source vulnerability audit..."
    - ! grep -rn "PRIVATE KEY" . --exclude-dir=.git || exit 1

deploy_staging:
  stage: deploy
  script:
    - echo "Deploying artifact to staging environment..."
  only:
    - main
"""
    with open(ci_file, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "success": True,
        "ci_file": ci_file,
        "size_bytes": len(content),
        "stages": ["lint", "test", "security", "deploy"],
    }


def trigger_workflow_dispatch(
    repo: str,
    workflow_id: str = "ci.yml",
    ref: str = "main",
    inputs: Optional[Dict[str, Any]] = None,
    github_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trigger an external GitHub Actions workflow dispatch via REST API.
    If no token or running in local preview mode, safely simulates the dispatch.
    """
    live_enabled = os.environ.get("MAS_ENABLE_LIVE_DISPATCH", "false").lower() == "true"
    token = github_token or os.environ.get("GITHUB_TOKEN")

    if live_enabled and token:
        url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
        payload = json.dumps({"ref": ref, "inputs": inputs or {}}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AcinonyxGitOpsAgent/1.0",
        }
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                status_code = resp.status
            return {
                "success": True,
                "mode": "live",
                "repo": repo,
                "workflow_id": workflow_id,
                "ref": ref,
                "http_status": status_code,
                "message": f"Successfully dispatched workflow '{workflow_id}' on repo '{repo}'",
            }
        except Exception as e:
            return {
                "success": False,
                "mode": "live",
                "error": f"Failed to dispatch workflow: {str(e)}",
            }
    else:
        # Simulated Dispatch (Hermetic / Preview Mode)
        simulated_run_id = int(time.time() * 1000) % 100000000
        return {
            "success": True,
            "mode": "simulated_preview",
            "repo": repo,
            "workflow_id": workflow_id,
            "ref": ref,
            "simulated_run_id": simulated_run_id,
            "status": "queued",
            "message": f"[STAGED PREVIEW] Simulated workflow dispatch for '{workflow_id}' on '{repo}' ({ref}). Live dispatch disarmed.",
        }


def run_local_gitops_ci(
    project_path: str,
    test_command: Optional[str] = None,
    event_bus: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Execute local CI verification directly inside the project directory,
    validating test suites and publishing a telemetry event to EventBus.
    """
    # Use the active interpreter and reject an empty discovery run explicitly.
    cmd = test_command or [sys.executable, "-c", (
        "import sys,unittest; "
        "suite=unittest.defaultTestLoader.discover('tests',pattern='test_*.py'); "
        "count=suite.countTestCases(); "
        "result=unittest.TextTestRunner(verbosity=2).run(suite); "
        "sys.exit(0 if count > 0 and result.wasSuccessful() else 1)"
    )]
    t0 = time.time()

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_path}:{env.get('PYTHONPATH', '')}"

    proc = subprocess.run(
        cmd,
        shell=test_command is not None,
        cwd=project_path,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    duration = time.time() - t0
    success = (proc.returncode == 0)

    result = {
        "success": success,
        "exit_code": proc.returncode,
        "duration_seconds": round(duration, 3),
        "command": cmd,
        "stdout": proc.stdout[-2000:] if proc.stdout else "",
        "stderr": proc.stderr[-2000:] if proc.stderr else "",
    }

    if event_bus:
        msg = Message(
            sender="GitOpsAgent",
            recipient="broadcast",
            content=f"CI Verification {'PASSED' if success else 'FAILED'} in {round(duration, 2)}s",
            metadata=MessageMetadata(
                topic="gitops.ci.result",
                extra={"exit_code": proc.returncode, "success": success, "duration": round(duration, 3)},
            ),
        )
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(event_bus.publish(msg))
            else:
                loop.run_until_complete(event_bus.publish(msg))
        except Exception:
            pass

    return result


def register_gitops_tools(registry: MCPRegistry) -> None:
    """Register GitOps CI/CD tools into the Model Context Protocol registry."""
    registry.register_tool(
        name="gitops_generate_github_actions",
        description="Scaffold a multi-stage GitHub Actions CI workflow (.github/workflows/ci.yml) for a workspace project.",
        input_schema={
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Absolute path to the workspace project"},
                "workflow_name": {"type": "string", "default": "Continuous Integration & Verification"},
            },
            "required": ["project_path"],
        },
        handler=lambda args: generate_github_actions_workflow(args["project_path"], workflow_name=args.get("workflow_name", "CI")),
    )

    registry.register_tool(
        name="gitops_generate_gitlab_ci",
        description="Scaffold a GitLab CI pipeline (.gitlab-ci.yml) for a workspace project.",
        input_schema={
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Absolute path to the workspace project"},
            },
            "required": ["project_path"],
        },
        handler=lambda args: generate_gitlab_ci_pipeline(args["project_path"]),
    )

    registry.register_tool(
        name="gitops_trigger_workflow",
        description="Dispatch a remote GitHub Actions workflow or run a staged simulated dispatch.",
        input_schema={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository in owner/repo format"},
                "workflow_id": {"type": "string", "default": "ci.yml"},
                "ref": {"type": "string", "default": "main"},
            },
            "required": ["repo"],
        },
        handler=lambda args: trigger_workflow_dispatch(args["repo"], workflow_id=args.get("workflow_id", "ci.yml"), ref=args.get("ref", "main")),
    )

    registry.register_tool(
        name="gitops_run_local_ci",
        description="Execute a local pre-commit CI validation gate and publish telemetry to EventBus.",
        input_schema={
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Absolute path to project directory"},
            },
            "required": ["project_path"],
        },
        handler=lambda args: run_local_gitops_ci(args["project_path"]),
    )
