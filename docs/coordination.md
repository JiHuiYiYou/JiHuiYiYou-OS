# Coordination — jhyy_OS × jhyy compiler

**目的**: jhyy_OS 设计 agent + jhyy 编译器设计 agent 共同读写的对齐文档。任何一方有跨边界问题、决策、疑问,先在这里写,再各自回写决策。
**位置**: 在 jhyy_OS repo 里(OS 设计 agent 的"家");compiler 设计 agent 通过 jhyy_OS 仓库路径访问。
**维护规则**:
- 任一方可编辑,无审批流程
- 重大决策标 🔒,待定问题标 🟡,已对齐标 ✅,存档标 📜,**OS 拟** / **Compiler 拟** 标 📝
- 滚动追加,不要删除历史(用 📜 段保留)
- 编辑前先 Read,避免覆盖别人正在写的内容

**关联**:
- OS doc 索引: [README.md](README.md)
- 编译器 doc 索引: [`../../JiHuiYiYou/CLAUDE.md`](../../JiHuiYiYou/CLAUDE.md)
- 编译器 OS 准备唯一权威: [`../../JiHuiYiYou/docs/plans/v2/v2.0.0-os-prep.md`](../../JiHuiYiYou/docs/plans/v2/v2.0.0-os-prep.md)
- OS 镜像: [v0.0.2-foundation-revision.md § 4](v0.0.2-foundation-revision.md)

---

## § 0 权威依赖链 / Critical Path(2026-08-05 锁)

**OS × compiler 跨项目时间线的 ground truth。**

```
v1.0 closure
  ├── v2.0 amd64_win_freestanding target + hello.efi OVMF demo   (∥ v3.0,两层独立)
  └── v3.0 3a → 3b → 3c → 3d → 3e → 3f
                │
                ▼
               M1 (kernel 启动)
                │
                ▼
               M2 (cooperative scheduler)
                │
                ▼
               M3 (syscall ABI)
                │
                ├── v3.1 3g → 3g.5 → 3g.7   (∥ M2-M3 OS 实施)
                │
                ▼
               M4 (capability 落地)
                │
                ▼
               M5b (IPC 实现)
                │
                ▼
               M6 → M7 → M8a → M8b → M8c → M9 → M10
                │
                ▼
               v3.2+ 3i (generics) → 3j (closures) → 3l (std lib)
                │
                ▼
               M11 (自举 OS 真闭环)
```

**节点表**(2026-08-05 锁,跟 `v2.0.0-os-prep § 2` 一致):

| 节点 | 含义 | OS 影响 |
|------|------|--------|
| **v1.0 closure** | jhyy 编译器自举(byte-equal 闭环)| 整个项目的硬前置 |
| **v2.0** | `amd64_win_freestanding` target + `hello-freestanding.jhyy` OVMF demo + spec § 12 增补 | **M1 target 能力解锁**;M1 前完成 |
| **v3.0** | 6 特性(3a asm / 3b naked / 3c volatile / 3d no_std / 3e link_section / 3f barrier)| **M1 语言特性解锁**;M1 前完成;v2.0 跟 v3.0 并行 |
| **M1** | kernel 启动(printk) | jhyy 编 `kernel.efi` → OVMF → 像素 |
| **M2** | cooperative scheduler | 单核 |
| **M3** | syscall ABI | 消息类型 + ipc_call 内核函数 |
| **v3.1** | 3g `&mut + lifetime` + 3g.5 phantom 0-byte + 3g.7 cap table 联调 | **M4 解锁**;M3-M4 之间完成 |
| **M4** | capability 落地 | Cap<T> sema 验证 + phantom 0 字节 + cap table byte-equal |
| **M5b** | IPC 实现 | endpoint cap + transfer protocol |
| **M6-M10** | driver / FS / UI / PCI / AHCI / virtio / SMP / riscv64 | MVP 完整 |
| **v3.2+** | 3i generics + 3j closures + 3l std lib | M11 解锁 |
| **M11** | 自举 OS 跑 jhyy 编译器 | 真自举 OS 闭环 |

**权威**:
- 编译器端:`v2.0.0-os-prep § 1 + § 2`(权威链 + 节点表)
- OS 端:`v0.0.2-foundation-revision.md § 4`(镜像)+ `v0.0.1.5-M5b-prereqs.md § 1-2`(M5b 硬条件细化)

**冲突解决**:任何 OS doc 跟 `v2.0.0-os-prep § 1/2` 冲突时,**以 compiler 为准**;OS 侧通过本文件 § 2 Q-OS-XXX 走协商。

---

## § 1 状态快照

### 1.1 jhyy_OS 侧

- **当前阶段**:v0.0.x 设计(0 行代码),v0.0.4 已落盘(GUI 集群 brainstorming)
- **仓库**:`C:\Users\liuzhen\Desktop\coding\jhyy_OS`
- **最近决策(2026-08-05 锁)**:
  - 5 原则锁定(可行且简单 / 双线作战 / 寄生 Windows / Debug 在语言里 / Kernel 不解决语言问题)
  - 混合内存模型:region types primary + linear cap + raw MMIO + unsafe_share
  - boot 路径 = UEFI + PE/COFF(走 OVMF)— **2026-08-04 spike 验过**(spike/boot.s)
  - MVP M1-M11 编译器依赖图锁(跟 v2.0.0-os-prep § 1 对齐)
  - 3g/3g.5/3g.7 在 M3-M4 之间(不在 M1 之前);M1-M3 OS 代码用 raw pointer,M4+ 可改 `&mut`
  - **GUI 集群探索已落盘**:`v0.0.4-gui-explorations.md`(M8d / M12 候选,Wayland-style 协议草案,4 个 milestone 候选 + 推荐候选 C 两阶段)
- **GUI 决策已锁(2026-08-05 第三轮)**:**D30-D39 全部 agent 锁**(per user 反馈"我决定还真不如你仔细权衡")— GUI 架构 = Wayland-style,里程碑 = 候选 C,D28 不调整(M8d 单态 type 妥协),GUI 工具包 = egui 立即模式
- **待 OS 团队解决**(内部任务):
  - capability.md 编译期规则细化(sema 8 条)
  - syscall-abi.md Type-driven IPC 的 sema 检查具体算法
  - process-model.md cap closure MVP 的 linter 设计
  - M1 boot stub jhyy 版(把 spike/boot.s 翻译成 jhyy)— 等 v3.0 6 特性 + v2.0 freestanding

### 1.2 jhyy compiler 侧

- **当前阶段**:v0.9 wip ✅ shipped (2026-08-11, commit 2.83);v1.0.0 ✅ TAGGED (2026-08-10, commit `eabee0d`);v2.0 / v3.0 sprint 设计待启动
- **仓库**:`C:\Users\liuzhen\Desktop\coding\JiHuiYiYou`
- **最近决策**:
  - **v2.0.0-os-prep.md 落盘** = OS 启动链路编译器侧唯一权威(2026-08-04 重写)
  - v3.x 语言扩展路线:v3.0 = 6 特性(3a-3f),v3.1 = `&mut + Cap<T>`(3g/3g.5/3g.7),v3.2+ = generics + closures + std
  - jhyy 编译器自身用 arena.jhyy(region-based)
- **待编译器团队解决**(内部任务):
  - v2.0 milestone:`amd64_win_freestanding` target + spec § 12 + hello.efi demo (走 QBE + GCC per D25)
  - v3.0 sprint 3a-3f 实施 (M1 硬前置 per D8)
  - v3.1 sprint 3g + 3g.5 + 3g.7 实施 (M4 硬前置 per D27,三段顺序强制)

---

## § 2 Open Questions

### 2.1 OS → Compiler 🟡

> **格式**:每条 Q 用 **状态 / 影响 / OS 假设 / 期望回复** 四段;新加的 Q 也按此格式

#### Q-OS-001: Cap<T> 8 条编译期规则的实现细节
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D12)
- **影响**: M4 capability
- **决策**(per `v3.x-capability-spec.md` § "实施拆 sprint" + § "待 user 后续决定"):
  - **sprint 拆法**:3g(主体:`&mut + lifetime` + 8 条 sema)+ 3g.5(phantom 0-byte codegen)+ 3g.7(jhyy_OS cap 表 byte-equal 联调)— **三段独立 sprint**(per `v3.x-capability-spec.md` § "实施拆 sprint")
  - **`Move` trait 关系**:**sprint 3g hardcoded move-only**,**不依赖 trait 系统**(per § 待 user 后续决定 #4 建议);trait 系统等 sprint 3i
  - **`#[cap_constructor]` 函数体限制**:是 — 只能调 `#[syscall]` / `#[kernel_entry]`(per § 待 user 后续决定 #2 建议"双重门控")
  - **`into_raw` 必须 `unsafe` block + warning**(per § 待 user 后续决定 #3 建议)
  - **revocation 协议**:lazy invalidation(Q-OS-008 已闭环)— 编译器只 emit `is_valid()` 调用,不自动 retry/poll
- **8 条规则的实施路径**:
  1. `#[cap_constructor]` 白名单 + 普通函数体禁止 `Cap { ... }` 字面量 — AST + sema
  2. `Cap<T1> ≠ Cap<T2>` — sema type compare(规则 2)
  3. `Cap<T>` mark move-only(隐式 copy 报错)— sema hardcoded(规则 3)
  4. `Cap<T> as *u8` 报错;`into_raw` 必须 `unsafe` block + warning — sema(规则 4)
  5. revocation = lazy invalidation — 纯 OS 端 + 编译器 emit `is_valid()` trait 调用(规则 5)
  6. `is_valid()` 标准库 trait — sprint 3l std lib(规则 6)
  7. 函数参数 `Cap<T>` = move 语义 — sema(规则 7)
  8. `&mut Cap<T>` 借用 = `&mut` 规则 — sprint 3g 共享借用检查(规则 8)
- **关联**:v3.x-capability-spec.md § 8 条规则 + § 验收标准;v0.0.1-capability.md § 1 + 5;OS 端已对齐
- **OS 端响应**:OS 侧 capability.md 已对齐 8 条 + phantom 0-byte;M4 实施时按此实现
- **无需回复**

#### Q-OS-002: Type-driven IPC handler 签名验证深度
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D13)
- **影响**: M3 + M5b
- **决策**:
  - **不需要新语言特性**。**MVP 阶段用 attribute 解决** — `#[ipc_handler(msg: M, env: *E)]`
  - **不进 lang-spec § X**(per 原则 5 "kernel 不解决语言问题")— dispatch 模式跟 jhyy 现有 trait / module 体系区别大,进 spec 会复杂化
  - sprint 3g 内 compiler 实现:`#[ipc_handler]` attribute 触发 sema 检查 + codegen 阶段 dispatch table 生成
  - **长期(可选)**:等 sprint 3i trait 系统后,`#[ipc_handler]` 可以 sugar 成 `impl Handler<M> for Service`
- **关联**:v0.0.1-syscall-abi.md § 1.1(OS 端已写好);v3.x-capability-spec.md 不变
- **OS 端响应**:M3 实施时 OS 端写 `#[ipc_handler] fn handle_page_fault(...)` 风格代码;compiler 端加 attribute 即可
- **无需回复**

#### Q-OS-003: Compile-time provenance debug build 副作用
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D14)
- **影响**: debug build 性能 / codegen
- **决策**:
  - **影响 codegen + runtime metadata**(不是 spec 层)— debug build 每个 `Cap<T>` 携带 provenance side table;release build strip
  - **实现路径**:codegen 在 debug build 时 emit provenance table(metadata 段);runtime 通过 `Cap<T>` 字段 + 间接寻址定位 provenance
  - **跟 arena.jhyy 模式无关** — provenance 是 OS-specific 运行期概念,arena 是编译器自身的 region-based 内存管理
  - **不进 std lib**(per Q-Compiler-004)— provenance 是 OS 独有 debug 机制,不会让 jhyy 编译器自身受益
  - **spec 增补**:lang-spec § 21(待增)— 描述 `Cap::provenance() -> DebugInfo` 接口,不强制所有 Cap 都带 provenance
- **关联**:v0.0.1-capability.md § 5 provenance 段
- **OS 端响应**:M4 实施时 OS 端写 `c.provenance()` 调用 debug 工具;compiler 端 codegen 处理
- **无需回复**

#### Q-OS-004: `unsafe_cap` 块语法设计
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D15)
- **影响**: M4 capability(99/1% 分层)
- **决策**:
  - **进 spec § 19(待增)** — 不放 OS std lib
  - **语法**:**`unsafe cap { ... }`**(复用 `unsafe` 块语义,加 `cap` 关键字)
    - 不污染 `unsafe` 语义(后者保留给 FFI / raw pointer 等通用不安全场景)
    - 编译期区分:`unsafe` 不影响 cap 不变量;`unsafe cap` 显式打破 cap 不变量
  - **不需要 `#![feature(unsafe_cap)]` gate** — 默认 sprint 3g 实现后启用
  - **WaiverCap** privilege = 进程 capability 表的 single bit;sema 编译期 + kernel 运行期 双重门控
