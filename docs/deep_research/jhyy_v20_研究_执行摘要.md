# jhyy v2.0 研究：执行摘要

> 完整研究：见 `jhyy_v2.0_多目标与可重现构建研究.md`（5 部分 + 修订 diff + 风险表）
> 本报告只回答一件事：**v2.0 现在就该改什么，以及要不要改 D25/D26。**

---

## 一句话结论

**D25/D26 的战略方向正确，不需要推翻；但 `v2.0.0-os-prep.md` 里有 4 处验收措辞与 D25 自相矛盾或混用 ELF 概念，必须在 v2.0 写第一行 code 之前修订。** 否则编码到一半会发现「完成定义」要求的东西（QBE self-host、QBE 工具链不依赖）跟决策 D25（走 QBE+GCC）根本互斥。

---

## 五个关键发现

| # | 发现 | 定错代价 | 结论 |
|---|------|---------|------|
| 1 | **QBE 上游已提交 `amd64_win`**（commit `d166a61`，明确写"允许 QBE 生成适用于 Windows 的正确汇编"），但**未把 QBE 移植为原生 Windows 程序**；已知限制含不支持 TLS、`C long` 与 QBE `l` 语义差异 | 🔴 极高（v2.0 快速路径失效） | ✅ 维持 D25：v2.0 走 QBE+GCC 低风险，但**必须锁定 QBE 源码提交**，禁止把"可生成 Windows 汇编"误解为"完整 Windows 工具链" |
| 2 | **§ 16.6 完成定义写"不依赖 QBE 二进制(已 self-host)"，与 D25「QBE 自写推到 v2.x 中期」直接冲突** | 🔴 极高 | 应删除该完成条件，改为"QBE 可生成 Windows 汇编即可，移除 QBE 是 v2.x 目标" |
| 3 | **`--build-id=none` 不是 PE/COFF 的时间戳修复器**：binutils 的 PE/COFF 后端会生成含 CodeView 记录的 `.build-id` 并挂到 Debug Directory（sourceware 2014 年补丁可证） | 🟠 高（release 不可复现） | D26 的兜底措辞要改：**默认推荐 `lld-link`（`/Brepro` + `/pdbpath:none` + `/debug:none`），GNU ld 为兼容后端**，而非无条件附加 `--build-id=none` |
| 4 | **UEFI x86_64 复用 Win64 ABI，不是 SysV**：`efi_main(ImageHandle, SystemTable)` 由固件以 **RCX、RDX** 调用，子系统 `EFI_APPLICATION`，映像**必须可重定位**（Rust `x86_64-unknown-uefi` 设 `entry_abi = Win64` 为证） | 🔴 架构级 | `amd64_win_freestanding` 与 `amd64_win` **共用 MS x64 后端**，只切换 env/runtime/linker；**绝不能为 UEFI 插入 SysV 特例** |
| 5 | **最小 runtime 契约必须成为 v2.0 一等交付物**，拆分 `crt0` + `core`(builtins) + `panic/abort` + 可选 arena；入口顺序 `_start → 固定栈/保存固件参数 → 零 BSS → 调 efi_main`；**不得复用 `compiler/runtime/runtime.c` 的 libc 路径** | 🟠 高 | 与 `#[no_std]`（v3.0 3d）**解耦**：用 `#[runtime_start]` + FFI MVS，避免 M1 阻塞在语言属性上 |

---

## 9 项文档修订（按优先级）

### 立即修订（v2.0 编码前，正确性/路线图冲突）

**① § 16.6 完成定义** — 删除"不依赖 QBE 二进制(已 self-host)"，改为"QBE 可生成 Windows 汇编；self-host 移除是 v2.x 目标"

**② § 5.1 第 6 条** — "QBE 工具链不依赖" → "QBE 工具链**仍可用**（per D25），只是不阻塞 OS 启动；移除 QBE = v2.x 完成定义"

**③ § 5.1 第 7 条** — `.exe byte-equal` 兜底从 `gcc -g0 + strip + SOURCE_DATE_EPOCH + --build-id=none` → **默认 `lld-link` 配方**：`/Brepro` + `/timestamp:0` + `/pdbpath:none` + `/debug:none`，固定 `ImageBase`；GNU ld 保留为兼容后端（需 `--no-insert-timestamp` + deterministic PDB）

