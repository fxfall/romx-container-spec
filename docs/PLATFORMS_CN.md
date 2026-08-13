# 平台与 Payload 格式

`platform` 标识主机平台系列；`payload_format` 标识提取后交给模拟器核心的标准 ROM 格式。两者都不会修改 payload 或 footer。

| 平台 | Payload 格式 | 标准扩展名 | 识别提示 |
|---|---|---|---|
| `gb` | `gb` | `.gb` | Nintendo logo 和 Header 标记 |
| `gbc` | `gbc` | `.gbc` | Nintendo logo 和 CGB flag |
| `gba` | `gba` | `.gba` | GBA logo 和固定 Header 值 `0x96` |
| `nes` | `nes` | `.nes` | iNES/NES 2.0 magic `NES 1A` |
| `nes` | `fds` | `.fds` | 存在时使用 FDS Header `FDS 1A` |
| `snes` | `sfc` | `.sfc` | LoROM/HiROM/ExHiROM 内部 Header |
| `snes` | `smc` | `.smc` | 可能包含 512 字节 copier header |
| `nds` | `nds` | `.nds` | Nintendo DS Header 和 logo |
| `3ds` | `3ds` | `.3ds` | `0x100` 偏移处的 NCSD 结构 |
| `3ds` | `cci` | `.cci` | NCSD 容器，与 `.3ds` 同类 |
| `genesis` | `md` | `.md` | `0x100` 偏移处通常为 `SEGA` |
| `genesis` | `gen` | `.gen` | 与 `.md` 同类格式 |
| `genesis` | `smd` | `.smd` | 交错格式，通常带 copier header |

这些内容只是识别辅助。读取器不能仅凭有歧义的扩展名判断平台。可信 ROM Header 优先于 metadata 和文件名提示。

### Game Boy CGB flag

Game Boy payload 应检查 ROM Header 偏移 `0x143` 的 CGB flag：

- `0xC0`：无论文件名或 playlist 如何，强制分类为 `gbc`；
- `0x80`：表示同时兼容 GB/GBC，使用有效 ROMX `payload_format`（`gb` 或 `gbc`）分类，不得猜测；
- 其他值：保留已经有效的 `payload_format`（`gb` 或 `gbc`），不能仅凭该字节推断新的分类。

`0x80` ROM 如果缺少或没有有效的 `payload_format`，必须报告为分类不明确。

ROMX 容器扩展名是在原 ROM 扩展名后追加 `x`：`.gba` 变为 `.gbax`，`.sfc` 变为 `.sfcx`，`.cci` 变为 `.ccix`。

`.cia` 与存在歧义的 Mega Drive `.bin` 不属于 ROMX 0.1.x payload profile。
它们保留到 ROMX 0.2.0，待加载与识别规则明确后再定义对应 profile。
