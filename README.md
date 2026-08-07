# romx-container-spec
An open ROM container specification for emulator frontends, game libraries, and archival workflows, with bilingual documentation, metadata schemas, and examples.

# ROMX

## 中文介绍

ROMX 是一个面向模拟器前端、游戏库工具和归档工具的开放 ROM 容器规范草案。

它将以下内容封装为一个可移动文件：

- 未修改的标准 ROM；
- UTF-8 JSON 游戏资料；
- 可选封面图片；
- 可验证的偏移、长度和 SHA-256 摘要。

ROMX 不定义模拟器核心行为，不修改 ROM 内容，也不用于绕过加密、签名或平台安全机制。

### 当前状态

当前版本为 **ROMX 1.0 Draft 1**，用于讨论和实现验证，尚不视为冻结标准。

### 推荐文件名

规范扩展名统一使用 `.romx`：

```text
Game Name.gba.romx
Game Name.nes.romx
Game Name.nds.romx
Game Name.cia.romx
```

最后一个扩展名始终是 `.romx`；倒数第二个扩展名仅作为人类提示，读取器必须以 footer、metadata 和 ROM Header 为准。

### 文档

- [ROMX 二进制规范](docs/ROMX-SPEC.md)
- [Metadata 参数](docs/METADATA.md)
- [平台与 ROM 格式](docs/PLATFORMS.md)
- [项目与容器文件结构](docs/FILE-STRUCTURE.md)
- [JSON Schema](schema/romx-metadata.schema.json)

### 最小 metadata

```json
{
  "schema_version": "1.0",
  "label": "Example Game",
  "platform": "gba",
  "payload_format": "gba"
}
```

`label` 是 ROMX 的标准显示名称字段，与 RetroArch LPL 保持一致。应用内部可以映射到自己的字段，例如 `GameEntry.title`。

### 设计原则

1. ROM 原样保存，核心只接收提取后的标准 ROM。
2. 偏移和长度使用小端无符号整数，支持大文件。
3. 缺少或损坏 metadata 时，仍可尝试通过 ROM Header 识别。
4. 未知 metadata 字段应被保留，不能导致整个容器不可读。
5. 所有路径均由读取器决定，容器不得携带需要直接写入的绝对路径。
6. 核心选择等运行参数只能作为建议，不能覆盖用户设置。

### 仓库状态

本仓库目前仅定义规范、Schema 和示例。参考打包器、验证器和测试向量将在格式评审后加入。

## English Introduction

ROMX is an open draft ROM container specification for emulator frontends, game-library tools, and archival workflows.

It packages the following into a portable file:

- An unmodified standard ROM;
- UTF-8 JSON game metadata;
- An optional cover image;
- Verifiable offsets, lengths, and SHA-256 digests.

ROMX does not define emulator-core behavior, modify ROM content, or bypass encryption, signatures, or platform security mechanisms.

### Current status

The current version is **ROMX 1.0 Draft 1**. It is intended for discussion and implementation validation and is not yet a frozen standard.

### Recommended filenames

The canonical extension is `.romx`:

```text
Game Name.gba.romx
Game Name.nes.romx
Game Name.nds.romx
Game Name.cia.romx
```

The final extension is always `.romx`; the preceding extension is only a human-readable hint. Readers must rely on the footer, metadata, and ROM header.

### Documentation

- [ROMX binary specification](docs/ROMX-SPEC.md)
- [Metadata reference](docs/METADATA.md)
- [Platforms and ROM formats](docs/PLATFORMS.md)
- [Project and container file structure](docs/FILE-STRUCTURE.md)
- [JSON Schema](schema/romx-metadata.schema.json)

### Minimal metadata

```json
{
  "schema_version": "1.0",
  "label": "Example Game",
  "platform": "gba",
  "payload_format": "gba"
}
```

`label` is ROMX's standard display-name field, aligned with RetroArch LPL. Applications may map it to an internal field such as `GameEntry.title`.

### Design principles

1. Preserve the ROM unchanged; cores receive only the extracted standard ROM.
2. Use little-endian unsigned integers for offsets and lengths to support large files.
3. If metadata is missing or damaged, readers may still identify the ROM through its header.
4. Unknown metadata fields must be preserved and must not make the container unreadable.
5. Paths are chosen by the reader; containers must not carry absolute paths that require direct writes.
6. Core-selection and runtime settings are suggestions and must not override user settings.

### Repository status

This repository currently contains only the specification, schema, and examples. Reference packers, validators, and test vectors will be added after format review.
