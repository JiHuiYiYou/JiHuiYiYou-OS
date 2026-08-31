# docs/deep_research/ — 研究索引

> 8 份深度研究的角色分类 + 实现参考标注 + 时间线锚点。
> 不重复原文结论；不修改 v0.0.0-v0.0.4 doc；只登记引用方向。

## 0. 元约定

### 角色 5 类

- **机制设计**：提出具体技术方案（代码路径 / 数据结构 / 接口 / 数据流）。
- **机制审查**：第三方审计 / 可证伪假设 / 外部基线对比 —— **不构成设计结论**。
- **排期修订**：调整 milestone 依赖关系 / 时间线 / 实施切片。
- **执行摘要**：依附同源研究的决策切片；自身不构成独立 design。
- **协议规范**：基于机制设计的研究,落盘为可机器检查的 spec 草案;含决策清单、IDL / 状态机 / 错误模型。

### 实现参考维度

- **论证密度**：具体数字、sprint 编号、byte-equal gate、修订 diff。
- **工程化**：寄存器编号、wire format、CI 命令、可机器检查的验收。
- **方法论**：可证伪假设、对照实验、验证矩阵、风险分级。
- **概念完整**：状态机、所有权链、权限分层 —— 但缺乏实测数据。

### 状态字段

- `成熟草案`：内容完整、论据充分、作者已自审，但未走 v0.0.x spec 评审闭环。
- `评审中`：已被某 spec 修订项引用，等评审闭环。
- `已并入`：内容已合并到 v0.0.x spec，本文件仅保留历史。
- `已弃`：内容已被替代，本文件作为档案。

### 引用图例

- `→` 仅引用
- `⇒` 提出修订建议
- `⇔` 双向冲突 / 张力

---

## 1. 文件登记表

| # | 文件 | 角色 | 实现参考维度 | 创建日 | 字符数 | 关键引用 | 状态 |
|---|---|---|---|---|---|---|---|
| 1 | [M8d_M12_排期修订.md](M8d_M12_排期修订.md) | 排期修订 | — | 2026-08-26 | 1420 | `jhyy_gui_subsystem.md` §9/§12;`coordination.md`(待更新) | 成熟草案 |
| 2 | [jhyy_v20_研究_执行摘要.md](jhyy_v20_研究_执行摘要.md) | 执行摘要 | — | 2026-08-26 | 4694 | 多目标构建研究(自身依附) | 成熟草案 |
| 3 | [jhyy_v20_多目标与可重现构建研究.md](jhyy_v20_多目标与可重现构建研究.md) | 机制设计 | 论证密度高 | 2026-08-26 | 34951 | `v0.0.1-syscall-abi.md`、`v0.0.2-foundation-revision.md` | 成熟草案 |
| 4 | [syscallABI边界与寄存器约定研究.md](syscallABI边界与寄存器约定研究.md) | 机制设计 | 工程化高 | 2026-08-26 | 27926 | `v0.0.1-syscall-abi.md` §1.1.2-4;`v0.0.1-process-model.md` §2.1 | 成熟草案 |
| 5 | [jhyy_gui_subsystem.md](jhyy_gui_subsystem.md) | 机制设计 | 概念完整 | 2026-08-26 | 28731 | `v0.0.1-capability.md`、`v0.0.1-syscall-abi.md`、`v0.0.4-gui-explorations.md` | 成熟草案 |
| 6 | [result.md](result.md) | 机制设计 | 方法论强 + 论证密度高 | 2026-08-26 | 33679 | `v0.0.1-capability.md` §1;`v3.x-capability-spec.md` §8 | 成熟草案 |
| 7 | [jhyy_OS有效性评估与架构分析.md](jhyy_OS有效性评估与架构分析.md) | **机制审查** | (审计,非设计) | 2026-08-28 | 19050 | `v0.0.0-design.md`、`jhyy_gui_subsystem.md`(被审)、`result.md` | 成熟草案 |
| 8 | [报告§11§12决策与拍板流程说明.markdown](报告§11§12决策与拍板流程说明.markdown) | 协议规范初稿 | 决策完整 + IDL / 状态机 / 错误码 | 2026-08-27 | 32228 | `jhyy_gui_subsystem.md` §11/§12;`v3.x-capability-spec.md` §4.1;`coordination.md` D-GUI 系列 | 评审中 |

