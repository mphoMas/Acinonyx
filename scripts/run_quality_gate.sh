#!/usr/bin/env bash
# ==============================================================================
# scripts/run_quality_gate.sh: Enterprise Quality & Verification Gate (10/10)
# Enforces zero-regression test execution, 100% capability completeness,
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

echo -e "\n[GATE 3/5]: Running Research Directorate Swarm Verification..."
python3 scripts/verify_research_swarm.py

echo -e "\n[GATE 4/5]: Compiling Portal Catalog & Data Cache..."
python3 scripts/compile_portal_catalog.py

echo -e "\n[GATE 5/5]: Executing Full Unit & Integration Test Suite..."
python3 -m pytest tests/ -v

echo -e "\n================================================================="
echo "   ✅ ALL QUALITY GATES PASSED (5/5)                             "
echo "================================================================="
