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
import zlib
from pathlib import Path
from typing import Iterable
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


def crc32(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xffffffff:08x}"


def normalize_crc32(value: str) -> str:
    """Validate and canonicalize an explicit database CRC32 key."""
    if len(value) != 8 or any(character not in "0123456789abcdefABCDEF" for character in value):
        raise RomxError("CRC32 override must be exactly 8 hexadecimal characters")
    return value.lower()


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


def _json_bytes(metadata_path: Path, rom_bytes: bytes, crc32_override: str | None = None) -> bytes:
    raw = metadata_path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise RomxError("metadata must not contain a UTF-8 BOM")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RomxError(f"invalid metadata JSON: {exc}") from exc
    _validate_metadata(value)
    value["crc32"] = normalize_crc32(crc32_override) if crc32_override is not None else crc32(rom_bytes)
    # Compact, deterministic UTF-8 JSON. No filesystem path is embedded.
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def pack(
    rom_path: Path,
    metadata_path: Path,
    output_path: Path,
    cover_path: Path | None = None,
    crc32_override: str | None = None,
) -> None:
    rom = rom_path.read_bytes()
    if not rom:
        raise RomxError("ROM payload must not be empty")
    metadata = _json_bytes(metadata_path, rom, crc32_override)
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


def _playlist_items(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
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
    if data.startswith(PNG_SIGNATURE) and len(data) >= 24 and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    return None


def _safe_filename(label: str) -> str:
    return label.replace("/", "_").replace("\\", "_").replace("\x00", "_").strip() or "untitled"


def _find_import_file(primary: Path, fallback: Iterable[Path]) -> Path | None:
    if primary.is_file():
        return primary
    for candidate in fallback:
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


def _retroarch_item_metadata(item: dict[str, Any]) -> dict[str, Any]:
    """Preserve non-path LPL compatibility fields under the x namespace."""
    extension: dict[str, Any] = {}
    for key in ("db_name", "core_name"):
        value = item.get(key)
        if isinstance(value, str) and value and value != "DETECT":
            extension[key] = value
    source_crc = item.get("crc32")
    if isinstance(source_crc, str) and source_crc:
        extension["source_crc32"] = source_crc
    known = {"path", "label", "core_path", "core_name", "crc32", "db_name"}
    extra = {key: value for key, value in item.items() if key not in known and not key.endswith("_path")}
    if extra:
        extension["extra"] = extra
    return extension


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
        return _find_import_file(force_cover_dir / f"{rom_path.stem}.png", (force_cover_dir / f"{label}.png",))

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
    return _find_import_file(cover_dir / f"{rom_path.stem}.png", (cover_dir / f"{label}.png",))


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
) -> int:
    """Import one LPL into sequential ROMX files.

    `rom_root` maps RetroArch virtual paths such as `/roms/02-GBA/1.gba` to
    a local tree. `force_rom_dir` and `force_cover_dir` ignore the directory
    part from the LPL and look up each item by basename, which is useful when
    ROMs or thumbnails have been moved to a flat directory. When no roots are
    supplied, absolute ROM paths in the LPL are used directly and a standard
    `playlists/../thumbnails/<playlist>/<cover_set>` tree is inferred. Useful
    LPL fields are written to metadata; RetroArch-only fields are preserved in
    `x-retroarch`, while paths remain outside metadata.
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
            rom_path = _resolve_lpl_path(lpl_path, item_path)
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
        label = item.get("label") or rom_path.stem
        metadata: dict[str, Any] = {"schema_version": "1.0", "label": str(label), "platform": _platform_for(payload_format, playlist_name), "payload_format": payload_format}
        identity = _lpl_item_identity(item.get("crc32"))
        if identity and identity[0] == "serial":
            metadata["serial"] = identity[1]
        retroarch = _retroarch_item_metadata(item)
        if retroarch:
            metadata["x-retroarch"] = retroarch
        cover_path = _cover_from_lpl(
            lpl_path,
            playlist_name,
            item,
            rom_path,
            str(label),
            cover_root,
            force_cover_dir,
            cover_set,
        )
        if cover_path:
            cover_bytes = cover_path.read_bytes()
            dimensions = _png_dimensions(cover_bytes)
            metadata["cover"] = {"mime_type": "image/png"}
            if dimensions:
                metadata["cover"].update(width=dimensions[0], height=dimensions[1], sha256=sha256(cover_bytes).hex())
        metadata_file = output_dir / f".metadata-{index:06d}.json"
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output_path = output_dir / f"{index:06d}.{payload_format}x"
        try:
            pack(rom_path, metadata_file, output_path, cover_path, crc32_override)
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
        rom = data[info["rom_offset"]:info["rom_offset"] + info["rom_size"]]
        metadata: dict[str, Any] = {}
        if info["metadata_size"]:
            start = info["metadata_offset"]
            metadata = _validate_metadata(json.loads(data[start:start + info["metadata_size"]].decode("utf-8")))
        payload_format = str(metadata.get("payload_format", "rom"))
        filename = f"{index:06d}.{payload_format}"
        (actual_rom_dir / filename).write_bytes(data[info["rom_offset"]:info["rom_offset"] + info["rom_size"]])
        label = str(metadata.get("label", romx_path.stem))
        if info["cover_size"]:
            cover = data[info["cover_offset"]:info["cover_offset"] + info["cover_size"]]
            if not cover.startswith(PNG_SIGNATURE):
                raise RomxError(f"embedded cover is not PNG: {romx_path}")
            (actual_cover_dir / f"{_safe_filename(label)}.png").write_bytes(cover)
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
        retroarch = metadata.get("x-retroarch")
        retroarch = retroarch if isinstance(retroarch, dict) else {}
        items.append({"path": lpl_item_path, "label": label, "core_path": "DETECT", "core_name": retroarch.get("core_name", "DETECT"), "crc32": f"{lookup_crc}|crc", "db_name": retroarch.get("db_name", "")})
    actual_lpl.parent.mkdir(parents=True, exist_ok=True)
    actual_lpl.write_text(json.dumps({"version": "1.5", "default_core_path": "DETECT", "default_core_name": "DETECT", "label_display_mode": 0, "right_thumbnail_mode": 0, "left_thumbnail_mode": 0, "thumbnail_match_mode": 0, "sort_mode": 0, "items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(items)


def main() -> int:
    parser = argparse.ArgumentParser(description="ROMX 1.0 packer, inspector, verifier, extractor, LPL importer, and LPL exporter")
    sub = parser.add_subparsers(dest="command", required=True)
    pack_parser = sub.add_parser("pack", help="create a ROMX file")
    pack_parser.add_argument("rom", type=Path)
    pack_parser.add_argument("metadata", type=Path)
    pack_parser.add_argument("-o", "--output", required=True, type=Path)
    pack_parser.add_argument("--cover", type=Path)
    pack_parser.add_argument("--crc32", help="override metadata CRC32 lookup key (8 hexadecimal characters)")
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
            pack(args.rom, args.metadata, args.output, args.cover, args.crc32)
        elif args.command == "inspect":
            print(json.dumps(inspect(args.romx), ensure_ascii=False, indent=2))
        elif args.command == "verify":
            _read_footer(args.romx)
            print(f"valid ROMX: {args.romx}")
        elif args.command == "extract":
            extract(args.romx, args.output)
        elif args.command == "import-lpl":
            count = import_lpl(args.lpl, args.output, args.rom_root, args.cover_root, args.force_rom_dir, args.force_cover_dir, args.cover_set, args.skip_missing, args.crc32)
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
