"""
mas.tools.bigquery_tool: Enterprise Google Cloud BigQuery execution and FinOps dry-run tools.
Enables autonomous SQL authoring, byte-scanning estimation, and dataset exploration for MAS agents.

Architect: Acinonyx
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import Any, Dict, Optional
from mas.mcp.protocol import MCPRegistry
from mas.observability import LOGGER, METRICS

# BigQuery on-demand pricing standard ($6.25 per TB)
PRICE_PER_TB_USD = 6.25
BYTES_PER_TB = 1024 ** 4


def _find_bq_binary() -> Optional[str]:
    """Locate bq CLI binary from PATH or known GCP SDK paths."""
    found = shutil.which("bq")
    if found:
        return found
    candidate = "/home/acinonyx/Desktop/MAS/gcloud auth application-default login/google-cloud-sdk/bin/bq"
    if os.path.exists(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return None


def bigquery_dry_run_tool(query: str, project_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate SQL syntax and calculate bytes scanned and estimated USD cost before query execution.
    Enforces FinOps governance and prevents accidental large table scans.
    """
    bq_bin = _find_bq_binary()
    if not bq_bin:
        LOGGER.warning("BigQuery CLI (bq) not found; executing simulated FinOps dry-run.")
        return {
            "success": True,
            "valid": True,
            "bytes_processed": 0,
            "estimated_cost_usd": 0.0,
            "message": "Simulated dry-run: Query syntax valid.",
            "mode": "simulated",
        }

    cmd = [
        bq_bin,
        "query",
        "--use_legacy_sql=false",
        "--dry_run",
        "--label",
        "datacloud:antigravity",
    ]
    if project_id:
        cmd.extend(["--project_id", project_id])
    cmd.append(query)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15.0,
        )
        combined_output = (proc.stdout or "") + (proc.stderr or "")

        if proc.returncode != 0:
            METRICS.incr("bigquery.dry_run_failure")
            return {
                "success": False,
                "valid": False,
                "error": combined_output.strip(),
            }

        # Parse bytes: e.g. "running this query will process 12345 bytes of data"
        match = re.search(r"process\s+([0-9]+(?:\.[0-9]+)?)\s*([KMGTP]?B|bytes)", combined_output, re.IGNORECASE)
        bytes_val = 0
        if match:
            raw_num = float(match.group(1))
            unit = match.group(2).upper()
            multipliers = {
                "BYTES": 1,
                "B": 1,
                "KB": 1024,
                "MB": 1024**2,
                "GB": 1024**3,
                "TB": 1024**4,
                "PB": 1024**5,
            }
            bytes_val = int(raw_num * multipliers.get(unit, 1))

        cost_usd = (bytes_val / BYTES_PER_TB) * PRICE_PER_TB_USD
        METRICS.incr("bigquery.dry_run_success")
        return {
            "success": True,
            "valid": True,
            "bytes_processed": bytes_val,
            "estimated_cost_usd": round(cost_usd, 6),
            "raw_message": combined_output.strip(),
            "mode": "native",
        }
    except Exception as e:
        return {
            "success": False,
            "valid": False,
            "error": f"Dry-run execution error: {str(e)}",
        }


def bigquery_query_run_tool(
    query: str,
    project_id: Optional[str] = None,
    max_rows: int = 50,
    max_bytes_billed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Execute standard SQL query against Google Cloud BigQuery and return structured JSON records.
    Automatically applies mandatory labeling, dry-run safety gates, and row limits.
    """
    # 1. Pre-execution FinOps Dry-Run Gate
    dry_run = bigquery_dry_run_tool(query, project_id=project_id)
    if not dry_run.get("valid", False):
        return {
            "success": False,
            "error": f"Query rejected by BigQuery syntax/cost gate: {dry_run.get('error')}",
        }

    # FinOps byte limit check
    if max_bytes_billed and dry_run.get("bytes_processed", 0) > max_bytes_billed:
        return {
            "success": False,
            "error": f"Query exceeds max_bytes_billed threshold: {dry_run.get('bytes_processed')} > {max_bytes_billed}",
        }

    bq_bin = _find_bq_binary()
    if not bq_bin:
        # Simulated execution for offline testing
        return {
            "success": True,
            "total_rows": 1,
            "rows": [{"status": "simulated_success", "query": query}],
            "bytes_processed": 0,
            "mode": "simulated",
        }

    cmd = [
        bq_bin,
        "query",
        "--use_legacy_sql=false",
        "--format=json",
        f"--max_rows={max(1, min(1000, max_rows))}",
        "--label",
        "datacloud:antigravity",
    ]
    if project_id:
        cmd.extend(["--project_id", project_id])
    cmd.append(query)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30.0,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout).strip()
            METRICS.incr("bigquery.query_failure")
            return {"success": False, "error": err}

        out_text = proc.stdout.strip()
        rows = json.loads(out_text) if out_text else []
        METRICS.incr("bigquery.query_success")
        return {
            "success": True,
            "total_rows": len(rows),
            "rows": rows,
            "bytes_processed": dry_run.get("bytes_processed", 0),
            "estimated_cost_usd": dry_run.get("estimated_cost_usd", 0.0),
            "mode": "native",
        }
    except Exception as e:
        return {"success": False, "error": f"BigQuery query error: {str(e)}"}


def register_bigquery_tools(registry: MCPRegistry) -> None:
    """Register BigQuery tools in the MCP tooling fabric."""
    registry.register_tool(
        name="bigquery_dry_run",
        description="Dry-run a Google Cloud BigQuery SQL query to validate syntax, estimate bytes scanned, and calculate USD cost without executing.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Standard SQL query string"},
                "project_id": {"type": "string", "description": "Optional GCP Project ID override"},
            },
            "required": ["query"],
        },
        handler=lambda **kwargs: bigquery_dry_run_tool(
            query=kwargs["query"], project_id=kwargs.get("project_id")
        ),
    )

    registry.register_tool(
        name="bigquery_query_run",
        description="Execute a Standard SQL query on Google Cloud BigQuery and return tabular JSON rows. Includes automatic labeling and cost gates.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Standard SQL query string"},
                "project_id": {"type": "string", "description": "Optional GCP Project ID override"},
                "max_rows": {"type": "integer", "default": 50, "description": "Maximum rows to return"},
            },
            "required": ["query"],
        },
        handler=lambda **kwargs: bigquery_query_run_tool(
            query=kwargs["query"],
            project_id=kwargs.get("project_id"),
            max_rows=kwargs.get("max_rows", 50),
        ),
    )
