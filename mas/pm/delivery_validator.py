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
import selectors
import stat
import struct
import subprocess
import time
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
DECOMPRESS_CHUNK_SIZE = 64 * 1024  # 64 KiB
DECOMPRESS_OVERFLOW_SENTINEL = 1  # 1 byte sentinel for producer-side exact boundary detection


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
    intent_id: str = Field(min_length=1, max_length=128)
    attempt_id: str = Field(min_length=1, max_length=128)
    fencing_token: int = Field(ge=1)
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


def _check_manifest_dict_size(data: dict[str, Any]) -> None:
    if len(data) > 64:
        raise DeliveryValidatorError("Manifest dictionary contains excessive keys")
    try:
        encoded = json.dumps(data)
    except Exception as exc:
        raise DeliveryValidatorError(f"Manifest dictionary not JSON serializable: {exc}") from exc
    if len(encoded.encode("utf-8")) > MAX_MANIFEST_JSON_SIZE:
        raise DeliveryValidatorError(f"Manifest data exceeds {MAX_MANIFEST_JSON_SIZE} byte limit")


def validate_manifest_input(manifest_input: Any) -> DeliveryManifest:
    """Strictly revalidate manifest input across all routes with equivalent size bounds.

    Prevents preconstructed model bypasses (e.g. via model_construct or model_copy).
    """
    if isinstance(manifest_input, (str, bytes)):
        return parse_manifest_json(manifest_input)
    elif isinstance(manifest_input, DeliveryManifest):
        # Force strict serialization and revalidation to catch model_construct / model_copy mutations
        raw = manifest_input.model_dump()
        _check_manifest_dict_size(raw)
        try:
            return DeliveryManifest.model_validate(raw, strict=True)
        except Exception as exc:
            raise DeliveryValidatorError(f"Manifest revalidation failed: {exc}") from exc
    elif isinstance(manifest_input, dict):
        _check_manifest_dict_size(manifest_input)
        try:
            return DeliveryManifest.model_validate(manifest_input, strict=True)
        except Exception as exc:
            raise DeliveryValidatorError(f"Manifest schema validation failed: {exc}") from exc
    else:
        raise DeliveryValidatorError(f"Unsupported manifest input type: {type(manifest_input).__name__}")


def read_file_bounded(path: Path | str, max_bytes: int) -> bytes:
    """Read a regular file safely via nonblocking, no-follow descriptor with size bounds."""
    p = Path(path)
    flags = os.O_RDONLY | os.O_NONBLOCK
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


