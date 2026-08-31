# jhyy_OS amd64 Syscall ABI 寄存器约定深度研究

## 摘要：RCX/R11 不可用于快速调用参数，jhyy 应定义独立的 syscall 边界 ABI

P0-3 的核心不是“如何把 `RCX` 让给硬件”，而是**用户态 MS x64、UEFI 函数调用与 `syscall` 指令边界必须分成三个互不覆盖的 ABI**。AMD/Intel `SYSCALL` 在从 IA32_STAR/LSTAR 装载 CS/RIP、按 IA32_FMASK 屏蔽 RFLAGS 之前，先将用户 RIP 写入 RCX、将旧 RFLAGS 写入 R11；因此 MS x64 将 RCX 用作第一个参数的事实，正好证明 jhyy 不能沿用到内核边界。[3][4] Linux 的实用解法是把原本属于 RCX 的位置移到 R10，并保持 RDI/RSI/RDX/R10/R8/R9 的参数顺序；项目所称“R10 顶替 RCX”即指这一编码位移，而不是把 `RAX=syscall#` 与 `RDI..R9` 整体前移。[2]

jhyy 的最佳方案不是继续把 header、消息、指针和超时塞进同一个“栈副本 + sret”布局，而是定义一套**定长、可校验、可与 type-driven IPC 双向映射的快速 ABI**：`RAX=service index`、`RDI=Cap<Endpoint>`、`RSI=msg_ptr`、`RDX=msg_size`、`R10=msg_tag`、`R8=timeout`、`R9=flags`；返回时 `RAX` 承载 reply header 或 `SysError`，`RDX` 承载 reply 指针。寄存器不足时不把参数溢出到用户栈，而应改用一个指向已校验描述符表的固定消息缓冲。上限 4 KiB 应视为“可随两个用户指针做一次 copy-in/out 的同步 payload”的工程上限，而非硬件常数；更大对象应经 `Cap<Shm>` 传递，并遵循先创建、后 attach、再 commit 的两阶段提交。

指针型返回值必须区分“由编译器生成的隐式 sret 槽”和“用户显式传递的 `out`/`inout` 指针”。前者属于调用帧，可由类型布局静态验证；后者跨越安全边界，必须执行地址空间归属、对齐、可写性、对象边界及访问阶段校验。由于 revoke、COW 与页表替换均可发生在检查与使用之间，单次检查后又直接解引用并不构成安全闭环。M3 必须采用“描述符 + 版本/epoch + 提交令牌 + 使用后失效”的方案，而不能依赖“校验一次即可长期缓存地址”的假设。

本文建议将 §1.1.3 的 P0-3 由“待 OS 团队拍板”升级为已锁设计，并将“header 寄存器、消息指针、4 KiB 快速上限、Cap<Shm> 降级、sret/out 指针分类、cap-offset 原地改写、TCB 字段及 DebugEvent 保存顺序”一并锁入新的 `v0.0.5-syscall-abi-registers.md`。[1] 该文档应直接纳入 v0.0.x 体系，而不只是停留在探索状态。

## 1. P0-3 的实质是 ABI 分层，而不是普通寄存器优化

jhyy 不能只有一个“amd64 调用约定”。MS x64 是 C/EFI 函数边界；UEFI 是固件提供的特定入口；`syscall` 是由 STAR/LSTAR、FMASK、CS/SS 选择子及返回指令共同定义的权限转换。三者恰好都在 64 位 x86 上运行，并不意味着它们可以共享同一套参数寄存器。

`v0.0.1-syscall-abi.md` §1.1.3 已准确指出：用户态可以按 MS x64 将 `RCX` 作为第一个整型参数，但 `syscall` 执行后会立即破坏 RCX 和 R11。[1] `v0.0.1-syscall-abi.md` §1.1.2 则规定 payload 由“消息类型大小 + 4 KiB 上限”控制；§1.1.4 进一步要求编译器按 `msg_tag` 查找 D16 cap-offset 表，由内核在 payload 内原地改写 `Cap<T>`。[1] 这两条要求共同决定了：syscall 边界不仅要编码参数，还必须编码“在哪里写回、哪些字节是 cap、如何回滚失败”。现有文档尚未定义 entry/exit 的寄存器所有权，也尚未定义用户指针从检查到使用的完整安全链条。

### 1.1 硬件事实决定了 RCX/R11 属于 entry/exit，而非参数编码

`SYSCALL` 的执行语义可以明确拆分为四步：保存返回控制流、保存调用状态、装载特权级执行环境，以及执行权限切换。用户态传入 RCX 的“第一个参数”在指令完成前就会消失，因此不能把它作为稳定参数位置。

1. `SYSCALL` 将下一指令线性地址，即用户返回 RIP，写入 RCX。
2. 将当前的 RFLAGS 写入 R11，并清除 RF 等受控位。
3. 根据 IA32_FMASK 屏蔽 RFLAGS，再装载 CS、SS 与 RIP。
4. 完成从用户特权级向内核特权级的切换。

SYSRET 是这一过程的逆过程：它从 RCX 恢复 RIP，从 R11 恢复 RFLAGS。这意味着 entry 汇编在调用 C/kernel 处理程序之前，必须完整保存 RCX、R11 及全部被毁寄存器；exit 路径在 `SYSRETQ` 前则必须恢复“用户观察到的”RCX、R11 和 volatile 寄存器。即使某个调用没有明确使用返回值，也不能让 RCX/R11 停留在内核中间状态。

Linux 上游 `entry_64.S` 的入口注释提供了直接、可核验的实现证据：

> “64-bit SYSCALL saves rip to rcx … saves rflags to r11 … Registers on entry: rax system call number; rcx return address; r11 saved rflags … rdi arg0; rsi arg1; rdx arg2; r10 arg3 … r8 arg4; r9 arg5.”[2]

该实现事实不能替代厂商手册：Intel SDM Vol.2 的 SYSCALL/SYSRET 章节与 AMD APM Vol.3 才是语义 ground truth，Intel 官方手册目录则用于定位相应 Volume 2 指令条目。[3][4] 但现有证据足以得出工程结论：**R10 替代的是 RCX 在参数序列中的位置，而不是“第一个参数原本放在 RCX”这一调用惯例可以原样保留。**

![SYSCALL/SYSRET 的状态与寄存器所有权边界](/data/workspace/dr:2026082601/fig_1_syscall_state.png)

*图 1：SYSCALL 执行前、执行中、内核 entry 及 SYSRET 恢复之间的寄存器所有权边界。来源：Linux `arch/x86/entry/entry_64.S` SYSCALL64 注释 [2]；AMD APM Vol.3 / Intel SDM Vol.2 [3][4]。*

### 1.2 R10、R11、SSE 与 selector 分别解决不同问题

