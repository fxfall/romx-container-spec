# ROMX 0.2.0 Container Specification

**Status: active development, not frozen.** ROMX 0.2.0 defines footer wire
version `2` and metadata schema version `0.2.0`. Byte semantics may change
until the project explicitly freezes the format.

A reader must validate the footer wire version before interpreting any
version-dependent field.

All integers are unsigned little-endian. Unless a section says otherwise, all
reserved fields and reserved flag bits must be zero in new files and must be
rejected when non-zero.

## 1. Design model

ROMX 0.2.0 separates immutable game content from mutable user data:

```text
payload data
payload index
optional metadata JSON
optional PNG cover
optional zero alignment padding
fixed-capacity mutable region
128-byte footer
```

The physical order above is mandatory. The payload is an uncompressed
concatenation of one or more source files. The payload index is the
authoritative virtual-file directory. Metadata describes the game, but it
never contains byte offsets or host paths.

The compact footer stores only values that cannot be derived from the fixed
layout. A mutable region has a fixed object directory and fixed-capacity object
extents. Explicit updates may overwrite those extents without modifying or
relocating the footer, payload, payload index, metadata, or cover.

## 2. Top-level layout and partition rules

The payload starts at file offset zero. RIDX begins at `payload_size` and its
size is derived from its validated `entry_count`. Metadata, cover, alignment
padding, and the mutable region follow in that order when present. The footer
occupies the final 128 bytes.

Every byte before the footer belongs to exactly one of the following:

- payload data or zero payload-alignment padding;
- payload index;
- metadata;
- cover;
- zero immutable-alignment padding;
- mutable region.

Regions and checked integer additions must not overflow, overlap, or extend
past the footer. The only permitted gaps are the zero padding explicitly
described by this specification.

When a mutable region is present, `mutable_offset` must be aligned to 4096
bytes. Zero bytes between the end of the cover (or the previous present
region) and `mutable_offset` are immutable alignment padding. When no mutable
region is present, no top-level trailing padding is allowed.

The following checked equations are normative:

- `payload_offset == 0` and `payload_index_offset == payload_size`;
- `payload_index_size == 64 + entry_count * 512` and
  `index_end == payload_size + payload_index_size`;
- `metadata_offset == index_end` when `metadata_size > 0`;
- `cover_offset == index_end + metadata_size` when `cover_size > 0`;
- `immutable_content_end == index_end + metadata_size + cover_size`;
- when `mutable_capacity > 0`, `mutable_offset == footer_offset -
  mutable_capacity`, `mutable_offset == align_up(immutable_content_end, 4096)`,
  and `mutable_capacity` is a multiple of 4096 and at least 12288 bytes;
- when `mutable_capacity == 0`, no mutable region exists and
  `footer_offset == immutable_content_end`.

Offsets named above are derived values, not footer fields. A zero metadata or
cover size means that region is absent and no offset is interpreted for it.
Metadata remains one strict JSON byte sequence and cover remains one PNG byte
sequence, matching the established ROMX region model; neither is a RIDX entry.

## 3. Footer

The footer is exactly 128 bytes at end of file.

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `ROMX` |
| `0x04` | 4 | uint32 | `wire_version` | Exactly `2` |
| `0x08` | 8 | uint64 | `payload_size` | Greater than zero; RIDX starts here |
| `0x10` | 8 | uint64 | `metadata_size` | Zero means absent |
| `0x18` | 8 | uint64 | `cover_size` | Zero means absent |
| `0x20` | 8 | uint64 | `mutable_capacity` | Fixed physical size; zero means absent |
| `0x28` | 2 | uint16 | `platform_id` | Section 3.2 platform registry |
| `0x2A` | 2 | uint16 | `launch_format_id` | Section 3.3 launch registry |
| `0x2C` | 4 | uint32 | `immutable_hash_algorithm` | Section 3.1 |
| `0x30` | 32 | bytes | `immutable_sha256` | SHA-256 or all zero |
| `0x50` | 4 | uint32 | `footer_crc32` | CRC32 of the complete footer |
| `0x54` | 44 | bytes | `reserved` | All zero; reserved for future wire versions |

To calculate `footer_crc32`, treat bytes `0x50..0x53` as zero and calculate
the CRC32 defined in section 8 over all 128 footer bytes, including the
reserved bytes.

### 3.1 Immutable hash algorithm

