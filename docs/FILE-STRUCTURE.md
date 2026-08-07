# ROMX File Structure

## On-disk layout

```text
ROM payload | embedded metadata JSON | optional embedded PNG cover | 128-byte footer
```

This is the recommended write order, not a reader requirement. The footer is always last. Readers locate each region from `*_offset` and `*_size` and must reject overlapping regions or regions that reach into the footer.

## Repository layout

The repository contains the English specification in `docs/`, the normative metadata schema in `schema/`, sample metadata in `examples/`, and the reference implementation in `tools/romx.py`.