字符数按 `wc -m`（含空格与中文标点）；创建日按文件系统 mtime。

---

## 2. 单文件登记

### §2.1 M8d_M12_排期修订.md

- **路径**：`docs/deep_research/M8d_M12_排期修订.md`
- **元信息**：创建日 2026-08-26 / 字符数 1420 / 状态：成熟草案
- **角色**：排期修订
- **核心论点摘要**：M8d 必须后移到 sprint 3g / 3i / 3j 后；M12 从「工具包功能集」重定义为「策略合规后的安全 API 稳定集」；4 阻塞项全落在语言/内核层。
- **本文引用了**：`jhyy_gui_subsystem.md` §9、§12
- **本文建议修订 ⇒**：`coordination.md` §0 Critical Path（M5b → M8d 链待更新）；`v0.0.4-gui-explorations.md`（M8d 时机）
- **阻塞项**：末尾 4 个 `[ ]` 复选框未勾选 —— 本文不替作者决定
- **已知悬而未决**：4 项均未勾选(per 原文 § 五)

### §2.2 jhyy_v20_研究_执行摘要.md

- **路径**：`docs/deep_research/jhyy_v20_研究_执行摘要.md`
- **元信息**：创建日 2026-08-26 / 字符数 4694 / 状态：成熟草案(依附)
- **角色**：执行摘要
- **核心论点摘要**：D25/D26 战略方向正确，但 4 处验收措辞与 D25 自相矛盾；9 项文档修订分 3 优先级；R1/R2/R3 是 v2.0 设计评审硬闸门。
- **本文引用了**：完整研究见 `jhyy_v20_多目标与可重现构建研究.md`（原文自身标注）
- **本文建议修订 ⇒**：`v2.0.0-os-prep.md` §16.6、§5.1.6/7、§3 决策 3
- **阻塞项**：完整研究未走 spec 评审闭环；9 项修订 diff 待 apply
- **已知悬而未决**：5 项关键发现中的「QBE 原生 Windows」边界（per R2）

### §2.3 jhyy_v20_多目标与可重现构建研究.md

- **路径**：`docs/deep_research/jhyy_v20_多目标与可重现构建研究.md`
- **元信息**：创建日 2026-08-26 / 字符数 34951 / 状态：成熟草案
- **角色**：机制设计
- **实现参考维度**：论证密度高 —— 11 类 PE 字段 + byte-equal gate + 9 项修订 diff + R1-R10 风险表 + OVMF/PE-COFF 双跑脚本
- **核心论点摘要**：v2.0 维持 D25(QBE+GCC)但删 self-host 完成条件；PE/COFF 改用 lld-link 默认 + 双链接器策略；UEFI 必须复用 Win64 ABI；TargetSpec 分层使 freestanding 与 hosted 复用 MS x64 后端。
- **本文引用了**：QBE `amd64_win` commit `d166a61`；Rust `x86_64-unknown-uefi` target；LLVM /Brepro；Microsoft PE Format；Debian ReproducibleBuilds wiki；binutils 2014 `--build-id` 补丁
- **本文建议修订 ⇒**：
  - `v2.0.0-os-prep.md` §16.6（完成定义）、§5.1.6/7（验收）、§3 决策 3（freestanding / no_std 边界）、§16.7（QBE 移除路径）
  - `jhyy-abi-v1.0.0.md` §3.1-3.3 + §13.3（多 target 矩阵）
  - `compiler/build.md`（QBE 锁提交）
- **阻塞项**：无语言/编译器侧硬前置（纯工具链 + 链接 + runtime）
- **已知悬而未决**：
  - `Cap<Shm>` dirty bitmap 编码（per § 9 待定，与 syscall 研究 § 9 待定冲突）
  - QBE IL strict 规范化（`.il` byte-equal 仅作 strict 诊断）
  - GNU ld PE 在不同 MinGW 版本上的行为（per 11 类 PE 字段实测）

### §2.4 syscallABI边界与寄存器约定研究.md

