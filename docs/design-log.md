# jhyy_OS 设计日志

**目的**: 记录从 v0.0.0 到 v0.0.1 完整设计链路 — 所有头脑风暴、亮点、思考链路、一步步的确定流程。
**日期范围**: 2026-08-03 ~ 2026-08-04

---

## § 1. 项目启动(v0.0.0)

### 1.1 启动动机

 2026-08-03 用户宣布: jhyy_OS 进入正式设计阶段。从"一直在脑海中"到"今天正式着手 v0.0.0 → v0.0.1"。

### 1.2 仓库布局决策

- 路径: `C:\Users\liuzhen\Desktop\coding\jhyy_OS`(独立 repo, 不放 `compiler/os/`)
- git: 暂不开(用户明确"不着急")
- v0.0.0 内容: 纯设计 doc, 0 行代码
- OS 源码语言: 纯 jhyy

### 1.3 三原则(锁,作为所有决策过滤器)

1. **可行且简单** ——任何决策先用"两个人能在 v0.x 阶段 hold 住"的尺子量
2. **双线作战是核心优势** ——jhyy 和 jhyy_OS 互相喂养, 反馈循环 = 周级
3. **项目初期寄生 Windows** ——开发 / 构建 / 调试在 Windows 上;OS 运行时脱离 Windows

### 1.4 技术候选筛选

**DROP**:
- CHERI / seL4 验证 / region-affine types → 不够成熟 / 不够简单
- eBPF / Wasm-as-userland / Wasm-in-kernel → 不喂养 jhyy 语言

**保留**:
- 同步 syscall + tokio-style 语言 async → 简单
- v3.x P0 OS 特性 → 典范案例(语言特性来自 OS 需求)

---

## § 2. "纯 jhyy from day 1" 精确语义

### 2.1 误读 + 纠正

我最初把"纯 jhyy from day 1"理解为"OS 源码语言 = JHYY"。
用户纠正: **bootstrap 路径必须用自举后的 jhyy_v_N**(不是 C 版 jhyy.exe)。

### 2.2 为什么 C 版 jhyy.exe 编不出 jhyy_OS

- 缺全部 6 个 P0 OS-required 特性: `inline asm / naked / volatile / no_std / link_section / memory barrier`
- C 版是阶段产物, 自举完成后冻结
- 用 C 版编 OS = 维护成本加倍, 自举白搞

### 2.3 时间线(用户给定)

```
v0.8 wip (现在) → v1.0 closure → v2.x N 代 fixed point → v3.x P0 (6 特) → jhyy_OS v0.1+ 真编
```

### 2.4 jhyy_OS repo 当前能做的

- 架构 / ISA / 内存模型 / syscall ABI / bootloader 设计(不依赖编译器现状)
- v0.0.0 阶段 = 纯设计

---

## § 3. 架构决策: 微内核 + amd64 + UEFI + capability

### 3.1 我的头脑风暴提议

3 套候选方案, 含商用 OS / 学术 OS / 自研简化版本。

### 3.2 用户的"务实直觉"

用户提议: **实用微内核 + amd64 only + UEFI only**, 长线加 riscv64。

详细:
- 微内核(seL4 / QNX / Minix 风格) + 用户态 driver
- amd64 only v0.x, riscv64 at v0.5+
- UEFI only 引导链
- capability-based 安全模型(从第一天起)
- 11 milestones M1-M11(Hello → 微内核特性 → SMP → riscv64)

### 3.3 故意不做清单

- ❌ POSIX 兼容
- ❌ formal verification
- ❌ aarch64 v0.x
- ❌ GPU driver
- ❌ SMP v0.x

### 3.4 3 个核心张力(用户列)

[保留张力, 后续 sprint 解决]

---

## § 4. async 战略 v1 → v2

### 4.1 v1: 用户给 7 条修正

我最初头脑风暴 async 在语言里的位置, 用户给 7 条修正:

