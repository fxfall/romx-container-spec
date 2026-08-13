# ROMX 0.1.0 Binary Specification

**Status: ROMX 0.1.0 — stable and frozen.** This document is the first frozen
baseline; the rules below are established before compatibility commitments.

Integer encoding is unsigned little-endian. The footer is exactly 128 bytes.
This document defines the byte semantics of the ROMX 0.1.0 container; the
metadata schema is versioned separately.

## 1. Container layout

The file contains three independently addressable regions followed by the
fixed footer:

```text
ROM payload | metadata JSON | optional PNG cover | 128-byte footer
```

The order is only the recommended writer order. Readers use footer offsets and
sizes and must accept any order. The ROM payload is copied byte-for-byte; the
container does not add a ROM header or modify the payload. Metadata and cover
are embedded bytes and never contain an external path. A core receives the
extracted ROM payload, not the container.

Every byte from offset zero through the byte immediately before the footer
must belong to exactly one non-empty region. Regions must therefore form a
complete, non-overlapping partition of the body: no gaps, overlaps, or bytes
outside all three regions are valid.

## 2. Footer

All footer integers are unsigned little-endian.

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `ROMX` |
| `0x04` | 4 | uint32 | `version` | Wire value `1`, identifying ROMX 0.1.0 |
| `0x08` | 8 | uint64 | `rom_offset` | Start of ROM payload |
| `0x10` | 8 | uint64 | `rom_size` | Greater than zero |
| `0x18` | 8 | uint64 | `metadata_offset` | Start of metadata when present |
| `0x20` | 8 | uint64 | `metadata_size` | Zero means absent |
| `0x28` | 8 | uint64 | `cover_offset` | Start of cover when present |
| `0x30` | 8 | uint64 | `cover_size` | Zero means absent |
| `0x38` | 32 | bytes | `reserved` | Ignored by readers; zero in new output |
| `0x58` | 4 | uint32 | `flags` | Feature flags |
| `0x5C` | 4 | uint32 | `footer_size` | Exactly `128` |
| `0x60` | 32 | bytes | `body_sha256` | Optional SHA-256 of all bytes before footer |

When `metadata_size == 0`, a reader must completely ignore
`metadata_offset`; a writer must write `metadata_offset == 0`. The same rule
applies to `cover_size == 0` and `cover_offset`. A non-empty region must be
within the body and must not overlap another non-empty region. The complete
body-partition rule in section 1 is additionally required.

`body_sha256` is the only hash stored in the footer. If `HAS_BODY_SHA256` is
clear, it must be 32 zero bytes. If set, it covers every body byte and a
mismatch makes the container structurally invalid. The 32-byte `reserved`
field has no ROM SHA-256 meaning in ROMX 0.1.0.

The footer `version` is a wire compatibility code, not a semantic version
number: ROMX 0.1.0 uses the value `1`. It must not be interpreted as ROMX 1.x.

### Flags

| Bit | Name | Meaning |
|---:|---|---|
| 0 | `HAS_METADATA` | `metadata_size > 0` |
| 1 | `HAS_COVER` | `cover_size > 0` |
| 2 | `HAS_BODY_SHA256` | `body_sha256` is present and checked |
| 3–31 | Reserved | Must be zero |

Flags and optional-region sizes must agree. Compression, encryption, or a
different footer layout requires a new format version.

## 3. ROM payload and CRC32

The payload must be the exact ROM bytes accepted by the target emulator core.
Writers must not pad, strip headers, byte-swap, patch, or otherwise modify it.
The container extension is the original ROM extension plus `x` (for example,
`.gba` becomes `.gbax`).

ROMX `crc32` uses the same CRC-32/ISO-HDLC parameters and byte ordering used by
RetroArch's CRC matching:

- polynomial `0x04C11DB7` (reflected implementation `0xEDB88320`);
- initial register `0xFFFFFFFF`;
- reflected input and output (`RefIn=true`, `RefOut=true`);
- final XOR `0xFFFFFFFF`;
- no augmentation or byte reversal beyond the reflected algorithm.

The canonical serialized form is exactly eight lower-case hexadecimal digits,
without `0x` (the test vector `123456789` is `cbf43926`). `metadata.crc32`
is the effective database lookup value. A writer generates it from the exact
payload by default; a caller may explicitly override it for database matching.
`origin_crc32`, when present, is the exact payload CRC and is optional. Neither
field is a replacement for the optional body SHA-256.