- **路径**：`docs/deep_research/syscallABI边界与寄存器约定研究.md`
- **元信息**：创建日 2026-08-26 / 字符数 27926 / 状态：成熟草案
- **角色**：机制设计
- **实现参考维度**：工程化高 —— 11 寄存器固定角色 + 22 验收用例 + 9 项文档修订清单 + 6 项 D-M3-1~6 决策待升级 + 完整 entry/exit 汇编骨架
- **核心论点摘要**：SYSCALL 硬件破坏 RCX/R11 → 不能用作快速参数；推荐 `arg0..5 = RDI,RSI,RDX,R10,R8,R9` + 4 KiB payload 上限 + `Cap<Shm>` 降级；sret/out/inout 三分类 + AsCursor+epoch+commit-token 用户指针安全链。
- **本文引用了**：Linux `entry_64.S` SYSCALL 注释；Intel SDM Vol.2 SYSCALL/SYSRET；AMD APM Vol.3；DragonFlyBSD `exception.S`；Microsoft x64 ABI；seL4 manual
- **本文建议修订 ⇒**：
  - `v0.0.1-syscall-abi.md` §1.1.2-4 / §1.2 / §1.3（参数编码 / cap 传递 / 超时）
  - `v0.0.1-process-model.md` §2.1（`SavedRegs` → 显式 TCB）、§5.3（cap 生命周期）
  - `v0.0.1-capability.md` §1、§3.3（跨 IPC 改写 + out/inout Cap）
  - `v0.0.2-foundation-revision.md` §3.2 + §4（`Cap<Shm>` + M3 行）
  - `v0.0.1.5-M5b-prereqs.md` §3.1-3.4 + §1（M3 冻结门）
  - `v0.0.4-debug-abi.md` §2.5/§6（SyscallFrame 类型）
  - `jhyy-abi-v1.0.0.md` §3.1-3.3 + §13.1/§13.3（独立 syscall 契约）
  - **新建** `v0.0.5-syscall-abi-registers.md`（本文明确建议）
- **阻塞项**：
  - 当前 OS 团队未审；`v0.0.5-syscall-abi-registers.md` 未建
  - D-M3-1~6 仍标「� 建议升级」，未走 D 锁流程
- **已知悬而未决**：
  - `Cap<Shm>` dirty bitmap 编码（与多目标研究 § 9 待定冲突）
  - SMAP 具体启用条件
  - DebugEvent 在 release build 中的保留级别
  - nested syscall 重入规则

### §2.5 jhyy_gui_subsystem.md

- **路径**：`docs/deep_research/jhyy_gui_subsystem.md`
- **元信息**：创建日 2026-08-26 / 字符数 28731 / 状态：成熟草案
- **角色**：机制设计
- **实现参考维度**：概念完整 —— Surface 6 态状态机 + 三账本 ID ledger + IDL 草案 + revoke 4 阶段窗口 + 8 维度验收表
- **核心论点摘要**：方案 c（线性 Cap + 内核共享映射）；`Cap<Shm>` 线性但映射共享；commit_seq 同步代替「当前指针」；Seat 单所有者 + focus_epoch 防 keylogger；M8d 后移到 3j 后；M12 重定义为「权限/生命周期/确定性三条不变式可机器检查」。
- **本文引用了**：seL4 capabilities & CSpace；Nitpicker (Genode)；Fuchsia View/Flatland；Wayland protocol；smithay/wlroots；Redox Orbital；SerenityOS WindowServer
- **本文建议修订 ⇒**：
  - `v0.0.1-capability.md` §1（8 字节 wire + 跨 IPC 改写）
  - `v0.0.1-syscall-abi.md`（`Cap<Shm>` 描述符 / > 4 KiB 走 SHM）
  - `v0.0.4-gui-explorations.md` §4-§6（GUI 消息含 Cap<Surface> / Wayland-style 协议草案 / 软件 vs GPU）
- **阻塞项**：
  - M8d 必须在 3g/3i/3j 后启动（per 排期修订）
  - 所有性能数字（1080p@60 / 帧预算 / 推导延迟）均为推断，无实测