| Value | Name | Requirement |
|---:|---|---|
| `0` | `NONE` | `immutable_sha256` is 32 zero bytes; no immutable hash is claimed |
| `1` | `SHA256` | Validate `immutable_sha256` over the immutable range |

Other values are invalid in ROMX 0.2.0. The immutable range is
`[0, mutable_offset)` when `mutable_capacity > 0`, otherwise
`[0, footer_offset)`. It never covers the mutable region or footer.

ROMX 0.2.0 writers must zero all 44 reserved bytes and ROMX 0.2.0 readers must
reject a footer when any is non-zero. A future definition may assign them only
under a new footer wire version.

### 3.2 Platform registry

`platform_id` is the authoritative platform classification. Metadata does not
duplicate it.

| Value | Name | Platform |
|---:|---|---|
| `0x0000` | `UNSPECIFIED` | No reliable platform declaration |
| `0x0001` | `GAME_BOY` | Game Boy |
| `0x0002` | `GAME_BOY_COLOR` | Game Boy Color |
| `0x0003` | `GAME_BOY_ADVANCE` | Game Boy Advance |
| `0x0004` | `NES` | Nintendo Entertainment System / Famicom |
| `0x0005` | `SNES` | Super Nintendo / Super Famicom |
| `0x0006` | `NINTENDO_64` | Nintendo 64 |
| `0x0007` | `NINTENDO_DS` | Nintendo DS |
| `0x0008` | `NINTENDO_3DS` | Nintendo 3DS |
| `0x0010` | `MASTER_SYSTEM` | Sega Master System |
| `0x0011` | `GAME_GEAR` | Sega Game Gear |
| `0x0012` | `MEGA_DRIVE` | Mega Drive / Genesis |
| `0x0013` | `MEGA_DRIVE_32X` | Mega Drive 32X |
| `0x0014` | `SEGA_CD` | Sega CD / Mega-CD |
| `0x0015` | `SEGA_SATURN` | Sega Saturn |
| `0x0016` | `DREAMCAST` | Sega Dreamcast |
| `0x0020` | `PC_ENGINE` | PC Engine / TurboGrafx-16 |
| `0x0021` | `PC_ENGINE_CD` | PC Engine CD / TurboGrafx-CD |
| `0x0030` | `PLAYSTATION` | Sony PlayStation |
| `0x0031` | `PLAYSTATION_2` | Sony PlayStation 2 |
| `0x0032` | `PSP` | PlayStation Portable |
| `0x0040` | `GAMECUBE` | Nintendo GameCube |
| `0x0041` | `WII` | Nintendo Wii |
| `0x0050` | `ARCADE` | Arcade ROM set |
| `0x0060` | `SCUMMVM` | ScummVM game data |
| `0x0061` | `DOS` | DOS game data |
| `0x0062` | `AMIGA` | Amiga game data |

`0x0000` never means “auto-detect.” It leaves the declaration unresolved. A
reader may return a separately labelled detection guess, but the guess is not
a stored declaration. A normal launchable writer must use a registered
non-zero value; `UNSPECIFIED` is allowed only for import, recovery, or
intentionally unclassified content.

### 3.3 Launch-format registry

`launch_format_id` describes how the RIDX entrypoint and its related entries
form loadable content. It does not replace the entrypoint's `format_id`.

| Value | Name | Meaning |
|---:|---|---|
| `0x0000` | `UNSPECIFIED` | No reliable launch contract |
| `0x0001` | `RAW_SINGLE_FILE` | Entrypoint itself is the complete logical launch file |
| `0x0002` | `CUE` | CUE descriptor plus referenced files |
| `0x0003` | `GDI` | GDI descriptor plus referenced tracks |
| `0x0004` | `M3U` | Multi-disc playlist plus referenced disc entrypoints |
| `0x0005` | `CCD` | CloneCD descriptor set |
| `0x0006` | `MDS` | Media Descriptor set |
| `0x0007` | `TOC` | TOC descriptor plus referenced files |
| `0x0008` | `DIRECTORY` | Indexed directory with a ROMX launch descriptor |
| `0x0009` | `ROMSET` | Expanded arcade ROM set and logical dependencies |
| `0x000A` | `SPLIT_FILE_SET` | One logical image split across indexed files |