“使用 R10”只是参数编码问题。R11 属于 entry/exit 状态，SSE/XMM 属于上下文完整性，STAR/LSTAR/FMASK 与段选择子则属于机器配置；它们不能混成一个“寄存器分配问题”。

- **R10**：位于 C 调用序列中 RCX 原本对应的参数位置。使用它可以避免与 MS x64 第一个参数发生编码冲突。
- **R11**：在内核执行期间临时保存 RFLAGS，不能用作稳定输入或输出。
- **SSE/XMM**：必须在 entry 中整体保存，在 exit 中恢复，或明确保留在用户态，避免浮点状态泄漏并减少上下文切换风险。
- **STAR/LSTAR/FMASK**：内核启动时配置。64 位 SYSCALL 通常经 IA32_LSTAR 进入内核；FMASK 决定进入时清空的 RFLAGS 位。
- **Selector/CS/SS**：SYSRET 的恢复路径必须与 entry 配置相匹配，具体语义需依据厂商手册及实测结果收敛。

若采用“R11 = 临时 RFLAGS，RCX = 返回地址”的紧凑 frame，SYSRET 可直接交换恢复；若采用“先构造完整 trap frame”的方案，RCX/R11 也应先落入 TCB，exit 再从 TCB 恢复。两种方式在正确性上等价，差别在于 M2 cooperative scheduler 是否复用同一 `SavedRegs`。现有 `v0.0.1-process-model.md` §2.1 只写了抽象的 `saved_regs: SavedRegs`，尚未规定字段位宽与排序，因此现在就是锁定布局的最后窗口。[6]

## 2. 行业方案共同支持“参数与硬件暂存位分离”

各内核在 amd64 上的差异主要体现在参数编码、IPC 寄存器压力、返回值与错误表示方式，而非是否回避 RCX/R11。它们共同证明：硬件破坏的寄存器必须排除出稳定参数集；jhyy 应借鉴的是分层原则，而不是复制某个既有编号方案。

| 方案 | 编号、参数与返回约定 | capability / 消息关系 | 对 jhyy 的有效启示 | 不宜直接复制之处 |
|---|---|---|---|---|
| **Linux x86-64** | `RAX=syscall#`；`RDI/RSI/RDX/R10/R8/R9`；返回值 RAX；额外结果可经指针写回 | VDSO、文件描述符与 `copy_to_user/copy_from_user`；access_ok、SMAP、页表隔离 | R10 位移、struct 返回值经用户指针、copy 路径原子化 | 文件描述符不是 capability；错误码全局化、POSIX 语义过重 |
| **FreeBSD amd64** | 传统 int 0x80 编号；参数寄存器与 Linux 不同，但入口均避开 RCX/R11 | 内核 trap frame 保存 RCX/R11 | syscall 号、参数与 trap frame 分离 | jhyy 不需要 BSD 兼容层 |
| **OpenBSD amd64** | 用户参数多按 `RDI/RSI/RDX/RCX/R8/R9` 进入 C；entry 需保存硬件暂存位 | 安全加固与只读映射、页表策略 | 硬件 RCX 不能等同于用户 arg0 | jhyy 不应照搬其 syscall 号空间 |
| **DragonFlyBSD** | `movq %rcx,TF_RIP(%rsp)` 且注释“rcx original value is in %r10”；同时保存 R11 | trap frame 字段完整 | 进入 C 前先保存 RIP/RFLAGS，再重排参数 | jhyy 是否复用 TCB 偏移仍需自行锁定 |
| **seL4 amd64** | 快速路径寄存器参数；badge、capability 指针及 reply 对象占用有限寄存器 | IPC 消息寄存器、cap transfer、fastpath/慢速路径 | cap-offset 与原地改写；寄存器压力按服务分类 | jhyy 服务集更小，无需复制 seL4 多 MR 模型 |
| **Genode/NOVA、Fiasco.OC** | 微内核 IPC 将 capability 选择子、消息字、映射项分通道传递 | 能力、端口、页映射与短消息优化 | 按消息大小与 capability 数量分层 | 具体超空间、UTCB 布局属于各自实现 |
| **Windows x64 NT** | 用户态 RCX/RDX/R8/R9 + 栈；NT service 另有编号与参数块 | 句柄近似 capability，但并非不可伪造 token | 明确区分“用户 C ABI”与“syscall 编码” | jhyy 不应在 syscall 边界继承 RCX 首参 |
| **x86-64 System V** | psABI 主要规定用户函数调用；内核边界通常由具体 OS 定义 | RFLAGS、errno 等不属于标准跨内核 ABI | psABI 不是“唯一合法 syscall 表” | 不能把 System V 用户调用约定误作硬件要求 |

### 2.1 Linux 证明 R10 位移可行，但不构成 jhyy 的规范约束

Linux 采用 R10 是事实，不是对 jhyy 的硬约束。真正可迁移的是两条原则：硬件破坏的寄存器不得承载参数；编号、输入、输出与暂存状态必须分开编码。

Linux 从 System V 用户调用约定出发，将 R10 插入 RDX 之后的参数序列，从而避免 RCX/R11 冲突。超过六字的参数不再简单溢出到用户栈，而是通过用户指针、iovec、struct 或其他明确参数块传递。`struct` 返回值通常由调用方提供缓冲区，内核执行 copy-to-user；`access_ok` 与 SMAP 构成“范围检查 + 访问屏障”的双重防护。

jhyy 可以借鉴这一分层，但不能因此引入 errno 全局状态或 FD 模型。`v0.0.1-syscall-abi.md` §1.4 已经锁定强类型 `SysError`；`ErrChain` 与 DebugEvent 也应作为调试辅助传递，而不是改变普通返回值的 ABI。[1][10]

### 2.2 BSD 的共同点是先保存硬件状态，再进入 C 语义

FreeBSD、OpenBSD 与 DragonFlyBSD 的具体参数顺序虽有差异，但都要求 entry 在 C 语义开始之前保存 RIP、RFLAGS 及完整 trap frame。

DragonFlyBSD 的 `movq %rcx,TF_RIP(%rsp)`、`movq %r11,TF_RFLAGS(%rsp)`，以及“rcx original value is in %r10”是尤其直接的证据。[5] 对 jhyy 而言，这意味着 TCB 字段应按固定偏移组织，而不是依赖编译期生成的任意结构顺序。`v0.0.1-process-model.md` §2.1 中的 `SavedRegs` 应至少规定：

- `RAX..R11`；
- `RBX/RBP/R12..R15`；
- `RSP/RIP`；
- `RFLAGS`；
- `XMM0..XMM5`；
- 段或 selector 字段；
- 内核栈与线程状态。

