# Platforms and Payload Formats

`platform` identifies the platform; `payload_format` identifies the standard ROM format that the emulator core receives after extraction.

Use lowercase ASCII IDs. A new platform must define at least one payload format and a recognition strategy. Do not identify ambiguous formats such as `.bin` by extension alone. The container extension is the original ROM extension plus `x` (for example, `.gba` becomes `.gbax`). Readers must validate the ROMX footer.

---

# 平台与 Payload 格式

`platform` 表示平台，`payload_format` 表示实际 ROM 格式。一个平台可以对应多个格式。

| platform | 平台 | payload_format | 标准扩展名 | Header/结构识别提示 |
|---|---|---|---|---|
| `gb` | Game Boy | `gb` | `.gb` | Nintendo logo、CGB flag |
| `gbc` | Game Boy Color | `gbc` | `.gbc` | Nintendo logo、CGB flag |
| `gba` | Game Boy Advance | `gba` | `.gba` | GBA logo、固定值 `0x96` |
| `nes` | NES/Famicom | `nes` | `.nes` | iNES/NES 2.0：`NES 1A` |
| `nes` | Famicom Disk System | `fds` | `.fds` | 有头格式：`FDS 1A`；无头格式需提示 |
| `snes` | SNES/Super Famicom | `sfc` | `.sfc` | LoROM/HiROM/ExHiROM internal header |
| `snes` | SNES copier image | `smc` | `.smc` | 可能包含 512-byte copier header |
| `nds` | Nintendo DS | `nds` | `.nds` | NDS Header 和 Nintendo logo |
| `3ds` | Nintendo 3DS cartridge | `3ds` | `.3ds` | NCSD：offset `0x100` 为 `NCSD` |
| `3ds` | Nintendo 3DS cartridge | `cci` | `.cci` | NCSD，与 `.3ds` 同类 |
| `3ds` | Nintendo 3DS installable archive | `cia` | `.cia` | CIA section/header 结构 |
| `genesis` | Mega Drive/Genesis | `md` | `.md` | offset `0x100` 通常为 `SEGA` |
| `genesis` | Mega Drive/Genesis | `gen` | `.gen` | 与 `.md` 同类 |
| `genesis` | Super Magic Drive dump | `smd` | `.smd` | 交错格式，通常有 copier header |
| `genesis` | Mega Drive binary | `bin` | `.bin` | 必须结合 Header 判断，扩展名本身不唯一 |

## 平台 ID 规则

- 使用小写 ASCII；
- 平台 ID 不绑定品牌展示名称；
- 新增平台必须同时定义至少一个 payload_format 和识别策略；
- `payload_format` 必须描述核心能够直接加载的解包结果；
- 不确定格式时不得仅凭 `.bin` 等通用扩展名断言平台。

## 文件名建议

```text
Title.nesx
Title.sfcx
Title.ndsx
Title.mdx
Title.ciax
```

双扩展名只提供提示，不是安全边界。读取器必须检查 ROMX footer。
