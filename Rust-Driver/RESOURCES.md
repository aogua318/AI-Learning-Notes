# Rust 与嵌入式 / 驱动开发 Resources

> 标注 ✅ 的条目为 2026-10-16 实际访问核实过内容；其余为高可信来源，使用前建议抽查最新版本。

## Knowledge

- [The Rust Programming Language（官方 Book）](https://doc.rust-lang.org/book/) ✅
  第 4 章 What Is Ownership 是所有权三规则的原始出处，措辞已核实。用途：语言预备期的第一教材，遇到概念先回这里查原文。
- [The Rust Book 13.1 Closures](https://doc.rust-lang.org/book/ch13-01-closures.html) / [13.2 Iterators](https://doc.rust-lang.org/book/ch13-02-iterators.html) / [13.4 Performance](https://doc.rust-lang.org/book/ch13-04-performance.html) ✅
  闭包捕获与 Fn traits、Iterator/next、iter/into_iter、适配器/消费者、零成本抽象的原文出处。用途：第四课主教材；first_word 迭代器版在 4.3。
- [The Rust Book 3.1 Variables and Mutability — Constants](https://doc.rust-lang.org/book/ch03-01-variables-and-mutability.html) ✅
  const 的硬规则（永远不可变、必须标类型、只能赋常量表达式）原文出处。用途：第五课主教材。
- [Rust Reference: Constant items](https://doc.rust-lang.org/reference/items/constant-items.html) / [Static items](https://doc.rust-lang.org/reference/items/static-items.html) / [Constant evaluation](https://doc.rust-lang.org/reference/const_eval.html) ✅
  const 内联与地址不保证、static 固定分配与 static mut 需要 unsafe、const 上下文与 E0080 的规范出处。用途：第五课规则核对与错误编号。
- [The Rust Book 7.1–7.5: Managing Growing Projects](https://doc.rust-lang.org/book/ch07-00-managing-growing-projects-with-packages-crates-and-modules.html) ✅
  模块树、默认私有、crate/self/super 路径、use/as/pub use、文件模块的原文出处。用途：第六课主教材；rustlings 10_modules 配套。
- [Rustlings（rust-lang 官方练习，MIT）](https://github.com/rust-lang/rustlings) ✅
  小型练习集，编译错误即反馈。用途：与 The Book 同步刷，move_semantics 系列练习是第一课的直接配套。
- [rp2040-hal API 文档（docs.rs）](https://docs.rs/rp2040-hal/latest/rp2040_hal/) ✅
  RP2040 的 HAL，实现 embedded-hal traits，含 usb / gpio / spi / i2c / pio 等模块；注意官方声明"API will remain volatile until 1.0.0"。用途：摇杆固件的主参考，写 USB HID 时查 usb 模块。
- [rp2040-project-template（rp-rs 官方模板）](https://github.com/rp-rs/rp2040-project-template) ✅
  rp2040-hal 起步模板，目标 thumbv6m-none-eabi，默认 probe-rs runner，也支持 picotool（PICOBOOT）烧录。用途：第一行固件代码的骨架。
- [GP2040-CE（OpenStickCommunity，MIT）](https://github.com/OpenStickCommunity/GP2040-CE) ✅
  Pico/RP2040 上的多平台手柄 / 摇杆固件，支持 SOCD 清理、多种输入模式。它是 C++ 写的，不抄代码，用途是读接线方案、按键扫描思路和"一个成品摇杆固件该有哪些功能"的参照系。
- [Embassy 官方站](https://embassy.dev/) ✅
  下一代嵌入式框架，embassy-rp 支持 RP2040，embassy-usb / embassy-net 分别提供设备端 USB 栈和网络栈。用途：第二阶段网络检测盒的备选技术栈（async 并发）。
- [Rust for Linux 内核文档（kernel.org）](https://www.kernel.org/doc/html/next/rust/index.html) ✅
  内核 Rust 官方文档入口，含 Quick Start、Coding Guidelines、Arch Support、Testing。用途：第二阶段"读懂 Linux Rust 驱动"的主入口。
- [aya 官方 Book](https://aya-rs.dev/book/) ✅
  用 Rust 写 eBPF 的库，Cargo 构建、CO-RE 支持、用户态与 eBPF 共享代码；约束已核实：无标准库（用 core）、512 字节栈、无堆、不能 panic。用途：第二年 eBPF / XDP 方向的主教材。
- [Raspberry Pi Pico 数据手册与入门文档（raspberrypi.com）](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf)
  RP2040 数据手册，查引脚、外设寄存器、USB 控制器的权威来源。用途：写固件时对照寄存器级行为。

## Wisdom (Communities)

- [Rust 官方用户论坛 users.rust-lang.org](https://users.rust-lang.org/)
  高信号、新手友好，语法与借用检查器问题的好去处。用途：语言预备期卡住时先搜这里。
- [r/rust](https://www.reddit.com/r/rust/)
  资讯与讨论流量大，信噪比一般但覆盖面广。用途：跟踪生态动态（新框架、新版本）。
- [rust-embedded Matrix 频道](https://matrix.to/#/#rust-embedded:matrix.org)
  嵌入式 Rust 最活跃的实时社区，rp2040-hal 作者常在。用途：固件踩坑时的第一求助点。
- [GP2040-CE 社区（GitHub Discussions / Discord）](https://github.com/OpenStickCommunity/GP2040-CE/discussions)
  摇杆 / 格斗手柄 DIY 老炮聚集地。用途：外壳结构、按键接线、街机手感问题的现实检验场。
- [Rust for Linux Zulip](https://rust-for-linux.zulipchat.com/)
  内核 Rust 开发的日常讨论区。用途：第二年读驱动源码时的旁听与提问。

## Gaps

- 缺少系统的中文"Rust 嵌入式从零"教程——现有资料以英文为主，用户的课程与手搓文档要承担中文语境补齐的责任
- Windows 原生环境下 rp2040-hal + UF2 烧录的中文实操资料稀少，第一课需要自建烧录流程图

## 社区偏好

- 用户未表示排斥社区；以上按需取用，不强制。
