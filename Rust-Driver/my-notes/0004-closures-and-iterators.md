# 第四课学习笔记：闭包与迭代器

> 整理自第四课 CP1–CP3 的提问、纠偏与代码验收（原笔记为即时问答，已按主题重组，误区处标注“曾误→正解”）。
> 配套材料：课程 [lessons/0004-closures-and-iterators.html](../lessons/0004-closures-and-iterators.html) · 术语表 [reference/glossary.html](../reference/glossary.html) · 练习：The Book 13.1/13.2 + WoL 的 first_word / parse_mac / print_hex 重构。

---

## 一、迭代器与游标：iter() / next() / &i32 的类型链

- `iter()` 返回**迭代器对象（游标）**，类型类似 `std::slice::Iter<'_, i32>`；它不是数组，也不是 `&i32`。
- 游标创建时停在第一个元素之前，**不产出任何元素**；第一次 `next()`（或 `for` / `collect` 来驱动）才取到第一个元素的引用，并前进一格。
- `it.next()` 返回 **`Option<&i32>`**：`Some(&v[0])` 表示有下一个，`None` 表示结束。
- 其中的 `&i32` 指向 **v 里的元素数据**，不是指向迭代器/游标；元素仍在 v 里，没有被复制或移动。
- **曾误**：“iter() 的类型是 &i32，指向这个游标；`&iter().next()` 才是指向数据的地址。”
- **正解**：游标的内部指针/索引不暴露；`next()` 返回的是包在 `Option` 里的元素引用。`&iter().next()` 是对临时 `Option` 取地址，不是数据地址；要取数据引用应写：

  ```rust
  let mut it = v.iter();          // it: 迭代器对象
  let first = it.next().unwrap(); // first: &i32 -> v[0]
  println!("{:p}", first);        // v[0] 的数据地址
  ```

  手动调用 `next()` 时迭代器变量要 `mut`；`for` 和 `collect` 会在内部把它变成可变的。

- 类型链：

  | 表达式 | 类型 | 指向/含义 |
  |---|---|---|
  | `it` | 迭代器对象（游标） | 当前位置，不是元素 |
  | `it.next()` | `Option<&i32>` | 有值 / 结束 |
  | `&i32` | 元素的引用 | 指向 v 中的元素，不是游标 |

- C 类比：`iter()` 像 `struct { const int *p; const int *end; }` 游标；`it.p` 是游标内部指针（不暴露），`next(&it)` 返回的 `const int *` 才指向数据。Rust 把 `NULL` 换成 `None`，把数据指针换成 `&i32`。

## 二、map 与惰性：适配器，不是“函数嵌套”

- `map` 是**适配器（adapter）**：把“上游迭代器 + 闭包”包成一个新迭代器；闭包被存起来，**构造时一次都不执行**。
- **曾误**：“map 内部有一个循环，循环完生成容器，collect 再把容器转换成目标类型。”
- **正解**：`map` 本身不跑循环；真正的循环在消费者（`collect` / `for` / `sum`）里。消费者反复调用 `next()`，`Map` 的 `next()` 每次先从上游取一个元素，再调用一次闭包。闭包调用次数 = 实际到达 map 的元素数；有 `filter` / `take` 时更少，不消费就是 0 次。
- 实测：`let it = v.iter().map(|x| { println!("map {x}"); x * 2 });` 之后先打印“map 构造完了”，`collect()` 开始后才逐条打印“map 正在处理”。
- 不是函数嵌套；可以理解成流水线的一节/转接头。`map` 的用途是变换每个元素；只想遍历做副作用，用 `for` 或 `for_each`。
- 逆序：`v.iter().rev().map(|x| x * factor).collect()` 正确，输出 `[30, 20, 10]`（`v = [1,2,3]`、`factor = 10`）。`rev()` 只改遍历顺序，不修改 v；`v.iter().map(...).rev().collect()` 也等价，前提是迭代器支持双端遍历（`v.iter()` 支持）。

## 三、collect：消费者，按上下文构造集合

- `collect()` 是消费者：它驱动整条链、反复 `next()`，把每个结果**一边取出、一边装进目标集合**，最后返回集合；不是先跑完再打包。
- 目标类型不是迭代器决定的，也不是 collect 自己决定的，而由**上下文**决定：变量标注、函数参数或返回类型。
  - `let out: Vec<i32> = ...collect();` 可以。
  - `let out = ...collect();` 没有上下文会报 **E0283: type annotations needed**。