ISO, CSO, ZSO, CHD, PBP, CDI, RVZ, WIA, and other self-contained images use
`RAW_SINGLE_FILE`; their exact format comes from the entrypoint RIDX entry.
`UNSPECIFIED` has the same unresolved-launch behavior as an unspecified
platform and is not an auto-detection instruction.

### 3.4 Registry ranges and unknown values

The platform, launch-format, and RIDX file-format registries all reserve:

| Range | Meaning |
|---:|---|
| `0x0000` | Unspecified or unknown, as defined by that field |
| `0x0001–0x7FFF` | ROMX standard registry |
| `0x8000–0xFFFE` | Private or experimental use |
| `0xFFFF` | Permanently prohibited |

Registered values are never reassigned. Adding a value does not change the
meaning of earlier values. An unknown value other than `0xFFFF` does not by
itself make the container structurally corrupt: a reader may still validate
and expose its files, but must report an unsupported platform or format. A
private value is interoperable only when the producer and consumer share its
definition.

## 4. Payload and RIDX payload index

Payload bytes are never compressed, encrypted, patched, byte-swapped, or
rewritten by the container. Each embedded source file occupies one indexed
byte range. Writers may insert zero padding between entries for alignment;
all unindexed bytes in the payload region must be zero.

ROMX adds no header, prefix, marker, alignment byte, or other container-owned
byte before the payload. The entrypoint must begin at absolute file offset
zero, so its first byte is exactly the first byte of the stored source file.
Alignment padding is permitted only after an indexed file, never before the
entrypoint. RIDX and every other ROMX structure follow the payload.

The payload index consists of a 64-byte header followed immediately by
`entry_count` fixed 512-byte entries. Each entry contains its own UTF-8 virtual
path. There is no separate string table, no entry ID namespace, and no free or
unused RIDX slot.

### 4.1 RIDX header

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `RIDX` |
| `0x04` | 2 | uint16 | `index_version` | Exactly `1` |
| `0x06` | 2 | uint16 | `header_size` | Exactly `64` |
| `0x08` | 4 | uint32 | `entry_count` | At least one |
| `0x0C` | 4 | uint32 | `entry_size` | Exactly `512` |
| `0x10` | 4 | uint32 | `flags` | Zero in ROMX 0.2.0 |
| `0x14` | 4 | uint32 | `index_crc32` | CRC32 of the complete index |
| `0x18` | 40 | bytes | `reserved` | All zero |

For `index_crc32`, treat bytes `0x14..0x17` as zero and calculate CRC32 over
the complete payload-index region. `payload_index_size` must equal exactly
`64 + entry_count * 512`, using checked arithmetic; no bytes may follow the
last entry inside the region.

### 4.2 RIDX entry

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | uint32 | `flags` | Section 4.3 |
| `0x04` | 2 | uint16 | `format_id` | Section 4.4 file-format registry |
| `0x06` | 2 | uint16 | `path_size` | UTF-8 byte length, 1–480 |
| `0x08` | 8 | uint64 | `data_offset` | Relative to payload start |
| `0x10` | 8 | uint64 | `data_size` | Embedded byte length |
| `0x18` | 4 | uint32 | `crc32` | Optional CRC32 of exactly the embedded bytes |
| `0x1C` | 4 | uint32 | `reserved` | Zero |
| `0x20` | 480 | bytes | `path` | `path_size` bytes followed by zero padding |

All non-empty embedded ranges must be inside the payload and must not overlap.
An embedded empty file has `data_size == 0` and an in-bounds `data_offset`.
Every byte after `path_size` in `path` must be zero. Exactly one entry must be
the entrypoint. It must have `data_offset == 0`, `data_size > 0`, and a non-zero
`format_id`.

Every RIDX entry describes bytes physically present in the payload. ROMX does
not represent external dependencies in RIDX. Required firmware, shared BIOS,
parent-set content, device ROMs, and other runtime dependencies are resolved
by the consumer and are outside the container format.

### 4.3 Entry flags

| Bit | Name | Meaning |
|---:|---|---|
| 0 | `ENTRYPOINT` | This is the single launch entry |
| 1 | `HAS_CRC32` | `crc32` contains the CRC32 of exactly this entry's bytes |
| 2–31 | Reserved | Zero |

Exactly one entry has `ENTRYPOINT`; all others clear it. When `HAS_CRC32` is
set, `crc32` is mandatory and is validated using section 8, including for an
empty file whose CRC32 is `00000000`. When `HAS_CRC32` is clear, `crc32` must
be zero and the entry has no stored checksum. A zero CRC32 is therefore
unambiguous: it is a checksum only when `HAS_CRC32` is set.