- **关联**:v0.0.1-capability.md § 4 Narrow Waivers;v0.0.2-foundation-revision.md § 3.3 Layered TCB;v3.x-language-expansion.md sprint 3g 设计;Q-Compiler-002 已闭环
- **OS 端响应**:M4 实施时 OS 端写 `unsafe cap { ... }` 块(类似 Rust `unsafe`);compiler 端 sprint 3g 内加关键字
- **无需回复**

#### Q-OS-005: MVP 路径的 `&mut` 借用何时实装
- **状态**: ✅ **2026-08-05 撤回 + 锁**(详见 § 3 D11)
- **影响**: M1-M3 MVP coding style(用 raw pointer vs `&mut`)
- **OS 假设(已撤回)**:M1-M10 OS 代码用 `*mut T` raw pointer;sprint 3g(v3.1)落地后从 M4 起可改 `&mut`
- **已撤回背景**:之前写"M1 起即可用 &mut"错(基于旧 v0.0.2 § 4 链式图把 3g 放 M1 之前),跟 compiler D5 冲突;已撤回,链式图已对齐 v2.0.0-os-prep § 1
- **期望回复(撤回,无需回复)**:sprint 3g 时间表在 v2.0.0-os-prep § 2 已锁

#### Q-OS-006: Generics 对 OS 的硬需求时点
- **状态**: ✅ **已锁**(详见 § 3 D7 + `v2.0.0-os-prep § 2`)
- **影响**: M11(编译器源用 `Vec<T>` / `Map<K,V>`)
- **结论**:M1-M10 不需要 generics(用 fixed array 够);M11 才硬需 3i
- **无需回复**

#### Q-OS-007: Cap 跨 IPC 的 cap-offset 描述符(2026-08-04 加)
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D16)
- **影响**: M5b IPC(原则 #5 "kernel 不解决语言问题"的正中要害)
- **决策**:
  1. **codegen 路径:双路径** —
     - **主路径**:**codegen 时内联到 syscall wrapper**(快路径,无 metadata 间接寻址)— 每个 `#[ipc_handler]` 调用都直接 emit cap-offset 数组
     - **次路径**:**metadata 段 emit 一份**(loader 友好,debug 用)— `qbe` 看 `.rodata.cap_offsets` 段
  2. **跟 `&mut + lifetime`(sprint 3g)的关系:复用 struct field offset 表** — codegen 阶段已经有 struct layout info,cap-offset 直接序列化 `Cap<T>` 字段的 offset 子集;**不重复实现**
  3. **ABI § 12 wire 形式**:`{msg_tag: u32, n_caps: u16, cap_offsets: [u16; n]}`(放在 16 字节 header 之后、payload 之前的固定区)— **OS 建议同意**
  4. **sprint**:sprint 3g 同步出 cap-offset emit,**不单独 sprint** — 跟 `&mut + lifetime` 主体一起
- **OS 端响应**:v0.0.1-syscall-abi.md § 1.1.4 ⚠️ P0-4 标记可移除(已闭环);M5b 实施时按此实现
- **无需回复**

#### Q-OS-008: Cap revocation 通知协议(2026-08-04 加,终结 v0.0.1 placeholder)
- **状态**: ✅ **OS 默认接受**(详见 § 3 2026-08-05 锁)
- **影响**: M5b IPC(无新 syscall)
- **OS 决定**:lazy invalidation。内核在 cap 被 revoke 时,只把 cnode 对应 slot 标 invalid;不在 userland 端主动通知。下次 syscall 触碰该 cap → cnode 检查失败 → 返回 `SysError::ErrCapRevoked`
- **理由**:
  1. 跟现有 `ErrCapRevoked` 错误码(sysc-all-abi § 1.4.1)兼容
  2. v0.0.1 已放弃 propagation(capability § 8),所以没"广播给衍生 cap"的必要
  3. 不需要新 syscalls / 不需要新 syscall ABI / 不需要 capability provenance schema 加字段
- **代价**:
  1. 进程长时间持有 revoke 过的 cap 不会立刻知道 → 需要上层协议(超时 / poll / 显式 validate)兜底
  2. 文档里要明确"revoke 不保证 caller 立刻看到失败,只保证下次使用时失败"
- **需 compiler 确认**:
  1. `Cap::is_valid()` 的语义是否就是"查 cnode slot 是否标 invalid"?
  2. 编译器是否需要 emit 额外的"syscall 后自动检查" wrapper,还是 userland 显式 `match` 错误码即可(后者更简单,推荐)
- **关联**:`v0.0.1-capability.md` § 8 placeholder 被本条终结;`v3.x-capability-spec.md` 行 300 建议"jhyy_OS 内核设计 doc 先定"——本条即回复
- **期望回复**:compiler 侧同意本协议,或将"is_valid"语义跟本条对齐即可

#### Q-OS-009: `IoResult<T>` 路径选择(2026-08-04 加,关联 P0-5)
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D17)
- **影响**: M5b / M7 / M11(类型化错误码统一泛型)
- **决策**:**路径 A(单态化)for MVP M1-M10** —
  - `IoResult` 拆成 `IoResultUsize` / `IoResultReply` / `IoResultUnit`,每次新增类型手写一份(3-4 份 enum 够 M1-M10 用)
  - jhyy 工具链阻碍:**无**(enum 字面量可直接复用 struct 字面量语法;typedef-like 引用不是必需的)
  - **路径 B 兼容性**:sprint 3i 实施时,**OS 端不重写代码** — `IoResultXxx` 类型名兼容(3i 加的 `IoResult<T>` 是 syntactic sugar,跟现有单态类型共存,按需 implicit conversion 或显式 wrap)
- **影响范围**:
  - v0.0.1-syscall-abi.md § 1.4.1 ⚠️ P0-5 标记**可移除**(已闭环)— 把 `IoResult<T>` 改为 `IoResultUsize` / `IoResultReply` / `IoResultUnit` 三个具体 enum
  - v0.0.1-process-model.md § 5.1 同步改 `IoResult<()>` → `IoResultUnit`
  - v0.0.1-capability.md § 2 `derive<T>` / `grant<T>` / `revoke<T>` 不受影响(`Cap<T>` 例外:编译器内建硬编码)
- **M11 升级路径**:sprint 3i 落地后,`IoResultXxx` 三份可手动合并回 `IoResult<T>`(用 type alias + 单态化 codegen 自动化);**不是必须做**
- **无需回复**

### 2.2 Compiler → OS 🟡

> **格式**:同 § 2.1

#### Q-Compiler-001: OS 端实际使用 Cap<T> 的最早时点
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D18)
- **影响**: sprint 3g 优先级
- **决策**:
  - **M4 起 OS 代码就开始用 `Cap<T>`**(不暂缓)
  - **理由**:M4 = capability 落地的 milestone;**在此之前 M1-M3 没有 Cap<T> 概念**(boot + scheduler + syscall 不需要 cap)
  - **3g 优先级**:**P0 — M4 启动的硬前置,不推迟**(per `v2.0.0-os-prep § 1` M4 行:v3.1 sprint 3g + 3g.5)
- **OS 端响应**:M4 sprint 实施时直接写 `Cap<Page>` / `Cap<Endpoint>` / `Cap<File>` 等;M1-M3 用 raw pointer + 显式权控(per § 3 D11)
- **OS 端回答 compiler**:M4 起就用,不会暂缓
- **无需回复**

#### Q-Compiler-002: `unsafe_cap` 是 OS 独有还是通用 feature
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D19)
- **影响**: 是否进 lang-spec
- **决策**:**进 spec § 19(待增)** — **不放** OS std lib
- **理由**:
  - `unsafe_cap` block 语法是**通用模式**(其他需要"打破 cap 不变量"的场景也能用,例如 embedded 内存映射、设备 driver 等)
  - **但** WaiverCap privilege = OS-specific 安全机制
  - 进 spec 让 `unsafe_cap` 关键字通用;WaiverCap 由 OS std lib 提供
- **影响**:
  - lang-spec § 19 增补 `unsafe cap { ... }` block 语法
  - v0.0.1-capability.md § 4 Narrow Waivers 同步增 WaiverCap 在 OS std
  - sprint 3g 实现 `unsafe cap` 关键字 + sema 检查
- **关联**:Q-OS-004 已闭环
- **OS 端回答 compiler**:进 spec;WaiverCap 是 OS std lib
- **无需回复**

