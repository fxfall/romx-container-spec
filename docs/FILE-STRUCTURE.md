# ROMX File Structure

## On-disk layout

```text
ROM payload | embedded metadata JSON | optional embedded PNG cover | 128-byte footer
```

This is the recommended write order, not a reader requirement. The footer is
always last. Readers locate each non-empty region from `*_offset` and `*_size`
and must reject overflow, out-of-bounds, or overlapping regions. If a region's
size is zero, its offset is ignored; writers must write that offset as zero.
The non-empty regions must cover every byte before the footer exactly once—no
body gaps or unassigned bytes are valid.

## Repository layout

The repository contains the English specification in `docs/`, the normative metadata schema in `schema/`, sample metadata in `examples/`, and the reference implementation in `tools/romx.py`.
