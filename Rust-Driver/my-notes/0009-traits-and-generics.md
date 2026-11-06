# 第九课学习笔记：trait 与泛型

> 整理自第九课 CP1–CP3 的笔记、追问、探针与项目验收（原笔记为即时问答，已按主题重组，误区处标注“曾误→正解”）。
> 配套材料：课程 [lessons/0009-traits-and-generics.html](../lessons/0009-traits-and-generics.html) · 术语表 [reference/glossary.html](../reference/glossary.html) · 探针 [demo/trait-probe/README.md](../demo/trait-probe/README.md) · 项目 [demo/button-model/src/main.rs](../demo/button-model/src/main.rs)
>
> 状态：**CP1–CP3 全部通过，第九课结课**。

---

## 一、trait：行为契约，不是泛型，也不是父类

### 1. 定义与实现

```rust
trait ButtonInput {
    fn is_pressed(&self) -> bool;
}

struct RealPin { pin: u8 }
struct FakePin { pressed: bool }

impl ButtonInput for RealPin {
    fn is_pressed(&self) -> bool {
        self.pin == 15
    }
}

impl ButtonInput for FakePin {
    fn is_pressed(&self) -> bool {
        self.pressed
    }
}
```

- `trait` 是**行为契约**：它声明“能做什么”，不保存数据。
- `impl ButtonInput for FakePin` 添加的是**方法体/实现**；方法签名已经在 trait 里，impl 的方法头必须兼容。
- `FakePin` 是“满足 `ButtonInput` 契约”，不是 `ButtonInput` 的子类型；没有字段继承，也没有布局变化。
- `Self` 在 trait 里指实现它的具体类型；在 `impl ButtonInput for RealPin` 里，`Self` 就是 `RealPin`。
- 一个类型可以实现多个 trait；trait 也可以有 supertrait，例如 `Error: Debug + Display`。
- trait 不能有数据字段；可以有默认方法（`impl Error for CreationError {}` 能空着就是这个原因）。

**曾误**：trait 类似泛型的一种行为契约。  
**正解**：trait 是契约，泛型是参数化代码；两者是两个轴，`fn describe<B: ButtonInput>` 才是把 trait 作为泛型约束接起来。

**曾误**：`impl` 添加了“函数签名”。  
**正解**：签名在 trait 里，`impl` 添加方法体；方法头必须与 trait 的签名兼容。

### 2. trait 与类型/枚举的区别

- `Option<T>` 是泛型枚举类型，`ButtonEvent` 是具体枚举类型；它们都可以有值（`None` / `Some(...)`、`Pressed` / `Released` 等）。
- `ButtonInput` 是 trait（契约），**不能直接有值**；值属于实现它的具体类型 `RealPin` / `FakePin`。
- `dyn ButtonInput` 是另一件事：它是 **unsized 的 trait object 类型**，必须放在 `&` / `Box` 后面；这不是“trait 本身有值”。
- Java 接口可以直接当引用类型用；Rust 的 trait 本身不行，要用 `dyn Trait` 或具体实现类型。

**曾误**：trait 像 Java 接口，所以能直接当类型用。  
**正解**：契约部分像 Java interface；但 Rust 的 trait 本身不是可创建值的具体类型，`dyn Trait` 才是 trait object 类型，而且要在指针后面。

---

## 二、bound：泛型参数的编译期约束

```rust
fn describe<B: ButtonInput>(button: &B) -> &'static str {
    if button.is_pressed() {
        "pressed"
    } else {
        "released"
    }
}
```

- `B` 是**类型参数**（type parameter）。
- `B: ButtonInput` 整体是 **trait bound**（trait 约束），读作“B 受 ButtonInput 约束”。
- `bound` 不是 Rust 关键字，而是英文术语；也可以写成：

```rust
fn describe<B>(button: &B) -> &'static str
where
    B: ButtonInput,
```

- bound 是**编译期**要求：调用者传入的具体类型必须实现 `ButtonInput`；函数体内只能依赖 bound 保证的方法。
- “编译期的能力清单”这个比喻的准确含义：**泛型函数内部只能使用 bound 保证的方法**；具体类型可能还有别的方法，但泛型代码不能依赖它们。
- 没有 bound 时，`button.is_pressed()` 报 **E0599**（方法找不到）；调用点传入不满足约束的类型则报 **E0277**（trait bound 不满足）。

