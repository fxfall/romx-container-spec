#!/usr/bin/env python3
"""Small ROMX 1.0 reference implementation.

The implementation mirrors the specification:

1. Copy the original ROM bytes without modification.
2. Append UTF-8 metadata JSON and an optional PNG cover.
3. Append the fixed 128-byte footer containing offsets, sizes, and hashes.
4. On read, parse the footer from EOF, validate bounds and hashes, then expose
   the embedded regions.

This file intentionally uses only the Python standard library. It is an
implementation guide and validation aid, not a production packer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any


MAGIC = b"ROMX"
VERSION = 1
FOOTER_SIZE = 128
FLAG_METADATA = 1 << 0
FLAG_COVER = 1 << 1
FLAG_BODY_SHA256 = 1 << 2
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# magic, version, six uint64 values, rom hash, flags, footer size, body hash
FOOTER = struct.Struct("<4sI6Q32sII32s")
assert FOOTER.size == FOOTER_SIZE


class RomxError(ValueError):
    """Raised for an invalid ROMX container or metadata document."""


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _validate_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RomxError("metadata top level must be a JSON object")
    required = ("schema_version", "label", "platform", "payload_format")
    missing = [key for key in required if key not in value]
    if missing:
        raise RomxError(f"metadata missing required fields: {', '.join(missing)}")
    if value["schema_version"] != "1.0":
        raise RomxError("metadata schema_version must be '1.0'")
    platforms = {"gb", "gbc", "gba", "nes", "snes", "nds", "3ds", "genesis"}
    formats = {"gb", "gbc", "gba", "nes", "fds", "sfc", "smc", "nds", "3ds", "cci", "cia", "md", "gen", "smd", "bin"}
    if value["platform"] not in platforms:
        raise RomxError(f"unsupported platform: {value['platform']!r}")
    if value["payload_format"] not in formats:
        raise RomxError(f"unsupported payload_format: {value['payload_format']!r}")
    if not isinstance(value["label"], str) or not value["label"]:
        raise RomxError("metadata label must be a non-empty string")
    cover = value.get("cover")
    if cover is not None and (not isinstance(cover, dict) or cover.get("mime_type") != "image/png"):
        raise RomxError("metadata cover.mime_type must be 'image/png'")
    return value


def _json_bytes(metadata_path: Path) -> bytes:
    raw = metadata_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RomxError("metadata must not contain a UTF-8 BOM")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RomxError(f"invalid metadata JSON: {exc}") from exc
    _validate_metadata(value)
    # Compact, deterministic UTF-8 JSON. No filesystem path is embedded.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def pack(rom_path: Path, metadata_path: Path, output_path: Path, cover_path: Path | None = None) -> None:
    rom = rom_path.read_bytes()
    if not rom:
        raise RomxError("ROM payload must not be empty")
    metadata = _json_bytes(metadata_path)
    cover = b""
    if cover_path is not None:
        cover = cover_path.read_bytes()
        if not cover.startswith(PNG_SIGNATURE):
            raise RomxError("cover is not a PNG file")

    rom_offset = 0
    metadata_offset = len(rom) if metadata else 0
    cover_offset = metadata_offset + len(metadata) if cover else 0
    body = rom + metadata + cover
    flags = FLAG_BODY_SHA256
    if metadata:
        flags |= FLAG_METADATA
    if cover:
        flags |= FLAG_COVER
    footer = FOOTER.pack(
        MAGIC, VERSION,
        rom_offset, len(rom),
        metadata_offset, len(metadata),
        cover_offset, len(cover),
        sha256(rom), flags, FOOTER_SIZE, sha256(body),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(body + footer)


def _read_footer(path: Path) -> tuple[bytes, dict[str, Any]]:
    data = path.read_bytes()
    if len(data) < FOOTER_SIZE:
        raise RomxError("file is shorter than the 128-byte footer")
    footer = FOOTER.unpack(data[-FOOTER_SIZE:])
    magic, version, rom_offset, rom_size, metadata_offset, metadata_size, cover_offset, cover_size, rom_hash, flags, footer_size, body_hash = footer
    if magic != MAGIC or version != VERSION or footer_size != FOOTER_SIZE:
        raise RomxError("invalid ROMX magic, version, or footer_size")
    if flags & ~ (FLAG_METADATA | FLAG_COVER | FLAG_BODY_SHA256):
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
    if bool(metadata_size) != bool(flags & FLAG_METADATA) or bool(cover_size) != bool(flags & FLAG_COVER):
        raise RomxError("footer flags do not match region sizes")
    if sha256(data[rom_offset:rom_offset + rom_size]) != rom_hash:
        raise RomxError("ROM SHA-256 mismatch")
    if flags & FLAG_BODY_SHA256 and sha256(data[:body_end]) != body_hash:
        raise RomxError("body SHA-256 mismatch")
    info = {"rom_offset": rom_offset, "rom_size": rom_size, "metadata_offset": metadata_offset, "metadata_size": metadata_size, "cover_offset": cover_offset, "cover_size": cover_size, "flags": flags, "rom_sha256": rom_hash.hex(), "body_sha256": body_hash.hex()}
    return data, info


def inspect(path: Path) -> dict[str, Any]:
    data, info = _read_footer(path)
    if info["metadata_size"]:
        start = info["metadata_offset"]
        end = start + info["metadata_size"]
        metadata = json.loads(data[start:end].decode("utf-8"))
        _validate_metadata(metadata)
        info["metadata"] = metadata
    info["has_cover"] = bool(info["cover_size"])
    return info


def extract(path: Path, output_dir: Path) -> None:
    data, info = _read_footer(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    rom = data[info["rom_offset"]:info["rom_offset"] + info["rom_size"]]
    payload_format = "rom"
    if info["metadata_size"]:
        start = info["metadata_offset"]
        end = start + info["metadata_size"]
        metadata = json.loads(data[start:end].decode("utf-8"))
        _validate_metadata(metadata)
        payload_format = metadata["payload_format"]
        (output_dir / "metadata.json").write_bytes(data[start:end])
    (output_dir / f"payload.{payload_format}").write_bytes(rom)
    if info["cover_size"]:
        start = info["cover_offset"]
        end = start + info["cover_size"]
        cover = data[start:end]
        if not cover.startswith(PNG_SIGNATURE):
            raise RomxError("embedded cover is not PNG")
        (output_dir / "cover.png").write_bytes(cover)


def main() -> int:
    parser = argparse.ArgumentParser(description="ROMX 1.0 reference packer, inspector, verifier, and extractor")
    sub = parser.add_subparsers(dest="command", required=True)
    pack_parser = sub.add_parser("pack", help="create a ROMX file")
    pack_parser.add_argument("rom", type=Path)
    pack_parser.add_argument("metadata", type=Path)
    pack_parser.add_argument("-o", "--output", required=True, type=Path)
    pack_parser.add_argument("--cover", type=Path)
    for name in ("inspect", "verify"):
        command = sub.add_parser(name, help=f"{name} a ROMX file")
        command.add_argument("romx", type=Path)
    extract_parser = sub.add_parser("extract", help="extract embedded regions")
    extract_parser.add_argument("romx", type=Path)
    extract_parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "pack":
            pack(args.rom, args.metadata, args.output, args.cover)
        elif args.command == "inspect":
            print(json.dumps(inspect(args.romx), ensure_ascii=False, indent=2))
        elif args.command == "verify":
            _read_footer(args.romx)
            print(f"valid ROMX: {args.romx}")
        else:
            extract(args.romx, args.output)
    except (OSError, RomxError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
