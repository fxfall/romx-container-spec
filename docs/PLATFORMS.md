# ROMX 0.2.0 Platform and Launch Profiles

Every ROMX 0.2.0 container uses the `.romx` extension. The footer
declares `platform_id` and `launch_format_id`; the RIDX entrypoint declares
its exact `format_id`. Metadata contains none of these structural values.

The numeric registries are normative in `ROMX-SPEC.md`. This document
registers valid ROMX 0.2.0 combinations. Runtime software support is outside the
container standard.

| Platform | Footer `platform_id` | Entrypoint RIDX `format_id` | Footer `launch_format_id` | Payload composition |
|---|---:|---|---|---|
| Game Boy | `0x0001 GAME_BOY` | `GB` | `RAW_SINGLE_FILE` | Single GB ROM |
| Game Boy Color | `0x0002 GAME_BOY_COLOR` | `GBC` | `RAW_SINGLE_FILE` | Single GBC ROM |
| Game Boy Advance | `0x0003 GAME_BOY_ADVANCE` | `GBA` | `RAW_SINGLE_FILE` | Single GBA ROM |
| NES | `0x0004 NES` | `NES`, `UNF`, `UNIF`, `FDS` | `RAW_SINGLE_FILE` | Single cartridge or disk image |
| SNES | `0x0005 SNES` | `SFC`, `SMC` | `RAW_SINGLE_FILE` | ROM and optional indexed MSU/PCM auxiliary entries |
| Nintendo 64 | `0x0006 NINTENDO_64` | `Z64`, `N64`, `V64` | `RAW_SINGLE_FILE` | Single cartridge image |
| Nintendo DS | `0x0007 NINTENDO_DS` | `NDS` | `RAW_SINGLE_FILE` | Single NDS image |
| Nintendo 3DS | `0x0008 NINTENDO_3DS` | `N3DS`, `CCI`, `CXI`, `APP` | `RAW_SINGLE_FILE` | Single directly loadable image |
| Master System | `0x0010 MASTER_SYSTEM` | `SMS` | `RAW_SINGLE_FILE` | Single cartridge image |
| Game Gear | `0x0011 GAME_GEAR` | `GG` | `RAW_SINGLE_FILE` | Single cartridge image |
| Mega Drive | `0x0012 MEGA_DRIVE` | `MD`, `GEN`, `SMD` | `RAW_SINGLE_FILE` | Single cartridge image |
| Mega Drive 32X | `0x0013 MEGA_DRIVE_32X` | `X32` | `RAW_SINGLE_FILE` | Single cartridge image |
| Sega CD | `0x0014 SEGA_CD` | `CUE`, `CHD`, `M3U` | Matching `CUE`, `RAW_SINGLE_FILE`, or `M3U` | Descriptor plus tracks, single CHD, or multi-disc set |
| Sega Saturn | `0x0015 SEGA_SATURN` | `CUE`, `CHD`, `M3U`, `CCD`, `MDS`, `TOC` | Matching descriptor type or `RAW_SINGLE_FILE` | Descriptor set, single CHD, or multi-disc set |
| Dreamcast | `0x0016 DREAMCAST` | `GDI`, `CDI`, `CHD`, `M3U` | Matching `GDI`, `RAW_SINGLE_FILE`, or `M3U` | GDI plus tracks, single image, or multi-disc set |
| PC Engine | `0x0020 PC_ENGINE` | `PCE` | `RAW_SINGLE_FILE` | Single cartridge image |
| PC Engine CD | `0x0021 PC_ENGINE_CD` | `CUE`, `CHD`, `M3U` | Matching `CUE`, `RAW_SINGLE_FILE`, or `M3U` | Descriptor plus tracks, single CHD, or multi-disc set |
| PlayStation | `0x0030 PLAYSTATION` | `CUE`, `CHD`, `PBP`, `M3U`, `CCD`, `MDS`, `TOC` | Matching descriptor type or `RAW_SINGLE_FILE` | Single image, descriptor set, or multi-disc set |
| PlayStation 2 | `0x0031 PLAYSTATION_2` | `ISO`, `CHD`, `CSO`, `ZSO` | `RAW_SINGLE_FILE` | Single directly loadable image |
| PSP | `0x0032 PSP` | `ISO`, `CSO`, `PBP`, `CHD`, `ELF`, `PRX` | `RAW_SINGLE_FILE` | Single directly loadable image or program |
| GameCube | `0x0040 GAMECUBE` | `GCM`, `ISO`, `RVZ`, `WIA` | `RAW_SINGLE_FILE` | Single directly loadable image |
| Wii | `0x0041 WII` | `ISO`, `WBFS`, `RVZ`, `WIA`, `WAD` | `RAW_SINGLE_FILE` or `SPLIT_FILE_SET` | Single image or indexed split-WBFS set |
| Arcade | `0x0050 ARCADE` | `ROMX_LAUNCH_DESCRIPTOR` | `ROMSET` | Expanded ROM set, optional CHD, and logical dependencies |
| ScummVM | `0x0060 SCUMMVM` | `ROMX_LAUNCH_DESCRIPTOR` | `DIRECTORY` | Indexed game directory |
| DOS | `0x0061 DOS` | `ROMX_LAUNCH_DESCRIPTOR` | `DIRECTORY` | Indexed game directory and launch configuration |
| Amiga | `0x0062 AMIGA` | `ROMX_LAUNCH_DESCRIPTOR` | `DIRECTORY` | Indexed game directory or installed-game tree |

“Matching descriptor type” means the footer launch value equals the
entrypoint format: CUE uses `CUE`, GDI uses `GDI`, M3U uses `M3U`, CCD uses
`CCD`, MDS uses `MDS`, and TOC uses `TOC`. A self-contained CHD, PBP, CDI, ISO,
or similar entry uses `RAW_SINGLE_FILE` while retaining its exact RIDX format.

## Descriptor and track rules

- CUE, GDI, M3U, CCD, MDS, and TOC references resolve to normalized RIDX
  relative paths.
- A multi-disc M3U references each disc entrypoint, not every track directly.
- SBI, SUB, ECM-related data, and required sidecars receive separate entries.
- A split WBFS set stores every segment and uses `SPLIT_FILE_SET`.
- ZIP and 7z are not virtual-file payloads. A `ROMSET` writer expands owned
  source files into RIDX entries; a preserved archive cannot be the entrypoint.
- Firmware, shared BIOS, parent-set content, device ROMs, and other runtime
  dependencies are not RIDX entries unless their bytes are actually embedded
  as part of the portable game set. Consumer-side dependency resolution is
  outside the container format.

## Unspecified and unsupported profiles

`platform_id == 0x0000` or `launch_format_id == 0x0000` is an unresolved
profile, not an instruction to guess. Unknown non-prohibited IDs are
unsupported rather than structurally corrupt.

`.cia` is not a ROMX 0.2.0 launch profile. A standalone optical `.bin` is not
accepted because it cannot reliably describe track layout or audio; a BIN
referenced by a valid descriptor is supported. N64DD cartridge/disk/IPL
combinations remain unprofiled until their launch contract is verified.

Header recognition, embedded icon extraction, online lookup, and runtime
selection are outside the container standard. A detected result never
replaces a stored footer or RIDX declaration.
