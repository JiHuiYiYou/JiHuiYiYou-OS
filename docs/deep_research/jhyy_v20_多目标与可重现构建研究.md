# jhyy v2.0 多目标契约、最小 Runtime 与 PE/COFF `.efi` 可重现构建深度研究报告

## 执行摘要：QBE 路线可行，但必须先锁定契约、链接器与 runtime 边界

1. **v2.0 应维持 D25，但必须删除“不依赖 QBE 二进制”的完成条件。** QBE 上游已提交 `amd64_win`，提交信息明确说明其“允许 QBE 生成适用于 Windows 的正确汇编”，但并未把 QBE 移植为原生 Windows 程序；当前已知限制包括不支持 TLS，以及 C `long` 与 QBE `l` 的语义差异[1]。因此，v2.0 采用 **QBE + MinGW GCC** 是低风险路径，前提是锁定 QBE 源码提交，并禁止把“QBE 可生成 Windows 汇编”误解为“QBE 已完整支持 Windows 工具链”。`amd64_win_freestanding` 可以复用同一 ABI 后端，重点转为禁止 libc、生成 PE/COFF 可重定位 EFI 映像，以及提供最小 runtime。

2. **PE/COFF 可重现构建原则可行，但不能沿用现有 ELF 兜底措辞。** 关键控制项包括 `TimeDateStamp`、OBJ 时间戳、PDB 路径、CodeView GUID/Age、节填充、符号与字符串顺序、重定位、固定 `ImageBase`，以及 `__DATE__/__TIME__/__TIMESTAMP__`[6][9][11]。`--build-id=none` 不是 PE/COFF 的通用时间戳修复器：binutils 的 PE/COFF 实现会生成包含 CodeView 记录的 `.build-id`，并将其挂接到 Debug Directory[10]。当前文档应改为：**默认推荐 `lld-link` 配方；继续支持 GNU ld 时，采用 `/debug:none` 或确定性 PDB 配置，而不是无条件附加 `--build-id=none`。**

3. **UEFI 必须复用 Win64 ABI，而非提前切换 SysV。** `x86_64-unknown-uefi` 使用 Win64 调用约定；x86_64 UEFI 的 `efi_main(ImageHandle, SystemTable)` 由固件以 RCX、RDX 调用，映像子系统为 `EFI_APPLICATION`，并且必须可重定位[4][5][8]。SysV 只应保留给 v2.x 的 `amd64_sysv*` 后端；若把 UEFI 入口误设为 SysV，即使后续代码生成正确，也属于接口级架构缺陷。

4. **最小 runtime 契约必须成为 v2.0 的一等交付物。** 建议拆分为 `crt0`、内置实现 `core`、panic/abort、可选 arena，并约定入口顺序为 `_start → 固定栈/保存固件参数 → 零初始化 BSS → 调用 `efi_main` 或语言 `main``。UEFI 阶段应禁用 red-zone，默认采用软浮点；不得静默复用 `compiler/runtime/runtime.c` 中的 libc 路径。

5. **修订建议可以立即合并。** 本报告提出 9 项文档修订。其中，第 1、2、4、5 项解决正确性或路线图冲突，应在 v2.0 编码前落地；其余项目可在 MVS 实现过程中同步修正。

---

## 第一部分：`--target=` 多目标分派契约应稳定 IR、隔离后端

### 1. TargetSpec：triple 只作查询键，权威配置由分层 spec 承载

**建议将 `--target=` 明确定义为“目标环境规范选择符”，而不是可以派生出全部编译行为的字符串解析器。** triple 的作用是选择基准配置；真正决定代码生成、运行约束和链接行为的，应是规范化后的 `TargetSpec`。

本报告采用如下 canonical form：

```
arch-vendor-os-environment
```

其中 `freestanding` 是 `environment` 的显式成员，而不是隐写在其他字段中的模糊标记。v2.0–v2.x 的最小目标矩阵如下：

| Canonical triple | ABI key | OS/env | v2.0 MVS | Runtime | 链接器策略 |
|---|---|---|---|---|---|
| `x86_64-pc-amd64_win` | `ms_x64` | Windows/ hosted | 已有 | hosted core | GCC → GNU ld |
| `x86_64-pc-amd64_win_freestanding` | `ms_x64` | UEFI/ freestanding | **新增** | crt0 + builtins | GCC → ld，或可选 lld-link |
| `x86_64-pc-amd64_sysv` | `sysv_x64` | Linux/ hosted | 推迟 | hosted core | 自写后端后启用 |
| `x86_64-pc-amd64_sysv_freestanding` | `sysv_x64` | none/ freestanding | 推迟 | crt0 + builtins | 自写后端后启用 |

Rust 的 UEFI 目标进一步证明，“freestanding/UEFI”并不要求更换基础 ABI。其 `x86_64-unknown-uefi` 复用了 `x86_64-unknown-windows` 的 LLVM target，显式设置 `entry_abi = Win64`，并以 `-mmx,-sse,+soft-float` 建立保守的 FP 模型[4]。jhyy 不必照搬 LLVM target 字符串，但应复刻同一配置层次：**ABI key 与 OS 环境正交。**

建议在编译器驱动中定义以下结构：

```text
struct TargetSpec = {
    triple: CanonicalTriple,
    arch: "x86_64",
    abi: ABIKey,           // MsX64 | SysVX64 | Aapcs64 | RiscV64
    os: OsKind,            // Windows | Uefi | None | Linux
    env: EnvKind,          // Hosted | Freestanding
    pointer_width: 64,
    data_layout: DataLayout,
    cpu: "x86-64",
    features: FeatureSet,   // +soft-float / -sse / -mmx / -red-zone ...
    call_conv: CallConv,    // entry / default / extern
    relocation_model: "static" | "pic",
    code_model: "small",
    image_format: "pe-coff" | "elf" | "mach-o",
    subsystem: "efi-application" | "console" | "none",
    entry_symbol: "_start",
    main_abi_symbol: "efi_main" | "main_jhyy",
    runtime: RuntimeProfile,// hosted-libc | uefi-minimal | none
    builtins: BuiltinSet,   // memcpy/memset/memcmp/__chkstk/soft-float
    panic_strategy: "abort",
    pre_link_args: [LinkerArg],
    link_args: [LinkerArg],
    post_link_args: [LinkerArg],
    reproducibility: ReproPolicy,
}
```

字段继承顺序建议为：

```
defaults.x86_64
  → arch.x86_64
  → abi.ms_x64
  → os.windows / os.uefi
  → env.hosted / env.freestanding
  → target-specific overrides
```

`amd64_win` 与 `amd64_win_freestanding` 必须共享 `abi.ms_x64`、IL type mapping、sret hidden pointer 和寄存器传参规则；二者仅在 `os`、`env`、`runtime`、`link_args`、可调用标准设施及调试配置上分叉。这样的继承结构使“新增 freestanding”主要表现为配置扩展，而不是 ABI 重写。

