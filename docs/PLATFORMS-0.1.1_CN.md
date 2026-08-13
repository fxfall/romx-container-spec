# ROMX 0.1.1 平台与 Payload 格式 profile

本文档只定义 ROMX 0.1.1 新增的平台与源格式 profile。ROMX 0.1.0 的全部 profile
原样继承自 [`PLATFORMS_CN.md`](PLATFORMS_CN.md)，不在本文重复介绍。

## 范围

ROMX 0.1.1 只修订格式 profile。VFS、内存映射、临时文件、释放策略、缓存以及
核心集成属于 libromx 或前端的实现职责，不是 ROMX wire format 的要求。

每个 profile 把一个完整的源文件保存为一个连续 payload。payload 必须逐字节保留：
writer 不得去除头部、交换字节序、重新编码、重新压缩或以其他方式转换源字节。
扩展名原样追加 `x`（`.iso` 变为 `.isox`，`.z64` 变为 `.z64x`）。下表的推荐
核心仅供参考，不构成规范依赖。

## 平台与 Payload profile

下表只列出 0.1.1 新增项。只有源格式本身是完整文件或镜像/容器时，profile 才有效。

| 平台 | 源扩展名 | ROMX 扩展名 | 平台 ID | 识别提示 | 内嵌封面/图标提示 | 推荐核心 |
| --- | --- | --- | --- | --- | --- | --- |
| NES UNIF | `.unf`、`.unif` | `.unfx`、`.unifx` | `nes` | UNIF 容器签名；可选 `NAME` chunk 可提供标题 | — | Mesen、Nestopia、FCEUmm |
| Nintendo 64 | `.z64`、`.n64`、`.v64` | `.z64x`、`.n64x`、`.v64x` | `n64` | N64 头与字节序标识；标题位于 `0x20–0x33` | — | Mupen64Plus-Next |
| PSP | `.iso` | `.isox` | `psp` | 包含 `PSP_GAME/PARAM.SFO` 的 UMD 镜像；读取 `TITLE` | `PSP_GAME/ICON0.PNG`；也可能有 `PIC0.PNG`/`PIC1.PNG` | — |
| PSP | `.cso` | `.csox` | `psp` | CSO 压缩 UMD 镜像；逻辑解压后读取 `PSP_GAME/PARAM.SFO` 的 `TITLE` | 逻辑解压后的 PSP 镜像资源 | — |
| PSP | `.pbp` | `.pbpx` | `psp` | PBP 魔数与内嵌 `PARAM.SFO`；读取 `TITLE` | 内嵌 `ICON0.PNG`；也可能有 `PIC0.PNG`/`PIC1.PNG` | — |
| PSP | `.chd` | `.chdx` | `psp` | CHD 容器；没有保证存在的标题字段 | 内部 PSP 镜像可能含 `ICON0.PNG` 等资源 | — |
| PSP Homebrew | `.elf` | `.elfx` | `psp` | ELF 头；没有标准的人类可读游戏标题 | — | — |
| PSP Homebrew | `.prx` | `.prxx` | `psp` | PRX/ELF 派生头；没有标准的人类可读游戏标题 | — | — |
| Mega Drive 32X | `.32x` | `.32xx` | `genesis32x` | `SEGA 32X` 卡带头；标题字段取决于具体头格式 | — | — |
| Master System | `.sms` | `.smsx` | `sms` | `TMR SEGA` 头位于随容量变化的偏移；没有标准游戏标题字段 | — | — |
| Game Gear | `.gg` | `.ggx` | `gamegear` | `TMR SEGA` 头位于随容量变化的偏移；没有标准游戏标题字段 | — | — |
| PC Engine | `.pce` | `.pcex` | `pce` | HuCard 头部识别；没有通用显示标题字段 | — | — |
| PlayStation | `.chd`、单碟 `.pbp` | `.chdx`、`.pbpx` | `ps1` | PBP `PARAM.SFO` 的 `TITLE`；CHD 标题取决于内部光盘 metadata/文件系统 | PBP `ICON0.PNG`；CHD 没有保证存在的封面资源 | — |
| PC Engine CD | `.chd` | `.chdx` | `pcecd` | CHD/内部光盘文件系统；没有保证通用的标题字段 | 没有保证存在的标准封面资源 | — |
| Sega CD | `.chd` | `.chdx` | `segacd` | CHD/内部光盘文件系统；没有保证通用的标题字段 | 没有保证存在的标准封面资源 | — |
| Sega Saturn | `.chd` | `.chdx` | `saturn` | CHD/内部光盘文件系统；没有保证通用的标题字段 | 没有保证存在的标准封面资源 | — |
| Dreamcast | `.chd`、`.cdi` | `.chdx`、`.cdix` | `dreamcast` | Dreamcast `IP.BIN`；存在时软件名位于 `0x80–0xFF` | `IP.BIN` 没有标准封面资源 | — |
| GameCube/Wii | `.gcm`、`.iso`、`.wbfs`、`.rvz`、`.wia`、`.wad` | `.gcmx`、`.isox`、`.wbfsx`、`.rvzx`、`.wiax`、`.wadx` | `gamecube`、`wii` | GCM/ISO 光盘标题位于 `0x20–0x5F`；封装格式保留源头部 | 可能存在 `opening.bnr`/banner 图标与素材 | — |
| PlayStation 2 | `.iso`、`.chd`、`.cso`、`.zso` | `.isox`、`.chdx`、`.csox`、`.zsox` | `ps2` | ISO 文件系统与 `SYSTEM.CNF`；没有规范化显示标题字段 | 没有保证存在的标准封面资源 | — |
| Nintendo 3DS | `.cxi` | `.cxix` | `3ds` | NCCH/CXI 结构；标题提取不保证 | ExeFS `SMDH` 图标/标题资源可解码为图片 | — |
| Nintendo 3DS | `.app` | `.appx` | `3ds` | NCCH/APP 结构；标题提取不保证 | ExeFS `SMDH` 图标/标题资源可解码为图片 | — |

