# 文件结构

## 项目目录

```text
rom/
├── README.md
├── docs/
│   ├── ROMX-SPEC.md
│   ├── METADATA.md
│   ├── PLATFORMS.md
│   ├── FILE-STRUCTURE.md
│   └── COMPATIBILITY.md
├── schema/
│   └── romx-metadata.schema.json
└── examples/
    ├── metadata.minimal.json
    └── metadata.full.json
```

后续实现阶段建议新增：

```text
tools/             参考 pack、unpack、inspect、verify 工具
tests/             解析器测试和损坏文件测试
test-vectors/      小型、可合法分发的二进制测试向量
docs/decisions/    格式设计决策记录
```

## ROMX 容器结构

```text
┌──────────────────────────────┐
│ ROM payload                  │  原始标准 ROM，不压缩、不修改
├──────────────────────────────┤
│ Metadata JSON                │  UTF-8，可选但推荐
├──────────────────────────────┤
│ Cover image                  │  PNG/JPEG/WebP，可选
├──────────────────────────────┤
│ ROMX footer                  │  固定 128 字节
└──────────────────────────────┘
```

读取器不得假设三个数据区一定按上述顺序排列，必须使用 footer 中的 offset 和 size。写入器应按上述顺序输出，以便流式生成和调试。

ROM、metadata、cover 区域不得重叠，也不得覆盖 footer。