字段偏移应同时覆盖 M2 cooperative switch 与 syscall entry/exit。若同一布局不能同时服务于两者，后续嵌套、中断及 SMP 迁移会强制破坏 ABI。

### 2.3 seL4 的价值是区分 hot/cold 路径，而不是复制 capability 编码

seL4 的快速 IPC 将“端点/能力查找 + 短消息拷贝”与“需要映射、授予或慢速唤醒”的路径分开。寄存器数量有限，因此 capability 选择子、消息字、badge 与 reply 对象都会迅速占满可用位置。

jhyy 服务集更小，cap 又是 8 字节 phantom 类型，内核只做 cnode 检查及原地改写，因此无需复制 seL4 的多 MR 模型。合理的映射是：

- `RDI=endpoint cap`；
- `msg_tag` 指向 D16 cap-offset；
- 热路径携带 4 KiB 以内连续 payload；
- grant、revoke 与 attach 使用明确的窄操作；
- 冷路径采用 `Cap<Shm>` 引用。

这种分层可以保留快速 RPC，同时避免用隐式全局或栈接力传递 capability。具体 seL4 fastpath 性能数字不在本次可读手册范围内，相关比例标注为“需实测”，不应据此制作性能图表。

### 2.4 Windows 只能证明“用户态 RCX 首参可行”，不能证明它可用于 syscall

Microsoft 官方文档规定，Windows x64 的前四个整型参数依次位于 `RCX/RDX/R8/R9`，其余参数按右到左顺序入栈；RAX/RCX/RDX/R8/R9/R10/R11 等属于易失寄存器。[7]

这组事实恰好说明 jhyy 用户态可以采用 MS x64，也解释了为什么 UEFI `efi_main(ImageHandle, SystemTable)` 使用 RCX/RDX。`v0.0.1-syscall-abi.md` §2 已经记录这一约定。[1] 但 Windows NT 的系统服务编号、参数块与返回约定是另一套内核接口。因此 jhyy 的正确结构应为：

- 用户态与 UEFI：`amd64_win`，即 MS x64；
- 编译器生成的 IPC 封装：普通函数调用；
- 封装尾部：重排为 syscall ABI；
- `syscall` 指令边界：独立约定。

在三个层面之间插入一层薄封装，既保留 Windows 工具链，又避免“用户态调用图突然按 RDI/RSI 编码”的全局破坏。

## 3. jhyy 应选择“header-in-register、payload-by-pointer、hot/cold 分层”

R10 方案不仅可行，而且应作为推荐锁定项。真正需要避免的不是 RCX 或 R10 二选一，而是让 header、payload、capability、超时、返回状态及调试上下文相互争夺固定寄存器。

推荐的编码如下：

| 方向 | 寄存器 | 语义 |
|---|---|---|
| in | RAX | service index，低 32 位有效 |
| in | RDI | `Cap<Endpoint>`；同时承载 namespace + rights 检查 |
| in | RSI | 指向用户消息的指针；不得解引用至普通用户缓冲 |
| in | RDX | `msg_size`；0..=4096 |
| in | R10 | `msg_tag`；索引 D16 metadata 与 cap-offset 表 |
| in | R8 | timeout 低 64 位；具体编码待定义 |
| in | R9 | flags/reserved；bit0 = has_large；bit1 = debug_context |
| out | RAX | reply header，或 `SysError`；非零错误编码策略待锁 |
| out | RDX | reply msg ptr；或 sret 状态 |
| clobber | RCX | 返回 RIP，用户不得输入 |
| clobber | R11 | 旧 RFLAGS，用户不得输入 |
| preserve | RBX/RBP/R12-R15 | TCB、地址空间游标及 reply 状态 |
| preserve | XMM | 按调用约定保存，或由 entry 明确处理 |

![jhyy amd64 快速 syscall ABI 的寄存器角色](/data/workspace/dr:2026082601/fig_2_register_budget.png)

*图 2：推荐快速 ABI 的 11 个固定角色。数据来源：本 design doc §4；硬件冲突由 Linux `entry_64.S` [2] 及 APM/SDM [3][4] 核对。*

### 3.1 使用 R10 的成本低于任何“前移”或双编码方案

**推荐方案（🔒 建议升级）：`arg0=RDI, arg1=RSI, arg2=RDX, arg3=R10, arg4=R8, arg5=R9`。**

这一定义明确、可与现有 4 KiB payload 边界衔接，并使 entry 汇编易于审查。Linux 已经采用相同位移；jhyy 只需声明自己的 service index、header 字段与 metadata 规则。[2]

其他方案均引入更高复杂度：

- **arg1 移回 RDX，整体前移**：可以避开 RCX，但会把 endpoint capability 从自然的第一个参数移开，并使消息长度、超时及 cap 参数连续块更难拆分。
- **RAX + RDI..R11 全部用于标量**：会占用 R11，破坏与 SYSRET 的对应关系，并迫使 entry 增加临时位置。
- **header 分散到栈或 magic 区域**：无法减少寄存器压力，还会引入用户态栈解析、TOCTOU 及“syscall 是否允许访问用户栈”的额外问题。
- **超过 4 KiB 时自动溢出到用户栈**：直接违反“4 KiB 内可一次 copy-in/out”的设计初衷。
- **按 MS x64 继续把 RCX 作为 arg1**：硬件会在 `SYSCALL` 执行时覆盖该参数，并随后把用户 RIP 错误恢复。这是必须排除的方案。

jhyy 已有“单态化、无泛型、无 RAII”的约束。[8] 固定 7 输入 + 2 输出的编码可以覆盖 4 KiB payload、64 位超时、flags 及 SHM 降级，无需引入运行时变长寄存器列表。

### 3.2 4 KiB 是接口上限，不是安全边界

4 KiB 足够容纳大多数控制消息、cap 批处理及小型 reply，并使单次 copy-in/copy-out 保持可审计；但它不是由 `syscall` 指令本身决定的常数。将其称为“v0.0.x 工程上限”，可以保留后续调整空间。

推荐规则如下：

- `msg_size <= 4096 - header_size` 时，payload 位于 `[RSI, RSI+msg_size)`。
- 若 `flags.has_large`：`RSI` 指向一个固定 32 字节描述符，而不是完整对象。
  - 描述符至少包含：`Cap<Shm>`、offset、length、dirty bitmap 指针、generation。
- `msg_tag` 决定是否存在 D16 cap-offset 段及 reply 模式；cap 字段由编译器从消息类型推导，不由运行时解析。
- 若 `R8` 携带超时，则采用明确的 128 位 `timeout` 编码；现阶段先保留 R8 并禁止高 64 位非零。

大对象经 `Cap<Shm>` 传递，而非把完整对象复制到 payload，具有以下语义优势：

