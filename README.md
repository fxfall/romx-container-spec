# ROMX

ROMX is an open ROM container specification for emulator frontends, game libraries, and archival workflows.

A ROMX file contains:

- an unmodified, directly loadable ROM payload;
- embedded UTF-8 metadata JSON;
- an optional embedded PNG cover;
- a fixed 128-byte footer with offsets, lengths, and SHA-256 values.

The container extension is the original ROM extension plus `x`: `.gba` becomes `.gbax`, `.nes` becomes `.nesx`, and `.nds` becomes `.ndsx`.

This repository defines ROMX 1.0 Draft 1. It contains the binary specification, metadata schema, platform rules, examples, and a small Python reference implementation.

## Documentation

- [Binary specification](docs/ROMX-SPEC.md)
- [Metadata reference](docs/METADATA.md)
- [Platforms and payload formats](docs/PLATFORMS.md)
- [Container structure](docs/FILE-STRUCTURE.md)
- [Metadata JSON Schema](schema/romx-metadata.schema.json)

## Reference implementation

The [Python reference implementation](tools/romx.py) demonstrates how to create, inspect, verify, and extract a ROMX file using only the Python standard library.

```bash
python3 tools/romx.py pack game.gba metadata.json -o game.gbax --cover cover.png
python3 tools/romx.py inspect game.gbax
python3 tools/romx.py verify game.gbax
python3 tools/romx.py extract game.gbax extracted/
python3 tools/romx.py import-lpl playlist.lpl -o romx-out --rom-root /path/to/rom-root --cover-root /path/to/thumbnails
python3 tools/romx.py export-lpl romx-out -o retroarch-out
```

The script is an implementation guide and validation aid, not a production packer.

`import-lpl` creates sequential names such as `000001.gbcx`, matching each LPL item to a ROM and (when available) `Named_Snaps/<rom-stem>.png`. Use `--rom-dir` and `--cover-dir` to force flat lookup directories. `export-lpl` writes the default RetroArch layout: `playlists/`, `roms/<playlist>/`, and `thumbnails/<playlist>/Named_Snaps/`; use `--lpl-path`, `--rom-dir`, and `--cover-dir` to override those destinations.

## 中文介绍

ROMX 是面向模拟器前端、游戏库和归档工具的开放 ROM 容器规范。

ROMX 文件包含：

- 未修改、可直接加载的标准 ROM；
- 内嵌的 UTF-8 metadata JSON；
- 可选的内嵌 PNG 封面；
- 固定 128 字节 footer，记录偏移、长度和 SHA-256 校验值。

容器扩展名是在原 ROM 扩展名后追加 `x`：`.gba` 变为 `.gbax`，`.nes` 变为 `.nesx`，`.nds` 变为 `.ndsx`。

本仓库定义 ROMX 1.0 Draft 1，包含二进制规范、metadata Schema、平台规则、示例和 Python 参考实现。

中文文档：

- [二进制规范（中文）](docs/ROMX-SPEC_CN.md)
- [Metadata 参数（中文）](docs/METADATA_CN.md)
- [平台与 Payload 格式（中文）](docs/PLATFORMS_CN.md)
- [文件结构（中文）](docs/FILE-STRUCTURE_CN.md)

参考脚本也支持：

```bash
python3 tools/romx.py import-lpl playlist.lpl -o romx-out --rom-root /path/to/rom-root --cover-root /path/to/thumbnails
python3 tools/romx.py export-lpl romx-out -o retroarch-out
```

`import-lpl` 会生成 `000001.gbcx` 形式的连续 ROMX 文件，并按 ROM 文件名匹配 `Named_Snaps/<rom-stem>.png`。可用 `--rom-dir` 和 `--cover-dir` 强制指定平铺目录。`export-lpl` 默认生成 RetroArch 的 `playlists/`、`roms/<playlist>/` 和 `thumbnails/<playlist>/Named_Snaps/` 结构，也可以用 `--lpl-path`、`--rom-dir`、`--cover-dir` 指定输出位置。