### 4.4 RIDX file-format registry

`format_id` is the authoritative format of one RIDX entry. The virtual path
retains the original filename and extension as part of the container's virtual
file tree.

| Value | Name | Typical extension or role |
|---:|---|---|
| `0x0000` | `UNKNOWN` | Unidentified non-entrypoint file |
| `0x0001` | `GB` | `.gb` |
| `0x0002` | `GBC` | `.gbc` |
| `0x0003` | `GBA` | `.gba` |
| `0x0004` | `NES` | `.nes` |
| `0x0005` | `UNF` | `.unf` |
| `0x0006` | `UNIF` | `.unif` |
| `0x0007` | `FDS` | `.fds` |
| `0x0008` | `SFC` | `.sfc` |
| `0x0009` | `SMC` | `.smc` |
| `0x000A` | `NDS` | `.nds` |
| `0x000B` | `N3DS` | `.3ds` |
| `0x000C` | `CCI` | `.cci` |
| `0x000D` | `CXI` | `.cxi` |
| `0x000E` | `APP` | `.app` |
| `0x0010` | `ISO` | `.iso` |
| `0x0011` | `CSO` | `.cso` |
| `0x0012` | `ZSO` | `.zso` |
| `0x0013` | `CHD` | `.chd` |
| `0x0014` | `PBP` | `.pbp` |
| `0x0015` | `CDI` | `.cdi` |
| `0x0016` | `GCM` | `.gcm` |
| `0x0017` | `WBFS` | `.wbfs`, `.wbf1`, and later segments |
| `0x0018` | `RVZ` | `.rvz` |
| `0x0019` | `WIA` | `.wia` |
| `0x001A` | `WAD` | `.wad` |
| `0x0020` | `CUE` | `.cue` |
| `0x0021` | `GDI` | `.gdi` |
| `0x0022` | `M3U` | `.m3u` |
| `0x0023` | `CCD` | `.ccd` |
| `0x0024` | `MDS` | `.mds` |
| `0x0025` | `TOC` | `.toc` |
| `0x0030` | `BIN` | `.bin` track |
| `0x0031` | `WAV` | `.wav` audio track |
| `0x0032` | `FLAC` | `.flac` audio track |
| `0x0033` | `IMG` | `.img` image or track |
| `0x0034` | `MDF` | `.mdf` image |
| `0x0040` | `SBI` | `.sbi` sidecar |
| `0x0041` | `SUB` | `.sub` sidecar |
| `0x0042` | `ECM` | `.ecm` sidecar or encoded track |
| `0x0050` | `Z64` | `.z64` |
| `0x0051` | `N64` | `.n64` |
| `0x0052` | `V64` | `.v64` |
| `0x0060` | `MD` | `.md` |
| `0x0061` | `GEN` | `.gen` |
| `0x0062` | `SMD` | `.smd` |
| `0x0063` | `X32` | `.32x` |
| `0x0064` | `SMS` | `.sms` |
| `0x0065` | `GG` | `.gg` |
| `0x0066` | `PCE` | `.pce` |
| `0x0070` | `ELF` | `.elf` |
| `0x0071` | `PRX` | `.prx` |
| `0x0080` | `MSU` | `.msu` |
| `0x0081` | `PCM` | `.pcm` |
| `0x0090` | `ROMX_LAUNCH_DESCRIPTOR` | Generated launch descriptor for a virtual directory or ROM set |

`UNKNOWN` is allowed for a non-entrypoint auxiliary file. A launch entrypoint
must use a non-zero standard or private value. `0xFFFF` is always invalid.

### 4.5 Paths, descriptors, and entrypoint

Paths use strict UTF-8, Unicode NFC, and `/` separators. They must be relative
and must not contain NUL, backslash, empty components, `.` or `..` components,
a leading slash, or a trailing slash. No two paths may collide after Unicode
case folding. A path occupies the first `path_size` bytes of its entry's
fixed path field and is not NUL-terminated.

Descriptors stored as entrypoints must reference other entries by normalized
relative path. A writer importing an absolute or otherwise non-portable CUE,
GDI, or M3U should preserve the original as a non-entrypoint auxiliary file
when desired and create a normalized launch descriptor as the entrypoint.

