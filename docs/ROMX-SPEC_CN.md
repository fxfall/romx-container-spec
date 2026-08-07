# ROMX 1.0 二进制规范

状态：Draft 1  
整数编码：无符号小端序  
Footer 大小：128 字节

## 1. 容器布局

文件由三个可独立定位的数据区和固定 footer 组成：

```text
ROM payload | metadata JSON | 可选 PNG cover | 128 字节 footer
```

以上是推荐的写入顺序，不是读取器的前提。读取器必须使用 footer 中的偏移和长度，不能假设数据区顺序。ROM payload 是原始 ROM 字节；ROMX 不添加 ROM 头，也不修改 payload。

Metadata 和 cover 都是 ROMX 文件中的内嵌字节，不使用外部路径。模拟器核心只接收提取出的 ROM payload。

## 2. Footer

Footer 位于文件最后 128 字节。所有整数均为无符号小端序。

| 偏移 | 大小 | 类型 | 字段 | 要求 |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `ROMX` |
| `0x04` | 4 | uint32 | `version` | v1 必须为 `1` |
| `0x08` | 8 | uint64 | `rom_offset` | ROM payload 起始位置 |
| `0x10` | 8 | uint64 | `rom_size` | 必须大于 0 |
| `0x18` | 8 | uint64 | `metadata_offset` | metadata 起始位置 |
| `0x20` | 8 | uint64 | `metadata_size` | 0 表示不存在 |
| `0x28` | 8 | uint64 | `cover_offset` | cover 起始位置 |
| `0x30` | 8 | uint64 | `cover_size` | 0 表示不存在 |
| `0x38` | 32 | bytes | `rom_sha256` | ROM payload 的 SHA-256 |
| `0x58` | 4 | uint32 | `flags` | 功能标记 |
| `0x5C` | 4 | uint32 | `footer_size` | v1 必须为 `128` |
| `0x60` | 32 | bytes | `body_sha256` | footer 前全部字节的 SHA-256；未启用时全 0 |

Footer 在 `0x80` 处结束。每个非空数据区都必须位于 footer 之前，且不能与其他数据区重叠。

### Flags

| 位 | 名称 | 含义 |
|---:|---|---|
| 0 | `HAS_METADATA` | `metadata_size > 0` |
| 1 | `HAS_COVER` | `cover_size > 0` |
| 2 | `HAS_BODY_SHA256` | 存在 `body_sha256` 并且必须校验 |
| 3–31 | Reserved | v1 必须为 0 |

Flags 必须与各数据区长度一致。v1 不支持 ROM 压缩或加密；此类变化必须提升主版本，或增加不会被 v1 读取器误认为原始 ROM 的明确能力标记。

## 3. ROM payload

Payload 必须是目标模拟器核心可以直接接收的标准 ROM 原始字节。写入器不得补齐、去除头部、交换字节、打补丁或以其他方式修改它。`rom_sha256` 只覆盖这些字节。`payload_format` 描述提取后格式，不会改变 payload。

文件名扩展名只是提示。ROMX 容器扩展名是在原 ROM 扩展名后追加 `x`，例如 `.gba` → `.gbax`。

## 4. Metadata 数据区

Metadata 是可选的 UTF-8 JSON，不能带 BOM。顶层值必须是符合 `schema/romx-metadata.schema.json` 的 object。`metadata_offset` 和 `metadata_size` 定位容器中的 JSON 字节。格式错误的 metadata 可以被忽略，ROM 仍可读取。

`platform` 和 `payload_format` 只描述 payload，不会改变提取行为。Game Boy CGB flag 为 `0xC0` 时必须分类为 `gbc`；为 `0x80` 时必须使用有效的 `gb` 或 `gbc` `payload_format`，不得猜测。其他字节值不覆盖有效的 `payload_format`。

## 5. Cover 数据区

v1 允许一个可选的 PNG cover。读取器必须先验证 PNG 文件签名，再检查大小和尺寸限制。metadata 中的 `cover` object 描述内嵌字节，不是路径或下载指令。

建议实现限制为 32 MiB，宽度或高度最大 8192 像素。cover 损坏不得阻止 ROM 提取。

## 6. 读取器校验

读取器应按以下顺序校验：

1. 文件大小至少为 128 字节；
2. footer magic、version、footer_size 有效；
3. 偏移和长度不溢出，并且结束位置在 footer 之前；
4. 非空数据区不重叠；
5. flags 与 metadata、cover 长度一致，保留位为 0；
6. metadata 未超过实现限制，并且存在时是有效 UTF-8 JSON；
7. cover 未超过限制，并且存在时具有有效 PNG 签名；
8. `rom_sha256` 与 ROM payload 匹配；
9. 设置 `HAS_BODY_SHA256` 时，`body_sha256` 与 footer 前全部字节匹配。

ROM 区域或 footer 校验失败时必须拒绝容器。metadata 或 cover 校验失败时可以忽略对应区域，但只有 ROM 和 footer 有效时才能继续。可信 ROM Header 优先于冲突的 metadata 或文件名提示。

## 7. 提取

提取时应先写入临时文件，验证长度和摘要后再原子重命名。缓存键可以使用 `<rom_sha256>.<payload_format>`。ROMX 容器本身始终是内嵌 metadata 和 cover 的来源。