**曾误**：`B` 只是一个普通标识符。  
**正解**：`B` 是类型参数；`button: &B` 的 `B` 是同一个参数的使用；`.is_pressed()` 由 bound 在编译期保证可用，具体执行哪个 impl 由具体类型在编译期决定（静态分发）。

---

## 三、静态分发 vs 动态分发

| 阶段 | 静态分发 `<B: ButtonInput>` | 动态分发 `&dyn` / `Box<dyn>` |
|---|---|---|
| 编译期 | 类型检查；单态化为每个具体 `B` 生成特化代码，调用目标确定 | 类型检查；确定 vtable，生成“构造胖指针”的代码 |
| 运行期 | 直接调用，无运行期分发开销；代码体积可能增大 | 在 coercion 点组装胖指针；每次调用查 vtable + 间接调用 |
| 谁决定调用哪份代码 | **编译器（单态化）** | **运行期通过 vtable** |
| 决定时机 | 编译期 | 运行期 |
| 依据 | 调用点的具体类型 `B` | 胖指针里携带的 vtable 指针 |

- **编译期**只确定 vtable、生成“构造胖指针”的代码；**运行期**执行到 coercion 点才真正组装数据指针 + vtable 指针。
- `&dyn` 借用；`Box<dyn>` 拥有堆上的 trait object。
- `&dyn Trait` / `Box<dyn Trait>` 是**胖指针**：数据指针 + 函数表指针；与切片 `&[u8]` 的“地址 + 长度”同构。
- 本机 x86_64 实测：`Box<RealPin>` 8 字节；`&dyn ButtonInput`、`Box<dyn ButtonInput>`、`&[u8]` 都是 16 字节。
- 把 `&Box<dyn T>` 传给 `&dyn T` 参数时要显式解引用：`as_ref()` 或 `&**`；方法调用会自动解引用。
- 对象安全：不是所有 trait 都能 `dyn`；`ButtonInput` 和 `Error` 可以，完整规则以后再说。

**曾误**：trait object 是编译期构造出来的。  
**正解**：编译期确定 vtable、生成构造代码；运行期在 coercion 点组装胖指针。

**曾误**：“谁决定调用哪份代码”就是“静态分发 / 动态分发”。  
**正解**：静态分发由编译器（单态化）决定；动态分发由运行期 vtable 决定。

---

## 四、`Box<dyn Error>` 与错误 trait

### 1. 三个角色

- `dyn Error`：类型擦除，保留 vtable，所以还能调用 `Error` 的方法。
- `Box`：拥有堆上的 trait object，离开作用域时释放。
- `Error`：错误契约，要求实现者同时满足 `Debug + Display`。

### 2. `Error: Debug + Display` 是 supertrait

```rust
pub trait Error: Debug + Display {
    // 默认方法由标准库提供
}
```

- `Error` 的契约里写着 `Debug + Display`，所以实现 `Error` 之前必须先有这两个。
- errors5 的 `CreationError` 是 enum，不是 unit struct：

```rust
#[derive(PartialEq, Debug)]
enum CreationError {
    Negative,
    Zero,
}

impl fmt::Display for CreationError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let description = match self {
            CreationError::Negative => "number is negative",
            CreationError::Zero => "number is zero",
        };
        f.write_str(description)
    }
}

impl Error for CreationError {}
```

- `impl Error for CreationError {}` 是空 impl：`Error` 的默认方法由标准库提供；只要 `Debug + Display` 已经满足，空 impl 就表示承诺实现契约。
- 缺 `Display` 时，`impl Error` 会报 E0277。

### 3. `?` 与 `From`

`?` 的通用展开是：

```rust
let x = match expr {
    Ok(v) => v,
    Err(e) => return Err(From::from(e)),
};
```

