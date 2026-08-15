# ROMX 0.2.0 容器规范

**状态：正在开发，尚未冻结。** ROMX 0.2.0 定义 footer wire version `2` 与
metadata schema version `0.2.0`。在项目明确冻结格式前，字节语义仍可能变化。

Reader 必须先验证 footer 的 wire version，再解释任何与版本相关的字段。

所有整数均为无符号小端序。除非章节另有规定，新文件的所有 reserved 字段和
保留 flag 位必须为零；Reader 遇到非零值必须拒绝。

## 1. 设计模型

ROMX 0.2.0 将不可变游戏内容与可变用户数据分离：

```text
payload data
payload index
可选 metadata JSON
可选 PNG cover
可选的零值对齐填充
固定容量 mutable region
128 字节 footer
```

以上物理顺序是强制的。Payload 是一个或多个源文件未经压缩的字节拼接。
Payload index 是权威虚拟文件目录。Metadata 描述游戏，但不得包含字节偏移或主机
路径。

精简 footer 只保存无法根据固定布局推导的值。Mutable region 拥有固定 object
directory 和固定容量的 object extent。显式更新可以覆盖这些 extent，而不会修改
或移动 footer、payload、payload index、metadata 或 cover。

## 2. 顶层布局与分区规则

Payload 从文件偏移零开始。RIDX 从 `payload_size` 开始，其大小根据验证后的
`entry_count` 推导。Metadata、cover、对齐填充和 mutable region 存在时按该顺序
排列。Footer 占据文件末尾 128 字节。

Footer 前的每个字节必须且只能属于以下一种内容：

- payload 文件数据或零值 payload 对齐填充；
- payload index；
- metadata；
- cover；
- 零值 immutable 对齐填充；
- mutable region。

所有区域以及经过溢出检查的整数加法都不得溢出、重叠或越过 footer。唯一允许的
间隔是本规范明确规定的零值填充。

存在 mutable region 时，`mutable_offset` 必须按 4096 字节对齐。Cover（或此前
最后一个存在的区域）结束位置到 `mutable_offset` 之间的零字节属于 immutable
对齐填充。不存在 mutable region 时，顶层区域末尾不允许填充。

以下经过溢出检查的等式属于强制规则：

- `payload_offset == 0`，并且 `payload_index_offset == payload_size`；
- `payload_index_size == 64 + entry_count * 512`，并且
  `index_end == payload_size + payload_index_size`；
- `metadata_size > 0` 时，`metadata_offset == index_end`；
- `cover_size > 0` 时，`cover_offset == index_end + metadata_size`；
- `immutable_content_end == index_end + metadata_size + cover_size`；
- `mutable_capacity > 0` 时，`mutable_offset == footer_offset -
  mutable_capacity`、`mutable_offset == align_up(immutable_content_end, 4096)`，
  并且 `mutable_capacity` 是 4096 的倍数且至少为 12288 字节；
- `mutable_capacity == 0` 时不存在 mutable region，并且
  `footer_offset == immutable_content_end`。

以上 offset 都是推导值，不是 footer 字段。Metadata 或 cover size 为零表示对应区域
不存在，不得解释其 offset。Metadata 仍是一条严格 JSON 字节序列，cover 仍是一条
PNG 字节序列，与既有 ROMX 区域模型一致；两者都不是 RIDX entry。

## 3. Footer

Footer 固定为文件末尾的 128 字节。

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `ROMX` |
| `0x04` | 4 | uint32 | `wire_version` | 必须为 `2` |
| `0x08` | 8 | uint64 | `payload_size` | 必须大于零；RIDX 从这里开始 |
| `0x10` | 8 | uint64 | `metadata_size` | 零表示不存在 |
| `0x18` | 8 | uint64 | `cover_size` | 零表示不存在 |
| `0x20` | 8 | uint64 | `mutable_capacity` | 固定物理容量；零表示不存在 |
| `0x28` | 2 | uint16 | `platform_id` | 第 3.2 节平台注册表 |
| `0x2A` | 2 | uint16 | `launch_format_id` | 第 3.3 节启动格式注册表 |
| `0x2C` | 4 | uint32 | `immutable_hash_algorithm` | 见 3.1 节 |
| `0x30` | 32 | bytes | `immutable_sha256` | SHA-256 或全零 |
| `0x50` | 4 | uint32 | `footer_crc32` | 完整 footer 的 CRC32 |
| `0x54` | 44 | bytes | `reserved` | 全部为零；为未来 wire version 预留 |

计算 `footer_crc32` 时，将 `0x50..0x53` 视为零，然后对完整的 128 字节 footer
（包括 reserved 字节）计算第 8 节定义的 CRC32。

### 3.1 Immutable hash algorithm

| Value | Name | Requirement |
|---:|---|---|
| `0` | `NONE` | `immutable_sha256` 为 32 个零字节；不声明 immutable hash |
| `1` | `SHA256` | 对 immutable range 验证 `immutable_sha256` |

其他值在 ROMX 0.2.0 中无效。`mutable_capacity > 0` 时，immutable range 为
`[0, mutable_offset)`；否则为 `[0, footer_offset)`。它永远不覆盖 mutable region
或 footer。

ROMX 0.2.0 writer 必须把全部 44 个 reserved 字节写为零，ROMX 0.2.0 reader 遇到
任意非零值必须拒绝该 footer。未来只有新的 footer wire version 才能定义这些字节。

### 3.2 平台注册表

`platform_id` 是权威平台分类。Metadata 不再重复保存它。

