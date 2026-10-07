"""
mas.release_policy: Independent, deterministic release evaluation engine for MAS web generation.
Enforces strict policy specifications, candidate cryptographic binding, verification completeness,
and defect classification without allowing unverified releases.

Architect: Acinonyx
"""

from __future__ import annotations

import hashlib
import json
import os
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

HEX_DIGITS = set(string.hexdigits)


@dataclass(frozen=True)
class PolicySpec:
    """
    Independently controlled release policy specification.
    Never extracted from untrusted audit payloads.
    """
    policy_id: str
    policy_version: str
    target_profile: str = "WCAG_AA"  # "WCAG_AA" | "WCAG_AAA"
    mandatory_suites: Set[str] = field(default_factory=lambda: {"static_contract", "axe_a11y", "playwright_render"})
    max_advisories: int = 10
    allowed_classifications: Set[str] = field(
        default_factory=lambda: {"BLOCKING_FUNCTIONAL", "BLOCKING_A11Y", "ADVISORY_STYLE"}
    )
    enforce_evidence_integrity: bool = True

    def validate(self) -> None:
        if not self.policy_id or not str(self.policy_id).strip():
            raise ValueError("PolicySpec.policy_id must not be empty.")
        if not self.mandatory_suites:
            raise ValueError("PolicySpec.mandatory_suites must contain at least one required suite.")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PolicySpec:
        return cls(
            policy_id=str(data.get("policy_id", "")),
            policy_version=str(data.get("policy_version", "1.0.0")),
            target_profile=str(data.get("target_profile", "WCAG_AA")),
            mandatory_suites=set(data.get("mandatory_suites", ["static_contract", "axe_a11y", "playwright_render"])),
            max_advisories=int(data.get("max_advisories", 10)),
            allowed_classifications=set(data.get("allowed_classifications", ["BLOCKING_FUNCTIONAL", "BLOCKING_A11Y", "ADVISORY_STYLE"])),
            enforce_evidence_integrity=bool(data.get("enforce_evidence_integrity", True)),
        )

    @classmethod
    def load_from_file(cls, file_path: str | Path) -> PolicySpec:
        p = Path(file_path).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"Policy file not found: {p}")
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        spec = cls.from_dict(data)
        spec.validate()
        return spec


@dataclass
class PolicyEvaluationResult:
    decision: str  # "RELEASE_PERMITTED" | "RELEASE_BLOCKED"
    reasons: List[str]
    blocking_finding_ids: List[str]
    advisory_count: int
    verified_suites: List[str]
    candidate_hash: str
    run_id: str
    policy_id: str

    @property
    def is_permitted(self) -> bool:
        return self.decision == "RELEASE_PERMITTED"