- 目标错误类型是 `Box<dyn Error>` 时，标准库的 `From<E> for Box<dyn Error>` 把 `e` 装箱。
- 写成 `Box::from(e)` 是这一种情况的具体化，不是 `?` 的通用规则；通用规则是 `From::from(e)`。
- 严格说，这个 `From` 还要求 `E: Error + 'static`；errors5 的两个错误类型都满足，生命周期细节先记账。
- Option 的 `?` 不用 `From`：失败时直接 `return None`。

### 4. `Termination` 是有条件的

标准库的 impl 大致是：

```rust
impl<T: Termination, E: Debug> Termination for Result<T, E> {
    // ...
}
```

所以 `main -> Result<(), Box<dyn Error>>` 能编译，是因为：

- `T = ()`：`()` 实现 `Termination`；
- `E = Box<dyn Error>`：它实现 `Debug`（因为 `Error: Debug`，`Box` 会把 `Debug` 转发给内部的 `dyn Error`）；
- 因此整个 `Result<(), Box<dyn Error>>` 满足 `Termination`。

运行期：

- `Ok(())` → 退出码 0；
- `Err(e)` → 打印 `Error: {e:?}`（**Debug**），退出码 1。

**曾误**：`fn main() -> Result<(), E: Debug>` 是合法签名。  
**正解**：`E: Debug` 是约束，不能写在返回类型里。正确写法是 `fn main() -> Result<(), E>` 并让 `E` 实现 `Debug`，或直接 `Result<(), Box<dyn Error>>`。

**曾误**：`main` 的错误打印走 `Display`。  
**正解**：走 `Debug`；`Display` 是 `{}` 的用户消息。`-5` 输出 `Error: Negative`，不是 `"number is negative"`。

### 5. errors5 的输出

| 输入 | 输出 | 退出码 |
|---|---|---|
| `42` | `output=PositiveNonzeroInteger(42)` | 0 |
| `-5` | `Error: Negative` | 1 |
| `abc` | `Error: ParseIntError { kind: InvalidDigit }` | 1 |

### 6. `map_err` vs `From`

```rust
// 当前 WoL：手动转换，把 ParseIntError 统一映射成 NonHex
bytes[i] = u8::from_str_radix(part, 16)
    .map_err(|_| MacError::NonHex)?;
```

- `map_err` 是 `Result` 的方法，在任何 `Result` 上就地转换；它和 `collect` 没有固定关系。
- `map_err(|_| ...)` 会把“空串 / 非法字符 / 溢出”全归为同一个变体，信息有损。
- `From` 是集中转换：实现一次，`?` 自动调用；如果变体里存了原始错误（如 `Parse(e)`），可以保留 `e.kind()`。
- `From` 具体保留多少信息，取决于你定义的变体；`From` 本身不会自动保留。
- 库代码优先自定义错误枚举：调用方能 match 具体变体，API 稳定，且不强制堆分配。
- `main` 是错误传播终点，可以 `Box<dyn Error>`：自动装箱、只需打印后退出。
- 固件 `no_std` 没有堆分配器，`Box` 用不了；那里用自定义错误枚举。

---

## 五、闭包三张门牌：`Fn` / `FnMut` / `FnOnce`

| trait | 调用接收者 | 对捕获的操作 | 可调用次数 |
|---|---|---|---|
| `Fn` | `&self` | 只读 | 任意多次 |
| `FnMut` | `&mut self` | 可变借用 | 任意多次 |
| `FnOnce` | `self` | 消耗 / move | 仅一次 |

### 1. 正确写法：不要在 let 注解里写 impl Trait

**曾误**：

```rust
let f: impl Fn() -> i32 = || x;   // E0562
```

实测：

```text
error[E0562]: `impl Trait` is not allowed in the type of variable bindings
note: `impl Trait` is only allowed in arguments and return types of functions and methods
```

中文对照：`impl Trait` 不允许出现在变量绑定的类型位置；只允许在函数/方法的参数和返回类型等位置。

**正解**：去掉类型标注，让闭包自己实现 trait：

```rust
let x = 5;
let f = || x;          // Fn
f(); f();

let mut count = 0;
let mut g = || count += 1;   // FnMut
g(); g();

let s = String::from("hi");
let h = move || s;     // FnOnce
h();
// h();                // E0382：h 已被移走
```

