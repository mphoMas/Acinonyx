#!/usr/bin/env python3
"""
scripts/run_company_profile_team.py: Run the AcinonyxLabs Multi-Agent Company Profile & JV Strike Pod.
Executes an adversarial review and strategic enhancement across Market Research, Product Strategy,
Systems Architecture, Data Engineering, and Adversarial Red-Teaming.

Usage:
    python3 scripts/run_company_profile_team.py [--provider auto|gemini|mock] [--output path]
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

# Load local environment variables (.env)
load_dotenv(ROOT_DIR / ".env")

from mas.organization.profile_pod import CompanyProfilePod
from mas.providers.factory import create_llm_provider

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_profile_team")


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AcinonyxLabs Multi-Agent Profile Pod")
    parser.add_argument(
        "--provider",
        default="auto",
        choices=["auto", "gemini", "claude", "huggingface", "mock"],
        help="LLM provider for agent reasoning (default: auto)",
    )
    parser.add_argument(
        "--profile",
        default=str(ROOT_DIR / "company" / "COMPANY_PROFILE.md"),
        help="Path to the company profile markdown file",
    )
    parser.add_argument(
        "--jv-terms",
        default=str(ROOT_DIR / "company" / "JV_TERM_SHEET_TEMPLATE.md"),
        help="Path to the JV term sheet markdown file",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT_DIR / "workspace" / "reports" / "COMPANY_PROFILE_TEAM_REVIEW.md"),
        help="Path to save the generated review dossier",
    )
    args = parser.parse_args()

    profile_path = Path(args.profile)
    jv_terms_path = Path(args.jv_terms)
    output_path = Path(args.output)

    if not profile_path.exists():
        logger.error("Company profile file not found at: %s", profile_path)
        return 1

    profile_content = profile_path.read_text(encoding="utf-8")
    jv_terms_content = jv_terms_path.read_text(encoding="utf-8") if jv_terms_path.exists() else ""

    logger.info("Initializing LLM provider: %s", args.provider)
    llm = create_llm_provider(args.provider)
    logger.info("Instantiated provider: %s", type(llm).__name__)

    logger.info("Mobilizing AcinonyxLabs CompanyProfilePod...")
    pod = CompanyProfilePod(llm_provider=llm)

    print("\n" + "=" * 70)
    print("🚀 MOBILIZING ACINONYX MULTI-AGENT PROFILE & JV STRIKE POD")
    print(f"   Pod ID: {pod.pod_id}")
    print(f"   Provider: {type(llm).__name__}")
    print("   Agents: Market Researcher, Product Lead, Chief Architect,")
    print("           Data Engineer, Adversarial Red Team, Technical Writer")
    print("=" * 70 + "\n")

    result = await pod.execute_review(
        profile_content=profile_content,
        jv_terms_content=jv_terms_content,
    )

    report_md = result.to_markdown_report()

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_md, encoding="utf-8")

    # Also mirror to AcinonyxLabs repo if present
    ext_repo_reports = Path("/home/acinonyx/Desktop/AcinonyxLabs/reports")
    if ext_repo_reports.parent.exists():
        ext_repo_reports.mkdir(parents=True, exist_ok=True)
        (ext_repo_reports / "COMPANY_PROFILE_TEAM_REVIEW.md").write_text(report_md, encoding="utf-8")
        logger.info("Mirrored dossier to /home/acinonyx/Desktop/AcinonyxLabs/reports/")

    print("\n" + "=" * 70)
    print("✅ MULTI-AGENT EVALUATION COMPLETE")
    print(f"   Duration: {result.elapsed_seconds:.2f} seconds")
    print(f"   Tokens Consumed: {result.tokens_consumed}")
    print(f"   Merkle Provenance: {result.merkle_provenance_hash}")
    print(f"   Report Saved: {output_path}")
    print("=" * 70 + "\n")

    print("\n--- EXECUTIVE SYNTHESIS PREVIEW ---")
    print(result.executive_synthesis[:800] + ("..." if len(result.executive_synthesis) > 800 else ""))
    print("\nFull dossier available at: " + str(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
