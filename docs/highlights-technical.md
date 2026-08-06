# jhyy_OS 亮点 · 技术版

## 8 个 killer features

### 1. 能力伪造 = 编译错误

`Cap<File>` 和 `u64` 是不同类型, `as` 转换禁止。

```jhyy
extern fn sys_read(f: Cap<File>, buf: *mut u8, len: usize) -> IoResult<usize>;
// sys_read(0x1234 as u64 as Cap<File>, ...) = 编译错误
```

seL4 能力安全做到语言层, 跟 capsicum / Linux patch 区分开。

### 2. async 成本可见

`Frame<2KB>` 在签名上, kernel 严格 1 KB / userland 8 KB。

```jhyy
async fn read(c: Cap<File>) -> Frame<2KB> { ... }  // 编译期大小可见
```

跟 Rust `Box<Future>` 完全相反 — Rust future 大小隐藏, jhyy 显式。

### 3. runtime 不超过 500 行

`std::async_runtime` ≤ 500 行 jhyy(spawn / join / select / cancel_token / work-stealing)。

跟 tokio 几万行不同, 核心 lib 装得下整个 async 系统。

### 4. 全栈单一语言

kernel + driver + shell + app + build tool 都 jhyy。

不是 "C kernel + C userland + 偶尔 Rust", 单一栈。

### 5. 自举完整闭环

jhyy 编 jhyy 编 jhyy 编 OS。

Linux(GCC 自举 + kernel 在 GCC 上)接近,但不是单一语言栈;Rust(Redox + rustc)更接近,但编译器自身用 unsafe 写运行时,语言层不保证 kernel 适用;Oberon 也自举,但语言是 1980s 的。**jhyy 的差异化**:单一现代语言栈 + 自举 + 编译期 capability 三者一起做,目前没先例。

### 6. capability 端到端集成(真杀手锏)

jhyy_OS 的 capability 类型安全 = **编译器层 + 类型系统层 + syscall ABI 层 + kernel 层 全栈协同,编译期类型 + 运行期 tag 双向验证**。

| 层 | 现有方案 | jhyy 方案 |
|----|----------|-----------|
| 编译器层 | — | 内建 Cap<T> 类型 + 拒绝 as-cast + 8 条编译期规则 |
| 类型系统层 | — | phantom type + 编译期 cap-offset 表(Q-OS-007) |
| syscall ABI 层 | capsicum (Linux patch) | 只接 Cap<T> + cap-offset 驱动 cnode_idx 改写 |
| kernel 层 | seL4 (手写 C,运行时单点) | jhyy 写 + 运行期 cnode slot tag 兜底(per-cap `{cnode_idx, depth, rights, type_tag}`) |

注意"编译期类型 + 运行期 tag 双向验证"这条边界:**phantom type 只活在持有者用户代码里**(编译器层 + 类型系统层 + syscall ABI 层全是编译期);kernel 端那张表必然是类型擦除的(`type_tag` 是个 `u32`,不是 phantom)。这条边界靠 cap-offset 表(Q-OS-007)统一:编译期生成,运行期按表改写,内核不需要重新解析用户 struct(正中原则 #5)。

seL4 做不到(手写 C,语言层为零);Capsicum 做不到(Linux patch,只在 syscall 层);CHERI 做不到(硬件,语言层不参与)。**jhyy 第一次四层都做了**。

### 7. Debug 在语言里(2026-08-04 加)

solo developer 不依赖 gdb / kdb / printk。debug 是 OS 的语言层 feature。

**4 层 agent-friendly debug 设计**:

| 层 | 机制 | 价值 |
|---|------|------|
| L1 编译期 bug 消除 | 类型驱动 IPC + capability provenance + 类型错误链 | bug 类消除在源头 |
| L2 类型化错误链 | walkable error chain:`Err { code, prev: *Err, trace: [CapId] }` | agent 顺着 chain 找根因 |
| L3 类型化内核状态 | `KernelState` enum + history(debug build)| debug build 携带状态变迁 |
| L4 Capability query API | `Cap::provenance()` / `query_caps(pid)` | agent 直接查询 |

**效果**: LLM agent 拿到内核状态 → 直接解析 → 给出诊断。jhyy_OS 上跑 Claude Code 是 stretch goal(不一定实现,但设计目标)。

详见 [v0.0.2-foundation-revision.md § 3.4](v0.0.2-foundation-revision.md) + [v0.0.3-explorations.md § 6](v0.0.3-explorations.md)。

### 8. Layered TCB + Narrow Waivers(2026-08-04 加)

3 层 trust anchor,99% 编译期 + 1% 运行期 waiver。

| 层 | 实现位置 | 占比 | 失败模式 |
|---|---------|------|---------|
| L1 编译器 | `jhyy compile` | 99% | fail-loud(编译错误) |
| L2 Runtime waiver | process capability table | < 1% | fail-fast(运行期 abort)|
| L3 Kernel syscall | syscall handler | 兜底 | fail-safe(syscall 错误)|

**Narrow Waivers 设计**:
- 99% capability 检查编译期做
- 1% 显式 `unsafe_cap { ... }` block,WaiverCap privilege bit
- 触发场景:legacy 互操作、MMIO、kernel 模块加载

**优势**:
- 编译期强(早失败,无运行期成本)
- 运行期兜(优雅降级)
- 性能 + 安全双赢

seL4 是 L3 + formal proof(强,但贵),Capsicum 是 L3 + flag(弱),Linux 是 L3 only(更弱)。jhyy 是 L1+L2+L3 三层,各有分工。

详见 [v0.0.1-capability.md § 4](v0.0.1-capability.md) + [v0.0.3-explorations.md § 7-8](v0.0.3-explorations.md)。

## 差异化 vs 同类项目

| 项目 | 类型安全 | capability | 自举 | 全栈单一语言 | debug-by-design | layered TCB |
|------|---------|-----------|------|-------------|-----------------|-------------|
| seL4 | C 手写 | ✓ (手写) | ✗ | ✗ | ✗ | L3 + proof |
| Capsicum | Linux patch | partial | ✗ | ✗ | ✗ | L3 + flag |
| CHERI | 硬件 | ✓ | ✗ | ✗ | ✗ | L3 硬件 |
| RustyHermit | Rust | ✗ | ✗ | ✗ (unikernel) | ✗ | L3 |
| Redox | Rust | partial | ✗ | partial (Rust + 一些 C) | ✗ | L3 |
| **jhyy_OS** | **语言级** | **✓ (端到端)** | **✓ (完整)** | **✓ (jhyy only)** | **✓ (语言层)** | **L1+L2+L3** |

## 学术定位

跟 Wirth 的 Oberon 系统对比:
- Oberon: 自举 + 单一语言(自创) + 微内核
- jhyy_OS: 自举完整 + 单一语言(jhyy, 现代静态类型) + 微内核 + capability 语言级 + async 显式 frame + debug-by-design + layered TCB

更现代 + 更严格的安全模型 + 自举层次更深(jhyy 编 jhyy 编 jhyy 编 OS, 4 层)+ debug 体验更友好。

## 时间诚实版

- **最脆弱假设**: solo 不放弃
- **中间产物**: v1.0 自举 / v2.x 多目标 / v3.x P0 / v0.0.1 三章设计 doc 任何一项单独成立都有价值
- **走不通也不白费**: 学术样本价值不依赖 OS 是否真启动