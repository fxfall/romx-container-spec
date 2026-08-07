# Metadata Reference

ROMX metadata is embedded UTF-8 JSON. It has no external path. The required fields are:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | Metadata schema version; v1 is `1.0` |
| `label` | string | Display title |
| `platform` | string | ROMX platform ID |
| `payload_format` | string | Extracted ROM format, without a dot |

Optional fields cover titles, release data, ROM identifiers, hashes, embedded cover metadata, and namespaced `x-` extensions. The authoritative ROM SHA-256 is in the footer, not metadata. Cover `mime_type` is always `image/png`.

Metadata must not contain external path references, executable commands, credentials, or embedded scripts.

---

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
| `cover.mime_type` | string | 固定为 `image/png` |
| `cover.width` | integer | 像素宽度 |
| `cover.height` | integer | 像素高度 |
| `cover.sha256` | string | cover 数据 SHA-256 |
| `cover.source` | string | 来源名称或 URL；不得作为自动访问指令 |

## 扩展字段

非标准字段必须以 `x-` 开头，建议使用组织命名空间：

```json
{
  "x-org.example-rating": 4.5
}
```

读取器应保留但可以忽略未知扩展字段。

metadata 和 cover 都已嵌入 ROMX，不使用外部路径引用。