| Value | Name | Platform |
|---:|---|---|
| `0x0000` | `UNSPECIFIED` | 没有可靠的平台声明 |
| `0x0001` | `GAME_BOY` | Game Boy |
| `0x0002` | `GAME_BOY_COLOR` | Game Boy Color |
| `0x0003` | `GAME_BOY_ADVANCE` | Game Boy Advance |
| `0x0004` | `NES` | Nintendo Entertainment System / Famicom |
| `0x0005` | `SNES` | Super Nintendo / Super Famicom |
| `0x0006` | `NINTENDO_64` | Nintendo 64 |
| `0x0007` | `NINTENDO_DS` | Nintendo DS |
| `0x0008` | `NINTENDO_3DS` | Nintendo 3DS |
| `0x0010` | `MASTER_SYSTEM` | Sega Master System |
| `0x0011` | `GAME_GEAR` | Sega Game Gear |
| `0x0012` | `MEGA_DRIVE` | Mega Drive / Genesis |
| `0x0013` | `MEGA_DRIVE_32X` | Mega Drive 32X |
| `0x0014` | `SEGA_CD` | Sega CD / Mega-CD |
| `0x0015` | `SEGA_SATURN` | Sega Saturn |
| `0x0016` | `DREAMCAST` | Sega Dreamcast |
| `0x0020` | `PC_ENGINE` | PC Engine / TurboGrafx-16 |
| `0x0021` | `PC_ENGINE_CD` | PC Engine CD / TurboGrafx-CD |
| `0x0030` | `PLAYSTATION` | Sony PlayStation |
| `0x0031` | `PLAYSTATION_2` | Sony PlayStation 2 |
| `0x0032` | `PSP` | PlayStation Portable |
| `0x0040` | `GAMECUBE` | Nintendo GameCube |
| `0x0041` | `WII` | Nintendo Wii |
| `0x0050` | `ARCADE` | Arcade ROM set |
| `0x0060` | `SCUMMVM` | ScummVM 游戏数据 |
| `0x0061` | `DOS` | DOS 游戏数据 |
| `0x0062` | `AMIGA` | Amiga 游戏数据 |

`0x0000` 永远不表示“自动识别”，而是声明尚未确定。Reader 可以另外返回明确标注
为推测的检测结果，但该推测不是保存声明。正常可启动的 writer 必须写入已注册的
非零值；`UNSPECIFIED` 只允许用于导入、恢复或用户明确选择的未分类内容。

### 3.3 启动格式注册表

`launch_format_id` 描述 RIDX entrypoint 与相关 entry 如何组成可加载内容。它不
替代 entrypoint 自己的 `format_id`。

| Value | Name | Meaning |
|---:|---|---|
| `0x0000` | `UNSPECIFIED` | 没有可靠的启动合约 |
| `0x0001` | `RAW_SINGLE_FILE` | Entrypoint 本身就是完整的逻辑启动文件 |
| `0x0002` | `CUE` | CUE 描述文件及其引用文件 |
| `0x0003` | `GDI` | GDI 描述文件及其引用轨道 |
| `0x0004` | `M3U` | 多碟 playlist 及其引用的光盘 entrypoint |
| `0x0005` | `CCD` | CloneCD 描述文件集合 |
| `0x0006` | `MDS` | Media Descriptor 集合 |
| `0x0007` | `TOC` | TOC 描述文件及其引用文件 |
| `0x0008` | `DIRECTORY` | 带 ROMX 启动描述文件的索引目录 |
| `0x0009` | `ROMSET` | 展开的街机 ROM set 与逻辑依赖 |
| `0x000A` | `SPLIT_FILE_SET` | 被多个索引文件分割的一个逻辑镜像 |

ISO、CSO、ZSO、CHD、PBP、CDI、RVZ、WIA 等自包含镜像都使用
`RAW_SINGLE_FILE`；准确格式来自 entrypoint 的 RIDX entry。`UNSPECIFIED` 与平台
未声明具有相同的未解决启动行为，不是自动检测指令。

### 3.4 注册范围与未知值

平台、启动格式和 RIDX 文件格式注册表统一保留以下范围：

| Range | Meaning |
|---:|---|
| `0x0000` | 对应字段定义的未声明或未知 |
| `0x0001–0x7FFF` | ROMX 官方注册值 |
| `0x8000–0xFFFE` | 私有或实验用途 |
| `0xFFFF` | 永久禁止 |

已注册值永远不得重新分配。新增值不会改变旧值含义。除 `0xFFFF` 外，未知值本身
不会让容器成为结构损坏：Reader 仍可验证和暴露文件，但必须报告不支持的平台或
格式。私有值只有在 producer 与 consumer 共享定义时才能互操作。

## 4. Payload 与 RIDX payload index

容器不得压缩、加密、补丁修改、字节交换或重写 payload 字节。每个内嵌源文件
占用一段由索引描述的字节范围。Writer 可以在 entry 之间插入用于对齐的零填充；
payload 区域内所有未被 entry 索引的字节都必须为零。

ROMX 不得在 payload 前添加 header、prefix、marker、对齐字节或其他容器自有字节。
Entrypoint 必须从文件绝对偏移零开始，因此它的第一个字节必须与保存的源文件第一个
字节完全相同。对齐填充只能出现在某个已索引文件之后，绝不能位于 entrypoint 前。
RIDX 及其他所有 ROMX 结构都位于 payload 之后。

Payload index 由 64 字节 header 及紧随其后的 `entry_count` 个固定 512 字节 entry
组成。每个 entry 直接包含自己的 UTF-8 虚拟路径。RIDX 没有独立 string table、
entry ID 命名空间，也没有空闲或未使用 slot。