- 调用方拥有 source-of-truth；
- 内核只映射必要的页区间；
- 写回范围可由长度与 bitmap 表达；
- copy-in/copy-out 与 zero-copy 可共用权限规则。

这一设计满足“地址空间校验主要在类型/编译器，内核做兜底”的原则。`Cap<Shm>` 的类型、对齐、生命周期及 grant 权限在 L1 由编译器约束；内核只在 L3 验证 cnode、rights、生成号与区间。它没有把内核变成“通用语言运行时”。

## 4. 安全闭环取决于校验对象，而不是校验次数

单次 `access_ok` 无法消除 TOCTOU。jhyy 应校验“描述符、epoch、区间与访问阶段”的组合，并在写回后使提交令牌失效；内核负责 fail-safe，编译器负责把指针分类、生命周期及 cap-offset 转换为稳定元数据。

### 4.1 sret、out 与 inout 必须拥有不同语义

`v0.0.1-syscall-abi.md` §1.1.3 使用“调用方栈副本 + sret”，`jhyy-abi-v1.0.0.md` §3.2 也规定调用方分配返回槽，并将其作为隐式第一个参数。[1][9] 这在普通用户函数调用中成立，但在 syscall 边界不能自动成立。

内核写入的对象可能属于当前线程栈、TLS、region 或显式 `out` 参数。建议从消息类型层面显式分类：

| 类别 | 编译器标记 | 内核要求 |
|---|---|---|
| sret | `-> Reply` | 由封装器生成的返回槽；不需要用户提供用户指针 |
| in | 普通字段 | copy-in，禁止回写 |
| out | `out T` | copy-out，必须执行完整地址检查 |
| inout | `inout T` | 双向 copy；前后状态均受控 |
| region | `&[mut] u8` | 携带 base、len 与 lifetime/epoch |
| cap | `Cap<T>` | 只按 8 字节 token 及 cnode 规则改写 |

若 `Reply` 只有标量字段，封装器可以直接从 `RAX/RDX` 重建，无需 sret。若 reply 较大，封装器应在调用帧内分配 `Reply` 槽，将 `RSI` 设置为该槽地址，并由编译器保证其生命周期覆盖 `syscall` 及错误路径。

显式 `out T` 或 `inout T` 则必须携带地址及类型信息。编译器不应将其降级为普通 `T`，否则会丢失“内核将写入何处”的安全证据。

### 4.2 用户指针必须校验至访问发生时刻

建议定义“地址空间游标” `AsCursor`，而非只进行布尔式 `access_ok`：

```text
struct AsCursor {
    owner_pid: u64,
    root_epoch: u64,
    base: u64,
    limit: u64,
    perms: u8,   // R/W/X/User
}
```

校验顺序应固定为：

1. 规范化地址，拒绝内核半地址、非 canonical 地址及 NULL 页。
2. 验证页表/region 归属等于当前进程或已授予的 shared region。
3. 检查对象起始与结束位于同一区域或同一映射段。
4. 核对自然对齐及字段边界。
5. 记录 generation/epoch 与提交令牌。
6. 对 inout，在拷贝前固定源版本。
7. 在持有 page/region 锁的阶段内完成 copy。
8. 成功后将 epoch 提交到 reply；任何中途失败均撤销已经写入的部分。

“L1 编译期 > L2 runtime > L3 kernel fail-safe”不应被理解为只检查一次。L1 保证指针具有正确类型、方向、对齐及生命周期；L2 可在创建共享内存或 capability 时建立 epoch；L3 每次访问都验证游标、rights 与 generation。

`v0.0.1-capability.md` §4 的 `unsafe_cap`/WaiverCap 三层结构可直接复用：普通消息路径不使用 WaiverCap；跨进程 SHM 的 attach 使用显式 capability 与明确生命周期。[12]

### 4.3 copy-in/out 必须由单个状态机驱动

`copy_user` 接口应按方向、生命周期及失败点组织：

```text
copy_in(ptr, len, perms, cursor, token)
copy_out(ptr, len, perms, cursor, token)
copy_inout(ptr, len, perms, cursor, token)
```

建议错误码如下：

| 错误 | 触发条件 | 回滚要求 |
|---|---|---|
| `ErrInvArg` | tag 未知、size 溢出、对齐错误、reserved 非零、cap offset 越界 | 不应用任何 cap 改写 |
| `ErrBadAddr` | canonical、归属、权限或对象边界检查失败 | 撤销已经写入的字节 |
| `ErrBadAlign` | 未满足自然对齐 | 撤销 |
| `ErrStale` | epoch/generation 不匹配 | 撤销 |
| `ErrCapRevoked` | cnode slot 无效、rights 不足或 depth 校验失败 | 撤销 cap 迁移 |
| `ErrTooBig` | size 超过 4 KiB 且未使用 large 描述符 | 不映射 |
| `ErrTimeout` | reply 未就绪且相对超时耗尽 | 释放临时映射与 reply reservation |

失败路径必须遵循“全部或无”：已写入的用户字节、cap 迁移及 SHM 映射均须回滚。否则部分成功会被封装器解释为普通返回值，从而泄漏对象身份或修改状态。

SMAP 思路在此体现为：内核默认不能随便访问用户页；进入 copy 范围时建立受控访问，退出时清除。`v0.0.x` 可以先用软件页表 walk 加 epoch 锁实现正确语义，再由具体 CPU 扩展决定是否启用 SMAP。代码层面必须存在 `with_user_access { ... }` 边界，不能将“未来启用 SMAP”视为纯性能优化。

## 5. 寄存器、TCB 与 D16 必须共用同一布局版本

entry 汇编应先保存硬件状态，再调用 C 处理程序；exit 则必须恢复用户可见的完整上下文。`SavedRegs` 与 D16 元数据都应采用显式布局、版本字段及可 dump 断言，避免依赖不同工具链的结构体填充规则。

### 5.1 entry 与 exit 应形成对称序列

建议汇编骨架如下，其中具体指令仍需依据目标汇编器语法与实测结果收敛：

```text
syscall_entry:
    swapgs                    ; 仅在模型需要时，依 SMP/GS 规则锁定
    mov    gs:kernel_rsp, %rsp
    push   %r11               ; saved RFLAGS
    push   %rcx               ; return RIP
    push   %rax               ; service index
    push   %rdi               ; endpoint cap
    push   %rsi               ; msg ptr
    push   %rdx               ; msg size
    push   %r10               ; msg_tag
    push   %r8                ; timeout
    push   %r9                ; flags
    ; 保存 RBX/RBP/R12-R15、XMM0-5、FS/GS 依据 TCB 布局
    call   syscall_dispatch
syscall_exit:
    ; 从 TCB 恢复 volatile 寄存器；RAX 已经设置返回值
    ; RCX = user RIP；R11 = user RFLAGS
    ; 必要时执行 STAC/CLAC 配对或屏障
    swapgs
    sysretq
```