For a single-file game, the entrypoint is that file. For a multi-file game,
the entrypoint is normally CUE, GDI, M3U, CCD, MDS, TOC, or another descriptor.
A `.chd`, `.pbp`, `.cdi`, `.iso`, `.rvz`, or similar self-contained image
remains one entry and must not be split merely because its internal filesystem
contains multiple files.

For a single-file container, `entry_count == 1`, the sole entry has
`ENTRYPOINT`, `data_offset == 0`, and `data_size == payload_size`. The payload
contains no alignment padding. For a multi-file container, `entry_count > 1`
and this state is derived from RIDX rather than duplicated in the footer.
These rules allow a reader to expose a single-file payload directly while
retaining the same RIDX parsing model.

Every ROMX 0.2.0 container uses the single `.romx` extension. Original
filenames and extensions exist only in RIDX virtual paths. A writer must not
derive the container extension from an entry's source format.

### 4.6 Damaged-footer salvage

Normal ROMX parsing begins with the footer. A missing, truncated, or invalid
footer makes the container structure invalid, and no stored boundary may be
treated as trusted. The zero-offset, prefix-free payload rule nevertheless
permits an implementation to offer a separate best-effort salvage mode.

A salvage reader may inspect native format signatures and headers starting at
file offset zero. It may expose a recovered single-file payload only when a
format-specific parser can establish a reliable exact payload length. It may
also use an untrusted footer value as a search hint, or search for a RIDX
candidate after a plausible payload boundary, but the candidate must pass its
complete CRC32 and all applicable single-file relationships before it provides
supporting evidence. A matching signature or an occurrence of ASCII `RIDX`
alone is never sufficient.

Recovered content must be reported as salvaged and unverified, never as a
structurally valid ROMX container. The consumer must pass only the recovered
bounded byte range to a core, not the complete damaged `.romx` file. If an
exact native payload boundary cannot be established, automatic launch is not
permitted. Salvage mode must not expose metadata, cover, or mutable data as
trusted and must never perform mutable write-back or repair the source file
without a separate explicit user operation.

## 5. Metadata and cover

Metadata is optional strict UTF-8 JSON without a BOM and follows RFC 8259.
Every object at every depth must have unique member names. Escaped unpaired
UTF-16 surrogates are invalid. The top-level value must conform to
`schema/romx-metadata.schema.json` and use
`schema_version: "0.2.0"`.

Metadata must not contain payload offsets, mutable offsets, host paths,
platform or launch-format declarations, or external cover paths. `crc32`
remains an optional database lookup identity.
When a RIDX entry has `HAS_CRC32`, that value is the integrity checksum of the
embedded entry. It is independent of metadata lookup identities. For a
multi-file set, `origin_crc32` should be omitted unless it clearly identifies
the entrypoint bytes.

The cover profile is unchanged in ROMX 0.2.0: it is exactly one PNG; IHDR is first
and unique; width and height are non-zero; the PNG color-type/bit-depth
combination is valid; IDAT exists and is consecutive; required PLTE rules are
met; every chunk boundary and CRC is valid; and one zero-length IEND is the
last chunk with no trailing bytes. Unknown critical chunks are invalid.

Invalid metadata or cover may be reported and ignored without preventing
access to a structurally valid payload. RIDX is mandatory and structural.

## 6. Mutable region

The mutable region is optional, physically allocated, fixed-capacity storage
for persistent user data. It is not part of the immutable SHA-256 range. It is
not a virtual payload file and is not intended to be mapped directly to an
emulator core. It contains a fixed header, a fixed object directory, and a
data area divided into non-overlapping object extents:

```text
header (4096) | fixed object directory | object extents and free space
```

The mutable region is not an append-only log and contains no snapshot history.
An update overwrites only the selected object's assigned extent and directory
slot. The bytes of an object are opaque to ROMX. ROMX does not define save,
cheat, statistics, or application-private file formats.

Sparse-file behavior is not part of ROMX. Writers must not depend on holes
remaining sparse after copying or downloading a container.

### 6.1 Mutable header