#### Q-Compiler-003: Type-driven IPC 是 OS 专属模式还是通用 trait
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D20)
- **影响**: 是否进 lang-spec § X
- **决策**:**MVP 阶段 OS 自己用 attribute 解决**(`#[ipc_handler(msg: M, env: *E)]`),**不进 lang-spec § X**
- **理由**:
  - dispatch 模式跟 jhyy 现有 trait / module 体系区别大(per 原则 5 "kernel 不解决语言问题")
  - 进 spec 会让 spec 复杂化(per 原则 1 "可行且简单")
- **影响**:
  - sprint 3g 内 compiler 实现 `#[ipc_handler]` attribute + sema 检查 + codegen dispatch table
  - **长期(可选)**:等 sprint 3i trait 系统后,`#[ipc_handler]` 可以 sugar 成 `impl Handler<M> for Service`(类似 Rust axum handler)
- **关联**:Q-OS-002 已闭环
- **OS 端回答 compiler**:MVP 阶段不进 spec;用 attribute 即可
- **无需回复**

#### Q-Compiler-004: Compile-time provenance 是通用 debug infra 还是 OS 独有
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D21)
- **影响**: 是否进 std lib
- **决策**:**不进 std** — **OS 独有**
- **理由**:
  - provenance 是 OS-specific debug 概念(跟踪 cap 来源 / 授权链)
  - jhyy 编译器自身用 arena.jhyy 已经够(per `architecture-refactor § 1.1` 第 5 行)— **不需要 provenance**
  - **进 std 会污染 std API 表面**(per 原则 1 + 5)
- **影响**:
  - 不进 std lib
  - OS 端 codegen 实现:debug build 时每个 `Cap<T>` 携带 provenance side table
  - lang-spec § 21(待增)只描述 `Cap::provenance() -> DebugInfo` 接口,不强制所有 Cap 都带
- **关联**:Q-OS-003 已闭环
- **OS 端回答 compiler**:OS 独有;不进 std
- **无需回复**

#### Q-Compiler-005: arena.jhyy 是否需要"named arena + cap"扩展
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D22)
- **影响**: arena API 扩展
- **决策**:**不扩展** — **OS 用 cap + offset 自己管理**
- **理由**:
  - arena.jhyy 是编译器内部 region-based 内存管理(per `architecture-refactor § 1.1` 第 5 行)— **编译期 / 静态内存模型**
  - cap 是 OS 端运行期权限机制 — **运行期 / 动态权限模型**
  - 两层不混合更清晰(per 原则 5 "kernel 不解决语言问题")
  - 进 arena API 会让编译器内部依赖 cap 概念,污染编译器(per 原则 1 "可行且简单")
- **影响**:
  - arena API 不动(保持匿名)
  - OS 端 cap 表 + offset 表自己实现(在 jhyy_OS 自己的 std 模块)
- **OS 端回答 compiler**:OS 用 cap + offset 自己管;arena API 不动
- **无需回复**