### 4.1 RIDX header

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `RIDX` |
| `0x04` | 2 | uint16 | `index_version` | 必须为 `1` |
| `0x06` | 2 | uint16 | `header_size` | 必须为 `64` |
| `0x08` | 4 | uint32 | `entry_count` | 至少为一 |
| `0x0C` | 4 | uint32 | `entry_size` | 必须为 `512` |
| `0x10` | 4 | uint32 | `flags` | ROMX 0.2.0 中为零 |
| `0x14` | 4 | uint32 | `index_crc32` | 完整 index 的 CRC32 |
| `0x18` | 40 | bytes | `reserved` | 全部为零 |

计算 `index_crc32` 时，将 `0x14..0x17` 视为零，并对完整 payload-index 区域计算
CRC32。使用经过溢出检查的算术时，`payload_index_size` 必须恰好等于
`64 + entry_count * 512`；该区域在最后一个 entry 后不得包含其他字节。

### 4.2 RIDX entry

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | uint32 | `flags` | 见 4.3 节 |
| `0x04` | 2 | uint16 | `format_id` | 第 4.4 节文件格式注册表 |
| `0x06` | 2 | uint16 | `path_size` | UTF-8 字节长度，1–480 |
| `0x08` | 8 | uint64 | `data_offset` | 相对于 payload 起点 |
| `0x10` | 8 | uint64 | `data_size` | 内嵌字节长度 |
| `0x18` | 4 | uint32 | `crc32` | 恰好覆盖内嵌字节的可选 CRC32 |
| `0x1C` | 4 | uint32 | `reserved` | 为零 |
| `0x20` | 480 | bytes | `path` | `path_size` 字节，之后以零填充 |

所有非空内嵌范围必须位于 payload 内并且不得重叠。内嵌空文件的
`data_size == 0`，`data_offset` 必须在范围内。`path` 中 `path_size` 之后的每个
字节必须为零。必须恰好有一个 entrypoint，并且它必须满足 `data_size > 0` 和非零
`format_id`，同时 `data_offset == 0`。

每个 RIDX entry 都描述实际存在于 payload 中的字节。ROMX 不在 RIDX 中表示外部
依赖。所需 firmware、共享 BIOS、父集内容、设备 ROM 及其他运行时依赖由 consumer
解析，不属于容器格式。

### 4.3 Entry flags

| Bit | Name | Meaning |
|---:|---|---|
| 0 | `ENTRYPOINT` | 这是唯一的启动 entry |
| 1 | `HAS_CRC32` | `crc32` 保存恰好覆盖本 entry 字节的 CRC32 |
| 2–31 | Reserved | 为零 |

必须恰好一个 entry 设置 `ENTRYPOINT`，其他 entry 必须清除该位。设置
`HAS_CRC32` 时，`crc32` 强制存在并按照第 8 节验证；这也适用于 CRC32 为
`00000000` 的空文件。未设置 `HAS_CRC32` 时，`crc32` 必须为零，表示该 entry 没有
保存 checksum。因此零 CRC32 不存在歧义：只有设置 `HAS_CRC32` 时它才是校验值。

### 4.4 RIDX 文件格式注册表

`format_id` 是单个 RIDX entry 的权威格式。虚拟路径保留原始文件名和扩展名，作为
容器虚拟文件树的一部分。

| Value | Name | Typical extension or role |
|---:|---|---|
| `0x0000` | `UNKNOWN` | 无法识别的非 entrypoint 文件 |
| `0x0001` | `GB` | `.gb` |
| `0x0002` | `GBC` | `.gbc` |
| `0x0003` | `GBA` | `.gba` |
| `0x0004` | `NES` | `.nes` |
| `0x0005` | `UNF` | `.unf` |
| `0x0006` | `UNIF` | `.unif` |
| `0x0007` | `FDS` | `.fds` |
| `0x0008` | `SFC` | `.sfc` |
| `0x0009` | `SMC` | `.smc` |
| `0x000A` | `NDS` | `.nds` |
| `0x000B` | `N3DS` | `.3ds` |
| `0x000C` | `CCI` | `.cci` |
| `0x000D` | `CXI` | `.cxi` |
| `0x000E` | `APP` | `.app` |
| `0x0010` | `ISO` | `.iso` |
| `0x0011` | `CSO` | `.cso` |
| `0x0012` | `ZSO` | `.zso` |
| `0x0013` | `CHD` | `.chd` |
| `0x0014` | `PBP` | `.pbp` |
| `0x0015` | `CDI` | `.cdi` |
| `0x0016` | `GCM` | `.gcm` |
| `0x0017` | `WBFS` | `.wbfs`、`.wbf1` 及后续分段 |
| `0x0018` | `RVZ` | `.rvz` |
| `0x0019` | `WIA` | `.wia` |
| `0x001A` | `WAD` | `.wad` |
| `0x0020` | `CUE` | `.cue` |
| `0x0021` | `GDI` | `.gdi` |
| `0x0022` | `M3U` | `.m3u` |
| `0x0023` | `CCD` | `.ccd` |
| `0x0024` | `MDS` | `.mds` |
| `0x0025` | `TOC` | `.toc` |
| `0x0030` | `BIN` | `.bin` 轨道 |
| `0x0031` | `WAV` | `.wav` 音频轨道 |
| `0x0032` | `FLAC` | `.flac` 音频轨道 |
| `0x0033` | `IMG` | `.img` 镜像或轨道 |
| `0x0034` | `MDF` | `.mdf` 镜像 |
| `0x0040` | `SBI` | `.sbi` 伴随文件 |
| `0x0041` | `SUB` | `.sub` 伴随文件 |
| `0x0042` | `ECM` | `.ecm` 伴随文件或编码轨道 |
| `0x0050` | `Z64` | `.z64` |
| `0x0051` | `N64` | `.n64` |
| `0x0052` | `V64` | `.v64` |
| `0x0060` | `MD` | `.md` |
| `0x0061` | `GEN` | `.gen` |
| `0x0062` | `SMD` | `.smd` |
| `0x0063` | `X32` | `.32x` |
| `0x0064` | `SMS` | `.sms` |
| `0x0065` | `GG` | `.gg` |
| `0x0066` | `PCE` | `.pce` |
| `0x0070` | `ELF` | `.elf` |
| `0x0071` | `PRX` | `.prx` |
| `0x0080` | `MSU` | `.msu` |
| `0x0081` | `PCM` | `.pcm` |
| `0x0090` | `ROMX_LAUNCH_DESCRIPTOR` | 为虚拟目录或 ROM set 生成的启动描述文件 |

