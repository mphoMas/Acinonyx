"""
mas.tools.filesystem: Filesystem inspection, reading, writing, and search tools for MCP.
Architect: Acinonyx
"""

from __future__ import annotations
import glob
import os
from typing import Any, List


# Global jail boundaries for autonomous agent filesystem operations
ALLOWED_PROJECT_ROOTS: List[str] = [
    "/home/acinonyx/Desktop/MAS",
    "/srv/mas-projects",
    "/tmp",
]


def set_allowed_roots(roots: List[str]) -> None:
    """Configure authorized project roots for filesystem operations."""
    global ALLOWED_PROJECT_ROOTS
    ALLOWED_PROJECT_ROOTS = [os.path.abspath(r) for r in roots]


def _is_path_safe(path: str) -> bool:
    """Verify that the target path resolves within an authorized project boundary."""
    abs_path = os.path.abspath(path)
    return any(abs_path.startswith(root) for root in ALLOWED_PROJECT_ROOTS)


async def fs_read_file(path: str, max_bytes: int = 100000) -> str:
    """Read contents of a file at the given path."""
    if not _is_path_safe(path):
        return f"ERROR: Access denied. Path '{path}' is outside authorized project boundaries."
    if not os.path.exists(path):
        return f"ERROR: File not found at '{path}'"
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)
        return content
    except Exception as e:
        return f"ERROR: Failed to read '{path}': {str(e)}"


async def fs_write_file(path: str, content: str) -> str:
    """Write or overwrite content to a file, creating parent directories if necessary."""
    if not _is_path_safe(path):
        return f"ERROR: Access denied. Path '{path}' is outside authorized project boundaries."
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"SUCCESS: File written to '{path}' ({len(content)} bytes)."
    except Exception as e:
        return f"ERROR: Failed to write '{path}': {str(e)}"


async def fs_list_dir(path: str = ".") -> str:
    """List directory contents with file types and sizes."""
    if not os.path.exists(path):
        return f"ERROR: Directory '{path}' not found."
    try:
        entries = []
        for item in sorted(os.listdir(path)):
            full_path = os.path.join(path, item)
            is_dir = os.path.isdir(full_path)
            size = os.path.getsize(full_path) if not is_dir else 0
            kind = "DIR" if is_dir else f"FILE ({size}B)"
            entries.append(f"{kind.ljust(15)} {item}")
        return "\n".join(entries) if entries else "[Empty directory]"
    except Exception as e:
        return f"ERROR: Failed to list '{path}': {str(e)}"


async def fs_glob(pattern: str) -> str:
    """Search files matching a glob pattern."""
    try:
        matches = glob.glob(pattern, recursive=True)
        return "\n".join(matches) if matches else "[No matches found]"
    except Exception as e:
        return f"ERROR: Glob failed: {str(e)}"


def register_filesystem_tools(registry: Any) -> None:
    """Register filesystem capabilities into an MCPRegistry."""
    registry.register_tool(
        name="fs_read",
        description="Reads the text content of a file.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"},
                "max_bytes": {"type": "integer", "description": "Maximum bytes to read", "default": 100000},
            },
            "required": ["path"],
        },
        handler=fs_read_file,
    )

    registry.register_tool(
        name="fs_write",
        description="Writes content to a file, creating parent directories if needed.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Text content to write"},
            },
            "required": ["path", "content"],
        },
        handler=fs_write_file,
    )

    registry.register_tool(
        name="fs_list",
        description="Lists files and subdirectories in a folder.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path", "default": "."},
            },
        },
        handler=fs_list_dir,
    )

    registry.register_tool(
        name="fs_glob",
        description="Finds files matching a glob pattern (e.g. '**/*.py').",
        input_schema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob search pattern"},
            },
            "required": ["pattern"],
        },
        handler=fs_glob,
    )
