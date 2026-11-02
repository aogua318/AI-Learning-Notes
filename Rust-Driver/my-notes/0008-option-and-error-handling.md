# 第八课学习笔记：Option 与错误处理

> 整理自第八课 CP1–CP3 的笔记、追问与代码验收（原笔记为即时问答，已按主题重组，误区处标注“曾误→正解”）。
> 配套材料：课程 [lessons/0008-option-and-error-handling.html](../lessons/0008-option-and-error-handling.html) · 术语表 [reference/glossary.html](../reference/glossary.html) · 代码：[demo/button-model](../demo/button-model/src/main.rs) · [demo/wol](../demo/wol/src/main.rs)

---

## 一、Option：包装，不是扩展

### 1. 结构

```rust
pub enum Option<T> {
    None,
    Some(T),
}
```

- `Option<T>` 是标准库 `core::option` 里的泛型枚举，prelude 自动引入；不是关键字，也不是我们定义的。
- `None` 不装值；`Some(T)` 装一个 `T`。
- `T` 本身不变；`Option<T>` 是一个**新类型**，不是给 `T` 增加一个 `None` 变体。
- `Option<T>` 是类型；`Some(3)`、`None` 是值。

**曾误**：Option 是“给类型参数增加一个 None 变体”。
**正解**：Option 是“把 T 包进一个新的二选一类型”。对比 `ButtonEvent`：

| 方式 | 类型形状 | 结果 |
|---|---|---|
| 给 `ButtonEvent` 加 `None` | `Pressed \| Released \| Held \| None` | 一个类型，4 个变体；所有 match 都要处理 None |
| `Option<ButtonEvent>` | `None \| Some(ButtonEvent)` | 两个类型；ButtonEvent 仍 3 个变体，None 在外层 |

### 2. 用 Option 收口 button-model

`ButtonState::update` 返回 `Option<ButtonEvent>`：

- 上升沿 → `Some(Pressed)`
- 下降沿 → `Some(Released)`
- 已按下且仍按下 → `Some(Held)`
- false/false（无事件）→ `None`

`main` 的输出：

```text
no event
pin 15: pressed
pin 15: held 20 ms
pin 15: released
```

`match` 可以嵌套：`Some(ButtonEvent::Pressed { pin })` 外层剥 Option，内层读枚举变体。

### 3. if let、while let 与嵌套 Option

```rust
if let Some(word) = optional_target {
    println!("{word}");
}

let mut stack = vec![1, 2, 3];
while let Some(top) = stack.pop() {
    println!("{top}");
}
```

`Vec::pop()` 返回 `Option<T>`：非空 `Some(最后一个元素)`，空 `None`。`while let` 在模式不再匹配时结束循环。

嵌套 Option：

```rust
let mut items: Vec<Option<i8>> = vec![Some(1), None, Some(3)];
while let Some(Some(n)) = items.pop() {
    println!("{n}");
}
```

- 外层 `Some`：`Vec` 还有元素、`pop()` 成功；
- 内层 `Some`：元素本身是 `Some(i8)`，不是 `None`；
- 两层都命中才绑定 `n: i8`；任意一层 `None` 都结束循环。

### 4. 常用方法（先看接收者）

| 方法 | 接收者 | None 时 | 用途 |
|---|---|---|---|
| `map(f)` | `self` | `None` | `Some(x)` → `Some(f(x))`，闭包只在 Some 时执行 |
| `unwrap_or(d)` | `self` | 返回 `d` | 默认值，不 panic |
| `ok_or(e)` | `self` | `Err(e)` | 转成 Result，补一个错误值 |
| `as_ref()` | `&self` | `None` | 借用内部值，不移动原 Option |
| `unwrap()` | `self` | panic | 断言成功，失败崩溃 |

`map` 的类型链：

```text
n: Option<u8> = Some(7)
→ map 的 T = u8
→ 闭包参数 v: u8
→ v + 1 的 1 也推断为 u8
→ 返回 Option<u8>
```

`None` 时闭包不会执行；`map` 不是“内部跑循环并生成容器”，它只是条件应用函数。

---

## 二、Result：成功或失败 + 原因

### 1. 结构

```rust
pub enum Result<T, E> {
    Ok(T),
    Err(E),
}
```

