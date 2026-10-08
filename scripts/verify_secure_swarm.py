"""Run structural acceptance checks and save actual counts, never a made-up rating."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Local Python image pinned by digest")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.out.mkdir(parents=True, exist_ok=False)
    source = hashlib.sha256()
    for path in sorted([*root.glob("mas/swarm/*.py"), root / "tests/test_secure_swarm.py", root / "pyproject.toml"]):
        source.update(str(path.relative_to(root)).encode() + b"\0" + path.read_bytes())
    started = time.time()
    command = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_secure_swarm.py",
        "-q",
        "--tb=short",
        "--junitxml=" + str((args.out / "tests.xml").resolve()),
    ]
    with (args.out / "test-output.log").open("w") as log:
        result = subprocess.run(
            command,
            cwd=root,
            env={**os.environ, "MAS_SWARM_TEST_IMAGE": args.image},
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=600,
            check=False,
        )
    xml = ET.parse(args.out / "tests.xml").getroot()
    suites = [xml] if xml.tag == "testsuite" else list(xml.iter("testsuite"))
    counts = {name: sum(int(s.get(name, 0)) for s in suites) for name in ("tests", "failures", "errors", "skipped")}
    passed = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    ok = result.returncode == 0 and passed > 0 and not any(counts[k] for k in ("failures", "errors", "skipped"))
    report = {
        "scope": "structural contracts and real Docker execution; TLS model fixture",
        "source_sha256": source.hexdigest(),
        "image": args.image,
        "started": started,
        "finished": time.time(),
        "command": command,
        "exit_code": result.returncode,
        "counts": {**counts, "passed": passed},
        "structural_acceptance": "passed" if ok else "failed",
        "live_model_quality": "not_assessed",
        "enterprise_readiness": "not_assessed",
        "rating": "not_awarded",
    }
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
