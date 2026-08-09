#!/usr/bin/env python3
"""Small ROMX 0.1.0 reference implementation.

The implementation mirrors the specification:

1. Copy the original ROM bytes without modification.
2. Append UTF-8 metadata JSON and an optional PNG cover.
3. Append the fixed 128-byte footer containing offsets, sizes, and the optional body SHA-256.
4. On read, parse the footer from EOF, validate bounds and hashes, then expose
   the embedded regions.

This file uses the Python standard library plus Pillow for optional cover
conversion. PNG covers are byte-preserved by default; Pillow is only needed
for non-PNG covers or an explicit cover resolution. It is an implementation
guide and validation aid, not a production packer.
"""

from __future__ import annotations

import argparse
from io import BytesIO
import hashlib
import json
import re
import struct
import sys
import zlib
from pathlib import Path
from typing import Any


MAGIC = b"ROMX"
# ROMX 0.1.0 uses wire version code 1 in the fixed footer.
WIRE_VERSION = 1
FOOTER_SIZE = 128
FLAG_METADATA = 1 << 0
FLAG_COVER = 1 << 1
FLAG_BODY_SHA256 = 1 << 2
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COVER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
MAX_COVER_BYTES = 32 * 1024 * 1024
MAX_COVER_DIMENSION = 8192
ZERO_SHA256 = b"\0" * 32

PLATFORMS = {"gb", "gbc", "gba", "nes", "snes", "nds", "3ds", "genesis"}
PAYLOAD_FORMATS = {
    "gb", "gbc", "gba", "nes", "fds", "sfc", "smc", "nds", "3ds",
    "cci", "cia", "md", "gen", "smd", "bin",
}
METADATA_FIELDS = {
    "schema_version", "name", "platform", "payload_format", "serial",
    "developer", "publisher", "origin", "franchise", "release_date",
    "genre", "region", "language", "users", "coop", "rumble", "analog",
    "enhancement_hw", "category", "media", "description", "crc32",
    "origin_crc32", "dump_status", "cover",
}
DUMP_STATUSES = {"unknown", "good", "bad", "overdump", "hack", "translation", "homebrew"}

# magic, version, six uint64 values, reserved bytes, flags, footer size, body hash
FOOTER = struct.Struct("<4sI6Q32sII32s")
assert FOOTER.size == FOOTER_SIZE


class RomxError(ValueError):
    """Raised for an invalid ROMX container or metadata document."""


class _JsonConstantError(ValueError):
    """Internal marker for Python JSON extensions rejected by RFC 8259."""


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def crc32(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xffffffff:08x}"


def normalize_crc32(value: str) -> str:
    """Validate and canonicalize an explicit database CRC32 key."""
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{8}", value) is None:
        raise RomxError("CRC32 override must be exactly 8 hexadecimal characters")
    return value.lower()


def normalize_cover_bytes(data: bytes, target: tuple[int, int] | None = None) -> bytes:
    """Convert supported cover formats to PNG, optionally at exact size.

    PNG bytes are returned unchanged when no target size is requested. Other
    formats require Pillow and use the first frame for animated GIFs.
    """
    if not data:
        raise RomxError("cover image must not be empty")
    if target is not None:
        width, height = target
        if width <= 0 or height <= 0 or width > MAX_COVER_DIMENSION or height > MAX_COVER_DIMENSION:
            raise RomxError("cover resolution must be between 1 and 8192 pixels")
    elif data.startswith(PNG_SIGNATURE):
        _validate_png_bytes(data)
        return data
    try:
        from PIL import Image
    except ImportError as exc:
        raise RomxError("image conversion requires Pillow; install requirements.txt") from exc
    try:
        with Image.open(BytesIO(data)) as image:
            image.seek(0)
            if target is not None:
                image = image.resize(target, Image.Resampling.LANCZOS)
            image = image.convert("RGBA")
            output = BytesIO()
            image.save(output, format="PNG", optimize=True)
            normalized = output.getvalue()
            _validate_png_bytes(normalized)
            return normalized
    except Exception as exc:
        raise RomxError(f"unsupported or invalid cover image: {exc}") from exc


def normalize_cover_path(path: Path, target: tuple[int, int] | None = None) -> bytes:
    return normalize_cover_bytes(path.read_bytes(), target)


def parse_cover_size(value: str | None) -> tuple[int, int] | None:
    if value is None:
        return None
    separator = "x" if "x" in value else "X" if "X" in value else None
    if separator is None:
        raise RomxError("cover size must use WIDTHxHEIGHT")
    try:
        width, height = (int(part.strip()) for part in value.split(separator, 1))
    except ValueError as exc:
        raise RomxError("cover size must use WIDTHxHEIGHT") from exc
    if width <= 0 or height <= 0 or width > MAX_COVER_DIMENSION or height > MAX_COVER_DIMENSION:
        raise RomxError("cover size must be between 1x1 and 8192x8192")
    return width, height


