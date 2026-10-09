"""
mas.tools.filesystem: Filesystem inspection, reading, writing, and search tools for MCP.
Architect: Acinonyx
"""

from __future__ import annotations
import glob
import os
from contextlib import contextmanager
from typing import Any, List

from pathlib import Path
from mas.config import REPO_ROOT


# Global jail boundaries for autonomous agent filesystem operations
ALLOWED_PROJECT_ROOTS: List[Path] = [
    Path(REPO_ROOT).resolve(),
    Path("/srv/mas-projects").resolve(),
]


def set_allowed_roots(roots: List[str | Path]) -> None:
    """Configure authorized project roots for filesystem operations."""
    global ALLOWED_PROJECT_ROOTS
    ALLOWED_PROJECT_ROOTS = [Path(r).resolve() for r in roots]


def effective_roots() -> List[Path]:
    from mas.tenancy import current_binding
    binding = current_binding()
    if binding:
        binding.require("storage:read")
        return [binding.workspace]
    return ALLOWED_PROJECT_ROOTS


def _tenant_path(path: str | Path) -> str:
    from mas.tenancy import current_binding
    binding = current_binding()
    return str(binding.workspace / path) if binding and not Path(path).is_absolute() else str(path)


def _is_path_safe(path: str | Path) -> bool:
    """
    Verify that the target path resolves strictly within an authorized project boundary,
    preventing symlink traversal and prefix collisions.
    """
    try:
        real_path = Path(_tenant_path(path)).resolve()
        for root in effective_roots():
            try:
                if real_path == root or real_path.is_relative_to(root):
                    return True
            except (ValueError, TypeError):
                continue
        return False
    except Exception:
        return False


@contextmanager
def _tenant_parent(path: str, *, create: bool = False):
    """Walk directory descriptors without following mutable symlink components."""
    from mas.tenancy import current_binding
    binding = current_binding()
    binding.require("storage:write" if create else "storage:read")
    relative = Path(path).relative_to(binding.workspace)
    if ".." in relative.parts:
        raise PermissionError("Directory traversal denied")
    parts = relative.parts or (".",)
    directory = os.open(binding.workspace, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in parts[:-1]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=directory)
                except FileExistsError:
                    pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        yield directory, parts[-1]
    finally:
        os.close(directory)


async def fs_read_file(path: str, max_bytes: int = 100000) -> str:
    """Read contents of a file at the given path."""
    path = _tenant_path(path)
    if not _is_path_safe(path):
        return f"ERROR: Access denied. Path '{path}' is outside authorized project boundaries."
    if not os.path.exists(path):
        return f"ERROR: File not found at '{path}'"
    try:
        from mas.tenancy import current_binding
        if current_binding():
            with _tenant_parent(path) as (directory, name):
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                with os.fdopen(descriptor, "r", encoding="utf-8", errors="replace") as f:
                    return f.read(max_bytes)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)
        return content
    except Exception as e:
        return f"ERROR: Failed to read '{path}': {str(e)}"


async def fs_write_file(path: str, content: str) -> str:
    """Write or overwrite content to a file, creating parent directories if necessary."""
    from mas.tenancy import current_binding
    if current_binding():
        current_binding().require("storage:write")
    path = _tenant_path(path)
    if not _is_path_safe(path):
        return f"ERROR: Access denied. Path '{path}' is outside authorized project boundaries."
    try:
        if current_binding():
            with _tenant_parent(path, create=True) as (directory, name):
                descriptor = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory)
                with os.fdopen(descriptor, "w", encoding="utf-8") as f:
                    f.write(content)
        else:
            resolved_parent = Path(path).resolve().parent
            os.makedirs(resolved_parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        return f"SUCCESS: File written to '{path}' ({len(content)} bytes)."
    except Exception as e:
        return f"ERROR: Failed to write '{path}': {str(e)}"


async def fs_list_dir(path: str = ".") -> str:
    """List directory contents with file types and sizes."""
    path = _tenant_path(path)
    if not _is_path_safe(path):
        return f"ERROR: Access denied. Path '{path}' is outside authorized project boundaries."
    if not os.path.exists(path):
        return f"ERROR: Directory '{path}' not found."
    if not os.path.isdir(path):
        return f"ERROR: Path '{path}' is not a directory."
    try:
        entries = []
        from mas.tenancy import current_binding
        if current_binding():
            import stat
            with _tenant_parent(path) as (parent, name):
                directory = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                try:
                    for item in sorted(os.listdir(directory)):
                        info = os.stat(item, dir_fd=directory, follow_symlinks=False)
                        if stat.S_ISLNK(info.st_mode):
                            continue
                        kind = "DIR" if stat.S_ISDIR(info.st_mode) else f"FILE ({info.st_size}B)"
                        entries.append(f"{kind.ljust(15)} {item}")
                    return "\n".join(entries) if entries else "[Empty directory]"
                finally:
                    os.close(directory)
        for item in sorted(os.listdir(path)):
            full_path = os.path.join(path, item)
            if not _is_path_safe(full_path):
                continue
            is_dir = os.path.isdir(full_path)
            size = os.path.getsize(full_path) if not is_dir else 0
            kind = "DIR" if is_dir else f"FILE ({size}B)"
            entries.append(f"{kind.ljust(15)} {item}")
        return "\n".join(entries) if entries else "[Empty directory]"
    except Exception as e:
        return f"ERROR: Failed to list '{path}': {str(e)}"


async def fs_glob(pattern: str) -> str:
    """Search files matching a glob pattern within authorized project boundaries."""
    from mas.tenancy import current_binding
    if current_binding():
        return "ERROR: Recursive glob has not been approved for tenant execution."
    pattern = _tenant_path(pattern)
    # Check base directory if absolute path pattern
    if pattern.startswith("/") and not _is_path_safe(pattern.split("*")[0].rstrip("/")):
        return "ERROR: Access denied. Glob pattern targets path outside authorized boundaries."
    try:
        matches = glob.glob(pattern, recursive=True)
        safe_matches = [m for m in matches if _is_path_safe(m)]
        return "\n".join(safe_matches) if safe_matches else "[No matches found]"
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
