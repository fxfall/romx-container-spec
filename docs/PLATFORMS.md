# Platforms and Payload Formats

`platform` identifies the platform; `payload_format` identifies the standard ROM format delivered to the emulator core after extraction.

Use lowercase ASCII IDs. A new platform must define at least one payload format and a recognition strategy. Do not identify ambiguous formats such as `.bin` by extension alone.

| Platform | Payload format | Standard extension | Recognition hint |
|---|---|---|---|
| `gb` | `gb` | `.gb` | Nintendo logo, CGB flag |
| `gbc` | `gbc` | `.gbc` | Nintendo logo, CGB flag |
| `gba` | `gba` | `.gba` | GBA logo, fixed `0x96` |
| `nes` | `nes` | `.nes` | iNES/NES 2.0: `NES 1A` |
| `nes` | `fds` | `.fds` | `FDS 1A` header when present |
| `snes` | `sfc` | `.sfc` | LoROM/HiROM/ExHiROM internal header |
| `snes` | `smc` | `.smc` | May contain a 512-byte copier header |
| `nds` | `nds` | `.nds` | NDS header and Nintendo logo |
| `3ds` | `3ds` | `.3ds` | NCSD at offset `0x100` |
| `3ds` | `cci` | `.cci` | NCSD, same family as `.3ds` |
| `3ds` | `cia` | `.cia` | CIA section/header structure |
| `genesis` | `md` | `.md` | Usually `SEGA` at offset `0x100` |
| `genesis` | `gen` | `.gen` | Same family as `.md` |
| `genesis` | `smd` | `.smd` | Interleaved format, often with copier header |
| `genesis` | `bin` | `.bin` | Header inspection required; extension is ambiguous |

The container extension is the original ROM extension plus `x`: `.gba` becomes `.gbax`, `.nes` becomes `.nesx`, and `.nds` becomes `.ndsx`. Readers must validate the ROMX footer.