- **已知悬而未决**：
  - GPU / virtio-gpu 排期（post-M12 触发）
  - 拖放 / data device / HDR / 3D 等扩展项
  - 协议版本号冻结条件

### §2.6 result.md

- **路径**：`docs/deep_research/result.md`
- **元信息**：创建日 2026-08-26 / 字符数 33679 / 状态：成熟草案
- **角色**：机制设计
- **实现参考维度**：方法论强（3 段 sprint + 9 项文档修订 diff + 16 项验收矩阵 B1-B16 + 12 项风险与缓解）；论证密度高（8 字节 layout + 5 层表示 + phantom 算法 + D16 算法 + 12 类确定性 checklist）
- **核心论点摘要**：Cap 安全 = 8 字节值 + 编译期线性约束 + D16 元数据；`_phantom` 在类型/HIR 保留、MIR 零大小、QBE IL 不 emit；`T` 不依赖未来泛型，sema 用 `TypeName + decl_order` 作为类型标签；D16 = 编译器与内核唯一位置契约；3g → 3g.5 → 3g.7 三段顺序强制。
- **本文引用了**：CompCert 编译链正确性；seL4 capabilities & CSpace；CHERI/Morello technical report；Rust PhantomData / `repr(C)` / `#[must_use]`；Reproducible Builds SOURCE_DATE_EPOCH；v0.0.1 capability / syscall / foundation / Debug ABI / v3.x-capability
- **本文建议修订 ⇒**：
  - `v0.0.1-capability.md` §1（layout pass 派生 vs sema 保留 phantom）、§2（linear kill）、§7（规则 3/7 + D16/provenance 映射）
  - `v0.0.4-debug-abi.md` §5/§7（`CapId` 不是 `msg_tag`）
  - `v3.x-capability-spec.md` §8 规则 3/7（改 hardcoded linear）、§Memory layout（padding 节点）
  - `v0.0.1-syscall-abi.md` §1.1.4 D16（IL / 符号语法）
  - `v0.0.2-foundation-revision.md` §3.2（Cap 借用用 3g minimal borrow region）
  - `jhyy-abi-v1.0.0.md` §13（待增 §13.2/§13.3 D16 + Cap layout）
  - `v2.x-qbe-rewrite.md` §5（三张 ID ledger）
- **阻塞项**：
  - sprint 3g 启动前置未解（本身 = 闭环）
  - macro expansion 顺序未稳定（linear check 必须 post-expansion）
  - 跨 crate type id 稳定性延后到 3i
- **已知悬而未决**：
  - `Err<T>` 泛型（sprint 3i，在 3g 之后）→ 3g 不能用，需在 sprint 边界重新审视
  - recursive Cap 聚合（`Option<Cap<T>>` / union）—— 当前禁止
  - Drop / RAII / lifetime subtyping / HRTB（均不实现）

### §2.7 jhyy_OS有效性评估与架构分析.md

- **路径**：`docs/deep_research/jhyy_OS有效性评估与架构分析.md`
- **元信息**：创建日 2026-08-28 / 字符数 19050 / 状态：成熟草案（外部审计）
- **角色**：**机制审查**（不是机制设计）
- **核心论点摘要**：jhyy_OS 三项创新（Cap 编译期原理 / GUI 线性句柄+epoch revoke / Agent Debug ABI）截至 2026-08 = 「**设计可信、实现待证、领先未证**」；8 项可证伪假设 H1-H8 应优先于功能开发固化；Narrow Waivers 比例决定方案成败（1% vs 10-30%）。
- **本文引用了**：seL4 / CHERI/CompartOS / RedLeaf / Theseus / Austral / ChatDBG 等成熟系统的实证数据 + Soft Typing 资料
- **本文审查对象**：`v0.0.0-design.md` §6；`v0.0.1-capability.md`；`jhyy_gui_subsystem.md`；`result.md`
- **本文不构成设计结论**：三类证据等级严格分开（设计声明 / 外部实证 / 研究推断）；jhyy 特有组件均无实测数据，故本文只标「预期量级 / 风险方向」
- **阻塞项**：
  - Narrow Waivers 真实比例未知（1% 还是 10-30%？决定性压力点）
  - H1-H8 八项假设无一项被实测验证