**④ § 3 决策 3** — 补一句："v2.0 的 `hello-freestanding.jhyy` **不依赖 `#[no_std]` crate attr**（per 原决策），runtime 由 crt0 + builtins 显式提供，与 v3.0 sprint 3d 解耦"

### 与实现同步修订

**⑤ runtime 包边界**（新增 `compiler/runtime/freestanding/`：crt0.asm / builtins.c / panic.c）+ **⑥ target registry**（`targets/*.toml`，未知 triple 快速失败）+ **⑦ ABI § 13**（多 target 矩阵 + freestanding + Cap\<T\> wire + Debug ABI，§ 12 版本历史不动）

### v2.x 再处理

**⑧ SysV backend** + **⑨ 完整 `#[no_std]`**

---

## 最大风险排序（定错代价）

| # | 风险 | 早期信号 | 闸门 |
|---|------|---------|------|
| **R1** | UEFI 误用 SysV 入口（`efi_main` 写成普通 `extern "C"`） | OVMF 启动即崩 | `extern "efiapi"` + `abi.ms_x64` + ABI conformance test |
| **R2** | 误信"QBE 原生 Windows"（TLS/`long` 假设、隐式 libgcc 依赖） | 链接期 libgcc 缺失 | 锁定 QBE 提交 + 完整 libgcc/链接清单 + 双工具链测试 |
| **R3** | GNU ld PE 非确定（仅靠 `strip`/`--build-id=none`） | SHA 抖动、Debug Directory 差异 | lld-link 默认 + GNU ld 参数矩阵 |
| R4 | `.reloc`/ImageBase 错（遗漏 `--enable-reloc-section`） | 换固件/地址后崩 | 保留 `.reloc` + OVMF 多地址测试 + `/DYNAMICBASE` |
| R5 | QBE IL label 漂移（normal gate = strict） | v1.2.1 式 7 行漂移 | IL 规范化，`.efi`-only release gate |
| R6 | crt0/BSS/栈错（复用 hosted runtime） | 打印前崩 | 显式 crt0 + `memset_zero` + 栈对齐断言 |
| R7 | SSE/red-zone 破坏 | 首次中断后状态错 | `-mno-red-zone -mgeneral-regs-only -msoft-float` |
| R8 | `#[no_std]` 成 M1 阻塞 | M1 无法启动 | `#[runtime_start]` + FFI MVS（已含在④） |

**R1/R2/R3 应作为 v2.0 设计评审硬闸门**——这三个一旦定错，修复成本从链接参数扩散到 codegen、语言属性、OS repo。

---

## 建议的下一步动作（按顺序）

1. **先改文档**（本次研究直接产出修订 diff，可直接 apply）：§ 16.6 + § 5.1.6/7 + § 3 决策 3 → 消除与 D25 的矛盾
2. **锁工具版本**：GCC / binutils / lld / QBE 提交号写入 `build.md`，加版本声明测试
3. **搭 repro 验证环境**：按研究报告的实测脚本跑两次独立构建，`radiff2` 定位差异段，确认 lld-link 配方确实 byte-equal
4. **再写 code**：target registry → `TargetSpec` → codegen dispatcher（仅新增配置 + runtime，不重写既有 codegen）→ crt0 + builtins → `hello.efi` 跑 OVMF
5. **CI 双跑**：`amd64_win` 的 stage 2 byte-equal 基线 **+** `amd64_win_freestanding` 的 repro gate，W-001~W-009 加 `applies_to: MsX64` 元数据防 SysV 后端误继承

---

## 参考来源（承重结论的一手依据）

- QBE `amd64_win` 提交：`c9x.me/git/qbe.git/commit?id=d166a61`
- Rust `x86_64-unknown-uefi` target 定义（含 `entry_abi = Win64`、`-mmx,-sse,+soft-float`）
- UEFI Spec 2.11 Ch.2（`uefi.org`）
- Microsoft PE Format（`learn.microsoft.com`）
- LLVM Blog 2019/11 "Deterministic Builds with Clang and LLD"（`/Brepro` + `/TIMESTAMP`）
- Debian Wiki `ReproducibleBuilds/TimestampsInPEBinaries`
- binutils 2014-01 `--build-id` for PE/COFF 补丁（`sourceware.org`）
- .NET runtime `PE-COFF.md` Deterministic PE/COFF File 附录

> 完整论证、TargetSpec 数据结构、CLI 契约、链接配方、实测脚本、逐条 diff 与风险表 → `jhyy_v2_0_多目标与可重现构建研究.md`
