# ROMX 1.0 二进制规范

状态：Draft 1  
整数编码：Little Endian  
Footer 大小：128 bytes

## 1. 布局

ROMX 文件由 ROM payload、metadata JSON、可选 cover 和固定 footer 组成。Footer 位于文件最后 128 字节，因此读取器可以先定位 footer，再按偏移读取各区域。

## 2. Footer

| Offset | Size | 类型 | 字段 | 说明 |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | magic | ASCII `ROMX` |
| `0x04` | 4 | uint32 | version | v1 必须为 `1` |
| `0x08` | 8 | uint64 | rom_offset | ROM 起始偏移 |
| `0x10` | 8 | uint64 | rom_size | ROM 字节数，必须大于 0 |
| `0x18` | 8 | uint64 | metadata_offset | metadata 起始偏移 |
| `0x20` | 8 | uint64 | metadata_size | 0 表示无 metadata |
| `0x28` | 8 | uint64 | cover_offset | cover 起始偏移 |
| `0x30` | 8 | uint64 | cover_size | 0 表示无 cover |
| `0x38` | 32 | bytes | rom_sha256 | 原始 ROM 的 SHA-256 |
| `0x58` | 4 | uint32 | flags | 功能标记 |
| `0x5C` | 4 | uint32 | footer_size | v1 必须为 128 |
| `0x60` | 32 | bytes | body_sha256 | footer 之前全部字节的 SHA-256；未启用时全 0 |

### flags

| Bit | 名称 | 含义 |
|---:|---|---|
| 0 | `HAS_METADATA` | metadata_size 大于 0 |
| 1 | `HAS_COVER` | cover_size 大于 0 |
| 2 | `HAS_BODY_SHA256` | body_sha256 有效 |
| 3-31 | Reserved | v1 写入器必须写 0 |

v1 不支持 ROM 压缩和加密。未来若增加，必须提升主版本或使用明确的新能力标记，不能让旧读取器把压缩数据当成 ROM。

## 3. ROM payload

- 必须是核心本来可以直接加载的标准 ROM 文件内容。
- 不得补齐、去头、字节交换或修改 Header。
- `rom_sha256` 只覆盖 ROM payload。
- 解包后的建议扩展名由 `payload_format` 决定。

## 4. Metadata

- 编码必须为 UTF-8，不允许 BOM。
- 顶层必须为 JSON object。
- 标准字段见 `METADATA.md` 和 JSON Schema。
- 读取器应兼容未知字段。
- 严格写入器不得生成尾逗号；兼容读取器可以选择容忍尾逗号。
- metadata 不可信，所有字符串长度、数组长度和显示内容均需限制。

## 5. Cover

v1 允许嵌入一个 cover，格式为 PNG、JPEG 或 WebP。格式必须通过文件签名识别，不能只相信 metadata。

建议限制：

- 最大 32 MiB；
- 最大边长 8192 px；
- 解码前检查图片尺寸，防止解压炸弹；
- 提取文件名由读取器生成，不使用 metadata 提供的路径。

## 6. 校验顺序

读取器至少执行：

1. 文件大小不小于 128 字节；
2. magic、version、footer_size 有效；
3. 所有 offset/size 不溢出且位于 footer 之前；
4. 数据区互不重叠；
5. metadata 不超过实现限制；
6. cover 不超过实现限制；
7. 校验 rom_sha256；
8. flags bit 2 有效时校验 body_sha256；
9. 比较 Header、metadata、文件名提示的格式，冲突时记录警告。

平台判断优先级：

```text
可信 ROM Header > metadata.platform/payload_format > 双扩展名提示
```

## 7. 错误处理

- ROM 区域或 footer 无效：拒绝容器。
- metadata 无效：可以忽略 metadata，但若 ROM Header 可识别，仍允许读取 ROM。
- cover 无效：忽略 cover，不影响 ROM。
- 平台冲突：默认使用可信 Header，并向用户报告。

## 8. 原子提取

实现应先写入临时文件，完成长度和摘要校验后再原子重命名。缓存键建议使用：

```text
<rom_sha256>.<payload_format>
```

数据库应保存原始 `.romx` 路径；模拟核心只接收提取后的标准 ROM 路径。
