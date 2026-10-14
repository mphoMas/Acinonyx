"""Offline manifest and artifact validation for completed delivery runs.

Validates versioned manifests, bounded zip archives, Git diff scope, and
coordinator database state before submitting to DeliveryService.
No commands/tests are executed by this validator; no trusted receipts or
acceptance are produced.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import struct
import subprocess
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mas.pm.delivery import DeliveryBrief, DeliveryService

SHA = r"^[0-9a-f]{40}$"
SHA256 = r"^[0-9a-f]{64}$"

MAX_MANIFEST_JSON_SIZE = 1024 * 1024  # 1 MiB
MAX_ARCHIVE_COMPRESSED_SIZE = 12 * 1024 * 1024  # 12 MiB
MAX_MEMBER_COUNT = 64
MAX_MEMBER_UNCOMPRESSED_SIZE = 2 * 1024 * 1024  # 2 MiB
MAX_TOTAL_UNCOMPRESSED_SIZE = 10 * 1024 * 1024  # 10 MiB


class DeliveryValidatorError(ValueError):
    """Validation failure in manifest, archive, git objects or DB binding."""


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, revalidate_instances="always")


class ManifestObservation(StrictModel):
    check_id: str = Field(min_length=1, max_length=80)
    outcome: Literal["PASSED", "FAILED", "SKIPPED", "UNAVAILABLE"]
    evidence_ref: str = Field(min_length=1, max_length=1024)
    digest: str = Field(pattern=SHA256)
    size: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def non_blank(self):
        if not self.check_id.strip() or not self.evidence_ref.strip():
            raise ValueError("Nonblank check_id and evidence_ref required")
        return self


class DeliveryManifest(StrictModel):
    schema_version: Literal["mas-delivery-manifest-v1"] = "mas-delivery-manifest-v1"
    tenant_id: str = Field(min_length=1, max_length=128)
    project_id: str = Field(min_length=1, max_length=128)
    issue_id: str = Field(min_length=1, max_length=128)
    brief_version: int = Field(ge=1)
    policy_version: int = Field(default=1, ge=1)
    revision: int = Field(ge=1)
    run_id: str = Field(min_length=1, max_length=128)
    intent_id: str = Field(default="intent_1", min_length=1, max_length=128)
    attempt_id: str = Field(default="attempt_1", min_length=1, max_length=128)
    fencing_token: int = Field(default=1, ge=1)
    candidate_sha: str = Field(pattern=SHA)
    base_sha: str = Field(pattern=SHA)
    suite_digest: str = Field(pattern=SHA256)
    observations: list[ManifestObservation] = Field(min_length=1, max_length=128)
    closures: dict[str, list[str]] = Field(default_factory=dict, max_length=64)
    limitations: str = Field(default="", max_length=8192)

    @model_validator(mode="after")
    def validate_manifest(self):
        for field_name in ("tenant_id", "project_id", "issue_id", "run_id", "intent_id", "attempt_id"):
            val = getattr(self, field_name)
            if not val.strip():
                raise ValueError(f"Nonblank {field_name} required")
        check_ids = [o.check_id for o in self.observations]
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("Duplicate check_id in observations")
        for finding_id, paths in self.closures.items():
            if not finding_id.strip():
                raise ValueError("Nonblank finding_id required in closures")
            if not paths or len(paths) > 64:
                raise ValueError("Nonempty bounded closure paths required")
            for p in paths:
                if not p.strip() or p.startswith("/") or "\\" in p or ".." in p.split("/"):
                    raise ValueError("Bounded relative closure path required")
        return self


def parse_manifest_json(content: str | bytes) -> DeliveryManifest:
    """Parse manifest JSON with duplicate key detection, nonfinite rejection and size bounds."""
    if isinstance(content, bytes):
        if len(content) > MAX_MANIFEST_JSON_SIZE:
            raise DeliveryValidatorError(f"Manifest JSON exceeds {MAX_MANIFEST_JSON_SIZE} byte limit")
        text = content.decode("utf-8")
    else:
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_MANIFEST_JSON_SIZE:
            raise DeliveryValidatorError(f"Manifest JSON exceeds {MAX_MANIFEST_JSON_SIZE} byte limit")
        text = content

    def check_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for k, v in pairs:
            if k in result:
                raise DeliveryValidatorError(f"Duplicate JSON key: {k}")
            result[k] = v
        return result

    def reject_constant(c: str) -> None:
        raise DeliveryValidatorError(f"Nonfinite JSON constant forbidden: {c}")

    try:
        raw = json.loads(text, object_pairs_hook=check_duplicates, parse_constant=reject_constant)
    except DeliveryValidatorError:
        raise
    except Exception as exc:
        raise DeliveryValidatorError(f"Malformed manifest JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise DeliveryValidatorError("Manifest root must be a JSON object")

    try:
        return DeliveryManifest.model_validate(raw, strict=True)
    except Exception as exc:
        raise DeliveryValidatorError(f"Manifest schema validation failed: {exc}") from exc


def validate_manifest_input(manifest_input: Any) -> DeliveryManifest:
    """Strictly revalidate manifest input across all routes.

    Prevents preconstructed model bypasses (e.g. via model_construct or model_copy).
    """
    if isinstance(manifest_input, (str, bytes)):
        return parse_manifest_json(manifest_input)
    elif isinstance(manifest_input, DeliveryManifest):
        # Force strict serialization and revalidation to catch model_construct / model_copy mutations
        raw = manifest_input.model_dump()
        try:
            return DeliveryManifest.model_validate(raw, strict=True)
        except Exception as exc:
            raise DeliveryValidatorError(f"Manifest revalidation failed: {exc}") from exc
    elif isinstance(manifest_input, dict):
        try:
            return DeliveryManifest.model_validate(manifest_input, strict=True)
        except Exception as exc:
            raise DeliveryValidatorError(f"Manifest schema validation failed: {exc}") from exc
    else:
        raise DeliveryValidatorError(f"Unsupported manifest input type: {type(manifest_input).__name__}")


def read_file_bounded(path: Path | str, max_bytes: int) -> bytes:
    """Read a regular file safely via file descriptor with size bounds."""
    p = Path(path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        fd = os.open(str(p), flags)
    except Exception as exc:
        raise DeliveryValidatorError(f"Cannot open file {p}: {exc}") from exc

    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise DeliveryValidatorError(f"Expected regular file, got mode {oct(st.st_mode)}: {p}")
        if st.st_size > max_bytes:
            raise DeliveryValidatorError(f"File {p} size {st.st_size} exceeds {max_bytes} byte limit")
        data = bytearray()
        while True:
            chunk = os.read(fd, 64 * 1024)
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > max_bytes:
                raise DeliveryValidatorError(f"File {p} exceeds {max_bytes} byte limit during read")
        return bytes(data)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class ValidatedArtifactMember:
    name: str
    size: int
    crc32: int
    sha256: str
    data: bytes


def _validate_safe_member_path(name: str) -> str:
    if not name or "\x00" in name or "\\" in name:
        raise DeliveryValidatorError(f"Unsafe member path: {name!r}")
    if any(ord(c) < 32 or ord(c) == 127 for c in name):
        raise DeliveryValidatorError(f"Control characters forbidden in member path: {name!r}")
    if name.startswith("/"):
        raise DeliveryValidatorError(f"Absolute path forbidden in archive: {name!r}")
    parts = name.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise DeliveryValidatorError(f"Invalid path segments in archive member: {name!r}")
    return name


def validate_artifact_archive(
    archive_input: bytes | Path | str,
    observations: list[ManifestObservation] | None = None,
) -> dict[str, ValidatedArtifactMember]:
    """Validate bounded zip archive with streamed byte caps, path safety, and layout integrity.

    If observations are provided, every observation's artifact reference must exist
    and match digest and size. Absent artifacts fail validation immediately.
    """
    if isinstance(archive_input, (str, Path)):
        raw_bytes = read_file_bounded(archive_input, MAX_ARCHIVE_COMPRESSED_SIZE)
    elif isinstance(archive_input, bytes):
        if len(archive_input) > MAX_ARCHIVE_COMPRESSED_SIZE:
            raise DeliveryValidatorError(f"Archive exceeds maximum compressed size of {MAX_ARCHIVE_COMPRESSED_SIZE} bytes")
        raw_bytes = archive_input
    else:
        raise DeliveryValidatorError("Archive input must be bytes, Path or str")

    if not raw_bytes:
        # Empty archive payload
        if observations:
            # Cannot satisfy observations with an empty archive
            raise DeliveryValidatorError("Archive is empty but observations were declared")
        return {}

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes), "r")
    except Exception as exc:
        raise DeliveryValidatorError(f"Invalid zip archive: {exc}") from exc

    with zf:
        infolist = zf.infolist()
        if len(infolist) > MAX_MEMBER_COUNT:
            raise DeliveryValidatorError(f"Member count {len(infolist)} exceeds maximum of {MAX_MEMBER_COUNT}")

        # Locate central directory offset
        eocd_idx = raw_bytes.rfind(b"PK\x05\x06")
        if eocd_idx == -1:
            raise DeliveryValidatorError("End of central directory record not found in archive")
        if eocd_idx + 22 > len(raw_bytes):
            raise DeliveryValidatorError("Truncated end of central directory record")

        _, _, _, _, _, cd_size, cd_offset, comment_len = struct.unpack("<4sHHHHIIH", raw_bytes[eocd_idx:eocd_idx+22])
        if eocd_idx + 22 + comment_len != len(raw_bytes):
            raise DeliveryValidatorError("Trailing unmapped bytes after zip archive comment")

        members: dict[str, ValidatedArtifactMember] = {}
        seen_canonical: set[str] = set()
        total_uncompressed = 0

        # Sort entries by physical local header offset to verify archive continuity
        sorted_infos = sorted(infolist, key=lambda x: x.header_offset)
        expected_next_offset = 0

        for info in sorted_infos:
            # Inspect original member name for NUL or truncation
            orig_name = getattr(info, "orig_filename", info.filename)
            if "\x00" in orig_name:
                raise DeliveryValidatorError(f"NUL character in archive member name: {orig_name!r}")
            if "\x00" in info.filename:
                raise DeliveryValidatorError(f"NUL character in archive member name: {info.filename!r}")
            if orig_name != info.filename:
                raise DeliveryValidatorError(f"Member name truncated or modified by zipinfo: orig={orig_name!r}, norm={info.filename!r}")

            # Check for encryption flag (bit 0)
            if info.flag_bits & 0x1:
                raise DeliveryValidatorError(f"Encrypted zip member forbidden: {info.filename}")

            # Check compression method (only 0: STORED, 8: DEFLATED)
            if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise DeliveryValidatorError(f"Unsupported zip compression method: {info.compress_type} in {info.filename}")

            # Reject directory entries or non-regular files
            if info.is_dir() or info.filename.endswith("/"):
                raise DeliveryValidatorError(f"Directory entries forbidden in artifact archive: {info.filename}")

            # Check unix mode from external_attr (symlinks: 0o120000)
            unix_mode = (info.external_attr >> 16) & 0o170000
            if unix_mode == 0o120000:
                raise DeliveryValidatorError(f"Symlinks forbidden in artifact archive: {info.filename}")
            if unix_mode != 0 and unix_mode != 0o100000:
                raise DeliveryValidatorError(f"Non-regular file in archive: {info.filename}")

            clean_path = _validate_safe_member_path(info.filename)
            canon = clean_path.lower()
            if canon in seen_canonical:
                raise DeliveryValidatorError(f"Duplicate or colliding canonical member name: {info.filename}")
            seen_canonical.add(canon)

            # Reconcile local header with central directory header
            header_offset = info.header_offset
            if header_offset != expected_next_offset:
                raise DeliveryValidatorError(
                    f"Archive continuity gap: expected local header at {expected_next_offset}, found at {header_offset}"
                )

            if header_offset + 30 > len(raw_bytes):
                raise DeliveryValidatorError(f"Truncated local header for member: {info.filename}")

            local_sig, _, flag, meth, _, _, loc_crc, loc_csz, loc_usz, fn_len, ex_len = struct.unpack(
                "<4sHHHHHIIIHH", raw_bytes[header_offset:header_offset+30]
            )
            if local_sig != b"PK\x03\x04":
                raise DeliveryValidatorError(f"Corrupt local header signature for member: {info.filename}")

            raw_fn = raw_bytes[header_offset+30 : header_offset+30+fn_len]
            if b"\x00" in raw_fn:
                raise DeliveryValidatorError(f"NUL byte in local header filename: {raw_fn!r}")

            # If streaming data descriptor bit (bit 3) is NOT set, local sizes must match central directory
            if (flag & 0x8) == 0:
                if meth != info.compress_type:
                    raise DeliveryValidatorError(f"Compression method mismatch between local and central headers for {info.filename}")
                if loc_csz != info.compress_size:
                    raise DeliveryValidatorError(f"Compressed size mismatch between local and central headers for {info.filename}")
                if loc_usz != info.file_size:
                    raise DeliveryValidatorError(f"Uncompressed size mismatch between local and central headers for {info.filename}")
                if loc_crc != info.CRC:
                    raise DeliveryValidatorError(f"CRC mismatch between local and central headers for {info.filename}")

            data_start = header_offset + 30 + fn_len + ex_len
            data_end = data_start + info.compress_size
            if data_end > len(raw_bytes):
                raise DeliveryValidatorError(f"Payload for {info.filename} extends beyond archive boundary")

            # Validate physical member payload and decompress
            member_uncompressed = bytearray()
            if info.compress_type == zipfile.ZIP_STORED:
                if info.compress_size != info.file_size:
                    raise DeliveryValidatorError(f"STORED member {info.filename} compress_size != file_size")
                if info.file_size > MAX_MEMBER_UNCOMPRESSED_SIZE:
                    raise DeliveryValidatorError(f"STORED member {info.filename} exceeds {MAX_MEMBER_UNCOMPRESSED_SIZE} byte limit")
                raw_payload = raw_bytes[data_start:data_end]
                if len(raw_payload) != info.file_size:
                    raise DeliveryValidatorError(f"Physical STORED payload length {len(raw_payload)} != {info.file_size}")
                if (zlib.crc32(raw_payload) & 0xFFFFFFFF) != info.CRC:
                    raise DeliveryValidatorError(f"CRC32 mismatch for STORED member: {info.filename}")
                member_uncompressed = raw_payload
                if total_uncompressed + len(member_uncompressed) > MAX_TOTAL_UNCOMPRESSED_SIZE:
                    raise DeliveryValidatorError(f"Archive exceeds {MAX_TOTAL_UNCOMPRESSED_SIZE} total uncompressed limit")
                total_uncompressed += len(member_uncompressed)
            else:
                # ZIP_DEFLATED
                comp_payload = raw_bytes[data_start:data_end]
                if len(comp_payload) != info.compress_size:
                    raise DeliveryValidatorError(f"Physical compressed payload length != {info.compress_size}")

                dobj = zlib.decompressobj(-15)
                chunk_size = 64 * 1024
                offset = 0
                while offset < len(comp_payload):
                    chunk = comp_payload[offset:offset+chunk_size]
                    offset += len(chunk)
                    decomp = dobj.decompress(chunk)
                    member_uncompressed.extend(decomp)
                    if len(member_uncompressed) > MAX_MEMBER_UNCOMPRESSED_SIZE:
                        raise DeliveryValidatorError(f"Member {info.filename} uncompressed size exceeds {MAX_MEMBER_UNCOMPRESSED_SIZE} bytes")
                    if total_uncompressed + len(decomp) > MAX_TOTAL_UNCOMPRESSED_SIZE:
                        raise DeliveryValidatorError(f"Archive exceeds {MAX_TOTAL_UNCOMPRESSED_SIZE} total uncompressed limit")
                    total_uncompressed += len(decomp)

                tail = dobj.flush()
                if tail:
                    member_uncompressed.extend(tail)
                    if len(member_uncompressed) > MAX_MEMBER_UNCOMPRESSED_SIZE:
                        raise DeliveryValidatorError(f"Member {info.filename} exceeds {MAX_MEMBER_UNCOMPRESSED_SIZE} byte limit")
                    total_uncompressed += len(tail)

                if dobj.unused_data:
                    raise DeliveryValidatorError(f"Trailing unused compressed data in DEFLATE stream for {info.filename}")
                if not dobj.eof:
                    raise DeliveryValidatorError(f"Incomplete DEFLATE stream for {info.filename}")
                if len(member_uncompressed) != info.file_size:
                    raise DeliveryValidatorError(f"Decompressed size {len(member_uncompressed)} != declared {info.file_size} for {info.filename}")
                if (zlib.crc32(member_uncompressed) & 0xFFFFFFFF) != info.CRC:
                    raise DeliveryValidatorError(f"CRC32 mismatch for DEFLATED member: {info.filename}")

            computed_crc = zlib.crc32(member_uncompressed) & 0xFFFFFFFF
            digest = hashlib.sha256(member_uncompressed).hexdigest()

            members[clean_path] = ValidatedArtifactMember(
                name=clean_path,
                size=len(member_uncompressed),
                crc32=computed_crc,
                sha256=digest,
                data=bytes(member_uncompressed),
            )

            # Advance expected_next_offset past data (and data descriptor if bit 3 set)
            expected_next_offset = data_end
            if (flag & 0x8) != 0:
                if raw_bytes[expected_next_offset:expected_next_offset+4] == b"PK\x07\x08":
                    expected_next_offset += 16
                else:
                    expected_next_offset += 12

        # Verify that central directory starts immediately after the last member
        if sorted_infos and expected_next_offset != cd_offset:
            raise DeliveryValidatorError(
                f"Archive continuity gap: central directory expected at {expected_next_offset}, found at {cd_offset}"
            )

        # Validate observations against extracted members
        if observations:
            for obs in observations:
                if obs.evidence_ref not in members:
                    raise DeliveryValidatorError(
                        f"Observation '{obs.check_id}' references absent artifact: '{obs.evidence_ref}'"
                    )
                member = members[obs.evidence_ref]
                if obs.digest != member.sha256:
                    raise DeliveryValidatorError(
                        f"Observation '{obs.check_id}' digest mismatch for '{obs.evidence_ref}': declared {obs.digest}, got {member.sha256}"
                    )
                if obs.size is not None and obs.size != member.size:
                    raise DeliveryValidatorError(
                        f"Observation '{obs.check_id}' size mismatch for '{obs.evidence_ref}': declared {obs.size}, got {member.size}"
                    )

        return members


def is_path_in_scope(file_path: str, scope: list[str]) -> bool:
    """Check if relative file path falls within any bounded relative path prefix in scope."""
    for s in scope:
        clean = s.rstrip("/")
        if file_path == clean or file_path.startswith(clean + "/"):
            return True
    return False


def validate_git_candidate(repo_path: Path | str, base_sha: str, candidate_sha: str, allowed_scope: list[str]) -> list[str]:
    """Validate Git commit objects and diff scope using NUL-safe parsing.

    Checks additions, deletions, renames, and modifications against allowed_scope.
    Rejects symlinks (120000), submodules (160000), and mode changes.
    Returns list of modified relative paths.
    """
    repo = Path(repo_path).resolve(strict=True)

    # Validate that base_sha and candidate_sha resolve to commits
    for name, sha in (("base", base_sha), ("candidate", candidate_sha)):
        cmd = ["git", "-C", str(repo), "rev-parse", "--verify", f"{sha}^{{commit}}"]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10.0)
        except subprocess.TimeoutExpired:
            raise DeliveryValidatorError(f"Git rev-parse timed out verifying {name} commit: {sha}")
        if proc.returncode != 0:
            raise DeliveryValidatorError(f"Invalid or missing {name} commit in repository: {sha}")

    # Inspect diff-tree with NUL separation
    diff_cmd = ["git", "-C", str(repo), "diff-tree", "-z", "-r", "-M", "--no-commit-id", base_sha, candidate_sha, "--"]
    try:
        proc = subprocess.run(diff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10.0)
    except subprocess.TimeoutExpired:
        raise DeliveryValidatorError("Git diff-tree execution timed out")

    if proc.returncode != 0:
        raise DeliveryValidatorError(f"Git diff-tree execution failed: {proc.stderr.decode(errors='replace')}")

    raw_output = proc.stdout
    if len(raw_output) > 1024 * 1024:
        raise DeliveryValidatorError("Git diff output exceeds 1 MiB limit")
    if not raw_output:
        return []

    tokens = raw_output.split(b"\x00")
    idx = 0
    modified_paths: list[str] = []

    while idx < len(tokens):
        meta = tokens[idx].decode("utf-8", errors="replace").strip()
        if not meta:
            idx += 1
            continue

        parts = meta.split()
        if len(parts) < 5 or not parts[0].startswith(":"):
            raise DeliveryValidatorError(f"Unexpected git diff-tree output token: {meta!r}")

        src_mode = parts[0][1:]
        dst_mode = parts[1]
        status = parts[4]

        # Check for forbidden modes (symlinks: 120000, submodules: 160000)
        for mode in (src_mode, dst_mode):
            if mode == "120000":
                raise DeliveryValidatorError("Symlinks forbidden in candidate changes")
            if mode == "160000":
                raise DeliveryValidatorError("Git submodules forbidden in candidate changes")

        # Reject mode changes on existing files
        if src_mode != "000000" and dst_mode != "000000" and src_mode != dst_mode:
            raise DeliveryValidatorError(f"File mode changes forbidden: {src_mode} -> {dst_mode}")

        idx += 1
        if idx >= len(tokens):
            break
        path1 = tokens[idx].decode("utf-8", errors="replace")

        if status.startswith("R") or status.startswith("C"):
            idx += 1
            if idx >= len(tokens):
                raise DeliveryValidatorError("Truncated rename record in diff-tree output")
            path2 = tokens[idx].decode("utf-8", errors="replace")
            # Both paths must be within declared scope
            if not is_path_in_scope(path1, allowed_scope) or not is_path_in_scope(path2, allowed_scope):
                raise DeliveryValidatorError(f"Rename across scope forbidden: {path1} -> {path2}")
            modified_paths.extend([path1, path2])
        else:
            if not is_path_in_scope(path1, allowed_scope):
                raise DeliveryValidatorError(f"Modified file outside declared scope: {path1}")
            modified_paths.append(path1)

        idx += 1

    return sorted(set(modified_paths))


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    status: Literal["VALIDATED_CLAIMS", "VALIDATION_FAILED"]
    reasons: list[str]
    issue_id: str
    run_id: str
    candidate_sha: str
    revision: int
    project_id: str
    tenant_id: str
    submission_payload: dict[str, Any] | None


def validate_db_binding(
    conn: Any,
    manifest: DeliveryManifest,
    expected_revision: int | None = None,
) -> tuple[dict[str, Any], DeliveryBrief]:
    """Validate task, brief, issue, dispatches, and completed run binding in coordinator database."""
    if hasattr(conn, "_get_connection"):
        conn = conn._get_connection()
    # 1. Project enrollment
    project = conn.execute("SELECT tenant_id FROM pm_delivery_projects WHERE project_id=?", (manifest.project_id,)).fetchone()
    if not project or project["tenant_id"] != manifest.tenant_id:
        raise DeliveryValidatorError("Project not enrolled in delivery gates or tenant mismatch")

    # 2. Task lookup
    task = conn.execute(
        "SELECT * FROM pm_delivery_tasks WHERE issue_id=? AND project_id=? AND tenant_id=?",
        (manifest.issue_id, manifest.project_id, manifest.tenant_id),
    ).fetchone()
    if not task:
        raise DeliveryValidatorError("Delivery task record not found")

    if task["phase"] not in ("AWAITING_SUBMISSION", "READINESS_RETURNED"):
        raise DeliveryValidatorError(f"Task phase '{task['phase']}' is not eligible for submission")

    if task["version"] != manifest.brief_version:
        raise DeliveryValidatorError(f"Brief version mismatch: DB has {task['version']}, manifest has {manifest.brief_version}")

    if task["revision"] != manifest.revision:
        raise DeliveryValidatorError(f"Task revision mismatch: DB has {task['revision']}, manifest has {manifest.revision}")

    if expected_revision is not None and task["revision"] != expected_revision:
        raise DeliveryValidatorError(f"Expected revision {expected_revision} != task revision {task['revision']}")

    brief = DeliveryBrief.model_validate(json.loads(task["brief"]), strict=True)
    if brief.base_sha != manifest.base_sha:
        raise DeliveryValidatorError(f"Base commit SHA mismatch: brief has {brief.base_sha}, manifest has {manifest.base_sha}")
    if brief.suite_digest != manifest.suite_digest:
        raise DeliveryValidatorError(f"Suite digest mismatch: brief has {brief.suite_digest}, manifest has {manifest.suite_digest}")

    brief_check_ids = {c.id for c in brief.checks}
    for obs in manifest.observations:
        if obs.check_id not in brief_check_ids:
            raise DeliveryValidatorError(f"Unknown check_id in observation: {obs.check_id}")

    # 3. Issue checks
    issue = conn.execute(
        "SELECT policy_version, has_pending_reconciliation, path_whitelist FROM pm_issues WHERE id=? AND project_id=?",
        (manifest.issue_id, manifest.project_id),
    ).fetchone()
    if not issue:
        raise DeliveryValidatorError("Issue record not found")
    if issue["policy_version"] != brief.policy_version:
        raise DeliveryValidatorError("Issue policy_version does not match brief policy_version")
    if manifest.policy_version != brief.policy_version:
        raise DeliveryValidatorError("Manifest policy_version does not match brief policy_version")
    if issue["has_pending_reconciliation"]:
        raise DeliveryValidatorError("Issue has pending reconciliation")
    if set(json.loads(issue["path_whitelist"])) != set(brief.scope):
        raise DeliveryValidatorError("Issue path_whitelist does not match brief scope")

    # 4. Completed run binding
    run = conn.execute(
        """SELECT a.candidate_commit_sha, a.status AS attempt_status, r.status AS run_status,
                  r.exit_code, d.version AS dispatch_version, i.status AS intent_status,
                  i.fencing_token, r.fencing_token AS run_fence
           FROM pm_coordinator_runs r
           JOIN pm_coordinator_attempts a ON a.attempt_id=r.attempt_id
           JOIN pm_delivery_dispatches d ON d.intent_id=r.intent_id
           JOIN pm_coordinator_intents i ON i.intent_id=r.intent_id
           WHERE r.run_id=? AND a.issue_id=? AND a.tenant_id=?""",
        (manifest.run_id, manifest.issue_id, manifest.tenant_id),
    ).fetchone()

    if not run:
        raise DeliveryValidatorError("Run is not bound to task attempt, dispatch, and intent")
    if run["dispatch_version"] != task["version"]:
        raise DeliveryValidatorError("Dispatch version does not match task brief version")
    if run["intent_status"] != "COMPLETED":
        raise DeliveryValidatorError(f"Intent status '{run['intent_status']}' is not COMPLETED")
    if run["fencing_token"] != run["run_fence"]:
        raise DeliveryValidatorError("Intent and run fencing tokens do not match")
    if manifest.fencing_token != run["fencing_token"]:
        raise DeliveryValidatorError(f"Manifest fencing token {manifest.fencing_token} != DB fencing token {run['fencing_token']}")
    if run["attempt_status"] != "SUCCEEDED":
        raise DeliveryValidatorError(f"Attempt status '{run['attempt_status']}' is not SUCCEEDED")
    if run["run_status"] != "EXITED" or run["exit_code"] != 0:
        raise DeliveryValidatorError(f"Run is not exited with code 0: status={run['run_status']}, exit_code={run['exit_code']}")
    if run["candidate_commit_sha"] != manifest.candidate_sha:
        raise DeliveryValidatorError(
            f"Run candidate commit SHA mismatch: run has {run['candidate_commit_sha']}, manifest has {manifest.candidate_sha}"
        )

    return dict(task), brief


def validate_delivery_manifest(
    manifest_input: Any,
    archive_input: bytes | Path | str,
    repo_path: Path | str,
    conn: Any,
) -> ValidationResult:
    """Validate manifest, artifact archive, git tree and database binding without modifying database."""
    reasons: list[str] = []

    try:
        manifest = validate_manifest_input(manifest_input)
    except Exception as exc:
        return ValidationResult(
            valid=False,
            status="VALIDATION_FAILED",
            reasons=[str(exc)],
            issue_id="",
            run_id="",
            candidate_sha="",
            revision=0,
            project_id="",
            tenant_id="",
            submission_payload=None,
        )

    # 1. DB binding check
    brief: DeliveryBrief | None = None
    try:
        _, brief = validate_db_binding(conn, manifest)
    except Exception as exc:
        reasons.append(str(exc))

    # 2. Archive validation (verifying archive structure AND observation references)
    try:
        validate_artifact_archive(archive_input, observations=manifest.observations)
    except Exception as exc:
        reasons.append(str(exc))

    # 3. Git tree diff validation
    if brief:
        try:
            validate_git_candidate(Path(repo_path), manifest.base_sha, manifest.candidate_sha, brief.scope)
        except Exception as exc:
            reasons.append(str(exc))

    if reasons:
        return ValidationResult(
            valid=False,
            status="VALIDATION_FAILED",
            reasons=reasons,
            issue_id=manifest.issue_id,
            run_id=manifest.run_id,
            candidate_sha=manifest.candidate_sha,
            revision=manifest.revision,
            project_id=manifest.project_id,
            tenant_id=manifest.tenant_id,
            submission_payload=None,
        )

    submission_dict = {
        "run_id": manifest.run_id,
        "candidate_sha": manifest.candidate_sha,
        "observations": [
            {
                "check_id": obs.check_id,
                "outcome": obs.outcome,
                "evidence_ref": obs.evidence_ref,
                "digest": obs.digest,
            }
            for obs in manifest.observations
        ],
        "closures": manifest.closures,
        "limitations": manifest.limitations,
    }

    return ValidationResult(
        valid=True,
        status="VALIDATED_CLAIMS",
        reasons=[],
        issue_id=manifest.issue_id,
        run_id=manifest.run_id,
        candidate_sha=manifest.candidate_sha,
        revision=manifest.revision,
        project_id=manifest.project_id,
        tenant_id=manifest.tenant_id,
        submission_payload=submission_dict,
    )


def validate_and_submit(
    service: DeliveryService,
    manifest_input: Any,
    archive_input: bytes | Path | str,
    repo_path: Path | str,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    """Atomic validate-and-submit operation.

    Revalidates the manifest input, archive bytes and observation links,
    Git candidate diff, and fresh DB binding under active caller tenant session.
    Only if all checks pass, calls DeliveryService.submit().
    Zero DB mutation on validation failure.
    """
    manifest = validate_manifest_input(manifest_input)

    # 1. Archive validation
    validate_artifact_archive(archive_input, observations=manifest.observations)

    conn = service.db._get_connection()
    task, brief = validate_db_binding(conn, manifest, expected_revision=expected_revision)

    # 3. Git diff validation
    validate_git_candidate(Path(repo_path), manifest.base_sha, manifest.candidate_sha, brief.scope)

    # 4. Construct submission payload from validated manifest
    submission_payload = {
        "run_id": manifest.run_id,
        "candidate_sha": manifest.candidate_sha,
        "observations": [
            {
                "check_id": obs.check_id,
                "outcome": obs.outcome,
                "evidence_ref": obs.evidence_ref,
                "digest": obs.digest,
            }
            for obs in manifest.observations
        ],
        "closures": manifest.closures,
        "limitations": manifest.limitations,
    }

    rev = expected_revision if expected_revision is not None else manifest.revision
    return service.submit(manifest.issue_id, rev, submission_payload)


def publish_submission(service: DeliveryService, *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Published submission interface.

    Prohibits passing shallow ValidationResult instances.
    Accepts (service, manifest_input, archive_input, repo_path, expected_revision=None).
    """
    if len(args) == 1 and isinstance(args[0], ValidationResult):
        raise DeliveryValidatorError(
            "Passing shallow ValidationResult to publish_submission is prohibited. "
            "Pass original manifest_input, archive_input, and repo_path to ensure authoritative validation."
        )
    return validate_and_submit(service, *args, **kwargs)
