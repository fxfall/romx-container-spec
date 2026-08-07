# File Structure

## ROMX container

```text
┌──────────────────────────────┐
│ ROM payload                  │  Unmodified standard ROM
├──────────────────────────────┤
│ Metadata JSON                │  Embedded UTF-8 JSON
├──────────────────────────────┤
│ Cover image                  │  Optional PNG
├──────────────────────────────┤
│ ROMX footer                  │  Fixed 128 bytes
└──────────────────────────────┘
```

Readers must use footer offsets and sizes; they must not depend on region order. ROM, metadata, and cover regions must not overlap or cover the footer.

---

# 文件结构

## ROMX 容器结构

```text
┌──────────────────────────────┐
│ ROM payload                  │  原始标准 ROM，不压缩、不修改
├──────────────────────────────┤
│ Metadata JSON                │  UTF-8，嵌入容器本体
├──────────────────────────────┤
│ Cover image                  │  PNG，可选
├──────────────────────────────┤
│ ROMX footer                  │  固定 128 字节
└──────────────────────────────┘
```

读取器必须使用 footer 中的 offset 和 size，不得依赖数据区顺序。

ROM、metadata、cover 区域不得重叠，也不得覆盖 footer。
