"""An empty or broken corpus must never receive a successful verification."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_research_swarm.py"


@pytest.mark.parametrize("corpus, expected", [("empty", 1), ("broken", 1), ("valid", 0)])
def test_research_verifier_reports_measured_results(tmp_path, corpus, expected):
    if corpus != "empty":
        (tmp_path / "README.md").write_text("[Reference](reference.md)\n")
    if corpus == "valid":
        (tmp_path / "reference.md").write_text("Reference content\n")
    result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(tmp_path)], capture_output=True, text=True, check=False, timeout=5)
    assert result.returncode == expected
    report = json.loads(result.stdout)
    assert report["rating"] == "not_awarded"
    assert report["live_agent_review"] == "not_performed"
    assert report["academic_factual_accuracy"] == "not_assessed"
    assert report["status"] == ("passed" if expected == 0 else "failed")
    assert report["md_files_count"] == {"empty": 0, "broken": 1, "valid": 2}[corpus]
    if corpus == "empty":
        assert report["merkle_root"] is None
    if corpus == "broken":
        assert report["broken_links_count"] == 1