`UNKNOWN` 允许用于非 entrypoint auxiliary 文件。启动 entrypoint 必须使用非零
标准值或私有值。`0xFFFF` 始终无效。

### 4.5 路径、描述文件与 entrypoint

路径使用严格 UTF-8、Unicode NFC 和 `/` 分隔符。路径必须是相对路径，禁止包含
NUL、反斜杠、空组件、`.` 或 `..` 组件、前导斜杠或结尾斜杠。Unicode 大小写
折叠后不得有两个路径冲突。Path 占据 entry 固定 path 字段的前 `path_size` 个
字节，并且不以 NUL 结尾。

作为 entrypoint 保存的描述文件必须通过规范化相对路径引用其他 entry。Writer
导入包含绝对路径或其他不可移植引用的 CUE、GDI 或 M3U 时，可以把原文件保留为
非 entrypoint auxiliary 文件，同时生成一个规范化启动描述文件作为 entrypoint。

单文件游戏的 entrypoint 就是该文件。多文件游戏的 entrypoint 通常是 CUE、GDI、
M3U、CCD、MDS、TOC 或其他描述文件。`.chd`、`.pbp`、`.cdi`、`.iso`、`.rvz`
等自包含镜像仍然是单个 entry，不得仅因为内部文件系统包含多个文件而拆分。

单文件容器必须满足：`entry_count == 1`、唯一 entry 设置 `ENTRYPOINT`、
`data_offset == 0`、`data_size == payload_size`，并且 payload 不包含对齐填充。多文件
容器必须满足 `entry_count > 1`；该状态从 RIDX 推导，不在 footer 中重复保存。这样
reader 可以直接暴露单文件 payload，同时继续使用同一种 RIDX 解析模型。

所有 ROMX 0.2.0 容器统一使用 `.romx` 扩展名。原始文件名和扩展名只存在于 RIDX
虚拟路径。Writer 不得根据 entry 的源格式派生容器扩展名。

### 4.6 Footer 损坏后的 salvage

正常 ROMX 解析从 footer 开始。Footer 缺失、截断或无效时，容器结构无效，任何保存
边界都不得视为可信。不过，零偏移且无前缀的 payload 规则允许实现提供独立的尽力
恢复模式。

Salvage reader 可以从文件偏移零开始检查原生格式 signature 与 header。只有平台专用
解析器能够可靠确定准确 payload 长度时，才可以暴露恢复出的单文件 payload。它也
可以把未受信任的 footer 值作为搜索提示，或者在可能的 payload 边界之后搜索 RIDX
候选；但候选必须通过完整 CRC32 及所有适用的单文件关系验证，才能作为辅助证据。
仅匹配格式 signature 或仅发现 ASCII `RIDX` 都不充分。

恢复内容必须明确报告为 salvaged 且 unverified，绝不能报告为结构有效的 ROMX
容器。Consumer 只能把恢复出的有界字节范围传给核心，不能传递整个损坏的 `.romx`
文件。无法确定准确原生 payload 边界时，禁止自动启动。Salvage mode 不得把 metadata、
cover 或 mutable data 作为可信内容暴露，也不得执行 mutable write-back；除非用户另行
明确操作，否则不得修复源文件。

## 5. Metadata 与 cover

Metadata 是可选的无 BOM 严格 UTF-8 JSON，并遵循 RFC 8259。每一层 object 的
member name 都必须唯一。转义后未配对的 UTF-16 surrogate 无效。顶层值必须符合
`schema/romx-metadata.schema.json`，并使用
`schema_version: "0.2.0"`。

Metadata 不得包含 payload offset、mutable offset、主机路径、平台或启动格式声明，
也不得包含外部 cover 路径。`crc32` 仍是可选数据库查询标识。RIDX entry 设置
`HAS_CRC32` 时，该值是内嵌 entry 的完整性校验，与 metadata 查询标识彼此独立。
对于多文件集合，除非 `origin_crc32` 明确表示 entrypoint 字节，否则应省略。

ROMX 0.2.0 的 cover profile 不变：它必须是恰好一条 PNG 字节流；IHDR 为第一个 chunk
且只能出现一次；宽高非零；PNG color-type/bit-depth 组合合法；必须存在连续的
IDAT；满足必要的 PLTE 规则；每个 chunk 边界和 CRC 正确；必须存在一个零长度
IEND，且 IEND 是最后一个 chunk，后面没有任何字节。未知 critical chunk 无效。

无效 metadata 或 cover 可以被报告并忽略，不妨碍访问结构有效的 payload。RIDX
是强制结构区域。

## 6. Mutable region

Mutable region 是可选、物理分配且容量固定的持久化用户数据空间。它不属于
immutable SHA-256 范围。它不是虚拟 payload 文件，也不用于直接映射给模拟器核心。
它包含固定 header、固定 object directory，以及由互不重叠的 object extent 组成的
data area：

