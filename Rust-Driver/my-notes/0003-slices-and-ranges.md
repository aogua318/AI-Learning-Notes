# 第三课学习笔记：切片与区间

> 整理自第三课的临时笔记与三项作业提交（原笔记为即时记录，已按主题重组，误区处标注“曾误→正解”）。
> 配套材料：课程 [lessons/0003-slices-and-ranges.html](../lessons/0003-slices-and-ranges.html) · 术语表 [reference/glossary.html](../reference/glossary.html) · 练习：The Book 4.3 回看 + WoL 项目 first_word + rustlings 09_strings（均已完成）。

---

## 一、切片的本质：借用 + 范围

- 你的原笔记：“字符串切片只是借用，不是生成一个新的对象，本质还是在访问同一块内存区。”——**正确**。
- 精度：`&str` 变量本身是一个新的引用值（**胖指针 = 地址 + 长度**，占两个字宽），但**不是新的字符串数据**；它指向原 `String` 的缓冲区，不复制、不分配。
- C 类比：`&str ≈ (const char*, len)`；`&[u8]` 同理，是“缓冲区地址 + 长度”。
- 切片是引用 → 不拥有所有权，离开作用域不 drop；切片活着时原数据不能改（第二课的排他规则）。
- 两种常见形态：`&str`（字符串切片）、`&[T]`（数组 / Vec 切片）。字符串字面量本身就是 `&str`，指向二进制文件的只读段。

## 二、区间：左闭右开与三条设计理由

- `a..b` 是**左闭右开**（含 a、不含 b）；`a..=b` 是闭区间；`..b` / `a..` / `..` 是省略写法。
- 作业答案（正确，且没有再提 first_word）：
  1. **直接计算长度**：`len = 上界 − 下界`；
  2. **相邻区间无缝拼接**：`[0..2)` 接 `[2..4)`；
  3. **空区间写得出来**：`x..x`，长度 0。
- 这三条脱离 first_word 也成立——说明第二课留下的“用例锚定”误区已经拆掉。first_word 的 `&s[0..i]` 恰好不含空格，只是半开性质的**顺带好处**，不是设计原因。
- 精度：对 `String` 切片时，下标必须落在 UTF-8 字符边界上且不超过 `len`，否则运行时 panic；`x..x` 只有在边界合法时才是空切片。

## 三、first_word 两版：下标 vs 切片

- 第一版 `fn first_word(s: &String) -> usize`：返回**第一个空格的下标**；没有空格时返回 `s.len()`。
  - **精度修正**（作业原话）：“第一版 first_word 返回的是第一个单词的长度。”
  - **正解**：返回的是**空格下标（单词结束的位置）**。first_word 的单词恰好总是从下标 0 开始，所以这次数值上确实等于第一个单词的长度；换一个从中间开始的词，下标和长度就分家了。更关键的是 `usize` 不携带“它属于 s”的信息——s 被 clear 后，这个数字仍然存在，但已经无法代表任何有效位置。
- 第二版返回 `&str`：切片把 `word` 与原字符串绑定。`word` 活着（还要被 `println!` 使用）时，s 不能改；`s.clear()` 报 E0502。
- 你的 WoL 实现：

  ```rust
  fn first_word(s: &str) -> &str {
      let bytes = s.as_bytes();
      for i in 0..bytes.len() {
          if bytes[i] == b' ' {
              return &s[0..i];
          }
      }
      &s[..]
  }
  ```

  完全正确；签名收 `&str` 比 Book 的 `&String` 更泛（第三课第 7 节）。已实测：`"Hello World"` → `"Hello"`，`"Solo"` → `"Solo"`。

## 四、E0596 与 E0502：两层报错（重点纠偏）

