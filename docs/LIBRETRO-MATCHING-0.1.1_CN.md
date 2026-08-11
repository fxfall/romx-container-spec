# ROMX 0.1.1 libretro 数据库匹配

Python 在线适配器按照 `libretro-build-database.sh` 中为各数据库选择的
key field 执行匹配，不会对每个 ROM 同时尝试两种 key。这样可以避免对大尺寸
光盘镜像重复计算 CRC，也不会把 serial 索引数据库误当成 CRC 索引数据库。

| ROMX 平台/profile | libretro 数据库 profile | 主匹配键 |
| --- | --- | --- |
| `gb`、`gbc`、`gba` | Nintendo 卡带数据库 | `rom.crc` |
| `nes`、`fds` | NES/FDS 数据库 | `rom.crc` |
| `snes` | Super Nintendo 数据库 | `rom.crc` |
| `nds`、`3ds` | Nintendo DS/3DS 数据库 | `rom.crc` |
| `n64` | Nintendo 64 数据库 | `rom.crc` |
| `genesis`、`genesis32x`、`sms`、`gamegear` | Sega 卡带数据库 | `rom.crc` |
| `pce` | PC Engine 卡带数据库 | `rom.crc` |
| `pcecd` | PC Engine CD 数据库 | `rom.crc` |
| `psp`（`.iso`、`.cso`、`.chd`、`.pbp`） | Sony - PlayStation Portable | `rom.serial` |
| `ps1`（`.chd`、单碟 `.pbp`） | Sony - PlayStation | `rom.serial` |
| `ps2`（`.iso`、`.chd`、`.cso`、`.zso`） | Sony - PlayStation 2 | `rom.serial` |
| `segacd`（`.chd`） | Sega - Mega-CD - Sega CD | `rom.serial` |
| `saturn`（`.chd`） | Sega - Saturn | `rom.serial` |
| `dreamcast`（`.chd`、`.cdi`） | Sega - Dreamcast | `rom.serial` |
| `gamecube`（`.gcm`、`.iso`） | Nintendo - GameCube | `rom.serial` |
| `wii`（`.wbfs`、`.rvz`、`.wia`） | Nintendo - Wii | `rom.serial` |
| `wii`（`.wad`） | Nintendo - Wii (Digital) | `rom.crc` |

该映射取自 [libretro-super 数据库构建脚本](https://github.com/libretro/libretro-super/blob/master/libretro-build-database.sh)
以及数据库仓库对 CRC/serial key field 的说明。DAT 中仍可能保存额外的 CRC
和密码学哈希，用于信息完整性与辅助数据，但自动匹配不再在主键失败后偷偷
切换到另一种 key。

对于 serial 索引 profile，适配器会从格式本身提取 serial。PSP ISO/PBP 从
`PSP_GAME/PARAM.SFO` 的 `DISC_ID` 提取，因此修改过的镜像即使完整文件 CRC
不同，只要 serial 没变仍然可以匹配。

PSP `.elf`/`.prx` homebrew 没有稳定的标准数据库 key，不会按 UMD serial
profile 查询。PSP PSN package 是独立的 CRC 索引数据库；ROMX 0.1.1 默认的
`.pbp` profile 指单游戏/单碟 PSP profile，使用 serial。

`--online` 会按照本表选择主键，再用数据库返回的 `name` 查询 libretro 缩略图。
匹配方式不会写入 ROMX metadata，也不会生成本地对比报告。