- **已知悬而未决**：
  - 在进入 M1 前应完成的 8 项最低验证门（per § 8.5）
  - 3 个最小可行实验（capability 派生链 / surface 生命周期 / Agent Debug 对照）未启动

### §2.8 报告§11§12决策与拍板流程说明.markdown

- **路径**：`docs/deep_research/报告§11§12决策与拍板流程说明.markdown`
- **元信息**：创建日 2026-08-27 / 字符数 32228 / 状态：评审中
- **角色**：**协议规范初稿**(本类共 1 份)
- **实现参考维度**：决策完整(D-GUI-1 ~ D-GUI-10 决策清单 + ratification gate);协议细节含 topology / wire format / IDL / lifecycle invariants L1-L4 / Shm region ↔ mapping split / 异步 revoke 4 阶段 / seat 策略 / error model / M8d scope & sequencing / acceptance matrix
- **核心论点摘要**：jhyy GUI protocol spec 初稿。capability boundary axiom + 5 类 cap 类型 + linear handle + 8 字节 cnode ref + byte-equal axiom + append-only 版本 + L1-L4 lifecycle invariants + 单 seat 焦点链 epoch 验证 + 8 维验收矩阵
- **本文引用了**：`jhyy_gui_subsystem.md` §11/§12;`v3.x-capability-spec.md` §4.1;`coordination.md` D16
- **本文建议修订 ⇒**：`v3.x-capability-spec.md` §4.1-§4.3 加 `Cap<Shm>` 例外条款;`coordination.md` 加 D-GUI 系列条目;`jhyy-abi-v1.0.0.md` §13 按本协议扩充 cap 类型清单
- **阻塞项**：
  - D-GUI-8/9/10 + §4.2/§7.2/§8 → 🔒 (2026-09-01,见原 doc §13 revision history)
  - 当前 draft 形式存在 `docs/deep_research/`,未独立为 `docs/design/gui_protocol.md`
- **已知悬而未决**：
  - wire representation(8 字节 layout + rights encoding + epoch presence 是否进 cap);sprint 3i 落地
  - grace period 默认值;MAX_RECTS;Bytes\<N\> 表示;fourcc registry(均 🔧 IMPLEMENTATION-DEFINED)
  - buffer / GPU domain revoke 强制顺序(per § 6.4 注)

---

## 3. 角色分布概览

### 机制设计（4）

| 文件 | 实现参考维度 | 主要交付物 |
|---|---|---|
| `jhyy_v20_多目标与可重现构建研究.md` | 论证密度高 | TargetSpec / QBE 锁 / PE/COFF repro / 9 项修订 diff |
| `syscallABI边界与寄存器约定研究.md` | 工程化高 | 11 寄存器固定角色 / 22 验收 / D-M3-1~6 |
| `jhyy_gui_subsystem.md` | 概念完整 | 方案 c / 6 态状态机 / IDL 草案 |
| `result.md` | 方法论强 + 论证密度高 | 8 字节 layout / 5 层表示 / 16 项验收矩阵 |

### 机制审查（1）

| 文件 | 审查对象 | 关键结论 |
|---|---|---|
| `jhyy_OS有效性评估与架构分析.md` | 三项创新 | 「设计可信、实现待证、领先未证」；8 项可证伪假设 |

### 排期修订（1）

| 文件 | 修订对象 | 关键调整 |
|---|---|---|
| `M8d_M12_排期修订.md` | GUI 协议层 + 工具包 | M8d 后移到 3j 后；M12 重定义为安全 API 稳定集 |

### 执行摘要（1）

| 文件 | 依附 | 切片用途 |
|---|---|---|
| `jhyy_v20_研究_执行摘要.md` | 多目标构建研究 | 9 项修订 + R1-R10 风险排序；sprint kickoff 时优先查阅 |

### 协议规范初稿（1）

| 文件 | 实现参考维度 | 主要交付物 |
|---|---|---|
| `报告§11§12决策与拍板流程说明.markdown` | 决策完整 + IDL / 状态机 / 错误码 | D-GUI-1 ~ D-GUI-10 决策清单 / topology / wire format / IDL / L1-L4 lifecycle invariants / Shm region ↔ mapping split / revoke 4 阶段 / seat 策略 / error model / acceptance matrix |

