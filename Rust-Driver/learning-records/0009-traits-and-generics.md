# 第九课聚类：trait 与泛型——从契约到 Box&lt;dyn Error&gt;（2026-11-02）

本记录覆盖第九课 CP1–CP3 的笔记批阅、追问、探针与项目验收；第九课已结课。对应课程：[lessons/0009-traits-and-generics.html](../lessons/0009-traits-and-generics.html)。

## 一、CP1 弧线

### 笔记 1：trait 契约与两种分发

**初版要点**：trait 是行为契约、不是父类；`impl ButtonInput for FakePin` 让 FakePin 满足契约；trait 只描述“能做什么”，不能有字段、不能直接当值类型；静态/动态分发表覆盖了编译期、运行期、决定时机与依据。

**必须修正的点**：

- “trait 类似泛型”把两个轴混在一起：trait 是契约，泛型是参数化代码，`<B: ButtonInput>` 才是结合点。
- “impl 添加了函数签名”不准确：签名在 trait 里，impl 添加方法体；方法头必须与签名兼容。
- “FakePin 是 ButtonInput 的一种实现”容易读成子类型；应说“满足契约”，没有字段/布局/继承变化。
- 表格把“构造 trait object”放在编译期：编译期只确定 vtable、生成构造胖指针的代码；运行期在 coercion 点组装数据指针 + vtable 指针。
- “谁决定调用哪份代码”写成“静态分发 / 动态分发”只是重复列名；应写“编译器（单态化）” vs “运行期 vtable”。
- 缺少 CP1 要求的 `Option<T>` / `ButtonEvent` 对比；补为“类型/枚举可以有值；trait 是契约，不能直接有值；`dyn Trait` 是 unsized trait object”。

**修订后通过**：trait 是契约；impl 提供方法体；bound 是编译期约束；静态分发由编译器单态化决定，动态分发由运行期 vtable 决定。

### 笔记 2：Box&lt;dyn Error&gt;

**初版要点**：`dyn` 类型擦除、`Box` 拥有堆值、`Error` 提供错误契约；`Error: Debug + Display` 是 supertrait 前置条件；`?` 负责装箱；`main -> Result<(), Box<dyn Error>>` 能编译。

**必须修正的点**：

- `?` 不是 `Box::from(e)`，而是 `From::from(e)`；目标为 `Box<dyn Error>` 时才由标准库的 `From<E> for Box<dyn Error>` 装箱。
- “标准库为 Result 实现了 Termination”不完整：是 `impl<T: Termination, E: Debug> Termination for Result<T, E>`；`main` 里 `T = ()`，`E = Box<dyn Error>` 满足 `Debug`，所以整体满足。
- 补充运行期行为：`Ok(())` 退出 0；`Err(e)` 用 Debug 打印 `Error: ...`，退出 1。

**修订后通过**：`dyn` 擦除类型、`Box` 拥有堆值、`Error` 是 `Debug + Display` 契约；`?` 走 `From`；Termination 的条件明确。

### 笔记 3：标准库 trait 落点

**初版亮点**：`Debug` / `Display` / `From` / `Termination` 的落点表完整；`map_err` vs `From` 的对照清楚；errors6 保留 `ParseIntError` 的理由（API 契约、可匹配、可诊断）很到位；库代码自定义枚举 vs main 用 `Box<dyn Error>` 的决策表质量高。

**必须修正的点**：

- `fn main() -> Result<(), E: Debug>` 不是合法签名；`E: Debug` 是约束，不能写进返回类型。正确是 `fn main() -> Result<(), E>` 且 `E: Debug`，或直接 `Result<(), Box<dyn Error>>`。
- `?` 的自动转换只适用于 Result；Option 的 `?` 直接返回 None，不走 From。
- `map_err` 与 `collect` 没有固定关系；它是任何 `Result` 上的方法。
- errors5 的 `CreationError` 是 enum `{ Negative, Zero }`，不是 unit struct；`impl Display` 要用 `fmt::Display` / `fmt::Formatter` / `fmt::Result`，或先 `use std::fmt;`。
- `Box<dyn Error>` 的 Debug 来自 `Error: Debug`，不是 Box 额外要求。
- Fn 层级解释“能多次只读调用 → 当然能多次可变调用”容易误解；应说 `Fn` 也满足 `FnMut` 的 `&mut self` 调用方式，`FnMut` 不要求真的修改捕获。