### 2. 为什么计数闭包至少是 FnMut

- `count += 1` 需要 `&mut count`。
- 每次调用闭包，都要通过 `&mut self` 访问捕获的 `count`。
- `Fn` 只提供 `&self`，只能读，不能改，不够。
- `FnMut` 提供 `&mut self`，刚好够。
- 规则：闭包对捕获变量的“最强操作”决定它的最低 trait：只读 → `Fn`；修改 → `FnMut`；消耗 / move → `FnOnce`。

### 3. 包含关系

```text
Fn  ⊂  FnMut  ⊂  FnOnce
(最严格)          (最宽松)
```

- `Fn: FnMut`，`FnMut: FnOnce`。
- `Fn` 闭包也满足 `FnMut` 的 `&mut self` 调用方式；`FnMut` 不要求真的修改捕获。
- 要求 `F: FnOnce` 的函数能接受任何闭包；要求 `F: Fn` 的函数只能接受 `Fn` 闭包。

```rust
fn call_once<F: FnOnce()>(f: F) { f(); }        // 接受三种
fn call_mut<F: FnMut()>(mut f: F) { f(); f(); } // 接受 Fn / FnMut，不接受纯 FnOnce
fn call_many<F: Fn()>(f: F) { f(); f(); }       // 只接受 Fn
```

### 4. FnOnce 例子

```rust
let name = String::from("Rust");
let take = move || name;
let s = take();      // ✅ 一次；take 被消耗
// take();           // ❌ E0382
```

```rust
let data = vec![1, 2, 3];
let handle = std::thread::spawn(move || {
    data.into_iter().sum::<i32>()
});
```

`thread::spawn` 要求 `F: FnOnce() + Send + 'static`：线程只运行一次，且要 move 捕获进去。

**曾误**：`Fn` 能“多次只读调用”，所以“当然能多次可变调用”。  
**正解**：`Fn` 闭包也满足 `FnMut` 的调用方式；`FnMut` 只要求能通过 `&mut self` 调用，不要求真的修改捕获值。

---

## 六、CP1 探针证据

探针文件与完整命令见 [demo/trait-probe/README.md](../demo/trait-probe/README.md)。以下是在 rustc 1.99.1 / edition 2021 下的实测结果。

### 1. 探针 A

```bash
cd Rust-Driver/demo/trait-probe
rustc --edition 2021 trait_demo.rs -o trait_demo.exe
./trait_demo.exe
```

```text
generic: real=pressed fake=released
dyn: pressed
dyn: released
```

无 bound 的负例 `no_bound.rs` 编译失败：

```text
error[E0599]: no method named `is_pressed` found for reference `&B` in the current scope
help: items from traits can only be used if the type parameter is bounded by the trait
help: ... restrict type parameter `B` with trait `ButtonInput`
```

### 2. 探针 B

```bash
rustc --edition 2021 box_error.rs -o box_error.exe
./box_error.exe; echo "exit=$?"
```

```text
Error: ParseIntError { kind: InvalidDigit }
exit=1
```

这里打印的是 **Debug**；`?` 通过 `From::from(e)` 把它装箱成 `Box<dyn Error>`。

### 3. 闭包修正版

```bash
rustc --edition 2021 fn_probe.rs -o fn_probe.exe
./fn_probe.exe
```

```text
Fn: 5 5
FnMut: (1, 2)
FnOnce: hi
```

### 4. Termination 修正版

```bash
rustc --edition 2021 termination_fix.rs -o termination_fix.exe
./termination_fix.exe; echo "exit=$?"
```

```text
exit=0
```

---

## 七、CP2：rustlings errors4–6

状态：errors4、errors5、errors6 全部通过；runner 前进到 `generics1`。

### 1. errors4：自定义错误枚举

```rust
fn new(value: i64) -> Result<Self, CreationError> {
    match value {
        x if x < 0 => Err(CreationError::Negative),
        0 => Err(CreationError::Zero),
        x => Ok(Self(x as u64)),
    }
}
```

