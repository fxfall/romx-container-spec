# ROMX 0.2.0 开发政策

**状态：草案与研究阶段。** 本文约束 `main` 上的开发流程，但不是已经冻结的
逐字节规范。

## 与 ROMX 0.1.x 的关系

ROMX 0.1.0 与 0.1.1 是历史标准，只用于一致性测试、回归测试、实现对照以及迁移
研究。对应规范、schema 与冻结 fixture 保存在同名版本分支中。

ROMX 0.2.0 不要求完全向后兼容 ROMX 0.1.x。开发可以修改：

- footer 布局与 wire version；
- 区域数量、顺序、寻址方式与可写性；
- payload 表达方式，包括多文件或虚拟文件树模型；
- metadata 字段、schema 规则与标识语义；
- 完整性、恢复与有效性规则。

项目可以提供兼容 reader、导入器或迁移工具，但读取 0.1.x 是实现功能，不是
0.2.0 格式的规范性要求。

## 版本边界

在 0.2.0 footer 与 schema 正式定义前，`main` 上仍写入 wire version `1` 的工具
属于 ROMX 0.1.x 历史测试/参考实现，不得把这些字节声明为 ROMX 0.2.0。

最终 ROMX 0.2.0 必须使用独立 wire version。reader 必须先区分 0.1.x 与 0.2.0，
再解释对应版本的 footer 字段和区域。

## 历史 fixture

现有 `tests/fixtures/` 与 `tests/fixtures/writer/` 是不可改写的 0.1.x 历史测试向量。
ROMX 0.2.0 必须使用独立 fixture 命名空间，不得重写历史 corpus。

在 `main` 上讨论或实验实现的 0.2.0 布局、字段与功能不会自动成为规范；只有被
0.2.0 正式规范明确标记后才具有规范性。
