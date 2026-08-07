# ROMX 文件结构

## 磁盘布局

```text
ROM payload | 内嵌 metadata JSON | 可选内嵌 PNG cover | 128 字节 footer
```

这是推荐的写入顺序，不是读取器的要求。Footer 始终位于文件末尾。读取器根据 `*_offset` 和 `*_size` 定位每个区域，必须拒绝重叠区域或延伸到 footer 的区域。

## 仓库结构

仓库包含 `docs/` 中的英文规范、`schema/` 中的 metadata Schema、`examples/` 中的示例，以及 `tools/romx.py` 中的 Python 参考实现。
