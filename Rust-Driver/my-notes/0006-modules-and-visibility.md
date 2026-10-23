# 第六课学习笔记：模块与可见性

> 整理自第六课 CP1–CP3 的笔记、追问与代码验收（原笔记为即时问答，已按主题重组，误区处标注“曾误→正解”）。
> 配套材料：课程 [lessons/0006-modules-and-visibility.html](../lessons/0006-modules-and-visibility.html) · 术语表 [reference/glossary.html](../reference/glossary.html) · 练习：rustlings `10_modules` + WoL 拆模块。

---

## 一、四层边界：module / crate / package / workspace

| 概念 | 是什么 | 边界 |
|---|---|---|
| **module** | crate 内的命名空间，用 `mod` 声明 | 模块树的一层；文件只是存放位置 |
| **crate** | 一次编译单元 / 一个 target，拥有自己的模块树根 | `main.rs`、`lib.rs`、`src/bin/foo.rs` 分别是不同 crate 的根 |
| **package** | 一个带 `Cargo.toml` 的 Cargo 项目 | 最多 1 个 library crate + 任意多个 binary crate |
| **workspace** | 多个 package 的集合 | 根 `Cargo.toml` 的 `[workspace] members` 规定成员 |

**曾误**：“crate 就是当前项目/当前文件”“一个程序最多两个 crate”“main.rs 有三个根”。

**正解**：

- crate 不是文件，也不是 package；它是**编译单元 + 模块树根**。
- 一个进程只有一个 binary crate 根（一个 `main` 入口），但可以链接 **N 个 library crate**（自己的 lib、依赖、std）。
- `main.rs` 只有一个根；`lib.rs` / `helper/src/lib.rs` 是别的 crate 的根，不是 main 的根。
- 文件不是 crate：同一个 `protocol.rs` 可以同时被 lib 和 bin 的 `mod protocol;` 包含，分别编进两个 crate。

一个 workspace 示例：

```text
crate-tour/
├── Cargo.toml          # [workspace] members = ["app", "helper"]
├── app/                # package app
│   ├── src/lib.rs      # library crate app 的根
│   ├── src/protocol.rs # app 库里的模块
│   ├── src/main.rs     # binary crate app 的根
│   └── src/bin/tool.rs # binary crate tool 的根
└── helper/             # package helper
    └── src/lib.rs      # library crate helper 的根
```

`cargo metadata` 能看到 4 个 target：app lib、app bin、tool bin、helper lib；`app.exe` 链接 app bin + app lib + helper lib + std。

## 二、模块树与路径

```text
crate（src/main.rs）
├── main
└── protocol（src/protocol.rs）
    ├── build_magic_packet（pub）
    ├── print_hex（pub）
    ├── parse_mac（私有）
    └── packet（src/protocol/packet.rs，按需 pub mod）
```

- `crate::`：从当前 crate 的根出发（绝对路径）；
- `self::`：当前模块；
- `super::`：父模块；
- 标识符开头：当前模块里的子项/同级项（相对路径）。

`crate::` 永远指**当前 crate 的根**，不是当前文件。`main.rs`、`lib.rs`、`helper/lib.rs` 各自编译时，`crate::` 分别指它们自己的根。

## 三、可见性：默认私有 + 权限链

| 写法 | 可见范围 |
|---|---|
| 无 `pub` | 当前模块及其后代 |
| `pub(super)` | 父模块 |
| `pub(crate)` | 整个 crate（所有模块/文件），外部 crate 不可见 |
| `pub` | 外部 crate 也可访问（路径每层都要可见） |

- 默认私有：**子模块能看见祖先**；**祖先看不见子模块的私有项**。
- 路径上每一层都要放行；外层私有模块会挡住里面所有 public 项。
- `pub fn` 放在私有模块里，从外面仍然走不到：不是 `pub` 只给一层，而是路径断了。
- `pub(crate)` 的边界是 crate：lib 的 `pub(crate)` 对 main 不可见（lib/bin 是不同 crate）。
- 结构体字段、枚举变体的可见性另有规则，留到结构体/枚举课。

