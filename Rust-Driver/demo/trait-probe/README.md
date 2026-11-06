# trait-probe — 第九课 CP1 探针

对应课程：[第九课《trait 与泛型》](../../lessons/0009-traits-and-generics.html)  
对应笔记：[my-notes/0009-traits-and-generics.md](../../my-notes/0009-traits-and-generics.md)  
状态：CP1 证据（2026-11-02，rustc 1.99.1，edition 2021）

这里把 CP1 的两个探针和两处编译修正做成可复跑的小文件。没有 Cargo.toml，直接用 `rustc` 编译，避免为一个练习建项目。

## 文件

| 文件 | 用途 | 预期 |
|---|---|---|
| `trait_demo.rs` | 探针 A：泛型静态分发 + `&dyn` 动态分发 | 三行输出 |
| `no_bound.rs` | 探针 A 负例：删掉 `: ButtonInput` | **故意编译失败**，E0599 |
| `box_error.rs` | 探针 B：最小 `Box<dyn Error>` | 打印 Debug，exit 1 |
| `fn_probe.rs` | 笔记 4 修正版：`Fn` / `FnMut` / `FnOnce` | 三行输出 |
| `termination_fix.rs` | 笔记 3.1 修正版：`E: Debug` 是约束 | 无输出，exit 0 |

## 探针 A：静态分发与动态分发

```bash
cd Rust-Driver/demo/trait-probe
rustc --edition 2021 trait_demo.rs -o trait_demo.exe
./trait_demo.exe
```

实测输出：

```text
generic: real=pressed fake=released
dyn: pressed
dyn: released
```

- `trait_demo.rs` 里 `describe<B: ButtonInput>` 是静态分发：编译期为 `RealPin` / `FakePin` 各生成一份特化代码。
- `describe_dyn(&dyn ButtonInput)` 是动态分发：同一份代码通过胖指针里的函数表处理两个不同具体类型。

负例 `no_bound.rs`：

```bash
rustc --edition 2021 no_bound.rs -o no_bound.exe
```

实测输出（预期失败）：

```text
error[E0599]: no method named `is_pressed` found for reference `&B` in the current scope
help: items from traits can only be used if the type parameter is bounded by the trait
help: ... restrict type parameter `B` with trait `ButtonInput`
```

中文对照：
- 在当前作用域中，引用 `&B` 上找不到名为 `is_pressed` 的方法。
- 只有类型参数被该 trait 约束时，才能使用 trait 中的项。
- 考虑用 `ButtonInput` 约束类型参数 `B`。

## 探针 B：最小 Box<dyn Error>

```bash
rustc --edition 2021 box_error.rs -o box_error.exe
./box_error.exe; echo "exit=$?"
```

实测输出：

```text
Error: ParseIntError { kind: InvalidDigit }
exit=1
```

- 这里打印的是 **Debug**，由 `main` 返回 `Err` 时的 `Termination` 打印，不是 `Display`。
- `?` 在失败时执行 `return Err(From::from(e))`；目标错误类型是 `Box<dyn Error>`，标准库的 `From<E> for Box<dyn Error>` 把 `ParseIntError` 装箱。

## 修复 1：`fn main() -> Result<(), E: Debug>` 不是合法签名

`E: Debug` 是泛型约束，不能写在返回类型里。错误写法：

```rust
fn main() -> Result<(), E: Debug> {
    Ok(())
}
```

正确写法见 `termination_fix.rs`：

```rust
#[derive(Debug)]
struct E;

fn main() -> Result<(), E> {
    Ok(())
}
```

`E` 实现了 `Debug`，所以 `Result<(), E>` 满足 `Termination`。运行：

```bash
rustc --edition 2021 termination_fix.rs -o termination_fix.exe
./termination_fix.exe; echo "exit=$?"
```

```text
exit=0
```

## 修复 2：`let f: impl Fn(...)` 会报 E0562

`impl Trait` 不允许出现在变量绑定的类型标注里：

```rust
let f: impl Fn() -> i32 = || x;   // E0562
```

实测：

```text
error[E0562]: `impl Trait` is not allowed in the type of variable bindings
note: `impl Trait` is only allowed in arguments and return types of functions and methods
```

中文对照：`impl Trait` 不允许出现在变量绑定的类型位置；只允许在函数/方法的参数和返回类型等位置。

正确做法是去掉类型标注，让闭包自己实现 trait：

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

`fn_probe.rs` 用 `FnMut` / `FnOnce` 的泛型参数演示了同一组例子：

```bash
rustc --edition 2021 fn_probe.rs -o fn_probe.exe
./fn_probe.exe
```

```text
Fn: 5 5
FnMut: (1, 2)
FnOnce: hi
```

## CP1 证据清单

- 探针 A：`generic: real=pressed fake=released`、`dyn: pressed`、`dyn: released`；无 bound 的 E0599 原文与中文对照。
- 探针 B：`Error: ParseIntError { kind: InvalidDigit }`、`exit=1`；说明这是 Debug 而不是 Display。
- 笔记 1–4：已按课程批阅修正，关键句见 [my-notes/0009](../../my-notes/0009-traits-and-generics.md)。
- 编译修正：`Termination` 签名、`impl Trait` 的 let 位置错误。

## 清理

`*.exe`、`*.pdb` 是本地编译产物，不提交。需要时按上面的命令重新生成。
