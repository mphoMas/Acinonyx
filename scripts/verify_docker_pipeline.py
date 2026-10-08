#!/usr/bin/env python3
"""
scripts/verify_docker_pipeline.py: Validates Dockerfile, compose config,
and container non-root safety for Acinonyx CI/CD.
Deliverable for task OPS-01 (MAS-5) by platform_sre.
"""

from pathlib import Path
import re
import sys


def verify_docker_config(repo_root: Path) -> int:
    print(f"[*] Validating Docker & CI Pipeline in: {repo_root}")
    errors = []

    # 1. Validate Dockerfile
    dockerfile = repo_root / "Dockerfile"
    if not dockerfile.exists():
        errors.append("Dockerfile not found in root")
    else:
        content = dockerfile.read_text()
        if "USER mas" not in content and "USER 10001" not in content:
            errors.append("Dockerfile does not enforce unprivileged non-root USER mas")
        if "HEALTHCHECK" not in content:
            errors.append("Dockerfile lacks HEALTHCHECK declaration")
        if "EXPOSE 8080" not in content:
            errors.append("Dockerfile does not expose port 8080")

    # 2. Validate docker-compose.yml
    compose = repo_root / "docker-compose.yml"
    if not compose.exists():
        errors.append("docker-compose.yml not found in root")
    else:
        content = compose.read_text()
        if "8080:8080" not in content:
            errors.append("docker-compose.yml does not bind port 8080")

    # 3. Validate GitHub Actions CI configuration
    ci_yml = repo_root / ".github" / "workflows" / "ci.yml"
    if not ci_yml.exists():
        errors.append(".github/workflows/ci.yml not found")
    else:
        content = ci_yml.read_text()
        if "branches: [main, Acinonyx_frontier]" not in content:
            errors.append("ci.yml does not trigger on Acinonyx_frontier branch")
        if "docker build" not in content:
            errors.append("ci.yml does not build docker image")

    if errors:
        print(f"[-] FAILED: {len(errors)} pipeline errors detected:")
        for err in errors:
            print(f"    - {err}")
        return 1

    print("[+] SUCCESS: Docker and CI pipeline configuration verified.")
    return 0


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    sys.exit(verify_docker_config(root))
