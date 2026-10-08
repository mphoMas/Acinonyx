"""
mas.tools.storage_tool: Google Cloud Storage (GCS) object operations tool for MAS agents.
Enables bucket listing, file staging, and object uploads/downloads with explicit failure when the cloud CLI is unavailable.

Architect: Acinonyx
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, Optional

from mas.config import REPO_ROOT
from mas.mcp.protocol import MCPRegistry
from mas.observability import METRICS


def _find_gcloud_or_gsutil() -> Optional[str]:
    found = shutil.which("gcloud")
    if found:
        return found
    candidate = f"{REPO_ROOT}/gcloud auth application-default login/google-cloud-sdk/bin/gcloud"
    if os.path.exists(candidate) and os.access(candidate, os.X_OK):
        return candidate
    return None


def gcs_list_objects_tool(
    bucket_or_uri: str,
    project_id: Optional[str] = None,
    max_items: int = 50,
) -> Dict[str, Any]:
    """List objects in a Google Cloud Storage bucket or URI prefix."""
    gcloud_bin = _find_gcloud_or_gsutil()
    target = bucket_or_uri if bucket_or_uri.startswith("gs://") else f"gs://{bucket_or_uri}"

    if not gcloud_bin:
        return {
            "success": False,
            "uri": target,
            "items": [],
            "count": 0,
            "mode": "unavailable",
            "error": "GCS CLI unavailable; no objects were listed.",
        }

    cmd = [gcloud_bin, "storage", "ls"]
    if project_id:
        cmd.extend(["--project", project_id])
    cmd.append(target)

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15.0)
        if proc.returncode != 0:
            return {"success": False, "uri": target, "items": [], "error": proc.stderr.strip(), "mode": "native"}
        output = proc.stdout.strip()
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        METRICS.incr("gcs.list_success")
        return {
            "success": True,
            "uri": target,
            "items": lines[:max_items],
            "count": len(lines),
            "mode": "native",
        }
    except Exception as e:
        return {"success": False, "uri": target, "error": f"GCS list error: {str(e)}"}


def gcs_read_text_tool(uri: str, max_bytes: int = 100000) -> Dict[str, Any]:
    """Read a text or CSV object directly from Google Cloud Storage."""
    if not uri.startswith("gs://"):
        return {"success": False, "error": "URI must start with 'gs://'"}

    gcloud_bin = _find_gcloud_or_gsutil()
    if not gcloud_bin:
        return {"success": False, "uri": uri, "error": "GCS CLI unavailable; no object was read.", "mode": "unavailable"}

    cmd = [gcloud_bin, "storage", "cat", uri]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20.0)
        if proc.returncode != 0:
            return {"success": False, "uri": uri, "error": proc.stderr.strip()}
        text = proc.stdout[:max_bytes]
        METRICS.incr("gcs.read_success")
        return {
            "success": True,
            "uri": uri,
            "content": text,
            "bytes_read": len(text),
            "mode": "native",
        }
    except Exception as e:
        return {"success": False, "uri": uri, "error": f"GCS read error: {str(e)}"}


def register_storage_tools(registry: MCPRegistry) -> None:
    """Register Cloud Storage tools into MCP."""
    registry.register_tool(
        name="gcs_list_objects",
        description="List objects or prefixes in a Google Cloud Storage bucket (e.g. 'gs://my-bucket/stage/').",
        input_schema={
            "type": "object",
            "properties": {
                "bucket_or_uri": {"type": "string", "description": "Bucket name or gs:// URI prefix"},
                "project_id": {"type": "string", "description": "Optional GCP Project ID override"},
                "max_items": {"type": "integer", "default": 50},
            },
            "required": ["bucket_or_uri"],
        },
        handler=lambda **kwargs: gcs_list_objects_tool(
            bucket_or_uri=kwargs["bucket_or_uri"],
            project_id=kwargs.get("project_id"),
            max_items=kwargs.get("max_items", 50),
        ),
    )

    registry.register_tool(
        name="gcs_read_text",
        description="Read text or CSV content from a Google Cloud Storage object (gs://).",
        input_schema={
            "type": "object",
            "properties": {
                "uri": {"type": "string", "description": "Target gs:// object URI"},
                "max_bytes": {"type": "integer", "default": 100000},
            },
            "required": ["uri"],
        },
        handler=lambda **kwargs: gcs_read_text_tool(
            uri=kwargs["uri"], max_bytes=kwargs.get("max_bytes", 100000)
        ),
    )
