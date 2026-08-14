#!/usr/bin/env python3
"""Deterministic ROMX 0.2.0 reference writer and structural inspector.

This tool exists to generate independent test vectors for ROMX readers and
writers. It is deliberately not a user-facing conversion application.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import unicodedata
import zlib


FOOTER_SIZE = 128
FOOTER_VERSION = 2
RIDX_HEADER_SIZE = 64
RIDX_ENTRY_SIZE = 512
RIDX_PATH_CAPACITY = 480
RIDX_VERSION = 1
MUTABLE_HEADER_SIZE = 4096
MUTABLE_ENTRY_SIZE = 512
MUTABLE_ENTRY_CAPACITY = 8
MIN_MUTABLE_CAPACITY = 12288
CHUNK_SIZE = 1024 * 1024

ENTRYPOINT = 1 << 0
HAS_CRC32 = 1 << 1

HASH_NONE = 0
HASH_SHA256 = 1

PLATFORMS = {
    "UNSPECIFIED": 0x0000,
    "GAME_BOY": 0x0001,
    "GAME_BOY_COLOR": 0x0002,
    "GAME_BOY_ADVANCE": 0x0003,
    "NES": 0x0004,
    "SNES": 0x0005,
    "NINTENDO_64": 0x0006,
    "NINTENDO_DS": 0x0007,
    "NINTENDO_3DS": 0x0008,
    "MASTER_SYSTEM": 0x0010,
    "GAME_GEAR": 0x0011,
    "MEGA_DRIVE": 0x0012,
    "MEGA_DRIVE_32X": 0x0013,
    "SEGA_CD": 0x0014,
    "SEGA_SATURN": 0x0015,
    "DREAMCAST": 0x0016,
    "PC_ENGINE": 0x0020,
    "PC_ENGINE_CD": 0x0021,
    "PLAYSTATION": 0x0030,
    "PLAYSTATION_2": 0x0031,
    "PSP": 0x0032,
    "GAMECUBE": 0x0040,
    "WII": 0x0041,
    "ARCADE": 0x0050,
    "SCUMMVM": 0x0060,
    "DOS": 0x0061,
    "AMIGA": 0x0062,
}

LAUNCH_FORMATS = {
    "UNSPECIFIED": 0x0000,
    "RAW_SINGLE_FILE": 0x0001,
    "CUE": 0x0002,
    "GDI": 0x0003,
    "M3U": 0x0004,
    "CCD": 0x0005,
    "MDS": 0x0006,
    "TOC": 0x0007,
    "DIRECTORY": 0x0008,
    "ROMSET": 0x0009,
    "SPLIT_FILE_SET": 0x000A,
}

FORMATS = {
    "UNKNOWN": 0x0000,
    "GB": 0x0001, "GBC": 0x0002, "GBA": 0x0003,
    "NES": 0x0004, "UNF": 0x0005, "UNIF": 0x0006,
    "FDS": 0x0007, "SFC": 0x0008, "SMC": 0x0009,
    "NDS": 0x000A, "N3DS": 0x000B, "CCI": 0x000C,
    "CXI": 0x000D, "APP": 0x000E,
    "ISO": 0x0010, "CSO": 0x0011, "ZSO": 0x0012,
    "CHD": 0x0013, "PBP": 0x0014, "CDI": 0x0015,
    "GCM": 0x0016, "WBFS": 0x0017, "RVZ": 0x0018,
    "WIA": 0x0019, "WAD": 0x001A,
    "CUE": 0x0020, "GDI": 0x0021, "M3U": 0x0022,
    "CCD": 0x0023, "MDS": 0x0024, "TOC": 0x0025,
    "BIN": 0x0030, "WAV": 0x0031, "FLAC": 0x0032,
    "IMG": 0x0033, "MDF": 0x0034,
    "SBI": 0x0040, "SUB": 0x0041, "ECM": 0x0042,
    "Z64": 0x0050, "N64": 0x0051, "V64": 0x0052,
    "MD": 0x0060, "GEN": 0x0061, "SMD": 0x0062,
    "X32": 0x0063, "SMS": 0x0064, "GG": 0x0065,
    "PCE": 0x0066, "ELF": 0x0070, "PRX": 0x0071,
    "MSU": 0x0080, "PCM": 0x0081,
    "ROMX_LAUNCH_DESCRIPTOR": 0x0090,
}

EXTENSION_FORMATS = {
    ".gb": "GB", ".gbc": "GBC", ".gba": "GBA",
    ".nes": "NES", ".unf": "UNF", ".unif": "UNIF",
    ".fds": "FDS", ".sfc": "SFC", ".smc": "SMC",
    ".nds": "NDS", ".3ds": "N3DS", ".cci": "CCI",
    ".cxi": "CXI", ".app": "APP", ".iso": "ISO",
    ".cso": "CSO", ".zso": "ZSO", ".chd": "CHD",
    ".pbp": "PBP", ".cdi": "CDI", ".gcm": "GCM",
    ".wbfs": "WBFS", ".rvz": "RVZ", ".wia": "WIA",
    ".wad": "WAD", ".cue": "CUE", ".gdi": "GDI",
    ".m3u": "M3U", ".ccd": "CCD", ".mds": "MDS",
    ".toc": "TOC", ".bin": "BIN", ".wav": "WAV",
    ".flac": "FLAC", ".img": "IMG", ".mdf": "MDF",
    ".sbi": "SBI", ".sub": "SUB", ".ecm": "ECM",
    ".z64": "Z64", ".n64": "N64", ".v64": "V64",
    ".md": "MD", ".gen": "GEN", ".smd": "SMD",
    ".32x": "X32", ".sms": "SMS", ".gg": "GG",
    ".pce": "PCE", ".elf": "ELF", ".prx": "PRX",
    ".msu": "MSU", ".pcm": "PCM",
}


class RomxError(ValueError):
    pass


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


def crc32_file(handle, offset: int, size: int) -> int:
    value = 0
    handle.seek(offset)
    remaining = size
    while remaining:
        block = handle.read(min(CHUNK_SIZE, remaining))
        if not block:
            raise RomxError("unexpected EOF while calculating CRC32")
        value = zlib.crc32(block, value)
        remaining -= len(block)
    return value & 0xFFFFFFFF


def sha256_file(handle, offset: int, size: int) -> bytes:
    digest = hashlib.sha256()
    handle.seek(offset)
    remaining = size
    while remaining:
        block = handle.read(min(CHUNK_SIZE, remaining))
        if not block:
            raise RomxError("unexpected EOF while calculating SHA-256")
        digest.update(block)
        remaining -= len(block)
    return digest.digest()


def parse_registry(value: str, registry: dict[str, int], label: str) -> int:
    key = value.upper()
    if key in registry:
        return registry[key]
    try:
        number = int(value, 0)
    except ValueError as exc:
        raise RomxError(f"unknown {label}: {value}") from exc
    if not 0 <= number <= 0xFFFE:
        raise RomxError(f"{label} is out of range or prohibited: {value}")
    return number


def validate_virtual_path(path: str) -> bytes:
    if not path or unicodedata.normalize("NFC", path) != path:
        raise RomxError(f"virtual path is empty or not Unicode NFC: {path!r}")
    if "\x00" in path or "\\" in path or path.startswith("/") or path.endswith("/"):
        raise RomxError(f"invalid virtual path: {path!r}")
    components = path.split("/")
    if any(component in ("", ".", "..") for component in components):
        raise RomxError(f"invalid virtual path component: {path!r}")
    encoded = path.encode("utf-8", "strict")
    if not 1 <= len(encoded) <= RIDX_PATH_CAPACITY:
        raise RomxError(f"virtual path must encode to 1..{RIDX_PATH_CAPACITY} bytes")
    return encoded


def strict_json(raw: bytes) -> dict:
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RomxError("metadata must not contain a UTF-8 BOM")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise RomxError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(token):
        raise RomxError(f"non-RFC 8259 JSON number: {token}")

    try:
        text = raw.decode("utf-8", "strict")
        value = json.loads(text, object_pairs_hook=unique_object,
                           parse_constant=invalid_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RomxError(f"invalid metadata JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RomxError("metadata top level must be an object")

    def reject_surrogates(item, location="metadata"):
        if isinstance(item, str):
            if any(0xD800 <= ord(character) <= 0xDFFF for character in item):
                raise RomxError(f"unpaired UTF-16 surrogate in {location}")
        elif isinstance(item, list):
            for index, child in enumerate(item):
                reject_surrogates(child, f"{location}[{index}]")
        elif isinstance(item, dict):
            for key, child in item.items():
                reject_surrogates(key, f"{location} key")
                reject_surrogates(child, f"{location}.{key}")

    reject_surrogates(value)
    string_limits = {
        "name": (1, 512), "serial": (0, 128), "developer": (0, 256),
        "publisher": (0, 256), "origin": (0, 128), "franchise": (0, 256),
        "language": (0, 256), "enhancement_hw": (0, 256),
        "category": (0, 128), "media": (0, 64), "description": (0, 32768),
    }
    allowed = {
        "schema_version", *string_limits, "release_date", "genre", "region",
        "users", "coop", "rumble", "analog", "crc32", "origin_crc32",
        "dump_status", "cover",
    }
    unknown = set(value) - allowed
    if unknown:
        raise RomxError(f"unknown metadata properties: {sorted(unknown)}")
    if value.get("schema_version") != "0.2.0":
        raise RomxError('metadata schema_version must be "0.2.0"')
    if "name" not in value:
        raise RomxError("metadata name is required")
    for key, (minimum, maximum) in string_limits.items():
        if key in value and (not isinstance(value[key], str) or
                             not minimum <= len(value[key]) <= maximum):
            raise RomxError(f"metadata {key} violates its string length")
    if "release_date" in value and (not isinstance(value["release_date"], str) or
            re.fullmatch(r"[0-9]{4}(-[0-9]{2}(-[0-9]{2})?)?",
                         value["release_date"]) is None):
        raise RomxError("metadata release_date violates its pattern")
    for key, maximum, item_maximum in (("genre", 32, 64), ("region", 32, 32)):
        if key in value:
            items = value[key]
            if not isinstance(items, list) or len(items) > maximum or \
                    any(not isinstance(item, str) or len(item) > item_maximum
                        for item in items) or len(set(items)) != len(items):
                raise RomxError(f"metadata {key} violates its array schema")
    if "users" in value and (isinstance(value["users"], bool) or
            not isinstance(value["users"], int) or not 1 <= value["users"] <= 255):
        raise RomxError("metadata users must be an integer from 1 to 255")
    for key in ("coop", "rumble", "analog"):
        if key in value and not isinstance(value[key], bool):
            raise RomxError(f"metadata {key} must be boolean")
    for key in ("crc32", "origin_crc32"):
        if key in value and (not isinstance(value[key], str) or
                             re.fullmatch(r"[0-9a-f]{8}", value[key]) is None):
            raise RomxError(f"metadata {key} must be eight lower-case hex digits")
    if "dump_status" in value and value["dump_status"] not in {
            "unknown", "good", "bad", "overdump", "hack", "translation", "homebrew"}:
        raise RomxError("metadata dump_status is not registered")
    if "cover" in value:
        cover = value["cover"]
        if not isinstance(cover, dict) or set(cover) - {"mime_type", "width", "height"}:
            raise RomxError("metadata cover must be a closed object")
        if "mime_type" in cover and cover["mime_type"] != "image/png":
            raise RomxError("metadata cover mime_type must be image/png")
        for key in ("width", "height"):
            if key in cover and (isinstance(cover[key], bool) or
                    not isinstance(cover[key], int) or not 1 <= cover[key] <= 8192):
                raise RomxError(f"metadata cover {key} must be an integer from 1 to 8192")
    return value


def validate_png(raw: bytes) -> tuple[int, int]:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RomxError("cover is not a PNG")
    position = 8
    seen_ihdr = False
    seen_idat = False
    idat_finished = False
    seen_iend = False
    seen_plte = False
    width = height = color_type = bit_depth = 0
    known_critical = {b"IHDR", b"PLTE", b"IDAT", b"IEND"}
    valid_depths = {
        0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8},
        4: {8, 16}, 6: {8, 16},
    }
    chunk_index = 0
    while position < len(raw):
        if len(raw) - position < 12:
            raise RomxError("PNG chunk header is truncated")
        length = struct.unpack_from(">I", raw, position)[0]
        chunk_type = raw[position + 4:position + 8]
        end = position + 12 + length
        if end > len(raw):
            raise RomxError("PNG chunk exceeds cover bounds")
        chunk_data = raw[position + 8:position + 8 + length]
        expected = struct.unpack_from(">I", raw, position + 8 + length)[0]
        if crc32(chunk_type + chunk_data) != expected:
            raise RomxError("PNG chunk CRC32 mismatch")
        if chunk_index == 0 and chunk_type != b"IHDR":
            raise RomxError("IHDR must be the first PNG chunk")
        if chunk_type == b"IHDR":
            if seen_ihdr or length != 13:
                raise RomxError("IHDR must occur once with length 13")
            width, height, bit_depth, color_type, compression, filtering, interlace = \
                struct.unpack(">IIBBBBB", chunk_data)
            if width == 0 or height == 0 or color_type not in valid_depths or \
                    bit_depth not in valid_depths[color_type] or compression != 0 or \
                    filtering != 0 or interlace not in (0, 1):
                raise RomxError("invalid PNG IHDR")
            seen_ihdr = True
        elif chunk_type == b"PLTE":
            if seen_plte or seen_idat or length == 0 or length % 3 or length > 768:
                raise RomxError("invalid PNG PLTE")
            seen_plte = True
        elif chunk_type == b"IDAT":
            if idat_finished:
                raise RomxError("PNG IDAT chunks must be consecutive")
            seen_idat = True
        elif chunk_type == b"IEND":
            if length != 0 or seen_iend:
                raise RomxError("invalid PNG IEND")
            seen_iend = True
            if end != len(raw):
                raise RomxError("PNG has bytes after IEND")
        elif chunk_type[0] & 0x20 == 0 and chunk_type not in known_critical:
            raise RomxError("unknown critical PNG chunk")
        if seen_idat and chunk_type not in (b"IDAT", b"IEND"):
            idat_finished = True
        position = end
        chunk_index += 1
    if not seen_ihdr or not seen_idat or not seen_iend:
        raise RomxError("PNG requires IHDR, IDAT, and IEND")
    if color_type == 3 and not seen_plte:
        raise RomxError("indexed PNG requires PLTE")
    if color_type in (0, 4) and seen_plte:
        raise RomxError("grayscale PNG must not contain PLTE")
    return width, height


def align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def write_zeros(handle, size: int, digest=None) -> None:
    block = bytes(min(CHUNK_SIZE, max(1, size)))
    remaining = size
    while remaining:
        part = block[:min(len(block), remaining)]
        handle.write(part)
        if digest is not None:
            digest.update(part)
        remaining -= len(part)


def copy_source(source: Path, output, digest) -> tuple[int, int]:
    value = 0
    total = 0
    with source.open("rb") as input_file:
        while True:
            block = input_file.read(CHUNK_SIZE)
            if not block:
                break
            output.write(block)
            digest.update(block)
            value = zlib.crc32(block, value)
            total += len(block)
    return total, value & 0xFFFFFFFF


def make_ridx(entries: list[dict], include_crc32: bool) -> bytes:
    index = bytearray(RIDX_HEADER_SIZE + len(entries) * RIDX_ENTRY_SIZE)
    struct.pack_into("<4sHHIII", index, 0, b"RIDX", RIDX_VERSION,
                     RIDX_HEADER_SIZE, len(entries), RIDX_ENTRY_SIZE, 0)
    for position, entry in enumerate(entries):
        base = RIDX_HEADER_SIZE + position * RIDX_ENTRY_SIZE
        flags = ENTRYPOINT if entry["entrypoint"] else 0
        if include_crc32:
            flags |= HAS_CRC32
        path_bytes = entry["path_bytes"]
        struct.pack_into("<IHHQQII", index, base, flags, entry["format_id"],
                         len(path_bytes), entry["offset"], entry["size"],
                         entry["crc32"] if include_crc32 else 0, 0)
        index[base + 0x20:base + 0x20 + len(path_bytes)] = path_bytes
    struct.pack_into("<I", index, 0x14, crc32(index))
    return bytes(index)


def make_empty_mutable(capacity: int) -> bytes:
    if capacity % 4096 or capacity < MIN_MUTABLE_CAPACITY:
        raise RomxError("mutable capacity must be a 4096-byte multiple and at least 12288")
    directory_size = MUTABLE_ENTRY_CAPACITY * MUTABLE_ENTRY_SIZE
    data_offset = MUTABLE_HEADER_SIZE + directory_size
    header = bytearray(MUTABLE_HEADER_SIZE)
    struct.pack_into("<4sHHIIQQQQI", header, 0, b"RMUT", 1,
                     MUTABLE_HEADER_SIZE, MUTABLE_ENTRY_SIZE,
                     MUTABLE_ENTRY_CAPACITY, MUTABLE_HEADER_SIZE,
                     directory_size, data_offset, capacity - data_offset, 0)
    struct.pack_into("<I", header, 0x34, crc32(header))
    return bytes(header)


def build_romx(output_path: Path, entries: list[dict], entrypoint: str,
               platform_id: int, launch_format_id: int, metadata: bytes,
               cover: bytes, mutable_capacity: int, include_entry_crc32: bool,
               include_sha256: bool, payload_alignment: int,
               replace: bool = False) -> dict:
    if not entries:
        raise RomxError("at least one entry is required")
    if payload_alignment < 1 or payload_alignment & (payload_alignment - 1):
        raise RomxError("payload alignment must be a positive power of two")
    if output_path.exists() and not replace:
        raise RomxError(f"output already exists: {output_path}")
    if metadata:
        strict_json(metadata)
    if cover:
        validate_png(cover)

    seen = set()
    normalized_entries = []
    for item in entries:
        virtual_path = item["path"]
        path_bytes = validate_virtual_path(virtual_path)
        folded = virtual_path.casefold()
        if folded in seen:
            raise RomxError(f"case-folding path collision: {virtual_path}")
        seen.add(folded)
        source = Path(item["source"])
        if not source.is_file():
            raise RomxError(f"entry source is not a file: {source}")
        format_id = item.get("format_id")
        if format_id is None:
            format_name = EXTENSION_FORMATS.get(Path(virtual_path).suffix.lower())
            if format_name is None:
                raise RomxError(f"cannot infer format for {virtual_path}")
            format_id = FORMATS[format_name]
        normalized_entries.append({
            "path": virtual_path, "path_bytes": path_bytes, "source": source,
            "format_id": format_id, "entrypoint": virtual_path == entrypoint,
        })
    points = [entry for entry in normalized_entries if entry["entrypoint"]]
    if len(points) != 1:
        raise RomxError("entrypoint must identify exactly one entry")
    if points[0]["format_id"] == 0 or points[0]["source"].stat().st_size == 0:
        raise RomxError("entrypoint must be non-empty and have a non-zero format")
    normalized_entries.sort(key=lambda item: (not item["entrypoint"], item["path"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=output_path.name + ".tmp-",
                                          dir=output_path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        immutable_digest = hashlib.sha256()
        with temporary.open("w+b") as output:
            payload_position = 0
            for index, entry in enumerate(normalized_entries):
                if index:
                    aligned = align_up(payload_position, payload_alignment)
                    write_zeros(output, aligned - payload_position, immutable_digest)
                    payload_position = aligned
                entry["offset"] = payload_position
                size, value = copy_source(entry["source"], output, immutable_digest)
                entry["size"] = size
                entry["crc32"] = value
                payload_position += size
            payload_size = payload_position
            if normalized_entries[0]["offset"] != 0:
                raise AssertionError("entrypoint must begin at offset zero")
            if len(normalized_entries) == 1 and normalized_entries[0]["size"] != payload_size:
                raise AssertionError("single-file payload must contain no padding")

            ridx = make_ridx(normalized_entries, include_entry_crc32)
            output.write(ridx)
            immutable_digest.update(ridx)
            output.write(metadata)
            immutable_digest.update(metadata)
            output.write(cover)
            immutable_digest.update(cover)
            immutable_content_end = output.tell()

            mutable_offset = 0
            if mutable_capacity:
                mutable_offset = align_up(immutable_content_end, 4096)
                write_zeros(output, mutable_offset - immutable_content_end,
                            immutable_digest)
                mutable_header = make_empty_mutable(mutable_capacity)
                output.write(mutable_header)
                write_zeros(output, mutable_capacity - len(mutable_header))
            footer_offset = output.tell()
            immutable_hash = immutable_digest.digest() if include_sha256 else bytes(32)
            footer = bytearray(FOOTER_SIZE)
            struct.pack_into("<4sIQQQQHHI32sI", footer, 0, b"ROMX",
                             FOOTER_VERSION, payload_size, len(metadata), len(cover),
                             mutable_capacity, platform_id, launch_format_id,
                             HASH_SHA256 if include_sha256 else HASH_NONE,
                             immutable_hash, 0)
            struct.pack_into("<I", footer, 0x50, crc32(footer))
            output.write(footer)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return inspect_romx(output_path, verify_entry_crc32=True)


def all_zero(handle, offset: int, size: int) -> bool:
    handle.seek(offset)
    remaining = size
    while remaining:
        block = handle.read(min(CHUNK_SIZE, remaining))
        if not block or any(block):
            return False
        remaining -= len(block)
    return True


def inspect_romx(path: Path, verify_entry_crc32: bool = False) -> dict:
    file_size = path.stat().st_size
    if file_size < FOOTER_SIZE:
        raise RomxError("file is shorter than the ROMX footer")
    with path.open("rb") as handle:
        footer_offset = file_size - FOOTER_SIZE
        handle.seek(footer_offset)
        footer = bytearray(handle.read(FOOTER_SIZE))
        if len(footer) != FOOTER_SIZE or footer[:4] != b"ROMX":
            raise RomxError("invalid footer magic or size")
        version = struct.unpack_from("<I", footer, 0x04)[0]
        if version != FOOTER_VERSION:
            raise RomxError("unsupported footer wire version")
        expected_footer_crc = struct.unpack_from("<I", footer, 0x50)[0]
        struct.pack_into("<I", footer, 0x50, 0)
        if crc32(footer) != expected_footer_crc:
            raise RomxError("footer CRC32 mismatch")
        if any(footer[0x54:]):
            raise RomxError("footer reserved bytes are non-zero")
        payload_size, metadata_size, cover_size, mutable_capacity = \
            struct.unpack_from("<QQQQ", footer, 0x08)
        platform_id, launch_format_id = struct.unpack_from("<HH", footer, 0x28)
        hash_algorithm = struct.unpack_from("<I", footer, 0x2C)[0]
        immutable_sha256 = bytes(footer[0x30:0x50])
        if payload_size == 0 or payload_size + RIDX_HEADER_SIZE > footer_offset:
            raise RomxError("payload size cannot locate a RIDX header")

        handle.seek(payload_size)
        header = bytearray(handle.read(RIDX_HEADER_SIZE))
        if len(header) != RIDX_HEADER_SIZE or header[:4] != b"RIDX":
            raise RomxError("invalid RIDX magic or header size")
        index_version, header_size = struct.unpack_from("<HH", header, 0x04)
        entry_count, entry_size, index_flags, index_crc = \
            struct.unpack_from("<IIII", header, 0x08)
        if index_version != RIDX_VERSION or header_size != RIDX_HEADER_SIZE or \
                entry_count == 0 or entry_size != RIDX_ENTRY_SIZE or index_flags != 0 or \
                any(header[0x18:]):
            raise RomxError("invalid RIDX header fields")
        index_size = RIDX_HEADER_SIZE + entry_count * RIDX_ENTRY_SIZE
        if payload_size + index_size > footer_offset:
            raise RomxError("RIDX exceeds immutable content")
        handle.seek(payload_size)
        index = bytearray(handle.read(index_size))
        struct.pack_into("<I", index, 0x14, 0)
        if crc32(index) != index_crc:
            raise RomxError("RIDX CRC32 mismatch")

        entries = []
        folded_paths = set()
        entrypoints = 0
        for position in range(entry_count):
            base = RIDX_HEADER_SIZE + position * RIDX_ENTRY_SIZE
            flags, format_id, path_size, data_offset, data_size, value, reserved = \
                struct.unpack_from("<IHHQQII", index, base)
            if flags & ~(ENTRYPOINT | HAS_CRC32) or reserved or not 1 <= path_size <= 480:
                raise RomxError("invalid RIDX entry fields")
            path_field = index[base + 0x20:base + RIDX_ENTRY_SIZE]
            if any(path_field[path_size:]):
                raise RomxError("RIDX path padding is non-zero")
            try:
                virtual_path = bytes(path_field[:path_size]).decode("utf-8", "strict")
            except UnicodeDecodeError as exc:
                raise RomxError("RIDX path is not strict UTF-8") from exc
            validate_virtual_path(virtual_path)
            folded = virtual_path.casefold()
            if folded in folded_paths:
                raise RomxError("RIDX paths collide after case folding")
            folded_paths.add(folded)
            if data_offset > payload_size or data_size > payload_size - data_offset:
                raise RomxError("RIDX entry exceeds payload")
            is_entrypoint = bool(flags & ENTRYPOINT)
            if is_entrypoint:
                entrypoints += 1
                if data_offset != 0 or data_size == 0 or format_id == 0:
                    raise RomxError("entrypoint violates zero-offset or format rules")
            entries.append({
                "path": virtual_path, "flags": flags, "format_id": format_id,
                "data_offset": data_offset, "data_size": data_size,
                "crc32": f"{value:08x}" if flags & HAS_CRC32 else None,
                "entrypoint": is_entrypoint,
            })
        if entrypoints != 1:
            raise RomxError("RIDX must contain exactly one entrypoint")
        ranges = sorted((entry["data_offset"], entry["data_offset"] + entry["data_size"])
                        for entry in entries if entry["data_size"])
        cursor = 0
        for start, end in ranges:
            if start < cursor:
                raise RomxError("RIDX payload ranges overlap")
            if start > cursor and not all_zero(handle, cursor, start - cursor):
                raise RomxError("unindexed payload bytes are non-zero")
            cursor = end
        if cursor < payload_size and not all_zero(handle, cursor, payload_size - cursor):
            raise RomxError("trailing unindexed payload bytes are non-zero")
        if entry_count == 1 and (entries[0]["data_offset"] != 0 or
                                 entries[0]["data_size"] != payload_size):
            raise RomxError("single-file payload is not exact and contiguous")

        metadata_offset = payload_size + index_size
        cover_offset = metadata_offset + metadata_size
        immutable_content_end = cover_offset + cover_size
        if mutable_capacity:
            if mutable_capacity % 4096 or mutable_capacity < MIN_MUTABLE_CAPACITY or \
                    mutable_capacity > footer_offset:
                raise RomxError("invalid mutable capacity")
            mutable_offset = footer_offset - mutable_capacity
            if mutable_offset != align_up(immutable_content_end, 4096) or \
                    not all_zero(handle, immutable_content_end,
                                 mutable_offset - immutable_content_end):
                raise RomxError("invalid immutable alignment padding")
            handle.seek(mutable_offset)
            mutable_header = bytearray(handle.read(MUTABLE_HEADER_SIZE))
            if len(mutable_header) != MUTABLE_HEADER_SIZE or mutable_header[:4] != b"RMUT":
                raise RomxError("invalid mutable header")
            stored_header_crc = struct.unpack_from("<I", mutable_header, 0x34)[0]
            struct.pack_into("<I", mutable_header, 0x34, 0)
            if crc32(mutable_header) != stored_header_crc:
                raise RomxError("mutable header CRC32 mismatch")
            immutable_size = mutable_offset
        else:
            mutable_offset = 0
            immutable_size = footer_offset
            if immutable_content_end != footer_offset:
                raise RomxError("unexpected bytes before footer")

        if metadata_size:
            handle.seek(metadata_offset)
            metadata_bytes = handle.read(metadata_size)
            strict_json(metadata_bytes)
        if cover_size:
            handle.seek(cover_offset)
            validate_png(handle.read(cover_size))
        if hash_algorithm == HASH_NONE:
            if any(immutable_sha256):
                raise RomxError("disabled immutable SHA-256 must be zero")
        elif hash_algorithm == HASH_SHA256:
            if sha256_file(handle, 0, immutable_size) != immutable_sha256:
                raise RomxError("immutable SHA-256 mismatch")
        else:
            raise RomxError("invalid immutable hash algorithm")
        if verify_entry_crc32:
            for entry in entries:
                if entry["crc32"] is not None:
                    actual = crc32_file(handle, entry["data_offset"], entry["data_size"])
                    if f"{actual:08x}" != entry["crc32"]:
                        raise RomxError(f"entry CRC32 mismatch: {entry['path']}")

        return {
            "file": path.name,
            "file_size": file_size,
            "file_sha256": sha256_file(handle, 0, file_size).hex(),
            "footer": {
                "wire_version": version,
                "footer_size": FOOTER_SIZE,
                "footer_crc32": f"{expected_footer_crc:08x}",
                "payload_size": payload_size,
                "metadata_size": metadata_size,
                "cover_size": cover_size,
                "mutable_capacity": mutable_capacity,
                "platform_id": platform_id,
                "launch_format_id": launch_format_id,
                "immutable_hash_algorithm": hash_algorithm,
                "immutable_sha256": immutable_sha256.hex(),
            },
            "regions": {
                "payload": {"offset": 0, "size": payload_size},
                "ridx": {"offset": payload_size, "size": index_size},
                "metadata": {"offset": metadata_offset if metadata_size else 0,
                             "size": metadata_size},
                "cover": {"offset": cover_offset if cover_size else 0,
                          "size": cover_size},
                "mutable": {"offset": mutable_offset, "size": mutable_capacity},
                "footer": {"offset": footer_offset, "size": FOOTER_SIZE},
            },
            "ridx": {
                "index_version": index_version,
                "entry_count": entry_count,
                "entry_size": entry_size,
                "index_crc32": f"{index_crc:08x}",
                "entries": entries,
            },
            "status": "valid",
        }


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc32(kind + data))


def one_pixel_png() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    scanline = b"\x00\x20\x60\xa0\xff"
    return signature + png_chunk(b"IHDR", ihdr) + \
        png_chunk(b"IDAT", zlib.compress(scanline, 9)) + png_chunk(b"IEND", b"")


def synthetic_nes() -> bytes:
    return b"NES\x1a" + bytes((1, 1, 0, 0)) + bytes(8) + bytes(16384 + 8192)


def write_manifest(path: Path, manifest: dict) -> None:
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False,
                               sort_keys=True) + "\n", encoding="utf-8")


def generate_fixtures(directory: Path, replace: bool = False) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="romx-reference-") as temp_name:
        temp = Path(temp_name)
        nes = temp / "game.nes"
        nes.write_bytes(synthetic_nes())
        cue = temp / "game.cue"
        track1 = temp / "track01.bin"
        track2 = temp / "track02.bin"
        cue.write_bytes(b'FILE "track01.bin" BINARY\n  TRACK 01 MODE2/2352\n'
                        b'    INDEX 01 00:00:00\nFILE "track02.bin" BINARY\n'
                        b'  TRACK 02 AUDIO\n    INDEX 01 00:00:00\n')
        track1.write_bytes(bytes(range(256)) * 10)
        track2.write_bytes(bytes(reversed(range(256))) * 6)
        metadata = (b'{"schema_version":"0.2.0","name":"Reference NES",'
                    b'"crc32":"00000000"}')
        cover = one_pixel_png()

        cases = [
            ("minimal-single.romx", [{"path": "game.nes", "source": nes,
              "format_id": FORMATS["NES"]}], "game.nes", PLATFORMS["NES"],
             LAUNCH_FORMATS["RAW_SINGLE_FILE"], b"", b"", 0, False, False),
            ("single-complete.romx", [{"path": "game.nes", "source": nes,
              "format_id": FORMATS["NES"]}], "game.nes", PLATFORMS["NES"],
             LAUNCH_FORMATS["RAW_SINGLE_FILE"], metadata, cover,
             MIN_MUTABLE_CAPACITY, True, True),
            ("multi-cue.romx", [
                {"path": "disc/game.cue", "source": cue, "format_id": FORMATS["CUE"]},
                {"path": "disc/track01.bin", "source": track1, "format_id": FORMATS["BIN"]},
                {"path": "disc/track02.bin", "source": track2, "format_id": FORMATS["BIN"]},
             ], "disc/game.cue", PLATFORMS["PLAYSTATION"], LAUNCH_FORMATS["CUE"],
             b"", b"", 0, True, False),
        ]
        for name, entries, entrypoint, platform, launch, meta, image, mutable, entry_crc, sha in cases:
            output = directory / name
            manifest = build_romx(output, entries, entrypoint, platform, launch,
                                  meta, image, mutable, entry_crc, sha, 1,
                                  replace=replace)
            write_manifest(output.with_suffix(".manifest.json"), manifest)


def parse_assignments(values: list[str], label: str) -> dict[str, str]:
    result = {}
    for value in values:
        if "=" not in value:
            raise RomxError(f"{label} must use VIRTUAL_PATH=VALUE: {value}")
        key, assigned = value.split("=", 1)
        if key in result:
            raise RomxError(f"duplicate {label} for {key}")
        result[key] = assigned
    return result


def command_build(args) -> None:
    sources = parse_assignments(args.entry, "entry")
    formats = parse_assignments(args.entry_format, "entry-format")
    entries = []
    for virtual_path, source in sources.items():
        format_id = None
        if virtual_path in formats:
            format_id = parse_registry(formats[virtual_path], FORMATS, "entry format")
        entries.append({"path": virtual_path, "source": source, "format_id": format_id})
    entrypoint = args.entrypoint or (next(iter(sources)) if len(sources) == 1 else None)
    if entrypoint is None:
        raise RomxError("--entrypoint is required for multiple entries")
    manifest = build_romx(
        Path(args.output), entries, entrypoint,
        parse_registry(args.platform, PLATFORMS, "platform"),
        parse_registry(args.launch_format, LAUNCH_FORMATS, "launch format"),
        Path(args.metadata).read_bytes() if args.metadata else b"",
        Path(args.cover).read_bytes() if args.cover else b"",
        args.mutable_capacity, args.entry_crc32, args.immutable_sha256,
        args.payload_alignment, args.force)
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))


def command_inspect(args) -> None:
    manifest = inspect_romx(Path(args.input), args.verify_entry_crc32)
    print(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True))


def command_fixtures(args) -> None:
    generate_fixtures(Path(args.directory), args.force)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build a deterministic ROMX file")
    build.add_argument("output")
    build.add_argument("--entry", action="append", default=[], metavar="VPATH=SOURCE",
                       required=True)
    build.add_argument("--entry-format", action="append", default=[],
                       metavar="VPATH=FORMAT")
    build.add_argument("--entrypoint")
    build.add_argument("--platform", required=True)
    build.add_argument("--launch-format", required=True)
    build.add_argument("--metadata")
    build.add_argument("--cover")
    build.add_argument("--mutable-capacity", type=int, default=0)
    build.add_argument("--payload-alignment", type=int, default=1)
    build.add_argument("--entry-crc32", action="store_true")
    build.add_argument("--immutable-sha256", action="store_true")
    build.add_argument("--force", action="store_true")
    build.set_defaults(function=command_build)

    inspect = commands.add_parser("inspect", help="validate and describe a ROMX file")
    inspect.add_argument("input")
    inspect.add_argument("--verify-entry-crc32", action="store_true")
    inspect.set_defaults(function=command_inspect)

    fixtures = commands.add_parser("fixtures", help="generate reference fixtures")
    fixtures.add_argument("directory")
    fixtures.add_argument("--force", action="store_true")
    fixtures.set_defaults(function=command_fixtures)
    return parser


def main() -> int:
    try:
        args = make_parser().parse_args()
        args.function(args)
        return 0
    except (OSError, RomxError) as exc:
        print(f"romx_reference.py: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
