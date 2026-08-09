# ROMX 0.1.0 frozen fixtures

This directory is the language-neutral ROMX 0.1.0 conformance corpus. Every
`*.romx` file has a same-name `*.manifest.json` companion. The binary and its
manifest are frozen together: implementations must not silently regenerate,
normalize, or delete a fixture when running tests.

Reader fixtures are stored directly in this directory. Canonical writer golden
fixtures are stored in `writer/`.

Regenerate only from the checked-in deterministic source and then verify the
result before committing:

```bash
python3 tools/generate_fixtures.py --write
python3 tools/generate_fixtures.py --check
```

The manifest records the expected footer fields, payload and metadata lookup
CRC32 values, the optional body SHA-256, component statuses, and the expected
result of payload extraction. `ROMX_OK` and `ROMX_E_*` names are portable
expectation labels; implementations may map them to their own error type.

| Fixture | Required behavior |
| --- | --- |
| `minimal-valid` | One non-empty ROM byte region; metadata and cover absent; body SHA-256 disabled and zeroed. |
| `metadata-absent`, `cover-absent` | Each optional region can be absent independently. |
| `reordered-regions` | Footer offsets, not write order, identify ROM, metadata, and cover. |
| `footer-magic-invalid`, `footer-version-invalid`, `footer-size-invalid` | Reject invalid footer identity fields. |
| `offset-overflow`, `offset-out-of-bounds`, `regions-overlap` | Reject unsafe region arithmetic and layout. |
| `flags-mismatch` | Reject flags that disagree with optional region sizes. |
| `reserved-nonzero` | Ignore the ROMX 0.1.0 reserved bytes at `0x38`; new writers still zero them. |
| `body-sha256-disabled-nonzero` | Reject a nonzero body hash when its flag is clear. |
| `body-sha256-mismatch` | Reject an enabled body SHA-256 mismatch. |
| `metadata-bom`, `metadata-invalid-utf8`, `metadata-duplicate-key` | Mark metadata invalid without treating the optional region as ROM. |
| `metadata-crc32-lookup` | Accept a syntactically valid database lookup CRC32 without comparing it to the payload. |
| `cover-chunk-out-of-bounds`, `cover-chunk-crc-mismatch`, `cover-missing-iend` | Mark malformed PNG covers invalid. |
| `payload-salvage` | Preserve and extract the ROM even when metadata and cover are both invalid. |

Structural failures are rejected while opening the reader. Metadata and cover
failures are optional-region failures: a reader must still make the ROM payload
available when the footer is structurally valid and any enabled body SHA-256
check succeeds.

## Writer golden fixtures

Every file in `writer/` is an exact canonical writer result. Its manifest
records the logical writer input and options, the canonical region order,
every region's exact bytes, the complete file hex string, and the complete-file
SHA-256. Writer tests must compare the produced file byte-for-byte with the
checked-in `.romx`; the complete-file hash alone is not a substitute.

| Golden fixture | Required writer behavior |
| --- | --- |
| `payload-only` | Write only the unmodified payload and a footer; metadata and cover are absent. |
| `metadata-auto-crc32` | Calculate metadata `crc32` from the payload automatically. |
| `metadata-lookup-crc32-override` | Preserve the explicit database lookup CRC32 override. |
| `metadata-origin-crc32` | Replace enabled `origin_crc32` with the actual payload CRC32. |
| `cover` | Write canonical metadata followed by the exact PNG cover bytes. |
| `body-sha256-disabled`, `body-sha256-enabled` | Produce the exact disabled/enabled body-hash footer forms for the same logical input. |

All writer goldens use canonical `ROM | metadata | cover | footer` order,
little-endian footer integers, compact UTF-8 JSON without a BOM, zero in every
reserved byte, zero offsets for absent regions, and no unassigned body bytes.
