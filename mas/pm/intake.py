"""
mas.pm.intake: Canonical intake and task assignment workflow validators for MAS-PM.
Deliverable for task PM-02 (MAS-8) by product_lead.
"""

from typing import Any, Dict


def validate_canonical_intake(issue_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates that newly created tasks satisfy canonical intake criteria."""
    required_fields = ["title", "project_key", "priority"]
    for field in required_fields:
        if field not in issue_data or not issue_data[field]:
            raise ValueError(f"Canonical intake error: missing required field '{field}'.")

    return {
        "status": "VALIDATED",
        "intake_mode": "canonical_board_workflow",
        "title": issue_data["title"],
    }
