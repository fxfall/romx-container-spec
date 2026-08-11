# ROMX 0.1.1 frontend integration profile

ROMX 0.1.1 is a frontend integration profile for the frozen ROMX 0.1.0 wire
format. It introduces no new container bytes and remains compatible with every
valid 0.1.0 file.

Frontends must identify a container from its validated footer and region
structure, independently from optional metadata and cover validation. Invalid,
absent, or unsupported optional metadata must not cause the complete container
to be passed to an emulator core and must not prevent access to a structurally
valid payload.

For cores that accept an in-memory content buffer, frontends should expose only
the exact payload range. A guarded mapping may map aligned payload pages and
copy only partial boundary pages. Its lifetime must follow the core's declared
`persistent_data` requirement.

For path-based cores using frontend VFS, virtual offset zero maps to
`rom_offset`, virtual size is exactly `rom_size`, and no read may expose another
container region. File extraction is a compatibility fallback, not the default
integration mode.

Body SHA-256 remains optional and disabled by default. When present it is
normative and must be checked before exposing the payload. When absent, a
frontend must not force a complete payload scan merely to start content.

The profile reserves no ROMX 0.2.0 virtual-tree bytes or metadata fields.
Multi-file payload containers require a new wire-format version.