该骨架只表达控制流，不是最终指令清单。尤其需要注意：

- `SWAPGS` 的使用条件；
- GS 基地址模型；
- XMM 保存顺序；
- 栈对齐；
- 调试保存点；
- cooperative switch 与嵌套 syscall 的栈切换。

但语义必须稳定：RCX/R11 只承载返回状态；RDI..R9 构成可重排的 syscall frame；`SavedRegs` 位于 TCB。

### 5.2 TCB 布局必须同时服务调度与调试

`v0.0.1-process-model.md` §2.1 只提供抽象的 `saved_regs: SavedRegs`。[6] M3 建议将其替换为显式 TCB：

```c
struct TcbRegs {
    uint64_t rflags, rip, rsp;
    uint64_t rax, rbx, rcx, rdx, rsi, rdi;
    uint64_t r8, r9, r10, r11, r12, r13, r14, r15;
    uint64_t rbp;
    uint64_t xmm0_5[6][16];   // 自然对齐；若 M1 不用则置 reserved
    uint64_t fs_base, gs_base; // 单核占位
    uint64_t reserved[4];
};
```

编译器应为该结构生成固定偏移断言。版本号既属于 syscall ABI，也属于调试 ABI：`v0.0.4-debug-abi.md` §6 中的 `KernelStateHistory` 需要能够引用同一寄存器快照。[10]

### 5.3 D16 应原地改写 cap，但 payload 拷贝仍保持双相

D16 当前表述为 `{msg_tag: u32, n_caps: u16, cap_offsets: [u16; n]}`。[1] 建议锁定为：

- 16 字节对齐的 header；
- 至多 15 个 cap offset；
- 每个 offset 必须位于 payload 内，且为 8 字节对齐；
- 同一字节不得属于两个 cap；
- offset 列表按升序排列。

内核处理流程如下：

1. copy-in payload 到内核临时缓冲；或采用 double-map 只读映射。
2. 按 `msg_tag` 加载编译期 D16 描述符。
3. 对每个 cap offset 执行 cnode 查找、类型/rights/depth 检查、跨进程授权验证及 receiver namespace 计算。
4. 在临时缓冲中改写 token；此时用户原始 payload 仍不可见。
5. 仅在 commit 阶段向 receiver 交付，并撤销发送方移动后的访问。
6. reply 方向重新执行同一流程。

这条路径符合原则 #5：编译器生成 cap-offset、tag 及 wrapper；内核只解释紧凑元数据，不重建整套类型系统。若编译器为每个含 cap 的消息生成 `const D16_DESCRIPTOR[msg_tag]`，则可从 `v0.0.1-capability.md` §1 的 8 字节 cap 布局直接派生 D16，无需 language-level generics。[12]

## 6. Codegen 与确定性必须共同约束寄存器分配

M3 不应允许编译器自由挑选 syscall 寄存器。内联封装器、wrapper 生成及 D16 metadata 都应从同一机器可读描述产生，并在 CI 中比较汇编输出。

### 6.1 编译器接口应保持窄而完整

建议定义三个互补层：

```jhyy
// 用户书写的语言层；编译器验证消息与 endpoint
extern fn ipc_call(ep: Cap<Endpoint>, msg: Msg, timeout: u64) -> IoResult<Reply>;

// codegen 生成的具体单态封装；sprint 3a inline asm / 3b naked
extern fn __jhyy_syscall_3(rax: u64, rdi: u64, rsi: u64, rdx: u64,
                            r10: u64, r8: u64, r9: u64) -> u128;

// metadata；D16；每个 Msg 单态生成
const MSG_D16: D16Descriptor = ...;
```

具体封装器应由 codegen 生成，而不是手写重复汇编。其职责包括：

- 将 sret 槽地址或显式 `out` 指针放入 RSI；
- 加载 endpoint capability；
- 设置 `msg_size` 与 `msg_tag`；
- 将 128 位超时拆分到 R8/R9；
- 执行 `syscall`；
- 拆分 `RAX/RDX`；
- 构造 `IoResult`；
- 保留 RBX/RBP/R12..R15；
- 按消息字段顺序销毁已经移动的 cap。

`v0.0.2-foundation-revision.md` §4 将 sprint 3a/3b/3c/3f 列为 M1 前置，并将 3g 系列放在 M3-M4 之间。[11] 因此 M3 wrapper 可用 `inline asm` 加 `naked` entry，但不得假设 `&mut` 已经 ship；M1-M3 应使用 `*mut T` 及显式 cursor。

### 6.2 byte-equal 要求优先固定 wrapper 模板

为满足“跨编译稳定”，CI 应在固定 seed、目录、并行度及无关类型顺序下比较 `.il`/`.s` 封装输出：

1. 按消息类型字典序确定 D16 顺序。
2. 按声明顺序确定 cap-offset；插入无关类型不得改变已有 tag。
3. 固定临时寄存器命名及内联阈值。
4. 将 syscall stub 放在独立的 codegen pass，而不是依赖通用寄存器分配器。
5. 将 D16 写入可重定位 section，并由链接器确定性排序。
6. 每次构建生成 `abi_fingerprint = hash(regset || d16 || tcb || debug)`。

`-j1/-j4/-j8` 只验证构建复现性，不证明 ABI 稳定。真正的 ABI 测试必须在独立目录、不同构建顺序及构建后比较中进行。若并行构建产生的 tag 顺序不同，则并行度本身就是 ABI 破坏源。

`v0.0.0-design.md` §6 将 M3 排在 M2 之后，并指出 M5a design doc 可与实现并行。[13] 因此新文档必须在 M3 之前完成 review，否则 M3 会固化错误编码。

## 7. 验收必须从错误提交开始，而不是只测 happy path

正常路径只能证明封装器可以执行，不能证明地址校验、cap 回滚或并发失效安全。`v0.0.1.5-M5b-prereqs.md` §3 已经列出 header 解析、cnode 检查及相对超时；M3 验收应在此基础上加入内核指针、SHM、revoke 与并发提交用例。[14]

