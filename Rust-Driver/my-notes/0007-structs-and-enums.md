# 第七课学习笔记：结构体与枚举

> 整理自第七课 CP1–CP3 的笔记、追问与代码验收（原笔记为即时问答，已按主题重组，误区处标注“曾误→正解”）。
> 配套材料：课程 [lessons/0007-structs-and-enums.html](../lessons/0007-structs-and-enums.html) · 术语表 [reference/glossary.html](../reference/glossary.html) · 代码：[demo/button-model](../demo/button-model/src/main.rs)

---

## 一、结构体的三种形态

| 形态 | 声明 | 字段访问 | 适用场景 |
|---|---|---|---|
| 命名字段结构体 | `struct Named { aa: u8, bb: bool }` | `.aa` / `.bb` | 多字段、要可读性 |
| 元组结构体 | `struct Tuple(u8, u32, bool);` | `.0` / `.1` / `.2` | newtype、位置明显、字段少 |
| 单元结构体 | `struct Unit;` | 无字段 | 标记、trait 实现、类型状态、命名空间 |

**曾误**：`struct Pp(u8, u32, bool)` 的外层是“一个元组”，三个字段都在这个元组里。  
**正解**：`Pp` 是命名的元组结构体，有**三个位置字段**，类型是 `Pp`，不是 `(u8, u32, bool)`。如果想让一个字段本身是元组，要写 `struct Pp((u8, u32, bool));`；这时 `p.0` 是元组，`p.0.0` 才是第一个元素。

```rust
struct Named {
    aa: u8,
    bb: bool,
    cc: String,
}

struct Tuple(u8, u32, bool);

struct Unit;

fn main() {
    let n = Named {
        aa: 1,
        bb: false,
        cc: String::from("x"),
    };
    let t = Tuple(1, 2, true);
    let _u = Unit;

    println!("{} {} {}", n.aa, t.0, t.2);
}
```

- 花括号结构体声明后**不要分号**；元组结构体和单元结构体声明后**要分号**。
- 类型名用 CamelCase；`struct a` 会有 `non_camel_case_types` 警告。
- 单元结构体是零大小类型，`size_of::<Unit>() == 0`；它有一个值 `Unit`，不是“没有值”。

## 二、结构体字段的所有权

### 1. 整体赋值：看结构体是否实现 Copy

**曾误**：字段全是 Copy，结构体赋值就不会移动。  
**正解**：只有结构体**实现了 Copy**（`#[derive(Copy, Clone)]`）时，整体赋值才是复制；否则即使字段全是 Copy，整体赋值仍然 move。

```rust
struct S {
    a: u8,
    b: bool,
}

let x = S { a: 1, b: false };
let y = x;        // 移动
// println!("{}", x.a); // E0382
```

```rust
#[derive(Copy, Clone)]
struct C {
    a: u8,
    b: bool,
}

let m = C { a: 1, b: false };
let n = m;        // 复制
println!("{} {}", m.a, n.a);
```

### 2. `..base`：逐字段取值，不是整体移动

`..base` 对每个被省略的字段执行 `字段: base.字段`：

- 字段是 Copy：复制；
- 字段非 Copy：移动，`base` 变成部分移动；
- 显式写出的字段不会从 base 取。

```rust
struct Order {
    name: String,
    year: u32,
}

let template = Order {
    name: String::from("Bob"),
    year: 2019,
};

// name 显式给出：不移动 template.name；year 是 Copy
let order = Order {
    name: String::from("Hacker in Rust"),
    ..template
};
println!("{} {}", order.name, template.year); // 可以

// 如果省略 name：String 被移走，template 部分移动
let _moved = Order { ..template };
// println!("{}", template.year); // 可以：year 未移走
// println!("{}", template.name); // E0382
// println!("{:?}", template);    // E0382：整体不可用
```

**曾误**：`..template` 会把 `template` 的整体所有权交给新值。  
**正解**：只移动被省略的非 Copy 字段；Copy 字段复制；旧值可能部分移动，未移走的字段仍可读。

