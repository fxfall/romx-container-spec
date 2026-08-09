# ROMX 1.0 二进制规范

**状态：ROMX 1.0——稳定、冻结。** 本文是首次冻结基线；以下规则在兼容性承诺
建立前确定。

整数使用无符号小端编码，footer 固定为 128 字节。本文件定义 ROMX 1.0
容器的字节语义；metadata schema 独立版本化。

## 1. 容器布局

文件由三个可独立定位的区域和固定 footer 组成：

```text
ROM payload | metadata JSON | 可选 PNG cover | 128 字节 footer
```

上面的顺序只是推荐写入顺序。读取器必须使用 footer 中的 offset/size，接受
任意区域顺序。ROM payload 必须逐字节复制；容器不会增加 ROM header 或修改
payload。metadata 和 cover 都是内嵌字节，不包含外部路径。核心接收提取出的
原始 ROM payload，而不是容器文件。

从偏移 0 到 footer 前一个字节的每个字节，都必须且只能属于一个非空区域。
因此三个区域必须完整、无重叠地覆盖 body：不能有空洞、重叠或不属于区域的字节。

## 2. Footer

footer 中所有整数均为无符号小端编码。

| 偏移 | 大小 | 类型 | 字段 | 要求 |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `ROMX` |
| `0x04` | 4 | uint32 | `version` | 必须为 `1` |
| `0x08` | 8 | uint64 | `rom_offset` | ROM payload 起点 |
| `0x10` | 8 | uint64 | `rom_size` | 大于 0 |
| `0x18` | 8 | uint64 | `metadata_offset` | metadata 存在时的起点 |
| `0x20` | 8 | uint64 | `metadata_size` | 0 表示不存在 |
| `0x28` | 8 | uint64 | `cover_offset` | cover 存在时的起点 |
| `0x30` | 8 | uint64 | `cover_size` | 0 表示不存在 |
| `0x38` | 32 | bytes | `reserved` | 读取器忽略；新文件写 0 |
| `0x58` | 4 | uint32 | `flags` | 功能标志 |
| `0x5C` | 4 | uint32 | `footer_size` | 必须为 `128` |
| `0x60` | 32 | bytes | `body_sha256` | 可选的 footer 前所有字节 SHA-256 |

当 `metadata_size == 0` 时，读取器必须完全忽略 `metadata_offset`，写入器必须
写成 `metadata_offset == 0`。`cover_size == 0` 与 `cover_offset` 同理。非空区域
必须位于 body 内且不与其他非空区域重叠，同时满足第 1 节的完整覆盖要求。

footer 中唯一保存的 hash 是 `body_sha256`。`HAS_BODY_SHA256` 未设置时，该字段
必须为 32 个零字节；设置时覆盖 footer 前的所有 body 字节，校验不匹配则容器
结构无效。`reserved` 的 32 字节在 ROMX 1.0 中不代表 ROM SHA-256。

### Flags

| 位 | 名称 | 含义 |
|---:|---|---|
| 0 | `HAS_METADATA` | `metadata_size > 0` |
| 1 | `HAS_COVER` | `cover_size > 0` |
| 2 | `HAS_BODY_SHA256` | 存在并校验 `body_sha256` |
| 3–31 | 保留 | 必须为 0 |

flags 必须与可选区域 size 一致。压缩、加密或不同 footer 布局必须提升格式版本。

## 3. ROM payload 与 CRC32

payload 必须是目标模拟器核心接受的原始 ROM 字节。写入器不得填充、去除 header、
交换字节、打补丁或以其他方式修改。容器扩展名为原 ROM 扩展名后加 `x`（例如
`.gba` 变成 `.gbax`）。

ROMX `crc32` 使用与 RetroArch CRC 匹配完全相同的 CRC-32/ISO-HDLC 参数：多项式
`0x04C11DB7`（反射实现 `0xEDB88320`）、初值 `0xFFFFFFFF`、输入输出反射、最终异或
`0xFFFFFFFF`，不做额外增广或字节反转。规范序列化形式必须是无 `0x` 前缀的 8 位
小写十六进制；测试向量 `123456789` 的结果为 `cbf43926`。

`metadata.crc32` 是数据库匹配值。写入器默认根据原始 payload 生成；调用方可以为
匹配外部数据库而显式覆盖。`origin_crc32` 是可选的原始 payload CRC，只有启用时才
保存。两者都不能替代可选的 body SHA-256。

