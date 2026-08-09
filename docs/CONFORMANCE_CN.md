# ROMX 1.0 一致性冻结夹具

仓库在 [`tests/fixtures`](../tests/fixtures/) 中提供跨语言使用的 ROMX 1.0
冻结测试集，可由 libromx、ROMX Core、Python 参考实现和其他读取器共同使用。

每个夹具由一对文件组成：

```text
<name>.romx
<name>.manifest.json
```

manifest 是测试预期的权威来源，包含：

- `expected.reader_open`：footer 与区域表是否应被接受；
- `expected.validate_all`：完成可选 metadata 与 cover 检查后的结果；
- `expected.footer`：本 fixture 涉及的 v1 footer 字段；
- `expected.crc32`：payload 的计算值、metadata 查找值及其数据库查找语义；
- `expected.sha256`：body 的计算值与 footer 值；
- `expected.components`：结构、可选 body hash、metadata、CRC32 语法和 cover 状态；
- `expected.payload_extraction`：ROM payload 是否必须仍可提取；
- `expected.payload_salvage`：是否专门测试可恢复的可选区域错误。

夹具很小且完全确定：payload 是 `abc`，有效 cover 是 1×1 RGBA PNG，因此不
需要携带受版权保护的游戏或图片资源。生成脚本只用于保证可复现；兼容性测试
应以仓库中已提交的二进制文件为准。

读取器应先拒绝无效的 footer 结构，再读取可选区域。错误的 metadata 或 PNG
cover 不得阻止 ROM payload 提取。Metadata 的 `crc32` 是数据库查找值，不与
payload 自动比较。禁用 body SHA-256 时，对应 flag 必须清零且字段必须全为零；
启用时不匹配必须拒绝容器。`0x38` 的 32 字节为保留区，读取器忽略，新写入器
写为零。

`metadata-absent-nonzero-offset` 和 `cover-absent-nonzero-offset` 夹具确认 size 为
0 的区域会忽略 offset，并由读取器归一化为 0。`regions-gap` 夹具确认 footer 前的
字节不能落在所有声明区域之外。`metadata-nested-duplicate-key` 夹具覆盖嵌套 JSON
object 的重复键拒绝。PNG 夹具覆盖 chunk 越界和 CRC；实现还必须执行二进制规范中的
ROMX PNG profile：IHDR 首个且唯一、必须有连续 IDAT、颜色/位深组合合法、
IEND 最后且后面不能有额外字节。

执行源文件与冻结文件的逐字节校验：

```bash
python3 tools/generate_fixtures.py --check
```

## Writer golden fixtures

`tests/fixtures/writer/` 保存规范 writer 的逐字节黄金结果。每个 manifest 的
`input` 记录 payload、metadata、cover 和 writer 选项；`canonical` 记录布局与
编码规则；`expected` 记录所有区域、footer、完整文件十六进制和完整文件 SHA-256。
测试必须将 writer 输出与 `.romx` 逐字节比较，不能只比较摘要。

golden 覆盖只有 payload、metadata 自动 CRC32、lookup CRC32 override、根据实际
payload 写入 `origin_crc32`、cover、body SHA-256 开启和关闭。全部采用
`ROM | metadata | cover | footer` canonical 顺序；空区域 offset 为 0，metadata
使用无 BOM、无多余空白的 UTF-8 JSON，footer 整数使用小端编码，所有保留字节为 0。