1. Effect escape hatch: 留 algebraic effects 作为未来 escape hatch
2. C 类解耦: 编译器 async 跟语言 async 解耦(bootstrap chicken-and-egg)
3. 显式 frame size: async fn 强制显式 frame size(对齐 jhyy 哲学)
4. io_uring-style ABI: 自己定义 completion-event syscall ABI, 不照搬 Linux
5. async-in-trait day-1 解法: 起步 static only, "async dyn" 留 escape hatch
6. Send/Sync 借 Rust: 业界熟悉, 命名一致
7. 不统一 Result 和 Future: 取消传染 ≠ 错误传染

### 4.2 7 铁律

| # | 规则 |
|---|------|
| 1 | async fn = 显式 state machine |
| 2 | 显式 frame size(默认 1 KB)|
| 3 | 取消 = Drop future + guaranteed cleanup |
| 4 | 编译器内部 sync forever |
| 5 | async-in-trait = static dispatch only |
| 6 | Send/Sync = Rust 同名 marker trait |
| 7 | 不统一 Result + Future |

### 4.3 A-only vs A+B 大分歧

**用户立场(A-only)**: jhyy 只承诺 A 类(kernel), B/C 是副作用。
- A = 差异化, jhyy_OS 强绑定, 核心承诺
- B = 用现有库替代, jhyy 不正面竞争
- C = 编译器实现细节, 不污染语言设计

**我的反论(A+B)**: 即使 OS-focused, jhyy 也需要 B 类, 4 个论证:
1. **OS 边界模糊**: shell / init / build tools / debuggers 是 OS 旗舰展示程序
2. **B 不必是 Rust 复杂度**: Rust 陷阱 = A+B+C, 减 C 即可不减 B
3. **生态决定命运**: seL4 反例 vs Linux 正例, userland 是平台必要条件
4. **Async 是 OS-required 相邻领域**: no_std 和 link_section 跟 async runtime 高度相关

### 4.4 v2: 用户让步

用户在 v2 让步, 接受 A+B, 4 个论证:
1. OS 边界模糊
2. B 不需要 tokio 复杂度
3. 生态决定命运
4. P0 跟 async 相邻

**关键洞察**: "减 B" 是错的, 正解是 "减 C"。bootstrap chicken-and-egg 论证 → C 必须解耦 → 解耦就足够避 Rust 陷阱 → 不必再牺牲 B。

### 4.5 3-tier 模型 + 5 条 B 锁

用户锁 B 锁死的 5 条:
1. runtime ≤ 500 行 jhyy
2. frame 默认 8 KB(A 是 1 KB)
3. 取消协议跟 A 共享
4. async-in-trait = static only
5. runtime opt-in

### 4.6 C 类永不入 spec

用户不让覆盖: C 类永不入 spec(rustc 编译器内部至今不用 Rust async, 这是有意识的选择)。

### 4.7 v0.1.x 子里程碑

async spec 起草推迟到 v0.1.2 决策点 + 反馈。

### 4.8 core vs std 决策: Option C

我拍板: `core::async_types` + `std::async_runtime`。

理由: core 哲学是零依赖, runtime 隐含 thread / 调度器假设, 放 core 张力大。类型部分放 core, runtime 部分放 std。跟 Rust 实际 split 最接近。

---

## § 5. v0.0.1 三章联动 design doc 框架

### 5.1 触发: 我的 3 反驳 + 2 观察

我提的 3 反驳:
1. M5 IPC 拆分: M5a 应该锁 6 件事(我加进程 / 线程模型)
2. 9P 推后: M7 用自研最简协议 + Cap 类型化
3. M8 拆分: M8a 用 UEFI 早期捷径

我提的 2 观察:
1. 5 个未知数(我数到 7) + 耦合分析
2. Cap 是差异化

### 5.2 用户扩展 6 项

