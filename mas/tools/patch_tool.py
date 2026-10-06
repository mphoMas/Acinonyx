"""
mas.tools.patch_tool: Surgical unified diff and contiguous line replacement tool.
Enables agents to apply precise code modifications without overwriting entire files,
minimizing token consumption and preventing accidental data loss.

Architect: Acinonyx
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional
from mas.mcp.protocol import MCPRegistry
from mas.observability import METRICS
from mas.tools.filesystem import _is_path_safe


def fs_patch_file_tool(
    path: str,
    target_content: str,
    replacement_content: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    allow_multiple: bool = False,
) -> Dict[str, Any]:
    """
    Surgically replace a contiguous block of text within a target file.
    Validates path boundaries and requires exact unique substring matching.
    """
    if not _is_path_safe(path):
        return {
            "success": False,
            "error": f"Access denied. Path '{path}' is outside authorized project boundaries.",
        }

    if not os.path.exists(path):
        return {"success": False, "error": f"File not found: '{path}'"}

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        full_content = "".join(lines)
    except Exception as e:
        return {"success": False, "error": f"Failed to read '{path}': {e}"}

    # If line bounds provided (1-indexed inclusive)
    if start_line is not None and end_line is not None:
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        slice_chunk = "".join(lines[start_idx:end_idx])

        if target_content not in slice_chunk:
            return {
                "success": False,
                "error": f"Target content not found within lines {start_line}..{end_line}.",
            }

        new_slice = slice_chunk.replace(target_content, replacement_content, 1 if not allow_multiple else -1)
        new_content = "".join(lines[:start_idx]) + new_slice + "".join(lines[end_idx:])
        occurrences = slice_chunk.count(target_content)
    else:
        occurrences = full_content.count(target_content)
        if occurrences == 0:
            return {
                "success": False,
                "error": f"Target content not found in '{path}'. Ensure exact character match.",
            }
        if occurrences > 1 and not allow_multiple:
            return {
                "success": False,
                "error": f"Found {occurrences} occurrences of target content in '{path}'. Specify start_line/end_line or set allow_multiple=True.",
            }
        new_content = full_content.replace(target_content, replacement_content, 1 if not allow_multiple else -1)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        METRICS.incr("filesystem.patch_success")
        return {
            "success": True,
            "path": path,
            "occurrences_replaced": occurrences,
            "bytes_before": len(full_content),
            "bytes_after": len(new_content),
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to write patch to '{path}': {e}"}


def register_patch_tools(registry: MCPRegistry) -> None:
    """Register surgical patching tools into MCP."""
    registry.register_tool(
        name="fs_patch_file",
        description="Surgically replace a contiguous block of text in a file without rewriting the entire file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Target file path"},
                "target_content": {"type": "string", "description": "Exact string to be replaced"},
                "replacement_content": {"type": "string", "description": "Replacement string"},
                "start_line": {"type": "integer", "description": "Optional 1-indexed starting line"},
                "end_line": {"type": "integer", "description": "Optional 1-indexed ending line"},
                "allow_multiple": {"type": "boolean", "default": False},
            },
            "required": ["path", "target_content", "replacement_content"],
        },
        handler=lambda **kwargs: fs_patch_file_tool(
            path=kwargs["path"],
            target_content=kwargs["target_content"],
            replacement_content=kwargs["replacement_content"],
            start_line=kwargs.get("start_line"),
            end_line=kwargs.get("end_line"),
            allow_multiple=kwargs.get("allow_multiple", False),
        ),
    )
