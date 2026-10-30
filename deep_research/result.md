# jhyy `Cap<T>` 类型系统 v3.1 落地设计报告

## 核心结论：Cap 安全由“8 字节值 + 编译期线性约束 + D16 元数据”三段共同保证

1. **推荐方案一句话概括：将 `Cap<T>` 实现为“语法像泛型、sema 硬编码的内建线性句柄”，在类型层保留 `T` 与 `_phantom:*T`，在 layout/ABI 层固定为 8 字节 cnode 引用；由 D16 cap-offset 表承担跨 IPC 改写，由确定性 ID 分配保证 byte-equal。**
2. **`T` 不依赖未来泛型机制。** 3g 只接受白名单中的 0 参数名义类型 `T`，sema 使用 `TypeName + declaration_order` 作为类型标签；3i 后可通过 add-only 单态化接入真泛型，旧二进制和 ABI 无需变化。[4]
3. **线性规则必须在 MIR 显式判定。** 引入 capability use-count（gen/kill）和 borrow region，先运行 copy/use/borrow 检查，再 lower 到 QBE IL；这样既能衔接现有 IL emit，也能保证检查顺序不影响字节输出。[4]
4. **phantom 不是“普通零大小类型”。** AST/sema/HIR 保留 4 个语义字段，struct layout 计算后写入 `AbiRecord { size:8, align:8, cap_field_count:1 }`；QBE IL 只生成 `i32; i8; i16; pad`，padding 在写入端显式 zero-init。[1]
5. **D16 是编译器与内核的唯一位置契约。** codegen 按源顺序遍历含 Cap 的消息类型，生成稳定 `msg_tag` 和去重 offset，并以专用 IL section/符号输出；内核只按 `header.msg_tag` 索引，不解析完整 jhyy 类型。[3]
6. **软件 phantom + linear type 的安全边界必须写进 M4 论证。** 在“用户态不能伪造句柄、不能绕过类型、不能复制、不能猜测索引”的模型中，本方案足以支撑语言层授权；但对内存破坏、TOCTOU、跨线程句柄复用及内核对象生命周期，仍必须由内核 cnode/rights/revocation 兜底。[5]

## 1. 设计边界已锁定，但三个 sprint 必须增量落地

本章给出形式化判断规则，并说明为什么不能把 Cap 检查推迟到现有 borrow checker 或未来 trait 系统。核心判断是：`Cap<T>` 的值安全由线性类型负责，类型区分由 phantom 负责，运行时授权由内核负责，三者不能相互替代。

### 1.1 元规则：同一事实只能有一个权威源

本设计只扩展语言语义，不重新设计内核对象、cnode 存储或 syscall handler。项目文档已经锁定以下事实，本文不再讨论替代布局：

- `Cap<T>` 运行时固定 8 字节：`cnode_idx:u32 @0`、`depth:u8 @4`、`rights:u16 @6`，offset 5 有 1 字节显式 padding；
- `is_valid`、权限检查和 revocation 由内核兜底；
- IPC header 为 16 字节，含 `msg_tag:u32`；
- D16 cap-offset 记录格式为 `{msg_tag:u32, n_caps:u16, cap_offsets:[u16; n]}`。[1][3]

因此，sema 中的 `CapTy(Tag, Rights)`、layout 中的 `AbiRecord` 和 codegen 中的 IL aggregate **不得各自独立定义规范**。所有下游计算必须从统一 `TypeEnv` 读取。若修改字段顺序、对齐或 rights 编码，必须同步更新这三处以及 ABI 文档。

> **M-CAP-1（Well-formed Cap）。**
>
> \[
> \frac{T\in\text{NamedType}\qquad \text{layout}(T)=\text{phantom}}
> {\text{Cap}\langle T\rangle\ \text{well-formed}}
> \]

> **M-CAP-2（Type separation）。**
>
> \[
> \frac{\text{name}(T_1)=\text{name}(T_2)\quad \text{decl}(T_1)=\text{decl}(T_2)}
> {\text{Cap}\langle T_1\rangle = \text{Cap}\langle T_2\rangle}
> \]

`T` 相等按“规范名称 + 声明位置”判定，不比较 AST 指针；不同包或未来模块的歧义通过 canonicalized path 解决。此时没有真正的泛型应用，因此也不需要约束求解。

### 1.2 `T` 是编译期标签，不会进入运行时 ABI

项目当前没有 generics、closures、RAII 或 nested function，且 Move trait 尚未实现。[2] 因此，3g 必须把 `Cap<T>` 当作内建 nominal type constructor：

- 解析 `cap<T>` 时不进入未来泛型环境；
- 只允许白名单的类型实参；
- 不生成类型参数作用域；
- 不尝试 partial application；
- 不允许非白名单表达式出现在 `<>` 中。

`T` 的作用是在编译期区分授权对象，不携带运行时方法表、vtable、size 或 type id。后续若接入真泛型，只新增单态化实例，不改变 `Cap<T>` 的 wire layout。

```jhyy
type Cap<T> = struct {        // 仅 sema/internal AST 视角
    cnode_idx: u32,
    depth:     u8,
    rights:    u16,
    _phantom:  *T,            // 0-byte marker，不占 ABI
}
```

`T` 的信息不进入普通 ABI，但仍必须保留在两类位置：

1. 诊断信息、debug side table 和 `--debug-info` metadata；
2. 防止 `Cap<File>` 与 `Cap<Socket>` 混用。

由此形成两套结构：类型层记录完整语义，ABI 层固定为 8 字节句柄。两者的一致性由 layout pass 证明，而不是由运行时反射保证。