![target dispatch](https://one-agent-prod-1343551737.cos.ap-guangzhou.myqcloud.com/artifacts/1851/b8c73c218ea2433b98bd69ffa98e9bab/0PnLdjCGaRD/task-79d7f4509001ffd0ab344bcafba56771/.rendered/_assets/dr%3A20260826_jhyy_efi/fig_target_dispatch.png?q-sign-algorithm=sha1&q-ak=AKID_REDACTED&q-sign-time=1787727729%3B1795503729&q-key-time=1787727729%3B1795503729&q-header-list=host&q-url-param-list=&q-signature=b3c35921f1dbe3004c7469a25f1832300a70ed1a)

*图 1：target 分支应前移至语义定型，emit 只消费稳定的 ABI key；链接器选项不应回灌语言语义。数据来源：QBE `amd64_win` 提交[1]、Rust UEFI target[4]、UEFI 规范[8]。*

**目标选择不得改变已稳定的语言 IR；需要分派的是 lowering 规则，而不是程序语义。** 建议在驱动中先执行 `parse → select_base → resolve_env → validate`，随后才进入语义分析。IR 中引入平台中性字段 `ty.layout` 和 `call.conv`，但不写入 `OsString` 之类不可比较数据；后端则根据 `ABIKey` 选择寄存器类、shadow space、struct passing、sret 和帧布局。

现有 `amd64_win` 的“RCX/RDX/R8/R9 + hidden sret pointer”应与 `amd64_win_freestanding` 共用一套实现。项目 ABI 文档记录的现有 sret 约定必须完整保留，相关兼容性要求包括：

- 所有返回大对象的调用均经过同一 hidden pointer lowering；
- 现有 `W-001~W-009` workaround 按 `ABIKey = MsX64` 匹配；
- 同一调用签名在 hosted 与 freestanding 之间不得出现寄存器或栈帧差异；
- 不得仅为支持 UEFI，在 MS x64 后端中插入 SysV 特例。

由此可将 v2.0 的大部分变更收敛为“新增配置 + 新增 runtime”，而不是重写既有 codegen。

### 2. CLI、语义与链接契约：未知 triple 必须快速失败

**CLI 的首要责任是尽早消除“同名不同义”和“冲突 flag”的配置歧义。** 建议规定：

- `--target` 接受 canonical triple；
- 短名如 `amd64_win_freestanding` 仅作为带警告的别名；
- 未在 `targets/*.toml` 注册的组合直接报错；
- 一个编译单元只能有一个“编译 target”，并锁定 `target_spec.id`。

与 target 相关的输入应分为三类：

| 类别 | 典型输入 | 允许范围 |
|---|---|---|
| 源级属性 | `#[target(...)]`、`#[cfg(target_os="uefi")]`、`#[export_name]` | 多个目标可共同存在，由条件选择 |
| 编译级 flag | `--target`、`-O`、`-C relocation-model` | 同一编译单元必须一致 |
| 链接级 flag | `--linker`、`-C link-arg`、库搜索路径 | 允许追加，但不得覆盖 spec 的强制项 |

组合冲突至少应覆盖以下场景：

- `--target=amd64_win -C no_libc`：允许，但仅用于极简 Windows 实验，不应与 UEFI runtime 混用；
- `--target=amd64_sysv -C red-zone`：尚未实现 SysV，报错；
- `--target=amd64_win_freestanding` 与 `extern "sysv64" fn`：除非显式 FFI 标记，否则报错；
- `-C reproducible=strict` 与 `-g`、PDB、动态 `ImageBase` 或当前时间源：在 finalize 阶段报错；
- `-C relocation-model=static` 与缺少 `.reloc`：报告 EFI 兼容性风险。

**“不 link libc”与 `#[no_std]` 是两个不同维度的开关。** v2.0 可以把 `freestanding` 设为默认配置，但编译器需要区分三层状态：

| 层 | 含义 | 报错阶段 |
|---|---|---|
| 1. 链接环境 | `env.hosted` 允许 libc，`env.freestanding` 禁止 libc | 链接或 runtime 选择 |
| 2. 语言能力 | `#[no_std]` 禁用托管标准库 | 语义分析 |
| 3. 启动契约 | `#[start]`、`#[panic_handler]`、`#[lang = "start"]` 由 target runtime 定义 | 语义分析与 runtime 解析 |

v2.0 最小可行规则是：

- `amd64_win_freestanding` 自动推导 `env.freestanding` 和 `runtime = uefi-minimal`；
- 仅在用户显式写入 `#[no_std]` 时触发完整 no_std 能力检查；
- `#[link_section]`、`#[naked]`、`#[export_name]`、`asm!` 仍受语言版本门控；
- 在 `#[no_std]` 尚未稳定前，允许通过 `#[runtime_start]` 或内置 crt0 组合提供 `efi_main`，避免把启动机制与标准库属性强绑定。

建议禁止以下隐式行为：

- 隐式链接 `runtime.c`；
- 隐式引入 libc 符号；
- 通过 `#[no_std]` 自动改变 calling convention；
- 通过 `--target` 自动启用尚未稳定的语言属性；
- 把“没有标准库”解释为“没有 panic handler、启动代码或内置符号”。

freestanding 被禁用或延迟检查的清单如下：

| 类别 | v2.0 处理 |
|---|---|
| 动态堆 | 禁用 |
| 线程 local | 禁用 |
| `std` 输入/环境 | 禁用 |
| `print!` / `println!` | 降级为 `printk` 内部项 |
| `panic` 展开 | 只允许 abort |
| `#[link_section]` | 仅 M1 之后稳定 |
| `#[naked]` | 仅 M1 之后稳定 |
| `asm!` 稳定 API | 仅 M1 之后稳定 |

对于 M1，可以通过预导入 `jhyy::efi::{printk, EFI_HANDLE, EFI_SYSTEM_TABLE}` 及内部 runtime 包来满足启动需求，而不要求用户直接使用 `#[no_std]`。这既符合现有决策 3，也避免了“runtime 已经拆分，但语言仍假装只有一个 hosted C runtime”的断层。

### 3. codegen dispatcher：先建立开关，再按文件隔离变更

**现有 `codegen.c` 与 `codegen.jhyy` 不应一次性重写；v2.0 只需先打通配置、链接和启动路径。** 建议按以下顺序实施：

1. 先建立 `TargetSpec`；
2. 再引入 `ABIKey`；
3. 随后改造调用规则查询；
4. 最后接入新链接器 driver。

建议保留现有 MS x64 函数为默认实现，新增 `abi/mod`、`emit/ms_x64`、`emit/sysv_x64` 和 `linker/{gnu_ld,lld_link}.toml`。寄存器分配、指令选择和 sret 规则全部通过 `TargetSpec.abi` 查询，不读取 triple 字符串。

| 改造点 | 位置（建议） | 动作 | 估算 | 是否影响既有 byte-equal |
|---|---|---|---:|---|
| TargetSpec 解析/校验 | `driver/target.rs/.jhyy` | 新增 canonical triple 表、错误码 | 400 | 否 |
| Sema 平台条件 | `sema.jhyy` | `#[cfg(target_*)]`、禁用清单 | 350 | 否 |
| CallingConv 查询 | `abi/call.rs` | RCX/RDX/R8/R9、sret、shadow | 500 | 仅新增 target |
| IR lower 钩子 | `lower.jhyy` | 类型布局、参数类、byval | 600 | 否 |
| MS x64 emit | `codegen.c` `emit_fn` | 读取 ABIKey；函数指针表 | 300 | 否 |
| SysV emit | v2.x 新文件 | RDI/RSI/RDX/RCX/R8/R9 | 1500 | 不涉及 |
| Runtime resolver | `runtime.jhyy` | hosted / crt0 / builtins | 450 | 否 |
| Linker driver | `linker/*` | pe/elf 参数、repro flags | 600 | 仅新增 target |
| QBE IL 规范化 | `qbe/emit`、`tests/repro` | label/temp 稳定排序 | 500 | 仅新增测试 |

上述工作量均为设计与评审估算，不是已测量值。估算显示，v2.0 的核心工作不在既有 MS x64 后端，而在目标表、runtime 选择和链接契约；这进一步支持保留 `amd64_win` 既有实现。

**QBE IL 稳定性必须单独立项，不能把理论上的纯函数式转换直接当作 CI 硬门。** QBE IL 使用 `$global`、`%temporary`、`@label` 和聚合类型，标签与临时名可能受到生成顺序影响[12]。QBE 上游提交也未承诺 deterministic output flag[1]。因此：

- `.il` byte-equal 应作为 **strict mode** 的参考指标；
- 不能把其漂移直接判定为代码生成错误；
- 若实现 label canonicalization，应覆盖语义等价重命名、块排序、Phi 参数排序、数据段顺序，以及跨编译单元的稳定命名。

v1.2.1 的 7 行 label cascade 漂移表明，排序变化可能沿 CFG 传播。因此，验证目标应分为两级：

| 级别 | 验证对象 | 通过条件 |
|---|---|---|
| Normal | `.efi` | 功能性、ABI、OVMF 启动、final artifact byte-equal |
| Strict | `.il`、`.s`、`.efi` | 在固定工作区、固定输入顺序和固定 QBE 提交下全部 byte-equal |

### 4. 最小 Runtime 契约：crt0 负责启动，core 负责内置，程序只负责业务逻辑

**最小 runtime 的目标不是“尽量小的 C 运行时”，而是建立责任明确、可由启动器替换的接口边界。** 建议拆分为四层：

| 层 | 最小职责 | 禁止事项 |
|---|---|---|
| `crt0` | 启动汇编、栈、BSS、固件参数、入口调用 | 业务逻辑、libc 调用 |
| `core` | `memcpy/memset/memcmp`、`__chkstk`、软浮点、abort | 动态分配、全局初始化器魔术 |
| `panic` | `#[panic_handler]` → abort/日志 | unwind、依赖固件之外的服务 |
| `alloc` | 可选 arena | v2.0 M1 不要求 |

UEFI 入口的确定性顺序如下：

```
firmware: RCX=ImageHandle, RDX=SystemTable
→ _start
   ; 1. 若固件未保证栈，设置 RSP；UEFI 已提供栈，仅做断言/对齐
   ; 2. 保存 ImageHandle/SystemTable（.data/.bss 或寄存器参数透传）
   ; 3. 调用 memset 清零 .bss
   ; 4. 调用 runtime_init(ImageHandle, SystemTable)
   ; 5. call efi_main / main_jhyy
   ; 6. 用返回值调用 Exit()；若返回类型为 ! 则 halt
```

UEFI 调用约定要求前四个整数参数依次使用 RCX、RDX、R8、R9；RSP 必须按 16 字节对齐，易失寄存器包括 RAX、RCX、RDX、R8、R9、R10、R11 和 XMM0–XMM5[8]。启动汇编建议从固件接收 `(EFI_HANDLE, *EFI_SYSTEM_TABLE)` 后，只执行最小准备动作：

```asm
; amd64_win_freestanding crt0.S（概念示例，非项目源文件）
    .text
    .globl _start
_start:
    ; RCX=ImageHandle, RDX=SystemTable（UEFI/Win64）
    mov [ImageHandle@GOTOFF], rcx
    mov [SystemTable@GOTOFF], rdx
    and rsp, -16
    sub rsp, 32                 ; 保留 32 字节 shadow space
    lea r8, [__bss_start]
    lea r9, [__bss_end]
    call memset_zero            ; (dst, value=0, n)
    call runtime_init
    call efi_main               ; RCX/RDX 已透传
    mov rcx, rax
    call ExitImage
1:  hlt
    jmp 1b
```

上述代码片段为设计草案，尚未在 QEMU/OVMF 中实测。具体 `.bss` 符号、GOT 形式、重定位和 `ExitImage` 服务指针取决于 QBE/GCC 输出以及链接脚本，因此不能直接写入最终 runtime。

编译选项建议为：

```text
-m64 -mabi=ms -ffreestanding -fno-builtin -fno-stack-protector
-mno-red-zone -mgeneral-regs-only -msoft-float -fshort-wchar
-fno-asynchronous-unwind-tables -fno-unwind-tables
```

`-mno-red-zone` 对 UEFI 是必需的，因为固件可以在不遵守 red-zone 约定的情况下触发中断或调用；`-mgeneral-regs-only` 避免在尚未建立 FP/SIMD 状态时使用向量指令。第三方资料亦建议使用 `-fpic`、`-mno-red-zone` 和 `-mgeneral-regs-only` 等选项构建 UEFI 代码[13]。

**BSS、栈和 panic 必须由 runtime 契约显式覆盖，不能假设由固件或链接器默认处理。**

| 资源 | 责任方 | v2.0 最小行为 |
|---|---|---|
| 初始栈 | 固件 | 入口前可用；crt0 仅做对齐断言 |
| `.bss` | crt0 + 链接器 | `memset(0)`；禁止未零初始化假设 |
| `.data` | PE 加载器 | 由文件初始化 |
| `ImageHandle/SystemTable` | crt0 | 保存为 `core::efi::CONTEXT` |
| 堆 | 可选 `alloc` | v2.0 使用固定 arena 或禁用 |
| Panic | `#[panic_handler]` | `efi_panic → 打印 + hlt/Exit` |
| Stack overflow | 编译器 | 启用 `__chkstk` 或静态帧限制 |

**`__chkstk` 应默认按需启用，而不是因 freestanding 被静默删除。** 若启用 segmented stacks 或存在大栈帧探测，runtime 必须提供：

```text
__chkstk(size: usize) -> ()
```

实现应读取固定守卫页，或直接调用 UEFI `AllocatePages`；在 M1 阶段，可以先通过 `-mstack-probe-size` 或限制最大栈帧来规避复杂探测。无论如何，链接最终必须解析该符号，不能保留 undefined weak 行为。

### 5. v2.0 MVS：先打通“编译—链接—启动—可重现”闭环

**v2.0 的最小成功切片应围绕一条完整路径定义，而不是按语言特性逐项铺开。** 建议 MVS 为：

> `hello-freestanding.jhyy → .il → .s/.o → kernel.efi → OVMF 输出 “jhyy: hello efi”`

具体验收范围如下：

| 类别 | v2.0 MVS | 可推迟 |
|---|---|---|
| Target 分派 | canonical triple、`TargetSpec`、MsX64 | SysV、rv64 |
| Codegen | 复用 `amd64_win`；支持 extern/FFI | 自写 IL→.s |
| Runtime | crt0、BSS、`efi_main`、panic、abort、mem* | heap、threads、unwind |
| 语言特性 | 必要 FFI、printk | `#[no_std]` 属性稳定、`#[link_section]`、`#[naked]`、`asm!` 稳定 API |
| 链接 | PE32+、EFI_APPLICATION、`.reloc` | 自研 linker |
| Reproducibility | `.efi` strict byte-equal | `.il` strict 可选 |
| 测试 | OVMF printk + repro CI | SMP、FS、网络、驱动 |

MVS 刻意不把 `amd64_sysv` 自写后端、完整 `core`、heap 和语言属性稳定化绑定为 M1 阻塞项。M1 启动所需的 `printk`、固定栈、BSS 和 panic 均可由内部 runtime 包与 FFI 提供。

M1–M11 依赖链应改为：

```
M1 = v2.0 MVS（目标契约 + EFI 启动）
M2 = no_std/capability 语义（v3.0 3d）
M3 = link_section / naked / asm（v3.0 3b/3e/3f）
M4 = 自写 backend、SysV（v2.x）
M5+ = 内核服务、调度、驱动、文件系统
```

这一排序避免了当前“先稳定语言属性，M1 才能启动”的循环依赖。其关键逻辑是：**启动器需要的是稳定 runtime 接口，不是全部语言属性已经稳定。** 只要 crt0、内置符号、panic 和 FFI 可以组合，M1 即可成立。

---

## 第二部分：最小 Runtime 是 EFI 启动正确性的前提

### 6. Runtime 接口：程序只看到 `main_jhyy`，crt0 负责固件适配

**UEFI 程序应在语言入口之外增加一层显式 runtime 适配，以隔离固件 ABI 与用户代码。** 建议定义以下符号：

| 符号 | 责任 |
|---|---|
| `_start` | 由 PE `AddressOfEntryPoint` 引用 |
| `efi_main` | 由 crt0 调用，或从 `_start` 直接导出 |
| `runtime_init` | BSS 之后、用户代码之前的初始化 |
| `main_jhyy` | 用户程序逻辑入口 |
| `jhyy_panic` | 语言级 panic 落地 |
| `memcpy/memset/memcmp` | 编译器内置 |
| `__chkst(可选)` | 大栈帧探测 |
| `__aeabi_* / soft-float` | 当前目标不需要，保留扩展位 |

用户代码建议采用：

```text
#[runtime_start]
fn main_jhyy(handle: EFI_HANDLE, st: &EFI_SYSTEM_TABLE) -> EFI_STATUS {
    printk(st, "jhyy: hello efi\n");
    EFI_SUCCESS
}
```

编译器应生成：

- `efi_main`，负责读取保存的固件参数；
- 或在调用约定允许时，由 `_start` 直接别名到 `efi_main`；
- 随后调用 `main_jhyy(handle, st)`；
- 成功路径调用 `BootServices.Exit`；
- 失败路径调用 `jhyy_panic`。

UEFI 规定，所有 image 入口均接收 image handle 和 system table；x86_64 下，前两个参数位于 RCX、RDX[8]。因此，`efi_main` 不应被定义为普通 `extern "C" fn()`。建议引入 `extern "efiapi"`：在 MS x64 target 上等于 `extern "ms64"`，在 SysV target 上由后端重写。这样可防止 `#[no_std]` 尚未落地时，入口 ABI 已经先行错误。

### 7. builtin 与 panic：编译器不能随意调用 undefined libc

**编译器内置和 panic 兜底必须进入 target spec，而不是继续散落在 `runtime.c`。** 建议明确以下规则：

| 类别 | v2.0 默认策略 |
|---|---|
| `memcpy/memset/memcmp` | 由 `core` 提供强符号；编译器不得生成 libc 调用 |
| 128 位整数运算 | 默认拒绝，或提供 soft-intrinsics |
| `memmove` | 提供独立实现，禁止折叠为 `memcpy` |
| `__chkstk` | 按需提供 |
| 软浮点 | 默认不启用，配置开关集中管理 |
| AEABI 类符号 | x86_64 不需要，避免误报依赖 |
| `jhyy_panic` | 输出 `PanicInfo`、服务状态、文件/行号；调用 abort |
| abort | 输出失败状态后执行 `Exit` 或 `hlt` |
| panic 展开 | 禁止 |

`compiler/runtime/runtime.c` 应重构为：

- `runtime/hosted/`：保留 `main` 适配和 arena；
- `runtime/uefi/crt0.S`；
- `runtime/uefi/builtins.c`；
- `runtime/uefi/panic.c`；
- `runtime/common/builtins.c`。

构建系统根据 `TargetSpec.runtime` 选择包。原有 hosted 测试不得再无条件链接整个 `runtime.c`，否则即使指定 freestanding，仍可能把 libc 依赖带回最终映像。

**Capability wire format 不应进入 v2.0 runtime 最低门。** `Cap<T>` 的 8 字节布局规定为：

```text
cnode_idx:u32
depth:u8
rights:u16
phantom:u8 = 0
```

该布局可以写入 ABI spec 第 13 章，但 MVS 不需要 capability 系统调用。建议先在 QBE IL 层将 `Cap<T>` 定义为 8 字节 opaque struct；M1 只验证其按值传递、大小、对齐和 debug print。只有当 M2+ 内核提供 capability invoke 时，才增加 wire register/stack convention。这样可以避免 v2.0 同时承担启动、可重现、Capability ABI、no_std 和语言属性扩展。

### 8. 构建模式：默认关闭副作用，reproducible 必须覆盖全链路

**`-ffreestanding` 的语义应来源于 target，CLI 只提供诊断性覆盖。** 建议规则如下：

| 配置来源 | 默认结果 | 允许行为 |
|---|---|---|
| `--target=amd64_win_freestanding` | `freestanding = true` | 自动禁用 hosted runtime |
| `#[freestanding]` crate 属性 | 可选、显式 | 便于非默认 crate 自检 |
| `--target=amd64_win -C freestanding=yes` | 允许 | 仅用于实验性无 libc Windows |
| `--target=amd64_win_freestanding -C freestanding=no` | **禁止** | 避免 UEFI 映像重新引入 libc |

编译期开关至少包括：

- `-C red-zone=no`
- `-C sse=no`
- `-C builtins=minimal`
- `-C reproducible=strict`
- `-C deterministic-qbe=strict`
- `-C keep-intermediates=il,s,obj,efi`

“严格 reproducible”的含义应是：在固定 `SOURCE_DATE_EPOCH`、固定 workspace、固定工具版本、固定输入顺序，以及经过规范化排序的 QBE IL 下，`.efi` byte-equal。若 `.il` 因合法但非规范的 label 重命名发生抖动，应保留测试产物，并将 `.efi` 作为唯一 release gate。

---

## 第三部分：PE/COFF 可重现构建可行，但必须控制全链路输入

### 9. QBE 可用于 v2.0，但必须锁定提交并持续验证

**`amd64_win` 已经是上游概念，项目不需要为此修改 QBE 即可启动 v2.0；真正的风险在于提交漂移和 C 类型语义。** QBE 提交记录表明，`amd64_win` 通过 `-t amd64_win` 或 `TARGET=amd64_win` 选择，测试方式为交叉工具链加 Wine[1]。上游提交作者为 Scott Graham，日期为 2025-02-07；提交者及提交日期为 Quentin Carbonneaux，时间为 2026-02-12[1]。

提交记录还明确列出两项边界：

- **不支持 TLS；**
- C `long` 与 QBE `l` 的语义不同，测试驱动因此将部分 `long` 改为 `long long`[1]。

这意味着 jhyy 的 `long`/`isize` 映射必须设置 CI 约束，避免依赖上游尚未保证的类型语义。

建议采取以下供应链控制：

1. 在 `toolchain/qbe.lock` 中锁定 commit；
2. 在 CI 中复刻官方 `TARGET=amd64_win tools/test.sh all`；
3. 增加 jhyy 自有 ABI conformance tests；
4. 建立 `qbe` submodule 或 vendor 副本；
5. 保留 `QBE_IL_DUMP`；
6. 保留 `QBE=/path/to/qbe` 覆盖机制。

v2.x 自写后端可以改为：

```text
amd64_win(hosted) → QBE
amd64_win(freestanding) → QBE
amd64_sysv* → 自写 IL→.s
```

在此之前，不应删除 QBE。D25 的路线由此得到维护：QBE 是工具链实现细节，不是最终产品依赖。

![repro controls](https://one-agent-prod-1343551737.cos.ap-guangzhou.myqcloud.com/artifacts/1851/b8c73c218ea2433b98bd69ffa98e9bab/0PnLdjCGaRD/task-79d7f4509001ffd0ab344bcafba56771/.rendered/_assets/dr%3A20260826_jhyy_efi/fig_repro_controls.png?q-sign-algorithm=sha1&q-ak=AKID_REDACTED&q-sign-time=1787727729%3B1795503729&q-key-time=1787727729%3B1795503729&q-header-list=host&q-url-param-list=&q-signature=0ceae9f9da4e5e3e23666d6c3ced9de1888d0fc9)

*图 2：PE/COFF 可重现性涉及时间戳、调试、链接、IL 与宏等多类独立控制；单一 `/Brepro` 或 strip 不足以覆盖。数据来源：Microsoft PE/COFF[9]、LLVM 可重现构建[6]、Debian 可重现构建[11]、binutils[10]。*

完整控制项 CSV 可下载：[PE/COFF 可重现构建字段与控制项](/data/workspace/dr:20260826_jhyy_efi/repro_fields.csv)。

### 10. 技术核验：时间戳只是入口，链接布局与调试标识才是主要风险

**PE/COFF 的每个非确定性来源都必须有单一权威控制点。** Microsoft PE 规范指出，TimeDateStamp 可以为零或 `0xFFFFFFFF`；节必须按 `SectionAlignment` 对齐；Debug Directory 保存调试数据的地址与大小；重定位项包含 `ABSOLUTE`、`HIGHLOW` 等类型[9]。可重现 PE/COFF 说明进一步指出，确定性文件的内容只能由文档化输入决定，TimeDateStamp 在确定性 PE/COFF 中不再是真实生成时间，而是由文件内容导出的标识符[14]。

| # | 核验项 | PE/COFF 事实 | jhyy v2.0 最小可靠控制 | 状态 |
|---|---|---|---|---|
| 1 | `--build-id=none` | binutils PE/COFF 会创建 `.build-id`，写入 CodeView 记录，并由 Debug Directory 引用；固定 16 字节[10] | 不要在兜底命令中无条件附加 `--build-id=none`；选择 `none`、`hash` 或 `debug:none`，一次且仅一次 | **文档必须改** |
| 2 | COFF `TimeDateStamp` | 位于 COFF Header，可为零[9] | ld `--no-insert-timestamp`；或固定 `SOURCE_DATE_EPOCH`；lld `/Brepro` 或 `/timestamp:<N>` | 已验证文档 |
| 3 | OBJ timestamp | clang/clang-cl 默认写入；lld-link 也写入输出时间戳[6] | GCC `-Wdate-time -D__DATE__=...`；MSVC/clang `/Brepro`；GCC 工具链需实测 | 需 CI 实测 |
| 4 | Debug/PDB | Debug Directory 引用 CodeView RSDS；GUID/Age/path 均非确定[9][14] | `/debug:none`，或 `/pdbpath:none` + 固定 GUID/Age；禁止嵌入绝对路径 | lld 已验证，GCC 需实测 |
| 5 | `ImageBase`、ASLR | PE 可重定位；UEFI 映像可能被加载到其他地址[5] | 保留 `.reloc`；测试时使用固定 `ImageBase`，但不得删除重定位 | 需 OVMF 实测 |
| 6 | Section padding/sort | SectionAlignment 与文件对齐填充可能非确定[9] | 零填充、固定对象顺序、稳定链接脚本 | 需 CI 实测 |
| 7 | `__DATE__/__TIME__/__TIMESTAMP__` | 本质上非确定[6] | `-D__DATE__= -D__TIME__= -D__TIMESTAMP__=`；CI 设置 `SOURCE_DATE_EPOCH` | 已验证文档 |
| 8 | Symbol/string order | 临时名、匿名命名空间、并行编译会影响顺序[15] | 排序 `.o`、稳定 `ar`、关闭并行中间输出、规范化 QBE label | QBE 需实测 |
| 9 | CFI、`.eh_frame`、`.pdata`、guard | 表顺序或指针可能非确定 | `-fno-unwind-tables -fno-asynchronous-unwind-tables`；不启用 stack guard | UEFI 推荐 |
| 10 | IAT/import | UEFI 应用应静态链接，不支持动态链接[5] | 不允许 `import`；不依赖 IAT 顺序 | 设计保证 |
| 11 | QBE label/temp monotonicity | QBE IL 使用 `@label`、`%temp`，无 deterministic flag 文档[1][12] | strict mode 规范化；normal mode 仅验证 `.efi` | **主要风险** |

**推荐的默认配方是 `lld-link`，但 v2.0 无需在首日迁移整个工具链。** lld-link 的 `/Brepro` 会将基于内容派生的哈希写入时间戳字段；`/timestamp:<N>` 允许使用固定提交时间，`/pdbpath:none` 可控制 PDB 路径，并可通过 `/Brepro` 消除当前时间源[6][7]。Rust UEFI target 也默认使用 `link`-flavor 的 lld 生成 PE32+，设置 `EFI_APPLICATION` 和 `efi_main`[5]。

因此，建议采用双链接器策略：

| 链接器 | 定位 | 默认 |
|---|---|---|
| `lld-link` | 可重现参考后端 | v2.0 CI 默认 |
| GNU ld via GCC | 兼容性后端 | 保留，但 final release 不必须 |

GNU ld 继续兼容的条件是：

- 固定版本；
- 通过 `--no-insert-timestamp` 清零 `TimeDateStamp`；
- 显式关闭或确定性化 `.build-id`；
- 移除绝对路径；
- 保证 `.reloc`；
- 在 CI 中保留双构建比对。

Debian 文档指出，`--no-insert-timestamp` 对 PE 可执行文件有效，但 DLL 可能与绑定可执行文件发生冲突[11]。由于 EFI 应用不是普通 Windows DLL，v2.0 可以接受该方案；但这属于证据外推，仍需在 MinGW 版本矩阵中实测。

**`SOURCE_DATE_EPOCH` 只能作为统一输入时钟，不能替代链接器确定性。** LLVM 文章将其用于 `clang`/lld 场景[6]；binutils PE timestamp patch 也读取该环境变量[11]。但不同 MinGW/GCC/binutils 版本对它的尊重程度并不一致。jhyy driver 应：

1. 先读取 `SOURCE_DATE_EPOCH`；
2. 再向 GCC 传递 `-D__DATE__= -D__TIME__= -D__TIMESTAMP__=`；
3. 显式选择 `/Brepro`、`--no-insert-timestamp` 或 `/timestamp:`；
4. 禁止“设置环境变量后假定链接器必然确定”的隐式行为。

### 11. 端到端验证：`.efi` 相等必须以双构建和字节定位为 gate

**以下命令属于待 CI 执行的规范脚本，不是 Windows 实测结果。** 脚本设计目的是把“构建成功”“运行成功”和“字节相等”分成三个独立 gate，避免运行通过掩盖链接差异。

#### 11.1 最小 jhyy 源示例

```text
// hello-freestanding.jhyy（设计草案，未在项目树中创建）
#[runtime_start]
fn main_jhyy(handle: EFI_HANDLE, st: &EFI_SYSTEM_TABLE) -> EFI_STATUS {
    let con = unsafe { (*st).con_out };
    unsafe { ((*con).output_string)(con, u"jhyy: hello efi\r\n") };
    EFI_SUCCESS
}
```

实际字段、宽字符字面量和 FFI 类型仍需对接真正的 UEFI 绑定。当前草案只用于展示最小程序结构。

#### 11.2 构建脚本

```bash
#!/usr/bin/env bash
set -euo pipefail
export SOURCE_DATE_EPOCH=1700000000
export TARGET=amd64_win_freestanding
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

jhyy --target=$TARGET -Oz -C reproducible=strict \
     -C linker=lld-link \
     hello-freestanding.jhyy -o "$WORK/hello.efi"

# 建议由 jhyy driver 内部生成的链接参数：
# /SUBSYSTEM:EFI_APPLICATION /ENTRY:_start
# /FIXED:NO /DYNAMICBASE /Brepro /timestamp:$SOURCE_DATE_EPOCH
# /debug:none 或 /pdbpath:none /pdbaltpath:none
# /NODEFAULTLIB /NOIMPLIB /IGNORE:4210,4221
```

采用 GCC/GNU ld 时的关键参数应为：

```text
-mno-red-zone -mgeneral-regs-only -ffreestanding -fno-builtin
-Wl,--no-insert-timestamp,--enable-reloc-section
-Wl,--subsystem,10        # EFI_APPLICATION
-Wl,--entry,_start
-Wl,--disable-auto-import,--no-undefined
```

其中 `--subsystem 10` 必须与链接器 emulation 兼容；具体语法应在真实 binutils 上校验。

#### 11.3 OVMF 运行脚本

```bash
qemu-system-x86_64 \
  -machine q35,accel=tcg \
  -cpu qemu64 \
  -m 512 \
  -drive if=pflash,format=raw,readonly=on,file=OVMF_CODE.fd \
  -drive if=pflash,format=raw,readonly=on,file=OVMF_VARS.fd \
  -drive if=virtio,format=raw,file=fat:rw:espdisk \
  -nographic -serial mon:stdio
```

建议将构建产物放置为：

```text
espdisk/EFI/BOOT/BOOTX64.EFI
```

UEFI 规范定义 `EFI_BOOT_SERVICES.LoadImage()` 将控制权转交给 `AddressOfEntryPoint`；x86_64 使用 RCX、RDX 传递前两个参数[8]。OSDev 资料也记录了 OVMF 使用 FAT 文件系统和 `EFI/BOOT` 的通用布局[16]。本报告未执行 QEMU/OVMF 测试，因此上述命令属于待验证脚本。

#### 11.4 双构建与字节定位

```bash
mkdir -p build-a build-b
SRC_TREE=/abs/path/to/source \
  bash build.sh "$SRC_TREE" build-a/kernel.efi
SRC_TREE=/abs/path/to/source \
  env -i PATH="$PATH" SOURCE_DATE_EPOCH=1700000000 \
  bash build.sh "$SRC_TREE" build-b/kernel.efi

sha256sum build-a/kernel.efi build-b/kernel.efi
diff -r build-a build-b || true
llvm-readobj --file-headers --sections --relocations build-a/kernel.efi > a.txt
llvm-readobj --file-headers --sections --relocations build-b/kernel.efi > b.txt
diff -u a.txt b.txt || true
radiff2 build-a/kernel.efi build-b/kernel.efi
```

验证标准建议分为三级：

1. **`.efi`：全部 byte-equal。**
2. **`.il` / `.s`：normal mode 只要求语义等价；strict mode 才要求 byte-equal。**
3. **`.o`：允许存在路径差异，因为尚未经过最终链接。**

若 `sha256` 不同，应按以下顺序定位：

- PE header；
- Debug Directory；
- `.build-id`；
- `.text`；
- `.data`；
- `.reloc`；
- 节间 padding；
- 符号字符串表；
- QBE label/temporary 差异。

这种分层可以快速区分“链接器时间戳问题”“节布局问题”和“代码生成顺序问题”，避免反复修改单个 flag 却无法判断根因。

### 12. CI gate 设计：把可重现性变成可执行断言

**D26 应保留，但验收措辞必须从“工具 flag 列表”升级为“产物属性 + 诊断流程”。** 建议 v2.0 CI 运行两次完全独立的构建，分别使用：

- `linker=gnu_ld`，验证兼容性；
- `linker=lld_link`，验证可重现性。

最终 release artifact gate 使用 `lld-link`。每次差异必须报告：

- 首个不同字节；
- 所属 PE section；
- RVA；
- 文件偏移；
- 差异字节数；
- 对应 `.il`/`.s` diff；
- 工具版本与输入顺序。

`dumpbin /headers` 的等价物建议使用：

```bash
llvm-readobj --file-headers --coff-file-headers --optional-header --sections
```

并对照：

- `Machine = 0x8664`；
- `Subsystem = EFI_APPLICATION (10)`；
- `TimeDateStamp`；
- `BaseOfCode`；
- `SizeOfImage`；
- `.reloc`；
- Debug Directory。

Microsoft 规范明确列出 `IMAGE_SUBSYSTEM_EFI_APPLICATION = 10`[9]，因此子系统值不应依赖 OVMF 运行结果间接猜测。

---

## 第四部分：文档必须消除路线冲突和工具语义错配

### 13. 待修订项：优先处理 D25、runtime 边界和 PE 工具语义

**文档修订的核心不是润色，而是消除“路线图已锁”与“验收措辞自相矛盾”之间的冲突。** 建议按以下优先级处理：

| 优先级 | 位置 | 当前问题 | 建议 |
|---|---|---|---|
| P0 | §16.6 完成定义 | 要求 self-host QBE，与 D25 冲突 | 按 D25 改写为“使用 QBE + GCC，但 QBE 被锁定且可替换” |
| P0 | §5.1.7 | 使用 ELF 导向的 `.exe byte-equal` 兜底 | 改为 PE/COFF 字段控制和双链接器策略 |
| P0 | §16.6 step 4 | 忽略 runtime 与 SysV/Win64 边界 | 补齐 crt0、builtins、入口、链接脚本 |
| P1 | §3 决策 2/3 | “不 link libc”与 `#[no_std]` 边界不清 | 拆分为 env、capability、start contract |
| P1 | §16.7 | 把自写 QBE 与移除 QBE 绑在一起 | 改为 backend matrix 与 rollout gate |
| P1 | ABI §3.1、§13 | 只描述 hosted MS x64 | 增加 target/os/env 表和 freestanding exception |
| P2 | W-001~W-009 | 未声明 target 适用范围 | 增加 `applies_to = [MsX64]` |

修订原则如下：

- P0 项解决正确性和路线图冲突，应在编码前合并；
- P1 项可在 MVS 实施过程中同步；
- P2 项用于避免后续 workaround 被错误复用到 SysV。

所有涉及“QBE 原生支持”的表述，都应明确指的是 **QBE IL backend target**，而不是完整的 Windows 工具链。

### 14. 修订建议 diff

**Diff A：§5.1 验收标准第 7 条——将 ELF flag 改为 PE/COFF 策略。**

```diff
- 7. byte-equal 三件套（.il + .s + .exe），`.exe byte-equal` 兜底
-    `gcc -g0 + strip + SOURCE_DATE_EPOCH + --build-id=none`
+ 7. 可重现构建（D26）：默认采用 `lld-link` 参考链接器，以最终 `.efi` 的
+    byte-equal 为一等完成定义；`.il`/`.s` byte-equal 为 strict 诊断项，不作为
+    release 阻塞条件。PE/COFF 必须确定性控制：
+      - COFF/OBJ `TimeDateStamp`：固定 `SOURCE_DATE_EPOCH`，或 `/Brepro`、
+        `/timestamp:<N>`、GNU ld `--no-insert-timestamp`；
+      - 调试信息：`/debug:none`，或 `/pdbpath:none` + 固定 CodeView GUID/Age，
+        禁止绝对构建路径；
+      - 布局：保留 `.reloc`，固定节顺序、对象文件顺序、节对齐与填充；
+      - 编译宏：`-D__DATE__= -D__TIME__= -D__TIMESTAMP__=`；
+      - QBE IL：label、临时名和块顺序必须稳定，或仅以 `.efi` 作为 gate。
+    `--build-id=none` 不是 PE/COFF 通用兜底：GNU ld 的 PE/COFF 实现会写入
+    CodeView `.build-id` 并由 Debug Directory 引用。仅当显式选择
+    `.build-id=none` 且无其他调试标识需求时使用；否则由链接器生成确定性
+    build-id 或完全禁用调试目录。
+    验证：两次独立构建后 `sha256sum` 相等；若不等，使用
+    `llvm-readobj`/`radiff2` 定位到 PE header、节、`.reloc`、符号或 QBE IL。
```

**Diff B：§5.1 验收标准第 6 条——明确“依赖”的含义。**

```diff
- 6. QBE 工具链不依赖（用 QBE 仍是 OK，只是不阻塞 OS）
+ 6. QBE 不是最终产品依赖（D25）：v2.0 允许并推荐使用锁定的 QBE + MinGW GCC
+    实现 `amd64_win` 与 `amd64_win_freestanding`。完成定义是“可替换”，而非
+    “当前未使用”：
+      - `toolchain/qbe.lock` 锁定 commit；
+      - 自有 ABI/Runtime conformance tests；
+      - 提供 `amd64_sysv*` 或自写后端后，才可移除 QBE。
+    禁止在 `.efi` 关键路径上依赖未锁定、未测试的 QBE 构建。
```

**Diff C：§16.6 第 4 步——删除 self-host QBE，补入 runtime。**

```diff
- 测试：jhyy 编 hello-freestanding.jhyy → kernel.efi → OVMF 跑通 printk
- （用 v3.0 sprint 3a-3f 之前，只用 QBE IL 标准 emit + no libc link 即可）
- 完成定义：「jhyy --target=amd64_win_freestanding hello.jhyy -o hello.efi」
- 成功 + hello.efi 在 OVMF 跑通 + 不依赖 QBE 二进制（已 self-host）
+ 测试：jhyy 编 hello-freestanding.jhyy → .il → .s → .o → kernel.efi
+ → OVMF 跑通 printk。仅依赖 QBE IL 标准 emit + 不链接 libc；UEFI runtime
+ 由 jhyy runtime `crt0` + builtins + panic 提供。printk 所需能力允许
+ 直接使用内部 FFI，不要求先稳定 `#[no_std]` / `#[link_section]` /
+ `#[naked]` / `asm!`。
+ 完成定义（v2.0，与 D25 一致）：
+   1. `--target=amd64_win_freestanding` 成功生成 PE32+ `kernel.efi`；
+   2. Subsystem = EFI_APPLICATION，含 `.reloc`，入口 `_start`/Win64 ABI；
+   3. QEMU + OVMF 启动并输出预期 printk；
+   4. 使用锁定 QBE + MinGW GCC（QBE 是工具链实现细节，不是产品依赖）；
+   5. 两次独立构建的 `.efi` byte-equal；`.il`/`.s` strict 差异可豁免，但必须附诊断；
+   6. 不链接 libc，不引用 hosted `runtime.c` 的 libc 路径。
```

**Diff D：§3 决策 3——拆分 freestanding、no_std 和 startup capability。**

```diff
- v2.0 freestanding 不依赖 `#[no_std]` crate attr（只需“不 link libc”）；
- `#[no_std]` 跟 v3.0 sprint 3d 联动。
+ 决策 3（拆分）：
+   - `env.freestanding`：由 `--target=*_freestanding` 隐式设定，禁止链接 libc；
+     这是 v2.0 的构建/链接契约。
+   - `#[no_std]`：控制语言能力边界，仍按 v3.0 sprint 3d 稳定；v2.0 不得要求用户
+     写出该属性即可启动。
+   - startup contract：v2.0 通过 `#[runtime_start]` 或内置 runtime 提供
+     `efi_main`、crt0、BSS、`panic_handler`；`#[link_section]`、`#[naked]`、
+     `asm!` 按 v3.0 3a–3f 的门控引入，不在 MVS 中阻塞。
+   - ABI：`amd64_win_freestanding` 使用 Win64/MS x64；`amd64_sysv*` 是 v2.x 后端
+     责任，不共享 UEFI 入口 ABI。
```

**Diff E：§16.7——拆分自写 backend、QBE 移除和链接器迁移。**

```diff
- 自写 QBE 后端、移除 QBE 工具链；`.exe byte-equal` 兜底沿用 §5.1。
+ v2.x backend 演进：
+   - 先落地 `amd64_sysv` 自写 IL→.s，再增加 `amd64_sysv_freestanding`；
+     `amd64_win*` 在 v2.x 中期前继续由锁定 QBE 支持。
+   - 仅在自写 backend 通过现有 ABI/Runtime/Repro conformance tests，
+     并且 `amd64_win` 与 `amd64_win_freestanding` 均可替代时，才移除 QBE。
+   - 链接器策略独立演进：v2.0 起 `lld-link` 为 reproducible reference backend，
+     GNU ld 为兼容性后端；移除 QBE 不要求同时迁移链接器，迁移链接器也不要求
+     先自写 backend。
```

**Diff F：ABI §3.1——从单一 MS x64 描述升级为目标矩阵。**

```diff
- 当前 ABI：MS x64（RCX/RDX/R8/R9，sret via hidden pointer）。
+ 当前 hosted ABI：`amd64_win`，MS x64；前四个整数参数 RCX/RDX/R8/R9，
+ sret via hidden pointer；所有 `W-001~W-009` 默认适用。
+ 新增 target 分派规则（§13）：
+   - `amd64_win_freestanding`：复用 MS x64 calling convention、sret 和 QBE
+     `-t amd64_win`；仅切换 env/runtime/linker，不切换 ABI。
+   - `amd64_sysv`、`amd64_sysv_freestanding`：RDI/RSI/RDX/RCX/R8/R9；v2.x 自写
+     后端负责，不影响 v2.0。
+   - UEFI 入口：`extern "efiapi" fn(ImageHandle, &SystemTable)`，x86_64 由固件
+     以 RCX/RDX 调用；crt0 负责栈/BSS/参数透传。
```

### 15. 兼容性检查：既有 byte-equal 与 W 系列 workaround 必须受 target 约束

**新门禁不能破坏既有 Windows 自举闭环。** 建议在 CI 中并行运行：

- `amd64_win` 的 stage 2 byte-equal 基线；
- `amd64_win_freestanding` 的 repro gate。

新增 target registry 后，应增加：

- canonical triple 反序列化快照测试；
- 未知 target 错误快照；
- 每个调用约定的参数/返回 struct/大对象 sret 测试；
- 现有 W 系列 workaround 的 `applies_to` 元数据。

W 系列建议扩展为：

```text
W-001..W-009 : MsX64        # 现有 Windows hosted
W-010..W-019 : MsX64Freestanding  # UEFI 启动、red-zone、reloc、PDB
W-020..W-029 : SysVX64       # v2.x
```

这样可以防止 SysV 后端误继承仅适用于 MS x64 的栈、struct 或 shadow-space 行为。

建议以现有 `v3.x-capability-spec.md` 的“修订清单”格式集中维护以下字段：

| 字段 | 内容 |
|---|---|
| 修订编号 | 例如 REV-001 |
| 位置 | 文件、章节、行号区间 |
| 当前措辞 | 原始文档内容 |
| 建议措辞 | 替换文本 |
| 依据 | QBE 提交、PE/COFF 规范、Rust target、实测或设计判断 |
| 状态 | proposed / approved / applied |
| 破坏面 | hosted、freestanding、backend、linker、repro |

---

## 第五部分：最大风险不是 QBE 缺失，而是边界错配

### 16. 风险排序：按“定错代价”管理

**最高风险来自 ABI、runtime 和链接格式之间的边界错配，而不是 QBE 是否支持 Windows。** 一旦发生，修复成本会从链接参数扩散到 codegen、语言属性和操作系统仓库。

| # | 风险 | 触发条件 | 定错代价 | 早期信号 | 缓解措施 |
|---|---|---|---|---|---|
| R1 | UEFI 误用 SysV 入口 | 将 `efi_main` 定义为普通 SysV `extern "C"` | 架构级，运行时崩溃 | OVMF 启动即异常 | `extern "efiapi"`、`abi.ms_x64`、ABI conformance test |
| R2 | 误信“QBE 原生 Windows” | 将上游 ABI 提交理解为完整工具链 | v2.x 路线图重写 | TLS/long 假设、libgcc 隐式依赖 | 锁定提交、完整 libgcc/链接清单、双工具链测试 |
| R3 | GNU ld PE 非确定 | 仅依赖 `strip` 或 `--build-id=none` | release 不可复现 | SHA 抖动、Debug Directory 差异 | lld-link 为默认；GNU ld 固定版本和参数矩阵 |
| R4 | `.reloc`/ImageBase 错误 | `-Wl,--enable-reloc-section` 被遗漏 | 固件加载失败 | 换固件或地址后崩溃 | 保留 `.reloc`、OVMF 多地址测试、`/DYNAMICBASE` |
| R5 | QBE IL 标签漂移 | normal gate 设为 strict | CI 不稳定 | v1.2.1 类似 7 行漂移 | IL 规范化、`.efi`-only release gate |
| R6 | crt0/BSS/栈错误 | 复用 hosted runtime 或省略清零 | 早期内存损坏 | 打印前崩溃、随机异常 | 显式 crt0、`memset_zero`、栈对齐断言 |
| R7 | SSE/中断破坏 | 默认启用 SSE 或依赖 red-zone | 固件相关崩溃 | 首次中断后状态错误 | `-mno-red-zone -mgeneral-regs-only -msoft-float` |
| R8 | `#[no_std]` 成为 M1 阻塞 | 把 runtime 拆分与语言属性绑定 | 路线循环依赖 | M1 无法启动 | `#[runtime_start]` + FFI MVS |
| R9 | Capability ABI 过早耦合 | v2.0 实现完整 capability invoke | 后续 ABI 变更 | runtime 复杂度激增 | 8 字节布局先行、M2+ 再接入 invoke |
| R10 | 工具版本矩阵失控 | `SOURCE_DATE_EPOCH` 行为跨版本变化 | 无法解释差异 | 同命令跨机器结果不同 | 锁 GCC/binutils/lld/QBE；版本声明测试 |

**R1、R2、R3 应作为 v2.0 的设计评审闸门。**

- R1 一旦定错，runtime 和 FFI 均无法正确启动；
- R2 一旦定错，整个“v2.0 快速路径”会失效，QBE 自写后端可能被迫提前；
- R3 一旦定错，D26 的 OS 镜像可重现目标无法落地。

R4–R7 可在 sprint 内通过测试发现；R8–R10 则属于项目管理风险，应通过显式切片和工具锁定规避。

### 17. 决策立场：维持 D25/D26，但必须修订验收措辞

**建议明确维持 D25 和 D26，同时要求相应文档立即修订。** 依据如下：

- QBE 已具备 `amd64_win` 后端，且 v2.0 freestanding 可复用同一 MS x64 ABI[1]；
- D25 允许 QBE + GCC；
- Rust UEFI 实践表明，PE32+、EFI_APPLICATION、可重定位和 lld 均可形成工程闭环[5]；
- PE/COFF 的关键非确定字段均有可控配置[6][9][11]。

因此，D25/D26 的战略方向正确，问题在于现有验收文本仍沿用 ELF 概念，并在完成定义中提前要求 QBE self-host，与 D25 冲突。

修订优先级为：

1. **立即修订：** §16.6 完成定义、§5.1.7、§3 决策 3；
2. **与实现同步修订：** runtime 包边界、target registry、ABI §13；
3. **v2.x 再处理：** SysV backend、QBE 移除、完整 `#[no_std]`。

最终应使文档状态满足：

> 架构决策、验收标准、runtime 边界和链接器配方彼此一致。

---

## 结论：v2.0 的正确路径是复用 MS x64，把新增复杂度压在 runtime 与链接层

**jhyy v2.0 最有胜率的路径，不是同时引入 SysV、no_std、自写 backend 和 reproducible linker，而是严格复用已有 `amd64_win` 的 MS x64 代码路径，只新增 freestanding runtime、PE/COFF 链接契约与可重现门禁。**

这一路径成立需要同时满足五个前提：

1. QBE 上游已提交 `amd64_win`，并经过项目自带 ABI 测试验证[1]；
2. UEFI x86_64 使用 Win64/MS x64，入口参数为 RCX、RDX，映像子系统为 `EFI_APPLICATION`，且必须可重定位[4][5][8]；
3. PE/COFF 时间戳、调试标识、节布局、重定位和代码生成顺序均受显式控制[6][9]；
4. runtime 边界明确区分 `env.freestanding`、`#[no_std]` 和 startup contract；
5. `.efi` 可重现成为 CI 硬门，`.il`/`.s` 抖动只触发诊断。

在这组前提下，v2.0 可以成为稳定跳板：后续只需扩展 `ABIKey`、`TargetSpec` 和 linker driver，即可增加 SysV 与自写 backend，而不会回过头重写 UEFI 启动路径。

反之，若在 v2.0 中把 UEFI 入口改为 SysV、把 QBE 移除设为完成条件、继续让 hosted `runtime.c` 隐式参与 freestanding 构建，或继续将 `--build-id=none` 作为 PE 兜底，就会在 codegen、runtime、链接和验收四个层面同时制造技术债。上述风险均可在编码前通过本报告建议的文档修订消除。

---

## 数据来源

[1] **QBE — Implementation of Windows amd64_win target**  
https://c9x.me/git/qbe.git/commit?id=d166a61141ceb6936447c57f730c3c6d78791a1d

[2] **QBE commit d166a61141ceb6936447c57f730c3c6d78791a1d（fetch 抓取页）**  
https://c9x.me/git/qbe.git/commit?id=d166a61141ceb6936447c57f730c3c6d78791a1d

[3] **QBE 源码仓库**  
https://c9x.me/git/qbe.git

[4] **rustc_target：x86_64-unknown-uefi target 定义**  
https://doc.rust-lang.org/nightly/nightly-rustc/src/rustc_target/spec/targets/x86_64_unknown_uefi.rs.html

[5] **Rust Platform Support：unknown-uefi**  
https://doc.rust-lang.org/doc/rustc/platform-support/unknown-uefi.html

[6] **Deterministic Builds with Clang and LLD**  
https://blog.llvm.org/2019/11/deterministic-builds-with-clang-and-lld.html

[7] **[lld] r332613 - [COFF] Add /Brepro and /TIMESTAMP options**  
https://lists.llvm.org/pipermail/llvm-commits/Week-of-Mon-20180514/552858.html

[8] **UEFI Specification, Version 2.11, Chapter 2**  
https://uefi.org/specs/UEFI/2.11/02_Overview.html

[9] **Microsoft PE Format**  
https://learn.microsoft.com/en-us/windows/win32/debug/pe-format

[10] **[PATCH 4/4] Add ld --build-id support for PE/COFF**  
https://sourceware.org/ml/binutils/2014-January/083918.html

[11] **Debian Wiki：ReproducibleBuilds/TimestampsInPEBinaries**  
https://wiki.debian.org/ReproducibleBuilds/TimestampsInPEBinaries

[12] **QBE Intermediate Language（IL）结构说明**  
https://deepwiki.com/8l/qbe/2-qbe-intermediate-language-(il)

[13] **OSDev Wiki：UEFI Bare Bones（修订版本）**  
https://wiki.osdev.org/index.php?diff=24586

[14] **PE/COFF Specification Addendum：Deterministic PE/COFF File**  
https://github.com/dotnet/runtime/blob/main/docs/design/specs/PE-COFF.md

[15] **The Old New Thing：Why are the module timestamps in Windows 10 so nonsensical?**  
https://devblogs.microsoft.com/oldnewthing/20180103-00/?p=97705/

[16] **OSDev Wiki：UEFI 启动与 FAT 文件系统布局**  
https://wiki.osdev.org/index.php?diff=24586

[17] **QBE — Compact SSA Compiler Backend for Hobby Languages**  
https://lwn.net/Articles/1080519/

[18] **Build System Configuration：setup_var.efi（DeepWiki）**  
https://deepwiki.com/datasone/setup_var.efi/4.2-build-system-configuration

[19] **Microsoft Support 首页（检索入口，未用于承重结论）**  
https://support.microsoft.com/en-us?ICID=US_CPProBizSnap12_PDP_FAQ12

[20] **QBE — Compact SSA Compiler Backend for Hobby Languages（hivebook）**  
https://hivebook.wiki/wiki/qbe-compact-ssa-compiler-backend-for-hobby-languages

[21] **ld(1) 手册**  
https://www.linux.org/docs/man1/ld.html

[22] **Build System Configuration：setup_var.efi（DeepWiki，重复检索结果）**  
https://deepwiki.com/datasone/setup_var.efi/4.2-build-system-configuration