#### Q-Compiler-006: phantom type 字段 vs cap constructor attribute
- **状态**: ✅ **2026-08-05 闭环**(详见 § 3 D23)
- **影响**: sprint 3g 实现复杂度
- **决策**:**sentinel 字段 + codegen skip**(per `v3.x-capability-spec.md` § 待 user 后续决定 #1 建议"实现简单")
- **实现细节**:
  - `Cap<T>` 字段 `_phantom: *T` 在 AST 保留(`_` 前缀 = phantom 标识)
  - 语义分析时识别 `_phantom` 字段为 phantom(zero-sized type)
  - codegen skip `_phantom` 字段 — **不 emit 到 .s**(运行时 0 字节)
  - `Cap<T>` 运行时 layout = `{cnode_idx: u32, depth: u8, rights: u16}` 共 7 字节 + 1 字节 padding = **总 8 字节**
  - 跟 OS 端 cap 表布局 byte-equal(per § 3 D6)
- **影响**:
  - sprint 3g codegen 处理 `_phantom` skip
  - v3.x-capability-spec.md § 内存布局已对齐(per `architecture-refactor § R-9` 已部分改);spec 措辞统一
- **OS 端回答 compiler**:用 sentinel 字段 + codegen skip;`#[cap_constructor]` attribute 是另一个独立机制(Q-OS-001 规则 1),不替代 sentinel
- **无需回复**

#### Q-Compiler-007: Debug ABI 所有权 + spec 起草(2026-08-12 新增)
- **状态**: ✅ **2026-08-12 闭环**(详见 § 3 D41;字段类型分歧另见 D40)
- **影响**: M3 syscall ABI + M5b IPC + sprint 3g 实施
- **决策**(per [`v0.0.4-debug-abi.md`](v0.0.4-debug-abi.md),2026-08-12 起草 + 同日 review 后 🔒 锁):
  - **DebugEventKind / Confidence enum** → jhyy-lang-spec § 22(待增,sprint 3g 启动前锁)
  - **ErrChain / KernelState / KernelStateHistory ABI**(c-typedef + wire format)→ [`v0.0.4-debug-abi.md`](v0.0.4-debug-abi.md) § 5-6(新, primary)
  - **ProvenanceInfo wire format + Confidence 三级标记** → [`v0.0.4-debug-abi.md`](v0.0.4-debug-abi.md) § 4 + § 7(新;7 字段语义 add-only,类型经 D40 修订)
  - **side table 实现细节** → [`v0.0.1-capability.md § 5`](v0.0.1-capability.md)(existing, 引用新 spec)
  - **kernel introspection syscall**(`debug_query_kernel_state(pid)` 等)→ `v0.0.5-syscall-abi-update.md`(OS side,本 Q 已闭环 → **可启动起草**)
- **compiler 侧 review 结论**(2026-08-12,逐节过 § 2-§ 8;§ 3 / § 4 / § 6 / § 8 无异议):
  - **R1(blocking,已修)** § 2.2 DebugEvent header 尺寸三个数互相打架:字段尺寸和 = 54、偏移表实际跨度 = 56(42-43 有 2B 未记账)、按初稿字段序真做自然对齐 = 64(`timestamp_ns: u64 @4` 未 8 对齐)。**决定性约束**:jhyy 无 `packed` / `repr(...)`,且 3a-3n 全部 sprint 均未规划 → 紧凑布局不可表达,wire-format 只能自然对齐。**修法**:按对齐降序重排 → **56B**,无需任何显式内部 padding
  - **R2(blocking,已修)** § 5.2 ErrChain 同一 bug:声称"三个 u64 全部 8-aligned",但 `prev@28` / `trace_off@40` / `source_loc@4` 均未对齐,按初稿字段序真对齐是 72B。**修法**:同样按对齐降序重排 → 仍是 **64B**(尺寸不变,只改字段序)
  - **R3(blocking,已修)** § 5.3 jhyy-side 用了 **sprint 3g 时点仍不存在**的语法(判据是 3g 启动那一刻的语言能力,不是今天的 v1.1.0 baseline;3g 之前只 ship v3.0 的 3a-3f,全是 codegen/attribute 层,无一动类型系统):
    - `Err<T>` 泛型 —— 泛型是 **sprint 3i(v3.2+)**,排在 3g **之后** → 去掉类型参数,与 wire-format 同名 `ErrChain`(`T` 本也未在任何字段使用)。**易误判点**:同期 `Cap<T>` 看似泛型,实为 phantom-type 特例(sema hardcoded + codegen skip `_phantom`,per D12),不走泛型机制,不能据此认为 3g 有泛型
    - `trace: [CapId]` / `context: [ProvenanceInfo]` —— `[T]` 无尺寸数组类型在 3a-3n **从未规划** → 按 D40 规则改 `[*]CapId` / `[*]ProvenanceInfo`
    - § 4.5 `pub enum Confidence` —— `pub` / 可见性修饰符**同样从未出现在任何 sprint 规划里** → 去掉 `pub`;若确需跨模块可见性,应另开 Q 走 spec 增补,不在 debug spec 里夹带
  - **R4(non-blocking,已登记)** ABI § 7.4:struct/enum 不可按值跨 FFI 边界。本 spec 全部 struct 均为内存布局契约(指针传递),不冲突 —— 已在 spec § 9.2 登记,提醒 M3 集成 `SysError.chain` 时以指针传 `ErrChain`
- **关联**:
  - D14 / D16 / D17 / D19 / D21 已锁;`v0.0.4-debug-abi.md` 与 D1-D39 全部决议兼容(per spec § 9.2 兼容表)
  - **D40**(字段类型规则,修订 D14 之 `v0.0.1-capability.md § 5.1`)+ **D41**(本 Q 闭环 + spec 锁)
  - `highlights-technical.md § 7` ErrChain 一行 placeholder 被新 spec 替换
- **OS 端回应 compiler**:R1-R3 全盘接受并已改入 spec;R4 已登记。spec 状态 🟡 Draft → 🔒 Locked
- **无需回复**

---

## § 3 Recent Decisions

> **新格式**:每条标日期 + 🔒 锁 / 📜 存档 + 决策号(D1-D41)+ 一句话 + 关联 doc

### 2026-08-12 🔒 D40: wire-format ↔ jhyy-side 表达规则(修订 D14 字段类型部分)
- **决策**(取代逐字段特判的**可推广规则**):
  > **wire-format 有显式 `*_len` 字段 → jhyy 侧用 `[*]T` slice;wire-format 是 NULL 结尾单向链 → jhyy 侧用 `*T` 裸指针。**
- **全 spec 套用**:
  | 字段 | wire-format | 判定 | jhyy-side |
  |------|------------|------|-----------|
  | `ProvenanceInfo.grant_chain` / `revoke_chain` | `uint64_t`,NULL=root,无 len | 链 | `*ProvenanceInfo`(**改**)|
  | `ErrChain.prev` | `uint64_t`,0=root,无 len | 链 | `*ErrChain`(已正确)|
  | `ErrChain.trace` | `trace_off` + `trace_len` | 数组 | `[*]CapId`(**改**)|
  | `ErrChain.context` | `context_off` + `context_len` | 数组 | `[*]ProvenanceInfo`(**改**)|
- **理由**:
  - 原状态是 jhyy 侧 slice(16B ptr+len)/ wire-format 单 ptr(8B)**两种视图并存**,序列化有损,且 `len` 语义从未定义 —— 没人填、没人信(初稿自己写的就是"取 slice.data 作为 next 指针")
  - grant chain 派生自 cnode 树,**本就是 linked list**(per `v0.0.1-capability.md § 5.4` "单向 list" 措辞)
  - `v0.0.4-debug-abi.md § 7.2` 已承认 list 表达不了 multiparent 分叉 —— 真实结构由新增 DAG `parents[8]`/`children[8]` 承载,slice 语义纯属负担
- **收益**:`ProvenanceInfo` jhyy 侧与 wire-format 均为 **136B**,两侧视图统一,codegen 直译,无 `len` 同步问题
- **影响**:改 `v0.0.1-capability.md § 5.1` 字段类型 + `v0.0.4-debug-abi.md § 5.3 / § 7.3 / § 7.5`;**D14 主体决策不变**(见 D14 条目 📜 修订注)
- **关联**:D14 部分修订;Q-Compiler-007 闭环(D41);`v0.0.4-debug-abi.md § 7.5`;`jhyy-abi-v1.0.0.md § 2.3`(slice = 16B ptr+len)

### 2026-08-12 🔒 D41: Debug ABI spec 锁定 + 所有权(Q-Compiler-007 闭环)
- **决策**:
  - [`v0.0.4-debug-abi.md`](v0.0.4-debug-abi.md) 经 compiler 侧逐节 review(§ 2-§ 8)+ R1-R4 修订后 **🟡 Draft → 🔒 Locked**
  - **所有权**:OS 侧持 spec 起草 + wire format;compiler 侧持 sprint 3g 实施(jhyy-side `DebugEvent` / `Confidence` / `ErrChain` 类型定义 + `DebugEvent::emit()` codegen)
  - **尺寸定案**:DebugEvent **56B** / ErrChain **64B** / StateTransition 48B / KernelStateHistory 12304B / ProvenanceInfo **136B**(全部 align 8)
  - **`v0.0.5-syscall-abi-update.md`**(kernel introspection syscall)解除阻塞,OS 侧可启动起草
- **review 发现(R1-R4)**:详见 § 2.2 Q-Compiler-007 条目。要点:R1/R2 两处 c-typedef 尺寸与自然对齐自相矛盾(54/56/64 与 64/72),根因是 **jhyy 无 `packed`/`repr(...)` 且 3a-3n 全程未规划** → wire-format 只能自然对齐,按对齐降序重排解决;R3 jhyy-side 用了 3g 时点不存在的语法(泛型在 3i,`[T]` 与 `pub` 从未规划);R4 FFI 按值传参限制已登记
- **方法论(值得沿用)**:跨边界 spec 的语言可行性,判据是**该 spec 实现 sprint 启动那一刻**的语言能力,不是起草当天的 baseline,也不是"迟早会有"。3g 之前只 ship v3.0 的 3a-3f,全是 codegen/attribute 层,不动类型系统
- **关联**:Q-Compiler-007 闭环;D40(字段类型规则);D14/D16/D17/D19/D21 兼容(per spec § 9.2);sprint 3g 启动前置解除

### 2026-08-05 🔒 D8: v2.0 milestone 是 M1 启动硬前置(2026-08-05 新增)
- **决策**:M1 启动的两个并联前置 = v2.0(`amd64_win_freestanding` target + hello.efi demo,走 QBE+GCC,无 libc link)+ v3.0(6 特性 3a-3f)
- **理由**:v2.0 提供 target 能力(走 MSVCRT 替代 libc);v3.0 提供 OS 必备语言特性。两层独立可并行,但都要 M1 前完成
- **冲突解决**:任何 OS doc 跟 v2.0 节点冲突时,以 `v2.0.0-os-prep § 1` 为准
- **关联**:v0.0.2 § 4 镜像 + v0.0.1.5 § 1 #2-3

### 2026-08-05 🔒 D9: 3g/3g.5/3g.7 在 M3-M4 之间(不在 M1 之前)(2026-08-05 新增)
- **决策**:v3.1 sprint 3g + 3g.5 + 3g.7 是 **M4 启动的硬前置**,**不**在 M1 之前完成
- **理由**:跟 compiler D5(`v2.0.0-os-prep § 3`)一致;v3.1 跟 M2-M3 OS 实施可并行
- **冲突解决**:任何 OS doc 把 3g 放在 M1 之前 → 撤回
- **关联**:v0.0.2 § 4 链式图(已校准)+ v0.0.1.5 § 1(已校准)+ 本文件 § 0 Critical Path

### 2026-08-05 🔒 D10: `#[no_std]` 软要求 — v2.0 freestanding 已覆盖不 link libc(2026-08-05 新增)
- **决策**:M1 启动的硬前置**不**是 `#[no_std]` 属性本身,而是 v2.0 milestone 的"不 link libc"保证。`#[no_std]` 属性(sprint 3d)是 v3.0 内的代码风格属性(给 OS 代码清晰度),不是 M1 硬阻塞
- **理由**:compiler D3(`v2.0.0-os-prep § 3`)锁:"v2.0 freestanding 不依赖 `#[no_std]` crate attr(只需'不 link libc');`#[no_std]` 跟 v3.0 sprint 3d 联动"
- **代价**:MVP 早期 OS 代码可以**不**用 `#[no_std]`(v2.0 已能编);sprint 3d 落地后可选择性加(更标准的风格)
- **关联**:v0.0.1.5 § 1 #7 标注"(软要求)";v0.0.2 § 4 M1 行

### 2026-08-05 🔒 D11: `&mut` 借用矩阵 — M1-M3 用 raw pointer, M4+ 可改 `&mut`(2026-08-05 新增)
- **决策**:
  - M1-M3 OS 代码:`*mut T` / `*const T` raw pointer + 手动 discipline
  - M4 起 OS 代码:可改 `&mut T` + lifetime(借 sprint 3g)
- **理由**:compiler D5(`v2.0.0-os-prep § 3`)锁:"M1-M10 用 `*mut T` raw pointer + 手动 discipline;sprint 3g 后改 `&mut`"
- **撤回**:之前 OS 侧写的"M1 起即可用 &mut" 错(基于旧 v0.0.2 § 4 链式图把 3g 放 M1 之前),已撤回
- **关联**:v0.0.2 § 6.2 ⚠️(已恢复);本文件 Q-OS-005

### 2026-08-05 🔒 Q-OS-008 终结:Cap revocation = lazy invalidation(2026-08-05 锁)
- **决策**:lazy invalidation 协议(详见 § 2.1 Q-OS-008)— 内核在 cap 被 revoke 时只标 invalid,userland 下次 syscall 触碰时收 `ErrCapRevoked`
- **理由**:不增 syscall / 不动 ABI / 跟现有错误码体系兼容 / 跟 v0.0.1-capability § 8 放弃 propagation 一致
- **关联**:v0.0.1-capability.md § 8 placeholder 终结;v3.x-capability-spec.md 行 300 OS 端回复

### 2026-08-05 🔒 D12: Cap<T> 8 条编译期规则实施细节锁(Q-OS-001 闭环)
- **决策**(per `v3.x-capability-spec.md` § "实施拆 sprint" + § "待 user 后续决定"):
  - **sprint 拆法**:3g(主体)+ 3g.5(phantom 0-byte codegen)+ 3g.7(jhyy_OS cap 表 byte-equal 联调)— 三段独立
  - **`Move` trait 关系**:**sprint 3g hardcoded move-only,不依赖 trait 系统**;trait 系统等 sprint 3i
  - **`#[cap_constructor]` 函数体限制**:只能调 `#[syscall]` / `#[kernel_entry]`(双重门控)
  - **`into_raw` 必须 `unsafe` block + warning**(per Rust 风格)
- **关联**:Q-OS-001 闭环;v3.x-capability-spec.md § 8 条规则 + § 验收标准;v0.0.1-capability.md

### 2026-08-05 🔒 D13: Type-driven IPC 用 attribute 解决, 不进 spec § X(Q-OS-002 闭环)
- **决策**:`#[ipc_handler(msg: M, env: *E)]` attribute + sema 检查 + codegen dispatch table
- **理由**:per 原则 5 + 1;不进 spec 复杂化
- **长期(可选)**:等 sprint 3i trait 系统后 sugar 成 `impl Handler<M>`
- **关联**:Q-OS-002 闭环;v0.0.1-syscall-abi.md § 1.1

### 2026-08-05 🔒 D14: Compile-time provenance 是 OS 独有 debug,不进 std(Q-OS-003 闭环)
- **决策**:
  - **影响 codegen + runtime metadata**(不是 spec 层)
  - debug build 每个 `Cap<T>` 携带 provenance side table;release build strip
  - **不进 std lib**(per Q-Compiler-004)
  - spec 增补 lang-spec § 21(待增)— 描述 `Cap::provenance() -> DebugInfo` 接口
- **关联**:Q-OS-003 闭环;Q-Compiler-004 闭环;v0.0.1-capability.md § 5
- 📜 **部分修订(2026-08-12,D40)**:`v0.0.1-capability.md § 5.1` 的 `grant_chain` / `revoke_chain` 字段类型由 `[*]ProvenanceInfo` slice 改为 `*ProvenanceInfo` 裸指针。**D14 主体决策(OS 独有 / 不进 std / debug build side table / `Cap::provenance()` 接口)不变**,本条仍有效。

### 2026-08-05 🔒 D15: `unsafe_cap` 块语法 = `unsafe cap { ... }`,进 spec § 19(Q-OS-004 闭环)
- **决策**:
  - **进 spec § 19(待增)** — 不放 OS std lib
  - **语法**:`unsafe cap { ... }`(复用 `unsafe` 语义,加 `cap` 关键字)
  - **不需要 `#![feature(unsafe_cap)]` gate** — 默认 sprint 3g 实现后启用
  - **WaiverCap** privilege = 进程 capability 表 single bit;双重门控(编译期 + 运行期)
- **关联**:Q-OS-004 闭环;Q-Compiler-002 闭环;v0.0.1-capability.md § 4 Narrow Waivers;v0.0.2-foundation-revision.md § 3.3

### 2026-08-05 🔒 D16: Cap 跨 IPC cap-offset 表 = 双路径 emit(Q-OS-007 闭环)
- **决策**:
  - **主路径**:codegen 时**内联到 syscall wrapper**(快路径)
  - **次路径**:**metadata 段 emit**(loader 友好,debug 用)
  - **复用 `&mut` 借用检查的 struct field offset 表**(不重复实现)
  - **ABI § 12 wire 形式**:`{msg_tag: u32, n_caps: u16, cap_offsets: [u16; n]}`(放在 16 字节 header 之后、payload 之前)— **OS 建议同意**
  - **sprint**:sprint 3g 同步出,**不单独 sprint**
- **关联**:Q-OS-007 闭环;v0.0.1-syscall-abi.md § 1.1.4 ⚠️ P0-4 标记可移除

### 2026-08-05 🔒 D17: `IoResult<T>` 路径 A(单态化) for MVP M1-M10(Q-OS-009 闭环)
- **决策**:`IoResult` 拆成 `IoResultUsize` / `IoResultReply` / `IoResultUnit` 三个具体 enum
- **理由**:M1-M10 真不需要动态类型(boot + IPC + 基础 cap 操作);sprint 3i 不依赖
- **M11 升级路径(可选)**:sprint 3i 后 `IoResultXxx` 可手动合并回 `IoResult<T>`
- **影响**:v0.0.1-syscall-abi.md § 1.4.1 ⚠️ P0-5 标记可移除(改为单态 enum);v0.0.1-process-model.md § 5.1 同步
- **关联**:Q-OS-009 闭环

### 2026-08-05 🔒 D18: OS 端 M4 起就用 `Cap<T>`,不暂缓(Q-Compiler-001 闭环)
- **决策**:M4 起 OS 代码就用 `Cap<T>`;**sprint 3g 优先级 = P0**(M4 硬前置,不推迟)
- **理由**:M1-M3 没 cap 概念(boot + scheduler + syscall);M4 = capability 落地
- **OS 端回答 compiler**:M4 起就用;M1-M3 用 raw pointer + 显式权控
- **关联**:Q-Compiler-001 闭环;§ 3 D11 &mut 矩阵

### 2026-08-05 🔒 D19: `unsafe_cap` 进 spec § 19,WaiverCap 是 OS std(Q-Compiler-002 闭环)
- **决策**:
  - **进 spec** — `unsafe cap` block 语法通用(其他打破 cap 不变量场景可用)
  - **WaiverCap** = OS std lib 提供(sprint 3l std 阶段)
- **关联**:Q-Compiler-002 闭环;Q-OS-004 已闭环(D15);v0.0.1-capability.md § 4

### 2026-08-05 🔒 D20: Type-driven IPC 不进 spec,MVP 用 attribute(Q-Compiler-003 闭环)
- **决策**:`#[ipc_handler]` attribute 实现;不进 lang-spec § X(per 原则 5 + 1)
- **关联**:Q-Compiler-003 闭环;Q-OS-002 已闭环(D13)

### 2026-08-05 🔒 D21: Compile-time provenance 不进 std,OS 独有(Q-Compiler-004 闭环)
- **决策**:不进 std(jhyy 编译器自身用 arena.jhyy 够,不需 provenance)
- **关联**:Q-Compiler-004 闭环;Q-OS-003 已闭环(D14);v3.x-capability-spec.md 不变

### 2026-08-05 🔒 D22: arena.jhyy 不扩展,OS 用 cap + offset 自管(Q-Compiler-005 闭环)
- **决策**:
  - arena API 不动(保持匿名)
  - OS 端 cap 表 + offset 表自己实现(在 jhyy_OS std 模块)
  - arena = 编译期 region-based 内存;cap = 运行期权限机制 — 两层不混合
- **关联**:Q-Compiler-005 闭环;`compiler/src0/arena.jhyy` 不变

### 2026-08-05 🔒 D23: phantom 实现 = sentinel 字段 + codegen skip(Q-Compiler-006 闭环)
- **决策**:
  - `_phantom: *T` 字段在 AST 保留;语义分析识别 `_` 前缀 = phantom
  - codegen skip `_phantom` 字段 — **不 emit 到 .s**(运行时 0 字节)
  - `Cap<T>` 运行时 layout = `{cnode_idx: u32 + depth: u8 + rights: u16}` = 7 字节 + 1 padding = **总 8 字节**
  - 跟 OS 端 cap 表 byte-equal(per D6)
- **关联**:Q-Compiler-006 闭环;v3.x-capability-spec.md § 内存布局已对齐;per `architecture-refactor § R-9`

### 2026-08-05 🔒 D24 UD-1: v0.9 codegen bug 真修顺序 = 全修一口气清干净
- **决策**(per `architecture-refactor § 15` 待 user 决定 #1):
  - **W-001 ~ W-009 全部真修**(v0.9 一口气清干净)
  - 加上 29-extsw hypothesis 验证(grep arena.jhyy ptr 算术上下文)
  - **不分散到 v1.0 末**(per § R-1 v0.9 新建理由)
- **影响**:v0.9.0 任务清单新增;regress baseline **12 OK(持平,v0.8 wip commit 12 收尾,per changelog-v0.8.0)** → v0.9 末持平 + W 删干净
- **OS 对接**:0(v0.9 仍是 C 端编译器阶段,OS 不可启动)

### 2026-08-05 🔒 D25 UD-2: v2.0 `amd64_win_freestanding` 走 QBE + GCC
- **决策**(per `architecture-refactor § 15` 待 user 决定 #2):
  - **v2.0 仍走 QBE + GCC**(实施快,无新 IL → .s 阶段)
  - QBE 自写 → .s 推到 **v2.x 中期**(per `architecture-refactor § 16.7`)
  - v2.0 关键 = `jhyy --target=amd64_win_freestanding hello.jhyy -o hello.efi`(走 OVMF 跑通)
- **影响**:v2.0.0 任务清单 + v2.x-qbe-rewrite 范围重写(per `architecture-refactor § R-6`)
- **OS 对接**:**第一项解锁** — jhyy 编 jhyy_OS kernel.efi(无 libc link)

### 2026-08-05 🔒 D26 UD-3: v2.0 .exe byte-equal 纳为完成定义
- **决策**(per `architecture-refactor § 15` 待 user 决定 #3):
  - **纳为完成定义**:`jhyy_v1.il` byte-equal `jhyy_v2.il` + `jhyy_v1.s` byte-equal `jhyy_v2.s` + `.exe byte-equal`(兜底)
  - `.exe byte-equal` 达成路径:`gcc -g0 + strip + SOURCE_DATE_EPOCH + --build-id=none`(per `architecture-refactor § 16.7`)
  - **OS 镜像可重现** 是关键收益(便于 debug + rollback)
- **影响**:v2.0 验收标准加 byte-equal 三件套;build.md 加 SOURCE_DATE_EPOCH 段
- **OS 对接**:0(OS 不依赖 byte-equal,但镜像可重现便于 jhyy_OS build 验证)

### 2026-08-05 🔒 D27 UD-4: sprint 3g 联动 = 3g + 3g.5 + 3g.7 三段
- **决策**(per `architecture-refactor § 15` 待 user 决定 #4):
  - **3g 主体**:`&mut + lifetime` + Cap<T> 8 条编译期规则 + sema 实现(per `v3.x-capability-spec § 8`)
  - **3g.5 phantom 0-byte 布局保证**:codegen + abi 锁定(per D23 / Q-Compiler-006)
  - **3g.7 联调**:jhyy_OS cap 表 byte-equal 验证(M4 启动硬前置)
  - 三段顺序强制(不可调换)— 3g.5 依赖 3g 的 codegen 路径;3g.7 依赖 3g.5 的 phantom 0-byte 锁定
- **影响**:v3.x-language-expansion.md § Sprint 3g 拆三段;v3.x-capability-spec.md § "实施拆 sprint" 锁定
- **OS 对接**:**M4 启动可达**

### 2026-08-05 🔒 D28 UD-5: v3.x 后续(3h-3n)启动时机
- **决策**(per `architecture-refactor § 15` 待 user 决定 #5):
  - **3h 浮点**:3g.7 后可推(语言便利性,M1 启动后即可)— 但 MVP 内核不用 f32/f64,优先级低
  - **3i generics + 3j closures + 3l std lib**:**M11 启动前必推**(M11 硬前置,per `v2.0.0-os-prep § 1`)
  - **3k 错误恢复**:3j 后推(UX 改进,不阻塞 MVP)
  - **3m 基本优化**:3l 后推(性能,自举后)
  - **3n 包管理器**:延后到 M11 之后(UX,跟 OS 启动无关)
- **影响**:v3.x-language-expansion.md sprint 3h-3n 优先级明确
- **OS 对接**:M1 启动后立刻推 3g(v3.1);M11 启动前推 3i + 3j + 3l

### 2026-08-05 🔒 D29 UD-6: v0.8 / v0.9 changelog 撰写时机
- **决策**(per `architecture-refactor § 15` 待 user 决定 #6):
  - **v0.8 changelog**:**现在收尾写**(commit 1-12 全记)— 跟 v0.8 wip branch 收尾同步
  - **v0.9 changelog**:**v0.9 启动前写**(任务清单冻结后才发)
  - v1.0.0 changelog:**v1.0 真闭环达成后写**(jhyy_1 跑 regress 持平)
- **影响**:v0.8 / v0.9 任务清单 § 验收 段引用 changelog;doc 维护节奏清晰
- **OS 对接**:0(doc 维护,不影响 OS 启动)

### 2026-08-05 🔒 D30: GUI 架构 = Wayland-style + jhyy capability 增强
- **决策**:GUI 协议 = Wayland 风格(compositor + surface + seat + buffer cap 体系)— 借用 Wayland 协议做参考,但用 jhyy `Cap<T>` 替代 fd,8 字节 phantom 0-byte
- **理由**:
  - microkernel + capability + type-driven IPC 跟 Wayland 模型**同构** — 不是"做 Wayland clone",是"识别已有选型"
  - 5 原则全契合(§ 9.2)
  - Wayland 工具(weston / sway / wlroots)可参考实现,但不引用代码(per D37)
- **关联**:v0.0.4-gui-explorations.md § 2 候选 A + § 4 协议草案
- **OS 对接**:M8d 协议层直接走这条

### 2026-08-05 🔒 D31: GUI Milestone = 候选 C(M8d 协议层 + M12 GUI 工具包两阶段)
- **决策**:不把 GUI 全塞进 M8a(M8a 仍是 framebuffer persistent + UEFI GOP);新加 M8d(协议层,在 M8c 之后)+ M12(GUI 工具包,在 M11 之后)
- **理由**:
  - 候选 A(M8a' + M8d):拉前 sprint 3h,M8a 范围爆炸
  - 候选 B(M12 独立):GUI 太晚,jhyy 编译器自身没法用 GUI 工具
  - 候选 C(两阶段):**阶段清晰,jhyy 编译器 M8d 末立即能写 GUI 协议测试**;M11 后吃完整 3i/3j/3l 的 M12 GUI 工具包
  - 候选 D(集成 M11):M11 范围爆炸
- **关联**:v0.0.4-gui-explorations.md § 3 候选 C + § 9 风险矩阵
- **OS 对接**:M8d / M12 加入主线 milestone(等 jhyy_OS 启动 M8d 时细化)

### 2026-08-05 🔒 D32: M8d 时机 = M8c 之后(M5b + 3g.5 + 3g.7 完成后)
- **决策**:M8d compositor 启动硬前置 = M5b(IPC 实现)+ 3g.5(phantom 0-byte codegen)+ 3g.7(cap table byte-equal 联调)— 跟 M8c 一起在 M4 后启动
- **理由**:
  - M8d 协议层需要 IPC(M5b)传递 cap,需要 phantom 0-byte(3g.5)保证 Cap<Surface> 8 字节 wire 格式,需要 cap table byte-equal(3g.7)保证跨进程 cap 表一致
  - M8c(PCI / AHCI driver)跟 M8d 都依赖 M4 capability 体系,自然挨在一起
- **关联**:coordination.md § 0 Critical Path(已有 M5b / 3g.5 / 3g.7 节点)+ v0.0.4-gui-explorations.md § 3 候选 C
- **OS 对接**:M8d 真实施时按此排期

### 2026-08-05 🔒 D33: D28 不调整 — M8d 单态 type + function pointer 妥协
- **决策**:D28(v3.x 后续 3h-3n 启动时机)**不动**;M8d protocol 用单态 type(每个 surface role / seat role 写一份 message type 跟 handler),事件 handler 用 function pointer(非闭包),字体用整数调色板(无 f32/f64)— M12 GUI 工具包直接吃完整 3h(浮点抗锯齿)+ 3i(`Widget<T>` generics)+ 3j(闭包事件 handler)+ 3l(std GUI lib)
- **理由**:
  - **推前 3h/3i/3j 会破坏 compiler sprint 节奏**(per 5 原则 #1 "可行且简单")
  - **M8d 单态 type 妥协**:N 个 surface role × N 个 message type ≈ 1k 行重复,但**协议能跑**
  - **OS 团队不需要靠"推前 compiler sprint"来解锁 GUI**(per 5 原则 #2 "双线作战")
- **代价**:
  - M8d protocol 代码量增加(~1k 行)— 但 OS 团队 hold 得住
  - M12 GUI 工具包必须等 M11(3i+3j+3l 都在 M11)— **这跟 GUI 工具包本来就在 M12 一致,无新阻塞**
- **关键洞察**:**GUI 一来不一定要推前 compiler sprint** — protocol 层单态 type 妥协就能 M8d 用,M12 GUI 工具包自然等 M11
- **关联**:v0.0.4-gui-explorations.md § 5.3;本文件 § 3 D28
- **OS 对接**:M8d 协议层按单态 type 设计;M12 GUI 工具包自然吃完整特性

### 2026-08-05 🔒 D34: M8d 走 CPU 合成,GPU 留 post-M12
- **决策**:M8d / M12 早期 compositor 在 CPU 上 blend / scale(skia 软渲染模式);GPU 加速(drm / i915 / amdgpu driver,virtio-gpu,vulkan subset)留 post-M12 性能瓶颈触发
- **理由**:
  - GPU driver 协议极复杂(Vulkan spec ~1000 页)— 5 原则 #1 直接淘汰
  - 60 FPS @ 1080p skia 软渲染 = 单核 50%,够 demo + 简单应用
  - 5 原则 #1 + #3 直接胜出
- **关联**:v0.0.4-gui-explorations.md § 6 候选 A
- **OS 对接**:M8d compositor 几百行 blend 代码;post-M12 再评估 GPU

### 2026-08-05 🔒 D35: 输入事件 push 模式 + serial 字段
- **决策**:输入事件流 = push(硬件中断 → input driver(M8b)→ compositor IPC → 目标 GUI app)— 不走 pull(轮询)。每事件携带 serial 字段(compositor 单调递增),接收方在 focus out 后用 serial 判 stale 并丢弃
- **理由**:
  - push 比 pull 简单(compositor 主循环已知所有 seat)
  - serial 字段防"focus out 后 key event 泄漏"(per Wayland 教训)
  - cap provenance + walkable error chain 帮 debug 事件路由问题
- **关联**:v0.0.4-gui-explorations.md § 7 输入事件模型 + § 4.2 输入协议
- **OS 对接**:M8d compositor + input driver 一起按 push 设计;spec § 22 草案(待 M8d 实施时细化)

### 2026-08-05 🔒 D36: GUI 工具包风格 = egui 立即模式
- **决策**:M12 GUI 工具包 = egui 风格(每帧重新生成 widget tree)— 不走 iced 保留模式(diff 算法)
- **理由**:
  - egui 立即模式 = 简单(每帧从 state 渲染)— 5 原则 #1 直接胜出
  - iced 保留模式 = Elm 风格 diff 算法复杂 — 违反"可行且简单"
  - egui 已有 Rust 实现可参考实现(jhyy 移植,不是代码复用)
- **关联**:v0.0.4-gui-explorations.md § 11 边界 #9;M12 实施时细化
- **OS 对接**:M12 启动前 GUI 工具包 spec 起草

### 2026-08-05 🔒 D37: Wayland 参考实现 = 只参考协议,不引用代码
- **决策**:jhyy_OS GUI 协议层参考 Wayland 协议(compositor / surface / seat / buffer 概念)— 但**不引用 sway / wlroots 代码**(jhyy_OS 必须纯 jhyy,per 5 原则 #5 "kernel 不解决语言问题")
- **理由**:
  - Wayland 工具是 C 实现,跟 jhyy 类型系统 / phantom / capability 不直接对应
  - 协议对得上即可(compositor → surface commit → buffer → seat input)
  - 5 原则 #5 直接胜出(per `feedback_jhyy_extensible.md`)
- **关联**:v0.0.4-gui-explorations.md § 4 Wayland-style 协议草案 + § 11 边界 #8
- **OS 对接**:M8d 协议层按 jhyy 类型重新设计,不复制 C 实现

### 2026-08-05 🔒 D38: GUI 测试策略 = QEMU + screenshot 自动化
- **决策**:M8d 起 GUI 测试走 QEMU + screenshot 自动化(类似 wlroots test infrastructure)— 不引入额外测试框架
- **理由**:
  - QEMU 已在 PATH(M1-M11 复用)— 不增加开发依赖
  - screenshot 对比能验证 compositor 输出(像素级)
  - 5 原则 #3 "寄生 Windows" 直接胜出
- **关联**:v0.0.4-gui-explorations.md § 11 边界 #4
- **OS 对接**:M8d 设计时定测试 harness 细节(screenshot diff / reference image 库)

### 2026-08-05 🔒 D39: GPU driver 触发 = post-M12 性能瓶颈显现时
- **决策**:GPU driver(virtio-gpu / 简化 DRM 子集)不在 M8d / M12 路线;只有 post-M12 出现性能瓶颈(CPU 软渲染帧率掉到 30 FPS 以下)才评估
- **理由**:
  - 不为"未来可能"投资(5 原则 #1)
  - M8d / M12 用户场景(IDE / regress / debugger)CPU 软渲染够用
  - post-M12 真要 4K / 3D / 动画时再上 GPU
- **关联**:v0.0.4-gui-explorations.md § 6 + § 11 边界 #10
- **OS 对接**:M8d / M12 全 CPU 路径;post-M12 评估触发条件

### 📜 2026-08-04 🔒 D1: boot 路径锁 UEFI + PE/COFF
- **决策**:不用 multiboot2+ELF 路径(MVP),走 QEMU + OVMF + jhyy 编 .efi
- **关联**:v0.0.1-syscall-abi.md § 2 + `v2.0.0-os-prep § 3 D1` + 2026-08-04 spike 验过(`spike/boot.s`)

### 📜 2026-08-04 🔒 D2: 混合内存模型锁 region types primary
- **决策**:不用 borrow checker as primary(违反"可行且简单"原则),走 region types primary(jhyy 编译器自身用 arena.jhyy)
- **关联**:v0.0.2-foundation-revision.md § 3.2

### 📜 2026-08-04 🔒 D3: MVP M11 依赖图锁
- **决策**:M1-M10 不需 generics/closures/async;M11 才需(sprint 3i+3j+3l)
- **关联**:v0.0.2-foundation-revision.md § 4(本文件 § 0 已校准更新)+ `v2.0.0-os-prep § 2`

### 📜 2026-08-04 🔒 D4: 缺 feature = 设计输入(非 blocker)
- **决策**:jhyy 是 OS-driven,缺 feature 就加,只要不冲突现有 spec
- **memory ref**:`feedback_jhyy_extensible.md`

### 📜 2026-08-04 🔒 D5: jhyy spec 当前能力 baseline 锁
- **决策**:v1.1.0 spec(v0.7 编译器)能用的 = baseline;不靠 spec 不存在的特性
- **关联**:v0.0.2-foundation-revision.md § 6

### 📜 2026-08-03 🔒 D6: Cap<T> phantom type 8 字节布局锁
- **决策**:`{cnode_idx: u32, depth: u8, rights: u16}` + `_phantom: *T`(0 字节) = 总 8 字节
- **关联**:v0.0.1-capability.md § 1 + `v3.x-capability-spec.md`

### 📜 2026-08-04 🔒 D7: v2.0 milestone 落盘(2026-08-04 OS-prep doc 重写)
- **决策**:v2.0 = `amd64_win_freestanding` target + spec § 12 + hello.efi demo;v3.0 = 6 特性(3a-3f);v3.1 = `&mut + Cap<T>`(3g/3g.5/3g.7)
- **关联**:`v2.0.0-os-prep § 1-2`(本文件 § 0 镜像)

---

## § 4 Cross-Reference Tables

### 4.1 OS doc ↔ Compiler doc 对齐状态(2026-08-05 校准)

| OS doc | 对应 Compiler doc | 对齐状态 |
|--------|------------------|---------|
| [v0.0.1-capability.md](v0.0.1-capability.md) | [v3.x-capability-spec.md](../../JiHuiYiYou/docs/plans/roadmap/v3.x-capability-spec.md) | ✅ 已对齐(8 字节 + 8 条规则) |
| [v0.0.1-capability.md § 4 Narrow Waivers](v0.0.1-capability.md) | 无对应 | 🟡 待编译器 review (Q-Compiler-002) |
| [v0.0.1-capability.md § 5 provenance](v0.0.1-capability.md) | 无对应 | 🟡 待编译器 review (Q-Compiler-004) |
| [v0.0.1-syscall-abi.md § 1.1 Type-driven IPC](v0.0.1-syscall-abi.md) | 无对应 | 🟡 待编译器 review (Q-OS-002) |
| [v0.0.1-syscall-abi.md § 1.4 类型化错误码](v0.0.1-syscall-abi.md) | [lang-spec § 11 enum match](../../JiHuiYiYou/docs/abis/jhyy-lang-spec-v1.1.0.md) | ✅ 现有特性够用 |
| [v0.0.0-design.md § 6 路线图](v0.0.0-design.md) | [v3.x-language-expansion.md](../../JiHuiYiYou/docs/plans/roadmap/v3.x-language-expansion.md) | ✅ M1-M11 ↔ sprint 3a-3l |
| [v0.0.2-foundation-revision.md § 4](v0.0.2-foundation-revision.md) | [v2.0.0-os-prep.md](../../JiHuiYiYou/docs/plans/v2/v2.0.0-os-prep.md) § 1-2 | ✅ **2026-08-05 锁** 镜像 |
| [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md) | [v2.0.0-os-prep.md](../../JiHuiYiYou/docs/plans/v2/v2.0.0-os-prep.md) § 1 + 5.4 | ✅ **2026-08-05 锁** 镜像 |
| [v0.0.1-syscall-abi.md § 1.1.4 cap-offset 表](v0.0.1-syscall-abi.md) | [jhyy-abi-v1.0.0.md § 12 (待增)](../../JiHuiYiYou/docs/abis/jhyy-abi-v1.0.0.md) | ✅ 2026-08-05 闭环(D16 / Q-OS-007);spec 实施 = sprint 3g.7 |
| [v0.0.1-syscall-abi.md § 1.4.1 单态 enum IoResult](v0.0.1-syscall-abi.md) | [jhyy-lang-spec-v1.1.0.md § 11 enum match](../../JiHuiYiYou/docs/abis/jhyy-lang-spec-v1.1.0.md) | ✅ 2026-08-05 闭环(D17 / Q-OS-009);已实施 `IoResultUnit` (process-model § 5.1 line 120) |

### 4.2 Compiler sprint ↔ OS milestone(2026-08-05 校准)

| Compiler sprint | 节点 | 启用时点 | OS milestone | OS 影响 |
|-----------------|------|---------|--------------|---------|
| — | **v2.0** | v2.0 | M1 target 能力 | M1 硬前置 |
| 3a inline asm | v3.0 | v3.0 | M1 (boot MMIO / 端口 I/O) | M1 硬前置 |
| 3b `#[naked]` | v3.0 | 3a 后 | M1 (boot entry) | M1 硬前置 |
| 3c volatile | v3.0 | 3b 后 | M1, M8a (MMIO framebuffer) | M1 硬前置 |
| 3d `#[no_std]` | v3.0 | 3c 后 | M1+ 代码风格 | **软** (v2.0 已覆盖) |
| 3e `#[link_section]` | v3.0 | 3d 后 | M1 (boot 段) | M1 硬前置 |
| 3f memory barrier | v3.0 | 3e 后 | M1 (基本), M9 (SMP) | M1 硬前置 |
| 3g `&mut + lifetime` | **v3.1** | 3f 后 | **M4** capability | **M4 硬前置**(不在 M1 之前) |
| 3g.5 phantom 0-byte | v3.1 | 3g 后 | M4 | M4 硬前置 |
| 3g.7 cap table 联调 | v3.1 | 3g.5 后 | M4 | M4 硬前置 |
| 3h 浮点 | v3.2 | 3g.7 后 | — | MVP 用不上 |
| 3i generics | v3.2+ | 3h 后 | M11 (编译器源 `Vec<T>`) | M11 硬前置 |
| 3j closures | v3.2+ | 3i 后 | M11 (编译器源闭包) | M11 硬前置 |
| 3k 错误恢复 | v3.2+ | 3j 后 | — | UX |
| 3l std lib | v3.2+ | 3k 后 | M11 (编自己需 std + runtime) | M11 硬前置 |

详见 [v0.0.2-foundation-revision.md § 4](v0.0.2-foundation-revision.md) + [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md)

---

## § 5 待定 spec 增补

| 归属 | spec section | 内容 | 状态 | 触发条件 |
|------|--------------|------|------|---------|
| jhyy lang-spec | § 18(待增)| `Cap<T>` 定义 + 8 条编译期规则 | ⏳ 草案 | v3.1 sprint 3g 启动前锁 |
| jhyy lang-spec | § 19(待增)| `unsafe cap { ... }` block 语法 + WaiverCap 语义 | ⏳ 草案 | sprint 3g 启动前锁(D15 / D19 闭环)— 进 spec 不放 OS std |
| jhyy abi | § 13(待增,§ 12 = 版本历史 v1.0.0 锁定)| Cap wire format + cnode 布局 + **多 target ABI 表 + freestanding ABI 约定** + **cap-offset 表 wire 形式 `{msg_tag: u32, n_caps: u16, cap_offsets: [u16; n]}`** + Debug ABI 镜像 | ⏳ 草案 | v2.0 milestone 启动前锁(由 compiler D5 + v2.0.0-os-prep § 5.1 #5 触发);cap-offset 部分 **2026-08-05 D16 锁** |
| jhyy lang-spec | § 20(待增)| ~~Type-driven IPC handler 签名验证~~ | ✅ **2026-08-05 D13 / D20 闭环** | **不进 spec**,MVP 用 `#[ipc_handler]` attribute |
| jhyy lang-spec | § 21(待增)| Compile-time provenance 接口(`Cap::provenance() -> DebugInfo`) | ⏳ 草案 | sprint 3g 启动前锁(D14 / D21 闭环)— OS 独有,不进 std |

---

## § 6 Action Items(滚动)

### OS 侧待办

- [x] Q-OS-001 / Q-OS-002 / Q-OS-003 / Q-OS-004 / Q-OS-005 / Q-OS-006 / Q-OS-007 / Q-OS-008 / Q-OS-009 **全部 2026-08-05 闭环**(详见 § 3 D11-D17 / D12-D17 / § 2.1 各 Q)
- [ ] (内部)细化 sema 8 条规则实现路径(D12 已给 8 条规则 sprint 3g 内实施路径)
- [x] Type-driven IPC sema 检查算法(D13 已定:`#[ipc_handler]` attribute)
- [ ] (内部)细化 cap closure linter 设计
- [ ] (内部)spike/boot.s → jhyy M1 boot stub 翻译(等 v2.0 freestanding + v3.0 6 特性)
- [x] (内部)v0.0.1-syscall-abi.md ⚠️ P0-4 (Q-OS-007 / D16 闭环) 标记移除 → 已替换为 § 1.1.4 ✅ 闭环说明(line 64)
- [x] (内部)v0.0.1-syscall-abi.md ⚠️ P0-5 (Q-OS-009 / D17 闭环) 标记移除 → ✅ 已删除(grep 0 命中,剩余 ⚠️ = P0-3 独立开放问题)
- [x] (内部)v0.0.1-process-model.md § 5.1 `IoResult<()>` → `IoResultUnit`(同步) → ✅ 已替换(line 120 注释 + 代码 + 单态 enum 同步生效)
- [x] **GUI 集群探索已落盘**:`docs/v0.0.4-gui-explorations.md`(2026-08-05)— 推荐候选 C(M8d 协议 + M12 工具包两阶段)+ 推前 sprint 3h/3i/3j 提议
- [x] **GUI 决策 D30-D39 全部 agent 锁**(2026-08-05)— D33 关键:**D28 不调整**,M8d 单态 type 妥协,M12 GUI 工具包吃完整 3h/3i/3j/3l
- [ ] (内部)M8d 协议层 spec 起草(per D30/D32)— 等 M5b + 3g.5 + 3g.7 完成后启动
- [ ] (内部)M12 GUI 工具包 spec 起草(per D31/D36)— 等 M11 完成后启动
- [ ] (内部)M8a 实施时确认用整数调色板(per D33)— 不依赖 sprint 3h 浮点

### Compiler 侧待办(OS 端确认)

- [x] Q-Compiler-001 / Q-Compiler-002 / Q-Compiler-003 / Q-Compiler-004 / Q-Compiler-005 / Q-Compiler-006 **全部 2026-08-05 闭环**(详见 § 3 D18-D23 / § 2.2 各 Q)
- [x] Q-Compiler-007: Debug ABI 所有权 + spec 起草 → ✅ **2026-08-12 闭环**(详见 § 3 D41;字段类型分歧走 D40)。`v0.0.4-debug-abi.md` 🔒 Locked,sprint 3g 启动前置解除
- [x] (内部)v1.0 closure 自举 → ✅ **TAGGED 2026-08-10**(commit `eabee0d`),Stage 2 三层 N=3 byte-equal 闭环(.il sha `2445e97d...`),regress 持平 50/53 baseline — 实际结果优于预期(预期 12 OK 持平即可,实际 50/53)
- [x] (内部)v0.9 启动:codegen bug W-001~W-009 全修 + main.c 翻译 + Stage 1 byte-equal(per D24) → ✅ **shipped 2026-08-11**(wip commit 2.83)
- [ ] (内部)v2.0 milestone:`amd64_win_freestanding` target + spec § 12 + hello.efi demo(走 QBE + GCC per D25)
- [ ] (内部)v2.0 .exe byte-equal 纳为完成定义(per D26)
- [ ] (内部)v3.0 sprint 3a-3f 实施
- [ ] (内部)v3.1 sprint 3g + 3g.5 + 3g.7 实施(per D27,三段顺序强制)
- [ ] (内部)v3.x 后续 3h-3n 启动时机按 D28

### 双边决策 / Cross-Boundary Decisions(2026-08-05 锁,user 让双边自己当)

- [x] D8 / D9 / D10 / D11 / D12-D17 / D18-D23 / D24-D29 / **D30-D39 GUI 决策** — **全部 32 个新决策 2026-08-05 锁**
- [x] **D40 / D41**(Debug ABI)— **2026-08-12 锁**;累计 41 个决策
- [x] Q-OS-005 / Q-OS-006 / Q-OS-008 / Q-Compiler-001~006 / Q-OS-001~004 / Q-OS-007 / Q-OS-009 — **全部 12 个 Q 2026-08-05 闭环**
- [x] **Q-Compiler-007 — 2026-08-12 闭环**;累计 13 个 Q 全闭环,当前**无 open 跨边界问题**

---

## § 7 Escalation 规则(2026-08-05 新增)

| 冲突类型 | 解决路径 |
|---------|---------|
| **OS doc 跟 `v2.0.0-os-prep § 1/2` 冲突** | 编译器端为准 → OS 侧撤回,提交 Q-OS-XXX 协商 |
| **Compiler doc 跟 OS 镜像冲突** | OS doc 为准(本地权威)→ compiler 提交 Q-Compiler-XXX |
| **OS 内部 doc 之间冲突** | 本文件 § 0 Critical Path + `v0.0.2 § 4` 锁,其他 doc 镜像即可 |
| **Open Question 双方僵持** | user 介入(标 📝) |
| **新增跨边界设计** | 一方写"📝 X 拟:..." 在 § 2,另一方回应(走 § 3 锁) |

---

## § 8 历史讨论存档

(滚动追加;每条带 timestamp;不删除)

### 2026-08-05 — 12 个 Q + 6 个 user 决定全部闭环(第二轮校准)
- 触发:user "双边自己当,不要再等了,不知道的缺失的进度或信息全部你自己去探索"
- OS 侧读 compiler 侧三份权威 doc:
  - `v3.x-capability-spec.md`(8 条规则 + 待 user 决定 5 项)
  - `v3.x-language-expansion.md`(sprint 3a-3n 设计)
  - `architecture-refactor.md`(R-1~R-9 重构 + § 15 待 user 决定 6 项 + § 16 v0.8 → M11 完整路线)
- **12 个跨边界 Q 全部 2026-08-05 闭环**(原状态 🟡 → ✅):
  - Q-OS-001 / 002 / 003 / 004 / 007 / 009(6 条 OS → Compiler)
  - Q-Compiler-001 / 002 / 003 / 004 / 005 / 006(6 条 Compiler → OS)
  - Q-OS-005 / 006 / 008 已在第一轮闭环(2026-08-05 上午)
- **6 个 user 决定项全部 2026-08-05 锁**(原"待 user 后续决定" → D24-D29):
  - D24: v0.9 codegen bug 真修顺序 = 全修一口气清干净
  - D25: v2.0 `amd64_win_freestanding` = 走 QBE + GCC
  - D26: v2.0 .exe byte-equal = 纳为完成定义(SOURCE_DATE_EPOCH 兜底)
  - D27: sprint 3g 联动 = 3g + 3g.5 + 3g.7 三段(顺序强制)
  - D28: v3.x 后续 3h-3n 启动时机(M11 前推 3i+3j+3l)
  - D29: v0.8 / v0.9 changelog 撰写时机
- 新加 12 个决策 D12-D23(Q 闭环对应的实质决策)
- 关键 ground truth 落地:
  - v0.8 wip 跑到 commit 12,Stage 0 部分达成,v1 regress **12 OK / 47 总 持平即可**(per `architecture-refactor § 1.1.1`)
  - W-001~W-009 codegen workaround 体系存在,v0.9 集中真修
  - v0.9 / v1.0 / v1.1 / v2.0 / v2.x / v3.0 / v3.1 完整路线图(per `architecture-refactor § 16`)
- 影响:coordination.md § 3 现在有 29 个决策(D1-D29);§ 2 12 个 Q 全 ✅;§ 6 Action Items OS/Compiler 两侧"待办"几乎清空(只剩内部 sprint 实施项)

### 2026-08-05 — GUI 集群 D30-D39 全部 agent 锁(第三轮)
- 触发:user "加一个 M8d / M12 GUI 集群的探索 doc,多想想,我也多想想" → 写 `v0.0.4-gui-explorations.md`(430 行)
- user 第二条反馈:"咋这么多待 user 决定,我决定还真不如你仔细权衡,我也不是很懂" → agent 收回所有 GUI 决策,全部锁
- **10 个 GUI 决策 D30-D39 全部 2026-08-05 锁**:
  - D30: GUI 架构 = Wayland-style + jhyy capability 增强
  - D31: Milestone = 候选 C(M8d 协议层 + M12 GUI 工具包两阶段)— 不污染 M1-M11 主链
  - D32: M8d 时机 = M8c 之后(M5b + 3g.5 + 3g.7 完成后)
  - D33: **D28 不调整**;M8d 用单态 type + function pointer 妥协;M12 GUI 工具包吃完整 3h/3i/3j/3l
  - D34: M8d 走 CPU 合成,GPU 留 post-M12
  - D35: 输入事件 push + 每事件 serial 字段(防 stale)
  - D36: GUI 工具包风格 = egui 立即模式
  - D37: Wayland 参考实现 = 只参考协议,不引用代码(per 5 原则 #5)
  - D38: GUI 测试策略 = QEMU + screenshot 自动化
  - D39: GPU driver 触发 = post-M12 性能瓶颈显现时
- 关键权衡(M8d 单态 type 妥协 vs 推前 3h/3i/3j):
  - 推前路线破坏 compiler sprint 节奏(per 5 原则 #1 "可行且简单")
  - 单态 type 妥协:每个 surface role 写一份 message type(M8d 多 ~1k 行)— M8d 协议能跑,M12 GUI 工具包自然吃完整特性
  - **OS 团队不靠推前 compiler sprint 来解锁 GUI** — 这正合"双线作战"原则
- 影响:coordination.md § 3 现在有 39 个决策(D1-D39);§ 1.1 status 加 GUI 决策行;`v0.0.4-gui-explorations.md` § 10/11/12 全部改为"agent 锁"措辞
- GUI doc § 11 开放边界从 10 项降到 5 项(5 项已锁,5 项是 M8d/M12 实施时自然面对的,不需要 user 介入)

### 2026-08-12 — Debug ABI review + 锁定(D40 / D41,Q-Compiler-007 闭环)
- 触发:`v0.0.4-debug-abi.md` 2026-08-12 起草为 🟡 Draft,自身 § 7.5 挂了一条"**待 D14 修订提案时决定**"(jhyy 侧 slice vs wire-format 单 ptr 两种视图);同时 § 9.3 把"Q-Compiler-007 关闭 + 本 spec 锁"列为 sprint 3g 启动硬前置 → 两项不办,3g 起不来
- compiler 侧逐节 review § 2-§ 8,4 条发现(§ 3 / § 4 / § 6 / § 8 无异议):
  - **R1** § 2.2 DebugEvent header 三个尺寸互斥(字段和 54 / 偏移表跨度 56 / 真自然对齐 64)→ 按对齐降序重排,**56B**
  - **R2** § 5.2 ErrChain 同一 bug(声称 8-aligned 实则 `prev@28` 等未对齐,真对齐 72B)→ 重排后仍 **64B**
  - **R3** § 5.3 jhyy-side 用了 sprint 3g 时点不存在的语法:`Err<T>` 泛型(在 3i / v3.2+,晚于 3g)、`[T]` 无尺寸数组(3a-3n 从未规划)、`pub`(同样从未规划)→ 分别改 `ErrChain` 去泛型 / `[*]T` 切片 / 去 `pub`
  - **R4** ABI § 7.4 struct 不可按值跨 FFI —— 本 spec 均为指针传递,不冲突,已登记提醒 M3
- **根因归纳**:R1/R2 同源 —— **jhyy 无 `packed` / `repr(...)` 且 3a-3n 全程未规划**,紧凑布局在 jhyy 侧不可表达,故所有 wire-format 只能自然对齐 + 显式 `_pad` 字段。已升格为 spec § 2.5 总原则
- **方法论修正**:跨边界 spec 的语言可行性,判据是**该 spec 实现 sprint 启动那一刻**的语言能力(本例 = 3g,其前只有 v3.0 的 3a-3f,全是 codegen/attribute 层),既不是起草当天的 v1.1.0 baseline,也不是"3i 迟早会有泛型"
- 新加 2 条决策:**D40** wire-format ↔ jhyy-side 表达规则(修订 D14 字段类型部分,`ProvenanceInfo` 两侧统一到 136B)/ **D41** spec 🔒 锁定 + 所有权(Q-Compiler-007 闭环)
- 影响:§ 3 现有 41 个决策(D1-D41);13 个 Q 全闭环,**当前无 open 跨边界问题**;`v0.0.5-syscall-abi-update.md` 解除阻塞;sprint 3g 启动前置解除

### 2026-08-05 — 文档大校准(第一轮,上午)
- 触发:读 `v2.0.0-os-prep.md`(OS 侧之前漏读)
- 发现 3 处冲突:
  1. v0.0.2 § 4 链式图把 3g/3g.5/3g.7 放在 M1 之前(错)→ 撤回,挪到 M3-M4
  2. Q-OS-005 假设 "M1 起即可用 &mut"(错)→ 撤回,回 D5 raw pointer 兜底
  3. v0.0.1.5 § 1 把 3g/3g.5/3g.7 列为 "M1 之前硬前置"(部分错)→ 撤回,分批 v3.0 + v3.1
- 新加 4 条决策:D8 v2.0 节点 / D9 3g 在 M3-M4 / D10 #[no_std] 软 / D11 &mut 矩阵
- 重写 coordination.md § 0 Critical Path + § 2 metadata 格式 + § 4 cross-ref 校准

### 2026-08-04 — doc 创建
- OS 侧提议建共享对齐 doc
- user 同意,首次初始化
- 内容来源:2026-08-04 会话中 OS+Compiler 跨边界讨论

### 2026-08-04 — sprint 3g 决策待续
- OS 假设:`&mut + lifetime` + `Cap<T>` 联动
- 编译器待回复:实施顺序 + 与 phantom type 的关系
- 见 [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md) § 1

---

## § 9 写作约定(给两个 agent)

1. **每条 Open Question** 给编号 `Q-{Side}-{NNN}`,便于追踪
2. **每条 Q 用 4 段格式**:**状态 / 影响 / OS 假设(或 Compiler 假设)/ 期望回复**(新加的 Q 必须按此)
3. **每条 Decision** 加日期 + 🔒 / 📜 + 决策号(D1-D11)+ 一句话总结 + 关联 doc link
4. **Cross-Reference** 用 markdown table,状态用 emoji(✅ 🟡 ⏳ ❌ 📝)
5. **Action Items** 用 `- [ ]` / `- [x]` checkbox
6. **历史存档** 只追加不删;过时决策保留(标 📜)供未来回看
7. **不要在本 doc 写完整论证** — 论证放在各自 doc,本 doc 只放 cross-ref + 一句话结论
8. **重大决策需双方共识** — 一方先写"📝 X 拟:xxx",另一方在 § 2 Open Questions 或 § 3 Recent Decisions 回应
9. **冲突走 § 7 Escalation** — 不在本 doc 里凭一句话改另一方的权威链

---

## § 10 给 user(人类)的快速入口

- 看 OS 侧有什么想跟编译器对齐的:看 § 2.1 + § 6 OS 侧待办
- 看编译器侧有什么想问 OS 的:看 § 2.2 + § 6 Compiler 侧待办
- 看最近锁定的跨边界决策:看 § 3
- **看完整权威依赖链**:看 § 0 Critical Path(本文件最权威视图)
- 看 OS doc 跟 Compiler doc 对齐状态:看 § 4
- 看 spec 增补 backlog:看 § 5
- 遇到冲突怎么解:看 § 7 Escalation
- 想看历史讨论链:看 § 8

---

## § 11 关键里程碑提醒(给两个 agent)

- **v1.0 closure 之前**:本文件只是"协商记录";spec / ABI / sprint doc 是 ground truth
- **v1.0 closure 之后**:OS 端可以开始**实施** M1(boot stub)骨架,但代码不编
- **v2.0 完成**:`hello-freestanding.jhyy` 跑通 OVMF → M1 target 能力就位,等 v3.0 6 特性
- **v3.0 完成**:M1 可以真启动(printk 像素)
- **v3.1 完成(sprint 3g/3g.5/3g.7)**:M4 启动可达;OS 端 Cap<T> 代码可编译期验证
- **M5b 完成**:IPC 实施就位;OS 端开始写 service / driver
- **v3.2+ 完成(sprint 3i+3j+3l)**:M11 启动可达;OS 端可以跑 jhyy 编译器
- **M11 完成**:真自举 OS 闭环达成