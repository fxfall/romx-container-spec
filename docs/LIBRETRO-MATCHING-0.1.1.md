# ROMX 0.1.1 libretro database matching

The Python online adapter follows the key-field selection used by
`libretro-build-database.sh`; it does not try both keys for every file. This
keeps a large disc image from being needlessly hashed and avoids treating a
serial-indexed database as a CRC-indexed one.

| ROMX platform/profile | Libretro database profile | Primary key |
| --- | --- | --- |
| `gb`, `gbc`, `gba` | Nintendo cartridge databases | `rom.crc` |
| `nes`, `fds` | NES/FDS databases | `rom.crc` |
| `snes` | Super Nintendo database | `rom.crc` |
| `nds`, `3ds` | Nintendo DS/3DS databases | `rom.crc` |
| `n64` | Nintendo 64 database | `rom.crc` |
| `genesis`, `genesis32x`, `sms`, `gamegear` | Sega cartridge databases | `rom.crc` |
| `pce` | PC Engine cartridge database | `rom.crc` |
| `pcecd` | PC Engine CD database | `rom.crc` |
| `psp` (`.iso`, `.cso`, `.chd`, `.pbp`) | Sony - PlayStation Portable | `rom.serial` |
| `ps1` (`.chd`, single-disc `.pbp`) | Sony - PlayStation | `rom.serial` |
| `ps2` (`.iso`, `.chd`, `.cso`, `.zso`) | Sony - PlayStation 2 | `rom.serial` |
| `segacd` (`.chd`) | Sega - Mega-CD - Sega CD | `rom.serial` |
| `saturn` (`.chd`) | Sega - Saturn | `rom.serial` |
| `dreamcast` (`.chd`, `.cdi`) | Sega - Dreamcast | `rom.serial` |
| `gamecube` (`.gcm`, `.iso`) | Nintendo - GameCube | `rom.serial` |
| `wii` (`.wbfs`, `.rvz`, `.wia`) | Nintendo - Wii | `rom.serial` |
| `wii` (`.wad`) | Nintendo - Wii (Digital) | `rom.crc` |

The mapping is taken from the build table in the [libretro-super database
builder](https://github.com/libretro/libretro-super/blob/master/libretro-build-database.sh)
and the database repository's explanation of CRC versus serial key fields.
The DAT files still contain additional CRC and cryptographic fields for
information and validation, but those fields are not used as an automatic
fallback when the selected primary key does not match.

For serial-indexed profiles, the adapter extracts the serial from the payload
when the format exposes one. PSP ISO/PBP uses `PSP_GAME/PARAM.SFO`'s
`DISC_ID`; a modified image can therefore match by serial even when its
full-file CRC differs from the DAT entry.

PSP `.elf`/`.prx` homebrew has no stable standard database key and is not
queried as a UMD serial profile. PSP PSN packages are a separate CRC-indexed
database profile; ROMX 0.1.1's default `.pbp` profile is the serial-indexed
single-game/disc PSP profile.

The `--online` option applies this table and then uses the matched database
`name` for the libretro thumbnail lookup. It does not add a lookup-method
field to ROMX metadata and does not create a local comparison report.
