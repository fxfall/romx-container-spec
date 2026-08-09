#!/usr/bin/env python3
"""Generate and verify the frozen ROMX 1.0 conformance fixtures.

The fixture bytes are deliberately tiny and deterministic.  Reader fixtures
exercise container boundary rules; writer golden fixtures freeze canonical
byte output.  Neither depends on an emulator, Pillow, or a particular
implementation language.  The checked-in ``*.romx`` and ``*.manifest.json``
files are the conformance corpus; this script is their reproducible source.

Usage::

    python3 tools/generate_fixtures.py --write
    python3 tools/generate_fixtures.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path
from typing import Any


FOOTER_SIZE = 128
UINT64_MAX = (1 << 64) - 1
FLAG_METADATA = 1 << 0
FLAG_COVER = 1 << 1
FLAG_BODY_SHA256 = 1 << 2

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "tests" / "fixtures"
WRITER_DIRECTORY = "writer"
ROM = b"abc"
ROM_CRC32 = f"{zlib.crc32(ROM) & 0xffffffff:08x}"
ZERO_SHA256 = "00" * 32

# A valid 1x1 RGBA PNG.  It is intentionally kept inline so fixture generation
# has no Pillow or image-file dependency.
PNG = bytes.fromhex(
    "89504e470d0a1a0a"
    "0000000d49484452000000010000000108060000001f15c489"
    "0000000b49444154789c6360000200000500017a5eab3f"
    "0000000049454e44ae426082"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def metadata_bytes(
    *,
    name: str = "ROMX fixture",
    crc: str | None = ROM_CRC32,
    has_cover: bool = False,
) -> bytes:
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "name": name,
        "platform": "gb",
        "payload_format": "gb",
    }
    if crc is not None:
        value["crc32"] = crc
    if has_cover:
        value["cover"] = {
            "mime_type": "image/png",
            "width": 1,
            "height": 1,
        }
    return json_bytes(value)


def le32(value: int) -> bytes:
    return struct.pack("<I", value)


def le64(value: int) -> bytes:
    return struct.pack("<Q", value)


def make_footer(
    *,
    magic: str,
    version: int,
    rom_offset: int,
    rom_size: int,
    metadata_offset: int,
    metadata_size: int,
    cover_offset: int,
    cover_size: int,
    reserved: str,
    flags: int,
    footer_size: int,
    body_sha256: str,
) -> bytes:
    footer = bytearray(FOOTER_SIZE)
    footer[0:4] = magic.encode("ascii")
    footer[4:8] = le32(version)
    footer[8:16] = le64(rom_offset)
    footer[16:24] = le64(rom_size)
    footer[24:32] = le64(metadata_offset)
    footer[32:40] = le64(metadata_size)
    footer[40:48] = le64(cover_offset)
    footer[48:56] = le64(cover_size)
    footer[56:88] = bytes.fromhex(reserved)
    footer[88:92] = le32(flags)
    footer[92:96] = le32(footer_size)
    footer[96:128] = bytes.fromhex(body_sha256)
    return bytes(footer)


def container(
    *,
    metadata: bytes | None = None,
    cover: bytes | None = None,
    order: tuple[str, ...] = ("rom", "metadata", "cover"),
    body_sha_enabled: bool = True,
    footer_overrides: dict[str, int | str] | None = None,
) -> tuple[bytes, dict[str, Any]]:
    parts = {"rom": ROM, "metadata": metadata or b"", "cover": cover or b""}
    body = bytearray()
    offsets: dict[str, int] = {name: 0 for name in parts}
    for name in order:
        part = parts[name]
        if part:
            offsets[name] = len(body)
            body.extend(part)

    body_bytes = bytes(body)
    fields: dict[str, int | str] = {
        "magic": "ROMX",
        "version": 1,
        "rom_offset": offsets["rom"],
        "rom_size": len(parts["rom"]),
        "metadata_offset": offsets["metadata"] if parts["metadata"] else 0,
        "metadata_size": len(parts["metadata"]),
        "cover_offset": offsets["cover"] if parts["cover"] else 0,
        "cover_size": len(parts["cover"]),
        "reserved": ZERO_SHA256,
        "flags": (
            (FLAG_METADATA if parts["metadata"] else 0)
            | (FLAG_COVER if parts["cover"] else 0)
            | (FLAG_BODY_SHA256 if body_sha_enabled else 0)
        ),
        "footer_size": FOOTER_SIZE,
        "body_sha256": sha256(body_bytes) if body_sha_enabled else ZERO_SHA256,
    }
    if footer_overrides:
        fields.update(footer_overrides)
    footer = make_footer(**fields)  # type: ignore[arg-type]
    return body_bytes + footer, {
        "body": body_bytes,
        "footer": fields,
        "metadata": metadata,
        "cover": cover,
    }


def manifest(
    *,
    name: str,
    purpose: list[str],
    info: dict[str, Any],
    reader_open: str,
    validate_all: str,
    components: dict[str, str],
    metadata_result: str | None = None,
    cover_result: str | None = None,
    payload_extraction: str = "not_attempted",
    salvage: bool = False,
    metadata_crc_declared: str | None = None,
) -> dict[str, Any]:
    footer = info["footer"]
    body = info["body"]
    footer_body_sha = str(footer["body_sha256"])
    if reader_open != "ROMX_OK":
        metadata_result = "not_attempted"
        cover_result = "not_attempted"
    else:
        if metadata_result is None:
            metadata_result = "ROMX_OK" if info["metadata"] is not None else "ROMX_E_METADATA_ABSENT"
        if cover_result is None:
            cover_result = "ROMX_OK" if info["cover"] is not None else "ROMX_E_COVER_ABSENT"
    declared_crc = metadata_crc_declared
    crc_status = "not_attempted" if reader_open != "ROMX_OK" else "absent"
    if reader_open == "ROMX_OK" and info["metadata"] is not None:
        if components.get("metadata") == "invalid":
            crc_status = "invalid"
        elif declared_crc is None:
            crc_status = "absent"
        else:
            crc_status = "valid_lookup_value"
    return {
        "manifest_version": 2,
        "fixture": name,
        "file": f"{name}.romx",
        "purpose": purpose,
        "payload": {"size": len(ROM), "computed_crc32": ROM_CRC32},
        "expected": {
            "reader_open": reader_open,
            "validate_all": validate_all,
            "payload_extraction": payload_extraction,
            "footer": {
                "magic": footer["magic"],
                "version": footer["version"],
                "rom_offset": footer["rom_offset"],
                "rom_size": footer["rom_size"],
                "metadata_offset": footer["metadata_offset"],
                "metadata_size": footer["metadata_size"],
                "cover_offset": footer["cover_offset"],
                "cover_size": footer["cover_size"],
                "reserved": footer["reserved"],
                "flags": footer["flags"],
                "footer_size": footer["footer_size"],
                "body_sha256": footer_body_sha,
            },
            "crc32": {
                "payload_computed": ROM_CRC32,
                "metadata_declared": declared_crc,
                "metadata_syntax": crc_status,
                "role": "database_lookup_only",
            },
            "sha256": {
                "body_computed": sha256(body),
                "body_footer": footer_body_sha,
            },
            "components": components,
            "metadata_result": metadata_result,
            "cover_result": cover_result,
            "payload_salvage": salvage,
        },
    }


def writer_metadata_bytes(
    source: dict[str, Any] | None,
    *,
    crc32_override: str | None = None,
    cover: bytes | None = None,
) -> bytes | None:
    """Apply the canonical writer transformations to source metadata."""
    if source is None:
        return None
    value = dict(source)
    value["crc32"] = crc32_override if crc32_override is not None else ROM_CRC32
    if "origin_crc32" in value:
        value["origin_crc32"] = ROM_CRC32
    if cover is not None:
        value["cover"] = {"mime_type": "image/png", "width": 1, "height": 1}
    return json_bytes(value)


def writer_manifest(
    *,
    name: str,
    data: bytes,
    info: dict[str, Any],
    source_metadata: dict[str, Any] | None,
    crc32_override: str | None,
    origin_crc32_enabled: bool,
    body_sha256_enabled: bool,
) -> dict[str, Any]:
    footer = info["footer"]
    metadata = info["metadata"]
    cover = info["cover"]
    body = info["body"]
    footer_bytes = data[-FOOTER_SIZE:]
    return {
        "manifest_version": 1,
        "kind": "writer_golden",
        "fixture": name,
        "file": f"{name}.romx",
        "input": {
            "payload_hex": ROM.hex(),
            "metadata": source_metadata,
            "cover_hex": cover.hex() if cover is not None else None,
            "options": {
                "crc32_override": crc32_override,
                "origin_crc32_enabled": origin_crc32_enabled,
                "body_sha256_enabled": body_sha256_enabled,
            },
        },
        "canonical": {
            "region_order": ["rom", "metadata", "cover", "footer"],
            "metadata_encoding": "utf-8-json-no-bom-compact",
            "footer_integer_encoding": "little-endian",
            "reserved_bytes": "zero",
        },
        "expected": {
            "file_size": len(data),
            "file_sha256": sha256(data),
            "file_hex": data.hex(),
            "regions": {
                "rom": {"offset": footer["rom_offset"], "size": footer["rom_size"], "hex": ROM.hex()},
                "metadata": {
                    "offset": footer["metadata_offset"],
                    "size": footer["metadata_size"],
                    "utf8": metadata.decode("utf-8") if metadata is not None else None,
                    "hex": metadata.hex() if metadata is not None else None,
                },
                "cover": {
                    "offset": footer["cover_offset"],
                    "size": footer["cover_size"],
                    "hex": cover.hex() if cover is not None else None,
                },
                "footer": {
                    "offset": len(body),
                    "size": FOOTER_SIZE,
                    "hex": footer_bytes.hex(),
                },
            },
            "footer": footer,
        },
    }


def writer_fixture_specs() -> list[tuple[bytes, dict[str, Any]]]:
    base_metadata: dict[str, Any] = {
        "schema_version": "1.0",
        "name": "ROMX writer golden",
        "platform": "gb",
        "payload_format": "gb",
    }
    body_metadata = {**base_metadata, "name": "ROMX body SHA-256 golden"}
    cases = (
        ("payload-only", None, None, False, None, False),
        ("metadata-auto-crc32", base_metadata, None, False, None, False),
        ("metadata-lookup-crc32-override", base_metadata, "00000000", False, None, False),
        (
            "metadata-origin-crc32",
            {**base_metadata, "origin_crc32": "00000000"},
            None,
            True,
            None,
            False,
        ),
        ("cover", base_metadata, None, False, PNG, False),
        ("body-sha256-disabled", body_metadata, None, False, None, False),
        ("body-sha256-enabled", body_metadata, None, False, None, True),
    )
    specs: list[tuple[bytes, dict[str, Any]]] = []
    for name, source, crc_override, origin_enabled, cover, body_sha_enabled in cases:
        source_copy = dict(source) if source is not None else None
        metadata = writer_metadata_bytes(
            source_copy,
            crc32_override=crc_override,
            cover=cover,
        )
        data, info = container(
            metadata=metadata,
            cover=cover,
            body_sha_enabled=body_sha_enabled,
        )
        specs.append(
            (
                data,
                writer_manifest(
                    name=name,
                    data=data,
                    info=info,
                    source_metadata=source_copy,
                    crc32_override=crc_override,
                    origin_crc32_enabled=origin_enabled,
                    body_sha256_enabled=body_sha_enabled,
                ),
            )
        )
    return specs


def fixture_specs() -> list[tuple[bytes, dict[str, Any]]]:
    valid_metadata = metadata_bytes()
    cover_metadata = metadata_bytes(has_cover=True)

    specs: list[tuple[bytes, dict[str, Any]]] = []

    def add(
        name: str,
        data: bytes,
        info: dict[str, Any],
        *,
        purpose: list[str],
        reader_open: str = "ROMX_OK",
        validate_all: str = "ROMX_OK",
        components: dict[str, str],
        metadata_result: str | None = None,
        cover_result: str | None = None,
        payload_extraction: str = "not_attempted",
        salvage: bool = False,
        metadata_crc_declared: str | None = None,
    ) -> None:
        specs.append(
            (
                data,
                manifest(
                    name=name,
                    purpose=purpose,
                    info=info,
                    reader_open=reader_open,
                    validate_all=validate_all,
                    components=components,
                    metadata_result=metadata_result,
                    cover_result=cover_result,
                    payload_extraction=payload_extraction,
                    salvage=salvage,
                    metadata_crc_declared=metadata_crc_declared,
                ),
            )
        )

    valid_components = {
        "structure": "valid", "body_sha256": "valid", "metadata": "valid",
        "metadata_crc32": "valid_lookup_value", "cover": "valid",
    }

    data, info = container(body_sha_enabled=False)
    add(
        "minimal-valid", data, info,
        purpose=["minimal-valid-romx", "metadata-absent", "cover-absent", "body-sha256-disabled"],
        components={
            "structure": "valid", "body_sha256": "absent", "metadata": "absent",
            "metadata_crc32": "absent", "cover": "absent",
        },
        payload_extraction="ROMX_OK",
    )

    data, info = container(body_sha_enabled=True)
    add(
        "metadata-absent", data, info,
        purpose=["metadata-absent", "body-sha256-enabled"],
        components={
            "structure": "valid", "body_sha256": "valid", "metadata": "absent",
            "metadata_crc32": "absent", "cover": "absent",
        },
        payload_extraction="ROMX_OK",
    )

    data, info = container(
        body_sha_enabled=True,
        footer_overrides={"metadata_offset": 0x1234},
    )
    add(
        "metadata-absent-nonzero-offset", data, info,
        purpose=["metadata-size-zero-offset-is-ignored"],
        components={
            "structure": "valid", "body_sha256": "valid", "metadata": "absent",
            "metadata_crc32": "absent", "cover": "absent",
        },
        payload_extraction="ROMX_OK",
    )

    data, info = container(metadata=valid_metadata, body_sha_enabled=True)
    add(
        "cover-absent", data, info,
        purpose=["cover-absent"],
        components={**valid_components, "cover": "absent"},
        payload_extraction="ROMX_OK",
        metadata_crc_declared=ROM_CRC32,
    )

    data, info = container(
        metadata=valid_metadata,
        body_sha_enabled=True,
        footer_overrides={"cover_offset": 0x5678},
    )
    add(
        "cover-absent-nonzero-offset", data, info,
        purpose=["cover-size-zero-offset-is-ignored"],
        components={**valid_components, "cover": "absent"},
        payload_extraction="ROMX_OK",
        metadata_crc_declared=ROM_CRC32,
    )

    data, info = container(metadata=cover_metadata, cover=PNG, order=("cover", "metadata", "rom"))
    add(
        "reordered-regions", data, info,
        purpose=["any-region-order", "valid-cover"],
        components=valid_components,
        payload_extraction="ROMX_OK",
        metadata_crc_declared=ROM_CRC32,
    )

    for name, overrides, error, purpose in (
        ("footer-magic-invalid", {"magic": "BAD!"}, "ROMX_E_INVALID_FOOTER", "footer-magic"),
        ("footer-version-invalid", {"version": 2}, "ROMX_E_INVALID_FOOTER", "footer-version"),
        ("footer-size-invalid", {"footer_size": 127}, "ROMX_E_INVALID_FOOTER", "footer-size"),
        ("offset-overflow", {"rom_offset": UINT64_MAX - 3, "rom_size": 8}, "ROMX_E_RANGE", "offset-overflow"),
        ("offset-out-of-bounds", {"rom_offset": 0, "rom_size": len(ROM) + 1}, "ROMX_E_RANGE", "offset-out-of-bounds"),
    ):
        data, info = container(body_sha_enabled=False, footer_overrides=overrides)
        add(
            name, data, info, purpose=[purpose], reader_open=error,
            validate_all="not_attempted", components={"structure": "invalid"},
        )

    data, info = container(
        metadata=valid_metadata, body_sha_enabled=False,
        footer_overrides={"metadata_offset": 2},
    )
    add(
        "regions-overlap", data, info, purpose=["regions-overlap"],
        reader_open="ROMX_E_OVERLAP", validate_all="not_attempted",
        components={"structure": "invalid"},
    )

    data, info = container(body_sha_enabled=True)
    uncovered_body = info["body"] + b"gap"
    uncovered_footer = dict(info["footer"])
    uncovered_footer["body_sha256"] = sha256(uncovered_body)
    data = uncovered_body + make_footer(**uncovered_footer)  # type: ignore[arg-type]
    info["body"] = uncovered_body
    info["footer"] = uncovered_footer
    add(
        "regions-gap", data, info, purpose=["all-body-bytes-must-be-covered"],
        reader_open="ROMX_E_RANGE", validate_all="not_attempted",
        components={"structure": "invalid"},
    )

    data, info = container(
        metadata=valid_metadata, body_sha_enabled=False,
        footer_overrides={"flags": 0},
    )
    add(
        "flags-mismatch", data, info, purpose=["flags-mismatch"],
        reader_open="ROMX_E_INVALID_FLAGS", validate_all="not_attempted",
        components={"structure": "invalid"},
    )

    data, info = container(
        body_sha_enabled=True, footer_overrides={"reserved": "a5" * 32},
    )
    add(
        "reserved-nonzero", data, info,
        purpose=["reserved-bytes-ignored-by-reader"],
        components={
            "structure": "valid", "body_sha256": "valid", "metadata": "absent",
            "metadata_crc32": "absent", "cover": "absent",
        },
        payload_extraction="ROMX_OK",
    )

    data, info = container(
        body_sha_enabled=False, footer_overrides={"body_sha256": "a5" * 32},
    )
    add(
        "body-sha256-disabled-nonzero", data, info,
        purpose=["disabled-body-sha256-must-be-zero"],
        reader_open="ROMX_E_INVALID_FLAGS", validate_all="not_attempted",
        components={"structure": "invalid"},
    )

    data, info = container(
        body_sha_enabled=True, footer_overrides={"body_sha256": ZERO_SHA256},
    )
    add(
        "body-sha256-mismatch", data, info,
        purpose=["enabled-body-sha256-mismatch"],
        validate_all="ROMX_E_BODY_HASH",
        components={
            "structure": "valid", "body_sha256": "invalid", "metadata": "absent",
            "metadata_crc32": "absent", "cover": "absent",
        },
    )

    invalid_metadata_cases = (
        ("metadata-bom", b"\xef\xbb\xbf" + valid_metadata, "metadata-json-bom", "ROMX_E_METADATA_UTF8"),
        (
            "metadata-invalid-utf8",
            b'{"schema_version":"1.0","name":"A\xff","platform":"gb","payload_format":"gb"}',
            "metadata-invalid-utf8",
            "ROMX_E_METADATA_UTF8",
        ),
        (
            "metadata-duplicate-key",
            b'{"schema_version":"1.0","name":"A","name":"B","platform":"gb","payload_format":"gb"}',
            "metadata-json-duplicate-key",
            "ROMX_E_METADATA_SCHEMA",
        ),
        (
            "metadata-nested-duplicate-key",
            b'{"schema_version":"1.0","name":"A","platform":"gb","payload_format":"gb","crc32":"352441c2","cover":{"mime_type":"image/png","mime_type":"image/png"}}',
            "metadata-nested-json-duplicate-key",
            "ROMX_E_METADATA_SCHEMA",
        ),
    )
    for name, metadata, purpose, metadata_error in invalid_metadata_cases:
        data, info = container(metadata=metadata, body_sha_enabled=True)
        add(
            name, data, info, purpose=[purpose, "invalid-metadata-does-not-block-payload"],
            components={
                "structure": "valid", "body_sha256": "valid", "metadata": "invalid",
                "metadata_crc32": "invalid", "cover": "absent",
            },
            metadata_result=metadata_error,
            payload_extraction="ROMX_OK",
            salvage=True,
        )

    lookup_metadata = metadata_bytes(crc="00000000")
    data, info = container(metadata=lookup_metadata, body_sha_enabled=True)
    add(
        "metadata-crc32-lookup", data, info,
        purpose=["crc32-is-database-lookup-not-integrity"],
        components={**valid_components, "cover": "absent"},
        payload_extraction="ROMX_OK",
        metadata_crc_declared="00000000",
    )

    def malformed_cover(kind: str) -> bytes:
        if kind == "oob":
            value = bytearray(PNG)
            value[8:12] = struct.pack(">I", 0x7FFFFFFF)
            return bytes(value)
        if kind == "crc":
            value = bytearray(PNG)
            value[55] ^= 1
            return bytes(value)
        if kind == "iend":
            return PNG[:-12]
        raise AssertionError(kind)

    for kind, name, purpose in (
        ("oob", "cover-chunk-out-of-bounds", "png-chunk-out-of-bounds"),
        ("crc", "cover-chunk-crc-mismatch", "png-chunk-crc-mismatch"),
        ("iend", "cover-missing-iend", "png-missing-iend"),
    ):
        bad_cover = malformed_cover(kind)
        data, info = container(metadata=metadata_bytes(has_cover=True), cover=bad_cover, body_sha_enabled=True)
        add(
            name,
            data,
            info,
            purpose=[purpose],
            components={
                "structure": "valid", "body_sha256": "valid", "metadata": "valid",
                "metadata_crc32": "valid_lookup_value", "cover": "invalid",
            },
            cover_result="ROMX_E_COVER_PNG",
            payload_extraction="ROMX_OK",
            metadata_crc_declared=ROM_CRC32,
        )

    salvage_metadata = b"\xef\xbb\xbf" + valid_metadata
    salvage_cover = malformed_cover("crc")
    data, info = container(metadata=salvage_metadata, cover=salvage_cover, body_sha_enabled=True)
    add(
        "payload-salvage",
        data,
        info,
        purpose=["payload-salvage", "invalid-optional-regions-must-not-block-rom"],
        components={
            "structure": "valid", "body_sha256": "valid", "metadata": "invalid",
            "metadata_crc32": "invalid", "cover": "invalid",
        },
        metadata_result="ROMX_E_METADATA_UTF8",
        cover_result="ROMX_E_COVER_PNG",
        payload_extraction="ROMX_OK",
        salvage=True,
    )

    return specs


def expected_files(output: Path) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    for data, item in fixture_specs():
        name = item["fixture"]
        files[output / f"{name}.romx"] = data
        files[output / f"{name}.manifest.json"] = (
            (json.dumps(item, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
    for data, item in writer_fixture_specs():
        name = item["fixture"]
        files[output / WRITER_DIRECTORY / f"{name}.romx"] = data
        files[output / WRITER_DIRECTORY / f"{name}.manifest.json"] = (
            (json.dumps(item, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        )
    return files


def write_files(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    expected = expected_files(output)
    actual = set(output.rglob("*.romx")) | set(output.rglob("*.manifest.json"))
    for path in actual - set(expected):
        path.unlink()
    for path, data in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def check_files(output: Path) -> int:
    expected = expected_files(output)
    failures = 0
    actual_paths = set(output.rglob("*.romx")) | set(output.rglob("*.manifest.json"))
    for path, data in expected.items():
        if not path.exists():
            print(f"missing fixture: {path}", file=sys.stderr)
            failures += 1
        elif path.read_bytes() != data:
            print(f"fixture differs from generator: {path}", file=sys.stderr)
            failures += 1
    for path in sorted(actual_paths - set(expected)):
        print(f"unexpected fixture file: {path}", file=sys.stderr)
        failures += 1
    if failures:
        print(f"{failures} frozen fixture error(s)", file=sys.stderr)
        return 1
    reader_count = len(fixture_specs())
    writer_count = len(writer_fixture_specs())
    print(f"verified {reader_count} reader fixtures and {writer_count} writer golden fixtures")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write the frozen fixture files")
    mode.add_argument("--check", action="store_true", help="verify checked-in files byte-for-byte")
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.write:
        write_files(output)
        print(
            f"wrote {len(fixture_specs())} reader fixtures and "
            f"{len(writer_fixture_specs())} writer golden fixtures to {output}"
        )
        return 0
    return check_files(output)


if __name__ == "__main__":
    raise SystemExit(main())