| ID | 场景 | 构造 | 期望结果 | QEMU/OVMF 步骤 |
|---|---|---|---|---|
| T01 | 6 参数边界 | endpoint + 4 KiB payload + timeout + flags | 内核按 RDI..R9 解码，reply 正确 | `-device isa-debug-exit` 输出 0 |
| T02 | 无 payload | `msg_size=0`、RSI=NULL 或 sentinel | 允许；禁止向 NULL 执行 copy-out | 测试固定 magic reply |
| T03 | 4 KiB 边界 | payload=4096-header | 成功 | 使用 boot sector/page dump 断言 |
| T04 | 超过 4 KiB 无 SHM | payload=4097 | `ErrTooBig`，无 cap 改写 | 注入 fault 计数器 |
| T05 | Large 降级 | has_large + 合法 `Cap<Shm>` 描述符 | 仅映射区间，zero-dopy copy 位图 | QEMU `-m 256M` + 自定义 shm driver |
| T06 | RCX 冲突回归 | wrapper 故意将值写入 RCX 后再执行 `syscall` | 编译期禁止或运行时失败，不得静默 | 单独 negative test |
| T07 | sret 正常 | `Reply` 只有标量 | 通过 RAX/RDX 重建 | 比较字节 |
| T08 | sret 大 reply | reply 超过 16 字节 | 编译器选择 inout/out 缓冲，TCB 不泄漏 | page fence |
| T09 | 内核写非法用户指针 | RSI 位于只读页 | `ErrBadAddr`，撤销部分写入 | QEMU monitor dump 页表 |
| T10 | 非 canonical/内核地址 | 设置 bit 63 或内核 canonical 区 | `ErrBadAddr` | 参数化 fuzz |
| T11 | TOCTOU | 另一线程在检查后 unmap/move | epoch 失效，`ErrStale`，无写穿透 | 确定性双线程 fixture |
| T12 | cap offset 越界 | D16 offset 位于 payload 外 | `ErrInvArg`，全部回滚 | metadata fuzz |
| T13 | 重复 cap offset | 两个 offset 重叠 | `ErrInvArg` | 代码生成 mutant |
| T14 | 跨进程 grant | sender move、receiver rights 不足 | `ErrCapRevoked`/rights，无 token 迁移 | 两个用户进程 |
| T15 | revoke 后进行中调用 | 提交前撤销 cap | 全无回滚，reply 失败 | 注入延迟点 |
| T16 | 嵌套 syscall | syscall A 的 wrapper 触发 B | entry/exit 栈及 RCX/R11 保存正确 | 显式服务链 |
| T17 | 超时 | 相对 1 ms RPC、receiver 睡眠 10 ms | `ErrTimeout`，reply reservation 清理 | `timer` mock |
| T18 | DebugEvent | 每次提交保存寄存器上下文 | 字节等于 TCB dump，`confidence=HardFact` | 启用 `--debug-info` |
| T19 | 构建目录 | `/tmp/a`、`/tmp/b` 不同路径 | wrapper 及 D16 hash 相等 | `diffoscope`/文本 diff |
| T20 | 并行度 | `-j1/-j4/-j8` | 产物 hash 相等 | 固定 seed + 删除缓存 |
| T21 | 无关类型插入 | 在无关模块添加类型 | 既有 `msg_tag` 稳定 | metadata ABI test |
| T22 | Cooperative switch | 调用期间让出 | TCB 完整恢复，RAX 不变 | M2 调度器 hook |

QEMU 命令模板如下：

```bash
qemu-system-x86_64 \
 -bios OVMF.fd \
 -kernel jhyy_os.efi \
 -m 256M -smp 1 \
 -device isa-debug-exit,iobase=0xf4,iosize=1 \
 -debugcon file:debugcon.log -global isa-debugcon.iobase=0x402 \
 -serial mon:stdio
```

具体端口及 OVMF 版本仍需按 M1 spike 实测，不能将模板视为不变规范。每个测试应使：

- 成功退出码为 0；
- 明确的错误类映射为 1..127；
- 严重断言映射为 128+。

CI 解析 `debugcon.log` 中的结构化 `DebugEvent`，并对照寄存器快照。任何失败测试都应提供 `KernelStateHistory + ErrChain + provenance`，而不是依赖 gdb。

## 8. M3 范围必须收敛，sprint 3g 系列应并行而非倒灌

M3 的交付物应限于“能够安全进入内核并传递类型化消息”，不能扩展到完整 GUI、异步 RPC 或通用语言运行时。3a/3b/3c/3f 是 M3 硬前置；3g/3g.5/3g.7 可以并行，但不能把 capability 类型推导悄悄塞回内核。

| Sprint | M3 交付物 | 估算 LoC/断言（非实测） | 依赖与耦合 |
|---|---|---:|---|
| **3a inline asm** | syscall stub、寄存器约束、`syscall`/寄存器 save | 300-700 | M2 TCB 布局前置；必须独立于 3g |
| **3b naked** | entry/exit 手写 prologue、SYSRET 路径 | 200-500 | 3a；与调度栈切换耦合 |
| **3c volatile** | user copy 访问屏障、MMIO 纪律 | 200-400 | 3a；定义 `with_user_access` |
| **3f barrier** | commit/revoke ordering、发布 epoch | 100-300 | 3c；M2 单核可降低要求，但不能删除接口 |
| **3g/3g.5/3g.7** | `Cap<T>` sema、phantom 0 字节、cap table byte-equal | 1500-3500 | 与 M3 并行；不得在 M3 之后阻塞基本 entry |
| **M3 acceptance** | §7 的 22 个测试 + fuzz | 2000-4000 | M2 + 3a/3b/3c/3f |

建议路线为：

1. **M3a（1 周非实测）**：先锁定寄存器表、TCB、错误码及 D16；使用裸汇编测试 entry/exit 往返。
2. **M3b（1-2 周）**：实现 <=4 KiB echo service、cap 移动及 copy-in/out。
3. **M3c（1 周）**：加入 SHM 描述符、epoch、撤销及超时。
4. **M3d（1 周）**：完成 §7 全矩阵、构建复现性及 debug ABI 冒烟测试。
5. **3g 并行**：cap sema 与 cnode byte-equal 联调。若 3g 延迟，M3 仍可使用具体、显式的 `CapRaw` wrapper；但不得让内核解析完整类型。

### 8.1 M3 的最大风险是把 M4/M5b 范围提前实现

