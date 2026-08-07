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

Non-standard fields must use the `x-` prefix. Metadata must not contain external paths, executable commands, credentials, or scripts.
