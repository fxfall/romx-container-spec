# Metadata 参数

ROMX metadata 使用 UTF-8 JSON object。标准标题字段为 `label`。

## 必填字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `schema_version` | string | metadata Schema 版本，v1 使用 `1.0` |
| `label` | string | UI 显示标题，与 RetroArch LPL 一致 |
| `platform` | string | 规范平台 ID |
| `payload_format` | string | 解包后标准 ROM 格式/扩展名，不含点 |

## 游戏身份与标题

| 字段 | 类型 | 说明 |
|---|---|---|
| `sort_label` | string | 排序标题 |
| `original_label` | string | 原始发行标题 |
| `alternative_labels` | object | 语言代码到标题的映射 |
| `game_id` | string | 平台游戏代码或数据库 ID |
| `serial` | string | 卡带/发行序列号 |
| `version` | string | 游戏版本或修订版 |

## 发行资料

| 字段 | 类型 | 说明 |
|---|---|---|
| `developer` | string | 开发商 |
| `publisher` | string | 发行商 |
| `release_date` | string | 建议 ISO 8601：`YYYY-MM-DD` |
| `genre` | string[] | 类型列表 |
| `region` | string[] | 地区列表，如 `USA`、`JPN`、`EUR` |
| `languages` | string[] | BCP 47 语言标签，如 `zh-Hans`、`en` |
| `players` | object | `min`、`max` |
| `description` | string | 简介，纯文本 |
| `tags` | string[] | 用户或工具标签 |

## ROM 信息

| 字段 | 类型 | 说明 |
|---|---|---|
| `rom_size` | integer | 可选冗余信息；必须与 footer 一致 |
| `crc32` | string | 8 位小写十六进制 |
| `md5` | string | 32 位小写十六进制 |
| `sha1` | string | 40 位小写十六进制 |
| `header_title` | string | 工具读取到的 ROM Header 标题 |
| `header_id` | string | Header 游戏代码 |
| `dump_status` | string | `unknown/good/bad/overdump/hack/translation/homebrew` |

SHA-256 的权威值存放在 footer，不需要在 metadata 重复保存。

## 媒体信息

| 字段 | 类型 | 说明 |
|---|---|---|
| `cover` | object | 嵌入封面的描述 |
| `cover.mime_type` | string | `image/png`、`image/jpeg`、`image/webp` |
| `cover.width` | integer | 像素宽度 |
| `cover.height` | integer | 像素高度 |
| `cover.sha256` | string | cover 数据 SHA-256 |
| `cover.source` | string | 来源名称或 URL；不得作为自动访问指令 |

## 数据来源

| 字段 | 类型 | 说明 |
|---|---|---|
| `source` | object | metadata 来源信息 |
| `source.name` | string | 数据库或工具名称 |
| `source.id` | string | 来源记录 ID |
| `source.url` | string | 参考 URL |
| `source.retrieved_at` | string | ISO 8601 时间 |

## 核心建议

| 字段 | 类型 | 说明 |
|---|---|---|
| `emulation` | object | 可选运行建议 |
| `emulation.preferred_core` | string | 建议核心 ID |
| `emulation.compatible_cores` | string[] | 已知兼容核心 |
| `emulation.bios` | string[] | 所需 BIOS 标识，不含本地路径 |
| `emulation.notes` | string | 兼容性说明 |

这些字段不能强制覆盖用户选择，也不得携带可执行命令、核心下载地址或本地绝对路径。

## 扩展字段

非标准字段必须以 `x-` 开头，建议使用组织命名空间：

```json
{
  "x-org.example-rating": 4.5
}
```

读取器应保留但可以忽略未知扩展字段。

## 明确禁止的字段内容

- 本地绝对路径；
- 自动执行命令；
- 密钥、口令或解密材料；
- 要求读取器静默访问的网络地址；
- 内嵌脚本。