- 它不是单纯类型转换，也不是“map 先生成容器再转换”；`collect` 本身就是启动器兼构造器。

## 四、闭包：能记住环境的匿名函数

- 最小例子：

  ```rust
  let n = 3;
  let add_n = |x| x + n;    // |x| 是参数，x + n 是函数体
  println!("{}", add_n(5)); // 8
  ```

- 闭包 = 匿名函数 + 捕获定义处环境的能力。它记得 `n`；普通函数不行（C 函数指针只能带代码）。
- C 类比：C 里要手动传上下文：

  ```c
  struct adder { int n; };
  int add_n(void *ctx, int x) { return x + ((struct adder*)ctx)->n; }
  ```

  Rust 把 `n` 自动装进匿名结构体，调用 `add_n(5)` 时自动带上。可以理解为“函数指针 + 隐式上下文结构体”。

- 语法：`|参数| 表达式`；无参数写 `||`；类型通常由上下文推断。**不捕获外部变量的 `|x| x + 1` 也叫闭包**——捕获能力是它和普通函数的关键区别，但不是使用前提。
- 捕获方式：
  - 只读 → 不可变借用；
  - 修改 → 可变借用；
  - 消耗/移出 → `move` 强制按值捕获（线程、异步常见）。
- 标准库按可调用能力分 `Fn` / `FnMut` / `FnOnce`，先认门牌；`map` 里的闭包大多只读，`filter`/计数用 `FnMut`，`move` 可能只实现 `FnOnce`。
- 你已经在用：`input.iter().map(|element| element * 2).collect()` 是无捕获闭包；`|x| x * factor` 捕获 factor。

## 五、WoL 实战：first_word 与 parse_mac

### first_word 迭代器版

```rust
fn first_word(s: &str) -> &str {
    let bytes = s.as_bytes();
    for (i, &item) in bytes.iter().enumerate() {
        if item == b' ' {
            return &s[0..i];
        }
    }
    &s[..]
}
```

- `bytes.iter()` 产出 `&u8`；`enumerate()` 配原始下标；`(i, &item)` 把元组拆开，`&item` 再把 `&u8` 拆成 `u8`，所以能和 `b' '` 直接比较。
- 四个输入：`"Hello World"` → `"Hello"`；`"Solo"` → `"Solo"`；`""` → `""`；`"   "`（三个空格）→ `""`。
- 与索引版的对比：索引版手动维护 `i`、`bytes.len()` 和边界；迭代器版让 `enumerate()` 管下标、`&item` 管解包，少一份手写状态，结果相同。
- **曾误**：“索引版需要用时再用，减少了全量预加载的时间。”
- **正解**：两种版本都是按需读取，都不会预加载整个容器；索引循环也是取一个算一个。区别是写法与状态管理，不是性能；迭代器是零成本抽象，通常编译成相近的机器码。

### parse_mac 流水线

```rust
fn parse_mac(mac: &str) -> Vec<u8> {
    mac.split('-')                                             // &str
        .map(|part| u8::from_str_radix(part, 16).unwrap_or(0)) // u8
        .collect()                                             // Vec<u8>
}
```

- `split('-')` 产出每段 `&str`；`map` 的闭包把一段变成 `u8`；`collect` 按返回类型收成 `Vec<u8>`。
- `print_hex` 也改成了 `for (i, &item) in packet.iter().enumerate()`；`item` 是 `u8`，直接 `{:02X}` 打印。
- 运行输出与重构前一致：102 字节魔术包不变；边界输入 `""` 和三个空格都返回空串。

## 六、自查问题（复习时盖住答案自测）

1. `it`、`it.next()`、其中的 `&i32` 分别是什么类型/指向什么？
2. 为什么 `next()` 返回 `Option<&i32>` 而不是 `&i32`？游标创建时会自动给你第一个元素吗？
3. `map` 在调用那一刻会执行闭包吗？真正驱动循环的是谁？闭包调用次数由什么决定？
4. `collect()` 的目标类型由什么决定？没有上下文会报什么错？
5. 闭包捕获外部变量有哪三种方式？`move` 强制哪一种？
6. 用 C 的函数指针 + 上下文结构体解释闭包；再用 C 的游标结构体解释 `iter()`/`next()`。
7. first_word 的索引版与迭代器版有什么相同、什么不同？parse_mac 的流水线每一段是什么类型？

---

> 本文件由第四课问答与代码验收整理而成。新的观察随时追加。