---

## 4. 时间线张力锚点

> 本节只登记原文已锁的具体弱点，不替作者重新抽象为「张力 A/B/C」。

### §4.1 M8d 必须后移的依据（原文已锁）

来源：`M8d_M12_排期修订.md` § 一核心结论 + `jhyy_gui_subsystem.md` § 8 阻塞项表

- 4 个真正阻塞项全部落在语言/内核层，compositor 协议层无法独立闭合：

  | 阻塞项 | 归属 sprint | M8d 是否可绕过 |
  |---|---|---|
  | `Cap<Shm>` 与共享映射语义 | 3i | 否 |
  | 异步 revoke 的 epoch / ack 模型 | 3j | 否 |
  | D16 IDL 确定性 | 3g | 否 |
  | framebuffer 与 VSync 驱动接口 | 3j | 否（可先做软件合成兜底） |

- 修订后依赖链：`3g → 3i → 3j → M8d → M12`

### §4.2 2 周 MVS 估算偏激进的依据（原文已锁）

来源：`M8d_M12_排期修订.md` § 三 M8d 最小闭环 + § 五状态标注

- M8d 协议层在 3g-3j 形成「类型检查 + mapping ledger + epoch revoke」最小闭环前，**只做 4 件事**（per 排期修订 § 三）：compositor 独立 capability 域骨架 / `Cap<Surface>` + `Cap<Buffer>` 状态机原型 / client 端双缓冲 + commit 移交可见性属性测试 / 幽灵 surface 反例测试
- 此时协议版本保持 `GUI_PROTOCOL_VERSION = 0`，明确标「草案，可破坏变更」
- **2 周估算偏激进**：即便 3g-3j 全部按期交付，compositor 协议层单态 type + function pointer 妥协（per `coordination.md` § 3 D33）≈ 1k 行，加上 4 项验收 + 反例测试，**实际所需时间 > 2 周**

### §4.3 张力的具体表现

合并工作量已超「两人 v0.x hold 住」尺度（per CLAUDE.md 五原则 1）：

| 维度 | 数字 | 来源 |
|---|---|---|
| 多目标构建研究 TargetSpec 字段 | **20+ 字段** | `jhyy_v20_多目标与可重现构建研究.md` § 1 |
| syscall ABI 验收用例 | **22 个** | `syscallABI边界与寄存器约定研究.md` § 7 |
| GUI 阻塞项 | **4 个**（Cap<Shm> / epoch revoke / D16 / VSync）| `M8d_M12_排期修订.md` § 一 |
| result.md 三段 sprint | **顺序强制**（3g → 3g.5 → 3g.7）| `result.md` § 10 |

**未决议**：是否把这些工作量显式分阶段裁剪（per § 7 局限，本 INDEX 不仲裁）。

### §4.4 未决议的排期调整

来源：`M8d_M12_排期修订.md` § 五末尾 4 个 `[ ]` 复选框

- [ ] 采纳方案 c（线性句柄 + 内核共享映射）
- [ ] `unsafe_share` 限定为 RW↔RO/W 审计机制
- [ ] v3.x spec 纳入 `Cap<Shm>`、SharedCap 取舍、epoch/ack revoke
- [ ] `coordination.md` 更新 M8d / M12 前置依赖与排期

INDEX 仅登记。

---

## 5. 实现参考价值速查表

> 给 sprint kickoff 用：实现 X 时参考哪份。

