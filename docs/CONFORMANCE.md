# ROMX 1.0 conformance fixtures

The repository ships a frozen corpus in [`tests/fixtures`](../tests/fixtures/).
It is intended to be consumed by libromx, ROMX Core, the Python reference
implementation, and independent readers.

Each fixture is a pair:

```text
<name>.romx
<name>.manifest.json
```

The manifest is authoritative for the test expectation. It contains:

- `expected.reader_open`: whether the footer and region table are accepted;
- `expected.validate_all`: the result after optional metadata and cover checks;
- `expected.footer`: every v1 footer field that is relevant to the fixture;
- `expected.crc32`: the computed payload value, metadata lookup value, and its database-lookup semantics;
- `expected.sha256`: the computed and footer body hashes;
- `expected.components`: structure, optional body hash, metadata, CRC32 syntax, and cover statuses;
- `expected.payload_extraction`: whether the payload must remain extractable;
- `expected.payload_salvage`: whether optional-region errors are deliberately recoverable.

The suite is deliberately small and deterministic. Its payload is `abc` and
its valid cover is a 1x1 RGBA PNG, so no copyrighted game or image assets are
needed. The generator is only a reproducibility aid; the checked-in bytes are
the fixtures that compatibility tests must use.

Implementations should reject invalid footer structure before reading optional
regions. Malformed metadata or PNG cover data must not make the ROM payload
unavailable. Metadata `crc32` is a database lookup value and is not compared
with the payload automatically. A disabled body SHA-256 uses a clear flag and
32 zero bytes; an enabled mismatch rejects the container. The 32 bytes at
`0x38` are reserved: readers ignore them and new writers zero them.

The `metadata-absent-nonzero-offset` and `cover-absent-nonzero-offset` fixtures
confirm that a zero-sized region's offset is ignored and normalized by readers.
The `regions-gap` fixture confirms that bytes before the footer cannot fall
outside all declared regions. The `metadata-nested-duplicate-key` fixture
exercises duplicate-key rejection inside a nested JSON object. PNG fixtures
exercise chunk bounds and CRCs;
implementations must also enforce the ROMX PNG profile in the binary
specification (first/unique IHDR, required consecutive IDAT, legal
color/depth, and final IEND with no trailing bytes).

Run the source/fixture byte-for-byte check with:

```bash
python3 tools/generate_fixtures.py --check
```

## Writer golden fixtures

`tests/fixtures/writer/` stores byte-exact golden results for a canonical
writer. Each manifest records logical inputs and options under `input`, layout
and encoding rules under `canonical`, and exact regions, footer, complete-file
hex, and complete-file SHA-256 under `expected`. Tests must compare writer
output byte-for-byte with the `.romx`; checking only the digest is insufficient.

The goldens cover payload-only output, automatic metadata CRC32, a lookup CRC32
override, `origin_crc32` derived from the actual payload, cover output, and body
SHA-256 both disabled and enabled. They all use canonical
`ROM | metadata | cover | footer` order, zero offsets for absent regions,
compact BOM-free UTF-8 JSON, little-endian footer integers, and zero in every
reserved byte.