- `T` 是成功值类型，`E` 是错误原因类型；两个都是类型参数。
- `Ok(T)` 装成功值；`Err(E)` 装错误值。
- `Option` 只回答“有没有”；`Result` 回答“成功还是失败、为什么”。

### 2. parse 与进制

```rust
"255".parse::<u8>()          // Ok(255)
"FF".parse::<u8>()           // Err(ParseIntError { kind: InvalidDigit })
u8::from_str_radix("FF", 16) // Ok(255)
```

- `parse::<u8>()` 调用 `u8` 的 `FromStr` 实现；对整数来说默认按**十进制**解析。
- `"FF"` 不是十进制数字，所以 `parse::<u8>()` 失败；它不会自动识别十六进制。
- 十六进制用 `u8::from_str_radix(s, 16)`。
- `::<u8>` 是 turbofish：显式指定泛型参数 `F = u8`。不写时可由上下文推断；无上下文会报 E0284（type annotations needed）。
- `parse` 返回 `Result<F, F::Err>`；`u8` 的 `F::Err` 是 `ParseIntError`。

**曾误**：`"FF".parse::<u8>()` 能解析成 255。  
**正解**：`parse` 对整数默认十进制，`FF` 会报 `InvalidDigit`；十六进制必须用 `from_str_radix`。课程第 2 节已修正。

### 3. 自定义错误 MacError

```rust
#[derive(Debug)]
pub enum MacError {
    Length,
    NonHex,
}
```

- `Length`：`split('-')` 后不是 6 段；
- `NonHex`：某段无法按十六进制解析成 `u8`；
- 严格说，`map_err(|_| MacError::NonHex)` 会把所有 `ParseIntError` 都映射成 `NonHex`，包括溢出（如 `"100"` 十六进制 = 256 > 255）。

### 4. Option 与 Result 的转换

- `Option::ok_or(err)` / `ok_or_else(|| ...)`：`Some(v) → Ok(v)`，`None → Err(err)`。
- `Result::ok()`：`Ok(v) → Some(v)`，`Err(_) → None`（丢弃错误原因）。

---

## 三、unwrap / expect / panic

### 1. unwrap

- `Option<T>::unwrap(self) -> T`：`Some(v) → v`，`None → panic`。
- `Result<T, E>::unwrap(self) -> T`：`Ok(v) → v`，`Err(e) → panic`；要求 `E: Debug`，因为 panic 时要打印错误值。
- 接收者是 `self`，会消耗 Option/Result；`Option<u8>` 是 Copy，`Option<String>` 会 move。

panic 消息示例：

```text
called `Option::unwrap()` on a `None` value
called `Result::unwrap()` on an `Err` value: ParseIntError { kind: InvalidDigit }
```

退出码 101。

### 2. unwrap_or / unwrap_or_else / unwrap_or_default

- `unwrap_or(0)`：`Some(7) → 7`，`None → 0`；不 panic，但丢弃“有没有值”的信息。
- `unwrap_or_else(|| ...)`：默认值延迟计算，只在 None/Err 时执行。
- `unwrap_or_default()`：要求 `T: Default`；数字默认 0，String 默认空串。
- 对 Result，`unwrap_or(0)` 会丢弃错误原因；如果调用者需要原因，应返回 Result。

**曾误**：`unwrap_or(0)` 是在“处理错误”。  
**正解**：它只是把失败/缺失抹平成默认值。0 本身是合法字节时，坏输入会被静默变成 0，生成看起来正常但实际错误的包。

### 3. 什么时候可以用 unwrap / expect

- 可以：测试、示例、原型；或代码自己保证不可能失败（如硬编码常量），用 `expect("理由")` 写清理由。
- 不可以：外部输入（用户、网络、文件、协议解析）、可预期的失败、需要调用者决定重试/报错/忽略的情况；固件 / no_std 里 panic 通常直接停机。
- `expect` 仍然是 panic，只是消息更清楚；它不是错误处理。

### 4. panic 是什么

- panic 是运行期的“不可恢复错误”机制：打印消息和位置，默认展开当前线程并通常导致程序退出（退出码 101）；no_std / panic=abort 下通常直接停机。
- `panic!`、`assert!`、`assert_eq!`、`unwrap`、`expect` 都可以触发 panic。
- panic 不是断言本身；断言是触发 panic 的一种方式。
- `return Err` 是普通函数返回，调用者可以 `match` / `?` 处理。