## 4. Metadata 区域

metadata 是可选的严格 UTF-8 JSON，禁止 BOM。解析和校验依据 RFC 8259。所有层级
的 JSON object 都必须禁止重复成员名；重复键无效，不能采用“后者覆盖前者”。JSON
转义中的孤立 UTF-16 surrogate 无效；合法的 surrogate pair 按一个 Unicode 标量接受。
顶层
必须是符合 `schema/romx-metadata.schema.json` 的 object；schema 设置
`additionalProperties: false`，未知 ROMX 1.0 字段无效。footer 和启用的 body SHA
通过后，无效 metadata 可以被报告并忽略，payload 仍可提取。

`cover`（如果存在）必须是只包含以下可选属性的 object：`mime_type`（值为
`"image/png"`）、`width`（1–8192 的整数）、`height`（1–8192 的整数），并且其
schema 也设置 `additionalProperties: false`。它只是描述 metadata，不是路径、URL
或 cover checksum；cover 字节按第 5 节 PNG profile 校验。

## 5. Cover PNG profile

可选 cover 是一段 PNG 字节流。接受前必须校验 PNG signature、每个 chunk 的边界和
CRC，并满足以下 ROMX 规则：

1. `IHDR` 必须是第一个 chunk，长度为 13，且只能出现一次。
2. IHDR 宽高非零且不超过实现限制（参考限制为 8192）；压缩方法和 filter 方法
   必须为 0，interlace 方法只能为 0 或 1。
3. 颜色类型与位深组合必须严格为：颜色 0→1/2/4/8/16；颜色 2→8/16；颜色
   3→1/2/4/8；颜色 4→8/16；颜色 6→8/16。其他组合无效。
4. 必须存在 `IDAT`，且所有 IDAT chunk 必须连续。调色板图像（颜色类型 3）
   必须在 IDAT 前有一个合法 `PLTE`；灰度和灰度 alpha 图像禁止 PLTE。PLTE
   长度必须非零、为 3 的倍数且不超过 768 字节。
5. 必须存在 `IEND`，其数据长度必须为 0，并且必须是最后一个 chunk。IEND 后
   不允许任何额外字节，因此第二个 IEND 也无效。

未知 critical chunk 无效；ancillary chunk 在边界和 CRC 正确的前提下允许。cover
   损坏不能阻止有效 ROM payload 的提取。

## 6. 读取校验与提取

读取器先校验 footer 的大小、magic、version、整数溢出和边界、flags、重叠以及
body 的完整覆盖。区域为空时完全忽略其 offset。随后校验 metadata 的严格 UTF-8、
无 BOM、RFC 8259 JSON、递归重复键和 metadata schema；cover 使用第 5 节规则。
启用 body SHA 时，必须计算 footer 前全部字节并比较。

footer 或启用的 body SHA 失败必须拒绝容器。无效的可选 metadata 或 cover 可以报告
并跳过，同时继续提取 payload。提取应写入临时文件、核对字节数后原子重命名；前端
可以使用 `<crc32>.<payload_format>` 作为缓存键。

## 7. 版本与 schema 演进

ROMX 1.0 是冻结格式。兼容性修改只能新增 conformance fixture，或澄清不改变字节
语义的文字。修改 footer 布局、字段语义或任何有效性规则，必须提升格式版本（例如
ROMX 2.0）；ROMX 1.0 读取器必须拒绝新版本。

metadata schema 与二进制容器独立演进：`schema_version` 标识 metadata 合约，footer
`version` 标识二进制容器。只改变 metadata 且保持向后兼容时，可以发布新的 schema
文档和 schema 版本而不改变 footer 字节；不理解该 schema 的读取器应将 metadata
视为不支持/无效，但仍可提取 payload。涉及 footer 字节、区域语义或二进制有效性的
变化不能只靠 metadata schema 版本承载，必须使用新的 ROMX 格式版本。

## 8. 冻结一致性夹具

`tests/fixtures/` 包含与语言无关的 reader 冻结 corpus；`tests/fixtures/writer/`
包含 canonical writer 的逐字节 golden corpus。每个 `.romx` 都有同名
`.manifest.json`。读取器应运行 reader corpus，写入器应将输出与 writer golden
逐字节比较；测试过程不得重写已有 fixture。
