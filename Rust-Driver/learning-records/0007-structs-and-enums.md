# 第七课聚类：结构体与枚举——变体、形态、tag 与事件模型（2026-10-27）

本记录覆盖第七课 CP1–CP3 的批阅、追问与代码验收。对应课程：lessons/0007-structs-and-enums.html。

## 一、CP1 三轮弧线

**第一轮**：三种结构体形态基本列出，但把元组结构体说成“外层只有一个元组”；认为字段全是 Copy 时结构体赋值不移动；把 `Self` 与 `self` 混用；枚举部分把单元变体的判别值说成“携带整数类型”。

**第二轮**：补了 `String` vs `&str`、关联函数与方法；语法仍有 `struct a{...};`、`struct:Pp`、`struct:Mm` 三处错误；`..base` 与 `assert_eq!` 的所有权解释仍是运行期视角。

**第三轮（通过）**：六题 rustlings 通过；用 `structs2` 的 `..order_template` 说明显式 `name` 不移动 `String`、省略 `name` 部分移动、`assert_eq!` 只借用。CP1 通过。

## 二、关键心智模型

### 1. 五个概念：类型 / 变体 / 值 / 变量 / 形态

- **类型**：`ButtonEvent`，所有变体共享。
- **变体**：`Pressed` / `Released` / `Held`，tag/构造器；不是类型，不是变量。
- **值**：`ButtonEvent::Pressed { pin: 15 }`，tag + payload。
- **变量**：`let mut e = ...` 的 `e`，装值的容器；可换成另一个变体，但值在任一时刻只有一个 tag。
- **形态**：unit / tuple / struct，负载的写法；不是类型。
- `ButtonEvent` 三个变体全是 struct 形态；`Message { Quit, Write(String), Move { x, y } }` 才是三种形态各一个。

### 2. 枚举 = tag + payload

- tag 隐藏，不是字段；构造器设置 tag，`match` 读 tag；不比较字段值。
- `Pressed { pin: 15 }` 与 `Released { pin: 15 }` payload 相同、tag 不同；`std::mem::discriminant` 比较为 `false`。
- 变体名可自定义；名字即源码层面的 tag；改名后所有构造/模式都要改。

### 3. nominal vs structural

- 元组结构体 `Pin(u8)` 是 nominal：名字即身份，`Pin` 与 `Level` 不通用；同类型值通用。
- 元组 `(u8,)` 是 structural：所有 `(u8,)` 同一类型，能互相传；无法区分 pin/level。
- `struct Pp(u8, u32, bool)` 是三个位置字段；`struct Pp((u8, u32, bool))` 才是一个元组字段。

### 4. Copy / 部分移动

- 结构体 Copy 必须实现 `Copy`；字段全 Copy 不等于结构体 Copy。
- 整体赋值：结构体非 Copy -> move。
- `..base`：逐字段；省略的非 Copy 字段 move，base 部分移动；未移走字段仍可读。
- `assert_eq!` 借用，不移动。
- `String` 字段拥有数据；`&str` 字段借用，需要生命周期，结构体不负责释放。

### 5. 事件 vs 状态

- `ButtonState.pressed` = 状态（level）。
- `ButtonEvent` = 事件（edge/change）：`Pressed`/`Released` 边沿，`Held` 持续。
- 课程版 `false/false -> Held` 是避开 `Option` 的简化；严格模型应无事件。
- 三个 bool 有非法组合；enum 三选一 + `match` 穷尽，能精确表达事件。

## 三、CP2 验收

rustlings `07_structs` structs1–3、`08_enums` enums1–3 六题全过；状态下一题 `hashmaps1`。

- `structs2` 的 `..order_template`：`name` 显式给出，不移动 `template` 的 `String`；其余字段 Copy；`template` 完整可用。
- `enums3` 的 `match` 覆盖 `Resize` / `Move` / `Echo` / `ChangeColor` / `Quit` 五个变体；漏 `Quit` 会 E0004，也无法设置 `quit`。
- `assert_eq!` 借用；测试失败原因是 `your_order.name` 的值，而不是移动。

## 四、CP3 验收

`Rust-Driver/demo/button-model`：

- `ButtonState { pin, pressed }` + `new` + `update(&mut self, pressed, ms)`；
- `ButtonEvent` 三个 struct 变体；
- `main` 使用 `(true, 10)` / `(true, 20)` / `(false, 30)`，`match` 打印；
- `cargo run` 输出三行 `pressed` / `held` / `released`。
- 一句话理由：三个 bool 无效组合太多；enum 精确表达事件，更直观。

## 五、学习者信号与教学含义

- **术语分层需要显式表**：变体/形态/类型/变量是四条边界；只用文字讲会合并。有效手段：对照表 + `Message` vs `ButtonEvent` + `discriminant` 探针。
- **运行期解释编译期**再次出现：把 `..` 说成整体移动、把 `assert_eq!` 说成移动、把 `false/false` 的 `Held` 当成“状态”。教学含义：先声明编译期/运行期；用 E0382 和 assert 借用探针。
- **字段全 Copy ≠ 结构体 Copy**：需要 `#[derive(Copy, Clone)]`；`..base` 与整体赋值要分开讲。
- **元组结构体外层**：`Pp(u8, u32, bool)` vs `Pp((u8, u32, bool))` 是最有效的反例。
- **枚举 vs bool**：从“非法组合”切入比“bool 信息少”更准确；三 bool 可加字段，核心是互斥 + 穷尽 `match`。
- 下一步：`Option` 与错误处理；把 `false/false` 的简化用 `Option` 收口。

## 六、里程碑与下一步

- CP1–CP3 全部通过；第七课结课。
- 产物：`my-notes/0007`、本记录、术语表晋升、`LEARNER-PROFILE`、`NOTES`、`demo/button-model/README`。
- rustlings：`structs1–3` / `enums1–3` 完成；下一题 `hashmaps1`。
- 下一课：`Option` 与错误处理（`Option` / `Result`、`?`、`unwrap` 边界）。
