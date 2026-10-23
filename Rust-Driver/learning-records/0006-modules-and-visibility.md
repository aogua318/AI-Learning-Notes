# 第六课聚类：模块与可见性——crate / package / file 三层边界（2026-10-22）

本记录覆盖第六课《模块与可见性》的 CP1 批阅与追问；CP2/CP3 完成后在本文件追加。对应课程：lessons/0006-modules-and-visibility.html。

## 一、CP1 三轮弧线

**第一轮**：模块树只写到 `crate → protocol → packet`，且认为 `parse_mac` 需要 `pub` 才能被 crate 访问；把 `pub` 说成“只暴露给上一层”；漏了 `pub(crate)` 与 E0433 的修法。

**第二轮**：树补上了 `main`、`build_magic_packet`、`print_hex`、`parse_mac`、`packet`；`parse_mac` 判断正确——main 不直接调用它，保持私有；用“嵌套盒子”比喻外层私有模块挡住里面 public 项，准确；`use` / `pub use` 也基本正确。仍缺 `pub(crate)` 与 E0433。

**第三轮（通过）**：`pub(crate)` 只对当前 crate 可见，lib 的 `pub(crate)` 不能被 main 访问；E0433 的修法补全（子模块内重新 `use crate::...` 或全路径），并知道 E0433 也可能是 crate 名拼错/依赖未声明。CP1 通过。

## 二、crate 到底是什么：四层边界

- **module**：crate 内的命名空间；`mod` 声明，文件只是存放位置。
- **crate**：一次编译单元 / 一个 target，拥有自己的模块树根；`main.rs`、`lib.rs`、`src/bin/foo.rs` 分别是不同 crate 的根。
- **package**：一个带 `Cargo.toml` 的 Cargo 项目；最多 1 个 library target + 任意多个 binary target。
- **workspace**：多个 package 的集合；根 `Cargo.toml` 的 `members` 规定成员。

用真实 workspace 验证：

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

`cargo metadata` 的 target 表：`app` 有 lib + 2 个 bin；`helper` 有 1 个 lib。整个 workspace 4 个 crate；`app.exe` 运行链接 app bin + app lib + helper lib + std，`tool.exe` 链接 tool bin + app lib + helper lib + std。

关键纠偏：

- `rustc app/src/main.rs` 单独编译会对 `app::` / `helper::` 报 E0433，因为它们是外部 crate，需要 Cargo 的 `--extern`；这证明 `lib.rs` / `helper/lib.rs` 不是 main 的根。
- 同一个 `protocol.rs` 可以同时被 lib 和 bin 的 `mod protocol;` 包含，被编进两个 crate；文件不是 crate。
- 一个进程只有一个 binary crate 根（一个 `main` 入口），但可以链接 N 个 library crate；“一个程序最多两个 crate”是把入口数当成了 crate 总数。
- `pub(crate)` 的边界是 crate：lib 的 `pub(crate)` 对 main 不可见（E0603），即使链接成同一个可执行文件。

## 三、错误编号与权限链

- **E0603**：function/module is private——目标项或路径中间模块私有。
- **E0433**：cannot find module or crate——`use` 不跨作用域、子模块没有自己的 `use`、crate 名拼错、依赖未声明。
- **权限链**：`pub` 是对父模块及以上/外部可见（路径每层都要通）；`pub(super)` 只给父模块；`pub(crate)` 整个 crate；无 `pub` 当前模块及后代。嵌套盒子比喻：外层私有模块没打开，里层 public 也拿不到。

## 四、学习者信号

- **需要真实项目和 metadata 才能钉住 crate**：口头讲“crate 是编译单元”不够；`cargo metadata` 的 target 表、lib+bin 探针、`rustc main.rs` 的 E0433 三组证据最有效。
- **文件/项目/crate 容易合并**：把 `main.rs`/`lib.rs` 当成“crate 的文件”，进而认为 main 有三个根；用“根属于哪个 crate”表纠正。
- **“pub 只给上一层”是常见误读**：`pub` 是更宽的公开，`pub(super)` 才是一层；嵌套盒子比喻帮助很大。
- **C/Java/Python 类比是入口，不是结论**：Java static、Python PATH、C `#include` 都能提供直觉，但每次都要用 Rust 的 target/模块树/可见性表校正。

## 五、CP2 验收（2026-10-22）

rustlings `10_modules` modules1–3 全部通过，状态推进到 `hashmaps1`。

- **modules1**：`pub fn make_sausage`，`get_secret_recipe` 保持私有；正确。
- **modules2**：`pub use self::fruits::PEAR as fruit;` 与 `pub use self::veggies::CUCUMBER as veggie;`；正确。`APPLE` / `CARROT` 的 unused warning 是题目自带常量。
- **modules3**：第一版写了 `pub use std::time::{SystemTime,UNIX_EPOCH};`。能跑，但语义多余：`SystemTime` / `UNIX_EPOCH` 本来就是公开项，`use` 只是把名字带进作用域；`pub use` 是重新导出，在 binary crate 根没有外部消费者。已改为 `use`，重跑通过。

关键信号：用户把“路径能找到”归因于“我用 pub 把它开放了出来”。这对 modules1/2 成立，对 modules3 不成立；需要区分 **`use` 引入名字** 与 **`pub`/`pub use` 放行可见性**。

## 六、CP3 验收（2026-10-22）

WoL 拆成两个文件：

- `src/main.rs`：`mod protocol;` + `use protocol::{build_magic_packet, print_hex};`，保留 `first_word` 与 `main`；
- `src/protocol.rs`：协议常量、`const _` 断言、`build_magic_packet`、`parse_mac`、`print_hex`。

可见性：

- `build_magic_packet` / `print_hex` 标 `pub`（main 调用）；
- `parse_mac` 保持私有（只被同一模块的 `build_magic_packet` 调用，同模块同级可见）；
- `PACKET_LEN` 等常量保持私有（main 不需要；仅有公开返回类型不要求常量本身 pub）。

`cargo fmt`、`cargo check` 通过；`cargo run` 输出与重构前一致，仍为 102 字节。CP3 通过，第六课结课。

## 七、里程碑与下一步

- CP1、CP2、CP3 全部通过；课程预检已通过（静态 0 error / 0 warning；浏览器双分支正确 4/4、错误 0/4）。
- 产物：`my-notes/0006-modules-and-visibility.md`、本聚类记录、术语表晋升（crate/module/visibility/use/pub use/package/workspace，语言核心共 24 词条）、WoL README 第六课小节、LEARNER-PROFILE 同步。
- 下一课：结构体与枚举（rustlings 07/08）。
