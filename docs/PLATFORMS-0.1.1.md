# ROMX 0.1.1 Platform and Payload Format Profiles

This document defines only the platform and source-format profiles added by
ROMX 0.1.1. All ROMX 0.1.0 profiles are inherited unchanged from
[`PLATFORMS.md`](PLATFORMS.md) and are not repeated here.

## Scope

ROMX 0.1.1 is a format-profile revision only. VFS, memory mapping, temporary
files, extraction policy, caching, and core integration are implementation
concerns of libromx or a frontend and are not ROMX wire-format requirements.

Each profile stores one complete source file as one contiguous payload. The
payload is byte-preserving: a writer MUST NOT strip headers, byte-swap,
re-encode, recompress, or otherwise transform the source bytes. The `x` suffix
is appended to the original extension (`.iso` becomes `.isox`, `.z64` becomes
`.z64x`). The recommended cores below are informative and are not normative
dependencies.

## Platform and payload profiles

The following table contains only 0.1.1 additions. A profile is valid only
when the source format itself is a complete file or image/container.

| Platform | Source extension | ROMX extension | Platform ID | Recognition hint | Embedded cover/artwork hint | Recommended cores |
| --- | --- | --- | --- | --- | --- | --- |
| NES UNIF | `.unf`, `.unif` | `.unfx`, `.unifx` | `nes` | UNIF container signature; optional `NAME` chunk can provide the title | — | Mesen, Nestopia, FCEUmm |
| Nintendo 64 | `.z64`, `.n64`, `.v64` | `.z64x`, `.n64x`, `.v64x` | `n64` | N64 header and byte-order signature; title at `0x20–0x33` | — | Mupen64Plus-Next |
| PSP | `.iso` | `.isox` | `psp` | UMD image containing `PSP_GAME/PARAM.SFO`; read `TITLE` | `PSP_GAME/ICON0.PNG`; `PIC0.PNG`/`PIC1.PNG` may also exist | — |
| PSP | `.cso` | `.csox` | `psp` | CSO-compressed UMD image; read `PSP_GAME/PARAM.SFO` `TITLE` after logical decompression | Same PSP image assets after logical decompression | — |
| PSP | `.pbp` | `.pbpx` | `psp` | PBP magic and embedded `PARAM.SFO`; read `TITLE` | Embedded `ICON0.PNG`; `PIC0.PNG`/`PIC1.PNG` may also exist | — |
| PSP | `.chd` | `.chdx` | `psp` | CHD container; no guaranteed title field | Underlying PSP image may contain `ICON0.PNG` and related assets | — |
| PSP homebrew | `.elf` | `.elfx` | `psp` | ELF header; no standard human-readable game title | — | — |
| PSP homebrew | `.prx` | `.prxx` | `psp` | PRX/ELF-derived header; no standard human-readable game title | — | — |
| Mega Drive 32X | `.32x` | `.32xx` | `genesis32x` | `SEGA 32X` cartridge header; title fields are format/header dependent | — | — |
| Master System | `.sms` | `.smsx` | `sms` | `TMR SEGA` header at a size-dependent offset; no standard game-title field | — | — |
| Game Gear | `.gg` | `.ggx` | `gamegear` | `TMR SEGA` header at a size-dependent offset; no standard game-title field | — | — |
| PC Engine | `.pce` | `.pcex` | `pce` | HuCard header identification; no universal display-title field | — | — |
| PlayStation | `.chd`, single-disc `.pbp` | `.chdx`, `.pbpx` | `ps1` | PBP `PARAM.SFO` `TITLE`; CHD title depends on the embedded disc metadata/filesystem | PBP `ICON0.PNG`; CHD has no guaranteed cover asset | — |
| PC Engine CD | `.chd` | `.chdx` | `pcecd` | CHD/embedded disc filesystem; no guaranteed common title field | No guaranteed standard cover asset | — |
| Sega CD | `.chd` | `.chdx` | `segacd` | CHD/embedded disc filesystem; no guaranteed common title field | No guaranteed standard cover asset | — |
| Sega Saturn | `.chd` | `.chdx` | `saturn` | CHD/embedded disc filesystem; no guaranteed common title field | No guaranteed standard cover asset | — |
| Dreamcast | `.chd`, `.cdi` | `.chdx`, `.cdix` | `dreamcast` | Dreamcast `IP.BIN`; software name at `0x80–0xFF` when present | No standard cover asset in `IP.BIN` | — |
| GameCube/Wii | `.gcm`, `.iso`, `.wbfs`, `.rvz`, `.wia`, `.wad` | `.gcmx`, `.isox`, `.wbfsx`, `.rvzx`, `.wiax`, `.wadx` | `gamecube`, `wii` | GCM/ISO disc title at `0x20–0x5F`; wrappers preserve the source header | `opening.bnr`/banner assets may provide icon/artwork | — |
| PlayStation 2 | `.iso`, `.chd`, `.cso`, `.zso` | `.isox`, `.chdx`, `.csox`, `.zsox` | `ps2` | ISO filesystem and `SYSTEM.CNF`; no canonical display-title field | No guaranteed standard cover asset | — |
| Nintendo 3DS | `.cxi` | `.cxix` | `3ds` | NCCH/CXI structure; title extraction is not guaranteed | ExeFS `SMDH` icon/title assets may be decoded to artwork | — |
| Nintendo 3DS | `.app` | `.appx` | `3ds` | NCCH/APP structure; title extraction is not guaranteed | ExeFS `SMDH` icon/title assets may be decoded to artwork | — |