---

## 四、?：错误的早退

`?` 只做两件事：成功取值，失败从**当前函数**提前返回。

```rust
// Result
let x = match expr {
    Ok(v) => v,
    Err(e) => return Err(From::from(e)),
};

// Option
let x = match expr {
    Some(v) => v,
    None => return None,
};
```

- 函数返回 `Result`，才能用 Result 的 `?`；返回 `Option`，才能用 Option 的 `?`。
- 成功类型 `T` 要匹配；错误类型 `E` 不要求完全相同，只要 `From` 能转换；转换不了是**编译期 E0277**，不是运行期失败。
- `?` 不是异常，也不是 panic；它是普通 early return。
- Option 在返回 Result 的函数里：`ok_or(err)?` / `ok_or_else(...)?`。
- Result 在返回 Option 的函数里：`.ok()?`（丢弃错误信息）或改返回类型。

`main` 也可以返回 Result：

```rust
fn main() -> Result<(), MacError> {
    let packet = build_magic_packet("AA-BB-CC-DD-EE-FF")?;
    println!("packet len = {}", packet.len());
    Ok(())
}
```

- 成功写 `Ok(())`；
- 失败返回 `Err(e)`，运行期打印 `Error: {e:?}`，退出码非 0；
- `E` 必须实现 `Debug`，否则 `Result<(), E>` 不满足 `Termination`，报 E0277。

---

## 五、格式化：{} 与 {:?}

- `{}` 走 `Display`；`{:?}` 走 `Debug`；`{:#?}` 是美化 Debug。
- `Option<T>` 实现了 `Debug`（当 `T: Debug`），但**没有实现 `Display`**：

```rust
let n = Some(3);
println!("{n:?}"); // Some(3)
// println!("{n}"); // E0277: Option<i32> doesn't implement Display
```

- `{n:?}` 里的 `?` 是 Debug 格式说明符，不是错误传播运算符；`?` 运算符在字符串外面。
- 想打印 Option 的内容，用 `match` / `unwrap_or` / `map_or`，或改用 `{:?}`。

---

## 六、CP2 验收：rustlings options / errors

### 1. options1

- `maybe_ice_cream` 用 `(0..22)` / `(22..24)` 分段，边界 22、23、24 都对；
- 测试里 `unwrap()` 取出 Option 的值，合理。

### 2. options2（重点）

第一版：

```rust
while let Some(integer) = optional_integers.pop().unwrap() {
```

测试能过，但这是“测试通过 ≠ 正确”：

- `pop()` 返回 `Option<Option<i8>>`；
- `.unwrap()` 把外层 Option 吃掉；Vec 为空时 `pop()` 返回 `None`，`.unwrap()` 直接 panic；
- 测试里的 Vec 有 `None` 哨兵，循环在 `Some(None)` 处提前结束，所以没走到“Vec 真空”那一步。

探针：

```text
unwrap 版本（vec![Some(1), Some(2)]）：
2
1
thread 'main' panicked ... called `Option::unwrap()` on a `None` value
exit 101

嵌套模式版本：
2
1
done
exit 0
```

正确写法：

```rust
while let Some(Some(integer)) = optional_integers.pop() {
    assert_eq!(integer, cursor);
    cursor -= 1;
}
```

- 外层 Some：Vec 还有元素；
- 内层 Some：元素本身不是 None；
- 两层都命中才绑定 `integer: i8`。

### 3. options3

- `match &optional_point` 借用，`p: &Point`；match 结束后 `optional_point` 仍可打印；
- `Point` 不是 Copy，不能 `match optional_point` 后继续使用原值。

### 4. errors1

- 返回类型从 `Option<String>` 改为 `Result<String, String>`；
- 空名字：`Err(String::from("Empty names aren't allowed"))`；
- 非空：`Ok(format!("Hi! My name is {name}"))`；
- 测试里的 `as_deref()` / `map_err()` 只是借用式比较，不需要改测试。

### 5. errors2

- 用 `qty.map(|x| x * cost_per_item + processing_fee)` 正确；
- 练习本意还有更短的 `?` 版本：

```rust
let qty = item_quantity.parse::<i32>()?;
Ok(qty * cost_per_item + processing_fee)
```

### 6. errors3