1. M5a 三章联动: syscall-abi / capability / process-model 三章一起锁 v0.0.1
2. 9P 6 op + 3 设计约束: Open/Read/Write/Close/Stat/List + Cap 类型化/VFS 可替换/flag 不承诺 POSIX
3. M8a UEFI 早期捷径: GOP framebuffer + SimpleTextInput(我加 post-boot flag)
4. 7 未知数耦合表: 主链 1→2→3→5 + 旁支 4/6/7
5. Cap spec 3 约束: phantom type + const fn → syscall + 只接 Cap 不接 u64
6. 3 章一起锁 v0.0.1

### 5.3 三章文件结构

```
jhyy_OS/docs/
├── v0.0.1-syscall-abi.md       # IPC + 进程模型 + 错误码 + endpoint 命名空间
├── v0.0.1-capability.md         # Cap 类型 + derive/grant/revoke + 编译器约束
├── v0.0.1-process-model.md      # 地址空间 + 线程 + namespace + COW fork
└── v0.0.1-design-index.md       # 三章交叉引用 + 跟 v0.0.0 关系
```

### 5.4 Cap spec 3 约束(草案)

```jhyy
type Cap<T> = struct { token: u64 }
type File = struct { _priv: () }
type Socket = struct { _priv: () }
```

- 约束 1: Cap = 不透明 token + phantom type
- 约束 2: capability 操作 = 语言级 const fn → syscall
- 约束 3: syscall 签名只接 Cap, 不接 u64

### 5.5 revocation propagation 扩展点

v0.0.1 简化: `revoke(c)` 只销毁 c 本身, 衍生 cap 不传播。
v0.0.x 后续: cnode / derivation tree + propagation。

### 5.6 M8a UEFI 早期捷径(我加 post-boot flag)

M8a = framebuffer persistent + boot-phase keyboard + UI lib。
**flag**: UEFI SimpleTextInput post-boot 失效(boot services 在 ExitBootServices 后消失)。

修正后范围:
- ✅ Framebuffer(persistent via MMIO)— post-boot 全程
- ✅ Boot-phase keyboard — boot menu + debug console
- ❌ Post-boot keyboard → M8b (PS/2 优先)

---

## § 6. 从编译器侧提的一个问题

### 6.1 用户切角色

用户让我"听听 jhyy_compiler 设计 agent 的想法"。我作为编译器侧 agent 给反馈。

### 6.2 我(OS 侧)抛给编译器侧的问题

OS 团队 v0.0.1 推到三章联动,卡在两个跨边界未知数上:

1. **C 端冻结时机**:v1.0 closure = C 版 jhyy.exe 冻结为"不再改"。那 v1.0 之后 v2.x N 代里,OS 团队能否用 C 版临时编早期 OS 原型?
2. **编译器侧维护路径**:C 端冻结后,自举闭环,bug 修复只能走 jhyy 端。这条风险 OS 团队需要看见。

回答见 § 6.3 / § 6.4。

### 6.3 C 端冻结时机

- v1.0 closure = C 端冻结
- v1.0 closure ≠ OS 可编(缺 6 P0)
- v2.x N 代 = C 端冻结 + jhyy 端成熟, OS 团队**只能**推 v0.0.x 设计 doc,**不能**用 C 端临时编 OS 原型(C 版 jhyy.exe 缺全部 6 P0,编不出 OS;跟 `docs/v0.0.0-design.md` § 6 C 端冻结时机一致)

### 6.4 加 1 条编译器特有风险

🟡 **C 端冻结后维护路径单边化**: 自举后修 bug 只能改 jhyy 端, 单边。

### 6.5 加 1 条 killer demo(真杀手锏)

**capability 端到端集成**:
- 编译器层 + 类型系统层 + syscall ABI 层 + kernel 层 全栈协同
- seL4 / Capsicum / CHERI 都做不到
- 只有自举语言能做到这种端到端集成

### 6.6 Q6: 编译器层约束清单

OS 团队 v0.0.1 capability spec 应明确"编译器层约束"一节:

- (a) 内建 `Cap<T>` 类型 — 语言层 vs std
- (b) 拒绝 `u64 as Cap<T>` 强转 — 类型系统层
- (c) 拒绝 non-Cap 参数 syscall — linter / 编译错误
- (d) `#[send] / #[sync]` trait — 类型系统层(v1.x 阶段可加)
- (e) 编译期 capability 派生树 / cnode 类型检查 — 类型系统层

### 6.7 OS 团队不依赖编译器现状

**关键观察**: v0.0.1 三章联动 doc 哪怕 OS 团队崩了, 这套设计本身就能进 paper / 学术报告(跟 Wirth 的 Oberon Reports 一样的角色)。

---

## § 7. 总结: v0.0.1 锁定状态

### 7.1 已锁

- 三原则(可行且简单 / 双线作战 / 寄生 Windows)
- 架构: 微内核 + amd64 + UEFI + capability
- 11 milestones
- async 战略 v2: A+B 共识 + 3-tier + 5 B 锁 + Option C
- v0.0.1 三章联动设计框架
- Cap spec 3 约束
- revocation propagation placeholder
- M8a post-boot flag
- 7 未知数耦合表(主链 1→2→3→5)

### 7.2 待 v0.0.1 完成

- syscall ABI 具体消息格式
- 错误码体系
- endpoint 命名空间(全局 vs per-process)
- 同步 RPC + 超时协议(绝对时间 vs 相对时间)
- capability 编译器层约束(OS team + compiler team 协作)
- 进程 / 线程模型细节(地址空间布局 + COW fork 语义)

### 7.3 待 v0.0.2+ 完成

- v0.1.0 kernel + sh.jhyy 跑通(sync 实现)
- v0.1.1 coreutils 跑通
- v0.1.2 B-tier async 决策点
- async spec 起草
- async feature 上线
- M1 真启动 OS = `jhyy_v_N 编 jhyy_OS`

---

## § 8. 2026-08-04 — v0.0.1 三章细化 + spec 校准

### 8.1 用户提的 5 个细节问题 + 2 个 framing 校准

**用户提的问题**(触发更深设计):
1. borrow checker 是否适合 jhyy_OS?
2. debug 反馈是否能"agent friendly"(想跑 Claude Code 在 OS 上)?
3. jhyy 本身能不能做这些(QBE / arena 限制)?
4. M11 自举需要编译器哪些特性?
5. MVP M11 看起来是什么样的?
6. 用户说"jhyy 是绕着你设计的"(jhyy 是 OS-driven)
7. 用户说"可以没有,只要不冲突都可以加"(缺 feature = 设计输入)

**5 个 framing 校准**:
- 可行且简单:✓/✗ only,no time estimates
- Debug by design(原则 4)
- Kernel 不解决语言问题(原则 5)
- jhyy 是 OS-driven,缺 feature = 设计输入
- 设计前先读 spec(feedback_consult_spec_first)

### 8.2 内存模型进化路径

| 阶段 | 想法 | 锁定结果 |
|------|------|---------|
| 1 | borrow checker primary | ❌ DROP |
| 2 | region types primary + linear cap + raw + unsafe_share | 🔒 锁 hybrid |
| 3 | 关键修正:arena 是 jhyy 编译器 native,borrow checker 多余 | feedback_consult_spec_first 教训 |

### 8.3 spec 阅读发现(我之前漏的)

读 `jhyy-lang-spec-v1.1.0` + `jhyy-abi-v1.0.0` + `v3.x-capability-spec` + `v3.x-language-expansion` 发现 5 处偏差:
- generics / closures / `&mut` / RAII 都未实现
- ABI 仅 amd64_win(无 ELF 后端)
- struct/enum 不能跨 FFI

→ 写 v0.0.2-foundation-revision.md spec 校准 + framing 校准 + M1-M11 依赖图

### 8.4 锁定的新内容