def _validate_png_bytes(data: bytes) -> tuple[int, int]:
    """Validate the ROMX PNG profile and return its IHDR dimensions.

    This deliberately validates structure only; decoding pixels is outside the
    container format.  The rules mirror libromx: IHDR is first and unique,
    IDAT is required (and consecutive), IEND is empty and final, critical
    chunks are known, and PNG color/depth combinations are legal.
    """
    if len(data) > MAX_COVER_BYTES:
        raise RomxError(f"cover exceeds the {MAX_COVER_BYTES // (1024 * 1024)} MiB limit")
    if not data.startswith(PNG_SIGNATURE):
        raise RomxError("cover is not a PNG file")
    offset = len(PNG_SIGNATURE)
    width = height = None
    color_type = None
    saw_idat = False
    ended_idat = False
    saw_iend = False
    saw_plte = False
    first = True
    while offset < len(data):
        if len(data) - offset < 12:
            raise RomxError("PNG chunk header or CRC is truncated")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        crc_end = chunk_end + 4
        if length > 0x7fffffff or chunk_end < chunk_start or crc_end > len(data):
            raise RomxError("PNG chunk exceeds the cover bounds")
        chunk_type = data[offset + 4:offset + 8]
        if any(not (65 <= byte <= 90 or 97 <= byte <= 122) for byte in chunk_type):
            raise RomxError("PNG chunk type is invalid")
        if chunk_type[2] & 0x20:
            raise RomxError("PNG chunk type has a reserved bit set")
        chunk_data = data[chunk_start:chunk_end]
        expected_crc = struct.unpack(">I", data[chunk_end:crc_end])[0]
        actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xffffffff
        if actual_crc != expected_crc:
            raise RomxError(f"PNG chunk CRC mismatch: {chunk_type.decode('ascii', 'replace')}")
        if first and (chunk_type != b"IHDR" or length != 13):
            raise RomxError("PNG IHDR must be the first chunk")
        if not first and (chunk_type[0] & 0x20) == 0 and chunk_type not in {b"PLTE", b"IDAT", b"IEND"}:
            raise RomxError("PNG contains an unknown critical chunk")
        if chunk_type == b"IHDR":
            if not first or width is not None or length != 13:
                raise RomxError("PNG has an invalid or duplicate IHDR chunk")
            width, height = struct.unpack(">II", chunk_data[:8])
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            if not 1 <= width <= MAX_COVER_DIMENSION or not 1 <= height <= MAX_COVER_DIMENSION:
                raise RomxError("PNG dimensions exceed the ROMX cover limit")
            if chunk_data[10] != 0 or chunk_data[11] != 0 or chunk_data[12] > 1:
                raise RomxError("PNG IHDR compression, filter, or interlace is invalid")
            valid_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if color_type not in valid_depths or bit_depth not in valid_depths[color_type]:
                raise RomxError("PNG color type and bit depth combination is invalid")
        elif chunk_type == b"PLTE":
            if (saw_plte or saw_idat or color_type in {0, 4} or length == 0 or
                    length % 3 != 0 or length > 768):
                raise RomxError("PNG PLTE chunk is invalid")
            saw_plte = True
        elif chunk_type == b"IDAT":
            if ended_idat:
                raise RomxError("PNG IDAT chunks are not consecutive")
            saw_idat = True
        elif chunk_type == b"IEND":
            if length != 0 or not saw_idat or (color_type == 3 and not saw_plte):
                raise RomxError("PNG IEND or required chunks are invalid")
            saw_iend = True
            if crc_end != len(data):
                raise RomxError("PNG has bytes after IEND")
        elif saw_idat:
            ended_idat = True
        offset = crc_end
        first = False
        if saw_iend:
            break
    if width is None or height is None or not saw_iend or offset != len(data):
        raise RomxError("PNG is missing IEND or has trailing bytes")
    return width, height


def classify_gb_payload(rom: bytes, payload_format: str | None) -> str:
    """Apply the Game Boy CGB flag policy from the ROMX platform rules."""
    if len(rom) <= 0x143:
        if payload_format in {"gb", "gbc"}:
            return payload_format
        raise RomxError("GB ROM is too small to classify without payload_format gb or gbc")
    flag = rom[0x143]
    if flag == 0xC0:
        return "gbc"
    if flag == 0x80:
        if payload_format in {"gb", "gbc"}:
            return payload_format
        raise RomxError("dual GB/GBC ROM requires payload_format gb or gbc")
    if payload_format in {"gb", "gbc"}:
        return payload_format
    raise RomxError("GB ROM requires payload_format gb or gbc")