```text
header (4096) | fixed object directory | object extents and free space
```

Mutable region 不是 append-only log，也不保存 snapshot 历史。更新只原位覆盖所选
object 已分配的 extent 和对应 directory slot。除非采用 6.4.1 或 6.4.2 节的互操作
profile，否则 ROMX 将 object 字节视为 opaque data。ROMX 不重新解释核心的原生
存档字节、金手指语法或 producer 私有格式。

稀疏文件行为不属于 ROMX。Writer 不得依赖容器被复制或下载后仍保留 hole 的稀疏
属性。

### 6.1 Mutable header

Mutable header 固定为 4096 字节，在创建 mutable region 时写入。普通 object 更新
不得修改它。

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `RMUT` |
| `0x04` | 2 | uint16 | `mutable_version` | 必须为 `1` |
| `0x06` | 2 | uint16 | `header_size` | 必须为 `4096` |
| `0x08` | 4 | uint32 | `entry_size` | 必须为 `512` |
| `0x0C` | 4 | uint32 | `entry_capacity` | 必须是 8 的倍数且至少为 8 |
| `0x10` | 8 | uint64 | `directory_offset` | 必须为 `4096` |
| `0x18` | 8 | uint64 | `directory_size` | 必须等于 `entry_capacity * 512` |
| `0x20` | 8 | uint64 | `data_area_offset` | 必须等于 `4096 + directory_size`，并按 4096 字节对齐 |
| `0x28` | 8 | uint64 | `data_area_size` | 必须等于 `mutable_capacity - data_area_offset` 且大于零 |
| `0x30` | 4 | uint32 | `flags` | ROMX 0.2.0 中为零 |
| `0x34` | 4 | uint32 | `header_crc32` | 完整 4096 字节 header 的 CRC32 |
| `0x38` | 4040 | bytes | `reserved` | 全部为零 |

计算 `header_crc32` 时，将 `0x34..0x37` 视为零。所有算术必须经过溢出检查。
Directory 紧接 header，二者之间没有 gap。每个未使用的 directory slot 必须是 512
个零字节。未分配 data extent 内的字节不解释，也不要求为零。

### 6.2 Mutable directory entry

每个非空 directory slot 是一个 512 字节 entry。全零 slot 表示 `EMPTY`，没有 object
identity，也没有已分配 extent。

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `MENT` |
| `0x04` | 2 | uint16 | `state` | 见 6.3 节 |
| `0x06` | 2 | uint16 | `namespace` | 见 6.4 节 |
| `0x08` | 4 | uint32 | `flags` | ROMX 0.2.0 中为零 |
| `0x0C` | 4 | uint32 | `key_size` | UTF-8 字节数，1–448 |
| `0x10` | 8 | uint64 | `data_offset` | 相对 mutable 起点，按 64 字节对齐 |
| `0x18` | 8 | uint64 | `data_capacity` | 已分配的 extent 容量，必须大于零 |
| `0x20` | 8 | uint64 | `data_size` | 当前 opaque data 长度，不得大于 `data_capacity` |
| `0x28` | 8 | uint64 | `generation` | 每次尝试替换时递增，从 1 开始 |
| `0x30` | 8 | uint64 | `modified_unix_seconds` | UTC Unix 时间；未知时为零 |
| `0x38` | 4 | uint32 | `data_crc32` | 恰好 `data_size` 字节的 CRC32 |
| `0x3C` | 4 | uint32 | `entry_crc32` | 完整 512 字节 entry 的 CRC32 |
| `0x40` | 448 | bytes | `key` | `key_size` 个字节，之后全部零填充 |

计算 `entry_crc32` 时，将 `0x3C..0x3F` 视为零。Key 遵循 RIDX 路径规则，相对于
所属 namespace，并且不是主机路径。`(namespace, key)` 组成 object identity，所有
非空且结构有效的 slot 之间不得重复。

每个非空 entry extent 必须完全位于 mutable data area 内，所有加法必须经过溢出
检查。所有非空且结构有效的 slot，其 extent 不得重叠，包括 `WRITING` 与
`DELETING` 状态。`data_size` 到 `data_capacity` 之间的字节不属于 object value，
reader 不得暴露。

Identity 重复或 extent 重叠时，所有涉及的 slot 都必须隔离；其他无关的有效 object
仍然可用。

`data_size` 可以为零，此时 CRC32 必须为 `00000000`。ROMX 不对 mutable object data
应用 codec、压缩、加密或任何字节转换。下述无压缩 bundle 只为多个原始文件增加
边界描述，文件字节保持不变。

### 6.3 Entry state

| Value | Name | Reader behavior |
|---:|---|---|
| `1` | `ACTIVE` | Entry 与 data CRC32 全部通过验证后才暴露 object |
| `2` | `WRITING` | 不暴露 object；其 extent 继续视为已分配 |
| `3` | `DELETING` | 将 object 视为不存在；清空 slot 前 extent 继续保留 |

零值只由全零 empty slot 表示，其他值无效。无效或中断写入的 entry 必须隔离：其
object 不可用，可能占用的 extent 在显式修复或删除清空 slot 前不得复用。只要存在
非零但结构无效的 slot，writer 就不得分配或移动 extent，因为该 slot 的范围不可信；
仍可在原 extent 上替换其他已有的有效 object。

### 6.4 Mutable namespace