def _has_zip64_extra(extra_data: bytes) -> bool:
    """Return True if ZIP64 extended information extra field (tag 0x0001) is present."""
    offset = 0
    length = len(extra_data)
    while offset + 4 <= length:
        header_id, data_size = struct.unpack_from("<HH", extra_data, offset)
        if header_id == 0x0001:
            return True
        if data_size < 0 or offset + 4 + data_size > length:
            break
        offset += 4 + data_size
    return False


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

    # Locate central directory offset
    eocd_idx = raw_bytes.rfind(b"PK\x05\x06")
    if eocd_idx == -1:
        raise DeliveryValidatorError("End of central directory record not found in archive")
    if eocd_idx + 22 > len(raw_bytes):
        raise DeliveryValidatorError("Truncated end of central directory record")

    # Check for structural ZIP64 locator immediately preceding EOCD (20 bytes: PK\x06\x07)
    if eocd_idx >= 20 and raw_bytes[eocd_idx-20 : eocd_idx-16] == b"PK\x06\x07":
        raise DeliveryValidatorError("ZIP64 format is not supported: ZIP64 locator detected")

    _, _, _, _, _, cd_size, cd_offset, comment_len = struct.unpack("<4sHHHHIIH", raw_bytes[eocd_idx:eocd_idx+22])
    if cd_size == 0xFFFFFFFF or cd_offset == 0xFFFFFFFF:
        raise DeliveryValidatorError("ZIP64 format is not supported: 64-bit central directory")
    if eocd_idx + 22 + comment_len != len(raw_bytes):
        raise DeliveryValidatorError("Trailing unmapped bytes after zip archive comment")

    # Check for structural ZIP64 records between central directory end and EOCD
    cd_end = cd_offset + cd_size
    if cd_end > eocd_idx:
        raise DeliveryValidatorError("Archive layout corruption: central directory extends beyond EOCD start")
    if cd_end < eocd_idx:
        gap = raw_bytes[cd_end:eocd_idx]
        if b"PK\x06\x06" in gap or b"PK\x06\x07" in gap:
            raise DeliveryValidatorError("ZIP64 format is not supported: ZIP64 structural record between CD and EOCD")

    try:
        zf = zipfile.ZipFile(io.BytesIO(raw_bytes), "r")
    except Exception as exc:
        raise DeliveryValidatorError(f"Invalid zip archive: {exc}") from exc

    with zf:
        infolist = zf.infolist()
        if len(infolist) > MAX_MEMBER_COUNT:
            raise DeliveryValidatorError(f"Member count {len(infolist)} exceeds maximum of {MAX_MEMBER_COUNT}")

        members: dict[str, ValidatedArtifactMember] = {}
        seen_canonical: set[str] = set()
        total_uncompressed = 0

        # Sort entries by physical local header offset to verify archive continuity
        sorted_infos = sorted(infolist, key=lambda x: x.header_offset)
        expected_next_offset = 0

        for idx, info in enumerate(sorted_infos):
            # Inspect original member name for NUL or truncation
            orig_name = getattr(info, "orig_filename", info.filename)
            if "\x00" in orig_name:
                raise DeliveryValidatorError(f"NUL character in archive member name: {orig_name!r}")
            if "\x00" in info.filename:
                raise DeliveryValidatorError(f"NUL character in archive member name: {info.filename!r}")
            if orig_name != info.filename:
                raise DeliveryValidatorError(f"Member name truncated or modified by zipinfo: orig={orig_name!r}, norm={info.filename!r}")

            # Reject ZIP64 member version, size, or extra fields
            if info.extract_version >= 45 or info.create_version >= 45:
                raise DeliveryValidatorError(f"ZIP64 format is not supported: version >= 45 for {info.filename}")
            if info.compress_size == 0xFFFFFFFF or info.file_size == 0xFFFFFFFF or info.header_offset == 0xFFFFFFFF:
                raise DeliveryValidatorError(f"ZIP64 format is not supported: 64-bit size or offset for {info.filename}")
            if _has_zip64_extra(info.extra):
                raise DeliveryValidatorError(f"ZIP64 format is not supported: extra field in central directory for {info.filename}")

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

            if loc_csz == 0xFFFFFFFF or loc_usz == 0xFFFFFFFF:
                raise DeliveryValidatorError(f"ZIP64 format is not supported: 64-bit local size for {info.filename}")

            raw_fn = raw_bytes[header_offset+30 : header_offset+30+fn_len]
            if b"\x00" in raw_fn:
                raise DeliveryValidatorError(f"NUL byte in local header filename: {raw_fn!r}")

            raw_extra = raw_bytes[header_offset+30+fn_len : header_offset+30+fn_len+ex_len]
            if _has_zip64_extra(raw_extra):
                raise DeliveryValidatorError(f"ZIP64 format is not supported: extra field in local header for {info.filename}")

            if meth != info.compress_type:
                raise DeliveryValidatorError(f"Compression method mismatch between local and central headers for {info.filename}")

            # If streaming data descriptor bit (bit 3) is NOT set, local sizes must match central directory
            if (flag & 0x8) == 0:
                if loc_csz != info.compress_size:
                    raise DeliveryValidatorError(f"Compressed size mismatch between local and central headers for {info.filename}")
                if loc_usz != info.file_size:
                    raise DeliveryValidatorError(f"Uncompressed size mismatch between local and central headers for {info.filename}")
                if loc_crc != info.CRC:
                    raise DeliveryValidatorError(f"CRC mismatch between local and central headers for {info.filename}")
            else:
                # Streaming data descriptor bit set: local fields may be 0, but if non-zero, must match
                if loc_crc != 0 and loc_crc != info.CRC:
                    raise DeliveryValidatorError(f"Local header CRC mismatch with central directory for {info.filename}")
                if loc_csz != 0 and loc_csz != info.compress_size:
                    raise DeliveryValidatorError(f"Local header compressed size mismatch with central directory for {info.filename}")
                if loc_usz != 0 and loc_usz != info.file_size:
                    raise DeliveryValidatorError(f"Local header uncompressed size mismatch with central directory for {info.filename}")

            data_start = header_offset + 30 + fn_len + ex_len
            data_end = data_start + info.compress_size
            if data_end > len(raw_bytes):
                raise DeliveryValidatorError(f"Payload for {info.filename} extends beyond archive boundary")

            # Validate physical member payload and decompress
            member_uncompressed: bytes
            if info.compress_type == zipfile.ZIP_STORED:
                if info.compress_size != info.file_size:
                    raise DeliveryValidatorError(f"STORED member {info.filename} compress_size != file_size")
                if info.file_size > MAX_MEMBER_UNCOMPRESSED_SIZE:
                    raise DeliveryValidatorError(f"STORED member {info.filename} exceeds {MAX_MEMBER_UNCOMPRESSED_SIZE} byte limit")
                if total_uncompressed + info.file_size > MAX_TOTAL_UNCOMPRESSED_SIZE:
                    raise DeliveryValidatorError(f"Archive exceeds {MAX_TOTAL_UNCOMPRESSED_SIZE} total uncompressed limit")
                raw_payload = raw_bytes[data_start:data_end]
                if len(raw_payload) != info.file_size:
                    raise DeliveryValidatorError(f"Physical STORED payload length {len(raw_payload)} != {info.file_size}")
                if (zlib.crc32(raw_payload) & 0xFFFFFFFF) != info.CRC:
                    raise DeliveryValidatorError(f"CRC32 mismatch for STORED member: {info.filename}")
                member_uncompressed = raw_payload
                total_uncompressed += len(member_uncompressed)
            else:
                # ZIP_DEFLATED
                if info.file_size > MAX_MEMBER_UNCOMPRESSED_SIZE:
                    raise DeliveryValidatorError(f"Member {info.filename} declared uncompressed size exceeds {MAX_MEMBER_UNCOMPRESSED_SIZE} byte limit")
                if total_uncompressed + info.file_size > MAX_TOTAL_UNCOMPRESSED_SIZE:
                    raise DeliveryValidatorError(f"Archive exceeds {MAX_TOTAL_UNCOMPRESSED_SIZE} total uncompressed limit")

                comp_payload = raw_bytes[data_start:data_end]
                if len(comp_payload) != info.compress_size:
                    raise DeliveryValidatorError(f"Physical compressed payload length != {info.compress_size}")

                dobj = zlib.decompressobj(-15)
                buf_member = bytearray()
                offset = 0

                while True:
                    if dobj.unconsumed_tail:
                        in_data = dobj.unconsumed_tail
                    elif offset < len(comp_payload):
                        in_data = comp_payload[offset : offset + DECOMPRESS_CHUNK_SIZE]
                        offset += len(in_data)
                    else:
                        break

                    rem_member = MAX_MEMBER_UNCOMPRESSED_SIZE - len(buf_member)
                    rem_total = MAX_TOTAL_UNCOMPRESSED_SIZE - total_uncompressed
                    rem_allowance = min(rem_member, rem_total)

                    if rem_allowance < 0:
                        raise DeliveryValidatorError(f"Member {info.filename} uncompressed size exceeds limit at producer boundary")

                    # Producer-side bounded decompress: allow at most rem_allowance + sentinel
                    budget = min(DECOMPRESS_CHUNK_SIZE, rem_allowance + DECOMPRESS_OVERFLOW_SENTINEL)
                    decomp = dobj.decompress(in_data, budget)

                    if len(decomp) > rem_allowance:
                        raise DeliveryValidatorError(
                            f"Member {info.filename} uncompressed size exceeds limit at producer boundary: "
                            f"produced {len(decomp)} bytes with allowance {rem_allowance}"
                        )

                    if decomp:
                        buf_member.extend(decomp)
                        total_uncompressed += len(decomp)

                    if dobj.eof:
                        break

                if dobj.unused_data or (dobj.eof and offset < len(comp_payload)):
                    raise DeliveryValidatorError(f"Trailing unused compressed data in DEFLATE stream for {info.filename}")
                if not dobj.eof:
                    raise DeliveryValidatorError(f"Incomplete DEFLATE stream for {info.filename}")
                if len(buf_member) != info.file_size:
                    raise DeliveryValidatorError(f"Decompressed size {len(buf_member)} != declared {info.file_size} for {info.filename}")
                if (zlib.crc32(buf_member) & 0xFFFFFFFF) != info.CRC:
                    raise DeliveryValidatorError(f"CRC32 mismatch for DEFLATED member: {info.filename}")

                member_uncompressed = bytes(buf_member)

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
                limit_offset = sorted_infos[idx + 1].header_offset if idx + 1 < len(sorted_infos) else cd_offset
                if raw_bytes[expected_next_offset:expected_next_offset+4] == b"PK\x07\x08":
                    descriptor_size = 16
                    if expected_next_offset + descriptor_size > len(raw_bytes):
                        raise DeliveryValidatorError(f"Truncated signed data descriptor for {info.filename}")
                    if expected_next_offset + descriptor_size > limit_offset:
                        raise DeliveryValidatorError(f"Data descriptor extends beyond boundary for {info.filename}")
                    sig, desc_crc, desc_csz, desc_usz = struct.unpack(
                        "<4sIII", raw_bytes[expected_next_offset:expected_next_offset+16]
                    )
                else:
                    descriptor_size = 12
                    if expected_next_offset + descriptor_size > len(raw_bytes):
                        raise DeliveryValidatorError(f"Truncated unsigned data descriptor for {info.filename}")
                    if expected_next_offset + descriptor_size > limit_offset:
                        raise DeliveryValidatorError(f"Data descriptor extends beyond boundary for {info.filename}")
                    desc_crc, desc_csz, desc_usz = struct.unpack(
                        "<III", raw_bytes[expected_next_offset:expected_next_offset+12]
                    )

                if desc_crc != computed_crc:
                    raise DeliveryValidatorError(
                        f"Data descriptor CRC32 mismatch for {info.filename}: descriptor={desc_crc:#x}, computed={computed_crc:#x}"
                    )
                if desc_crc != info.CRC:
                    raise DeliveryValidatorError(
                        f"Data descriptor CRC32 mismatch with central directory for {info.filename}: descriptor={desc_crc:#x}, central={info.CRC:#x}"
                    )
                if desc_csz != info.compress_size:
                    raise DeliveryValidatorError(
                        f"Data descriptor compressed size mismatch for {info.filename}: descriptor={desc_csz}, actual={info.compress_size}"
                    )
                if desc_usz != len(member_uncompressed):
                    raise DeliveryValidatorError(
                        f"Data descriptor uncompressed size mismatch for {info.filename}: descriptor={desc_usz}, actual={len(member_uncompressed)}"
                    )
                if desc_usz != info.file_size:
                    raise DeliveryValidatorError(
                        f"Data descriptor uncompressed size mismatch with central directory for {info.filename}: descriptor={desc_usz}, central={info.file_size}"
                    )

                expected_next_offset += descriptor_size

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