**`assert_eq!`**：只借用两个操作数，不移动。

```rust
let s = String::from("x");
assert_eq!(s, "x");
println!("{s}"); // 仍可用
```

### 3. String 字段 vs 引用字段

```rust
struct Owned {
    name: String,        // 拥有字符串数据
}

struct Borrowed<'a> {
    name: &'a str,       // 只借用外部数据
}
```

- `String` 字段拥有堆数据；结构体 move 时，字符串所有权一起 move；结构体负责 drop。
- `&str` 字段只借用；结构体不负责释放；必须保证被借用的数据活得够久。引用字段需要生命周期标注；本课不要求写生命周期，但要知道它不拥有数据。

## 三、impl、方法与关联函数

| 第一个参数 | 权限 | 调用 | 典型用途 |
|---|---|---|---|
| `&self` | 只读借用 | `instance.method()` | 查询、计算 |
| `&mut self` | 可变借用 | `instance.method()` | 修改字段 |
| `self` | 取得所有权 | `instance.method()` | 消耗并转换 |
| 无 `self` | 关联函数 | `Type::func()` | 构造器、工具函数 |

```rust
impl ButtonState {
    fn new(pin: u8) -> Self {
        Self {
            pin,
            pressed: false,
        }
    }

    fn is_pressed(&self) -> bool {
        self.pressed
    }

    fn press(&mut self) {
        self.pressed = true;
    }
}
```

- `new` 是关联函数，没有 `self`；用 `ButtonState::new(15)` 调用。`new` 是命名习惯，不是关键字。
- 方法是第一个参数为 `self` 的函数；用实例调用。
- `Self`（大写）是 `impl` 后类型的别名；`impl ButtonState` 里 `Self = ButtonState`。`self`（小写）是接收者值。`Self` 不随调用者变化。
- 一个类型可以有多个 `impl` 块；inherent impl 必须和类型在同一个 crate；trait impl 受孤儿规则限制。`impl` 不改变结构体布局。

## 四、枚举

### 1. 变体、tag、payload

- 枚举值 = **tag** + **payload**（负载）。
- tag 说明“是哪个变体”，由编译器隐藏；payload 是变体携带的数据。
- `match` 读 tag 选分支，再解构 payload；不靠字段值判断变体。

```rust
#[derive(Debug)]
enum ButtonEvent {
    Pressed { pin: u8 },
    Released { pin: u8 },
    Held { pin: u8, ms: u32 },
}
```

两个值 payload 相同，但 tag 不同：

```rust
let a = ButtonEvent::Pressed { pin: 15 };
let b = ButtonEvent::Released { pin: 15 };

println!(
    "{}",
    std::mem::discriminant(&a) == std::mem::discriminant(&b)
); // false
```

- 变体名可以自定义（`a`/`b`/`c` 也行，但不符合 CamelCase 习惯）；你起的名字就是源码层面的 tag 名字。
- 变体不是类型；不能写 `fn f(e: ButtonEvent::Pressed)`。
- 无字段 enum 的判别值默认从 0 递增，可显式写 `Red = 1`，用 `as` 读取；判别值不是 payload。

### 2. 三种变体形态

| 形态 | 例子 | 负载 | 访问 |
|---|---|---|---|
| 单元变体 | `Quit` | 无 | `match E::Quit` |
| 元组变体 | `Write(String)` / `Held(u8, u32)` | 位置字段 | `match E::Write(s)` |
| 结构体变体 | `Pressed { pin }` | 命名字段 | `match E::Pressed { pin }` |

- `ButtonEvent` 的三个变体**全是结构体变体**；它们不是三种形态各一个。
- `Message { Quit, Write(String), Move { x, y } }` 才是三种形态各一个。
- 元组变体不是“一个元组字段”：`Held(u8, u32)` 是两个位置字段；要一个元组字段写 `Held((u8, u32))`。
- 枚举值不能直接 `.0` / `.pin`；必须 `match` / `if let` 解构。