| Value | Name | Meaning |
|---:|---|---|
| `1` | `SAVE` | 原生持久游戏数据，包括 RAM、RTC、memory card 镜像或存档目录文件 |
| `2` | `CHEAT` | 金手指定义与选择状态 |
| `3` | `STATS` | 游戏时间及其他用户游戏统计数据 |
| `4` | `PRIVATE` | Producer 专用的持久数据 |

Namespace 只描述 opaque bytes 的大类用途，不定义文件类型、schema、文件扩展名、
模拟器、核心、前端或主机目标位置。`PRIVATE` key 必须以 producer 自行控制的标识符
开头，并在其后带 `/`。非空 entry 的 namespace 不得为零，也不得使用未列出的值。

ROMX 0.2.0 明确排除 save state；任何 namespace（包括 `PRIVATE`）都不得保存即时
存档。

### 6.4.1 无压缩 SAVE/CHEAT bundle profile

`SAVE` 或 `CHEAT` object 可以保存可互操作的无压缩 mutable bundle。Bundle 将有限
数量的普通文件组合在一起，但不改变文件字节。Object key 标识 consumer 选择的目标
根目录；bundle 内每个 path 都相对于该根目录。通用 key `libretro` 表示当前 Libretro
前端的 save 或 cheat 根，但实际主机路径仍由前端政策决定。

Bundle 从一个 64 字节 header 开始：

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 4 | bytes | `magic` | ASCII `RMBL` |
| `0x04` | 2 | uint16 | `bundle_version` | 必须为 `1` |
| `0x06` | 2 | uint16 | `header_size` | 必须为 `64` |
| `0x08` | 2 | uint16 | `namespace` | 必须等于外层 `SAVE` 或 `CHEAT` namespace |
| `0x0A` | 2 | uint16 | `flags` | 零 |
| `0x0C` | 4 | uint32 | `entry_size` | 必须为 `64` |
| `0x10` | 4 | uint32 | `entry_count` | bundle 内普通文件数量 |
| `0x14` | 4 | uint32 | `reserved` | 零 |
| `0x18` | 8 | uint64 | `directory_offset` | 必须为 `64` |
| `0x20` | 8 | uint64 | `path_table_offset` | 必须为 `64 + entry_count * 64` |
| `0x28` | 8 | uint64 | `data_offset` | 第一个 data 位置，必须为 `align_up(path_table_end, 64)` |
| `0x30` | 8 | uint64 | `bundle_size` | 必须等于外层 object 的 `data_size` |
| `0x38` | 4 | uint32 | `header_crc32` | 完整 64 字节 header 的 CRC32 |
| `0x3C` | 4 | uint32 | `reserved` | 零 |

计算 `header_crc32` 时，将 `0x38..0x3B` 视为零。固定 directory 紧接 header。
每个 64 字节 entry 如下：

| Offset | Size | Type | Field | Requirement |
|---:|---:|---|---|---|
| `0x00` | 8 | uint64 | `path_offset` | Path 字节在 bundle 内的绝对 offset |
| `0x08` | 4 | uint32 | `path_size` | UTF-8 字节数，1–1024 |
| `0x0C` | 4 | uint32 | `flags` | 零；version 1 只表示普通文件 |
| `0x10` | 8 | uint64 | `data_offset` | Bundle 内绝对 offset，按 64 字节对齐 |
| `0x18` | 8 | uint64 | `data_size` | 文件原始长度；允许为零 |
| `0x20` | 4 | uint32 | `data_crc32` | 恰好文件字节的 CRC32 |
| `0x24` | 28 | bytes | `reserved` | 全零 |

Path 遵循 RIDX path 规范化规则，且最多为 1024 个 UTF-8 字节；磁盘中不以 NUL
结尾。Entry 按 unsigned UTF-8 原始字节严格排序。Path 既不得逐字节重复，也不得在
ASCII 大小写折叠后重复。Path table 按 directory 顺序紧密保存 path，不含分隔符或
gap；之后以零填充到 `data_offset`。

文件 data 按 directory 顺序排列。每个 `data_offset` 必须恰好等于
`align_up(previous_file_end, 64)`。所有对齐 gap（包括最后一个文件之后）必须为零。
`bundle_size` 必须恰好等于最后一个文件对齐后的结束位置。空 bundle 有效，且恰好
由 64 字节 header 构成。所有算术必须经过溢出检查，range 不得重叠。

符合规范的 writer 只接受用户明确选择的普通文件，按原字节保存，不写入压缩、
archive metadata、权限、时间戳、symlink、hard link、device 或 directory entry。
Reader 在释放前必须验证外层 object CRC32、完整 bundle 布局、规范化 path、零填充
和每个 `data_crc32`。绝对路径、dot component、路径穿越、反斜杠、内嵌 NUL、
重复目标及任何穿过 symlink 的释放路径都必须拒绝。

恢复操作必须以 bundle 列出的 path 为事务边界：先在目标文件系统的新 staging 位置
释放并验证全部字节，再只原子替换列出的每游戏目录或文件。Consumer 绝不能替换
前端共享的整个 save/cheat 根。只要任一列出的本地目标已存在，首次自动恢复就必须
跳过，冲突只能由用户显式操作处理。有效的空 bundle 与 object 不存在含义不同：
它明确表示没有文件。

### 6.4.2 严格 STATS JSON profile

Key 为 `default` 的 `STATS` object 可以保存严格 UTF-8 JSON object，最大 16384
字节。它不得含 BOM、重复 key、未知 key、浮点数、注释或尾随非空白数据。以下
member 是必需的：

| Key | Type | Requirement |
|---|---|---|
| `schema` | string | 必须为 `romx.stats` |
| `version` | integer | 必须为 `1` |

以下 member 可选。所有 integer 都必须位于 `0..9007199254740991`，从而可以被通用
JSON 实现精确表示。

