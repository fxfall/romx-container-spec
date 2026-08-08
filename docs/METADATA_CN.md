# ROMX Metadata 1.0

Metadata 是内嵌在 ROMX 容器中的可选 UTF-8 JSON object。它由 footer 定位，不使用外部路径。规范字段约束以 `schema/romx-metadata.schema.json` 为准。

## 必填字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema_version` | string | 必须为 `1.0` |
| `label` | string | 显示标题 |
| `platform` | string | `PLATFORMS.md` 中的平台 ID |
| `payload_format` | string | 提取后的 ROM 格式，不含点号 |

## 可选字段

### 身份与发行资料

| 字段 | 类型 | 含义 |
|---|---|---|
| `sort_label` | string | 排序标题 |
| `original_label` | string | 原始发行标题 |
| `alternative_labels` | object | 语言标签到标题的映射 |
| `game_id` | string | 平台或数据库标识符 |
| `serial` | string | 卡带或发行序列号 |
| `version` | string | 游戏版本或修订版 |
| `developer` | string | 开发商 |
| `publisher` | string | 发行商 |
| `release_date` | string | `YYYY`、`YYYY-MM` 或 `YYYY-MM-DD` |
| `genre` | string[] | 类型标签 |
| `region` | string[] | 地区代码 |
| `languages` | string[] | BCP 47 语言标签 |
| `players` | object | 必须包含 `min` 和 `max` 整数 |
| `description` | string | 纯文本简介 |
| `tags` | string[] | 用户或工具标签 |

### ROM 与封面资料

| 字段 | 类型 | 含义 |
|---|---|---|
| `crc32` | string | 小写 8 位十六进制；用于 RetroArch/数据库匹配 |
| `header_title` | string | 从 ROM Header 读取的标题 |
| `header_id` | string | 从 ROM Header 读取的标识符 |
| `dump_status` | string | Schema 定义的枚举值之一 |
| `cover` | object | 内嵌 PNG 的描述 |
| `cover.mime_type` | string | 固定为 `image/png` |
| `cover.width` / `height` | integer | 像素尺寸 |
| `cover.sha256` | string | 内嵌 cover 字节的 SHA-256 |

写入器默认必须根据原始 ROM 字节重新生成 `crc32`，覆盖输入 metadata 中可能过期的值。需要匹配某个数据库已发布的身份时，可以显式提供 8 位十六进制自定义值；这个值只是查找提示，不代表完整性校验。CRC32 在卡带 ROM 数据库中很常见：RetroArch 将 CRC 或光盘序列号作为主要内容键，No-Intro DAT 通常同时发布 size、CRC32 和 SHA-1。ROMX 查找时使用 CRC32 加 ROM size。权威的 ROM SHA-256 保存在 footer 中，并且始终描述实际载荷，只负责完整性校验。MD5 和 SHA-1 不再存储；如果某个 provider 要求其他 hash，可以按需计算。Cover object 不包含文件系统路径、待访问 URL、命令、凭据或脚本。

导入或导出 RetroArch LPL 时，写入器可以把 `db_name`、`core_name` 和原始 LPL identity 字符串等前端字段保存在 `x-retroarch` 扩展中。ROM 路径和核心路径不复制，因为 ROM 与 cover 已经内嵌，或由输出流程负责定位。

ROMX 线格式中的 cover 固定保存为 PNG。实现可以接受 JPG、JPEG、WebP、GIF 和 BMP，并在打包前转换为 PNG。未指定输出分辨率时，PNG 输入应逐字节保留，其他格式保留解码后的原始尺寸；指定分辨率后，所有支持的格式都可以统一转换并调整为该尺寸。

## 扩展字段

非标准字段必须以 `x-` 开头并符合 Schema 的模式。读取器可以忽略未知扩展，但重写 metadata 时应尽量保留。
