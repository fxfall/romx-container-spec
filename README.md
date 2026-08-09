# ROMX

ROMX is an open ROM container specification for emulator frontends, game libraries, and archival workflows.

A ROMX file contains:

- an unmodified, directly loadable ROM payload;
- embedded UTF-8 metadata JSON;
- an optional embedded PNG cover;
- a fixed 128-byte footer with offsets, lengths, and an optional body SHA-256.

ROMX 0.1.0 uses RetroArch-compatible CRC-32/ISO-HDLC for metadata `crc32`,
serialized as lower-case eight-digit hexadecimal. The footer stores no payload
SHA-256; only the optional container-wide body SHA-256 is stored there.

The container extension is the original ROM extension plus `x`: `.gba` becomes `.gbax`, `.nes` becomes `.nesx`, and `.nds` becomes `.ndsx`.

This repository defines **ROMX 0.1.0**, a stable and frozen binary format. It contains the binary specification, metadata schema, platform rules, examples, conformance fixtures, and a small Python reference implementation.

## Documentation

- [Binary specification](docs/ROMX-SPEC.md)
- [Metadata reference](docs/METADATA.md)
- [Platforms and payload formats](docs/PLATFORMS.md)
- [Container structure](docs/FILE-STRUCTURE.md)
- [Metadata JSON Schema](schema/romx-metadata.schema.json)
- [Conformance fixtures](docs/CONFORMANCE.md)

## Reference implementation

The [Python reference implementation](tools/romx.py) demonstrates how to create, inspect, verify, and extract a ROMX file. Install [Pillow](requirements.txt) when converting JPG, JPEG, WebP, GIF, or BMP covers, or when resizing any cover.

```bash
pip install -r requirements.txt
python3 tools/romx.py pack game.gba metadata.json -o game.gbax --cover cover.png
# Metadata is optional; this writes payload plus footer only.
python3 tools/romx.py pack game.gba -o game.gbax
# Optional database identity override; without it CRC32 is regenerated from game.gba.
python3 tools/romx.py pack game.gba metadata.json -o game.gbax --crc32 0123abcd
# Convert any supported image and resize it to an exact resolution.
python3 tools/romx.py pack game.gba metadata.json -o game.gbax --cover cover.webp --cover-size 320x320
# Optional container-wide body SHA-256; disabled by default for conversion speed.
python3 tools/romx.py pack game.gba metadata.json -o game.gbax --body-sha256
python3 tools/romx.py inspect game.gbax
python3 tools/romx.py verify game.gbax
python3 tools/romx.py extract game.gbax extracted/
python3 tools/romx.py import-lpl playlist.lpl -o romx-out --rom-root /path/to/rom-root --cover-root /path/to/thumbnails
# The same optional body hash switch is available for import-lpl.
python3 tools/romx.py import-lpl playlist.lpl -o romx-out --body-sha256
python3 tools/romx.py export-lpl romx-out -o retroarch-out
```

The script is an implementation guide and validation aid, not a production packer.

`import-lpl` creates sequential names such as `000001.gbcx`, matching each LPL item to a ROM and (when available) `Named_Snaps/<rom-stem>.png`. It regenerates each metadata CRC32 from the original ROM by default; use `--crc32 0123abcd` to apply an explicit lookup override. PNG is preserved byte-for-byte by default; non-PNG covers are converted to PNG, and `--cover-size 320x320` converts/resizes every cover. The generated `cover` metadata is derived from the normalized PNG that is actually embedded. With no `--rom-root` or `--cover-root`, real absolute ROM paths and RetroArch virtual `/roms/...` paths are resolved from the LPL location, and the sibling thumbnail tree is inferred. Only database-compatible game information is written to ROMX metadata; LPL-only fields such as paths, core selection, playlist settings, and playback state are handled transiently by the converter. Use `--rom-dir` and `--cover-dir` to force flat lookup directories. `export-lpl` writes the default RetroArch layout: `playlists/`, `roms/<playlist>/`, and `thumbnails/<playlist>/Named_Snaps/`; use `--lpl-path`, `--rom-dir`, and `--cover-dir` to override those destinations.

## 中文介绍

ROMX 是面向模拟器前端、游戏库和归档工具的开放 ROM 容器规范。

ROMX 文件包含：

- 未修改、可直接加载的标准 ROM；
- 内嵌的 UTF-8 metadata JSON；
- 可选的内嵌 PNG 封面；
- 固定 128 字节 footer，记录偏移、长度和可选的 body SHA-256。

ROMX 0.1.0 的 metadata `crc32` 使用与 RetroArch 兼容的 CRC-32/ISO-HDLC，序列化为
8 位小写十六进制。Footer 不保存 payload SHA-256，只保存可选的容器 body SHA-256。

容器扩展名是在原 ROM 扩展名后追加 `x`：`.gba` 变为 `.gbax`，`.nes` 变为 `.nesx`，`.nds` 变为 `.ndsx`。

本仓库定义 **ROMX 0.1.0**，这是稳定且冻结的二进制格式，包含二进制规范、metadata Schema、平台规则、示例、冻结一致性夹具和 Python 参考实现。

中文文档：

- [二进制规范（中文）](docs/ROMX-SPEC_CN.md)
- [Metadata 参数（中文）](docs/METADATA_CN.md)
- [平台与 Payload 格式（中文）](docs/PLATFORMS_CN.md)
- [文件结构（中文）](docs/FILE-STRUCTURE_CN.md)
- [一致性冻结夹具（中文）](docs/CONFORMANCE_CN.md)

参考脚本也支持：

```bash
# metadata 可省略；此命令只写入 payload 和 footer。
python3 tools/romx.py pack game.gba -o game.gbax
python3 tools/romx.py import-lpl playlist.lpl -o romx-out --rom-root /path/to/rom-root --cover-root /path/to/thumbnails
# 可选的容器 body SHA-256；默认关闭以减少转换时的重复读取。
python3 tools/romx.py import-lpl playlist.lpl -o romx-out --body-sha256
python3 tools/romx.py export-lpl romx-out -o retroarch-out
```

`import-lpl` 会生成 `000001.gbcx` 形式的连续 ROMX 文件，并按 ROM 文件名匹配 `Named_Snaps/<rom-stem>.png`。PNG 默认逐字节保留，其他支持的图片会转换为 PNG，`--cover-size` 可统一调整尺寸；生成的 `cover` 元数据来自实际内嵌的标准化 PNG。可用 `--rom-dir` 和 `--cover-dir` 强制指定平铺目录。`export-lpl` 默认生成 RetroArch 的 `playlists/`、`roms/<playlist>/` 和 `thumbnails/<playlist>/Named_Snaps/` 结构，也可以用 `--lpl-path`、`--rom-dir`、`--cover-dir` 指定输出位置。