The mutable header is exactly 4096 bytes and is written when the mutable region
is created. Normal object updates do not modify it.

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `RMUT` |
| `0x04` | 2 | uint16 | `mutable_version` | Exactly `1` |
| `0x06` | 2 | uint16 | `header_size` | Exactly `4096` |
| `0x08` | 4 | uint32 | `entry_size` | Exactly `512` |
| `0x0C` | 4 | uint32 | `entry_capacity` | Multiple of 8; at least 8 |
| `0x10` | 8 | uint64 | `directory_offset` | Exactly `4096` |
| `0x18` | 8 | uint64 | `directory_size` | Exactly `entry_capacity * 512` |
| `0x20` | 8 | uint64 | `data_area_offset` | Exactly `4096 + directory_size`; 4096-byte aligned |
| `0x28` | 8 | uint64 | `data_area_size` | Exactly `mutable_capacity - data_area_offset`; greater than zero |
| `0x30` | 4 | uint32 | `flags` | Zero in ROMX 0.2.0 |
| `0x34` | 4 | uint32 | `header_crc32` | CRC32 of the complete 4096-byte header |
| `0x38` | 4040 | bytes | `reserved` | All zero |

For `header_crc32`, treat bytes `0x34..0x37` as zero. All arithmetic is
checked. The directory immediately follows the header; there is no gap. Every
unused directory slot is 512 zero bytes. Bytes in unallocated data extents are
not interpreted and need not be zero.

### 6.2 Mutable directory entry

Each non-empty directory slot is one 512-byte entry. An all-zero slot is
`EMPTY` and has no object identity or allocated extent.

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `MENT` |
| `0x04` | 2 | uint16 | `state` | Section 6.3 |
| `0x06` | 2 | uint16 | `namespace` | Section 6.4 |
| `0x08` | 4 | uint32 | `flags` | Zero in ROMX 0.2.0 |
| `0x0C` | 4 | uint32 | `key_size` | UTF-8 byte length, 1–448 |
| `0x10` | 8 | uint64 | `data_offset` | Relative to mutable start; 64-byte aligned |
| `0x18` | 8 | uint64 | `data_capacity` | Assigned extent size; greater than zero |
| `0x20` | 8 | uint64 | `data_size` | Current opaque byte length; at most `data_capacity` |
| `0x28` | 8 | uint64 | `generation` | Incremented for every attempted replacement; starts at 1 |
| `0x30` | 8 | uint64 | `modified_unix_seconds` | UTC Unix time; zero when unknown |
| `0x38` | 4 | uint32 | `data_crc32` | CRC32 of exactly `data_size` bytes |
| `0x3C` | 4 | uint32 | `entry_crc32` | CRC32 of the complete 512-byte entry |
| `0x40` | 448 | bytes | `key` | `key_size` bytes followed by zero padding |

For `entry_crc32`, treat bytes `0x3C..0x3F` as zero. The key follows the RIDX
path rules, is relative to its namespace, and is not a host path. The pair
`(namespace, key)` is the object identity and must be unique among non-empty,
structurally valid slots.

Every non-empty entry extent must lie completely inside the mutable data area.
Checked additions must not overflow. Extents belonging to non-empty,
structurally valid slots must not overlap, including slots in `WRITING` or
`DELETING` state. Bytes between `data_size` and `data_capacity` are outside the
object value and must not be exposed by a reader.

Duplicate identities or overlapping extents quarantine every implicated slot;
unrelated valid objects remain usable.

`data_size` may be zero; its CRC32 is then `00000000`. ROMX applies no codec,
compression, or byte transformation to mutable object data.

### 6.3 Entry states

| Value | Name | Reader behavior |
|---:|---|---|
| `1` | `ACTIVE` | Expose the object only after validating the entry and data CRC32 |
| `2` | `WRITING` | Do not expose the object; retain its extent as allocated |
| `3` | `DELETING` | Treat the object as absent; retain its extent until the slot is cleared |

Zero is represented only by an all-zero empty slot. Other values are invalid.
An invalid or interrupted entry is quarantined: its object is unavailable and
its possible extent must not be reused until an explicit repair or deletion
clears the slot. If any non-zero slot is structurally invalid, a writer must
not allocate or relocate extents because that slot's range is untrusted;
existing valid objects may still be replaced at their unchanged extents.

### 6.4 Mutable namespaces

| Value | Name | Meaning |
|---:|---|---|
| `1` | `SAVE` | Native persistent game data, including RAM, RTC, card images, or save-directory files |
| `2` | `CHEAT` | Cheat definitions and selections |
| `3` | `STATS` | Play time and other user-owned game statistics |
| `4` | `PRIVATE` | Producer-specific persistent data |