**修订后通过**：四种 std trait 的落点、`map_err` vs `From`、errors6 的保留原因、库 vs main 的决策表都成立。

### 笔记 4：闭包三张门牌

**初版亮点**：`Fn` / `FnMut` / `FnOnce` 的接收者、调用次数、捕获操作表正确；`Fn: FnMut: FnOnce` 的包含关系正确；计数闭包至少是 `FnMut` 的推理正确；`thread::spawn` 的 `FnOnce + Send + 'static` 正确。

**必须修正的点**：

- `let f: impl Fn() -> i32 = ...` 等写法实测 E0562：`impl Trait` 不允许出现在变量绑定的类型位置；只允许在函数/方法参数和返回类型等位置。正确做法是去掉类型标注，让闭包自己推断；约束写到泛型函数参数上。
- “Fn 能多次只读调用 → 当然能多次可变调用”措辞改为“Fn 也满足 FnMut 的调用方式；FnMut 不要求修改捕获”。
- `h()` 不能第二次调用，原因是调用 `h()` 消耗了闭包，捕获的 `name` 也随之外移；不只是“name 被 move 出”。

**修订后通过**：三张门牌、包含关系、FnMut 推理与 FnOnce 例子都成立。

### 探针验收

探针文件在 [demo/trait-probe/](../demo/trait-probe/README.md)，用 rustc 1.99.1 / edition 2021 实测。按用户请求，探针由 AI 代跑并留证；CP2 起由用户自己完成。

- **探针 A**：`generic: real=pressed fake=released`、`dyn: pressed`、`dyn: released`；无 bound 的 `no_bound.rs` 实测 E0599，help 指向 `: ButtonInput`。
- **探针 B**：`box_error.rs` 实测 `Error: ParseIntError { kind: InvalidDigit }`、`exit=1`；打印的是 Debug，不是 Display。
- **闭包修正版**：`fn_probe.rs` 实测 `Fn: 5 5`、`FnMut: (1, 2)`、`FnOnce: hi`。
- **Termination 修正版**：`termination_fix.rs` 编译通过，exit 0。

## 二、关键心智模型

### 1. trait 是契约，不是类型/父类

- `trait` 声明行为；`impl` 提供方法体；签名在 trait，方法头必须兼容。
- 具体类型满足契约，不是变成 trait 的子类型；没有字段继承、没有布局变化。
- trait 不能有数据字段；可以有默认方法（`impl Error for CreationError {}` 空 impl）。
- trait 本身不能直接有值；`dyn Trait` 是 unsized trait object，必须在 `&` / `Box` 后。

### 2. bound 是编译期能力清单

- `B: ButtonInput` 是 trait bound，不是关键字，不是运行期检查。
- 泛型函数内只能使用 bound 保证的方法；具体类型可以有更多方法，但泛型代码不能依赖。
- 无 bound → E0599（方法找不到）；调用点类型不满足 → E0277（trait bound 不满足）。
- `where B: ButtonInput` 等价。

### 3. 两种分发

| 阶段 | 静态分发 | 动态分发 |
|---|---|---|
| 编译期 | 单态化，为每个具体类型生成特化代码 | 确定 vtable，生成构造胖指针的代码 |
| 运行期 | 直接调用，无分发开销 | 组装胖指针；每次查 vtable + 间接调用 |
| 谁决定 | 编译器（单态化） | 运行期 vtable |
| 依据 | 调用点具体类型 | 胖指针里的 vtable |

- `&dyn` / `Box<dyn>` 是胖指针：数据 + 函数表；与切片“地址 + 长度”同构。
- 编译期确定 vtable/生成代码，运行期在 coercion 点组装胖指针。

### 4. Box&lt;dyn Error&gt; 的组成

- `dyn Error`：类型擦除，保留 vtable。
- `Box`：拥有堆上的 trait object。
- `Error`：契约，要求 `Debug + Display`（supertrait）。
- `?` → `From::from(e)`；目标为 `Box<dyn Error>` 时标准库负责装箱。
- `Result<T, E>: Termination` 的条件是 `T: Termination, E: Debug`；`main` 里 `T = ()`，`E = Box<dyn Error>` 满足 Debug。
- Ok 退出 0；Err 打印 Debug `Error: ...`，退出 1。
- 库代码优先自定义错误枚举；main 可以 Box；no_std 无堆，用自定义枚举。

