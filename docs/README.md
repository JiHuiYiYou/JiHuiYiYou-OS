# jhyy_OS — 设计文档索引

**项目状态**: v0.0.x 设计阶段, 0 行代码
**仓库路径**: `C:\Users\liuzhen\Desktop\coding\JHYY_OS`

---

## 一句话主张

> **computer-use 是使用计算机的能力。截屏是它今天唯一能用的实现,而且是劣质的那一种。**
> **Cap\<T\> 是第二种实现 —— OS 直接把能力以类型化契约交给 agent,不走像素。**
> **新一代 OS 的范式,就是 computer-use 的实现手段从截屏换成 Cap\<T\>。**

技术版论证见 [highlights-technical.md](highlights-technical.md),白话版见 [highlights-plain-language.md](highlights-plain-language.md),完整推导见 [v0.0.6-agent-native.md § 1](v0.0.6-agent-native.md)。

**8 个 killer features 不是并列卖点,是这条主张的 8 个支柱**(载体 / 前提 / 运维面 / 可行性 / 证明)—— 分组见两份 highlights 的支柱表。

---

## 文档分三层

读之前先确认自己在哪一层 —— 三层的权威性不同:

| 层 | 含义 | 读法 |
|---|------|------|
| **spec** | 已锁,必须遵守,跟 compiler 侧冲突时走 coordination 协商 | 当规范读 |
| **explore** | 脑暴存档 / 备选方案,记录当时想过什么,**不是决定** | 当背景读 |
| **log** | 过程台账 + 跨边界对齐 | 按需查 |

文件名不强制分层(历史原因),但下面的清单已按层标注。**带 🧪 的章节是存档,带 🔒 的是硬结论 —— 同一文件内可能混有两者。**

---

## 阅读顺序

| 意图 | 先看 |
|------|------|
| 一句话主张 + 8 个支柱 | [highlights-technical.md](highlights-technical.md) / [highlights-plain-language.md](highlights-plain-language.md) |
| agent-native 主张的完整推导 | [v0.0.6-agent-native.md](v0.0.6-agent-native.md) |
| 设计骨架 / 使命 / 路线图 | [v0.0.0-design.md](v0.0.0-design.md) |
| 三章联动(syscall / cap / process) | [v0.0.1-design-index.md](v0.0.1-design-index.md) |
| spec 校准后的修订 + M1-M11 依赖图 | [v0.0.2-foundation-revision.md](v0.0.2-foundation-revision.md) |
| Debug ABI(DebugEvent / ErrChain / KernelState) | [v0.0.4-debug-abi.md](v0.0.4-debug-abi.md) |
| 二进制格式 `.jhyynb` | [v0.0.5-binary-format.md](v0.0.5-binary-format.md) |
| M5b 实施前置(12 硬条件) | [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md) |
| OS × compiler 跨边界对齐 / D 编号 | [coordination.md](coordination.md) |
| GUI 集群探索 🧪 | [v0.0.4-gui-explorations.md](v0.0.4-gui-explorations.md) |
| 5 macro-strategies / 备选架构 🧪 | [v0.0.3-explorations.md](v0.0.3-explorations.md) |
| 设计过程 / 决策链路 | [design-log.md](design-log.md) |
| 改 OS 设计 / 起新 sprint | [v0.0.0-design.md](v0.0.0-design.md) § 6 路线图 |

---

## 文档清单

### 🔒 spec(已锁)

| 文档 | 内容 | 状态 |
|------|------|------|
| [v0.0.0-design.md](v0.0.0-design.md) | 设计骨架(使命 / 五约束 / 开放维度 / 11 milestones) | 🔒 已锁 |
| [v0.0.1-syscall-abi.md](v0.0.1-syscall-abi.md) | Type-driven IPC + 类型化错误码 + endpoint ns + boot 路径 | 📝 草案 |
| [v0.0.1-capability.md](v0.0.1-capability.md) | Cap + Narrow Waivers + provenance + Layered TCB + 编译器约束 | 📝 草案 |
| [v0.0.1-process-model.md](v0.0.1-process-model.md) | 地址空间 + 线程 + namespace + COW + cap closure MVP | 📝 草案 |
| [v0.0.4-debug-abi.md](v0.0.4-debug-abi.md) | DebugEvent 56B + ErrChain 64B + KernelState + ProvenanceInfo | 🔒 Locked |
| [v0.0.5-binary-format.md](v0.0.5-binary-format.md) | `.jhyynb` Header 112B + OS 端实施要点 | 🔒 Locked |
| [v0.0.2-foundation-revision.md](v0.0.2-foundation-revision.md) | spec 校准 + M1-M11 依赖图 + MVP coding style | 🔒 已锁 |
| [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md) | M5b IPC 实施前置(12 硬条件) | 🔒 已落盘 |

> ⚠️ **版本号有两套语义**:`v0.0.x` 既是**文档版本**(本清单)又是 **OS 版本**(v0.1.x 起)。且历史上存在两个 `v0.0.4`(gui-explorations 与 debug-abi)。以**文件名**为准,不要以版本号为准。

### 📝 拟锁定

| 文档 | 内容 | 状态 |
|------|------|------|
| [v0.0.6-agent-native.md](v0.0.6-agent-native.md) | Agent-native OS(CapBundle / Reversibility / 模型资源层预留 / M8d 禁截图) | 📝 拟锁定 |

### 🧪 explore(存档,不是决定)

| 文档 | 内容 |
|------|------|
| [v0.0.3-explorations.md](v0.0.3-explorations.md) | 5 macro-strategies / 备选内存模型 / MVP 最小集(§3 §6-9 已转 🔒) |
| [v0.0.4-gui-explorations.md](v0.0.4-gui-explorations.md) | 6 GUI 架构候选 / M8d·M12 拆分 / Wayland-style protocol 草案 |
| [`deep_research/`](../deep_research/INDEX.md) | 外部深度调研存档(仓库根,与 `docs/` 同级) |

### 📋 log(过程台账)

| 文档 | 内容 |
|------|------|
| [coordination.md](coordination.md) | **跨边界对齐 doc**(OS + compiler 共同读写)/ §0 critical path + D1–D44 + Q 登记 |
| [design-log.md](design-log.md) | 头脑风暴 + 决策链路(2026-08-03 ~ 08-04) |
| [highlights-technical.md](highlights-technical.md) | 主张 + 8 支柱(技术深度) |
| [highlights-plain-language.md](highlights-plain-language.md) | 同上,白话版 |