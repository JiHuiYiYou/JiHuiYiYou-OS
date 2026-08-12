# jhyy_OS 亮点 · 白话版

## 为什么做这个 OS

我们在做一个**自研操作系统**, 全部用自研的编程语言 jhyy 写。

这件事听起来很奇怪——已经有 Linux / Windows / macOS 了, 为什么还要做一个?

理由是: 想证明一件事——**用同一种语言从操作系统内核一直写到应用程序, 而且语言自己编自己, OS 自己跑这个语言, 形成完整闭环**, 这件事能不能做到。

## 它做了什么不一样的事

### 1. 文件访问能力是"真的", 不是个数字

普通 OS 里, 打开文件给你一个数字(fd = 3), 你拿这个数字去读。问题是: 任何代码都能拿 `3` 去读, 因为它就是个整数。

jhyy_OS 里, 打开文件给你一个"能力"(capability), 类型是 `Cap<File>`。这个类型:
- **不能伪造**: 不能把整数转成 `Cap<File>`, 编译就报错
- **不能用错**: `Cap<File>` 只能用来读文件, 不能拿它当网络连接用
- **不能越权**: 进程 A 给进程 B 一个 `Cap<File>`, B 才能访问这个文件; B 想转给 C? 得 A 同意

效果: **OS 安全性变成语言层的事**, 不用 OS 团队再单独审查。

### 2. 异步任务的内存大小写出来

写异步代码时, Rust 会偷偷分配堆内存, 你不知道你的任务有多大。

jhyy 里: `async fn read() -> Frame<2KB>` — 写出来多大, 就是多大。编译器会警告 / 报错如果太大。

效果: **OS 内核知道每个任务最坏占多少内存**, 不会因为一个异步任务把内核栈撑爆。

### 3. async runtime 是个小库, 不是巨型框架

普通语言的 async 库(tokio 等)有几万行代码。

jhyy 的 async runtime ≤ 500 行, 整个装在标准库里。

效果: **async 不复杂, 学习曲线短**。

### 4. OS 全用一种语言写

kernel(内核) + driver(驱动) + shell(命令行) + app(应用) + build tool(构建工具) — 全是 jhyy。

普通 OS 是混合的: kernel 用 C, 驱动用 C, 偶尔有 Rust, 工具又用 Python / Go。

效果: **一个语言学完, 整个 OS 都能改**。

### 5. 自举完整闭环(杀手锏)

最牛的地方:

```
jhyy 编译器 编 jhyy_OS 内核  →  jhyy_OS 内核 跑 jhyy 编译器
       ↑                                          ↓
       └──────────── 反过来也成立 ────────────────┘
```

意思是:
- jhyy 写的 OS 内核, 用 jhyy 编译器编译出来
- 编译出来的 OS 内核, 能跑 jhyy 编译器
- jhyy 编译器在 jhyy_OS 上, 又能编 jhyy_OS 自己

**完整闭环**。这件事:
- Linux 每天都在做类似的闭环(GCC 自举 + Linux kernel 编在 GCC 上),但 Linux kernel 是 C、toolchain 是另一条链 — **不是单一语言栈**
- Rust 接近(Redox + rustc 都在 Rust 栈里),但 rustc 不证明"Rust 适合写 kernel"(编译器自己用 unsafe 块写运行时)
- Oberon 接近(Oberon 系统 + Oberon 语言 + 自举),但 Oberon 是 1980s 的语言
- **jhyy 的差异化**:**单一现代语言栈(kernel + driver + shell + app + build tool 全 jhyy)+ 自举 + 编译期 capability** 三者一起做,目前没先例

效果: **学术价值高, 商业价值低, 但 "证明可能性" 的价值 = 100%**。

### 6. 能力安全的端到端集成(真正杀手锏)

第 1 条说 capability 是语言级的。但 jhyy 把它做到底:

| 层 | 普通方案 | jhyy 方案 |
|----|---------|-----------|
| 编译器 | — | 内建 Cap 类型 + 拒绝 as-cast |
| 类型系统 | — | phantom type + 编译期 cap-offset 表 |
| syscall ABI | Linux patch (capsicum) | 只接 Cap 不接整数 + cap-offset 驱动改写 |
| kernel | seL4 (C 手写) | jhyy 写 + 运行期 cnode tag 兜底 |

