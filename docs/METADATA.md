# ROMX 0.2.0 Metadata

Metadata is an optional strict UTF-8 JSON object whose size is stored in the
ROMX 0.2.0 footer and whose offset is derived from the fixed region order.
The normative field constraints are in
`schema/romx-metadata.schema.json`.

Unlike RIDX, metadata is descriptive. It must not contain physical offsets,
container lengths, host paths, launch paths, save paths, or cover paths.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Exactly `0.2.0` |
| `name` | string | Canonical display name |

Platform and launch format are not metadata. The footer's `platform_id` and
`launch_format_id`, together with the entrypoint RIDX `format_id`, remain
available when metadata is absent or invalid and are the only authoritative
declarations. A reader may expose their registered names without inserting
duplicate fields into the stored JSON.

## Optional database-compatible fields

| Field | Type | Meaning |
|---|---|---|
| `crc32` | string | Effective database lookup CRC32 |
| `origin_crc32` | string | Exact entrypoint CRC32 when that identity is meaningful |
| `serial` | string | Cartridge, release, or disc serial |
| `developer` | string | Developer |
| `publisher` | string | Publisher |
| `origin` | string | Country or region of development/origin |
| `franchise` | string | Franchise or series name |
| `release_date` | string | `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `genre` | string[] | Genre labels |
| `region` | string[] | Release regions |
| `language` | string | Language information |
| `users` | integer | Maximum supported users |
| `coop` | boolean | Cooperative play is supported |
| `rumble` | boolean | Rumble is supported |
| `analog` | boolean | Analog input is supported |
| `enhancement_hw` | string | Required or supported enhancement hardware |
| `category` | string | Content category |
| `media` | string | Original media type |
| `description` | string | Plain-text description |
| `dump_status` | string | Source-dump provenance hint |
| `cover` | object | Embedded PNG description |

`crc32` is a lookup aid, not a structural integrity field. It is optional in
ROMX 0.2.0 because many optical and multi-file databases use a serial or another
platform-specific identity. A RIDX entry may independently carry an optional
integrity CRC32 under `HAS_CRC32`; that value is not a database identity. For a
multi-file set, `origin_crc32` should be omitted unless it unambiguously
describes the entrypoint bytes.

`dump_status` may be `unknown`, `good`, `bad`, `overdump`, `hack`,
`translation`, or `homebrew`. It does not replace a present RIDX CRC32, footer
CRC32, or the optional immutable SHA-256 and must not be an automatic
launch-rejection rule.

The closed `cover` object may contain only `mime_type` (`image/png`), `width`,
and `height`. It describes the embedded cover bytes and is not a URL, path, or
integrity record.

Database, playlist, frontend, and runtime mappings are outside the ROMX 0.2.0
container standard. They must not introduce duplicate platform/format fields
or host paths into stored metadata. Platform and format come from footer/RIDX;
persistent save, cheat, statistics, and private keys belong to the mutable
object store.

## JSON validity

JSON follows RFC 8259, has no BOM, and must contain unique member names at
every object depth. Unpaired escaped UTF-16 surrogates are invalid. Unknown
properties are rejected by the closed schema.
