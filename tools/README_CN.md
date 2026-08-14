# ROMX reference tool

`romx_reference.py` 是确定性 ROMX 0.2.0 writer 与结构 inspector，用于为容器 library
生成独立测试输入。它只依赖 Python 标准库，并以流式方式复制 payload 文件。

它不是最终用户转换工具，不负责图片转换、在线查询、模拟器选择或自动重写描述文件。

示例：

```sh
python3 tools/romx_reference.py build game.romx \
  --entry game.nes=/path/to/game.nes \
  --platform NES \
  --launch-format RAW_SINGLE_FILE \
  --entry-crc32

python3 tools/romx_reference.py inspect game.romx --verify-entry-crc32
python3 tools/romx_reference.py fixtures tests/fixtures --force
```
