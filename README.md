<div align="center">

# JiHuiYiYou-OS

### 自研操作系统 — 与 JHYY 编译器共生

**Microkernel. Capability-based. amd64-only. Written in JHYY.**

[![Version](https://img.shields.io/badge/version-v0.0.0-blue)](#当前状态)
[![Phase](https://img.shields.io/badge/phase-pure%20design-yellow)](#当前状态)
[![Backend](https://img.shields.io/badge/source-JHYY-orange)](#与编译器项目的关系)
[![Platform](https://img.shields.io/badge/platform-amd64-lightgrey)](#)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)

[当前状态](#当前状态) · [5 原则](#五原则) · [项目结构](#项目结构) · [文档](#文档) · [路线图](#路线图) · [与编译器的关系](#与编译器项目的关系)

</div>

---

## 这是什么

JiHuiYiYou-OS (jhyy_OS) 是一门**自研操作系统**项目。与姊妹项目 [JHYY 编译器](https://github.com/JiHuiYiYou/JiHuiYiYou-compiler) 共生 —— 编译器的目标之一就是让 JHYY 语言具备写 OS kernel 的能力,OS 的需求反过来驱动编译器扩展语言特性。

**终极目标**: 真自举闭环 = jhyy 编 jhyy_OS,jhyy_OS 跑 jhyy 编译器。

## 当前状态

**v0.0.0 / 纯设计阶段 / 0 行代码**

- ✅ 仓库 + 设计骨架落盘
- ✅ 11 个里程碑 + 五原则锁定
- 🚧 等待 JHYY 编译器 v2.x (freestanding target) + v3.x (asm/naked/volatile/no_std/link_section 等 OS-required 扩展) 完成,才能开始 M1 (UEFI 启动)

按 [CLAUDE.md](CLAUDE.md) §「v0.0.0 阶段」,本仓库**只动 `docs/` 和 `memory`,不动 `src/`** —— 设计先行,实现等编译器就绪。

## 与编译器项目的关系

| 项目 | 当前状态 | 与本项目的关系 |
|------|---------|---------------|
| [JHYY 编译器](https://github.com/JiHuiYiYou/JiHuiYiYou-compiler) | v0.8 wip (C 宿主编译器) | **强前置**:jhyy v2.x freestanding target + v3.x 语言扩展 = M1 启动的硬门槛 |
| jhyy_OS | v0.0.0 (设计) | 反向:OS 需求 = jhyy 后续 sprint 的输入 |

**双线作战** 是核心优势 —— jhyy 和 jhyy_OS 互相喂养,反馈循环 = 周级。

## 五原则

任何架构决策过不了这五关 = DROP:

1. **可行且简单** —— 两个人能在 v0.x 阶段 hold 住
2. **双线作战是核心优势** —— jhyy 和 jhyy_OS 互相喂养
3. **项目初期寄生 Windows** —— 开发/构建/调试在 Windows 上做;OS 运行时脱离 Windows
4. **Debug 在语言里,不靠 gdb** —— 编译期消除 bug 类 + 类型化错误链 + capability provenance + 类型化内核状态
5. **Kernel 绝不解决语言应该解决的问题** —— kernel 设计难,先问"是语言该加 feature 还是 kernel 该 hack"

## 项目结构

```
jhyy_OS/
├── docs/                      # 设计 doc(已落盘)
│   ├── v0.0.0-design.md             设计骨架(11 milestones + 5 原则)
│   ├── v0.0.1-*.md                  三章联动:syscall-abi / capability / process-model
│   ├── v0.0.1.5-M5b-prereqs.md      M5b IPC 实施前置(12 硬条件)
│   ├── v0.0.2-foundation-revision.md   spec 校准 + M1-M11 依赖图
│   ├── v0.0.3-explorations.md       5 macro-strategies + 备选架构
│   ├── v0.0.4-gui-explorations.md   GUI 集群探索(M8d / M12 候选)
│   ├── coordination.md              OS × compiler 跨边界对齐
│   ├── design-log.md                头脑风暴 + 决策链路
│   ├── highlights-technical.md      8 killer features(技术版)
│   └── highlights-plain-language.md 8 killer features(白话版)
├── spike/                     # 设计 spike 代码(boot path 等小实验)
│   ├── boot.s                       UEFI x64 boot stub 模板
│   ├── wrap_gpt.py                  GPT 镜像包装脚本(备选路径)
│   ├── BOOTX64.EFI                  编出的 EFI 二进制(模板)
│   └── esp_root/                    FAT 目录后端(OVMF 自动 boot 用)
├── CLAUDE.md                  项目说明 + 最高纲领
├── LICENSE                    MIT
├── README.md                  本文件
├── .gitignore
└── .gitattributes
```

> `src/` 和 `build/` 等 OS 源码目录**尚未创建** —— 等编译器就绪、进入 v1.x 实施阶段才会启用。

## 文档

| 文档 | 用途 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | 项目说明 + 最高纲领 + 文档索引 |
| [docs/v0.0.0-design.md](docs/v0.0.0-design.md) | 设计骨架:使命 / 五约束 / 开放维度 / 11 milestones |
| [docs/v0.0.1-design-index.md](docs/v0.0.1-design-index.md) | v0.0.1 三章(syscall-abi / capability / process-model)交叉引用 |
| [docs/v0.0.2-foundation-revision.md](docs/v0.0.2-foundation-revision.md) | 2026-08-04 spec 校准 + M1-M11 依赖图 |
| [docs/v0.0.1.5-M5b-prereqs.md](docs/v0.0.1.5-M5b-prereqs.md) | M5b IPC 实施前置(12 硬条件) |
| [docs/coordination.md](docs/coordination.md) | OS × compiler 跨边界对齐 |
| [docs/highlights-technical.md](docs/highlights-technical.md) | 8 killer features(技术版) |
| [docs/highlights-plain-language.md](docs/highlights-plain-language.md) | 8 killer features(白话版) |
| [docs/design-log.md](docs/design-log.md) | 头脑风暴 + 决策链路 |

### Reading order

| 意图 | 先看 |
|------|------|
| 了解项目状态、设计原则 | [CLAUDE.md](CLAUDE.md) |
| 看亮点 / 设计初衷 | [docs/highlights-technical.md](docs/highlights-technical.md) |
| v0.0.0 完整设计稿 | [docs/v0.0.0-design.md](docs/v0.0.0-design.md) |
| 看 M1-M11 依赖图 | [docs/v0.0.2-foundation-revision.md](docs/v0.0.2-foundation-revision.md) |
| 看 M5b 实施前置 | [docs/v0.0.1.5-M5b-prereqs.md](docs/v0.0.1.5-M5b-prereqs.md) |
| 看 OS × compiler 跨边界问题 | [docs/coordination.md](docs/coordination.md) |
| 设计过程 / 决策链路 | [docs/design-log.md](docs/design-log.md) |

## 路线图(11 个 milestones)

| # | 里程碑 | 状态 | 解锁前置 |
|---|--------|------|---------|
| M1 | UEFI 启动 — `efi_main` 跑通 | 🚧 待编译器 v2.x freestanding | jhyy v2.0 |
| M2 | 内核页表 + 物理内存管理 | 🚧 | M1 |
| M3 | 进程模型 + 地址空间 | 🚧 | M2 |
| M4 | 用户态进程 boot | 🚧 | M3 |
| M5a | capability 类型系统 | 🚧 | jhyy v3.x |
| M5b | Type-driven IPC 实现 | 🚧 12 硬条件 | M5a + jhyy v3.x |
| M6 | 文件系统 | 🚧 | M5b |
| M7 | 设备驱动 | 🚧 | M6 |
| M8a | 进程间 capability grant/derive | 🚧 | M5a |
| M8b | 命名空间隔离 | 🚧 | M8a |
| M8c | 高级 capability 操作 | 🚧 | M8a |
| M8d | GUI 集群(待定,候选 C 两阶段) | 🚧 | v0.0.4 探索 |
| M9 | 自举编译器服务(子系统) | 🚧 | M5b + jhyy v1.0 自举 |
| M10 | 用户态服务栈 | 🚧 | M9 |
| M11 | 应用层 + 自举闭环 | 🚧 | M10 |

详细依赖图见 [docs/v0.0.2-foundation-revision.md](docs/v0.0.2-foundation-revision.md) § 4。

## 已知 DROP(候选架构过滤记录)

- **CHERI** — 不够成熟
- **seL4 验证** — 不够简单(违反原则 1)
- **region-affine types** — 不够成熟
- **eBPF / Wasm-as-userland / Wasm-in-kernel** — 不喂养 jhyy 语言(违反原则 5)

## 开发环境

- **构建 / 调试宿主机**: Windows 10 + MSYS2 bash + QEMU + OVMF
- **OS 实际运行**: QEMU x86_64 (微内核 amd64-only)
- **编译器**: JHYY(v2.x freestanding + v3.x OS-required 语言扩展后启用)
- **不依赖 gdb**(原则 4):debug 信息由语言层提供

## Contributors

- **人类作者**: JHYY ([JHYY@local](https://github.com/JiHuiYiYou))
- **AI 协作**: [MiniMax-M3](https://MiniMax) — 通过 [Claude Code](https://claude.ai/code) CLI 工作流参与设计、编码、调试、文档

> 与 [JHYY 编译器](https://github.com/JiHuiYiYou/JiHuiYiYou-compiler) 共享同一协作模式。MiniMax-M3 是 [MiniMax](https://MiniMax) 出品的基础模型,**不是** Anthropic Claude / OpenAI GPT 系列。

## License

[MIT](LICENSE)