### 5. 闭包三张门牌

- `Fn`：`&self`，只读，多次。
- `FnMut`：`&mut self`，可改，多次。
- `FnOnce`：`self`，消耗，一次。
- `Fn: FnMut: FnOnce`；`Fn` 也满足 `FnMut` 的调用方式，但 `FnMut` 不要求修改捕获。
- `impl Trait` 不能出现在 let 类型标注（E0562）；让闭包推断，或把约束写到泛型函数参数。

## 三、学习者信号与教学含义

- **表格综合能力强**：静态/动态分发表、std trait 落点表、库 vs main 决策表都抓到了主干；修正的是机制时点和条件，不是整体框架。
- **Java 迁移痕迹明显**：“接口/泛型实现/重写”这些词会把 Rust 的 trait/impl/泛型三个轴揉在一起。后续继续用 Rust 术语替换：契约、实现、类型参数、约束。
- **对语法位置敏感但需要显式提示**：`impl Trait` 放错到 let 注解，是“知道概念但不知道语法位置”的典型；用 E0562 和“参数/返回位置”对照一次即可。
- **容易把条件写成简写**：`E: Debug` 被写进返回类型；这不是理解错，而是把“约束”压缩成了签名。教学上要求把条件写成独立句子或表格列，避免混入语法。
- **API 设计判断成熟**：库自定义错误 vs main `Box<dyn Error>`、保留 `ParseIntError` 的理由都正确；可以开始在 CP3 里做实际取舍。
- **探针代跑**：本次按用户请求由 AI 代跑并留证；后续 CP2 的 rustlings 由用户自己跑，避免把“看到输出”当成“自己会写”。

## 四、CP2–CP3 弧线

### CP2：rustlings errors4–6

- **errors4**：初版解释“三个分支包装成一个 Result”不准确；修正为三个分支各自直接构造 `Ok`/`Err`，`match` 选出其中一个返回。
- **errors5**：初版只说“因为 `impl Error for CreationError`”，漏了 `ParseIntError` 也实现 `Error`、`?` 通过 `From::from` 装箱 `Box<dyn Error>`、以及 `Result<T: Termination, E: Debug>` 的 Termination 条件；二次解释补齐。
- **errors6**：`from_parse_int` 保留 `ParseIntError`，`parse` 用 `map_err` 转换；能说出 `e.kind()` / 调用方匹配变体的价值。
- 验收：errors4/5/6 全部通过，runner 前进到 `generics1`。

### CP3：button-model

- 在 `demo/button-model` 加 `ButtonInput` trait、`RealPin`/`FakePin` 两个 impl、泛型 `read_button` 与 `Vec<(&dyn ButtonInput, u32)>`；原 `ButtonState`/`update` 不动。
- 静态分发：`read_button(&real)` / `read_button(&fake)`；动态分发：循环里的 `input.is_pressed()`。
- 初版解释“`&dyn` 长度固定、`B` 长度不固定”是错的；修正为 `Vec<T>` 要求同一具体元素类型，`&dyn ButtonInput` 是同一个胖指针类型，可指向不同实现；不是长度问题。
- 初版把“动态分发”归给 `vec![...]`；修正为 Vec 只是异构容器，真正的动态分发发生在 `input.is_pressed()`。
- 输出保持四行不变：四采样 bool 序列仍为 false→true→true→false，状态机逻辑未变，`assert!` 无输出。
- 验收：`cargo fmt` / `cargo check` / `cargo run` 通过；修复尾随空格，`_` 收窄为 `None`。

## 五、下一步

- 第九课 CP1–CP3 全部通过；术语表已晋升 trait / bound / 单态化 / 静态分发 / 动态分发 / trait object / `Box<dyn Error>` / Termination / Fn 三 trait 等 19 条（语言核心 43 → 62 词条）。
- 下一课按长期路线进入生命周期与集合；`hashmaps1–3` 仍暂跳，等集合课补。
- CP2/CP3 已完成，不再重复布置；后续练习继续遵守“代码通过 ≠ 解释通过”。
