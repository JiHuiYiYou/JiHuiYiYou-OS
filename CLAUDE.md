# CLAUDE.md — jhyy_OS 项目

自研操作系统,与 JHYY 编译器项目共生。
当前: v0.0.0 / 纯设计阶段 / 0 行代码
目标: 真自举闭环 = jhyy 编 jhyy_OS,jhyy_OS 跑 jhyy 编译器

## 关系

- 与 `JiHuiYiYou/`(编译器 repo)是**独立项目**,但设计受编译器 roadmap 反向约束
- 长期愿景:见 memory `project_self_hosted_os_goal`
- 本仓库**寄生 Windows 开发环境**:开发/构建/调试在 Windows 上;OS 运行时脱离 Windows

## 项目布局

```
jhyy_OS/
  CLAUDE.md                  本文件 — 项目说明 + 最高纲领
  docs/                      设计 doc(已落盘,v0.0.0 → v0.0.1)
    ├── README.md                              索引
    ├── v0.0.0-design.md                       设计骨架
    ├── v0.0.1-design-index.md                 v0.0.1 三章交叉引用
    ├── v0.0.1-syscall-abi.md                  IPC + 进程模型 + 错误码
    ├── v0.0.1-capability.md                   Cap 类型 + 编译器约束
    ├── v0.0.1-process-model.md                地址空间 + 线程 + namespace
    ├── v0.0.1.5-M5b-prereqs.md                M5b IPC 实现前置(12 硬条件)
    ├── v0.0.2-foundation-revision.md          spec 校准 + 修订 plan(M1-M11 依赖图)
    ├── v0.0.3-explorations.md                 5 macro-strategies + 备选架构头脑风暴存档
    ├── v0.0.4-gui-explorations.md             GUI 集群探索(M8d / M12 候选 + Wayland-style protocol)
    ├── coordination.md                        OS × compiler 跨边界对齐
    ├── design-log.md                          头脑风暴 + 决策链路
    ├── highlights-technical.md                8 killer features(技术版)
    └── highlights-plain-language.md           同上(白话版)
  src/                OS 源码(待 v1.0.0 后)
  build/              构建产物 + QEMU image(待 v1.0.0 后)
```

注:`.claude/` 仅当需要项目级 Claude 配置(settings.local.json 等)时创建,目前不存在。

## Memory

- 位置:`~/.claude/projects/C--Users-liuzhen-Desktop-coding-jhyy_OS/memory/`
- 索引:见该目录下 `MEMORY.md`(以那个为权威,本文件不重复列条目)

## Reading order

| 意图 | 先看 |
|------|------|
| 了解项目状态、设计原则 | 本文件 + memory `project_jhyy_os_kickoff` |
| 看亮点 / 设计初衷 | `docs/highlights-technical.md` 或 `docs/highlights-plain-language.md` |
| v0.0.0 完整设计稿 | `docs/v0.0.0-design.md` |
| v0.0.1 三章联动 design doc | `docs/v0.0.1-design-index.md` |
| 看 2026-08-04 spec 校准 + M1-M11 依赖图 | `docs/v0.0.2-foundation-revision.md` |
| 看 M5b 实施前置(12 硬条件)| `docs/v0.0.1.5-M5b-prereqs.md` |
| 看 OS × compiler 跨边界问题 | `docs/coordination.md` |
| 看 raw 头脑风暴存档 | `docs/v0.0.3-explorations.md` |
| 看 GUI 集群探索(M8d / M12 候选)| `docs/v0.0.4-gui-explorations.md` |
| 设计过程 / 决策链路 | `docs/design-log.md` |
| 改编译器 ABI 看 OS 影响 | `JiHuiYiYou/docs/abis/jhyy-abi-v1.0.0.md` |
| 起新 OS 子 sprint | `docs/v0.0.0-design.md` § 6 路线图 |

## 最高纲领(五原则,2026-08-04 锁)

1. **可行且简单** ——任何决策先用"两个人能在 v0.x 阶段 hold 住"的尺子量
2. **双线作战是核心优势** ——jhyy 和 jhyy_OS 互相喂养,反馈循环 = 周级
3. **项目初期寄生 Windows** ——开发/构建/调试在 Windows 上做;OS 运行时脱离 Windows
4. **Debug 在语言里,不靠 gdb** ——编译期消除 bug 类 + 类型化错误链 + capability provenance + 类型化内核状态,让 solo developer 能独立 debug kernel
5. **Kernel 绝不解决语言应该解决的问题** ——任何 kernel 设计难,先问"是语言该加 feature 还是 kernel 该 hack"

