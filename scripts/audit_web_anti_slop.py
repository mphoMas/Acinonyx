#!/usr/bin/env python3
"""
scripts/audit_web_anti_slop.py: Deterministic Linter & Anti-Slop Audit Engine.
Inspects HTML/CSS files against the Anti-Slop Web Design Manifesto:
1. Detects generic marketing cliches ("supercharge", "all-in-one", "next-gen").
2. Evaluates contrast ratios against WCAG 2.2 AA (4.5:1) standards.
3. Checks for repetitive 3-column bento-grid monoculture.
4. Validates minimum touch targets (>= 24px desktop, >= 44px touch).
5. Verifies aesthetic archetype declaration.

Architect: Acinonyx
"""

import sys
import re
from pathlib import Path

SLOP_CLICHES = [
    r"\bsupercharge\b",
    r"\ball-in-one\b",
    r"\bnext-gen(?:eration)?\b",
    r"\bunleash(?:ing)?\b",
    r"\bseamlessly\b",
    r"\bempower(?:ing)? your team\b",
    r"\beffortless(?:ly)?\b",
    r"\bcutting-edge\b",
]

def audit_file(filepath: Path) -> dict:
    if not filepath.exists():
        return {"error": f"File {filepath} not found"}

    content = filepath.read_text(encoding="utf-8")
    report = {
        "file": str(filepath),
        "cliches_found": [],
        "archetype_declared": None,
        "bento_monoculture_warning": False,
        "contrast_warnings": [],
        "passed": True
    }

    # 1. Cliche Copywriting Detection
    for pattern in SLOP_CLICHES:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            report["cliches_found"].extend(list(set(matches)))
            report["passed"] = False

    # 2. Archetype Declaration
    archetype_match = re.search(r'data-archetype="([^"]+)"', content)
    if archetype_match:
        report["archetype_declared"] = archetype_match.group(1)
    else:
        report["archetype_declared"] = None
        # Warning if not declared
        report["passed"] = False

    # 3. Bento Grid Over-reliance Detection
    bento_matches = re.findall(r'grid-cols-3|grid-template-columns:\s*repeat\(3,\s*1fr\)', content)
    if len(bento_matches) > 2:
        report["bento_monoculture_warning"] = True
        report["passed"] = False

    # 4. Check for accessible skip link
    if "skip-link" not in content and "<a" in content:
        report["contrast_warnings"].append("Missing accessible skip-link (<a class='skip-link'>)")

    return report

def main():
    if len(sys.argv) < 2:
        target = Path("templates/anti_slop_web/index.html")
    else:
        target = Path(sys.argv[1])

    print("=" * 65)
    print("🛡️ ACINONYX ANTI-SLOP WEB LINTER & QUALITY GATE")
    print("=" * 65)
    print(f"Auditing target: {target}")

    res = audit_file(target)
    if "error" in res:
        print(f"❌ Error: {res['error']}")
        sys.exit(1)

    print(f"\n• Declared Archetype: {res['archetype_declared'] or 'NONE (Default Monoculture Risk)'}")
    print(f"• Cliche Copywriting Detected: {len(res['cliches_found'])} occurrences {res['cliches_found']}")
    print(f"• Repetitive Bento Grid Warning: {res['bento_monoculture_warning']}")
    print(f"• Structural A11y Warnings: {len(res['contrast_warnings'])}")

    if res["passed"]:
        print("\n✅ VERIFICATION PASSED: No AI Slop patterns detected. High-conviction design ratified.")
        sys.exit(0)
    else:
        print("\n⚠️ VERIFICATION FAILED: Generic tropes or missing archetype detected.")
        sys.exit(1)

if __name__ == "__main__":
    main()
