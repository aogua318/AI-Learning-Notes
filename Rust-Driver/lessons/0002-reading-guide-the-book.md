# 第二课阅读指南：The Book 4.2 & 4.3

> 配套课程：[lessons/0002-borrowing-and-references.html](./0002-borrowing-and-references.html)
> 用途：第二课课后任务 1、2 的导读。The Book 是英文的，这份指南告诉你**读哪里、盯什么、怎么自测**；关键原文保留英文并附中文。指南与课程说法不一致时，以 The Book 为准。

---

## 4.2 References and Borrowing（引用与借用）

预计 15 分钟。课程第 2～6 节就是这一节的浓缩，读原文时重点盯五处：

### 1. 借用是什么（节开头）

> We call the action of creating a reference **borrowing**.
> （创建引用的这个动作，我们叫作**借用**。）

> A reference is like a pointer in that it's an address we can follow to access the data stored at that address; that data is owned by some other variable.
> （引用像指针：是一个地址，顺着它能访问到数据；但那些数据归别的变量所有。）

课程对应：第 2 节"引用：所有权的参观证"。记住后半句——数据有别的所有者，所以引用离开时**什么都不 drop**。

### 2. 两条借用规则（本课第 2 节引用过，读时确认措辞）

1. At any given time, you can have **either one mutable reference or any number of immutable references**.
   （任意时刻，要么只有一个可变引用，要么有任意多个不可变引用。）
2. **References must always be valid**.
   （引用必须始终有效。）

### 3. 引用的作用域到最后一次使用（NLL）

> Note that a reference's scope starts from where it is introduced and continues through the last time that reference is used.
> （注意：引用的作用域从它被引入的地方开始，持续到它最后一次被使用。）

这正面回答了你 move_semantics 笔记里的直觉——"借了尽快用"不是风格建议，是作用域的天然形状。课程第 3 节有同一个例子的逐步拆解。

### 4. 数据竞争的定义（排他规则的存在理由）

> A data race is similar to a race condition and happens when these three behaviors occur:
>
> - Two or more pointers access the same data at the same time.（两个以上指针同时访问同一数据。）
> - At least one of the pointers is being used to write to the data.（至少一个在写。）
> - There's no mechanism being used to synchronize access to the data.（没有同步机制。）

三条同时成立才算数据竞争。`&mut T` 的排他规则直接消灭了第二条的 solo 写法。课程第 4 节。

### 5. 悬垂引用与修复

> In Rust, by contrast, the compiler guarantees that references will never be dangling references.
> （相比之下，Rust 编译器保证引用永远不会悬垂。）

`dangle()` 返回局部变量的引用会报 `error[E0106]: missing lifetime specifier`（缺少生命周期标注）。修复方法：**返回 `String` 本体，把所有权交出去**——课程第 6 节。"生命周期标注"是第 4.4 节之后的内容，现在认出错误码就够。

### 自测题（读完合上书回答）

1. 用自己的话说：为什么同一时间只能有一个 `&mut T`？用数据竞争三条件来答。
2. `let r1 = &s; println!("{r1}"); let r2 = &mut s;` 为什么合法？引用作用域在哪一刻结束？
3. 为什么"函数不能返回局部变量的引用"？修复方向为什么是"返回本体"？

---

## 4.3 The Slice Type（切片）

预计 15 分钟。这一节是第三课《切片与区间》的引子；你在 rustlings `primitive_types4` 问的"`&a[1..4]` 半开区间好处在哪"，第一半答案就在这一节。

### 1. 切片是什么

> Slices let you reference a contiguous sequence of elements in a collection. A slice is a kind of reference, so it does not have ownership.
> （切片让你引用集合中一段连续的元素；切片是一种引用，不拥有所有权。）

注意这句话怎么接上第二课：切片 = 借用 + 一段范围。它不拥有数据，所以也绝不触发 drop。

### 2. first_word 的两版（本节最值得细读的一段）

第一版返回下标：

```rust
fn first_word(s: &String) -> usize { /* 找到第一个空格，返回它的下标 */ }
```

问题在下标和 String 脱钩了——`s.clear()` 之后，返回的 `5` 还在，但它已经指向不存在的内容，而这种 bug 编译器不管。

第二版返回切片：

```rust
fn first_word(s: &String) -> &str { /* 找到第一个空格，返回 &s[0..i] */ }
```

现在 `s.clear()` 那行直接编译错误（`error[E0502]: cannot borrow s as mutable because it is also borrowed as immutable`）——因为切片活着的时候，原字符串连改都不让改。

读的时候问自己：**第二版为什么能抓住第一版抓不住的 bug？**（答案：借用规则把切片和 String 的"生死"绑在了一起，这正是第二课规则的威力。）

### 3. 切片语法与区间的省略写法

```rust
let s = String::from("hello world");
let hello = &s[0..5];   // 取下标 0..4（结束下标"大一不算"，左闭右开）
let world = &s[6..11];

let slice = &s[..2];    // 开头是 0 时可以省略
let slice = &s[3..];    // 取到末尾时可以省略
let slice = &s[..];     // 两个都省 = 整个字符串
```

原文的关键一句：切片内部存的是**起始位置和长度**，长度 = 结束下标 − 起始下标。这正是半开区间的好处之一——**减一下就是长度**（闭区间还得 +1）。相邻区间还能无缝拼接（`[0..2)` 接 `[2..4)`）。

你在 rustlings 见过的闭区间写法 `a[1..=4]`（包含端点 4）本节没出现，留到第三课展开。另注意：字符串切片的下标必须落在 UTF-8 字符边界上，切到多字节字符中间程序会直接退出。

### 4. 字符串字面量就是切片

```rust
let s = "Hello, world!";
```

> The type of `s` here is `&str`: It's a slice pointing to that specific point of the binary.
> （这里 `s` 的类型就是 `&str`：一个指向二进制文件中特定位置的切片。）

这也是字符串字面量不可变的原因——`&str` 是不可变引用。

### 5. 参数该写 &str 还是 &String

> Defining a function to take a string slice instead of a reference to a `String` makes our API more general and useful without losing any functionality.
> （函数收字符串切片而不是收 `&String`，API 更通用、更好用，且不损失任何功能。）

书上的例子：`first_word(s: &str)` 之后，`String` 的切片、`String` 的引用、字符串字面量全能传进去（靠 Deref 强制转换）。**这正是第二课课后任务 3 要你动手改的东西——先读 4.3，再改 WoL，顺序别反。**

### 自测题（读完合上书回答）

1. `&s[6..11]` 内部存了什么？长度怎么算？
2. `first_word` 返回 `&str` 之后，`s.clear()` 那行为什么编译不过了？靠哪条规则？
3. 函数参数写 `&str` 比写 `&String` 好在哪？那什么时候才该收 `String` 本体？

---

## 与后续课程的衔接

- **第三课《切片与区间》**：`&[T]` 全貌、半开区间的形式化理由、`1..=4` 的用武之地——你在 `primitive_types4` 的之问在那里收口。
- **再往后**：闭包与迭代器专课（`.iter().map().collect()`）。

## 主要来源

- [The Rust Book, Chapter 4.2: References and Borrowing](https://doc.rust-lang.org/book/ch04-02-references-and-borrowing.html)
- [The Rust Book, Chapter 4.3: The Slice Type](https://doc.rust-lang.org/book/ch04-03-slices.html)

（本指南所有英文引文均于 2026-10-20 从上述页面核实。）