def compute_candidate_hash(content: str | bytes) -> str:
    """Compute normalized SHA-256 hash of a candidate artifact."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def evaluate_release_policy(
    policy: PolicySpec,
    candidate_hash: str,
    run_id: str,
    audit: Dict[str, Any],
    findings_reports: List[Dict[str, Any]],
    workspace_root: Optional[str | Path] = None,
) -> PolicyEvaluationResult:
    """
    Deterministically evaluates release eligibility against an independent PolicySpec.
    """
    reasons: List[str] = []
    blocking_ids: List[str] = []
    verified_suites: List[str] = []
    advisories = 0

    # Gate 0: Validate independent policy
    try:
        policy.validate()
    except Exception as e:
        return PolicyEvaluationResult(
            decision="RELEASE_BLOCKED",
            reasons=[f"Invalid PolicySpec: {e}"],
            blocking_finding_ids=[],
            advisory_count=0,
            verified_suites=[],
            candidate_hash=candidate_hash if isinstance(candidate_hash, str) else "invalid",
            run_id=run_id if isinstance(run_id, str) else "invalid",
            policy_id=getattr(policy, "policy_id", "unknown"),
        )

    # Gate 1: Strict candidate hash and run_id format validation
    if not isinstance(candidate_hash, str) or len(candidate_hash) != 64 or not all(c in HEX_DIGITS for c in candidate_hash):
        reasons.append("Invalid or missing candidate_hash: must be exactly 64 hexadecimal characters.")

    if not isinstance(run_id, str) or not run_id.strip():
        reasons.append("Invalid or missing run_id: must be a non-empty string.")

    # Gate 2: Audit payload structure and candidate binding
    if not isinstance(audit, dict):
        return PolicyEvaluationResult(
            decision="RELEASE_BLOCKED",
            reasons=["Audit payload must be a dictionary."],
            blocking_finding_ids=[],
            advisory_count=0,
            verified_suites=[],
            candidate_hash=candidate_hash if isinstance(candidate_hash, str) else "invalid",
            run_id=run_id if isinstance(run_id, str) else "invalid",
            policy_id=policy.policy_id,
        )

    if audit.get("candidate_hash") != candidate_hash:
        reasons.append(
            f"Audit candidate_hash mismatch: expected '{candidate_hash}', got '{audit.get('candidate_hash')}'."
        )

    if audit.get("run_id") != run_id:
        reasons.append(
            f"Audit run_id mismatch: expected '{run_id}', got '{audit.get('run_id')}'."
        )

    # Strictly check boolean True (not truthy strings like "false")
    if audit.get("execution_complete") is not True:
        reasons.append("Verification audit is marked incomplete (execution_complete must be boolean True).")

    # Gate 3: Verification suite execution reconciliation
    suite_executions = audit.get("suite_executions")
    if suite_executions is None or not isinstance(suite_executions, list) or len(suite_executions) == 0:
        reasons.append("Audit suite_executions must be a non-null, non-empty list of execution records.")
        suite_executions = []

    # Detect duplicate or ambiguous suite executions
    suite_status_map: Dict[str, str] = {}
    suite_counts: Dict[str, int] = {}
    for entry in suite_executions:
        if not isinstance(entry, dict):
            reasons.append("Malformed suite_execution entry in audit (must be a dictionary).")
            continue
        s_name = entry.get("suite_name")
        s_status = entry.get("status")

        if not isinstance(s_name, str) or not s_name.strip():
            reasons.append("Unnamed or invalid suite_execution entry in audit.")
            continue

        suite_counts[s_name] = suite_counts.get(s_name, 0) + 1
        if s_name in suite_status_map and suite_status_map[s_name] != s_status:
            reasons.append(
                f"Ambiguous execution record for suite '{s_name}': reported both '{suite_status_map[s_name]}' and '{s_status}'."
            )
        suite_status_map[s_name] = s_status

    for s_name, count in suite_counts.items():
        if count > 1:
            reasons.append(
                f"Conflicting duplicate executions reported for suite '{s_name}' ({count} entries). Ambiguous runs are rejected."
            )

    # Reconcile mandatory suites against completed suites
    completed_suites = {
        s_name for s_name, status in suite_status_map.items() if status == "COMPLETED"
    }

    missing_suites = policy.mandatory_suites - completed_suites
    if missing_suites:
        reasons.append(f"Missing mandatory verification suites: {sorted(missing_suites)}.")

    # Gate 4: Findings Report Binding & Completeness
    reports_by_suite: Dict[str, Dict[str, Any]] = {}
    if not isinstance(findings_reports, list):
        reasons.append("findings_reports must be a list of report dictionaries.")
        findings_reports = []

    for rep in findings_reports:
        if not isinstance(rep, dict):
            reasons.append("Malformed findings report entry (must be a dictionary).")
            continue
        rep_suite = rep.get("suite_name")
        if not isinstance(rep_suite, str) or not rep_suite.strip():
            reasons.append("Findings report missing valid 'suite_name'.")
            continue

        # Check candidate and run_id bindings on each report
        if rep.get("candidate_hash") != candidate_hash:
            reasons.append(
                f"Findings report for '{rep_suite}' has mismatched candidate_hash: got '{rep.get('candidate_hash')}'."
            )
        if rep.get("run_id") != run_id:
            reasons.append(
                f"Findings report for '{rep_suite}' has mismatched run_id: got '{rep.get('run_id')}'."
            )

        # Critical check: report must explicitly contain the "findings" key and it must be a list
        if "findings" not in rep or not isinstance(rep["findings"], list):
            reasons.append(f"Findings report for suite '{rep_suite}' is missing mandatory 'findings' list.")
            continue

        if rep_suite in reports_by_suite:
            reasons.append(f"Duplicate findings reports submitted for suite '{rep_suite}'.")
        reports_by_suite[rep_suite] = rep

    # Verify that every completed suite has a valid findings report
    for s_name in completed_suites:
        if s_name not in reports_by_suite:
            reasons.append(
                f"Suite '{s_name}' was marked COMPLETED in audit, but no corresponding findings report was supplied."
            )
        else:
            verified_suites.append(s_name)

    # Gate 5: Inspect Findings and Enforce Classification Rules
    for rep_suite, rep in reports_by_suite.items():
        findings = rep.get("findings", [])

        for finding in findings:
            if not isinstance(finding, dict):
                reasons.append(f"Malformed finding entry in suite '{rep_suite}'.")
                continue

            f_id = finding.get("finding_id", "UNKNOWN_ID")
            classification = finding.get("classification")

            # Check for unknown classification
            if classification not in policy.allowed_classifications:
                reasons.append(
                    f"Unknown defect classification '{classification}' in finding '{f_id}' (suite '{rep_suite}')."
                )
                blocking_ids.append(f_id)
                continue

            if classification in ("BLOCKING_FUNCTIONAL", "BLOCKING_A11Y"):
                blocking_ids.append(f_id)
                rule_id = finding.get("rule_id", "UNKNOWN_RULE")
                target = finding.get("target_selector", "UNKNOWN_TARGET")
                obs = finding.get("observed_state", "No observed state provided.")
                reasons.append(f"[{classification}] {rule_id} on {target}: {obs}")

                # Evidence integrity verification for blocking findings
                if policy.enforce_evidence_integrity:
                    ev = finding.get("evidence_artifact")
                    if not ev or not str(ev).strip():
                        reasons.append(
                            f"Blocking finding '{f_id}' missing required 'evidence_artifact'."
                        )
                    else:
                        # Check existence of local file if applicable
                        ev_str = str(ev)
                        ev_path_part = ev_str.split("#")[0].strip()
                        if ev_path_part and ("/" in ev_path_part or ev_path_part.endswith((".json", ".html", ".png", ".txt"))):
                            target_p = Path(ev_path_part)
                            if not target_p.is_absolute() and workspace_root:
                                target_p = (Path(workspace_root) / target_p).resolve()
                            if not target_p.exists():
                                reasons.append(
                                    f"Blocking finding '{f_id}' references non-existent evidence artifact: '{ev}'."
                                )

                    bbox = finding.get("bounding_box")
                    if bbox:
                        w = bbox.get("width", 0)
                        h = bbox.get("height", 0)
                        if w <= 0 or h <= 0:
                            reasons.append(
                                f"Finding '{f_id}' bounding_box has invalid dimensions (width={w}, height={h} must be > 0)."
                            )

            elif classification == "ADVISORY_STYLE":
                # Style advisories are strictly non-blocking
                advisories += 1

    # Final Decision: advisories do NOT block release
    if reasons or blocking_ids:
        return PolicyEvaluationResult(
            decision="RELEASE_BLOCKED",
            reasons=reasons,
            blocking_finding_ids=blocking_ids,
            advisory_count=advisories,
            verified_suites=verified_suites,
            candidate_hash=candidate_hash if isinstance(candidate_hash, str) else "invalid",
            run_id=run_id if isinstance(run_id, str) else "invalid",
            policy_id=policy.policy_id,
        )

    return PolicyEvaluationResult(
        decision="RELEASE_PERMITTED",
        reasons=["All mandatory suites completed and bound; zero blocking defects found."],
        blocking_finding_ids=[],
        advisory_count=advisories,
        verified_suites=verified_suites,
        candidate_hash=candidate_hash,
        run_id=run_id,
        policy_id=policy.policy_id,
    )