## 内嵌游戏名提取建议

`metadata.name` 仍然是必填项，但调用者未提供名称时，writer 可以自动填充。建议
按以下顺序取得候选名称：

1. 调用者明确提供的名称；
2. 根据识别提示列，在 payload 已验证的字段中读取可读标题；
3. 使用平台规定的 `crc32` 或 `serial` 主键查询可信数据库得到的标题；
4. 最后退回源文件名（去掉扩展名）。

只有在格式签名/头部验证通过后，才接受 payload 中的标题。按对应格式的字符集
解码，并去除 NUL 字节和填充空格；空字符串或只含控制字符的值必须丢弃。头部签名、
产品代码、序列号或 title ID 属于标识，不是显示名称；除非没有更好的候选值，否则
不得直接写入 `metadata.name`。如果不存在可靠的内嵌标题，writer 应保留文件名
作为 fallback，之后由前端或数据库替换。

以上只是 metadata 派生建议，不增加 ROMX 容器的字节或字段，也不要求 core 或 VFS
实现。

## 内嵌封面/图标提取建议

“内嵌封面/图标提示”列列出的是可以转换为 ROMX PNG 封面的源素材。这些素材都是
可选的，只有 writer 明确转换并嵌入 PNG 后才属于 ROMX 容器内容。reader 必须先
验证源容器以及所有图片偏移和长度，再进行解码。

优先使用平台的主图标/banner（`ICON0.PNG`、3DS `SMDH` 图标或 `opening.bnr`）。
PSP 的 `PIC0.PNG` 和 `PIC1.PNG` 属于次级素材，在没有主图标时
才使用。源素材不要求本身就是 PNG；前端或 converter 可以将其解码为 PNG，但不得
改变 ROM payload。没有内嵌素材是正常情况，不得因此判定 ROMX 文件无效。

ROMX 扩展名保留源扩展名，以明确字节序和源格式身份（`.z64x`、`.n64x`、
`.v64x` 是三个不同的 profile）。`.iso` profile 只对具体格式有效，不是所有
光盘平台的通用保证；PS1 或 Saturn ISO 只有在它是完整单文件镜像时才有效。
PSP `.pbp` 与 PlayStation 单碟 `.pbp` profile 均限于一个游戏/一张碟。

## 0.1.1 明确不支持

以下格式依赖虚拟文件树或多个关联文件，保留到 ROMX 0.2.0：

| 格式或布局 | 原因 |
| --- | --- |
| `.cue`、`.gdi`、`.m3u`、`.ccd`、`.mds`、`.toc` | 光盘描述文件依赖相邻轨道文件 |
| CUE 加多个 BIN 文件 | 多条轨道是独立文件 |
| GDI 加多个轨道文件 | 多条轨道是独立文件 |
| 多碟 M3U | 播放列表引用多个碟片镜像 |
| `.sbi`、`.sub`、`.ecm` sidecar | 主镜像旁需要辅助文件 |
| MSU-1 主 ROM 加附属文件 | 主 ROM 与附属文件组成文件集合 |
| 任何需要相邻文件的描述文件 | 单个 payload 无法表达这种依赖 |

以下格式也不作为 0.1.1 单文件 profile 支持：

* `.zip`、`.7z`：归档内容是文件集合，不是一个源 ROM。
* `.cia`：保留到 ROMX 0.2.0 的安装包 profile。
* Mega Drive `.bin`：保留到 ROMX 0.2.0，待定义无歧义的身份与加载 profile。
* 作为平台级保证的 PS1/Saturn `.iso`；应遵循上面的完整镜像规则。
* N64DD `.ndd`：通常还需要 IPL、磁盘和卡带组合。

这些排除项不影响从已有容器恢复 payload，但它们不是符合 ROMX 0.1.x 的源格式
profile。

## Metadata 与兼容性

ROMX 0.1.1 不增加 metadata 字段。其 schema 是修正后 0.1.0 注册表的严格超集，
同时接受声明 `schema_version: "0.1.0"` 或 `"0.1.1"` 的 metadata。0.1.1 writer
写入 `0.1.1`，已有 0.1.0 metadata 保留原版本。Footer wire value 仍为 `1`；所有
有效的 0.1.0 容器与 metadata 都是 0.1.1 reader 的有效输入。

规范中的源格式身份由 metadata 的 `platform` 与 `payload_format` 组合以及本文
档的扩展名映射共同定义。Schema 校验各字段值是否合法，本文 profile 表定义
允许的平台/格式组合；扩展名本身不能替代 metadata 校验。
