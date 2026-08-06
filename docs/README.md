# jhyy_OS — 设计文档索引

**项目状态**: v0.0.0 → v0.0.1 设计阶段, 0 行代码
**仓库路径**: `C:\Users\liuzhen\Desktop\coding\jhyy_OS`

## 阅读顺序

| 意图 | 先看 |
|------|------|
| 了解项目定位 / 亮点 | [亮点 · 技术](highlights-technical.md) / [亮点 · 白话](highlights-plain-language.md) |
| 看设计骨架 | [v0.0.0-design.md](v0.0.0-design.md) |
| 看下一阶段(三章联动)| [v0.0.1-design-index.md](v0.0.1-design-index.md) |
| 看 2026-08-04 spec 校准后的修订 + plan | [v0.0.2-foundation-revision.md](v0.0.2-foundation-revision.md) |
| 看 raw 头脑风暴存档(5 macro-strategies / 备选架构 / MVP 最小集)| [v0.0.3-explorations.md](v0.0.3-explorations.md) |
| 看 GUI 集群探索(M8d / M12 候选 / Wayland-style protocol / 跟 jhyy 编译器双向联系)| [v0.0.4-gui-explorations.md](v0.0.4-gui-explorations.md) |
| 看 M5b IPC 实现的硬前置 | [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md) |
| 看设计过程(头脑风暴记录)| [design-log.md](design-log.md) |
| 改 OS 设计 / 起新 sprint | [v0.0.0-design.md](v0.0.0-design.md) § 6 路线图 |
| 看 OS 对编译器 roadmap 的反向约束 | [v0.0.2-foundation-revision.md](v0.0.2-foundation-revision.md) § 4 |

## 文档清单

### 顶层
- [v0.0.0-design.md](v0.0.0-design.md) — 设计骨架(使命 / 约束 / 路线图 / 开放问题)
- [v0.0.2-foundation-revision.md](v0.0.2-foundation-revision.md) — 2026-08-04 spec 校准 + 修订 plan(承认偏差 + M1-M11 依赖图 + MVP coding style)
- [v0.0.3-explorations.md](v0.0.3-explorations.md) — 2026-08-04 raw 头脑风暴存档(5 macro-strategies / 备选 / MVP 最小集)
- [v0.0.4-gui-explorations.md](v0.0.4-gui-explorations.md) — 2026-08-05 GUI 集群探索(M8d / M12 候选 / Wayland-style protocol / 跟 jhyy 编译器双向联系)
- [coordination.md](coordination.md) — **跨边界对齐 doc**(OS + compiler agent 共同读写,2026-08-04 建)
- [design-log.md](design-log.md) — 头脑风暴 + 决策链路(2026-08-03 ~ 08-04)
- [highlights-technical.md](highlights-technical.md) — 8 个 killer features(技术深度)
- [highlights-plain-language.md](highlights-plain-language.md) — 同上,白话版

### v0.0.1 三章联动 + 配套
- [v0.0.1-design-index.md](v0.0.1-design-index.md) — 三章交叉引用 + 跟 v0.0.0 关系
- [v0.0.1-syscall-abi.md](v0.0.1-syscall-abi.md) — Type-driven IPC + 类型化错误码 + endpoint ns + boot 路径
- [v0.0.1-capability.md](v0.0.1-capability.md) — Cap + Narrow Waivers + provenance + Layered TCB + 编译器约束
- [v0.0.1-process-model.md](v0.0.1-process-model.md) — 地址空间 + 线程 + namespace + COW + cap closure MVP
- [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md) — M5b IPC 实现前置(spec 校准后,12 硬条件)

## 文档状态

| 文档 | 状态 |
|------|------|
| v0.0.0-design.md | 已锁(讨论稿) |
| v0.0.2-foundation-revision.md | 已落盘(2026-08-04,基于 spec 校准)|
| v0.0.3-explorations.md | 已落盘(2026-08-04,头脑风暴存档)|
| v0.0.4-gui-explorations.md | 已落盘(2026-08-05,GUI 集群 brainstorming,未锁)|
| v0.0.1.5-M5b-prereqs.md | 已落盘(2026-08-04)|
| v0.0.1-*.md | 草案(待 v0.0.1 完成)|
| coordination.md | 持续追加(OS × compiler 跨边界对齐,2026-08-04 建)|
| design-log.md | 持续记录 |
| highlights-*.md | 持续更新 |