![Cap 在源码、AST/HIR、MIR、IL 和汇编/runtime 的表示分叉](https://one-agent-prod-1343551737.cos.ap-guangzhou.myqcloud.com/artifacts/1851/b8c73c218ea2433b98bd69ffa98e9bab/0PnLdjCGaRD/task-001b63a2510a63ae3692d9a5015b1a82/.rendered/_assets/dr%3Acap-design/fig_repr.png?q-sign-algorithm=sha1&q-ak=AKID_REDACTED&q-sign-time=1787722464%3B1795498464&q-key-time=1787722464%3B1795498464&q-header-list=host&q-url-param-list=&q-signature=97331bd0c57cd58a8e040b1ffba39ec72ce12018)

*图 1：`_phantom` 保留到 MIR；lower 到 QBE IL 时生成固定 8 字节 aggregate。数据来源：v0.0.1-capability.md §1、v3.x-capability-spec.md §8 [1][4]*

## 2. Cap 表示必须在 lowering 时从语义视图切换为 ABI 视图

Cap 的语义字段、线性状态与运行时存储必须分层维护。若 AST、IR 和 QBE 共用一套结构，要么 ABI 信息过早污染类型系统，要么 codegen 从类型推断中重建布局，形成难以验证的双源事实。

### 2.1 五层表示及其职责

| 层 | 数据结构 | `_phantom` 状态 | 关键不变量 |
|---|---|---|---|
| 源码/AST | `TyCap { param:*T }` | 存在 | `T` 已经白名单化 |
| HIR | `CapTy(tag, rights_var?)` | 作为 marker 字段存在 | 参与类型相等与字段访问 |
| MIR | `Cap(value_id, ty, region)` | 已标记为 zero-sized | 每个 `value_id` 有唯一 ownership 状态 |
| QBE IL | `agg {i32;i8;i16;pad8}` | 消失 | 所有 emit 使用 `AbiRecord`，而非原始 field 列表 |
| 运行时 | 8 字节 cnode 引用 | 不存在 | padding 为零；跨 IPC 由内核原地改写 |

**表示层的核心结论是：`_phantom` 并不在 AST 到 MIR 之间突然消失，而是在 layout/lowering 阶段被证明为零大小，随后从 IL aggregate 中剔除。** 因此，“phantom 在哪一层消失”应回答为：**类型与 HIR 层保留，MIR 保留零大小 marker，QBE IL 不再出现。**

推荐新增内部类型：

```text
Type   ::= ... | Cap(Tag, RightsExpr) | Phantom(T)
Layout ::= AbiRecord { size; align; fields:[AbiField]; cap_fields:[u16] }
```

`RightsExpr` 只在 3g.7 及权限收窄时实质性使用；MVP 可为 `RightsVar(unique_id)`，以便在未来单态化阶段追踪 derivation。

每个 `Cap` 的 layout 固定为：

```text
AbiField{name="cnode_idx", ty=i32, offset=0,  size=4}
AbiField{name="depth",     ty=u8,  offset=4,  size=1}
AbiField{name="rights",    ty=u16, offset=6,  size=2}
explicit_pad: AbiField{name="_cap_pad", ty=u8, offset=5, size=1}
```

因此，`size_of(Cap<T>) = 8`，`align_of(Cap<T>) = 8`。代码生成不得依赖 host struct 的 C layout，必须读取上述 `AbiRecord`。

建议的 IL 提案为：

```text
; D16 cap-offset section（每个编译单元尾部，按 msg_tag 升序）
section .capoffsets
capoffset 1, 2, {0, 8}      ; ReadMsg
capoffset 2, 1, {0}         ; GrantMsg
capoffset 3, 1, {16}        ; PageFaultMsg
```

汇编符号约定如下：

```text
__jhyy_capoffset_1 = .-__jhyy_capoffsets_start
__jhyy_capoffset_ReadMsg:
    .long 1, 2               ; msg_tag, n_caps
    .short 0, 8              ; cap_offsets（已去重、升序）
```

这些符号是编译器 ABI，不是 C FFI 稳定 API。当前阶段也不应将 struct/enum 按值跨越 FFI；Cap 只能通过指针或 message bytes 传递。[2]

### 2.2 类型参数编码：白名单、canonical 名称与延迟展开

**设计建议（3g）：**

1. 解析阶段识别 `cap` 作为 type-con 级别的固定名称；
2. AST 存储 `AstCap { arg: TypeName }`；
3. name resolution 拒绝 `cap<int>`、`cap<*Page>`、`cap<cap<Page>>`、局部类型参数及 alias 循环；
4. 只有完整、具体的白名单类型才允许作为 `T`；
5. 别名在展开后再比较。

`type_id` 有两个不同概念，必须避免混淆：

| 概念 | 定义 | 是否进入 ABI |
|---|---|---|
| `cap_type_id` | `stable_hash(canonical_name, decl_loc)` | 否 |
| `msg_tag` | 按 D16 顺序为消息类型分配的稳定编号 | 是 |

`cap_type_id` 可以出现在 debug-only metadata；`msg_tag` 才进入正式 IPC 协议。二者都不能依赖指针地址、哈希表迭代、`HashMap` 实现、随机种子或并行任务顺序。

具体算法是：

1. 先遍历所有源文件，按 `(file_index, line, column)` 排序；
2. 分配 `type_no`；
3. 再按 `type_no` 遍历消息类型；
4. 分配连续 `msg_tag`，从 1 开始；
5. 跳过不含 Cap 字段的类型；
6. 在 IL emit 前冻结 `CapOffsetTable`。

去重时比较 canonical struct type，不比较 alias 名称，以避免同一布局产生重复条目。建议保留反向断言：`msg_tag → canonical_struct` 必须为一一映射。

## 3. 八条 sema 规则必须统一接入现有检查管线

八条规则不是八组彼此独立的报错逻辑，而是一条线性 capability 判定链：先识别合法来源，再约束类型、复制、权限和所有权，最后检查借用。所有规则都必须在同一个 `SemaContext` 中读取 `TypeEnv` 与 `LinearEnv`，避免不同 pass 各自维护一套 Cap 事实。

### 3.1 检查顺序决定错误质量，也决定输出稳定性

推荐顺序为：

```text
parse → name-resolve → kind/builtin-cap check → type-infer →
linear-use check → borrow-region check → layout commit →
mono/ipc-collect → codegen/QBE emit
```

接入点如下：

| # | 规则 | 检查时机 | 算法 | 默认错误模板 |
|---|---|---|---|---|
| 1 | 不可伪造 | name-resolve + type-infer | 只有 `#[cap_constructor]` 函数可返回 `Cap<T>`；构造函数体只允许 syscall/受限 white-list；禁止手写 `Cap{...}` | `E-cap-forge` |
| 2 | 类型参数化 | type-infer | nominal equality + phantom marker | `E-cap-type-mismatch` |
| 3 | 不可复制 | linear-use | use-count = 1；copy 仅在显式 `Copy` 白名单且 `clone_cap` 路径中允许 | `E-cap-moved` |
| 4 | 不可降级 | type-infer + unsafe | 拒绝 `as`；`into_raw` 必须位于 `unsafe_cap` 且持有 `WaiverCap` | `E-cap-downgrade` |
| 5 | 可撤销 | codegen/stdlib contract | 标记 `must-revoke`；未消费参数触发 lint | `W-cap-unrevoked` |
| 6 | 空 capability | type-infer + MIR | `null` 零初始化；`is_valid` 返回 `bool`，不解除 linear 约束 | `E-cap-invalid` |
| 7 | 传参 = move | linear-use | 参数 consume；`&/&mut` 借用分别计入 shared/exclusive | `E-cap-use-after-move` |
| 8 | `&mut` 借用一致 | borrow-region | 引用能力 lattice + live region | `E-cap-aliasing` |

规则 5 在 3g 只实施静态可达性警告，不承诺完整 revocation propagation。项目当前没有 RAII 和 Drop checker；若用户忘记 `revoke`，编译器只能提示“capability `c` 离开作用域且未 consumed/revoked”。这不能证明内核对象已经失效，也不能替代 seL4 式 derivation-tree propagation。[1]

规则 6 的重点是：`null` 是合法线性值，只是缺少授权。对 `Cap<T>` 执行 `c = null` 应把 `c` 标记为“empty but initialized”，允许后续 `is_valid` 分支；但 `null` 仍不能从 `_phantom` 恢复具体类型，`unsafe_cap` 中的 raw 转换也不能假定非空。

规则 4 必须禁止普通 `as`，但允许以下两类白名单转换：

- syscall ABI 返回 `Cap<T>`；
- `unsafe_cap` 中的 `into_raw`。

每个降级点记录 `WaiverCap` 要求与 confidence。规则 1 的构造函数则必须具有完整审计边界：普通函数即使返回类型恰好是 `Cap<T>`，也不能凭 return type 成为构造函数。

## 4. 最小线性系统必须覆盖 move、pattern、集合与借用

仅禁止“两个同名变量同时存在”不足以实现线性语义。真正的规则是：每个 capability value 从构造到销毁只有一条 use 链；pattern、结构体字段、集合元素和函数参数都只是这条链的不同分支。

### 4.1 ownership 状态机：每个 value 只有一条完整 use 链

```text
State ∈ { Owned, BorrowedShared(k), BorrowedMut, Moved, Invalid }
```

转移规则如下：

- `let x = e`：若 `e:Cap<T>` 且 `e` 是 move-path，则 source 变为 `Moved`；
- `f(x)`：按 `Cap<T>` 值参数 consume，除非参数声明为 `&` 或 `&mut`；
- `let &y = &x`：增加共享借用计数；
- `let y = &mut x`：要求 `x` 只有当前活跃 owner，且没有其他活跃 borrow；
- `match`：每个 pattern 分支继承父作用域的 capability state；
- 析构作用域：若 final state 仍 `Owned`，按规则 5 发出 lint。

```text
use-count(v) = uses(v) − kills(v)
uses(v)     = 1 + |arguments| + |moves| + |deref-reads| + |unsafe-escapes|
kills(v)    = |revokes| + |grants| + |returns| + |matches-consumed| + |assign-to-moved|
```

**`use-count` 必须解释每个 use 与 kill 的语义。** 对当前 MVP，规则简化为：

> 若 value `v` 是线性 Cap，则全程序路径上 `Σgen(v) = 1`，且 `Σkill(v) ≥ 1`；在任意 join 点不得同时有“至少一条路径 moved”和“另一条路径仍 owned”，除非后续通过显式 `is_valid` 分支恢复。

`gen(v)` 表示 value 变为可用；`kill(v)` 表示 value 被 consume、revoke、grant、return 或在 match 中按分支销毁。join 点由 if/else、match 和循环构造。若两侧状态不一致，应先合并显式转移状态，再判断后续是否仍可用。

**形式化 move judgment：**

> **L-CONSUME.**
>
> \[
> \frac{\Gamma(x)=\text{Cap}\langle T\rangle^{1}\qquad x\notin\text{LiveBorrows}}
> {\Gamma,x:\text{Cap}\langle T\rangle^{1}\Rightarrow\Gamma,x:\text{Moved}}
> \]

> **L-JOIN.**
>
> \[
> \frac{\Gamma_1\sqcup\Gamma_2\ \text{defined}\qquad \forall x,\ \text{state}(x)\ \text{agrees}}
> {\Gamma_1\vee\Gamma_2\Rightarrow\Gamma_1\sqcup\Gamma_2}
> \]

若两侧对 `x` 分别为 `Owned` 与 `Moved`，且代码随后使用 `x`，则 `⊔` 未定义，并报告 `E-cap-partial-move`。

pattern binding 按 field path 展开。例如：

```jhyy
let Msg { addr, cap } = m;
```

其中 `cap:Cap<File>` 按完整 field path `m.cap` move 到 `cap`；`addr` 若是普通 copy 类型，则保持 copy。结构体字段的线性状态必须在字段粒度维护，而不能只记录整个 struct 是否已 move。

集合元素使用 `Elem(i, v)` 作为抽象位置：

- `for e in arr` 的 by-value循环会在 loop header 处强制 `e` 失效；
- 若索引访问后再次使用原数组，需要显式 `take`/`swap_remove` 语义；
- MVP 阶段禁止从共享切片中 move 单个 Cap；
- 固定数组本身也不实现 `Copy`。

这一限制比“数组整体是否 copy”更严格：即使数组不复制，单个元素仍可能从原数组移动到外部。因此数组不能自动成为 Cap 的逃生通道。

**警告分级（设计建议）：**

| 等级 | 触发条件 | 处置 |
|---|---|---|
| deny | 已 moved、aliasing `&mut`、非法 `as`、构造函数伪造 | 编译错误 |
| warn-hard | linear value 未 consumed/revoked、padding 可能泄露、unsafe_cap 无 WaiverCap | `--cap-strict` 下 deny |
| warn-soft | 未使用 borrow、debug-only provenance 未引用 | 普通 lint |

**deterministic checking：** linear solver 遍历 CFG 时使用以下稳定排序：

```text
blocks: post-order on (block_id)
phi inputs: by predecessor block_id
pattern fields: source declaration order
```

同一份 CFG 必须始终产生相同诊断。诊断收集后先排序，再输出首个错误，从而保持 `--cap-strict` 开关前后行为一致。

### 4.2 借用系统最小化，但足以支撑 Cap 独占访问

3g 不实现完整 Rust 生命周期。建议采用“region name =  lexical scope + unique index”，并使用 capability 引用能力的简单 lattice：

```text
R ∈ { Immutable, Mutable, Disjoint }
```

| 操作 | 前置条件 | 效果 |
|---|---|---|
| `&x` | `state(x)=Owned` | `BorrowedShared(1)` |
| `&mut x` | `state(x)=Owned` 且 active borrow count = 0 | `BorrowedMut` |
| 读取 `&x` | region 未结束 | 不改变 ownership |
| 写入 `&mut x` | 唯一活跃 borrow | 不改变 ownership |
| region 结束 | — | 恢复 `Owned` |

实现时把 region 实现为 `BorrowSet`，禁用 lifetime subtyping、HRTB、coercion 与 `Drop` 推断，只保留：

- lexical scope；
- explicit block；
- argument/return scope。

这样做能覆盖 90% 以上的 Cap 使用，同时避免 borrow checker 与未来 region 系统形成隐式契约。

## 5. phantom 必须保留语义字段，但 ABI 必须删除 0 字节值

phantom 的实现不是简单地“忽略一个字段”，而是分两步：先在类型层证明其语义作用，再在 layout 层证明其运行时大小为零。只要这两个证明没有统一入口，就可能出现“sema 认为存在、codegen 却读取”、或“ABI 已删除、诊断却无法定位”的不一致。

### 5.1 两套视图、一次 commit

struct layout 的算法骨架如下：

```python
def layout_struct(s):
    off = 0
    sema_fields = []
    abi_fields = []
    cap_paths = []
    for f in sorted(s.fields, key=field_order):
        ty = lower_type(f.ty)            # 递归；遇到 Cap<T> 进入 ABI view
        sema_fields.append(Field(f.name, ty, abi_size=ty.size))
        if ty.is_cap:
            abi_fields.append(AbiField(f.name, AGG_CAP8, off, size=8))
            cap_paths.append((f.name, off))
            off = align_up(off + 8, 8)
        elif ty.is_phantom:
            # phantom 参与类型，但不产生 abi field、offset 或初始化
            continue
        else:
            off = align_up(off, ty.align)
            abi_fields.append(AbiField(f.name, ty, off, ty.size))
            off += ty.size
    layout = AbiRecord(size=off, align=8, fields=abi_fields, cap_fields=cap_paths)
    check_layout_invariant(layout)        # 见下
    return layout
```

**invariant（在 `commit_layout` 后冻结）：**

1. 对任意 `Cap<T>` 字段，`AbiRecord.cap_fields` 中存在唯一 `(name, offset)`；
2. `AbiRecord.size - sum(non_cap, non_pad) = 8 * cap_field_count`；
3. 所有 aggregate 中的 padding 均有显式 `pad` 节点；
4. `AbiRecord.size % align = 0`；
5. 相同 canonical type 永远产生相同 `AbiRecord`；
6. 所有迭代都使用 `abi_fields` 排序，而非 symbol table 顺序。

padding 由 layout pass 显式管理：

- offset 5 的 1 字节 padding 被建模为 `pad@5`；
- `Cap<T>` 的 store aggregate 在 IL 中先 zero，再写入 `idx/depth/rights`；
- 构造 `Cap { ... }` 禁止用户输入，因此不存在从 `_phantom` 读取有效指针的问题。

真正的泄露风险发生在 C FFI、inline asm、volatile 和 `unsafe_cap` 边界。这些位置默认拒绝 capability，或在 emit 前插入“zero padding + 仅按 D16 offset 解释”的转换。

### 5.2 zero-sized marker 必须可诊断

`size_of(_phantom)` 与 `align_of(_phantom)` 均为 0；但“`_phantom` 存在”是类型信息，不能由普通 ZST 替代。否则，若未来允许 `Cap<()>`，其 `_phantom:*()` 仍应合法地区分 `Cap<()>` 与其他类型。

因此，建议新增内部属性 `zero_sized AND type_identity`，而不是仅设置 size 为 0。这样可避免未来误把普通 `()` 字段当成 capability marker。

验证建议是在 CI 中加入 property test：

- 随机生成 200 个含 Cap、嵌套 struct、`[Cap; N]` 的类型；
- 断言 `size % 8 == 0`；
- 断言 `cap_field_count * 8 + sum(other) + pad == size`；
- 断言 `field_offsets` 与 QBE `.s` 解析结果一致。

## 6. D16 必须在 IL 中显式形成，并由 codegen 单一职责维护

D16 是“含 Cap 的 struct layout”与“内核改写位置”之间的唯一契约。若把 offset 计算分散在 struct layout、IPC wrapper 和汇编输出中，任何一侧的字段顺序或去重策略变化都会 silently 破坏跨进程协议。因此必须形成独立、可冻结的 `CapOffsetTable`。

### 6.1 D16 生成流程

![D16 生成流程：从源顺序遍历到内核按 msg_tag 索引](https://one-agent-prod-1343551737.cos.ap-guangzhou.myqcloud.com/artifacts/1851/b8c73c218ea2433b98bd69ffa98e9bab/0PnLdjCGaRD/task-001b63a2510a63ae3692d9a5015b1a82/.rendered/_assets/dr%3Acap-design/fig_d16.png?q-sign-algorithm=sha1&q-ak=AKID_REDACTED&q-sign-time=1787722464%3B1795498464&q-key-time=1787722464%3B1795498464&q-header-list=host&q-url-param-list=&q-signature=ac99b039246919f440b746651e155f86e1ccd201)

*图 2：确定性顺序固定为“源文件排序 → 声明顺序 layout → 稳定 Cap 收集 → 冻结 msg_tag → IL section”。数据来源：v0.0.1-syscall-abi.md §1.1.4 [3]*

```text
pass 1: collect_messages()
  对 topo-sorted modules，按 (file_index, line, col) 遍历 type decl；
  若 canonical struct 存在 Cap 字段（含嵌套），记录 (canon_name, struct_id)。

pass 2: assign_msg_tag()
  sorted_msg_types = sort(stable_order, by struct_id)；
  for i, s in enumerate(sorted_msg_types, start=1):
      msg_tag[s] = i                 # 冻结点

pass 3: compute_offsets()
  复用 layout 后的 AbiRecord.cap_fields；
  offsets = sorted(unique offsets, ascending)；
  assert len(offsets) <= 65535       # D16 u16 上限

pass 4: emit()
  输出 .capoffsets；以 msg_tag 升序二次排序，emit 去重后的 (msg_tag, n, offsets)。
```

**复用关系：** D16 不是第二张独立 field-offset 表，而是“既有 layout 表 + Cap 谓词 + IPC 稳定编号”的视图。既有 `StructOffsetTable` 继续服务普通字段访问；新增 `CapOffsetView = select(cap_fields) ∘ StructOffsetTable`。

二者共用同一 `AbiRecord`，但输出格式不同：

| 表 | 内容 | 使用方 |
|---|---|---|
| `StructOffsetTable` | 全部字段 | 编译器 codegen |
| `CapOffsetTable` | 仅 Cap 字段 | 内核 IPC |
| `CapOffsetView` | 从 layout 派生的稳定视图 | D16 emit |

具体格式建议：

```text
section .capoffsets
; 每行：msg_tag, n_caps, [cap_offsets]（按声明顺序去重、升序）
capoffset 1, 2, {0, 8}
capoffset 2, 1, {0}
capoffset 3, 1, {16}
```

`.s` 中为每个条目生成 `MSG_TAG_${canon}` 与长度/offset 数组。链接脚本把 `.capoffsets` 放入只读段，并对齐到 8。内核由 syscall header 中的 `msg_tag` 计算条目地址，仅解释 `n_caps` 与 `cap_offsets`；它不解析 jhyy struct 的完整布局。

**嵌套与递归：** 当前只允许具体消息类型，禁止递归 Cap 聚合。若未来允许 `Option<Cap<T>>` 或 union，需要先扩展 D16 为树形描述符，不能把递归指针 offset 硬编码为 8。

**全局唯一性：** `msg_tag` 只对“本编译单元导出的 IPC 消息类型”唯一，对内联或私有消息可使用私有区间。跨 crate 稳定性延后到 3i；届时改用：

```text
msg_tag = stable_hash(scheme_version, package, version, canon_name)
```

并通过 `jhyy verify-abi` 比较旧版与新版 `CapOffsetTable`。

### 6.2 最小完整追踪示例

```jhyy
type File = struct { _priv: () }          // phantom, zero-sized
type Endpoint = struct { _priv: () }

#[cap_constructor]
extern fn sys_open(path: *u8, mode: u32) -> Cap<File>;

extern fn ipc_call(ep: Cap<Endpoint>, msg: *const u8, tag: u32) -> i64;

#[ipc_msg]
type ReadMsg = struct {
    addr: u64,
    cap:  Cap<File>,      // @8
}

fn read(ep: Cap<Endpoint>, mut f: Cap<File>) -> i64 {
    let m = ReadMsg { addr: 0, cap: f };  // f moved into m
    let tag = msg_tag<ReadMsg>();         // 编译器常数 1
    let r = ipc_call(ep, &raw m, tag);
    revoke(m.cap);                        // kill；禁止后续使用 m.cap
    r
}
```

变换轨迹如下：

1. **AST**

   ```text
   StructDecl ReadMsg { addr:Field(u64); cap:Field(Cap(File)) }
   Call(ipc_call, [ep, AddrOf(m), Int(tag)])
   ```

2. **HIR/sema**

   ```text
   ReadMsg.cap : CapTy("File")
   linear state: f → m.cap → consumed by revoke
   borrow: &raw m 为 raw pointer escape，需 unsafe_cap 门控
   ```

3. **MIR**

   ```text
   %m = struct { addr=0; cap=%f }      ; cap 仍是 Cap value
   call ipc_call(%ep, &%m, 1)
   kill %m.cap via revoke
   ```

4. **IL**

   ```text
   .type :ReadMsg = aggr i64, {i32; i8; i16; pad8}
   .data
   m:
       .long 0           ; addr
       .long 0           ; cnode_idx
       .byte 0           ; depth
       .word 0           ; rights
       .byte 0           ; explicit pad@5
   ```

5. **D16**

   ```text
   capoffset 1, 1, {8}
   ```

   注意：示例 5 中 IL 布局说明为演示目的进行了字段重排；实际 canonical layout 必须遵循项目锁定的 `{cnode_idx, depth, rights}` 顺序及 8 字节对齐，D16 offset 也以 layout pass 的冻结结果为准。

6. **.s**

   ```text
   __jhyy_capoffset_1:
       .long 1, 1
       .short 8
   ```

该示例刻意保留一处待 code review 的结构：MIR 中必须证明 `m.cap` 在 `revoke` 后不再使用；`&raw m` 的 escape 检查属于 MVP 之后的指针能力扩展，因此 3g 默认拒绝，需要显式 `unsafe_cap` 或改用 `ipc_call(&m, ...)`。这里的关键不是让示例无条件通过，而是把“何时仍允许 raw escape”明确变成规则，而不是依赖后续 pass 猜测。

## 7. provenance 必须依赖稳定 CapId，但 release build 不携带能力语义

provenance 是诊断与审计辅助，不是授权证据。它的稳定性要求低于 ABI，但仍必须服从确定性的关键不变量：同一输入、同一遍历顺序必须产生相同 CapId、相同表顺序和相同 IL；否则，debug/release 差异会污染 IPC 测试。

### 7.1 side table 与符号化 ID

`ProvenanceInfo` 的字段与 confidence 以 `v0.0.4-debug-abi.md` 为权威：56 字节 `DebugEvent` header、三级 confidence、136 字节 `ProvenanceInfo`，以及链/数组表达规则均已锁定。[5]

建议新增 `CapId = u32`，但 3g.5 不把 `CapId` 放入 `Cap<T>` 的 8 字节运行时值。每个 debug build 的 side table key 采用符号化 ID：

```text
CapId = stable_hash("cap-id",
                    source_loc,
                    msg_tag_or_constructor_id,
                    parent_ids sorted)
```

算法为：

1. 先分配 `type_no`、`msg_tag`、构造函数 ID 和 statement IDs；
2. 再按 `(file_index, line, col, sub_index)` 遍历所有 Cap 构造与 IPC copy；
3. 分配单调递增 `LocalCapId`；
4. 对 `grant/derive` 的 parent ID 排序后计算 `CapId`；
5. CapId 分配与 IL emit 使用同一 sorted worklist。

因此，CapId 在单次编译内稳定，并可随 deterministic IR 重放；它**不是跨进程全局标识**。跨进程关联必须依赖内核 cnode 中的 authority，不能依赖 debug-side `CapId`。

**strip 机制：**

- debug：生成 `.capmeta` 与 `.capoffsets.dbg`；
- release：codegen 设置 `debug_sections_enabled=false`，不 emit `ProvenanceInfo`、ring buffer 和 side-table relocations；
- 链接阶段，将 `.capmeta` 放入 `--gc-sections` 可回收段，并验证 `.capoffsets` 的 `msg_tag/n/offsets` 与 release 版完全相同。

使用 `__attribute__((unused))` 只能抑制警告，不能替代 section GC。最终验证应比较：

```text
release .capoffsets == debug .capoffsets
debug-only bytes   ⊂ debug-only sections
```

### 7.2 confidence 不得参与安全判定

| field | 推荐 confidence | 理由 |
|---|---|---|
| `constructed_at` | HardFact | 来自确定 source loc |
| `constructed_by` | CompilerInjected | 由调用图推断 |
| `grant_chain` | HardFact / Heuristic | 显式 grant 为事实；从日志恢复为启发式 |
| `revoke_chain` | HardFact | 由显式调用产生 |
| `current_holder` | HardFact | 仅在运行时 side table 中存在 |
| `rights` | HardFact | syscall 结果或内核状态 |
| `created_at_ns` | HardFact | 时间戳字段本身 |

`Heuristic` 字段不得用于 grant、revoke 或 Waiver 决策。[5] 这样可在提供调试便利的同时避免 provenance 成为“看似可信的第二授权通道”。

## 8. 外部系统提供约束机制，但不能替代 jhyy 的分层设计

跨系统比较的价值不在于复制某一种实现，而在于识别每条安全性质由哪一层保证。jhyy 不应把 CHERI 的硬件不变式、seL4 的存储隔离或 CompCert 的端到端证明压缩进单一语言特性。

### 8.1 系统对照：安全性质分布在编译、运行和证明层

| 系统 | 线性性 | 类型化授权 | 确定性保证 | byte-equal | 撤销传播 | 性能开销 | 对 jhyy 的可借鉴点 |
|---|---|---|---|---|---|---|---|
| CompCert | C 语义中的值/副作用 | Clight/Cminor 类型化中间表示 | 以 Coq 证明 compilation chain 语义保持为目标 | 未承诺工程 byte-equal；重点是 observable behavior 等价 | OS/cap 非核心 | 优化受限但可验证 | 每个 IR 有独立 small-step 语义；确定性应成为 invariant，而非输出排序习惯 [6] |
| seL4 | capability 作为内核对象引用 | CNode 存储 + rights + CSpace | 内核实现正确性由 proof 工程约束 | 不涉及用户编译器 byte-equal | derivation tree + revoke propagation | 一次表查找 | Cap 不可伪造最终由内核存储保证；编译器只负责类型和 IPC offset [7] |
| CHERI/Morello | 能力是 fat pointer，monotonicity | 硬件 tag/bounds/perms/provenance | 微架构实现确定；非“编译器可复现” | 寄存器/内存宽于普通指针 | 派生不可扩大权限 | 128 位 + 压缩/检查 | 软件 linear type 不能替代边界检查；用户态内存破坏需要硬件或严格 unsafe 审计 [8] |
| Rust | affine/linear via move + `&mut` | `Copy`、phantom、marker、trait | 无原生 byte-equal 承诺 | 受优化/LLVM 影响 | Drop checker | 零/低开销 | 借用规则、`PhantomData`、`repr(C)`、`#[must_use]`；但不要复制 Drop 复杂性 [9] |
| Reproducible Builds | 无关 | 无关 | 工具链环境确定性 | SOURCE_DATE_EPOCH 等 | 无关 | 接近零 | 将所有 entropy 明确列入 checklist；时间/路径不能进入 IL [10] |

**CompCert 的正确结论是“分层语义”，不是要求 jhyy 立即获得形式化证明。** CompCert 的编译链从 Clight 到 Cminor，再到后端汇编，并对可观察行为进行语义保持论证。[6] jhyy 3g 的现实目标应是将 Cap lowering 表达为可断言的 lattice/invariant，例如：

```text
type_ok → linear_ok → layout_frozen → il_deterministic
```

完整机器证明属于 v4.x 之后。这里的工程价值在于：先冻结中间表示、遍历顺序和不变量，未来才有可能围绕同一结构建立证明。

**seL4 的正确结论是“语言只负责把授权正确送到内核”。** seL4 将 capability 保存在 CNode 中，并通过 CSpace、rights 和 capability-space 防止用户态伪造。[7] jhyy 的 8 字节句柄只是 cnode 引用；若用户能猜测 `cnode_idx`、篡改 padding 或通过 raw pointer 伪造，仍需内核验证。因此，`#[cap_constructor]` + phantom + linear 属于 L1/L2，seL4 式存储隔离仍属于 L3。

**CHERI 的安全边界是硬件 provenance 与 monotonicity。** 官方 CHERI 技术材料指出：64 位平台能力为 128 位；validity tag 阻止无效能力用于 load/store/execute；provenance validity 保证有效能力只能由显式构造产生；capability monotonicity 保证派生能力不能超出源能力的权限和边界。[8]

jhyy 在 v0.x 明确不采用 CHERI，因此必须记录以下攻击模型：

- **软件方案足以覆盖：** type confusion、直接整数字面量伪造、隐式 copy、`as` 绕过、消息中错位 Cap；
- **软件方案不足：** raw-pointer/UAF/越界把任意 8 字节解释为 Cap、并发 double-grant、TOCTOU、`unsafe_cap` 滥用、内核对象 reuse；
- **需要硬件能力或内核强隔离：** 任意内存写入后重新解释 Cap、跨域 capability 伪造、能力越界传播。

因此，M4 论证应将“线性 type + phantom”定位为开发期与语言边界的完整性，而不能声称替代 CHERI 的运行时内存能力。

**Rust 的借鉴应限制在 MVP 最小子集。** 可借鉴：

- `Copy` 白名单；
- `PhantomData` 不占字段；
- `&mut` 独占借用；
- `#[must_use]`/lint；
- `repr(C)` 的固定 layout 思想。

不可直接移植：

- Drop checker；
- lifetime subtyping；
- HRTB；
- auto-trait；
- 完整 derive。

当前项目没有 RAII、Drop 和 trait 系统。[2] 若先实现自动 revoke，反而会掩盖 grant/revoke 语义，并推迟 M4 的撤销传播决策。

## 9. 可复现性必须成为 pass 不变量，而不是排序习惯

byte-equal 的难点不在“最终排序一次”，而在于任何后续 pass 都可能按哈希表、arena 地址或未冻结 ID 重新决定输出顺序。确定性必须进入 IR 定义、worklist、诊断和 side-table 算法，使输出成为输入顺序的函数。

### 9.1 通用 checklist 与 jhyy 映射

| 项目 | 风险 | jhyy 强制动作 | 归属 sprint |
|---|---|---|---|
| symtab 顺序 | HashMap 迭代 | 所有 `dump/sort` 使用 `(name, decl_order)` | 3g |
| IR 节点 emit | arena 地址作 key | CFG/phi 使用 stable block/var id | 3g |
| 临时变量命名 | 计数器受检查顺序影响 | `tmp_{node_id}_{op_index}` | 3g |
| 时间戳 | `__DATE__`、`created_at_ns` 泄露 | release 使用固定 epoch；debug 仅在允许段内 | 3g.5 |
| 路径字符串 | `__FILE__`、module path | 使用 stable file index + `--canon-source-root` | 3g |
| `__FILE__/__LINE__` | 行号变化 | 保留 int index，映射表进入 debug section | 3g.5 |
| CapId 分配 | 并行 visit | 顺序冻结的 worklist；ID 仅依赖 AST/CFG | 3g.5 |
| type id 分配 | 哈希随机化 | SipHash key 固定为 `0xdead_beef` 或排序后 FNV | 3g |
| msg_tag 分配 | 新类型插入顺序 | canonical struct 的拓扑排序 | 3g.7 |
| provenance strip | debug 符号残留 | section GC + diff 测试 | 3g.5 |
| linker/script | build-id、时间戳 | `--build-id=none`、固定脚本、规范 section 顺序 | 3g.7 |

建议新建 `DeterminismBudget`：任何 codegen pass 若需要新 ID，必须从 `canonical_input + monotonic_counter` 派生，并在 pass 文档中登记。

`SOURCE_DATE_EPOCH` 只能规范构建时间，不能替代编译器内部确定性。[10] 对 jhyy 而言，更有价值的是让以下对象全部可重放：

- AST ID；
- CFG ID；
- type_no；
- msg_tag；
- CapId；
- IL label；
- section symbol。

即使未来引入优化，也应通过“输入哈希 + 稳定启发式 + 排序 worklist”保证幂等，而不能依赖运行期线程调度或哈希实现。

## 10. 三个 sprint 必须依次交付类型、布局与闭环验证

3g、3g.5 与 3g.7 不能按“前端、后端、测试”机械切分，而应围绕同一冻结契约递进：3g 建立语义与 IR，3g.5 证明 ABI 并生成 D16，3g.7 验证编译器自身与既有 byte-equal fixed point 不冲突。

### 10.1 3g：类型与线性检查闭环

**目标：** 所有 `Cap<T>` 相关程序进入 codegen 前均具有完整 linear + borrow 判定；没有 Cap 的程序保持旧行为。

**修改文件/函数：**

| 位置 | 修改内容 |
|---|---|
| `compiler/src0/lexer.jhyy` | 新增 `cap`、模式 |
| `parser.jhyy` | 新增 `parse_cap_type` |
| `sema.jhyy:resolve_type` | 白名单 `T` |
| `sema.jhyy:check_function` | 识别 `#[cap_constructor]`、`unsafe_cap` |
| `infer.jhyy` | 规则 1–8 的 judgment |
| `linear.jhyy`（新增） | gen/kill/borrow region |
| `ir.jhyy` | `NodeCapConstruct`、`NodeRevoke`、`NodeUnsafeCap` |
| `codegen.jhyy:emit_expr` | 拒绝未处理 Cap 分支；通过现有 stable traversal 调用 `lower_cap` |

**复杂度：** 约 1,600–2,400 行，其中测试约 600–900 行。

**regress 用例：**

- `cap_ok.jhyy`；
- `cap_move_then_use.jhyy`；
- `cap_copy_forbidden.jhyy`；
- `cap_type_mismatch.jhyy`；
- `cap_into_raw_unsafe.jhyy`；
- `cap_borrow_aliasing.jhyy`；
- `cap_constructor_literal.jhyy`。

**byte-equal 验证：**

1. 对无 Cap 的 `fib.jhyy`、`ackermann.jhyy`、`nqueens.jhyy` 运行 `jhyy_N` 与 `jhyy_{N+1}`；
2. 比对 `.il` 与 `.s`；
3. 用 `git diff --stat` 与 `sha256` 双重断言；
4. 以现有 N=3 closure baseline 为回归门槛。

若新代码改变 zero-cap program 的输出，必须先证明修改的是诊断顺序，而不是 IR 语义，再恢复 canonical traversal。

**回滚：** 通过 feature gate `--cap=off` 使 lexer 不暴露 `cap`；linear pass 从 driver 中移除，不影响普通 struct。

### 10.2 3g.5：8 字节 ABI、D16 与 provenance

**目标：** 建立 type/layout/ABI 三方一致，并输出可被内核消费的 cap-offset 表。

**修改文件/函数：**

| 位置 | 修改内容 |
|---|---|
| `layout.jhyy:compute_struct` | 实现 Cap 8 字节聚合与 padding nodes |
| `abi.jhyy` | 新增 `AbiRecord` 冻结 |
| `codegen.jhyy:emit_aggregate` | 使用 fixed field order |
| `ipc.jhyy`（新增） | message collect + msg_tag |
| `il_emit.jhyy` | `.capoffsets` section |
| `provenance.jhyy`（新增） | `CapId`、confidence、side table |
| `driver.jhyy` | 新增 `--provenance=off/debug` |

**复杂度：** 约 1,900–2,800 行，其中测试约 800–1,200 行。

**regress 用例：**

- `cap_size8.jhyy`；
- `cap_struct_layout.jhyy`；
- `cap_ipc_d16.jhyy`；
- `cap_nested_msg.jhyy`；
- `cap_padding_zero.jhyy`；
- `cap_provenance_strip.jhyy`；
- `cap_msg_tag_stable.jhyy`：插入无关类型后重新编译，断言 msg_tag 不变。

**byte-equal 验证：** 构建 16 个含 Cap 的 deterministic fixture，分别覆盖：

```text
2 × {无 Cap, 有 Cap}
× {debug, release}
× {小端, freestanding target}
× {单线程, 固定并行任务数}
```

比较：

```text
release .capoffsets == debug .capoffsets
capmeta 全部位于 debug-only section
```

**回滚：** 保留旧 `size_of(Cap<T>)=16` 的 prototype flag；D16 section 仅在 `--ipc=cap` 下 emit。

### 10.3 3g.7：联调与 fixed-point 验收

**目标：** 编译器本体使用 Cap 表达，并同时验证 OS 内核 cap table 布局与 N=3 fixed point。

**修改文件/函数：**

| 位置 | 修改内容 |
|---|---|
| `compiler/src0/*.jhyy` | 将 OS-facing handle 迁移到 `Cap<T>` |
| `codegen.jhyy` | 生成 `__jhyy_capoffset_*` |
| `tests/bootstrap/stage.sh` | 新增 `cap_matrix` |
| `tests/bootstrap/cap_diff.py` | 比较 header、offset、padding、symbol 顺序 |
| `jhyy-abi-v1.0.0.md` | 新增 §13.3 D16 与 §13.2 Cap layout |

**复杂度：** 约 1,200–2,000 行，测试基础设施约 700–1,000 行。

**联调方法：**

1. 内核导出 `__jhyy_capoffset` 地址范围及测试解析器；
2. 用户态编译器生成同一 section；
3. 在 QEMU 中逐项比较：

   ```text
   msg_tag
   n_caps
   cap_offsets
   padding bytes
   ```

4. 使用 `Cap<Endpoint>`、`Cap<File>`、`Cap<Process>` 执行 grant → revoke → 重分配；
5. 验证语言层禁止的类型转换在编译期被拒绝，而内核仍拥有最终否决权。

**回滚：** 内核同时保留旧 raw-u32 测试 shim，feature flag `--legacy-raw-cap` 仅在 CI 双跑，不进入 release。

## 11. 测试矩阵必须同时覆盖语义、ABI 与构建环境

只比较最终二进制无法定位问题：若 Cap 语义错误，输出可能已经不同；若仅 padding 不同，又可能表现为偶发 byte-equal 失败。测试矩阵因此需要把 source、IR、IL、metadata 和并行环境分别隔离。

### 11.1 验收矩阵

| ID | 场景 | 固定条件 | 断言 |
|---|---|---|---|
| B1 | 无 Cap 的 `.il` | 普通 fixture | 与 baseline byte-equal |
| B2 | 有 Cap 的 `.il` | 单一源顺序 | `.il` byte-equal |
| B3 | Cap IPC 改写前后 | 同一 source、mock kernel | D16 解释前后 8 字节值一致 |
| B4 | provenance 开关 | 同 source | release 剥离全部 side table；`.capoffsets` 不变 |
| B5 | 不同 build 目录 | `--canon-source-root` | path index 相同，IL byte-equal |
| B6 | 不同并行度 | `make -j1/-j4/-j8` | worklist/ID/emit 一致 |
| B7 | 新增无关类型 | 插入普通 struct | 既有 `msg_tag` 稳定 |
| B8 | 字段声明顺序变化 | 两个合法版本 | D16 offset 相应变化，且生成器拒绝混用旧 header |
| B9 | padding | 读取 raw bytes | offset 5 的字节始终为零 |
| B10 | 类型白名单 | `cap<int>`、`cap<*Page>` | 编译错误 |
| B11 | linear move | `let a=b; b.use()` | `E-cap-moved` |
| B12 | `&mut` 独占 | shared + mut 活跃 | `E-cap-aliasing` |
| B13 | revoke | 未使用后的 `revoke` | warning→deny 可切换 |
| B14 | N=3 fixed point | `jhyy_2/.il`、`jhyy_3/.il` | `diff` 为空 |
| B15 | FFI 边界 | struct 按值跨 extern | 拒绝 Cap 字段 |
| B16 | unsafe_cap | 无 WaiverCap | runtime abort；有 WaiverCap 放行并告警 |

**通过条件：**

- B1–B9 全部 `.il`/`.s` byte-equal；
- B14 保持现有 N=3 fixed point；
- B10–B13 的诊断稳定；
- B15–B16 的 release 与 debug 在 Cap 安全属性上等价。

建议 CI 中每次提交运行两遍：第一遍正常构建，第二遍打乱源文件枚举和并行任务顺序。任何一侧失败都必须定位到非确定性 ID、遍历顺序或诊断收集逻辑。

## 12. 风险集中在 ID 稳定性、撤销盲区与 IPC 边界

Cap 系统的大部分风险都不是“是否实现某个特性”，而是特性之间是否形成契约：msg_tag 与 ID 生成必须一致，linear 与 borrow 必须同一 env，revoke 与内核对象生命周期必须联动，debug metadata 与 release ABI 必须可剥离而不改变协议。

### 12.1 风险与缓解策略

1. **无 Drop 导致 revoke 遗忘。**  
   静态检测只能看到显式 use，无法证明内核对象生命周期。  
   **缓解：** `#[must_revoke]` lint + `revoke_all` 作用域宏 + kernel audit log；不自动 revoke。

2. **`&mut` 与 raw pointer 混用。**  
   过渡期旧 OS 代码大量使用 `*mut T`。  
   **缓解：** `unsafe_cap` 作为唯一 raw escape，记录 WaiverCap；提供 `&mut_cap!` 宏；先对 Cap 字段禁用 `as *mut`。

3. **cap-offset 表与 FFI 不兼容。**  
   struct/enum 当前不能按值跨 FFI。[2]  
   **缓解：** D16 仅在 `#[ipc_msg]` 类型上生成；extern 参数拒绝含 Cap 的聚合，只接受指针。

4. **msg_tag 全局唯一性。**  
   当前 3g 只能保证编译单元稳定。  
   **缓解：** `msg_tag = stable_hash(...)` 推迟到 3i；3g 使用连续 ID 并冻结版本 1 schema。

5. **debug/release 行为差。**  
   provenance 在 release 中被 strip。  
   **缓解：** 能力语义不依赖 provenance；CI 同时运行 `debug∩release` 的 D16 测试。

6. **linear 检查与宏展开顺序耦合。**  
   当前宏系统仍未稳定。  
   **缓解：** linear check 在 expansion 之后、HIR 阶段运行；所有宏测试先展开为 MIR 再比对。

7. **Cap 作为 struct 字段的递归 layout。**  
   嵌套消息和递归类型可能造成 D16 offset 爆炸。  
   **缓解：** 禁止递归 Cap 聚合；layout pass 设置深度上限；`#[ipc_msg]` 必须显式标注。

8. **跨 crate type id 稳定性。**  
   未来模块或包可能复用 canonical name。  
   **缓解：** 3i 引入 package-version 命名空间；当前断言禁止跨编译单元重复 canonical name。

9. **CHERI 缺失下的内存伪造。**  
   raw write 可能构造非法 8 字节值。  
   **缓解：** unsafe 审计 + WaiverCap；内核 copy-in/copy-out 验证 cnode/rights；明确写入 M4 威胁模型。

10. **ID/哈希随机化破坏 byte-equal。**  
   默认 HashMap 或 SipHash 密钥变化均可能改变顺序。  
    **缓解：** 禁用非确定性容器；固定 hash seed；所有排序通过 property test。

11. **空 Cap 与 move 交互。**  
    `null` 可能被误当作可消费授权。  
    **缓解：** `is_valid` 不改变 linear state；`revoke(null)` 为 safe no-op，但受权限约束。

12. **grant/revoke 传播缺失。**  
    派生 Cap 撤销不能自动传播。  
    **缓解：** 当前记录 known limitation；后续采用 seL4 式 derivation tree，不在 3g 承诺。[1]

## 13. 文档修订必须冻结同一套 canonical 规则

当前项目文档已经足以指导实现，但若干表述若不修正，会导致 spec、sema 与 codegen 各自采用不同“事实源”。本节列出的不是可选建议，而是保证 3g/3g.5/3g.7 可实现的必要修订。

### 13.1 需要修订的具体位置

| 文档 | 位置 | 当前表述/风险 | 建议结论 |
|---|---|---|---|
| `v0.0.1-capability.md` | §1 layout | `_phantom:*T` 已正确；建议明确 `TypeLayout ≠ AbiLayout` | 增加 “ABI layout 由 layout pass 派生；sema 保留 phantom” [1] |
| `v0.0.1-capability.md` | §2 `derive/grant/revoke` | 当前未定义线性 kill 规则 | 新增 judgment 与 “3g 不实现 propagation” [1] |
| `v0.0.1-capability.md` | §7 编译器约束 (e)(g) | 将 D16/provenance 映射至 3g/3g.5 | 与 sprint 拆分表对齐 [1] |
| `v0.0.4-debug-abi.md` | §5/§7 | provenance 已 lock；需说明 `CapId` 不是 `msg_tag` | 增加 stable `CapId` 算法与 release strip 断言 [5] |
| `v3.x-capability-spec.md` | §8 规则 3/7 | 引用未来 `Move` trait | 改为 3g hardcoded linear pass；保留 3i 迁移说明 [4] |
| `v3.x-capability-spec.md` | §Memory layout | 明确 offset 5 padding 由 codegen 管理 | 增加 padding node/zero-init 不变量 [4] |
| `v0.0.1-syscall-abi.md` | §1.1.4 D16 | 已锁定；缺少 IL/`.s` 语法 | 采用本报告 §6 IL/符号提案，增加 linker GC 说明 [3] |
| `v0.0.2-foundation-revision.md` | §3.2 | region types primary，Cap linear | 增加 “Cap 借用使用 3g minimal borrow region” [2] |
| `jhyy-abi-v1.0.0.md` | §13（待增） | Cap wire/D16 尚无 canonical 文本 | 在 §13.2/§13.3 纳入 8 字节 layout、D16、padding [2] |
| `v2.x-qbe-rewrite.md` | §5 | 已有排序遍历、stable hash | 增加 CapId/msg_tag/CapOffsetTable 三张 ID ledger [2] |

## 14. 最终交付边界：编译器生成正确协议，内核保持最终授权权威

jhyy `Cap<T>` 的正确实现不取决于把更多安全检查推入语言层，而取决于让每层只承担自己能够证明的责任：

- **类型层：** 证明 `T` 的区分、`_phantom` 的存在以及值未被非法转换；
- **线性层：** 证明每个 Cap 沿明确 use/kill 链移动；
- **layout/ABI 层：** 证明运行时始终为 8 字节，padding 明确且为零；
- **IPC 层：** 通过稳定 `msg_tag` 与 D16 offset 告诉内核在哪里改写；
- **运行时层：** 通过 debug-only provenance 支持诊断，但不把 confidence 变成授权；
- **内核层：** 对 cnode、rights、revocation 和对象生命周期保持最终裁决权。

按 3g → 3g.5 → 3g.7 的顺序，分别交付：

1. linear/borrow sema；
2. layout、D16 与确定性 provenance；
3. fixed-point 与 OS 联调。

只要所有 ID、section、IL 与 `.s` 输出都从规范排序的输入派生，本方案就能与现有 N=3 byte-equal 闭环共存。反之，任何直接依赖遍历顺序、哈希实现、地址或构建时间的“捷径”，即使短期内输出一致，也必须视为不可接受的风险。

M4 论证不应承诺“软件 phantom + linear type 处处等价于 CHERI”，而应准确表述为：

> 在用户态遵守类型、线性与 unsafe 门控的前提下，本方案排除授权混淆和非法句柄构造；对内存完整性、对象生命周期与跨域传播，仍由内核及未来硬件能力机制兜底。

这一表述既不夸大当前方案，也为 seL4 式 revocation propagation、CHERI 扩展和未来真泛型迁移保留 add-only 演进空间。

## 数据来源

[1] **v0.0.1 Capability 设计文档（项目 ground truth）**  
`/data/inputs/v0.0.1-capability.md`

[2] **v0.0.2 Foundation Revision（项目 ground truth）**  
`/data/inputs/v0.0.2-foundation-revision.md`

[3] **v0.0.1 Syscall ABI / D16（项目 ground truth）**  
`/data/inputs/v0.0.1-syscall-abi.md`

[4] **v3.x Capability Specification（项目 ground truth）**  
`/data/inputs/v3.x-capability-spec.md`

[5] **v0.0.4 Debug ABI（项目 ground truth）**  
`/data/inputs/v0.0.4-debug-abi.md`

[6] **CompCert 编译器概览（清华大学软件学院镜像）**  
https://soft.cs.tsinghua.edu.cn/~dongyuan/docs/compcert-2010.pdf

[7] **seL4 Capabilities and System Calls**  
https://sel4.systems/Info/Docs/seL4-kernel-manual-13.0.0.pdf

[8] **CHERI Technical Report：Capability Validity、Bounds and Provenance**  
https://www.cl.cam.ac.uk/techreports/UCAM-CL-TR-941.pdf

[9] **Rust Documentation — PhantomData**  
https://doc.rust-lang.org/std/marker/struct.PhantomData.html

[10] **Reproducible Builds — SOURCE_DATE_EPOCH**  
https://reproducible-builds.org/docs/source-date-epoch/

[11] **Soft Typing（南京大学）**  
https://cs.nju.edu.cn/_upload/tpl/00/aa/170/template170/analysis/softtyping.pdf

[12] **Formal Verification of a Realistic Compiler（清华大学软件学院）**  
https://soft.cs.tsinghua.edu.cn/~dongyuan/verify/compcert.html

[13] **CompCert 编译器手册入口（检索材料）**  
https://compcert.org/man/compcertb-2.1.0/Compcert.html

[14] **24 小时快速入门 Rust：Copy、Clone 与引用借用**  
https://new.qq.com/rain/a/20251013A061I200