# ROMX 0.2.0 Metadata 参数

Metadata 是可选的严格 UTF-8 JSON object；ROMX 0.2.0 footer 保存其大小，offset
由固定区域顺序推导。字段约束以 `schema/romx-metadata.schema.json` 为准。

Metadata 与 RIDX 不同，它只负责描述信息。它不得包含物理 offset、容器长度、主机
路径、启动路径、存档路径或 cover 路径。

## 必填字段

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | 必须为 `0.2.0` |
| `name` | string | 规范显示名称 |

平台与启动格式不属于 metadata。Footer 的 `platform_id`、`launch_format_id` 与
entrypoint RIDX `format_id` 在 metadata 缺失或无效时仍然可用，也是唯一权威声明。
Reader 可以提供对应注册名称，但不得在保存的 JSON 中插入重复字段。

## 可选数据库兼容字段

| Field | Type | Meaning |
|---|---|---|
| `crc32` | string | 有效数据库查询 CRC32 |
| `origin_crc32` | string | 该标识有明确含义时，entrypoint 的准确 CRC32 |
| `serial` | string | 卡带、发行版或光盘序列号 |
| `developer` | string | 开发商 |
| `publisher` | string | 发行商 |
| `origin` | string | 开发或来源国家/地区 |
| `franchise` | string | 系列名称 |
| `release_date` | string | `YYYY`、`YYYY-MM` 或 `YYYY-MM-DD` |
| `genre` | string[] | 类型标签 |
| `region` | string[] | 发行地区 |
| `language` | string | 语言信息 |
| `users` | integer | 最大用户数 |
| `coop` | boolean | 支持合作游戏 |
| `rumble` | boolean | 支持震动 |
| `analog` | boolean | 支持模拟输入 |
| `enhancement_hw` | string | 必需或支持的增强硬件 |
| `category` | string | 内容分类 |
| `media` | string | 原始介质类型 |
| `description` | string | 纯文本介绍 |
| `dump_status` | string | 源 dump 来源/状态提示 |
| `cover` | object | 内嵌 PNG 描述 |

`crc32` 是查询辅助值，不是结构完整性字段。ROMX 0.2.0 将其改为可选，因为很多光盘和
多文件数据库使用 serial 或其他平台专用标识。RIDX entry 可以通过 `HAS_CRC32`
独立保存可选的完整性 CRC32；该值不是数据库标识。多文件集合应省略
`origin_crc32`，除非它可以无歧义地描述 entrypoint 字节。

`dump_status` 可以是 `unknown`、`good`、`bad`、`overdump`、`hack`、
`translation` 或 `homebrew`。它不替代已存在的 RIDX CRC32、footer CRC32 或可选
immutable SHA-256，也不得作为自动拒绝启动的规则。

封闭的 `cover` object 只能包含 `mime_type`（`image/png`）、`width` 和 `height`。
它描述内嵌 cover 字节，不是 URL、路径或完整性记录。

数据库、playlist、前端和 runtime 映射不属于 ROMX 0.2.0 容器标准。它们不得向
保存的 metadata 添加重复的平台/格式字段或主机路径。平台与格式来自 footer/RIDX；
持久存档、金手指、统计与私有 key 属于 mutable object store。

## JSON 有效性

JSON 遵循 RFC 8259，不得带 BOM，每一层 object 的 member name 必须唯一。转义后
未配对的 UTF-16 surrogate 无效。封闭 schema 拒绝未知 property。