- 三个分支**各自直接构造一个 `Result` 值**：负数是 `Err(Negative)`，零是 `Err(Zero)`，正是 `Ok(Self(...))`。
- `match` 选出其中一个作为 `new` 的返回值；不是“三个结果再包装成一个 Result”。

### 2. errors5：Box&lt;dyn Error&gt;

```rust
fn main() -> Result<(), Box<dyn Error>> {
    let pretend_user_input = "42";
    let x: i64 = pretend_user_input.parse()?;
    println!("output={:?}", PositiveNonzeroInteger::new(x)?);
    Ok(())
}
```

为什么能编译：

- `ParseIntError` 和 `CreationError` 都实现了 `Error`；`CreationError` 需要先有 `Debug + Display`，errors5 已提供；
- `?` 在错误类型不同时执行 `From::from(e)`；目标 `Box<dyn Error>` 有标准库的 `From<E> for Box<dyn Error>`，所以两种错误都能装箱；
- `Result<T, E>` 在 `T: Termination, E: Debug` 时实现 `Termination`；这里 `T = ()` 实现 `Termination`，`E = Box<dyn Error>` 实现 `Debug`（因为 `Error: Debug`）。

### 3. errors6：保留原始 ParseIntError

```rust
fn from_parse_int(err: ParseIntError) -> Self {
    Self::ParseInt(err)
}

fn parse(s: &str) -> Result<Self, ParsePosNonzeroError> {
    let x: i64 = s.parse().map_err(ParsePosNonzeroError::from_parse_int)?;
    Self::new(x).map_err(ParsePosNonzeroError::from_creation)
}
```

- 保留 `ParseIntError` 后，调用方可以 `match` 变体或查 `e.kind()`，区分 `Empty` / `InvalidDigit` / `PosOverflow`；
- 只留 `NonHex` 会把所有解析失败压成一个原因，调用方无法针对性处理；
- `map_err` 是显式转换，没有 panic，测试全过。

---

## 八、CP3：button-model trait 集成

文件：[demo/button-model/src/main.rs](../demo/button-model/src/main.rs)

### 1. 新增内容

```rust
trait ButtonInput {
    fn is_pressed(&self) -> bool;
}

struct RealPin { pin: u8 }
struct FakePin { pressed: bool }

impl ButtonInput for RealPin {
    fn is_pressed(&self) -> bool { self.pin == 15 }
}
impl ButtonInput for FakePin {
    fn is_pressed(&self) -> bool { self.pressed }
}

fn read_button<B: ButtonInput>(input: &B) -> bool {
    input.is_pressed()
}
```

`main` 里用一个异构集合驱动原状态机：

```rust
let real = RealPin { pin: 15 };        // true
let fake = FakePin { pressed: false }; // false

assert!(read_button(&real));           // 静态分发
assert!(!read_button(&fake));

let inputs: Vec<(&dyn ButtonInput, u32)> = vec![
    (&fake, 10),
    (&real, 15),
    (&real, 20),
    (&fake, 15),
];

for (input, ms) in inputs {
    let pressed = input.is_pressed();  // 动态分发
    match button.update(pressed, ms) { ... }
}
```

### 2. 静态 vs 动态

- 静态分发：`read_button(&real)` / `read_button(&fake)`；`B` 在编译期推断为 `RealPin` / `FakePin`，单态化，直接绑定。
- 动态分发：循环里的 `input.is_pressed()`；`input: &dyn ButtonInput`，运行期通过 vtable 查实现。
- `Vec<&dyn ButtonInput>` 只是**异构容器**；真正发生动态分发的是那行方法调用，不是 `vec![...]` 本身。

### 3. 为什么 Vec 能装两种类型

- `Vec<T>` 要求所有元素都是**同一个具体类型 T**；`Vec<RealPin>` 不能 `push(FakePin)`，即使两者大小相同。
- `&dyn ButtonInput` 是**同一个类型**：胖指针（数据指针 + vtable 指针，本机 16 字节），可以指向不同具体实现；所以 `Vec<&dyn ButtonInput>` 的元素类型统一，合法。
- 不是“B 的长度不固定”；B 是编译期选定的具体类型，问题在于一个 Vec 只能有一个具体元素类型。