任何开放维度选项过不了这五关 = DROP。

## 权威文档

| 文档 | 状态 | 用途 |
|------|------|------|
| memory(以 `MEMORY.md` 为权威) | — | 见 `MEMORY.md` 索引 |
| `docs/v0.0.0-design.md` | 已锁(讨论稿) | 设计骨架:使命 / 五约束 / 开放维度 / 11 milestones |
| `docs/v0.0.1-*.md`(3 章) | 草案 | syscall-abi / capability / process-model 三章联动 + index |
| `docs/v0.0.1.5-M5b-prereqs.md` | 已落盘(2026-08-04) | M5b IPC 实施前置(12 硬条件) |
| `docs/v0.0.2-foundation-revision.md` | 已落盘(2026-08-04) | spec 校准 + 修订 plan + M1-M11 依赖图 + MVP coding style |
| `docs/v0.0.3-explorations.md` | 已落盘(2026-08-04) | 5 macro-strategies + 备选架构 + MVP 最小集(头脑风暴存档) |
| `docs/v0.0.4-gui-explorations.md` | 已落盘(2026-08-05) | GUI 集群探索(M8d / M12 候选 + Wayland-style 协议草案 + 推荐候选 C 两阶段) |
| `docs/coordination.md` | 持续追加 | OS × compiler 跨边界对齐 + 12 个 Q-OS/Q-Compiler |
| `docs/design-log.md` | 持续记录 | 完整头脑风暴 + 决策链路(2026-08-03 ~ 08-04)|
| `docs/highlights-*.md` | 持续更新 | 8 killer features(技术 + 白话)|

## 提交规则(参照 [JiHuiYiYou/docs/internal/conventions.md](https://github.com/JiHuiYiYou/JiHuiYiYou-compiler/blob/main/docs/internal/conventions.md) § 提交规则)

1. **commit message 用中文概述** —— 单行 summary + 结构化 body(变更点 / 验证 / 引用)
2. **必须带 footer**:
   ```
   Co-Authored-By: MiniMax-M3 <noreply@MiniMax>
   ```
3. **每个 sprint 一个 commit**(sprint-level change 不拆散;bug fix 可单 commit)
4. **作者身份**:`JHYY <15901598712@163.com>`(系统 prompt 不让改 git config,用 env vars 单次指定):
   ```bash
   GIT_AUTHOR_NAME=JHYY \
   GIT_AUTHOR_EMAIL=15901598712@163.com \
   GIT_COMMITTER_NAME=JHYY \
   GIT_COMMITTER_EMAIL=15901598712@163.com \
   git commit -m "..."
   ```
5. **禁止提交构建产物**:`*.exe` / `*.o` / `*.il` / `*.s` / `*.EFI` / `*.img` / `*.log` 等(已在 `.gitignore`)

完整规则 + memory 索引见 [[feedback-commit-convention]]。

## v0.0.0 已锁决策

- 仓库路径:本目录
- git:已开(2026-08-06 起,`4db637f` 是基础设施 commit)
- v0.0.0 内容:纯设计 doc,0 行代码(已落盘 → `docs/`)
- OS 源码语言:纯 JHYY(不允许 C / asm / Rust 重写层)
- 架构:微内核 + amd64 only v0.x + UEFI only + capability-based(详见 `docs/v0.0.0-design.md` § 4)

## v0.0.0 阶段技术候选筛选(2026-08-03)

**DROP**:
- CHERI / seL4 验证 / region-affine types → 不够成熟 / 不够简单
- eBPF / Wasm-as-userland / Wasm-in-kernel → 不喂养 jhyy 语言

**保留**:
- 同步 syscall + tokio-style 语言 async → 简单,异步推到 v3.x 之后
- v3.x 已有 OS-required 语言特性 → 典范案例

## 工作风格

- **JHYY 工具链**:Windows + MSYS2 bash + QEMU;OS 实际编译要等 v3.x P0 完成(见 memory `project_jhyy_os_kickoff` 时间线)
- **v0.0.0 阶段**:只动 `docs/` 和 memory,不动 `src/`
- **设计不依赖编译器现状**:架构 / ISA / 内存模型 / syscall ABI / bootloader 设计可现在推进
- **改动后必跑**:回归(待 v1.0.0 后才有)

## 与编译器项目的耦合

- jhyy 自举闭环(v1.0.0)= OS 启动的硬前置
- jhyy v3.x 语言特性 = OS-driven 需求(参见 `JiHuiYiYou/CLAUDE.md` 版本轴)
- 反向:OS 需求 = jhyy 后续 sprint 的输入