| Key | Type | Meaning and constraints |
|---|---|---|
| `play_time_seconds` | integer | 累计前台游玩秒数 |
| `launch_count` | integer | 成功启动次数 |
| `first_played_unix_seconds` | integer | 已知最早 UTC Unix 时间 |
| `last_played_unix_seconds` | integer | 已知最晚 UTC Unix 时间；不得早于 `first_played_unix_seconds` |
| `favorite` | boolean | 用户收藏状态 |
| `completed` | boolean | 用户通关状态 |
| `completion_percent` | integer | 闭区间 0–100 |
| `achievements` | object | 下述成就汇总进度 |

`achievements` object 存在时，必须包含非负 integer `unlocked` 与 `total`，且
`unlocked` 不得大于 `total`。它还可以包含 `hardcore_unlocked`，其值不得大于
`unlocked`。不允许其他 member。`STATS` 不得保存 provider 凭据、access token、
账号标识或完整的 provider 专用成就记录；用户明确要求保存的 producer 数据应放入
`PRIVATE`。

Writer 必须按上表顺序输出紧凑 JSON；`achievements` 内按 `unlocked`、`total`、
`hardcore_unlocked` 排序。只要严格 schema 有效，reader 应接受其他 member 顺序和
JSON 空白。

游玩时间与启动次数采用 baseline 加 session delta 同步。显式写回前，consumer 必须
重新读取最新 ACTIVE `STATS` generation，只把本地 session delta 加到最新累计值；
first-played 取已知最小值，last-played 取已知最大值。不得用过时的绝对 snapshot
覆盖更新的累计计数。收藏、通关和成就汇总发生冲突时，由用户或前端显式决定。

### 6.5 显式操作与空间分配

容器层本身不会触发主机侧恢复、同步或写回。Consumer 可以实现 SAVE/CHEAT bundle
profile 规定的无冲突首次恢复策略：只有全部列出的目标都不存在时才恢复，否则跳过
整个操作。会覆盖本地数据的导入、冲突处理、写回和删除必须由 consumer 显式请求；
关闭内容或退出时不得自动写回。用户界面如何确认、实际主机路径，以及如何映射到
模拟器内存或前端目录，都不属于容器标准。

创建 object 时分配一个 empty directory slot 和一个不重叠的 extent。普通替换必须
保留已有 `data_offset` 与 `data_capacity`，只有新值能够放入时才能成功。删除会清空
directory slot 并释放其 extent。删除后 object 字节可以保留在已释放 extent 中，但
不能再被访问；是否安全擦除属于实现政策。

本标准不定义自动 relocation、directory 扩容、mutable region 扩容、compaction 或
container repack。没有 empty slot 或合适 extent，或者替换数据超过
`data_capacity` 时，请求必须失败且不得修改不可变内容。任何维护操作都必须由
consumer 单独显式请求。

### 6.6 原位覆盖的提交与失败语义

Writer 必须序列化 mutable 操作。创建或替换单个 object 时，writer 必须依次执行：

1. 写入完整有效的 `WRITING` entry，其中包含所选 identity、已分配 extent、下一
   generation、预期 size 与预期 data CRC32；
2. 在修改 data extent 前，确保该 entry 已持久化；
3. 从 `data_offset` 开始原位覆盖恰好所选 object 字节，并确保 data 已持久化；
4. 将同一个 directory slot 重写为完整有效的 `ACTIVE` entry，并确保它已持久化。

第 4 步是 commit point。Reader 只暴露 entry CRC32、字段、extent、key 与 data CRC32
全部有效的 `ACTIVE` entry。因此，中断的原位覆盖一定可以被检测出来，不会被误认为
已经提交。由于覆盖的是同一个 data extent，ROMX 不保证恢复旧值；只有受影响的
object 会变为不可用。

删除 object 时，writer 必须先写入并持久化有效的 `DELETING` entry，再把完整 512
字节 slot 清零并确保清零结果持久化。`DELETING` 一旦持久化，reader 就将 object
视为不存在。发生 torn slot write 时必须隔离该 slot，不能自动复用。

Object 更新不重新计算已启用的 `immutable_sha256`，不重写不可变区域，不移动 footer，也不
改变文件大小。Mutable header 无效会使整个 mutable region 不可用。单个 entry
无效、写入中断、data CRC32 不匹配或容量不足只影响 mutable data，绝不能使其他
有效的 payload、RIDX、metadata 或 cover 无效，也不得阻止访问这些区域。

## 7. 非规范性 mutable 容量建议

本节只是容量建议，不是有效性规则，也不是硬件最大值。容量包括 4096 字节 header、
固定 directory、已分配 object extent 与空闲空间。Writer 应为目录型存档选择足够的
directory slot，并为每个 object extent 预留有意义的容量。

| Profile | Typical systems | Recommended capacity |
|---|---|---:|
| `compact` | 任何优先控制容器增量的平台 | 0（无 mutable region） |
| `cartridge-detected` | GB/GBC/GBA、NES、SNES、MD、SMS、GG、PCE、N64 | `max(512 KiB, detected_save_capacity + 256 KiB + directory overhead)` |
| `cartridge-unknown` | 无法识别存档容量的卡带 | 通常 1 MiB；homebrew 为 2 MiB |
| `cartridge-large` | Nintendo DS 卡带存档 | `max(16 MiB, detected_save_capacity + 2 MiB + directory overhead)` |
| `disc-card-small` | PS1、PCE CD、Sega CD、Saturn、Dreamcast | 2 MiB；多 memory card/VMU 集合应选更大 profile |
| `arcade` | FBNeo/MAME NVRAM、配置、金手指 | 通常 1 MiB；完整单游戏集合为 4 MiB |
| `disc-card-medium` | PlayStation 2 | 32 MiB |
| `directory-save-large` | PSP、GameCube、Wii、Nintendo 3DS、DSi/NAND/SD 存档 | 过滤后的单游戏文件为 64 MiB；只有根据实测数据显式选择时才使用 128 MiB 或更大容量 |