| 内容 | 落地 |
|------|------|
| **5 原则**(原 3 原则 + Debug in 语言 + Kernel 不解决语言问题)| [v0.0.0-design.md § 2](v0.0.0-design.md) |
| **Narrow Waivers**(99% 编译期 + 1% WaiverCap + Layered TCB)| [v0.0.1-capability.md § 4-6](v0.0.1-capability.md) |
| **Compile-time provenance** | [v0.0.1-capability.md § 5](v0.0.1-capability.md) |
| **Type-driven IPC** | [v0.0.1-syscall-abi.md § 1.1](v0.0.1-syscall-abi.md) |
| **类型化错误码 enum** | [v0.0.1-syscall-abi.md § 1.4](v0.0.1-syscall-abi.md) |
| **endpoint namespace = per-process cap ns** | [v0.0.1-syscall-abi.md § 1.5](v0.0.1-syscall-abi.md) |
| **boot 路径 = UEFI + PE/COFF**(改)| [v0.0.1-syscall-abi.md § 2](v0.0.1-syscall-abi.md) |
| **cap closure MVP(显式 discipline)** | [v0.0.1-process-model.md § 5](v0.0.1-process-model.md) |
| **hybrid 内存模型** | [v0.0.2-foundation-revision.md § 3.2](v0.0.2-foundation-revision.md) |
| **MVP coding style(无 generics/closures/&mut 折中)** | [v0.0.2-foundation-revision.md § 6](v0.0.2-foundation-revision.md) |
| **M5b 12 硬条件** | [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md) |

### 8.5 新建 doc

- [v0.0.2-foundation-revision.md](v0.0.2-foundation-revision.md) — spec 校准 + plan
- [v0.0.3-explorations.md](v0.0.3-explorations.md) — raw 头脑风暴存档(5 macro-strategies / 备选架构 / MVP 最小集)
- [v0.0.1.5-M5b-prereqs.md](v0.0.1.5-M5b-prereqs.md) — M5b 实施前置
- [coordination.md](coordination.md) — OS × compiler 跨边界对齐

### 8.6 highlights 升级

- 6 → 8 killer features
- 加 #7 Debug-by-design + #8 Layered TCB + Narrow Waivers

### 8.7 闭环概念澄清(user 反馈)

用户问"在 OS 上再拉一个 OS 有什么意义" — 我误解成"嵌套 OS"。澄清:
- 闭环 = OS 能 host 自己的工具链 + 能编译自己
- **不是**"在运行中启动新 OS 实例"
- M11 = jhyy_OS 跑 jhyy 编译器 + 编译器编 jhyy_OS(并行验证,**不是流水线**)

### 8.8 新增 durable memory

| memory | 类型 | 内容 |
|--------|------|------|
| `feedback_feasibility_focus` | feedback | ✓/✗ only,no time estimates |
| `project_ai_coding_speed` | project | AI coding 加速削弱时间估算价值 |
| `feedback_consult_spec_first` | feedback | 设计前先读 spec |
| `feedback_jhyy_extensible` | feedback | 缺 feature = 设计输入,不是 blocker |

---

## § 9. 总结:2026-08-04 锁定 vs 待办

### 9.1 已锁

(略,见 v0.0.1-design-index.md § 4)

### 9.2 待办(滚动)

- OS 团队:细化 sema 8 条规则 / Type-driven IPC sema 检查算法 / cap closure linter
- Compiler 团队:细化 sprint 3g 实施计划 / phantom type 0-byte 布局
- 跨边界问题:见 coordination.md § 2

### 9.3 待 v0.0.1 完成(从 § 7.2 升级)

- ~~syscall ABI 具体消息格式~~ → 已锁 Type-driven IPC
- ~~错误码体系~~ → 已锁类型化 enum
- ~~endpoint 命名空间~~ → 已锁 per-process cap ns
- ~~同步 RPC + 超时协议~~ → 已锁相对时间
- ~~capability 编译器层约束~~ → 已锁(sprint 3g / 3g.5 / 3g.7)
- ~~进程 / 线程模型细节~~ → 部分锁,实施细节 v0.1+
- (新增)内存模型细节 → 已锁 hybrid 框架,实施细节 v0.1+