## Embedded title extraction guidance

`metadata.name` remains required, but a writer MAY populate it automatically
when the caller does not provide a name. The recommended candidate order is:

1. an explicitly supplied name;
2. a validated, human-readable title from the payload field described in the
   recognition-hint column;
3. a title returned by a trusted database lookup using the platform's defined
   `crc32` or `serial` key;
4. the source filename stem as a last-resort fallback.

Only accept a payload title after its format signature/header has been
validated. Trim NUL and padding bytes, decode with the format's documented
character set, and reject empty or control-character-only values. A header
signature, product code, serial, or title ID is an identifier, not a display
name; it must not be promoted to `metadata.name` unless no better fallback is
available. If no reliable title exists, the writer should retain the filename
fallback and let a frontend or database replace it later.

This is metadata-derivation guidance and does not add bytes or fields to the
ROMX container. It also does not require a core or a VFS implementation.

## Embedded artwork extraction guidance

The cover/artwork column identifies source assets that may be converted to the
ROMX PNG cover. These assets are optional and are not part of the ROMX
container until a writer explicitly embeds a converted PNG. A reader MUST
validate the source container and all image offsets/lengths before decoding.

The preferred primary artwork is the platform's icon/banner asset (`ICON0.PNG`,
a 3DS `SMDH` icon, or `opening.bnr`). PSP `PIC0.PNG` and `PIC1.PNG` are
secondary artwork and may be used when no primary icon is available. Native
assets are not required to be PNG; a frontend or converter may decode them to
PNG without changing the ROM payload. Missing artwork is a normal condition
and must not make an otherwise valid ROMX file invalid.

The source extension is retained in the ROMX extension so that byte order and
source-format identity remain explicit (`.z64x`, `.n64x`, and `.v64x` are
distinct profiles). The `.iso` profile is format-specific and is not a
platform-wide guarantee for every optical system; a PS1 or Saturn ISO is valid
only when it is a complete single-file image. PSP `.pbp` and PlayStation
single-disc `.pbp` profiles are limited to one game/disc.

## Explicitly out of scope for 0.1.1

The following require a virtual file tree or multiple related files and are
reserved for ROMX 0.2.0:

| Format or layout | Reason |
| --- | --- |
| `.cue`, `.gdi`, `.m3u`, `.ccd`, `.mds`, `.toc` | Disc descriptor depends on adjacent track files |
| CUE plus multiple BIN files | Multiple tracks are separate files |
| GDI plus multiple track files | Multiple tracks are separate files |
| Multi-disc M3U | Playlist references multiple disc images |
| `.sbi`, `.sub`, `.ecm` sidecars | Auxiliary files are required beside the main image |
| MSU-1 main ROM plus attached files | Main ROM and attachments form a file set |
| Any descriptor with required adjacent files | A single payload cannot represent the dependency |

The following are also not supported as 0.1.1 single-file profiles:

* `.zip` and `.7z`: the archive is a collection of files, not one source ROM.
* `.cia`: reserved for a ROMX 0.2.0 installation-package profile.
* Mega Drive `.bin`: reserved for ROMX 0.2.0 pending an unambiguous identity
  and loading profile.
* PS1/Saturn `.iso` as a platform-wide guarantee; use the complete-image rule
  above.
* N64DD `.ndd`: commonly requires an IPL, disk, and cartridge combination.

These exclusions do not prevent recovery of an existing container's payload,
but they are not conforming ROMX 0.1.x source profiles.

## Metadata and compatibility

ROMX 0.1.1 adds no metadata fields. Its schema is a strict superset of the
corrected 0.1.0 registry and accepts metadata declaring either
`schema_version: "0.1.0"` or `"0.1.1"`. A 0.1.1 writer emits `0.1.1`; existing
0.1.0 metadata retains its original version. The footer wire value remains `1`,
and every valid 0.1.0 container and metadata document is valid input to a
0.1.1-aware reader.

The normative source-format identity is the pair of `platform` and
`payload_format` in metadata plus the extension mapping in this document.
The schema validates the individual values; this profile table defines the
allowed platform/format combinations. The extension alone is not a substitute
for metadata validation.