### 3. 事件 vs 状态

- `ButtonState.pressed` = 当前状态（level），只有 true/false。
- `ButtonEvent` = 刚刚发生了什么（edge/change）：Pressed / Released / Held。
- 课程版 `update` 的 `else` 同时接住 true/true 和 false/false；false/false 也返回 Held，是为了避开 Option 的简化。CP3 只模拟 true/true/false，不受影响；严格模型应只在上一次和这一次都按下时发 Held。

### 4. match、`_`、if let

- `match` 必须穷尽所有变体；漏一个 E0004。
- `_` 是通配符，匹配剩余所有值；它让 match 仍穷尽，但会静默接住以后新增的变体，隐藏编译提醒。
- `if let` 只处理一个模式，不要求穷尽；不是“关闭穷尽检查”。
- `match` 是表达式，所有分支返回同一类型；`_` 可以出现在嵌套模式里。

## 五、CP2 与 CP3 验收

### CP2：rustlings 07/08

- `structs1–3`、`enums1–3` 六题通过。
- 关键：`structs2` 用 `..order_template`；`enums3` 的 `match` 覆盖五个变体。
- `assert_eq!` 借用，不移动。

### CP3：demo/button-model

代码见 [demo/button-model/src/main.rs](../demo/button-model/src/main.rs)。`cargo run` 输出：

```text
pin 15: pressed
pin 15: held 20 ms
pin 15: released
```

为什么用枚举而不是三个 bool：三个 bool 可以组合出“同时 pressed 和 released”或“全 false”等非法状态；枚举只能三选一，能精确表达事件，`match` 又强制处理每个变体。

## 六、误区清单（曾误→正解）

1. 元组结构体外层是一个元组 → 外层是命名结构体，字段是位置字段；`Pp(u8,u32,bool)` 是三个字段，`Pp((u8,u32,bool))` 才是一个元组字段。
2. 字段全是 Copy，结构体赋值就复制 → 结构体本身要实现 Copy；否则整体赋值仍 move。
3. `..base` 移动整个 base → 只逐字段取值；非 Copy 字段移动，base 部分移动。
4. `assert_eq!` 会移动操作数 → 只借用。
5. `Self` 和 `self` 是一回事 → `Self` 是类型别名，`self` 是接收者值。
6. 单元变体携带整数 → 单元变体没有 payload；判别值是另一层，可用整数显式指定。
7. 元组变体是一个元组 → 是位置字段列表；一个元组字段要双层括号。
8. 枚举变体是类型 → 变体不是类型，整个 enum 才是类型。
9. `_` 关闭穷尽检查 → `_` 是 catch-all，match 仍穷尽，但会吞掉新增变体。
10. `if let` 只关心一种类型 → 只关心一个模式/一个变体，不要求穷尽。
11. 三个 bool 也能精确表达事件 → 三个 bool 有非法组合；enum 保证互斥。
12. `ButtonEvent` 能描述“所有状态” → 它描述事件；当前状态由 `ButtonState` 保存。

## 七、自查问题

1. 命名字段/元组/单元结构体的声明、构造、字段访问各是什么？各适合什么场景？
2. 字段全是 Copy 的结构体，整体赋值会 move 还是 copy？`..base` 呢？
3. `String` 字段和 `&str` 字段的所有权差别是什么？
4. `&self` / `&mut self` / `self` / 无 self 分别是什么？怎么调用？
5. `Self` 和 `self` 的区别？
6. 枚举的 tag 和 payload 分别是什么？三个变体形态是什么？
7. `ButtonEvent` 的三个变体属于哪种形态？为什么它们仍是三个不同变体？
8. `match` 的穷尽检查、`_`、`if let` 的区别？
9. 为什么 `ButtonEvent` 比三个 bool 更精确？
10. 课程版 `update` 对 false/false 做了什么简化？

---

> 本文件由第七课 CP1–CP3 的问答与代码验收整理而成。新的观察随时追加。