### 9.4 待 v0.0.2+ 完成

(同 § 7.3)— v0.1.0 kernel + sh.jhyy + coreutils + async + M1-M11

---

## § 10. 2026-08-04 — UEFI x64 boot path spike 实测

### 10.1 触发

P0-1 ⚠️ 标注"待 spike 验"。在 v0.0.0/v0.0.2/v0.0.1-syscall-abi 三处都写了"real mode → protected mode → long mode 切换",需实证。

### 10.2 spike 设计

最小实验:`boot.s` 编成 PE/COFF EFI app(MS x64),OVMF boot。流程:
1. `pacman -S mingw-w64-x86_64-qemu mingw-w64-x86_64-mtools`(装 qemu 10.1.0 + OVMF + mtools)
2. `x86_64-w64-mingw32-gcc -nostdlib -Wl,--subsystem=10 -Wl,-e,efi_main` 编 `boot.s` → `BOOTX64.EFI`
3. `mkdir esp_root/EFI/BOOT; cp BOOTX64.EFI esp_root/EFI/BOOT/`
4. `qemu-system-x86_64 -drive if=pflash,format=raw,readonly=on,file=$OVMF -drive file=fat:rw:esp_root -device isa-debug-exit,iobase=0xf4,iosize=1`

`fat:目录` 比 `format=raw,file=disk.img`(GPT 包裹镜像)省事得多 —— 后者要自己写 MBR+GPT header+partition entries,踩了 entry LBA=35 错写成 2 等 bug。

### 10.3 踩过的坑(3 个)

| # | 错 | 对 | 验证方式 |
|---|----|----|---------|
| 1 | `mov r12, rcx`(当 ST) | `mov r12, rdx` | RCX=ImageHandle,RDX=SystemTable(UEFI x64 = MS x64) |
| 2 | `call [r13 + 8]` 没设 RCX=*This | `mov rcx, r13` 在 call 前 | ConOut->OutputString 是 EFIAPI=MS x64,第一参数走 RCX |
| 3 | LocateProtocol 偏移 `BootServices + 0x150` | (留待 v0.0.3 spike #2 验) | 不同 OVMF 版本字段顺序可能不同,simplified spike 没用到 LocateProtocol |

### 10.4 结果

```
BdsDxe: loading Boot0001 ...
BdsDxe: starting Boot0001 ...
HELLO
OK
[QEMU exit code 133 = (0x42 << 1) | 1 = isa-debug-exit got 'B']
```

✅ **P0-1 实测证实**:UEFI x64 固件交接时已经在 long mode,无模式切换。boot stub 几乎不需要 inline asm。
✅ **MS x64 调用约定**:`extern fn efi_main(ImageHandle, ST) -> Status`,RCX/RDX/... 自动传参,32-byte caller shadow space。

### 10.5 doc 同步

- v0.0.2 § 5.2:P0-1 ⚠️ → ✅ 验完,boot stub 需求重写
- v0.0.1-syscall-abi § 2.2:同样重写 + 加 UEFI 入口约定说明(RCX=ImageHandle,RDX=ST)
- memory:`feedback_uefi_x64_conventions.md`(新增)—— 把 4 条教训锁住

### 10.6 后续

- v0.0.3 spike #2:验 BootServices 偏移(AllocatePool / LocateProtocol / etc)— 不同 OVMF 版本会差
- v0.1+ 真启动 OS 时:UEFI stub + ExitBootServices + 自建页表 + 跳 kernel
- `#[naked]` 唯一用处:kernel interrupt handler(M5 之后)
- M1 真启动时:`extern fn efi_main(...)` 走 MS x64,jhyy 编译器只要支持 `extern fn` + 函数指针 + raw pointer load就够了