# ROMX Metadata 0.1.x

Metadata 是内嵌在 ROMX 容器中的可选 UTF-8 JSON object。它由 footer 定位，不使用外部路径。规范字段约束以 `schema/romx-metadata.schema.json` 为准。

ROMX 使用 `name` 作为规范显示名称，因为前端将游戏记录保存在自己的数据库中，而不是依赖 RetroArch playlist。RetroArch 适配层把 `name` 映射到数据库的 `name` 字段和前端显示标题。

## 必填字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema_version` | string | 基础注册表使用 `0.1.0`，扩展注册表使用 `0.1.1` |
| `name` | string | 规范游戏显示名称 |
| `platform` | string | `PLATFORMS.md` 中的平台 ID |
| `payload_format` | string | 提取后的 ROM 格式，不含点号 |
| `crc32` | string | 有效的数据库匹配 CRC32，小写 8 位十六进制 |

`crc32` 只是数据库匹配辅助值，不代表 payload 完整性。写入器默认根据 payload 自动生成它。只有调用方明确要求匹配某个数据库已发布的身份时，才允许手动覆盖。`origin_crc32` 与它独立且可选；存在时必须是根据实际 payload 字节计算出的 CRC32。它默认不生成，也不会被手动覆盖值替代。

0.1.1 schema 向后兼容，同时接受两种 `schema_version`。0.1.1 writer 写入
`0.1.1`；未修改的 0.1.0 metadata 继续保留 `0.1.0`。reader 必须根据
`schema_version` 选择规则，不能只因读取或复制 metadata 就改写其版本。

CRC32 与 RetroArch 完全兼容，使用 CRC-32/ISO-HDLC 参数：多项式
`0x04C11DB7`（反射实现 `0xEDB88320`）、初值 `0xFFFFFFFF`、输入输出反射、最终异或
`0xFFFFFFFF`。序列化必须是无前缀的 8 位小写十六进制；`123456789` 的结果为
`cbf43926`。

## 可选字段

### 与数据库兼容的游戏信息

| 字段 | 类型 | 含义 |
|---|---|---|
| `serial` | string | 卡带、发行版或光盘序列号 |
| `developer` | string | 开发商 |
| `publisher` | string | 发行商 |
| `origin` | string | 开发/来源国家或地区 |
| `franchise` | string | 游戏系列名称 |
| `release_date` | string | `YYYY`、`YYYY-MM` 或 `YYYY-MM-DD` |
| `genre` | string[] | 类型标签；适配层可合并为数据库需要的单值 |
| `region` | string[] | 发行地区；适配层可合并为数据库需要的单值 |
| `language` | string | 兼容数据库的语言信息 |
| `users` | integer | 支持的最大用户/玩家数 |
| `coop` | boolean | 是否支持合作游戏 |
| `rumble` | boolean | 是否支持震动 |
| `analog` | boolean | 是否支持模拟输入 |
| `enhancement_hw` | string | 所需或支持的增强硬件 |
| `category` | string | 内容分类 |
| `media` | string | 原始介质类型 |
| `description` | string | 纯文本简介 |

RetroArch 适配层将 `release_date` 映射为 `releaseyear` 和 `releasemonth`，将 `users` 映射为 `users`。ROMX 保留可读的日期和集合结构，不直接复制 RetroArch 内部字段的拼写。`platform` 用于选择前端数据库，不是单个游戏的数据库字段。

### ROM 来源与内嵌封面

| 字段 | 类型 | 含义 |
|---|---|---|
| `origin_crc32` | string | 可选，依据实际 ROM payload 计算出的 CRC32 |
| `dump_status` | string | 可选，原始 dump 的来源/状态提示 |
| `cover` | object | 可选的内嵌 cover 描述信息，不是完整性记录 |
| `cover.mime_type` | string | 可选；存在时必须为 `image/png` |
| `cover.width` / `height` | integer | 可选的像素尺寸 |

`dump_status` 描述的是来源或版本状态，不是密码学完整性，也不代表一定可以启动。`good` 可表示已知的良好 dump；`bad`、`overdump`、`hack`、`translation` 和 `homebrew` 用于说明已知的变体或状态。它不能替代 footer 中的 SHA-256，也不能作为自动拒绝 ROM 的规则。由于它在 RetroArch 数据库中没有直接对应字段，本字段暂时保留，后续可以单独决定是否删除。