def _duplicate_key_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RomxError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    """Reject Python's non-RFC-8259 NaN/Infinity extensions."""
    raise _JsonConstantError(f"non-standard JSON constant: {value}")


def _validate_json_unicode(value: Any) -> None:
    """Reject escaped lone UTF-16 surrogates accepted by Python's decoder."""
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise RomxError("JSON contains an unpaired UTF-16 surrogate")
    elif isinstance(value, list):
        for item in value:
            _validate_json_unicode(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _validate_json_unicode(key)
            _validate_json_unicode(item)


def _parse_json(raw: bytes, description: str) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RomxError(f"{description} must not contain a UTF-8 BOM")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_duplicate_key_object,
            parse_constant=_reject_json_constant,
        )
        _validate_json_unicode(value)
        return value
    except (UnicodeDecodeError, json.JSONDecodeError, _JsonConstantError) as exc:
        raise RomxError(f"invalid {description}: {exc}") from exc


def _validate_text(value: Any, field: str, maximum: int, *, required: bool = False) -> None:
    if not isinstance(value, str) or (required and not value) or len(value) > maximum:
        qualifier = "non-empty " if required else ""
        raise RomxError(f"metadata {field} must be a {qualifier}string of at most {maximum} characters")


def _validate_string_list(value: Any, field: str, maximum_items: int, maximum_length: int) -> None:
    if not isinstance(value, list) or len(value) > maximum_items:
        raise RomxError(f"metadata {field} must be an array of at most {maximum_items} strings")
    if any(not isinstance(item, str) or len(item) > maximum_length for item in value):
        raise RomxError(f"metadata {field} must contain unique strings of at most {maximum_length} characters")
    if len(set(value)) != len(value):
        raise RomxError(f"metadata {field} must contain unique strings of at most {maximum_length} characters")


def _validate_metadata(value: Any, *, require_crc: bool = True) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RomxError("metadata top level must be a JSON object")
    unknown = sorted(set(value) - METADATA_FIELDS)
    if unknown:
        raise RomxError(f"metadata contains unsupported fields: {', '.join(unknown)}")
    required = ["schema_version", "name", "platform", "payload_format"]
    if require_crc:
        required.append("crc32")
    missing = [key for key in required if key not in value]
    if missing:
        raise RomxError(f"metadata missing required fields: {', '.join(missing)}")
    if value["schema_version"] != "0.1.0":
        raise RomxError("metadata schema_version must be '0.1.0'")
    _validate_text(value.get("name"), "name", 512, required=True)
    if value.get("platform") not in PLATFORMS:
        raise RomxError(f"unsupported platform: {value.get('platform')!r}")
    if value.get("payload_format") not in PAYLOAD_FORMATS:
        raise RomxError(f"unsupported payload_format: {value.get('payload_format')!r}")
    if "crc32" in value:
        normalize_crc32(value["crc32"])
    if "origin_crc32" in value:
        normalize_crc32(value["origin_crc32"])
    for field, maximum in (
        ("serial", 128), ("developer", 256), ("publisher", 256),
        ("origin", 128), ("franchise", 256), ("language", 256),
        ("enhancement_hw", 256), ("category", 128), ("media", 64),
        ("description", 32768),
    ):
        if field in value:
            _validate_text(value[field], field, maximum)
    if "release_date" in value:
        _validate_text(value["release_date"], "release_date", 10)
        if re.fullmatch(r"[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?", value["release_date"]) is None:
            raise RomxError("metadata release_date must use YYYY, YYYY-MM, or YYYY-MM-DD")
    if "genre" in value:
        _validate_string_list(value["genre"], "genre", 32, 64)
    if "region" in value:
        _validate_string_list(value["region"], "region", 32, 32)
    if "users" in value and (isinstance(value["users"], bool) or not isinstance(value["users"], int) or not 1 <= value["users"] <= 255):
        raise RomxError("metadata users must be an integer from 1 to 255")
    for field in ("coop", "rumble", "analog"):
        if field in value and not isinstance(value[field], bool):
            raise RomxError(f"metadata {field} must be boolean")
    if "dump_status" in value and value["dump_status"] not in DUMP_STATUSES:
        raise RomxError(f"unsupported dump_status: {value['dump_status']!r}")
    if "cover" in value:
        cover = value["cover"]
        if not isinstance(cover, dict):
            raise RomxError("metadata cover must be an object")
        unknown_cover = sorted(set(cover) - {"mime_type", "width", "height"})
        if unknown_cover:
            raise RomxError(f"metadata cover contains unsupported fields: {', '.join(unknown_cover)}")
        if "mime_type" in cover:
            if cover["mime_type"] != "image/png":
                raise RomxError("metadata cover.mime_type must be 'image/png'")
        for dimension in ("width", "height"):
            if dimension in cover and (
                isinstance(cover[dimension], bool) or not isinstance(cover[dimension], int) or
                not 1 <= cover[dimension] <= MAX_COVER_DIMENSION
            ):
                raise RomxError(f"metadata cover.{dimension} must be an integer from 1 to {MAX_COVER_DIMENSION}")
    return value


