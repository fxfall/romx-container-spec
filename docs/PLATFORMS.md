# Platforms and Payload Formats

`platform` identifies the platform; `payload_format` identifies the standard ROM format delivered to the emulator core after extraction.

Use lowercase ASCII IDs. A new platform must define at least one payload format and a recognition strategy. Do not identify ambiguous formats such as `.bin` by extension alone.

The container extension is the original ROM extension plus `x`: `.gba` becomes `.gbax`, `.nes` becomes `.nesx`, and `.nds` becomes `.ndsx`. Readers must validate the ROMX footer.