def run_bounded_command(
    cmd: list[str],
    cwd: Path | str,
    max_stdout: int = 1024 * 1024,
    max_stderr: int = 256 * 1024,
    timeout: float = 10.0,
) -> tuple[int, bytes, bytes]:
    """Execute a subprocess command with streaming byte caps and deadline enforcement.

    Terminates and cleans up the child process immediately if stdout or stderr
    exceeds byte limits, avoiding unbounded memory buffering.
    """
    start = time.monotonic()
    deadline = start + timeout
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sel = selectors.DefaultSelector()
    if proc.stdout:
        os.set_blocking(proc.stdout.fileno(), False)
        sel.register(proc.stdout, selectors.EVENT_READ, data="stdout")
    if proc.stderr:
        os.set_blocking(proc.stderr.fileno(), False)
        sel.register(proc.stderr, selectors.EVENT_READ, data="stderr")

    stdout_buf = bytearray()
    stderr_buf = bytearray()
    exceeded_stream: str | None = None
    timed_out = False

    try:
        while sel.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            events = sel.select(timeout=max(0.01, min(remaining, 0.5)))
            for key, _ in events:
                stream_type = key.data
                stream = key.fileobj
                chunk = stream.read(65536)
                if not chunk:
                    sel.unregister(stream)
                    continue
                if stream_type == "stdout":
                    stdout_buf.extend(chunk)
                    if len(stdout_buf) > max_stdout:
                        exceeded_stream = "stdout"
                        break
                else:
                    stderr_buf.extend(chunk)
                    if len(stderr_buf) > max_stderr:
                        exceeded_stream = "stderr"
                        break
            if exceeded_stream:
                break
    finally:
        sel.close()
        if exceeded_stream or timed_out:
            proc.terminate()
            try:
                proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
        else:
            try:
                proc.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()

    if timed_out:
        raise DeliveryValidatorError(f"Command '{cmd[0]}' execution timed out")
    if exceeded_stream == "stdout":
        raise DeliveryValidatorError(f"Git command stdout exceeded {max_stdout} byte limit during collection")
    if exceeded_stream == "stderr":
        raise DeliveryValidatorError(f"Git command stderr exceeded {max_stderr} byte limit during collection")

    return proc.returncode, bytes(stdout_buf), bytes(stderr_buf)


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
        rc, _, _ = run_bounded_command(cmd, cwd=repo, max_stdout=64 * 1024, max_stderr=64 * 1024, timeout=10.0)
        if rc != 0:
            raise DeliveryValidatorError(f"Invalid or missing {name} commit in repository: {sha}")

    # Inspect diff-tree with NUL separation
    diff_cmd = ["git", "-C", str(repo), "diff-tree", "-z", "-r", "-M", "--no-commit-id", base_sha, candidate_sha, "--"]
    rc, raw_output, err = run_bounded_command(diff_cmd, cwd=repo, max_stdout=1024 * 1024, max_stderr=256 * 1024, timeout=10.0)
    if rc != 0:
        raise DeliveryValidatorError(f"Git diff-tree execution failed: {err.decode(errors='replace')}")

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

    # 4. Completed run binding and identity verification
    run = conn.execute(
        """SELECT r.run_id, r.intent_id AS run_intent_id, r.attempt_id AS run_attempt_id,
                  r.status AS run_status, r.exit_code, r.fencing_token AS run_fencing_token,
                  a.attempt_id AS attempt_id, a.issue_id AS attempt_issue_id, a.project_id AS attempt_project_id,
                  a.tenant_id AS attempt_tenant_id, a.candidate_commit_sha, a.status AS attempt_status,
                  i.intent_id AS intent_id, i.issue_id AS intent_issue_id, i.status AS intent_status,
                  i.fencing_token AS intent_fencing_token,
                  d.version AS dispatch_version, d.issue_id AS dispatch_issue_id
           FROM pm_coordinator_runs r
           LEFT JOIN pm_coordinator_attempts a ON a.attempt_id = r.attempt_id
           LEFT JOIN pm_coordinator_intents i ON i.intent_id = r.intent_id
           LEFT JOIN pm_delivery_dispatches d ON d.intent_id = r.intent_id
           WHERE r.run_id = ?""",
        (manifest.run_id,),
    ).fetchone()

    if not run:
        raise DeliveryValidatorError(f"Run '{manifest.run_id}' not found in coordinator database")
    if not run["attempt_id"] or not run["intent_id"] or not run["dispatch_version"]:
        raise DeliveryValidatorError(f"Run '{manifest.run_id}' is not fully bound to attempt, intent, and dispatch")

    # Authority and identity binding checks
    if run["attempt_tenant_id"] != manifest.tenant_id:
        raise DeliveryValidatorError(f"Run tenant mismatch: DB has '{run['attempt_tenant_id']}', manifest has '{manifest.tenant_id}'")
    if run["attempt_issue_id"] != manifest.issue_id or run["intent_issue_id"] != manifest.issue_id or run["dispatch_issue_id"] != manifest.issue_id:
        raise DeliveryValidatorError(f"Run '{manifest.run_id}' is bound to issue '{run['attempt_issue_id']}', not '{manifest.issue_id}'")
    if run["attempt_project_id"] != manifest.project_id:
        raise DeliveryValidatorError(f"Run '{manifest.run_id}' is bound to project '{run['attempt_project_id']}', not '{manifest.project_id}'")

    # Authoritative intent and attempt identity comparison
    if manifest.intent_id != run["run_intent_id"] or manifest.intent_id != run["intent_id"]:
        raise DeliveryValidatorError(f"Intent ID mismatch: manifest declared '{manifest.intent_id}', but run is bound to intent '{run['run_intent_id']}'")
    if manifest.attempt_id != run["run_attempt_id"] or manifest.attempt_id != run["attempt_id"]:
        raise DeliveryValidatorError(f"Attempt ID mismatch: manifest declared '{manifest.attempt_id}', but run is bound to attempt '{run['run_attempt_id']}'")

    if run["dispatch_version"] != task["version"]:
        raise DeliveryValidatorError("Dispatch version does not match task brief version")
    if run["intent_status"] != "COMPLETED":
        raise DeliveryValidatorError(f"Intent status '{run['intent_status']}' is not COMPLETED")
    if run["intent_fencing_token"] != run["run_fencing_token"]:
        raise DeliveryValidatorError("Intent and run fencing tokens do not match")
    if manifest.fencing_token != run["run_fencing_token"]:
        raise DeliveryValidatorError(f"Manifest fencing token {manifest.fencing_token} != DB fencing token {run['run_fencing_token']}")
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
