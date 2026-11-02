# 第八课聚类：Option 与错误处理——包装、错误传播与 WoL（2026-11-02）

本记录覆盖第八课 CP1–CP3 的批阅、追问与代码验收。对应课程：lessons/0008-option-and-error-handling.html。

## 一、CP1 弧线

**初版笔记**：Option/Result 结构、`ok_or` 方向、`unwrap`/`expect` 的可用场景、`panic` 与 `return Err` 的大方向、`?` 的 Ok/Err 分支、`From` 转换、Option/Result 不能直接混用——整体方向正确。

**必须修正的点**：

- 把 Option 说成“给 T 增加一个 None 的情况”——包装 vs 扩展未分开；
- `Result` 的 T/E 说成“两个参数”——应为类型参数；
- `ok_or` 的参数说成“错误类型”——应为类型 E 的错误值；
- `unwrap`/`expect` 只写了可用场景，缺“什么时候必须返回 Result”；
- `panic` 被说成“断言”，且“整个程序中断”不够精确；
- `?` 只写“返回 v / 返回 Err(e)”，缺“从当前函数提前返回”和 `From`；
- Option/Result 混用只写了 Option → Result 方向，缺 Result → Option 与“残余类型”表述。

**修订后通过**：Option 是新的二选一枚举，`None` 不装值；`?` 展开为 match + early return；`ok_or` 参数是错误值；外部输入/固件必须返回 Result。

## 二、关键心智模型

### 1. Option 是包装，不是扩展

- `Option<T> = None | Some(T)`；`None` 是 Option 的变体，不是 T 的变体；T 本身不变。
- 对比 `ButtonEvent` 加 `None`：那是一个类型 4 个变体；`Option<ButtonEvent>` 是两个类型，外层 Option、内层 ButtonEvent 仍 3 个变体。
- 类型 vs 值：`Option<T>` 是类型；`Some(3)` / `None` 是值；函数返回的是值，不是类型。
- 运行时成本：`ButtonEvent`、`Option<ButtonEvent>`、`ButtonEvent + None` 在本机实测都是 8 字节；多出来的“层”是类型层的两个问题，不是堆分配或指针。

### 2. Result 的错误归谁决定

- `E` 的类型由 API 作者在签名里选（`parse` → `ParseIntError`，`File::open` → `io::Error`，`parse_mac` → `MacError`）；
- 具体错误值由失败分支给出（`Err(MacError::Length)` / `Err(MacError::NonHex)`）；
- 调用者可以用 `?` + `From` 或 `map_err` 转成自己的错误类型；
- `Vec::pop()` 用 Option，因为空栈是“没有值”，不是“有原因的错误”。

### 3. ? 是 early return，不是异常

- Result：`Ok(v) => v`；`Err(e) => return Err(From::from(e))`；
- Option：`Some(v) => v`；`None => return None`；
- 只能用在返回同族 Result/Option 的函数里；T 要匹配，E 需能 From 转换；转换不了是编译期 E0277；
- Option 在 Result 函数里：`ok_or(err)?`；Result 在 Option 函数里：`.ok()?`（丢弃错误）。

### 4. unwrap / unwrap_or / panic 的边界

- `unwrap`：成功取值，失败 panic；`Result::unwrap` 要求 E: Debug；`Option::unwrap` 无此约束。
- `unwrap_or(0)`：失败返回 0，不 panic，但丢弃失败信息；`Some(0)` 与 `None` 无法区分。
- `unwrap_or_else` 延迟计算；`unwrap_or_default` 要求 T: Default。
- panic 是运行期不可恢复机制：默认展开当前线程、通常退出（101）；no_std/abort 通常停机；不是断言，`assert!`/`unwrap`/`expect` 都可触发。
- 外部输入、协议解析、固件必须返回 Result；测试/原型/确定不可能失败的不变量可用 unwrap/expect。

### 5. parse 的进制

- `parse::<T>()` 调用 T 的 `FromStr`；整数默认十进制。
- `"255".parse::<u8>()` → `Ok(255)`；`"FF".parse::<u8>()` → `Err(InvalidDigit)`；`u8::from_str_radix("FF", 16)` → `Ok(255)`。
- `::<u8>` 是 turbofish；不写时靠上下文推断，无上下文报 E0284。
- 课程第 2 节曾把 `"FF".parse::<u8>()` 写成 `Ok(255)`，已修正；这是本课的事实错误，已记入 NOTES。