Namespace describes only the broad purpose of opaque bytes. It does not define
a file type, schema, filename extension, emulator, core, frontend, or host
destination. A `PRIVATE` key must begin with a producer-controlled identifier
followed by `/`. Namespace zero and unlisted values are invalid in a non-empty
entry.

Save states are explicitly outside ROMX 0.2.0 and must not be stored in any
namespace, including `PRIVATE`.

### 6.5 Explicit operations and allocation

ROMX defines no automatic restore, synchronization, or write-back event.
Import, overwrite, write-back, and deletion occur only through an explicit
consumer request. User-interface confirmation, local destination paths,
conflict policy, and mapping to emulator memory or frontend directories are
outside the container standard.

Creation assigns an empty directory slot and one non-overlapping extent.
Ordinary replacement must keep the existing `data_offset` and
`data_capacity`; it succeeds only when the selected value fits. Deletion clears
the directory slot and releases its extent. The object bytes may remain in the
released extent but are unreachable; secure erasure is an implementation
policy.

The standard defines no automatic relocation, directory growth, mutable-region
growth, compaction, or container repack. If there is no empty slot or suitable
extent, or replacement data exceeds `data_capacity`, the requested operation
fails without modifying immutable content. Any maintenance operation must be
separately and explicitly requested by the consumer.

### 6.6 Direct-overwrite commit and failure semantics

Writers must serialize mutable operations. To create or replace one object, a
writer performs these steps in order:

1. write a complete, valid `WRITING` entry containing the selected identity,
   assigned extent, next generation, expected size, and expected data CRC32;
2. make that entry durable before modifying its data extent;
3. overwrite exactly the selected object bytes at `data_offset` and make the
   data durable;
4. rewrite the same directory slot as a complete, valid `ACTIVE` entry and
   make it durable.

Step 4 is the commit point. A reader exposes only an `ACTIVE` entry whose entry
CRC32, fields, extent, key, and data CRC32 all validate. An interrupted direct
overwrite is therefore detectable and cannot be mistaken for a committed
object. Because the same data extent is overwritten, ROMX does not guarantee
recovery of the previous value; only the affected object becomes unavailable.

To delete an object, a writer first writes and makes durable a valid `DELETING`
entry, then clears the complete 512-byte slot to zero and makes that change
durable. Once `DELETING` is durable, readers treat the object as absent. A
torn slot write is quarantined rather than reused automatically.

Object updates do not recalculate an enabled `immutable_sha256`, rewrite immutable
regions, move the footer, or change file size. An invalid mutable header makes
the whole mutable region unavailable. An invalid entry, interrupted write,
data CRC32 mismatch, or insufficient capacity affects only mutable data and
must never invalidate or prevent access to otherwise valid payload, RIDX,
metadata, or cover regions.

## 7. Non-normative mutable-capacity guidance

This section is sizing guidance, not a validity rule or hardware maximum.
Capacity includes the 4096-byte header, fixed directory, assigned object
extents, and free space. A writer should select enough directory slots for
directory-based saves and reserve useful capacity in each object extent.

| Profile | Typical systems | Recommended capacity |
|---|---|---:|
| `compact` | Any platform where minimal container growth is preferred | 0 (no mutable region) |
| `cartridge-detected` | GB/GBC/GBA, NES, SNES, MD, SMS, GG, PCE, N64 | `max(256 KiB, detected_save_capacity + 128 KiB + directory overhead)` |
| `cartridge-unknown` | A cartridge whose save capacity cannot be identified | 1 MiB |
| `cartridge-large` | Nintendo DS | `max(4 MiB, detected_save_capacity + 1 MiB + directory overhead)` |
| `disc-card-small` | PS1, PCE CD, Sega CD, Saturn, Dreamcast | 2 MiB |
| `arcade` | FBNeo/MAME NVRAM, configuration, cheats | 1 MiB |
| `disc-card-medium` | PlayStation 2 | 32 MiB |
| `directory-save-large` | PSP, GameCube, Wii, Nintendo 3DS | 64 MiB, explicitly selected |

At least 128 KiB of a non-zero small-system capacity should remain available
for cheat and statistics objects. When existing data is imported, allocated
object capacities should include expected growth in addition to current byte
sizes and directory overhead.

