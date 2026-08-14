# ROMX 0.2.0 平台与启动 Profile

所有 ROMX 0.2.0 容器统一使用 `.romx` 扩展名。Footer 声明
`platform_id` 与 `launch_format_id`；RIDX entrypoint 声明准确的 `format_id`。
Metadata 不包含这些结构值。

数值注册表以 `ROMX-SPEC_CN.md` 为规范依据。本文登记 ROMX 0.2.0 有效组合。
运行软件是否支持不属于容器标准。

| Platform | Footer `platform_id` | Entrypoint RIDX `format_id` | Footer `launch_format_id` | Payload composition |
|---|---:|---|---|---|
| Game Boy | `0x0001 GAME_BOY` | `GB` | `RAW_SINGLE_FILE` | 单个 GB ROM |
| Game Boy Color | `0x0002 GAME_BOY_COLOR` | `GBC` | `RAW_SINGLE_FILE` | 单个 GBC ROM |
| Game Boy Advance | `0x0003 GAME_BOY_ADVANCE` | `GBA` | `RAW_SINGLE_FILE` | 单个 GBA ROM |
| NES | `0x0004 NES` | `NES`, `UNF`, `UNIF`, `FDS` | `RAW_SINGLE_FILE` | 单个卡带或磁盘镜像 |
| SNES | `0x0005 SNES` | `SFC`, `SMC` | `RAW_SINGLE_FILE` | ROM 与可选的 MSU/PCM auxiliary entry |
| Nintendo 64 | `0x0006 NINTENDO_64` | `Z64`, `N64`, `V64` | `RAW_SINGLE_FILE` | 单个卡带镜像 |
| Nintendo DS | `0x0007 NINTENDO_DS` | `NDS` | `RAW_SINGLE_FILE` | 单个 NDS 镜像 |
| Nintendo 3DS | `0x0008 NINTENDO_3DS` | `N3DS`, `CCI`, `CXI`, `APP` | `RAW_SINGLE_FILE` | 单个可直接加载镜像 |
| Master System | `0x0010 MASTER_SYSTEM` | `SMS` | `RAW_SINGLE_FILE` | 单个卡带镜像 |
| Game Gear | `0x0011 GAME_GEAR` | `GG` | `RAW_SINGLE_FILE` | 单个卡带镜像 |
| Mega Drive | `0x0012 MEGA_DRIVE` | `MD`, `GEN`, `SMD` | `RAW_SINGLE_FILE` | 单个卡带镜像 |
| Mega Drive 32X | `0x0013 MEGA_DRIVE_32X` | `X32` | `RAW_SINGLE_FILE` | 单个卡带镜像 |
| Sega CD | `0x0014 SEGA_CD` | `CUE`, `CHD`, `M3U` | 对应 `CUE`、`RAW_SINGLE_FILE` 或 `M3U` | 描述文件加轨道、单 CHD 或多碟集合 |
| Sega Saturn | `0x0015 SEGA_SATURN` | `CUE`, `CHD`, `M3U`, `CCD`, `MDS`, `TOC` | 对应描述文件类型或 `RAW_SINGLE_FILE` | 描述文件集合、单 CHD 或多碟集合 |
| Dreamcast | `0x0016 DREAMCAST` | `GDI`, `CDI`, `CHD`, `M3U` | 对应 `GDI`、`RAW_SINGLE_FILE` 或 `M3U` | GDI 加轨道、单镜像或多碟集合 |
| PC Engine | `0x0020 PC_ENGINE` | `PCE` | `RAW_SINGLE_FILE` | 单个卡带镜像 |
| PC Engine CD | `0x0021 PC_ENGINE_CD` | `CUE`, `CHD`, `M3U` | 对应 `CUE`、`RAW_SINGLE_FILE` 或 `M3U` | 描述文件加轨道、单 CHD 或多碟集合 |
| PlayStation | `0x0030 PLAYSTATION` | `CUE`, `CHD`, `PBP`, `M3U`, `CCD`, `MDS`, `TOC` | 对应描述文件类型或 `RAW_SINGLE_FILE` | 单镜像、描述文件集合或多碟集合 |
| PlayStation 2 | `0x0031 PLAYSTATION_2` | `ISO`, `CHD`, `CSO`, `ZSO` | `RAW_SINGLE_FILE` | 单个可直接加载镜像 |
| PSP | `0x0032 PSP` | `ISO`, `CSO`, `PBP`, `CHD`, `ELF`, `PRX` | `RAW_SINGLE_FILE` | 单个可直接加载镜像或程序 |
| GameCube | `0x0040 GAMECUBE` | `GCM`, `ISO`, `RVZ`, `WIA` | `RAW_SINGLE_FILE` | 单个可直接加载镜像 |
| Wii | `0x0041 WII` | `ISO`, `WBFS`, `RVZ`, `WIA`, `WAD` | `RAW_SINGLE_FILE` 或 `SPLIT_FILE_SET` | 单镜像或索引分割 WBFS 集合 |
| Arcade | `0x0050 ARCADE` | `ROMX_LAUNCH_DESCRIPTOR` | `ROMSET` | 展开的 ROM set、可选 CHD 与逻辑依赖 |
| ScummVM | `0x0060 SCUMMVM` | `ROMX_LAUNCH_DESCRIPTOR` | `DIRECTORY` | 索引游戏目录 |
| DOS | `0x0061 DOS` | `ROMX_LAUNCH_DESCRIPTOR` | `DIRECTORY` | 索引游戏目录与启动配置 |
| Amiga | `0x0062 AMIGA` | `ROMX_LAUNCH_DESCRIPTOR` | `DIRECTORY` | 索引游戏目录或已安装游戏树 |

“对应描述文件类型”表示 footer 启动值与 entrypoint 格式一致：CUE 使用 `CUE`，
GDI 使用 `GDI`，M3U 使用 `M3U`，CCD 使用 `CCD`，MDS 使用 `MDS`，TOC 使用
`TOC`。自包含 CHD、PBP、CDI、ISO 等 entry 使用 `RAW_SINGLE_FILE`，同时在 RIDX
中保留准确格式。

## 描述文件与轨道规则

- CUE、GDI、M3U、CCD、MDS 和 TOC 引用解析到规范化 RIDX 相对路径。
- 多碟 M3U 引用每张光盘的 entrypoint，而不是直接引用每条轨道。
- SBI、SUB、ECM 相关数据及必需伴随文件分别拥有 entry。
- 分割 WBFS 集合保存每个分段，并使用 `SPLIT_FILE_SET`。
- ZIP 和 7z 不是虚拟文件 payload。`ROMSET` writer 将用户拥有的源文件展开为 RIDX
  entry；保留的压缩包不能作为 entrypoint。
- Firmware、共享 BIOS、父集内容、设备 ROM 及其他运行时依赖不属于 RIDX entry，
  除非其字节确实作为便携游戏集合的一部分内嵌。Consumer 侧依赖解析不属于容器格式。

## 未声明与不支持的 Profile

`platform_id == 0x0000` 或 `launch_format_id == 0x0000` 表示 profile 尚未解决，
不是要求猜测。未知且未被禁止的 ID 属于不支持，而不是结构损坏。

`.cia` 不是 ROMX 0.2.0 启动 profile。独立光盘 `.bin` 无法可靠描述轨道布局和音轨，
因此不接受；被有效描述文件引用的 BIN 受到支持。N64DD 卡带/磁盘/IPL 组合在启动
合约完成验证前不设 profile。

Header 识别、内嵌图标提取、在线查询和运行时选择不属于容器标准。检测结果永远
不得替换 footer 或 RIDX 中的保存声明。
