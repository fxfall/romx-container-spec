# ROMX 1.0 Binary Specification

Status: Draft 1  
Integer encoding: unsigned little-endian  
Footer size: 128 bytes

## 1. Container layout

The file consists of three independently addressable data regions followed by a fixed footer:

```text
ROM payload | metadata JSON | optional PNG cover | 128-byte footer
```

The order above is the recommended write order. Readers must use footer offsets and sizes, not assume this order. The ROM payload is the original ROM bytes; ROMX does not add a ROM header or alter the payload.

Metadata and cover are embedded bytes in the ROMX file. They have no external path. The emulator core receives only the extracted ROM payload.

## 2. Footer

The footer occupies the final 128 bytes. All integer fields are unsigned little-endian.

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `ROMX` |
| `0x04` | 4 | uint32 | `version` | Exactly `1` for v1 |
| `0x08` | 8 | uint64 | `rom_offset` | Start of ROM payload |
| `0x10` | 8 | uint64 | `rom_size` | Greater than zero |
| `0x18` | 8 | uint64 | `metadata_offset` | Start of metadata |
| `0x20` | 8 | uint64 | `metadata_size` | Zero means absent |
| `0x28` | 8 | uint64 | `cover_offset` | Start of cover |
| `0x30` | 8 | uint64 | `cover_size` | Zero means absent |
| `0x38` | 32 | bytes | `rom_sha256` | SHA-256 of ROM payload |
| `0x58` | 4 | uint32 | `flags` | Feature flags |
| `0x5C` | 4 | uint32 | `footer_size` | Exactly `128` for v1 |
| `0x60` | 32 | bytes | `body_sha256` | SHA-256 of bytes before footer, or all zero when disabled |

The footer ends at `0x80`. Every non-empty region must start at or after offset zero, end at or before the footer, and not overlap another region.

### Flags

| Bit | Name | Meaning |
|---:|---|---|
| 0 | `HAS_METADATA` | `metadata_size > 0` |
| 1 | `HAS_COVER` | `cover_size > 0` |
| 2 | `HAS_BODY_SHA256` | `body_sha256` is present and must be checked |
| 3–31 | Reserved | Must be zero in v1 |

The flags and sizes must agree. v1 does not compress or encrypt ROM payloads. Such a change requires a new major version or an explicit capability that v1 readers cannot mistake for raw ROM bytes.

## 3. ROM payload

The payload must be the exact standard ROM bytes accepted by the target emulator core. A writer must not pad, strip headers, byte-swap, patch, or otherwise modify it. `rom_sha256` covers only these bytes. `payload_format` describes the format produced after extraction; it does not change the payload.

The filename extension is only a hint. The container extension is the original ROM extension plus `x`, for example `.gba` → `.gbax`.

## 4. Metadata region

Metadata is optional UTF-8 JSON without a BOM. The top-level value must be an object conforming to `schema/romx-metadata.schema.json`. `metadata_offset` and `metadata_size` locate the exact JSON bytes in the container. Unknown namespaced fields may be preserved; malformed metadata may be ignored while the ROM remains readable.

The metadata `platform` and `payload_format` fields describe the payload and do not alter extraction. For a Game Boy CGB flag of `0xC0`, the reader must classify the payload as `gbc`; for `0x80`, it must use a valid `payload_format` of `gb` or `gbc` rather than guessing. Other byte values do not override a valid `payload_format`.

## 5. Cover region

v1 permits one optional PNG cover. The reader must validate the PNG signature and enforce limits before decoding. The metadata `cover` object describes the embedded bytes; it is not a path or a download instruction.

Recommended implementation limits are 32 MiB and an 8192-pixel maximum width or height. A malformed cover must not prevent ROM extraction.

## 6. Reader validation

A reader should perform these checks in order:

1. File size is at least 128 bytes.
2. Footer magic, version, and footer size are valid.
3. Offsets and sizes do not overflow and end before the footer.
4. Non-empty regions do not overlap.
5. Flags agree with metadata and cover sizes; reserved bits are zero.
6. Metadata is within implementation limits and, when present, valid UTF-8 JSON.
7. Cover is within limits and, when present, has a valid PNG signature.
8. `rom_sha256` matches the ROM payload.
9. If `HAS_BODY_SHA256` is set, `body_sha256` matches every byte before the footer.

If the ROM region or footer fails validation, reject the container. If metadata or cover fails validation, ignore that region and continue only if the ROM and footer are valid. A trusted ROM header has priority over conflicting metadata or filename hints.

## 7. Extraction

Write extraction output to a temporary file, verify its length and hash, then atomically rename it. A cache key may be `<rom_sha256>.<payload_format>`. The ROMX container itself remains the source of embedded metadata and cover.
