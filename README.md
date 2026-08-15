# ROMX

ROMX is an open container specification for emulator frontends, game
libraries, and archival workflows. This repository defines ROMX 0.2.0 only.

The specification covers the serialized container format: regions, binary
registries, validation, integrity, and mutable-object commit and failure
semantics. Library APIs, VFS adapters, temporary-file policy, database access,
emulator selection, and user interfaces belong to consumer implementations.

A `.romx` file can contain:

- an uncompressed concatenation of one or more unmodified game files;
- a binary RIDX virtual-file index and launch entrypoint;
- optional strict UTF-8 metadata JSON;
- an optional embedded PNG cover;
- an optional fixed-capacity mutable region for saves, cheats, statistics, and
  private data;
- a compact fixed 128-byte footer with region sizes and optional immutable
  SHA-256.

Payload entries are never compressed. Mutable objects occupy indexed,
fixed-capacity extents. Their bytes are opaque by default; the specification
also defines an optional uncompressed SAVE/CHEAT file-bundle profile and a
strict versioned STATS JSON profile for interoperable consumers. Explicit
updates overwrite only the selected extent and its directory entry, without
rewriting the immutable payload or moving the footer. When immutable SHA-256
is enabled, mutable updates do not require recalculating it.

The entrypoint payload begins at file offset zero with no ROMX header or
prefix. For a damaged footer, this preserves the possibility of separately
detecting and exposing an exact native single-file payload in an explicitly
unverified salvage mode.

ROMX 0.2.0 uses one container extension: `.romx`. The footer declares the
platform and launch model; RIDX declares every embedded file's format, virtual
path, byte range, entrypoint status, and optional CRC32.

The 0.2.0 format is under active development and is not frozen.

## Legal and copyright position

ROMX is a content-neutral container specification. It defines how bytes and
descriptive data are organized, validated, and accessed; it does not grant or
imply permission to copy, decrypt, modify, possess, embed, upload, or distribute
the content stored in a ROMX file.

A technically valid ROMX container may contain material protected by copyright,
trademark, contract, or other rights. Format conformance, successful conversion,
a matching checksum or serial, and ownership of an original copy do not by
themselves establish that a particular use is lawful. Game data, firmware,
BIOS files, encryption keys, cover artwork, metadata, manuals, and other
third-party material may each have separate rights and restrictions.

Users and distributors are solely responsible for obtaining any required
authorization and for complying with applicable laws, licenses, platform terms,
and technological-protection rules. Exceptions for backup, preservation,
research, and interoperability vary by jurisdiction and may be narrower than
expected. ROMX must not be represented as a way to legitimize unauthorized
copies or to evade access controls.

The repository's [MIT License](LICENSE) applies only to project-authored
specification text, schemas, examples, and software distributed by this
repository. It grants no license to third-party content placed in a ROMX
container and no rights to third-party names, logos, artwork, databases, or
trademarks. This project does not provide ROMs, disc images, firmware, BIOS
files, encryption keys, or proprietary artwork. Nothing in this repository is
legal advice.

## Documentation

- [Container specification](docs/ROMX-SPEC.md)
- [Platform and launch profiles](docs/PLATFORMS.md)
- [Metadata reference](docs/METADATA.md)
- [Development policy](docs/DEVELOPMENT.md)
- [Metadata JSON Schema](schema/romx-metadata.schema.json)
- [Metadata example](examples/metadata.example.json)

## 中文介绍

ROMX 是面向模拟器前端、游戏库与归档流程的开放容器规范。本仓库只定义 ROMX
0.2.0。

规范只约束容器的序列化格式，包括区域、二进制注册表、验证、完整性，以及 mutable
object 的提交与失败语义。Library API、VFS adapter、临时文件策略、数据库访问、模拟器选择
和用户界面属于消费端实现，不属于容器规范。

一个 `.romx` 文件可以包含：

- 一个或多个未修改游戏文件的不压缩拼接；
- RIDX 二进制虚拟文件索引与启动入口；
- 可选的严格 UTF-8 metadata JSON；
- 可选的内嵌 PNG 封面；
- 用于存档、金手指、统计与私有数据的可选固定容量 mutable region；
- 精简的固定 128 字节 footer，保存区域大小与可选 immutable SHA-256。

Payload entry 永远不压缩。Mutable object 使用带索引的固定容量 extent，内部字节
默认 opaque；规范同时定义可选的无压缩 SAVE/CHEAT 文件 bundle profile 和严格、
版本化的 STATS JSON profile，供 consumer 互操作。显式更新只覆盖所选 extent 及其
directory entry，无需重写 immutable payload，也不会移动 footer。启用 immutable
SHA-256 后，mutable 更新不需要重新计算它。

Entrypoint payload 从文件偏移零开始，前面没有 ROMX header 或 prefix。Footer 损坏
时，这一规则保留了在明确标记为未验证的 salvage mode 中单独识别并暴露准确原生
单文件 payload 的可能性。

ROMX 0.2.0 只使用 `.romx` 扩展名。Footer 声明平台与启动模型；RIDX 声明每个内嵌
文件的格式、虚拟路径、字节范围、启动入口状态与可选 CRC32。

0.2.0 格式仍在开发中，尚未冻结。

中文文档：

- [容器规范](docs/ROMX-SPEC_CN.md)
- [平台与启动 Profile](docs/PLATFORMS_CN.md)
- [Metadata 参数](docs/METADATA_CN.md)
- [开发政策](docs/DEVELOPMENT_CN.md)