def _json_bytes(
    metadata_path: Path,
    rom_bytes: bytes,
    crc32_override: str | None = None,
    cover_bytes: bytes | None = None,
) -> bytes:
    raw = metadata_path.read_bytes()
    value = _parse_json(raw, "metadata JSON")
    _validate_metadata(value, require_crc=False)
    value["crc32"] = normalize_crc32(crc32_override) if crc32_override is not None else crc32(rom_bytes)
    if "origin_crc32" in value:
        value["origin_crc32"] = crc32(rom_bytes)
    if cover_bytes is not None:
        cover = {"mime_type": "image/png"}
        dimensions = _png_dimensions(cover_bytes)
        if dimensions:
            cover.update(width=dimensions[0], height=dimensions[1])
        value["cover"] = cover
    _validate_metadata(value)
    # Compact, deterministic UTF-8 JSON. No filesystem path is embedded.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def pack(
    rom_path: Path,
    metadata_path: Path | None,
    output_path: Path,
    cover_path: Path | None = None,
    crc32_override: str | None = None,
    cover_size: tuple[int, int] | None = None,
    body_sha256_enabled: bool = False,
) -> None:
    rom = rom_path.read_bytes()
    if not rom:
        raise RomxError("ROM payload must not be empty")
    cover = b""
    if cover_path is not None:
        cover = normalize_cover_path(cover_path, cover_size)
        if not cover.startswith(PNG_SIGNATURE):
            raise RomxError("cover is not a PNG file")
    metadata = (
        _json_bytes(metadata_path, rom, crc32_override, cover or None)
        if metadata_path is not None else b""
    )

    rom_offset = 0
    metadata_offset = len(rom) if metadata else 0
    cover_offset = metadata_offset + len(metadata) if cover else 0
    body = rom + metadata + cover
    flags = FLAG_BODY_SHA256 if body_sha256_enabled else 0
    if metadata:
        flags |= FLAG_METADATA
    if cover:
        flags |= FLAG_COVER
    footer = FOOTER.pack(
        MAGIC, WIRE_VERSION,
        rom_offset, len(rom),
        metadata_offset, len(metadata),
        cover_offset, len(cover),
        ZERO_SHA256, flags, FOOTER_SIZE, sha256(body) if body_sha256_enabled else ZERO_SHA256,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(body + footer)


def _read_footer(path: Path) -> tuple[bytes, dict[str, Any]]:
    data = path.read_bytes()
    if len(data) < FOOTER_SIZE:
        raise RomxError("file is shorter than the 128-byte footer")
    footer = FOOTER.unpack(data[-FOOTER_SIZE:])
    magic, version, rom_offset, rom_size, metadata_offset, metadata_size, cover_offset, cover_size, _reserved, flags, footer_size, body_hash = footer
    if magic != MAGIC or version != WIRE_VERSION or footer_size != FOOTER_SIZE:
        raise RomxError("invalid ROMX magic, version, or footer_size")
    if flags & ~(FLAG_METADATA | FLAG_COVER | FLAG_BODY_SHA256):
        raise RomxError("reserved footer flags are set")
    body_end = len(data) - FOOTER_SIZE
    regions = [("rom", rom_offset, rom_size), ("metadata", metadata_offset, metadata_size), ("cover", cover_offset, cover_size)]
    nonempty = []
    for name, offset, size in regions:
        if size == 0:
            continue
        if offset > body_end or size > body_end - offset:
            raise RomxError(f"{name} region exceeds the body")
        nonempty.append((name, offset, offset + size))
    if not rom_size:
        raise RomxError("ROM payload must not be empty")
    for index, first in enumerate(nonempty):
        for second in nonempty[index + 1:]:
            if max(first[1], second[1]) < min(first[2], second[2]):
                raise RomxError(f"regions overlap: {first[0]} and {second[0]}")
    cursor = 0
    for name, start, end in sorted(nonempty, key=lambda item: item[1]):
        if start != cursor:
            raise RomxError(f"footer body contains uncovered bytes before {name} region")
        cursor = end
    if cursor != body_end:
        raise RomxError("footer body contains uncovered bytes")
    if bool(metadata_size) != bool(flags & FLAG_METADATA) or bool(cover_size) != bool(flags & FLAG_COVER):
        raise RomxError("footer flags do not match region sizes")
    if not flags & FLAG_BODY_SHA256 and body_hash != ZERO_SHA256:
        raise RomxError("body SHA-256 must be all zero when disabled")
    if metadata_size == 0:
        metadata_offset = 0
    if cover_size == 0:
        cover_offset = 0
    body_sha256_valid = not (flags & FLAG_BODY_SHA256) or sha256(data[:body_end]) == body_hash
    info = {
        "rom_offset": rom_offset, "rom_size": rom_size,
        "metadata_offset": metadata_offset, "metadata_size": metadata_size,
        "cover_offset": cover_offset, "cover_size": cover_size,
        "flags": flags,
        "body_sha256": body_hash.hex(),
        "body_sha256_enabled": bool(flags & FLAG_BODY_SHA256),
        "body_sha256_valid": body_sha256_valid,
    }
    return data, info


def _metadata_from_container(data: bytes, info: dict[str, Any]) -> dict[str, Any]:
    if not info["metadata_size"]:
        raise RomxError("metadata is absent")
    start = info["metadata_offset"]
    end = start + info["metadata_size"]
    metadata = _parse_json(data[start:end], "metadata JSON")
    return _validate_metadata(metadata)


def _cover_from_container(data: bytes, info: dict[str, Any]) -> bytes:
    if not info["cover_size"]:
        raise RomxError("cover is absent")
    start = info["cover_offset"]
    end = start + info["cover_size"]
    cover = data[start:end]
    _validate_png_bytes(cover)
    return cover


def _validate_hashes(info: dict[str, Any]) -> None:
    if not info["body_sha256_valid"]:
        raise RomxError("body SHA-256 mismatch")


def inspect(path: Path) -> dict[str, Any]:
    data, info = _read_footer(path)
    info["body_sha256_status"] = "valid" if info["body_sha256_valid"] else "invalid"
    info["metadata_status"] = "absent"
    if info["metadata_size"]:
        try:
            info["metadata"] = _metadata_from_container(data, info)
            info["metadata_status"] = "valid"
        except RomxError as exc:
            info["metadata_status"] = "invalid"
            info["metadata_error"] = str(exc)
    info["cover_status"] = "absent"
    if info["cover_size"]:
        try:
            _cover_from_container(data, info)
            info["cover_status"] = "valid"
        except RomxError as exc:
            info["cover_status"] = "invalid"
            info["cover_error"] = str(exc)
    return info


def extract(path: Path, output_dir: Path) -> None:
    data, info = _read_footer(path)
    _validate_hashes(info)
    output_dir.mkdir(parents=True, exist_ok=True)
    rom = data[info["rom_offset"]:info["rom_offset"] + info["rom_size"]]
    payload_format = "rom"
    if info["metadata_size"]:
        try:
            metadata = _metadata_from_container(data, info)
        except RomxError:
            metadata = None
        if metadata is not None:
            payload_format = metadata["payload_format"]
            start = info["metadata_offset"]
            end = start + info["metadata_size"]
            (output_dir / "metadata.json").write_bytes(data[start:end])
    (output_dir / f"payload.{payload_format}").write_bytes(rom)
    if info["cover_size"]:
        try:
            cover = _cover_from_container(data, info)
        except RomxError:
            cover = None
        if cover is not None:
            (output_dir / "cover.png").write_bytes(cover)


def _playlist_items(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        document = _parse_json(path.read_bytes(), "LPL JSON")
    except (OSError, RomxError) as exc:
        raise RomxError(f"invalid LPL file {path}: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("items"), list):
        raise RomxError(f"LPL file has no items array: {path}")
    return document, [item for item in document["items"] if isinstance(item, dict)]


def _virtual_path(value: str) -> Path:
    """Convert an LPL slash path to a local relative path."""
    return Path(value.lstrip("/"))


def _platform_for(payload_format: str, playlist_name: str = "") -> str:
    if payload_format in {"gb", "gbc"}:
        return payload_format
    name = playlist_name.lower()
    for marker, platform in (("gbc", "gbc"), ("gba", "gba"), ("3ds", "3ds"), ("nds", "nds"), ("snes", "snes"), ("genesis", "genesis"), ("gb", "gb"), ("nes", "nes")):
        if marker in name:
            return platform
    return {"gb": "gb", "gbc": "gbc", "gba": "gba", "nes": "nes", "fds": "nes", "sfc": "snes", "smc": "snes", "nds": "nds", "3ds": "3ds", "cci": "3ds", "cia": "3ds", "md": "genesis", "gen": "genesis", "smd": "genesis", "bin": "genesis"}.get(payload_format, "gb")


def _png_dimensions(data: bytes) -> tuple[int, int] | None:
    return _validate_png_bytes(data)


def _safe_filename(label: str) -> str:
    return label.replace("/", "_").replace("\\", "_").replace("\x00", "_").strip() or "untitled"


def _find_cover_file(directory: Path, stems: tuple[str, ...]) -> Path | None:
    for stem in stems:
        for extension in COVER_EXTENSIONS:
            candidate = directory / f"{stem}{extension}"
            if candidate.is_file():
                return candidate
    return None


def _resolve_lpl_path(lpl_path: Path, value: str) -> Path:
    """Resolve an LPL path without turning it into metadata."""
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    relative_to_lpl = lpl_path.parent / candidate
    return relative_to_lpl if relative_to_lpl.is_file() else candidate


def _resolve_lpl_rom_path(lpl_path: Path, value: str) -> Path:
    """Resolve real and RetroArch virtual absolute ROM paths."""
    if value.startswith("/roms/"):
        # <content-root>/retroarch/playlists/<name>.lpl -> <content-root>/roms/...
        content_root = lpl_path.parent.parent.parent
        candidate = content_root / _virtual_path(value)
        if candidate.is_file():
            return candidate
    return _resolve_lpl_path(lpl_path, value)


def _lpl_item_identity(value: Any) -> tuple[str, str] | None:
    """Parse RetroArch's ``CRC|crc`` or ``SERIAL|serial`` identity form."""
    if not isinstance(value, str) or not value or value.upper() == "DETECT":
        return None
    token, separator, kind = value.partition("|")
    if not token or not separator:
        return None
    kind = kind.lower()
    if kind == "crc":
        try:
            return "crc32", normalize_crc32(token)
        except RomxError:
            return None
    if kind == "serial":
        return "serial", token
    return None


def _cover_from_lpl(
    lpl_path: Path,
    playlist_name: str,
    item: dict[str, Any],
    rom_path: Path,
    label: str,
    cover_root: Path | None,
    force_cover_dir: Path | None,
    cover_set: str,
) -> Path | None:
    """Resolve a cover from explicit LPL data or the RetroArch tree."""
    if force_cover_dir:
        return _find_cover_file(force_cover_dir, (rom_path.stem, label))

    for key in ("cover_path", "thumbnail_path", "cover", "thumbnail"):
        value = item.get(key)
        if isinstance(value, str) and value:
            candidate = _resolve_lpl_path(lpl_path, value)
            if candidate.is_file():
                return candidate

    if cover_root:
        cover_dir = cover_root / playlist_name / cover_set
    else:
        # A standalone absolute LPL commonly lives in <root>/playlists; infer
        # the sibling RetroArch thumbnails tree without requiring another CLI
        # path argument.
        retroarch_root = lpl_path.parent.parent
        cover_dir = retroarch_root / "thumbnails" / playlist_name / cover_set
    return _find_cover_file(cover_dir, (rom_path.stem, label))


def import_lpl(
    lpl_path: Path,
    output_dir: Path,
    rom_root: Path | None = None,
    cover_root: Path | None = None,
    force_rom_dir: Path | None = None,
    force_cover_dir: Path | None = None,
    cover_set: str = "Named_Snaps",
    skip_missing: bool = False,
    crc32_override: str | None = None,
    cover_size: tuple[int, int] | None = None,
    body_sha256_enabled: bool = False,
) -> int:
    """Import one LPL into sequential ROMX files.

    `rom_root` maps RetroArch virtual paths such as `/roms/02-GBA/1.gba` to
    a local tree. `force_rom_dir` and `force_cover_dir` ignore the directory
    part from the LPL and look up each item by basename, which is useful when
    ROMs or thumbnails have been moved to a flat directory. When no roots are
    supplied, absolute ROM paths in the LPL are used directly and a standard
    `playlists/../thumbnails/<playlist>/<cover_set>` tree is inferred. Useful
    Only database-compatible game information is written to metadata; LPL-only
    fields remain conversion state and paths remain outside metadata.
    """
    document, items = _playlist_items(lpl_path)
    playlist_name = lpl_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    imported = 0
    for index, item in enumerate(items, 1):
        item_path = item.get("path")
        if not isinstance(item_path, str) or not item_path:
            if skip_missing:
                continue
            raise RomxError(f"LPL item {index} has no path")
        virtual = _virtual_path(item_path)
        if force_rom_dir:
            rom_path = force_rom_dir / virtual.name
        elif rom_root:
            rom_path = rom_root / virtual
        else:
            rom_path = _resolve_lpl_rom_path(lpl_path, item_path)
        if not rom_path.is_file():
            if skip_missing:
                continue
            raise RomxError(f"ROM not found for LPL item {index}: {rom_path}")
        payload_format = rom_path.suffix.lower().lstrip(".")
        if payload_format not in {"gb", "gbc", "gba", "nes", "fds", "sfc", "smc", "nds", "3ds", "cci", "cia", "md", "gen", "smd", "bin"}:
            raise RomxError(f"unsupported ROM extension in LPL item {index}: {rom_path.suffix}")
        rom_bytes = rom_path.read_bytes()
        if payload_format in {"gb", "gbc"}:
            payload_format = classify_gb_payload(rom_bytes, payload_format)
        name = item.get("label") or rom_path.stem
        metadata: dict[str, Any] = {"schema_version": "0.1.0", "name": str(name), "platform": _platform_for(payload_format, playlist_name), "payload_format": payload_format}
        identity = _lpl_item_identity(item.get("crc32"))
        if identity and identity[0] == "serial":
            metadata["serial"] = identity[1]
        cover_path = _cover_from_lpl(
            lpl_path,
            playlist_name,
            item,
            rom_path,
            str(name),
            cover_root,
            force_cover_dir,
            cover_set,
        )
        metadata_file = output_dir / f".metadata-{index:06d}.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output_path = output_dir / f"{index:06d}.{payload_format}x"
        try:
            item_crc_override = crc32_override
            if item_crc_override is None and identity and identity[0] == "crc32":
                item_crc_override = identity[1]
            pack(rom_path, metadata_file, output_path, cover_path, item_crc_override, cover_size, body_sha256_enabled)
        finally:
            metadata_file.unlink(missing_ok=True)
        imported += 1
    settings = {
        key: document[key]
        for key in ("version", "default_core_path", "default_core_name", "label_display_mode", "right_thumbnail_mode", "left_thumbnail_mode", "thumbnail_match_mode", "sort_mode")
        if key in document
    }
    (output_dir / "manifest.json").write_text(json.dumps({"source_lpl": str(lpl_path), "playlist": playlist_name, "items": len(items), "imported": imported, "lpl_settings": settings}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return imported


def export_lpl(
    romx_dir: Path,
    output_root: Path,
    playlist_name: str | None = None,
    lpl_path: Path | None = None,
    rom_dir: Path | None = None,
    cover_dir: Path | None = None,
    lpl_rom_prefix: str | None = None,
    cover_set: str = "Named_Snaps",
) -> int:
    """Extract a ROMX folder to ROMs, RetroArch thumbnails, and an LPL."""
    files = sorted(path for path in romx_dir.rglob("*") if path.is_file() and path.suffix.lower().endswith("x"))
    if not files:
        raise RomxError(f"no ROMX files found in {romx_dir}")
    playlist = playlist_name
    if not playlist:
        manifest_path = romx_dir / "manifest.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if isinstance(manifest.get("playlist"), str) and manifest["playlist"]:
                    playlist = manifest["playlist"]
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                pass
    playlist = playlist or romx_dir.name
    actual_rom_dir = rom_dir or (output_root / "roms" / playlist)
    actual_cover_dir = cover_dir or (output_root / "thumbnails" / playlist / cover_set)
    actual_lpl = lpl_path or (output_root / "playlists" / f"{playlist}.lpl")
    actual_rom_dir.mkdir(parents=True, exist_ok=True)
    actual_cover_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, str]] = []
    for index, romx_path in enumerate(files, 1):
        data, info = _read_footer(romx_path)
        _validate_hashes(info)
        rom = data[info["rom_offset"]:info["rom_offset"] + info["rom_size"]]
        metadata: dict[str, Any] = {}
        if info["metadata_size"]:
            try:
                metadata = _metadata_from_container(data, info)
            except RomxError:
                metadata = {}
        payload_format = str(metadata.get("payload_format", "rom"))
        filename = f"{index:06d}.{payload_format}"
        (actual_rom_dir / filename).write_bytes(data[info["rom_offset"]:info["rom_offset"] + info["rom_size"]])
        name = str(metadata.get("name", romx_path.stem))
        if info["cover_size"]:
            cover = _cover_from_container(data, info)
            (actual_cover_dir / f"{_safe_filename(name)}.png").write_bytes(cover)
        prefix = lpl_rom_prefix or f"/roms/{playlist}"
        lpl_item_path = str(Path(prefix) / filename).replace("\\", "/")
        lookup_crc = metadata.get("crc32")
        if not isinstance(lookup_crc, str):
            lookup_crc = crc32(rom)
        else:
            try:
                lookup_crc = normalize_crc32(lookup_crc)
            except RomxError:
                lookup_crc = crc32(rom)
        items.append({"path": lpl_item_path, "label": name, "core_path": "DETECT", "core_name": "DETECT", "crc32": f"{lookup_crc}|crc", "db_name": actual_lpl.name})
    actual_lpl.parent.mkdir(parents=True, exist_ok=True)
    actual_lpl.write_text(json.dumps({"version": "1.5", "default_core_path": "DETECT", "default_core_name": "DETECT", "label_display_mode": 0, "right_thumbnail_mode": 0, "left_thumbnail_mode": 0, "thumbnail_match_mode": 0, "sort_mode": 0, "items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(items)


def _add_body_sha_option(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--body-sha256", dest="body_sha256", action="store_true",
        help="store and validate the optional SHA-256 of all bytes before the footer",
    )
    group.add_argument(
        "--no-body-sha256", dest="body_sha256", action="store_false",
        help="disable the optional body SHA-256 and store zero bytes in its footer field",
    )
    parser.set_defaults(body_sha256=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="ROMX 0.1.0 packer, inspector, verifier, extractor, LPL importer, and LPL exporter")
    sub = parser.add_subparsers(dest="command", required=True)
    pack_parser = sub.add_parser("pack", help="create a ROMX file")
    pack_parser.add_argument("rom", type=Path)
    pack_parser.add_argument("metadata", nargs="?", type=Path, help="optional metadata JSON")
    pack_parser.add_argument("-o", "--output", required=True, type=Path)
    pack_parser.add_argument("--cover", type=Path, help="PNG/JPEG/WebP/GIF/BMP cover")
    pack_parser.add_argument("--crc32", help="override metadata CRC32 lookup key (8 hexadecimal characters)")
    pack_parser.add_argument("--cover-size", help="normalize cover to WIDTHxHEIGHT PNG")
    _add_body_sha_option(pack_parser)
    for name in ("inspect", "verify"):
        command = sub.add_parser(name, help=f"{name} a ROMX file")
        command.add_argument("romx", type=Path)
    extract_parser = sub.add_parser("extract", help="extract embedded regions")
    extract_parser.add_argument("romx", type=Path)
    extract_parser.add_argument("output", type=Path)
    import_parser = sub.add_parser("import-lpl", help="import a RetroArch LPL into sequential ROMX files")
    import_parser.add_argument("lpl", type=Path)
    import_parser.add_argument("-o", "--output", required=True, type=Path, help="directory for sequential ROMX files")
    import_parser.add_argument("--rom-root", type=Path, help="local root for LPL virtual ROM paths")
    import_parser.add_argument("--cover-root", type=Path, help="RetroArch thumbnails root")
    import_parser.add_argument("--rom-dir", dest="force_rom_dir", type=Path, help="force ROM lookup in this flat directory")
    import_parser.add_argument("--cover-dir", dest="force_cover_dir", type=Path, help="force PNG cover lookup in this flat directory")
    import_parser.add_argument("--cover-set", default="Named_Snaps", help="thumbnail set directory (default: Named_Snaps)")
    import_parser.add_argument("--skip-missing", action="store_true", help="skip LPL items whose ROM is missing")
    import_parser.add_argument("--crc32", help="override metadata CRC32 lookup key for every imported ROM")
    import_parser.add_argument("--cover-size", help="normalize imported covers to WIDTHxHEIGHT PNG")
    _add_body_sha_option(import_parser)
    export_parser = sub.add_parser("export-lpl", help="extract a ROMX folder to ROMs, thumbnails, and an LPL")
    export_parser.add_argument("romx_dir", type=Path)
    export_parser.add_argument("-o", "--output-root", type=Path, default=Path("."), help="RetroArch-style output root")
    export_parser.add_argument("--playlist-name", help="playlist name (default: ROMX folder name)")
    export_parser.add_argument("--lpl-path", type=Path, help="exact output LPL path")
    export_parser.add_argument("--rom-dir", type=Path, help="exact extracted ROM directory")
    export_parser.add_argument("--cover-dir", type=Path, help="exact extracted PNG cover directory")
    export_parser.add_argument("--lpl-rom-prefix", help="virtual ROM prefix written into LPL")
    export_parser.add_argument("--cover-set", default="Named_Snaps", help="thumbnail set directory (default: Named_Snaps)")
    args = parser.parse_args()
    try:
        if args.command == "pack":
            pack(args.rom, args.metadata, args.output, args.cover, args.crc32, parse_cover_size(args.cover_size), args.body_sha256)
        elif args.command == "inspect":
            print(json.dumps(inspect(args.romx), ensure_ascii=False, indent=2))
        elif args.command == "verify":
            _, info = _read_footer(args.romx)
            _validate_hashes(info)
            print(f"valid ROMX: {args.romx}")
        elif args.command == "extract":
            extract(args.romx, args.output)
        elif args.command == "import-lpl":
            count = import_lpl(args.lpl, args.output, args.rom_root, args.cover_root, args.force_rom_dir, args.force_cover_dir, args.cover_set, args.skip_missing, args.crc32, parse_cover_size(args.cover_size), args.body_sha256)
            print(f"imported {count} ROMX files into {args.output}")
        else:
            count = export_lpl(args.romx_dir, args.output_root, args.playlist_name, args.lpl_path, args.rom_dir, args.cover_dir, args.lpl_rom_prefix, args.cover_set)
            print(f"exported {count} LPL items from {args.romx_dir}")
    except (OSError, RomxError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
