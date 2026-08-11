# ROMX 0.1.1 前端接入 profile

ROMX 0.1.1 是基于冻结 ROMX 0.1.0 wire 格式的前端接入 profile，不增加任何容器
字节，并兼容所有有效的 0.1.0 文件。

前端必须根据已经校验的 footer 与区域结构识别容器，不能依赖可选 metadata 或 cover
是否有效。metadata 缺失、损坏或属于前端尚不支持的 schema 时，前端不得把完整容器
交给模拟器核心，也不得阻止访问结构有效的 payload。

对于接受内存内容的核心，前端只能暴露精确的 payload 范围。guarded mapping 可以直接
映射完整对齐页，仅复制首尾不完整边界页；映射生命周期必须服从核心声明的
`persistent_data` 要求。

对于通过 frontend VFS 读取路径的核心，虚拟偏移 0 对应 `rom_offset`，虚拟大小严格
等于 `rom_size`，任何读取都不得暴露其他容器区域。文件释放只是兼容性降级手段，不是
默认接入方式。

body SHA-256 仍为可选并默认关闭；存在时具有规范约束，暴露 payload 前必须校验。
不存在时，前端不能仅为启动内容而强制扫描完整 payload。

本 profile 不为 ROMX 0.2.0 虚拟文件树预留任何字节或 metadata 字段。多文件 payload
容器必须使用新的 wire 格式版本。