The compact profile is conforming and avoids multiplying the size of very
small ROMs. The other profiles do not guarantee that every future save set
fits. Storage outside the container and policy for selecting a larger capacity
are outside this specification.

## 8. CRC32

All CRC32 fields use the RetroArch-compatible CRC-32/ISO-HDLC parameters:

- polynomial `0x04C11DB7` (reflected `0xEDB88320`);
- initial register `0xFFFFFFFF`;
- reflected input and output;
- final XOR `0xFFFFFFFF`;
- test vector `123456789` produces `cbf43926`.

JSON serializes CRC32 as exactly eight lower-case hexadecimal digits. Binary
structures store the numeric uint32 in little-endian order.

## 9. Validation and failure isolation

A reader validates in this order:

1. footer location, magic, wire version, CRC32, region sizes, hash algorithm,
   platform and launch values, and reserved bytes;
2. checked top-level ranges, mandatory ordering, alignment, and zero padding;
3. RIDX header, exact size, CRC32, entry flags, paths, and payload ranges;
4. optional immutable SHA-256;
5. metadata UTF-8/JSON/schema and cover PNG profile;
6. mutable header, directory entries, extent relationships, and active-object
   CRC32 values.

Present RIDX entry CRC32 values and optional immutable SHA-256 validation may be lazy;
structural validation does not require reading every payload byte. A reader
must not report a payload set or immutable hash as fully verified until every
byte required by that claim has been checked. Lazy and eager payload validation
must produce the same domain result after covering the same bytes.

Validation results belong to independent domains:

| Domain | Invalid when | Effect on other domains |
|---|---|---|
| Container structure | Footer, checked derived layout, mandatory RIDX structure, entrypoint count or zero-offset rule, reserved value, or prohibited registry value is invalid | No region or entry boundaries are trusted |
| Launch profile | A known platform/launch/entrypoint-format combination is not registered by the ROMX 0.2.0 platform profiles | Structure and indexed bytes remain readable, but the declared profile is unusable |
| Registry support | A non-prohibited non-zero ID is unknown to the reader, or either footer ID is `UNSPECIFIED` | Structure remains valid; the profile is unsupported or unresolved rather than corrupt |
| Payload set | An entry whose `HAS_CRC32` flag is set has a CRC32 mismatch | Metadata, cover, and mutable state retain their own results |
| Immutable hash | Enabled `immutable_sha256` mismatches | Immutable content is invalid; mutable state remains separately parseable but must not be associated with trusted content |
| Metadata | UTF-8, JSON, schema, or metadata rules fail | Payload and cover remain independently usable |
| Cover | PNG profile fails | Payload and metadata remain independently usable |
| Mutable layout | Mutable header, directory bounds, identity uniqueness, or extent relationships are invalid | Mutable data is unavailable or implicated slots are quarantined; immutable content remains independently usable |
| Mutable object | Entry validation is interrupted or invalid, state is not `ACTIVE`, or data CRC32 mismatches | The affected object is unavailable; unrelated objects and all immutable content remain usable |

A reader may report more than one domain result. This failure isolation is
part of the container standard; the names and shape of a software API are not.

How a consumer exposes RIDX entries, supplies them to another program, or maps
mutable namespaces to host storage is outside the ROMX container standard.
These choices must not change stored offsets, paths, validation results, or
commit semantics.

## 10. Scope and evolution

ROMX 0.2.0 standardizes:

- uncompressed concatenated single- and multi-file payloads;
- a prefix-free entrypoint beginning at absolute file offset zero;
- the single `.romx` container extension;
- footer platform and launch-format registries;
- the RIDX virtual-file index and entrypoint;
- per-entry RIDX file-format IDs, original virtual paths, byte ranges, and
  optional CRC32 values;
- optional metadata and PNG cover;
- a fixed-capacity indexed mutable object store for explicit save, cheat,
  statistics, and private-data operations;
- immutable-only SHA-256 and scoped CRC32 validation.

ROMX 0.2.0 intentionally does not standardize payload compression, encryption,
save states, automatic mutable synchronization, cloud synchronization, delta
patches, or automatic unbounded mutable growth. CIA installation packages and
standalone ambiguous optical `.bin` images are not ROMX 0.2.0 launch profiles.
A BIN track referenced by a valid descriptor is supported.

Conformance fixtures, when added, belong under `tests/fixtures/` and use
descriptive behavior-based names without format-version suffixes.