### 6. 格式化 trait

- `{}` → `Display`；`{:?}` → `Debug`；`{:#?}` 美化 Debug。
- `Option` 实现了 Debug（T: Debug），没有 Display；`println!("{n}")` 报 E0277，`{n:?}` 可打印。
- `{n:?}` 里的 `?` 是格式说明符，不是错误传播运算符。

## 三、CP2 验收

rustlings `options1–3`、`errors1–3` 六题通过。

- **options1**：`(0..22)` / `(22..24)` 分段正确；测试 `unwrap` 合理。
- **options2**：第一版 `while let Some(integer) = optional_integers.pop().unwrap()` 测试通过，但绕过嵌套模式；无 `None` 哨兵时 outer unwrap 会 panic。探针：`vec![Some(1), Some(2)]` 的 unwrap 版本输出 2、1 后 panic（exit 101）；嵌套版本输出 2、1、done（exit 0）。已改 `while let Some(Some(integer)) = ...`。
- **options3**：`match &optional_point` 借用，match 后仍可打印；`Point` 非 Copy。
- **errors1**：`Result<String, String>`；空名字 Err，非空 Ok；测试的 `as_deref`/`map_err` 只是借用式比较。
- **errors2**：`qty.map(|x| x * cost_per_item + processing_fee)` 正确；`?` 版本更短。
- **errors3**：`main -> Result<(), ParseIntError>`；`?` 提前返回；末尾 `Ok(())`。

## 四、CP3 验收

### button-model

- `update` 返回 `Option<ButtonEvent>`；false/false → `None`；
- `cargo run` 输出 `no event` / `pressed` / `held 20 ms` / `released`；
- `match` 用 `_` 接住 None 能过；建议写 `None =>` 更精确。

### WoL

- `protocol.rs`：`pub enum MacError { Length, NonHex }` + Debug；
- `parse_mac -> Result<[u8; 6], MacError>`；`build_magic_packet -> Result<[u8; PACKET_LEN], MacError>`，内部 `?`；
- `main -> Result<(), MacError>`，`build_magic_packet(&mac)?`，末尾 `Ok(())`；
- 正常 `cargo run` 输出 102 字节；坏 MAC `AA-BB-CC-DD-EE` → `Error: Length`（exit 1）；`AA-BB-CC-DD-EE-ZZ` → `Error: NonHex`（exit 1）。

**解释修正**：protocol 不用 unwrap，因为 MAC 是外部输入、失败可预期；unwrap 会 panic；unwrap_or(0) 会静默把坏段变成 0x00，生成错误包；Result 携带 Length/NonHex，交给调用者处理。

## 五、学习者信号与教学含义

- **“测试通过 ≠ 正确”再次出现**：options2 用 `.unwrap()` 绕过目标模式，测试因 `None` 哨兵而通过。有效手段：边界探针（去掉哨兵、空 Vec），并检查“是否用了本课要练的模式”。
- **“包装 vs 扩展”措辞反复**：CP1 中仍出现“给 T 增加 None”的说法。有效手段：`Option<T> = None | Some(T)` 对照表 + `ButtonEvent + None` vs `Option<ButtonEvent>` + 类型/值分层。
- **对标准库来源与方法签名有强需求**：用户追问 `Vec::pop` 是源码还是手写、`parse::<String>`、`{n:?}` 与 `?` 的区别；编译器探针与源码路径能建立信任。
- **parse/radix 精度**：用户主动发现 `"FF".parse::<u8>()` 与课程输出矛盾，促成课程修正；教学含义：示例必须实测，尤其是“看起来像十六进制”的字符串。
- **格式化 trait**：`{}`/`{:?}` 的区别需要单独讲清；`{n:?}` 的 `?` 与错误传播 `?` 同字符不同语义。

## 六、里程碑与下一步

- CP1–CP3 全部通过；第八课结课。
- 产物：`my-notes/0008`、本记录、术语表晋升（Option/Result/?/unwrap/parse/panic）、`demo/button-model` 与 `demo/wol` 更新、`LEARNER-PROFILE`、`NOTES`。
- rustlings：`options1–3`、`errors1–3` 通过；runner 可能仍停在 `errors3`，用 watch 模式推进到 `errors4`。
- 下一课：trait 与泛型——正式讲 `<T>`、`From`、`Debug`、`Termination`；`errors4–6`（自定义错误、`Box<dyn Error>`）顺着那条线补完。
