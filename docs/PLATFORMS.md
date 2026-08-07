# Platforms and Payload Formats

`platform` identifies a console family. `payload_format` identifies the standard ROM format delivered to the emulator core after extraction. Neither field modifies the payload or the footer.

| Platform | Payload format | Standard extension | Recognition hint |
|---|---|---|---|
| `gb` | `gb` | `.gb` | Nintendo logo and header flags |
| `gbc` | `gbc` | `.gbc` | Nintendo logo and CGB flag |
| `gba` | `gba` | `.gba` | GBA logo and fixed header value `0x96` |
| `nes` | `nes` | `.nes` | iNES/NES 2.0 magic `NES 1A` |
| `nes` | `fds` | `.fds` | FDS header `FDS 1A` when present |
| `snes` | `sfc` | `.sfc` | LoROM/HiROM/ExHiROM internal header |
| `snes` | `smc` | `.smc` | May contain a 512-byte copier header |
| `nds` | `nds` | `.nds` | Nintendo DS header and logo |
| `3ds` | `3ds` | `.3ds` | NCSD structure at offset `0x100` |
| `3ds` | `cci` | `.cci` | NCSD container, same family as `.3ds` |
| `3ds` | `cia` | `.cia` | CIA section/header structure |
| `genesis` | `md` | `.md` | Usually `SEGA` at offset `0x100` |
| `genesis` | `gen` | `.gen` | Same format family as `.md` |
| `genesis` | `smd` | `.smd` | Interleaved format, often with copier header |
| `genesis` | `bin` | `.bin` | Ambiguous; header inspection is required |

These hints are identification aids only. A reader must not claim a platform from an ambiguous extension alone. A trusted ROM header takes priority over metadata and filename hints.

### Game Boy CGB flag

For Game Boy payloads, inspect the CGB flag at ROM header offset `0x143`:

- `0xC0`: classify as `gbc` regardless of filename or playlist.
- `0x80`: the ROM is compatible with both GB and GBC. Use the valid ROMX `payload_format` (`gb` or `gbc`) as the classification; do not guess.
- Any other value: retain the already valid `payload_format` (`gb` or `gbc`); do not infer a new classification from that byte alone.

A missing or invalid `payload_format` makes a `0x80` ROM ambiguous and should be reported to the user.

The ROMX container extension is the original ROM extension plus `x`: `.gba` becomes `.gbax`, `.sfc` becomes `.sfcx`, and `.cia` becomes `.ciax`.
