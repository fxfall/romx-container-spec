# ROMX 1.0 Binary Specification

Status: Draft 1. Integer encoding: little-endian. Footer size: 128 bytes.

## Layout

A ROMX file contains an unmodified ROM payload, embedded UTF-8 metadata JSON, an optional embedded PNG cover, and a fixed footer. The footer is the final 128 bytes and locates every region.

## Footer

| Offset | Size | Type | Field | Meaning |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `ROMX` |
| `0x04` | 4 | uint32 | `version` | Must be `1` in v1 |
| `0x08` | 8 | uint64 | `rom_offset` | ROM start |
| `0x10` | 8 | uint64 | `rom_size` | ROM byte count, greater than 0 |
| `0x18` | 8 | uint64 | `metadata_offset` | Metadata start |
| `0x20` | 8 | uint64 | `metadata_size` | Zero means absent |
| `0x28` | 8 | uint64 | `cover_offset` | Cover start |
| `0x30` | 8 | uint64 | `cover_size` | Zero means absent |
| `0x38` | 32 | bytes | `rom_sha256` | SHA-256 of the original ROM |
| `0x58` | 4 | uint32 | `flags` | Feature flags |
| `0x5C` | 4 | uint32 | `footer_size` | Must be `128` in v1 |
| `0x60` | 32 | bytes | `body_sha256` | SHA-256 of all bytes before footer; all zero when disabled |

Flags: bit 0 `HAS_METADATA`, bit 1 `HAS_COVER`, bit 2 `HAS_BODY_SHA256`; bits 3–31 are reserved and must be zero in v1.

v1 does not support ROM compression or encryption. Such changes require a new major version or an explicit capability that old readers cannot misinterpret.

## Payload and metadata

The payload must be directly loadable standard ROM data: no padding, header removal, byte swapping, or modification. Metadata is embedded in the container and located by `metadata_offset` and `metadata_size`; it has no external path. Unknown metadata fields may be preserved.

## Cover

v1 permits one embedded PNG cover. Validate its PNG signature and enforce size and dimension limits before decoding.

Recommended limits are 32 MiB and an 8192-pixel maximum dimension.

## Reading and errors

Readers must validate the footer, bounds, non-overlap, metadata and cover limits, then verify `rom_sha256` and (when flagged) `body_sha256`. Invalid ROM data or footer rejects the container; invalid metadata or cover may be ignored. A trusted ROM header takes precedence over conflicting metadata or filename hints.

## Atomic extraction

Extract to a temporary file, verify size and hashes, then atomically rename it. The emulator core receives only the extracted standard ROM.

Suggested cache key: `<rom_sha256>.<payload_format>`.