**嵌套盒子比喻**：外层盒子没打开，里层盒子打开了也拿不到；但如果你已经在外层盒子里面，就能打开里层。

## 四、use / as / pub use

- `use` 是**当前作用域的快捷方式**，只在所在作用域生效，不会自动传给子模块。
- `use` **不改变可见性**；能不能访问仍由 `pub` 决定。
- `as` 是别名绑定，不是 C 宏；不做文本替换。
- 嵌套路径：`use std::time::{SystemTime, UNIX_EPOCH};`。
- `pub use` 是**重新导出**：把被导入的名字放进当前模块的公开 API；普通 `use` 只在内部可见。

```rust
mod snacks {
    mod fruits {
        pub const PEAR: &str = "Pear";
    }

    pub use self::fruits::PEAR as fruit;
}
// main 可以访问 snacks::fruit；普通 use 则不行
```

**曾误**：“`pub use` 是把整个模块公开”“`use` 加了 pub 就能让路径找到”。

**正解**：`pub use` 导出的是**指定的项/名字**，不一定是整个模块；模块3里 `SystemTime` / `UNIX_EPOCH` 本来就是公开项，`use` 只负责把名字带进作用域，`pub` 在这里多余。

## 五、文件模块与 WoL 拆分

- `mod protocol;` 在 `main.rs`，编译器去找 `src/protocol.rs`（旧式写法 `src/protocol/mod.rs`）。
- **不要在 `protocol.rs` 里再写 `mod protocol`**；文件本身就是这个模块的内容。
- 嵌套：`protocol.rs` 里写 `pub mod packet;`，代码放 `src/protocol/packet.rs`。
- `mod` 只加载一次，不是 `#include`；不会重复定义。

WoL 的最终拆分：

```text
src/main.rs       mod protocol; use protocol::{...}; first_word; main
src/protocol.rs   常量; const _ 断言; build_magic_packet(pub); parse_mac(私有); print_hex(pub)
```

- `build_magic_packet` / `print_hex` 给 main 用 → `pub`；
- `parse_mac` 只被同模块的 `build_magic_packet` 调用 → 私有；
- 常量 main 不用 → 私有；`PACKET_LEN` 即使出现在公开返回类型 `[u8; PACKET_LEN]` 里，也不要求它自己 `pub`（签名对外是 `[u8; 102]`）；
- `cargo check` / `cargo run` 通过，输出仍为 102 字节。

## 六、错误编号

| 错误 | 含义 | 常见修法 |
|---|---|---|
| `E0603` | function/module is private | 给目标项或路径中间模块加合适的 `pub` |
| `E0433` | cannot find module or crate | 子模块里自己 `use crate::...`、用完整路径、检查 crate 名/依赖 |

## 七、自查问题（复习时盖住答案自测）

1. module、crate、package、workspace 四层分别是什么？各自由什么文件/清单界定？
2. 一个进程有几个 binary crate 根？可以链接几个 library crate？一个 package 最多几个 lib crate？
3. `main.rs`、`lib.rs`、`src/bin/foo.rs` 各是谁的根？`crate::` 在各自里面指什么？
4. 为什么父模块不能调用子模块的私有函数？为什么 `pub fn` 在私有模块里仍然出不去？
5. `pub`、`pub(super)`、`pub(crate)`、无 `pub` 的可见范围分别是什么？
6. `use` 和 `pub use` 的区别？`use` 会改变可见性吗？E0433 怎么修？
7. 为什么 `parse_mac` 不需要 `pub`？`PACKET_LEN` 为什么也不需要？
8. `mod protocol;` 为什么会去找 `src/protocol.rs`？`mod` 和 `#include` 差在哪？

---

> 本文件由第六课 CP1–CP3 的问答与代码验收整理而成。新的观察随时追加。
