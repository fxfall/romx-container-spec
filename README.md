# ROMX

ROMX is an open ROM container specification for emulator frontends, game libraries, and archival workflows.

A ROMX file contains:

- an unmodified, directly loadable ROM payload;
- embedded UTF-8 metadata JSON;
- an optional embedded PNG cover;
- a fixed 128-byte footer with offsets, lengths, and SHA-256 values.

The container extension is the original ROM extension plus `x`: `.gba` becomes `.gbax`, `.nes` becomes `.nesx`, and `.nds` becomes `.ndsx`.

This repository defines ROMX 1.0 Draft 1. It contains the binary specification, metadata schema, platform rules, examples, and a small Python reference implementation.

## Documentation

- [Binary specification](docs/ROMX-SPEC.md)
- [Metadata reference](docs/METADATA.md)
- [Platforms and payload formats](docs/PLATFORMS.md)
- [Container structure](docs/FILE-STRUCTURE.md)
- [Metadata JSON Schema](schema/romx-metadata.schema.json)

## Reference implementation

The [Python reference implementation](tools/romx.py) demonstrates how to create, inspect, verify, and extract a ROMX file using only the Python standard library.

```bash
python3 tools/romx.py pack game.gba metadata.json -o game.gbax --cover cover.png
python3 tools/romx.py inspect game.gbax
python3 tools/romx.py verify game.gbax
python3 tools/romx.py extract game.gbax extracted/
```

The script is an implementation guide and validation aid, not a production packer.
