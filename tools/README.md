# ROMX reference tool

`romx_reference.py` is a deterministic ROMX 0.2.0 writer and structural
inspector used to generate independent test inputs for container libraries.
It uses only the Python standard library and streams payload files.

It is not the end-user converter and does not perform image conversion,
online lookup, emulator selection, or automatic descriptor rewriting.

Examples:

```sh
python3 tools/romx_reference.py build game.romx \
  --entry game.nes=/path/to/game.nes \
  --platform NES \
  --launch-format RAW_SINGLE_FILE \
  --entry-crc32

python3 tools/romx_reference.py inspect game.romx --verify-entry-crc32
python3 tools/romx_reference.py fixtures tests/fixtures --force
```
