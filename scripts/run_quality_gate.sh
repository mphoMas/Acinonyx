#!/usr/bin/env bash
# ==============================================================================
# scripts/run_quality_gate.sh: Repository Quality & Verification Gate
# Enforces zero-regression test execution, capability reporting,
# Merkle provenance integrity, and zero broken links across the MAS estate.
# ==============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "================================================================="
echo "   🐆 ACINONYX ENTERPRISE: COMPREHENSIVE QUALITY GATE            "
echo "================================================================="

echo -e "\n[GATE 1/5]: Checking Code Style & Lints (ruff)..."
ruff check mas tests

echo -e "\n[GATE 2/5]: Checking Runtime Health & Capabilities Matrix..."
python3 -m mas.cli doctor
python3 -m mas.cli capabilities

echo -e "\n[GATE 3/5]: Checking Local Research Assets and Links..."
python3 scripts/verify_research_swarm.py

echo -e "\n[GATE 4/5]: Checking Python Source Compilation..."
python3 -m compileall -q mas scripts

echo -e "\n[GATE 5/5]: Executing Full Unit & Integration Test Suite..."
python3 -m pytest tests/ -v

echo -e "\n================================================================="
echo "   ✅ ALL QUALITY GATES PASSED (5/5)                             "
echo "================================================================="