| 实现目标 | 参考 | 关键章节 |
|---|---|---|
| 实现 syscall 入口 / 寄存器约定 | `syscallABI边界与寄存器约定研究.md` | §3 推荐编码 / §5 entry-exit / §10 D-M3-1~6 |
| 实现 capability 编译期 sema | `result.md` | §3 八条规则 / §4 线性 / §10 sprint 3g |
| 实现 capability phantom 0 字节 | `result.md` | §5 两套视图 / §10 sprint 3g.5 |
| 实现 capability 联调 + byte-equal | `result.md` | §10 sprint 3g.7 / §11 验收矩阵 B14 |
| 实现 multi-target 编译链 | `jhyy_v20_多目标与可重现构建研究.md` | §1 TargetSpec / §2 CLI / §3 codegen dispatcher |
| 实现 PE/COFF `.efi` 可重现 | `jhyy_v20_多目标与可重现构建研究.md` | §9-§10 11 类 PE 字段 / §11 双跑脚本 |
| 实现 UEFI 启动 + runtime | `jhyy_v20_多目标与可重现构建研究.md` | §4 最小 runtime / §6-§7 crt0 + builtins |
| 实现 GUI Surface 生命周期 | `jhyy_gui_subsystem.md` | §4 6 态状态机 / §5 协议类型 / §11.3 IDL |
| 实现 GUI revoke / epoch | `jhyy_gui_subsystem.md` | §3 方案 c / §4 撤销传播 |
| 实现 GUI 输入隔离 | `jhyy_gui_subsystem.md` | §6 seat + focus_epoch |
| 评估 Narrow Waivers 风险 | `jhyy_OS有效性评估与架构分析.md` | §2.4 / §7.2-§7.3 |
| 设计可证伪假设 / 验证矩阵 | `jhyy_OS有效性评估与架构分析.md` | §8 H1-H8 / §8.5 最低验证门 |
| 找 9 项修订 diff（sprint kickoff） | `jhyy_v20_研究_执行摘要.md` | §9 项文档修订 |
| 排期调整 M8d / M12 | `M8d_M12_排期修订.md` | 整文（2 KB） |
| 起草 GUI 协议规范 / IDL / 决策清单 | `报告§11§12决策与拍板流程说明.markdown` | §0 preamble / §1 topology / §2 cap contracts / §3 wire format / §4 IDL / §5 kernel boundary / §6 revoke / §7 seat / §8 error model / §9 M8d scope / §10 acceptance matrix |

---

## 6. 验证清单

| 自检项 | 判定标准 | 检查方式 |
|---|---|---|
| 索引完整性 | 8 份全有登记 | §2.x 子节数 = 8 |
| 角色分类 | 每份至少一条引用方向 | §2.x 「本文引用了」/「本文建议修订」非空 |
| 实现参考标注 | 每份机制设计有 1-2 个维度标签 | §2.x 「实现参考维度」非空 |
| 时间线锚点具体化 | §4 列 M8d/M12 + 2 周估算 + 4 阻塞并行 | grep `M8d / M12 / 2 周 / 4 阻塞` 关键词 |
| 不修改 7 份原文 | 仅新增 INDEX.md + coordination.md 加 1 节 | `ls -la` 7 份原文 mtime 不变 |
| 不修改 v0.0.0-v0.0.4 | 7 份 v0.0.x doc mtime 不变 | `ls -la` 对比 |
| 不锁结论 | INDEX 不出现「应 / 必须 / 推荐」措辞 | 词频检查（§4 / §5 不含）|
| 与 CLAUDE.md 一致 | 不与五原则矛盾 | grep `可行 / 双线 / 寄生 / Debug / Kernel` |

---

## 7. INDEX 的局限

1. **不解决时间线张力** —— §4 仅列锚点,排期调整未决。
2. **不锁定任何设计结论** —— 8 份原文 status 标「成熟草案」/「评审中」。
3. **不取代 coordination.md** —— 引用入口在 coordination.md § 4.3，本 INDEX 是其详细化。
4. **不取代 design-log.md** —— 设计决策记录仍归后者。
5. **不为 `result.md` 与 `有效性评估` 之间的分歧裁定** —— §2 标注各自角色（机制设计 vs 机制审查）。
6. **不保证 8 份原文自身不冲突** —— 仅登记，不仲裁。
7. **不自动跟踪更新** —— mtime / 字符数需手动更新（per CLAUDE.md 原则 1 反对增加工具链负担）。
8. **不解决「角色分类本身的争议」** —— 4 类由 user 在 2026-08-31 会话中确认。
9. **不替作者勾选 4 个 `[ ]` 复选框**（per §4.4）。
10. **不在 v0.0.x spec doc 加单行引用** —— 本次不动，留待下次 sprint 决定。
