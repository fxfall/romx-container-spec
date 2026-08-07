# ROMX 1.0 Binary Specification

Status: Draft 1. Integer encoding: little-endian. Footer size: 128 bytes.

## Layout

A ROMX file contains an unmodified ROM payload, embedded UTF-8 metadata JSON, an optional embedded PNG cover, and a fixed footer. The footer is the final 128 bytes and locates every region.

## Footer

The footer stores `ROMX` magic, version `1`, offsets and sizes for ROM, metadata, and cover, the ROM SHA-256, flags, footer size, and an optional body SHA-256. All regions must be within the footer boundary and must not overlap.

Flags: bit 0 `HAS_METADATA`, bit 1 `HAS_COVER`, bit 2 `HAS_BODY_SHA256`; bits 3–31 are reserved and must be zero in v1.

## Payload and metadata

The payload must be directly loadable standard ROM data: no padding, header removal, byte swapping, or modification. Metadata is embedded in the container and located by `metadata_offset` and `metadata_size`; it has no external path. Unknown metadata fields may be preserved.

## Cover

v1 permits one embedded PNG cover. Validate its PNG signature and enforce size and dimension limits before decoding.

## Reading and errors

Readers must validate the footer, bounds, non-overlap, metadata and cover limits, then verify `rom_sha256` and (when flagged) `body_sha256`. Invalid ROM data or footer rejects the container; invalid metadata or cover may be ignored. A trusted ROM header takes precedence over conflicting metadata or filename hints.

## Atomic extraction

Extract to a temporary file, verify size and hashes, then atomically rename it. The emulator core receives only the extracted standard ROM.