- `fn main() -> Result<(), ParseIntError>`；
- `let cost = total_cost(pretend_user_input)?;`；
- 末尾 `Ok(())`；
- 失败时从 main 提前返回 `Err(ParseIntError)`，运行期打印 `Error: ...`，退出码非 0。

---

## 七、CP3 验收：button-model 与 WoL

### 1. button-model

- `update` 返回 `Option<ButtonEvent>`；
- false/false → None；
- `cargo run` 输出：

```text
no event
pin 15: pressed
pin 15: held 20 ms
pin 15: released
```

### 2. WoL

- `MacError { Length, NonHex }`，`pub` + `#[derive(Debug)]`；
- `parse_mac` 返回 `Result<[u8; 6], MacError>`；
- `build_magic_packet` 返回 `Result<[u8; PACKET_LEN], MacError>`，内部 `let mac_bytes = parse_mac(mac)?;`，最后 `Ok(packet)`；
- `main` 返回 `Result<(), MacError>`，用 `build_magic_packet(&mac)?`，末尾 `Ok(())`；
- 正常 `cargo run` 输出 102 字节；
- 坏 MAC：`AA-BB-CC-DD-EE` → `Error: Length`；`AA-BB-CC-DD-EE-ZZ` → `Error: NonHex`；退出码非 0。

为什么 protocol 不用 unwrap：

- MAC 来自外部输入，解析失败是可预期的；
- `unwrap` 会 panic，CLI 直接崩，固件通常停机；
- `unwrap_or(0)` 会静默把坏段变成 0x00，生成看起来正常但 MAC 错误的包；
- 返回 `Result` 携带 `Length` / `NonHex`，让调用者打印错误、退出或重试。

---

## 八、误区清单（曾误→正解）

1. Option 是给 T 增加一个 None 变体 → Option 是新枚举 `None | Some(T)`；T 不变，None 是 Option 的变体。
2. Option 是关键字 → 是标准库类型名/标识符，prelude 自动引入。
3. `"FF".parse::<u8>()` 能得到 255 → 整数 parse 默认十进制，返回 `Err(InvalidDigit)`；十六进制用 `from_str_radix`。
4. `?` 是异常/panic → `?` 是编译期展开的 early return，不是异常。
5. Option 和 Result 可以混用 `?` → `?` 的残余类型必须同族；Option → Result 用 `ok_or`，Result → Option 用 `.ok()`。
6. `unwrap_or(0)` 是在处理错误 → 它只是默认值，会丢掉错误信息；0 是合法字节时更危险。
7. 测试通过 = 写法正确 → options2 的 `pop().unwrap()` 测试通过但无哨兵时 panic；要看是否用了目标模式。
8. `{n:?}` 的 `?` 是错误传播 → 它是 Debug 格式说明符，位置在字符串内部。
9. `NonHex` 一定表示“不是十六进制” → 也接住空段和溢出；当前实现把 ParseIntError 全映射成 NonHex。
10. `parse_mac` 严格校验 MAC 格式 → 只检查 6 段 + 能解析成 u8；`A-B-C-D-E-F` 也会通过，严格版还要检查每段两位。

---

## 九、自查问题

1. `Option<T>` 和 `Result<T, E>` 各回答什么问题？`None` / `Some(T)`、`Ok(T)` / `Err(E)` 分别是什么？
2. `Option<T>` 是“给 T 加 None”还是“包装 T”？用 `Option<ButtonEvent>` 说明。
3. `ok_or` 怎么把 Option 转 Result？`unwrap_or(0)` 和 `unwrap()` 的区别？
4. `unwrap` / `expect` 什么时候可以用，什么时候必须返回 Result？
5. panic 和 `return Err` 的区别？panic 默认会发生什么？
6. `?` 展开成什么？为什么返回类型必须匹配？`From` 在做什么？
7. Option 和 Result 为什么不能直接混用 `?`？两个方向分别怎么转？
8. `"255".parse::<u8>()`、`"FF".parse::<u8>()`、`u8::from_str_radix("FF", 16)` 的结果分别是什么？为什么？
9. `{}` 和 `{:?}` 的区别？为什么 Option 只能用 `{:?}` 打印？
10. protocol 里为什么不用 unwrap，也不用 unwrap_or(0)？

---

> 本文件由第八课 CP1–CP3 的问答与代码验收整理而成。新的观察随时追加。