SAVE、CHEAT、STATS 和 PRIVATE object 使用彼此独立的 extent。非零的小型系统容量
中，至少应保留 128 KiB 未分配空间给 CHEAT 与 STATS extent；producer 不得让 SAVE
增长占用这部分预留。导入现有数据时，分配的 object capacity 除当前字节大小和
directory overhead 外，还应包含预期增长空间。

`compact` 是符合规范的 profile，可避免很小的 ROM 因空白预留而增大数倍。其他
profile 也不保证所有未来存档集合都能放入。容器之外的存储以及如何选择更大容量
不属于本规范。


## 8. CRC32

所有 CRC32 字段使用与 RetroArch 兼容的 CRC-32/ISO-HDLC 参数：

- polynomial `0x04C11DB7`（reflected `0xEDB88320`）；
- initial register `0xFFFFFFFF`；
- 输入输出均 reflected；
- final XOR `0xFFFFFFFF`；
- 测试向量 `123456789` 得到 `cbf43926`。

JSON 将 CRC32 序列化为恰好八位小写十六进制。二进制结构将数值 uint32 按小端序
保存。

## 9. 验证与故障隔离

Reader 按以下顺序验证：

1. Footer 位置、magic、wire version、CRC32、区域大小、hash algorithm、平台与
   启动值以及 reserved 字节；
2. 经过溢出检查的顶层范围、强制顺序、对齐及零填充；
3. RIDX header、准确长度、CRC32、entry flags、路径及 payload 范围；
4. 可选 immutable SHA-256；
5. Metadata UTF-8/JSON/schema 与 cover PNG profile；
6. Mutable header、directory entry、extent 关系与 active object CRC32。

存在的 RIDX entry CRC32 和可选 immutable SHA-256 可以延迟验证；结构验证不要求读取
每一个 payload 字节。Reader 在完成对应声明所需的全部字节检查前，不得把 payload
set 或 immutable hash 报告为完全验证。Lazy 与 eager payload 验证覆盖相同字节后
必须得到相同的 domain 结果。

验证结果分为互相独立的 domain：

| Domain | Invalid when | Effect on other domains |
|---|---|---|
| 容器结构 | Footer、经过检查的推导布局、强制 RIDX 结构、entrypoint 数量或零偏移规则、reserved 值或禁止的注册值无效 | 不信任任何区域或 entry 边界 |
| 启动 profile | 已知的平台/启动/entrypoint 格式组合没有在 ROMX 0.2.0 平台 profile 中登记 | 结构与索引字节仍可读取，但声明的 profile 不可用 |
| 注册支持 | Reader 不认识某个未被禁止的非零 ID，或任一 footer ID 为 `UNSPECIFIED` | 结构仍有效；profile 属于不支持或未解决，而不是损坏 |
| Payload set | 设置 `HAS_CRC32` 的 entry 发生 CRC32 不匹配 | Metadata、cover 与 mutable 状态保留自己的结果 |
| Immutable hash | 启用的 `immutable_sha256` 不匹配 | 不可变内容无效；mutable 状态仍可单独解析，但不得与受信任内容关联 |
| Metadata | UTF-8、JSON、schema 或 metadata 规则失败 | Payload 与 cover 仍可独立使用 |
| Cover | PNG profile 失败 | Payload 与 metadata 仍可独立使用 |
| Mutable layout | Mutable header、directory 边界、identity 唯一性或 extent 关系无效 | Mutable data 不可用或涉及的 slot 被隔离；不可变内容仍可独立使用 |
| Mutable object | Entry 验证中断或无效、state 不是 `ACTIVE`，或 data CRC32 不匹配 | 受影响 object 不可用；其他 object 与全部不可变内容仍可使用 |

Reader 可以同时报告多个 domain 结果。这种故障隔离属于容器标准；软件 API 的
名称和形状不属于本规范。

Consumer 如何暴露 RIDX entry、如何将其提供给其他程序，以及如何把 mutable
namespace 映射到主机存储，都不属于 ROMX 容器标准。这些选择不得改变保存的 offset、
path、验证结果或提交语义。

## 10. 范围与演进

ROMX 0.2.0 标准化：

- 未压缩拼接的单文件与多文件 payload；
- 从文件绝对偏移零开始且无前缀的 entrypoint；
- 唯一的 `.romx` 容器扩展名；
- Footer 平台与启动格式注册表；
- RIDX 虚拟文件索引和 entrypoint；
- 每个 RIDX entry 的文件格式 ID、原始虚拟路径、字节范围与可选 CRC32；
- 可选 metadata 与 PNG cover；
- 用于显式存档、金手指、统计与私有数据操作的固定容量索引 mutable object store；
- 只覆盖不可变区域的 SHA-256，以及有明确范围的 CRC32 验证。

ROMX 0.2.0 暂不标准化 payload 压缩、加密、save state、mutable 自动同步、云同步、
增量补丁或自动无限增长的 mutable 空间。CIA 安装包和独立且含义不明确的光盘
`.bin` 镜像不是 ROMX 0.2.0 启动 profile；有效描述文件引用的 BIN 轨道受到支持。

未来的一致性 fixture 放在 `tests/fixtures/`，并使用描述具体行为的名称，不附加格式
版本后缀。