**四层协同,编译期类型 + 运行期 tag 双向验证**。这种深度, 只有自举语言能做到 —— Capsicum 在 syscall 层做了但语言层没做,seL4 在 kernel 层做了但语言层没做,CHERI 在硬件层做了但语言层没做。jhyy 第一次把四层都做了。

效果: **不是事后打补丁的安全, 是从语言层就保证安全**。

### 7. 调试是语言的功能, 不是 gdb(2026-08-04 加)

普通 OS 调试靠 gdb / kdb / printk。jhyy_OS 不用。

调试 4 层:
- **L1 编译期 bug 消除**:大部分 bug 在编译期就拒了(类型驱动 IPC、capability provenance)
- **L2 类型化错误链**:错误信息走类型化 chain(`ErrChain { source_loc, prev, trace, context, code }`),LLM agent 能顺着找根因 → 详见 [`v0.0.4-debug-abi.md § 5`](v0.0.4-debug-abi.md)(🔒 Locked 2026-08-12,64B)
- **L3 类型化内核状态**:内核状态是 enum + history,debug build 携带状态变迁 → 详见 [`v0.0.4-debug-abi.md § 6`](v0.0.4-debug-abi.md)(KernelState enum + KernelStateHistory ring buffer N=256)
- **L4 Capability 查询 API**:`Cap::provenance()` 直接看 cap 的来龙去脉(类似 git blame for caps) → wire format / Confidence 三级标记 / DAG 增强 见 [`v0.0.4-debug-abi.md § 4 + § 7`](v0.0.4-debug-abi.md)

效果: **solo developer 能独立 debug kernel,不用 gdb**;LLM agent 拿到状态直接诊断;**stretch goal:在 jhyy_OS 上跑 Claude Code**(设计目标,不一定实现)。

### 8. 三层信任 + 1% 特例通道(2026-08-04 加)

99% 的安全检查编译期就拒了。剩下 1% 的角落情况,显式 `unsafe_cap { ... }` 块 + WaiverCap 特权位。

**3 层 TCB**:
- L1 编译器(99%)→ 编译错误(fail-loud)
- L2 运行期 waiver(< 1%)→ 运行期 abort(fail-fast)
- L3 内核 syscall(兜底)→ syscall 错误(fail-safe)

效果: **不是"全编译期"也不是"全运行期",各司其职**。seL4 是"全运行期 + formal proof"(强但贵),jhyy 是"编译期主 + 运行期兜"(性价比高)。

## 真正能跑起来吗

诚实回答: **这是长期项目**。

理由:
1. jhyy 编译器 v1.0.0 已 TAGGED (2026-08-10, commit `eabee0d`) — Stage 2 三层 N=3 byte-equal 闭环达成 (.il sha `2445e97d...`), regress baseline 50/53 PASS (0 failed, 3 skipped)。OS 必需特性 v3.x P0 (3a-3f) 待 sprint 3g 启动。
2. jhyy_OS 还没写一行代码
3. 中间需要先让 jhyy 编译器能编自己(v1.0 自举 ✅), 然后加 OS 必需的特性(v3.x P0), 然后才能写 OS

如果做不完, 中间产物还是有价值:
- jhyy 编译器自举 = 语言学里程碑
- jhyy 多目标 = 工程价值
- v0.0.1 三章设计 doc = 学术价值(类似 Wirth 的 Oberon Reports)
- jhyy_OS 设计本身 = 学术价值
- v0.0.2-foundation-revision.md = spec 校准后修订 plan(任何阶段都有用)
- v0.0.3-explorations.md = 5 macro-strategies + 备选架构头脑风暴(类似 design space 论文)
- v0.0.1.5-M5b-prereqs.md = M5b 实施前置清单(可直接喂 M5b sprint)
- coordination.md = OS × compiler 跨边界对齐(任何 sprint 都有用)

## 跟 Wirth 的 Oberon 系统对比

Niklaus Wirth 在 1980s 做了 Oberon 系统:
- Oberon 语言 + Oberon OS + 自举 + 微内核

jhyy_OS 是 Oberon 思路的现代版本:
- jhyy 语言(现代静态类型, 跟 Rust 同一时代)
- capability 安全(语言级, 比 Oberon 强)
- async 显式 frame(现代特性)
- 自举层次更深(4 层, jhyy 编 jhyy 编 jhyy 编 OS)

如果成功, 这是学术界一直想要但没做到的样本。