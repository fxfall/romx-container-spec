# ROMX Metadata 1.0

Metadata is an optional UTF-8 JSON object embedded in the ROMX container. It is located by the footer and never by an external path. The normative field constraints are in `schema/romx-metadata.schema.json`.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Must be `1.0` |
| `label` | string | Display title |
| `platform` | string | Platform ID from `PLATFORMS.md` |
| `payload_format` | string | Extracted ROM format, without a leading dot |

## Optional fields

### Identity and release data

| Field | Type | Meaning |
|---|---|---|
| `sort_label` | string | Sort title |
| `original_label` | string | Original release title |
| `alternative_labels` | object | Language tag to title map |
| `game_id` | string | Platform or database identifier |
| `serial` | string | Cartridge or release serial |
| `version` | string | Game version or revision |
| `developer` | string | Developer |
| `publisher` | string | Publisher |
| `release_date` | string | `YYYY`, `YYYY-MM`, or `YYYY-MM-DD` |
| `genre` | string[] | Genre labels |
| `region` | string[] | Region codes |
| `languages` | string[] | BCP 47 language tags |
| `players` | object | Required `min` and `max` integers |
| `description` | string | Plain-text description |
| `tags` | string[] | User or tool labels |

### ROM and cover data

| Field | Type | Meaning |
|---|---|---|
| `crc32` | string | Lowercase 8-digit hexadecimal; the RetroArch/database lookup key |
| `header_title` | string | Title read from the ROM header |
| `header_id` | string | Identifier read from the ROM header |
| `dump_status` | string | One of the values defined by the schema |
| `cover` | object | Description of the embedded PNG |
| `cover.mime_type` | string | Always `image/png` |
| `cover.width` / `height` | integer | Pixel dimensions |
| `cover.sha256` | string | SHA-256 of embedded cover bytes |

`crc32` is used for RetroArch and ROM database lookup, normally together with ROM size. The authoritative ROM SHA-256 is in the footer for integrity and is not a database lookup key. MD5 and SHA-1 are intentionally not stored; providers that require another hash may calculate it on demand. The cover object does not contain a filesystem path, URL to fetch, command, credential, or script.

## Extensions

Non-standard fields must begin with `x-` and match the schema pattern. Readers may ignore unknown extensions but should preserve them when rewriting metadata.
