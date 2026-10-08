"""Verify local research assets and links; no agent review or quality rating."""

import glob
import hashlib
import os
import re
from pathlib import Path

RESEARCH_ROOT = str(Path(__file__).resolve().parents[1] / "research")
AI_ENCYCLOPEDIA_DIR = os.path.join(RESEARCH_ROOT, "ai_encyclopedia")
GCP_INFRA_DIR = os.path.join(RESEARCH_ROOT, "google_cloud_agentic_infra")
MAS_DIR = os.path.join(RESEARCH_ROOT, "multi_agent_systems")


def verify_filesystem_assets():
    """Verify all files, counts, sizes, links, and PDFs."""
    all_files = glob.glob(f"{RESEARCH_ROOT}/**/*", recursive=True)
    all_files = [f for f in all_files if os.path.isfile(f)]
    
    md_files = [f for f in all_files if f.endswith(".md")]
    pdf_files = [f for f in all_files if f.endswith(".pdf")]
    png_files = [f for f in all_files if f.endswith(".png")]
    
    total_lines = 0
    file_stats = {}
    for md in md_files:
        with open(md, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            total_lines += len(lines)
            rel_path = os.path.relpath(md, RESEARCH_ROOT)
            file_stats[rel_path] = len(lines)
            
    link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    broken_links = []
    total_links = 0
    for md in md_files:
        with open(md, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        for match in link_pattern.finditer(content):
            total_links += 1
            text, target = match.groups()
            if target.startswith("file://"):
                path_part = target.replace("file://", "").split("#")[0]
                if not os.path.exists(path_part):
                    broken_links.append((md, target, "Missing file"))
            elif not target.startswith(("http://", "https://", "mailto:", "#")):
                base_dir = os.path.dirname(md)
                clean_target = target.split("#")[0]
                if clean_target:
                    resolved = os.path.normpath(os.path.join(base_dir, clean_target))
                    if not os.path.exists(resolved):
                        broken_links.append((md, target, f"Missing relative: {resolved}"))

    return {
        "total_files": len(all_files),
        "md_files_count": len(md_files),
        "pdf_files_count": len(pdf_files),
        "png_files_count": len(png_files),
        "total_md_lines": total_lines,
        "total_links": total_links,
        "broken_links_count": len(broken_links),
        "broken_links": broken_links,
        "pdf_details": [
            {"name": os.path.basename(p), "size_bytes": os.path.getsize(p)}
            for p in sorted(pdf_files)
        ],
    }


def compute_merkle_provenance(file_paths):
    """Compute SHA-256 Merkle root across all verified research documents."""
    leaves = []
    for fp in sorted(file_paths):
        if os.path.isfile(fp):
            with open(fp, "rb") as f:
                content = f.read()
                leaves.append(hashlib.sha256(content).hexdigest())
    
    if not leaves:
        raise ValueError("No documents were verified")
        
    current = leaves
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            left = current[i]
            right = current[i + 1] if i + 1 < len(current) else left
            combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
            next_level.append(combined)
        current = next_level
    return current[0]


def main():
    """Static asset/link verification only; no fabricated agent reviews or rating."""
    import argparse
    import json
    global RESEARCH_ROOT
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=RESEARCH_ROOT)
    args = parser.parse_args()
    RESEARCH_ROOT = os.path.abspath(args.root)
    results = verify_filesystem_assets()
    paths = glob.glob(f"{RESEARCH_ROOT}/**/*.md", recursive=True)
    results["merkle_root"] = compute_merkle_provenance(paths) if paths else None
    results["scope"] = "local asset counts, SHA-256 provenance and local link existence only"
    results["academic_factual_accuracy"] = "not_assessed"
    results["live_agent_review"] = "not_performed"
    results["rating"] = "not_awarded"
    ok = results["md_files_count"] > 0 and results["broken_links_count"] == 0
    results["status"] = "passed" if ok else "failed"
    print(json.dumps(results, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
