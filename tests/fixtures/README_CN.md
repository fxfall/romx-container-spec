# ROMX reference fixtures

这些确定性 ROMX 0.2.0 文件由 `tools/romx_reference.py` 生成。每个
`.manifest.json` 都记录预期 footer、推导区域、RIDX header、entry、checksum 与验证
状态。

- `minimal-single.romx` 保存一份无前缀的合成 NES payload，不包含可选 entry CRC32、
  metadata、cover、mutable region 或 immutable SHA-256。
- `single-complete.romx` 保存相同 payload，并包含 entry CRC32、metadata、单像素 PNG
  cover、空的 12 KiB mutable region 与 immutable SHA-256。
- `multi-cue.romx` 的 CUE entrypoint 位于偏移零，另外直接索引两个轨道文件。三个
  entry 都包含 CRC32。

重新生成并验证：

```sh
python3 tools/romx_reference.py fixtures tests/fixtures --force
python3 tools/romx_reference.py inspect \
  tests/fixtures/single-complete.romx --verify-entry-crc32
```

合成 payload 只用于测试，不包含游戏内容。