### 4. 输出为什么不变

- 四个采样读出的 bool 序列仍是 `false → true → true → false`；
- `ButtonState` / `update` 的逻辑和 `pin = 15` 没变；
- 两个 `assert!` 不产生输出；
- 所以输出仍是：

```text
no event
pin 15: pressed
pin 15: held 20 ms
pin 15: released
```

验收：`cargo fmt`、`cargo check`、`cargo run` 全部通过；`_` 已收窄为 `None`，`pressed` 后的尾随空格已去掉。

---

## 九、误区清单（曾误→正解）

1. trait 类似泛型 → trait 是契约，泛型是参数化代码；`<B: Trait>` 才是结合点。
2. `impl` 添加函数签名 → 签名在 trait，impl 添加方法体。
3. FakePin 是 ButtonInput 的子类型 → 只是满足契约；没有继承/字段/布局变化。
4. trait 能直接当值类型用 → 不能；`dyn Trait` 是 unsized trait object，要在 `&`/`Box` 后。
5. `bound` 是关键字/运行期检查 → 英文术语；编译期约束。
6. 没有 bound 是运行期才出错 → 编译期 E0599。
7. trait object 在编译期构造 → 编译期确定 vtable/生成代码，运行期组装胖指针。
8. “谁决定调用哪份代码”就是静态/动态 → 编译器（单态化） vs 运行期 vtable。
9. `?` 用 `Box::from(e)` → 通用规则是 `From::from(e)`。
10. `Result` 无条件实现 `Termination` → 需要 `T: Termination, E: Debug`。
11. `fn main() -> Result<(), E: Debug>` → 非法；`E: Debug` 是约束，不是返回类型。
12. `main` 错误打印用 Display → 用 Debug。
13. `map_err` 必须配合 collect → 不；它是任何 `Result` 上的方法。
14. errors5 的 `CreationError` 是 unit struct → 是 enum `{ Negative, Zero }`。
15. `let f: impl Fn(...)` 可以写 → E0562；去掉注解让闭包推断。
16. Fn 能“可变调用” → Fn 也满足 FnMut 的调用方式，但不修改捕获。
17. `h()` 可以调用第二次 → FnOnce 消耗闭包；E0382。

---

## 十、自查问题

1. trait 是什么、不是什么？trait 能有字段吗？默认方法呢？
2. `impl Trait for Type` 添加的是签名还是方法体？方法头必须满足什么？
3. `B: ButtonInput` 里的 `B` 是什么？bound 在编译期做什么？没有 bound 报什么错？
4. 静态分发和动态分发分别在什么时候决定调用哪份代码？trait object 的胖指针在什么时候组装？
5. `Box<dyn Error>` 里 `dyn`、`Box`、`Error` 各贡献什么？`Error: Debug + Display` 是什么意思？
6. `?` 如何把错误装箱成 `Box<dyn Error>`？`From::from(e)` 和 `Box::from(e)` 的区别是什么？
7. `Result` 什么时候实现 `Termination`？`main` 返回 `Err` 时打印 Debug 还是 Display？
8. `map_err` 与 `From` 各适合什么场景？为什么库代码优先自定义错误枚举？
9. `Fn` / `FnMut` / `FnOnce` 的接收者和调用次数分别是什么？计数闭包为什么是 `FnMut`？
10. 为什么 `let f: impl Fn(...)` 会报 E0562？正确写法是什么？
11. 为什么 `fn main() -> Result<(), E: Debug>` 不是合法签名？正确写法是什么？
12. errors4 的三个 `match` 分支各自返回什么？为什么不是“三个结果再包装”？
13. errors5 的 `?` 如何把两种错误装箱？`main -> Result<(), Box<dyn Error>>` 为什么满足 `Termination`？
14. CP3 里 `Vec<RealPin>` 为什么不能放 `FakePin`？`Vec<&dyn ButtonInput>` 为什么可以？哪一行是静态/动态分发？
15. CP3 的输出为什么和第八课完全一致？

---

> 本文件由第九课 CP1–CP3 的问答、批阅、探针与项目验收整理而成；第九课已结课。
