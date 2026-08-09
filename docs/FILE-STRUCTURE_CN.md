# ROMX 文件结构

## 磁盘布局

```text
ROM payload | 内嵌 metadata JSON | 可选内嵌 PNG cover | 128 字节 footer
```

这是推荐的写入顺序，不是读取器的要求。Footer 始终位于文件末尾。读取器只对非空
区域使用 `*_offset` 和 `*_size`，必须拒绝溢出、越界或重叠区域。区域 size 为 0
时完全忽略 offset，写入器必须把该 offset 写成 0。所有非空区域必须恰好覆盖
footer 前的每个字节，不能有 body 空洞或未分配字节。

## 仓库结构

仓库包含 `docs/` 中的英文规范、`schema/` 中的 metadata Schema、`examples/` 中的示例，以及 `tools/romx.py` 中的 Python 参考实现。