## 4. Metadata region

Metadata is optional JSON encoded as strict UTF-8 without a BOM. Parsing and
validation follow RFC 8259. Every JSON object at every nesting level must have
unique member names; duplicate keys are invalid, not “last key wins”. Escaped
unpaired UTF-16 surrogates are invalid; a valid surrogate pair is accepted as
one Unicode scalar. The JSON
top-level value must be an object conforming to
`schema/romx-metadata.schema.json`. That schema has
`additionalProperties: false`; unknown ROMX 0.1.0 fields are invalid. Invalid
metadata may be ignored for payload extraction after the footer and enabled
body SHA have passed.

The `cover` member, when present, is an object with only these optional
properties: `mime_type` (`"image/png"`), `width` (integer 1–8192), and
`height` (integer 1–8192). Its schema also has `additionalProperties: false`.
It is descriptive metadata, not a path, URL, or cover checksum. Cover bytes
are validated by the PNG profile in section 5.

## 5. Cover PNG profile

The optional cover is one PNG byte stream. Implementations must validate the
signature, every chunk boundary, and every chunk CRC before accepting it. The
ROMX profile imposes these additional rules:

1. `IHDR` is the first chunk, has length 13, and occurs exactly once.
2. IHDR width and height are non-zero and within the implementation limit
   (the reference limit is 8192); compression method and filter method are 0,
   and interlace method is 0 or 1.
3. The color-type/bit-depth combinations are exactly: color 0 → 1/2/4/8/16;
   color 2 → 8/16; color 3 → 1/2/4/8; color 4 → 8/16; color 6 → 8/16.
   Other combinations are invalid.
4. `IDAT` must exist. All IDAT chunks must be consecutive. A palette image
   (color type 3) must contain one valid `PLTE` before IDAT; PLTE is forbidden
   for grayscale and grayscale-alpha images and must have a non-zero length
   divisible by three and no more than 768 bytes.
5. `IEND` must exist, have zero data length, and be the final chunk. Bytes
   after IEND are not allowed. A second IEND is therefore invalid.

Unknown critical chunks are invalid; ancillary chunks are allowed subject to
the boundary and CRC rules. A malformed cover does not prevent extraction of a
valid ROM payload.

## 6. Reader validation and extraction

Readers validate footer size/magic/version, integer overflow and bounds,
flags, overlaps, and complete body coverage before reading optional regions.
For an absent region, its offset is ignored. Metadata validation then checks
strict UTF-8, no BOM, RFC 8259 JSON, recursive duplicate-key rejection, and
the metadata schema. Cover validation applies section 5. If body SHA is
enabled, every byte before the footer is hashed and compared.

Footer or enabled-body-SHA failures reject the container. Invalid optional
metadata or cover may be reported and skipped while the payload remains
extractable. Extraction should use a temporary file, verify the byte count,
and atomically rename the result. A frontend may use `<crc32>.<payload_format>`
as a cache key.

## 7. Version and schema evolution

The ROMX 0.1.0 binary format is frozen. A binary compatibility change may only
add conformance fixtures or clarify wording without changing byte semantics.
Changing the footer layout, a footer field's meaning, region semantics, or a
binary validity rule requires a new format version (for example, ROMX 0.2.0);
a ROMX 0.1.0 reader must reject that version.

The metadata schema evolves independently from the container. Its
`schema_version` identifies the metadata contract while the footer wire
`version` identifies the binary container. The baseline registry uses
`schema_version: "0.1.0"`; its backward-compatible extension uses `0.1.1`.
The 0.1.1 schema accepts both versions, and a 0.1.1-aware reader MUST validate
and accept every valid 0.1.0 metadata document. Writers emit the version of the
registry they use and MUST NOT relabel unchanged metadata merely while reading
or copying it. A reader that does not understand a later schema may treat the
metadata as unsupported/invalid but may still extract the payload. A change
that affects footer bytes, region semantics, or binary validity cannot be
carried by a metadata schema version and must use a new ROMX format version.

## 8. Frozen conformance fixtures

`tests/fixtures/` contains a language-neutral frozen reader corpus, while
`tests/fixtures/writer/` contains the byte-exact canonical writer golden corpus.
Every `.romx` has a same-name `.manifest.json`. Readers should run the reader
corpus and writers should compare their output byte-for-byte with the writer
goldens without rewriting existing fixture bytes during tests.
