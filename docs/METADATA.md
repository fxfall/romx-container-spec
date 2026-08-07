# Metadata Reference

ROMX metadata is embedded UTF-8 JSON with no external path.

## Required fields

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Metadata schema version; v1 is `1.0` |
| `label` | string | Display title |
| `platform` | string | ROMX platform ID |
| `payload_format` | string | Extracted ROM format, without a dot |

Optional fields describe alternate titles, release data, ROM identifiers, hashes, and an embedded cover. The authoritative ROM SHA-256 is in the footer. Cover `mime_type` is always `image/png`.

## Optional fields

### Identity and titles

| Field | Type | Meaning |
|---|---|---|
| `sort_label` | string | Sort title |
| `original_label` | string | Original release title |
| `alternative_labels` | object | Language code to title map |
| `game_id` | string | Platform or database ID |
| `serial` | string | Cartridge or release serial |
| `version` | string | Game version or revision |

### Release information

| Field | Type | Meaning |
|---|---|---|
| `developer` | string | Developer |
| `publisher` | string | Publisher |
| `release_date` | string | ISO 8601 date, preferably `YYYY-MM-DD` |
| `genre` | string[] | Genre list |
| `region` | string[] | Region codes such as `USA`, `JPN`, `EUR` |
| `languages` | string[] | BCP 47 language tags |
| `players` | object | `min` and `max` players |
| `description` | string | Plain-text description |
| `tags` | string[] | User or tool tags |

### ROM information

| Field | Type | Meaning |
|---|---|---|
| `crc32` | string | Lowercase 8-digit hexadecimal |
| `md5` | string | Lowercase 32-digit hexadecimal |
| `sha1` | string | Lowercase 40-digit hexadecimal |
| `header_title` | string | Title read from the ROM header |
| `header_id` | string | Game code from the header |
| `dump_status` | string | `unknown`, `good`, `bad`, `overdump`, `hack`, `translation`, or `homebrew` |

### Cover

| Field | Type | Meaning |
|---|---|---|
| `cover` | object | Embedded cover description |
| `cover.mime_type` | string | Always `image/png` |
| `cover.width` | integer | Width in pixels |
| `cover.height` | integer | Height in pixels |
| `cover.sha256` | string | SHA-256 of cover bytes |
| `cover.source` | string | Human-readable source; never an automatic fetch instruction |

Non-standard fields must use the `x-` prefix. Metadata must not contain external paths, executable commands, credentials, or scripts.