- **E0596**：`s` 没有声明 `mut`；`clear` 需要 `&mut s`。改成 `let mut s` 后，这个错消失。
- **E0502**：`s` 同时被不可变借用（`word`）和可变借用（`clear`）使用。
  - **曾误**（作业原话）：“s.clear() 之后所有权已经给出去了，所以 s 借出的 word 也失效了。”
  - **正解**：`clear` **没有**交出所有权；它的签名是 `pub fn clear(&mut self)`——只是可变借用。`word` 是 `&str`，仍然活着，而且 clear 之后还要被 `println!` 使用；两个借用区间重叠，编译器不许。**不是“word 失效了”，而是“word 还有效，所以 s 不能改”**。
  - 若所有权真的被移走，报的是 **E0382**（borrow of moved value），不是 E0502。错误编号就是最直接的判别器。
  - C 类比：`clear(&mut s)` 像传 `String *p` 进去改内容，不是把 struct 交给函数。
- NLL 边界实证：

  ```rust
  let mut s = String::from("Hello World");
  let word = first_word(&s);
  println!("{word}");  // word 最后一次使用
  s.clear();           // 编译通过：不可变借用在这里已经结束
  ```

  调换顺序（clear 后再 println word）才报 E0502。规则不是“clear 一定不能跟在借用后面”，而是“**借用区间不能重叠**”。

## 五、rustlings 09_strings（strings1–4 已通过）

- **strings1**：`"blue".to_string()`，从 `&str` 造出 `String`。
- **strings2**：传 `&word`，把 `&String` 借成 `&str`（Deref 强制转换）。
- **strings3**：`trim_me` 的意图是返回去掉两端空白后的 `&str`。
  - 最短解法：`input.trim()`（标准库直接返回 `&str`）。
  - 你的手搓版用索引 + 迭代器，四个测试都过，但有两个边界崩溃（已实测）：
    - `""` → `right = 0`，`&input[0..1]` 越界 panic；
    - `"   "` → 找不到非空格，`right` 保持 `len`，`&input[0..len+1]` 越界 panic。
    - 另外只处理 ASCII 空格，不处理 `\t` / `\n`；`trim()` 处理 Unicode 空白。
  - 它也用了 `.iter().enumerate().rev()`——这是还没正式学的迭代器，能跑通说明你从 Book 看来了；迭代器专课会把它讲透。下次手写循环时，记得先补空串和全空白两个测试。
- **strings4**：11 个值的类型判断全部正确（`&str` / `String`）。注释里三处精度：
  - `.into()` 不是“随便写”，是 `Into<String>` 转换，目标类型由函数参数推断；
  - `.replace()` / `.to_lowercase()` 返回**新分配的 String**，不是“在原串上写入”；
  - `compose_me` 的 `+`：`Add<&str> for String` 的 `self` 按值收走左边的 String（可复用其缓冲区），右边只借 `&str`；所以左边必须是 String，返回值也必须是 String。

## 六、下一步

- 本课术语晋升：**切片（slice）**、**区间（range）**。
- 待解决：迭代器（`iter` / `into_iter` / `enumerate` / `rev`）、生命周期标注、`+` 与 Add trait、const。
- 下一课：《闭包与迭代器》——正好收 strings3 里提前用到的 `iter().enumerate().rev()`，以及 Book 版 first_word 的 `iter().enumerate()`。

---

## 自查问题（复习时盖住答案自测）

1. 切片复制数据吗？`&str` 的两个字段是什么？
2. 半开区间三条设计理由是什么？first_word 和它们是什么关系？
3. 第一版 first_word 返回的 5 是什么？为什么 `usize` 不能保证安全？
4. `clear()` 会拿走所有权吗？E0502 和 E0382 分别对应什么？
5. 为什么把 `println!("{word}")` 移到 `s.clear()` 之前就能编译？
6. `trim()` 返回 `&str` 还是 `String`？手搓 trim 的空串 / 全空白边界怎么修？
7. strings4 里哪些值产生 String、哪些是 &str？判断依据是什么？

---

> 本文件由临时笔记与作业批阅整理而成。学习过程中产生的新观察，随时告诉我，按主题追加进对应小节。