`cover` object 仅用于描述，但使用封闭 schema。它只能包含 `mime_type`
（`"image/png"`）、`width`（1–8192 的整数）和 `height`（1–8192 的整数），并且
`additionalProperties` 必须为 false。它不是文件系统路径、URL、命令、凭据或 checksum；
cover 字节本身遵循 `ROMX-SPEC.md` 的 PNG profile。前端应优先显示内嵌 cover；数据库
缩略图作为后备，或由用户主动选择替换。启用 `origin_crc32` 时，仍必须根据实际
payload 字节计算。

Metadata JSON 必须是严格 UTF-8、不得含 BOM，并遵循 RFC 8259。所有对象（包括嵌套
对象）都禁止重复成员名，解析器不得采用“后者覆盖前者”。JSON 转义中的孤立
UTF-16 surrogate 也无效；合法 surrogate pair 按一个 Unicode 标量接受。


## RetroArch 互操作映射表

下表列出 ROMX 所有标准 metadata 字段与 RetroArch 数据库（`.rdb`）字段、JSON playlist（`.lpl`）字段的对应关系。`—` 表示目标格式没有原生结构化字段；间接映射会在说明中标出。数据库字段名依据 RetroArch 的 RDB 读取器，playlist 字段名依据 [RetroArch playlist 文档](https://docs.libretro.com/guides/roms-playlists-thumbnails/)。

| ROMX 字段 | RetroArch 数据库 | RetroArch playlist | 映射与说明 |
|---|---|---|---|
| `schema_version` | — | — | ROMX 格式字段 |
| `name` | `name` | `label` | 规范游戏名称和显示标题 |
| `platform` | 数据库/系统名称 | `db_name` | 选择系统数据库/playlist，不是 RDB 游戏记录字段 |
| `payload_format` | — | `path`（扩展名/成员） | 决定输出内容的扩展名或压缩包成员，不是独立的 playlist metadata 字段 |
| `crc32` | `crc` | `crc32` | 有效匹配值；playlist 形式为 `XXXXXXXX\|crc` |
| `origin_crc32` | — | — | 可选的 payload 来源记录，不是匹配键 |
| `serial` | `serial` | `crc32` | 使用 serial 匹配的系统可在 playlist `crc32` 中携带 serial 标记 |
| `developer` | `developer` | — | 数据库信息 |
| `publisher` | `publisher` | — | 数据库信息 |
| `origin` | `origin` | — | 开发/来源国家或地区 |
| `franchise` | `franchise` | — | 系列名称 |
| `release_date` | `releaseyear`、`releasemonth` | — | 适配层拆分 ROMX ISO 日期；当前 RetroArch metadata 不要求 playlist 字段 |
| `genre` | `genre` | — | ROMX 数组可合并为 RDB 所需的单值 |
| `region` | `region` | — | ROMX 数组可合并为 RDB 所需的单值 |
| `language` | `language` | — | 数据库语言信息 |
| `users` | `users` | — | 支持的最大用户/玩家数 |
| `coop` | `coop` | — | 合作游戏能力 |
| `rumble` | `rumble` | — | 震动能力 |
| `analog` | `analog` | — | 模拟输入能力 |
| `enhancement_hw` | `enhancement_hw` | — | 增强硬件 |
| `category` | `category` | — | 数据库分类 |
| `media` | `media` | — | 原始介质类型 |
| `description` | `description` | — | 数据库简介 |
| `dump_status` | — | — | ROMX 来源状态提示，不是 RetroArch 匹配或 playlist 字段 |
| `cover` | — | `label`（间接） | cover 字节内嵌于 ROMX；生成 RetroArch 缩略图文件名时依据 playlist label |
| `cover.mime_type` | — | — | 内嵌 cover 描述字段 |
| `cover.width` / `height` | — | — | 内嵌 cover 描述字段 |

RetroArch 数据库 RDB 记录使用 `crc` 和 `name`，playlist 使用 `crc32` 和 `label`。数据库由 `db_name` 选择；随后缩略图主要依据得到的游戏名称和系统/playlist 目录关联，而不是直接依据 CRC。RetroArch 文档明确将 CRC/serial 作为匹配键，并使用数据库 `name` 作为游戏名称。参见 [RetroArch 数据库说明](https://docs.libretro.com/guides/databases/) 和 [数据库读取器](https://raw.githubusercontent.com/libretro/RetroArch/master/database_info.c)。


## LPL 转换边界

ROMX metadata 不提供 LPL 专属扩展区域。`path`、`core_path`、`core_name`、`db_name`、playlist 设置和游玩状态都属于转换输入或输出，不是可移植的 ROMX 字段。LPL 转换器根据 `platform`、`payload_format`、`name`、`crc32` 及输出选项临时生成这些值。文件系统路径和前端运行状态不得写入 ROMX metadata。