| 风险 | 概率 | 影响 | 触发信号 | 缓解与 owner |
|---|---:|---:|---|---|
| RCX/R11 被通用寄存器分配器复用 | 中 | 致命 | 负向测试 T06 失败 | stub 专用约束；3a owner |
| TCB 字段与 M2 调度器不匹配 | 高 | 高 | 嵌套或 switch 后 RIP 错乱 | 单一 `tcb_layout.h`；M2/M3 共同 review |
| sret/out 指针分类缺失 | 高 | 致命 | 出现裸 `*mut T` syscall 参数 | sema 白名单；3g 联调 |
| TOCTOU 只检查一次 | 中 | 致命 | T11 在 revoke 后仍能写穿 | epoch/commit；M3c 强制 mutant |
| msg_tag 受插入类型影响 | 中 | 高 | T21 哈希漂移 | 确定性排序 + fingerprint |`
| 4 KiB 上限成为硬兼容常数 | 低 | 中 | 未来 FS/SHM 需要更大 header | 使用 `has_large`，保留上限调参 |
| 3g 倒灌至 M3 | 中 | 高 | M3 等待 cap sema | 先采用原始 token 路径；3g 并行 |
| DebugEvent 导致 release 膨胀 | 低 | 低 | 二进制大小回归 | release strip；T18 debug-only |
| UEFI/MS x64 与 syscall 混淆 | 中 | 高 | 文档或 wrapper 仍写“RCX=arg1” | ABI 分层 lint；doc 修订 |

`v0.0.4-debug-abi.md` 已经锁定，其尺寸与 D40 规则可以作为 M3 emit 规范。[10] 但 `v0.0.1-syscall-abi.md` §2 仍需明确区分 UEFI 与 syscall：前者遵循固件协议，后者使用内核定义的 7-in/2-out 编码。

## 9. 跨文档一致性体检要求多处“必须改”

本节覆盖用户指定文档及本节新增的关联项。ABI v1.0.0 兼容性的判断依据是：`jhyy-abi-v1.0.0.md` §11.3 承诺 v1.0.0 内容不得变更，除非升级主版本并记录迁移。[9] 本次新增寄存器规范属于 OS-era §13 范畴，不修改 v1.0.0 locked baseline，因此多数核心改动可保持向后兼容。

### 9.1 “必须改”会直接破坏 M3 或既有安全性

| 文件 | 位置 | 当前表述（摘要） | 建议修订 | 级别 | ABI v1.0.0 影响 |
|---|---|---|---|---|---|
| `v0.0.1-syscall-abi.md` | §1.1.3 | payload 通过寄存器 + 栈传递，与 Windows x64 一致；P0-3 待拍板 | 将“Windows x64”限定为用户态；增加 §4 完整寄存器表；关闭 P0-3，标注为已锁 R10 方案 | **必须改** | 兼容；现有文字尚未形成发布 ABI |
| `v0.0.1-syscall-abi.md` | §1.1.3 | sret 指针只要求“完整地址空间校验” | 拆分为 sret/out/inout、AsCursor、epoch、提交令牌及回滚路径 | **必须改** | 兼容 |
| `v0.0.1-syscall-abi.md` | §1.1.2 | payload <= 4 KiB | 明确为“快速 copy 上限”；增加 `has_large + Cap<Shm>` 降级及描述符版本 | **必须改** | 兼容；先前只有上限，没有稳定编码 |
| `v0.0.1-syscall-abi.md` | §1.1.4 / §12 | D16 `{msg_tag,u32,n_caps,u16,cap_offsets,...}`；主路径与 metadata 段关系不清 | 锁定 16 字节对齐 header、offset 规则、双相提交；明确 codegen 与 `.jhyy_d16` section | **必须改** | 兼容；定义新增 OS-era 段 |
| `v0.0.1-syscall-abi.md` | §1.2 | capability 传递、派生、复制 | 区分 move/grant、attach、`Cap<Shm>` 及原地改写；增加 L3 检查表 | **建议改** | 兼容 |
| `v0.0.1-syscall-abi.md` | §1.3 | `u64` 相对超时 | 明确 R8 低 64 位、R9 高 64 位 reserved，以及 timeout 在 nested/cooperative 场景的时钟语义 | **必须改** | 兼容 |
| `v0.0.1-process-model.md` | §2.1 | `saved_regs: SavedRegs` | 替换为明确的 `TcbRegs` 偏移；列出 syscall 及调度器保存/恢复字段 | **必须改** | 兼容；未发布 ABI |
| `v0.0.1-process-model.md` | §5.3 | “编译器在 cap 离开 scope 时 emit `cap_destroy`” | 明确 syscall 期间 cap 所有权及 reply/error 两条路径；禁止 double-revoke | **建议改** | 兼容 |
| `v0.0.1-capability.md` | §1 | `Cap<T>` 8 字节 wire format；cnode_idx 位于 sender namespace | 将“跨 IPC 改写”拆为 D16 offset 验证、receiver cnode 分配及 commit/abort；增加 generation/rights 步骤 | **必须改** | 兼容 |
| `v0.0.1-capability.md` | §3.3 | syscall 只接受 `Cap<T>` | 增加 `out/inout Cap<T>`、cap payload 与用户指针的生命周期不变量 | **建议改** | 兼容 |
| `v0.0.2-foundation-revision.md` | §3.2 | hybrid 内存模型包含跨进程共享 `unsafe_share` | 增加 `Cap<Shm>` 两阶段 attach，并引用 syscall 地址校验 | **建议改** | 兼容 |
| `v0.0.2-foundation-revision.md` | §4 M3 行 | “消息体走 struct pass-by-value；syscall ABI 与 MS x64 需分开” | 升级为具体 3a-3f 任务、TCB/寄存器验收、3g 并行及冻结门 | **必须改** | 兼容 |
| `v0.0.1.5-M5b-prereqs.md` | §3.1-3.4 | userland `ipc_call`、内核 header 解析及 cnode 检查 | 增加 D16、copy-in/out、user pointer cursor、epoch、revoke 回滚及超时；拆分“call 返回”与“reply 提交” | **必须改** | 兼容 |
| `v0.0.4-debug-abi.md` | §2.5 / §6 | 跨边界 struct 自然对齐；DebugEvent 56 B | 增加 `SyscallFrame{regs, tag, d16_hash}` 作为 `DebugEvent.payload` 合法类型；明确 release strip | **建议改** | 不兼容风险较低；建议 v1.1.x 增加类型 |
| `jhyy-abi-v1.0.0.md` | §3.1-3.3 | MS x64、RCX/RDX/R8/R9；sret 作为隐式第一参数 | 增加 §13.1 的 `amd64_jhyy_syscall` 契约；明确该契约不得影响 §3 MS x64 | **必须改（位于 §13）** | **不破坏 v1.0.0**，但属于 narrow ABI 接口 |
| `jhyy-abi-v1.0.0.md` | §13.3 | IPC header 只有 8 字节 | 扩展至 16 字节，或增加后续扩展字段；锁定大小端、对齐及 tag 分配 | **必须改** | 兼容；OS-era §13 |
| `jhyy-lang-spec-v1.3.0.md` | §8/§14/§17.5 | inline asm、naked、volatile、barrier、defer | 增加 syscall register clobber 约束、naked 函数禁止普通返回、volatile user-copy 顺序、`defer` 不跨越 `syscall` 所有权边界 | **建议改** | 若新增属性，需要 v1.4；已有语法可保留兼容 |
| `v0.0.0-design.md` | §6 M3/M5b | M3=syscall ABI，依赖 M2；M5b=IPC 实现 | 在 M3 中加入“register/TCB/D16/copy semantics”硬验收；M5b 前置增加 §9 的 M3 冻结门 | **建议改** | 路线图，不是 wire ABI |
| `v0.0.0-design.md` | §4 | amd64 only v0.x | 增加“syscall ABI 是 amd64-specific state，riscv64 port 必须重新定义” | **仅澄清** | 兼容 |

### 9.2 “建议改/澄清”仍关系到可实施性与测试有效性

| 文件 | 位置 | 问题 | 建议 | 级别 |
|---|---|---|---|---|
| `v0.0.3-explorations.md` | §1.1 C | Type-driven IPC 标记为已锁 | 增加“寄存器编码及 cap-offset 是 type-driven 的编译期输出” | 仅澄清 |
| `v0.0.3-explorations.md` | §9 M3 | “syscall 指令 + header 解析” | 引用新的 design doc，避免探索文档成为唯一事实源 | 建议改 |
| `v0.0.4-gui-explorations.md` | §4 | GUI 消息包含 `Cap<Surface>` 等 | 增加“>4 KiB surface state 走 `Cap<Shm>`”及 sret/out 规则 | 建议改 |
| `v0.0.1-design-index.md` | §4 | 已锁项未列寄存器 ABI 或 TCB 字段 | 将 `v0.0.5-syscall-abi-registers.md` 及新 TCB 约定加入锁清单 | 必须改 |
| `v0.0.1.5-M5b-prereqs.md` | §1 | 条件 10-15 混合 capability、ABI 及 spec | 将“syscall register/TCB test”拆为独立硬条件 | 建议改 |

## 10. 决策日志：六项条目应升级为已锁

新增设计文档应记录以下决策。状态标记为“🔒 建议升级”，因为用户明确要求本专题仍以 design doc 草案形式评审；一旦合并，即可移除“建议”。

1. **D-M3-1（🔒 建议升级）**：amd64 `syscall` 边界使用独立寄存器约定，不使用 MS x64 的 RCX 首参。
2. **D-M3-2（🔒 建议升级）**：`arg0..5 = RDI,RSI,RDX,R10,R8,R9`；RAX 为 service index；RCX/R11 属于 entry/exit。
3. **D-M3-3（🔒 建议升级）**：快速 payload 上限为 4 KiB；超过该上限时使用 `Cap<Shm>` 两阶段描述符，不将参数自动溢出到用户栈。
4. **D-M3-4（🔒 建议升级）**：reply 分为 sret、out 与 inout；内核显式校验 AsCursor、epoch、提交令牌及全部或无回滚。
5. **D-M3-5（🔒 建议升级）**：`SavedRegs/TcbRegs` 使用固定布局，M2 cooperative switch 与 syscall entry/exit 共用同一定义。
6. **D-M3-6（🔒 建议升级）**：D16 由编译器为每个消息类型生成；内核只解释紧凑元数据，并支持原地 cap 改写。

仍需保留为探索项的内容包括：

- `Cap<Shm>` 是否携带 dirty bitmap；
- SMAP 具体启用条件；
- DebugEvent 在 release build 中的保留级别；
- nested syscall 是否允许任意重入。

这些条目在 v0.0.x 期间不得升级为硬兼容承诺。

## 11. 结论：应先冻结寄存器与状态布局，再实现 IPC

**P0-3 的答案明确：arg1 不应放在 RCX，推荐方案也不是“把整个 Linux ABI 复制过来”，而是采用 R10 位移后的 `RDI/RSI/RDX/R10/R8/R9` 固定编码。** 这一方案同时解决硬件冲突、MS x64 兼容及 type-driven IPC 的可生成性。Linux 入口证据足以支撑 R10 编码及 RCX/R11 保存需求；AMD APM、Intel SDM 与 QEMU/OVMF 实测则用于锁定 SYSRET、STAR/LSTAR/FMASK 及 selector 细节。[2][3][4]

M3 的门槛不应停留在“能够执行 `syscall`”。真正的最小闭环包括：

- header 寄存器固定；
- payload 及 SHM 降级固定；
- sret/out/inout 指针分类固定；
- cap-offset 原地改写固定；
- 内核执行全部或无回滚；
- TCB 同时支持 cooperative switch 与 syscall；
- DebugEvent 能够 dump 同一寄存器集合；
- codegen 在 `-j1/-j4/-j8`、不同构建目录及插入无关类型后保持 byte-equal。

若这些要求未同时落地，后续 M4/M5b 的 capability 转移、revoke 及跨进程 grant 将不断暴露新的状态不一致。本文建议将规范主体合入 `v0.0.5-syscall-abi-registers.md`，在 v0.0.1 三章内联动，并作为 M3 冻结门。

## 数据来源

[1] `/data/inputs/v0.0.1-syscall-abi.md`  
https://intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html

[2] Linux kernel source tree—`arch/x86/entry/entry_64.S`  
https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/arch/x86/entry/entry_64.S

[3] Intel® 64 and IA-32 Architectures Software Developer’s Manual—Instruction Set Reference  
https://www.intel.com/content/www/us/en/developer/articles/technical/intel-sdm.html

[4] AMD64 Architecture Programmer’s Manual Volume 3—General-Purpose and System Instructions  
https://www.amd.com/content/dam/amd/en/documents/processor-tech-docs/programmer-references/24593.pdf

[5] DragonFlyBSD—`sys/platform/pc64/x86_64/exception.S`  
https://raw.githubusercontent.com/DragonFlyBSD/DragonFlyBSD/master/sys/platform/pc64/x86_64/exception.S

[6] `/data/inputs/v0.0.1-process-model.md`

[7] Microsoft Learn—x64 calling convention  
https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention?view=msvc-170

[8] `/data/inputs/v0.0.0-design.md`

[9] `/data/inputs/jhyy-abi-v1.0.0.md`

[10] `/data/inputs/v0.0.4-debug-abi.md`

[11] `/data/inputs/v0.0.2-foundation-revision.md`

[12] `/data/inputs/v0.0.1-capability.md`

[13] `/data/inputs/v0.0.0-design.md`

[14] `/data/inputs/v0.0.1.5-M5b-prereqs.md`

[15] Linux kernel documentation—ABI rules  
https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/plain/Documentation/process/abi.rst

[16] seL4 manual  
https://sel4.systems/Info/Docs/seL4-manual-latest.pdf

[17] x86-64 psABI source repository  
https://gitlab.com/x86-psABIs/x86-64-ABI/-/blob/master/ABI-software-installation-versioning.textument?ref_type=heads

[18] `/data/workspace/dr:2026082601/data_syscall_register_budget.csv`  
该文件为研究过程中的寄存器预算结构化数据。