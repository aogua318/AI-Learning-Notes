# 第五课聚类：const 与编译期常量——三轮才分开“求值时机 / 份数 / 地址”（2026-10-22）

本记录覆盖第五课《const 与编译期常量》的 CP1 批阅与七个追问；CP2/CP3 完成后在本文件追加。对应课程：lessons/0005-const-and-compile-time.html。

## 一、CP1 三轮弧线

**第一轮**：用户把 `const`/`static` 都归为“编译期分配好数据”，把 `let` 说成“运行期才开始分配数据”；并把 `unsafe` 说成“杜绝数据竞争”。两处都需纠偏：`let` 的栈帧在函数进入时整体划好，变量槽可能在栈/寄存器，也可能被优化掉；`unsafe` 只是把证明安全的责任交给程序员，不阻止竞争。

**第二轮**：用户已能写出“const/static 编译时求值、let 栈上多份、static 固定地址”，但仍有三个残留：
- “`const`/`static` 都只有一份”——错，只有 `static` 保证一份；`const` 在使用处内联/复制，不保证份数与地址；
- “`static` 可以更改”——错，普通 `static` 是不可变绑定；只有 `static mut` 能直接改，且读写都要 `unsafe`；
- “`static mut` 用 unsafe 是因为它只有一份”——因果错；只读的 static 也只有一份但安全，危险来自“全局可写 + 多线程/中断共享 + 编译器无法证明同步”。

**第三轮（通过）**：用户给出正确对照：`const` 份数不一定、地址不保证；`static` 一份、固定地址；`const` 不可变，`static` 默认不可变；`static mut` 用 unsafe 的原因是“全局可写共享状态 + 编译器无法证明同步”。CP1 通过。

## 二、七个追问的结论

1. **数组为什么不能用 `let n`**：长度是数组类型的一部分（`[T; N]`），必须在编译期确定；`let n` 是运行期绑定，不是常量表达式，报 E0435。数组占用字节数 = `N * size_of::<T>()`。
2. **`static GREETING: &str` 与 `let s = "wol"`**：字面量字节在 rodata；`static` 是“静态存放的胖指针槽”，`let` 是“栈/寄存器上的胖指针”；两者都可以指向同一份字面量字节。探针实测 `GREETING.as_ptr() == s.as_ptr()`，但 `&GREETING` 与 `&s` 不同；`static` 不是字符串字节本身，想直接存字节要写 `static BYTES: [u8; 3] = *b"wol";`。
3. **const 内联/地址**：内联是“在使用处把值放进去”，不是文本替换；`const MAX` 没有运行时变量。取 `&MAX` 时编译器才物化，可能每个使用点一个匿名副本，不保证同址；需要固定地址用 `static`。
4. **Java static 类比**：只像“共享一份”这一层；Java static 是类级成员、JVM 管理、可直接改；Rust static 是程序级项、固定分配、默认不可变、可变的要 unsafe。`static` 不是类型，是项/值。Rust `const` 更像 Java 的 `static final` 编译期常量。
5. **static 不 Drop 与泄漏**：static 内存是程序镜像/静态区的一部分，进程结束由 OS 回收，不算堆泄漏；但 static 里拥有的资源（Vec、文件、锁）不会被 Drop 清理，长期运行/嵌入式里可能成为资源泄漏。探针：给 static 放有 Drop 的类型，程序结束没有打印 drop。`static &str` 不拥有字节，无泄漏。
6. **`const _` 的生命周期**：`_` 是匿名常量项，编译期求值，没有运行时对象，所以不存在“回收”；它只为强制 `assert!` 在编译期执行，通过则 `()` 通常被优化掉，失败则 E0080。`let _` 才是运行期求值并立即丢弃。
7. **立即数**：直接编码在指令里的常量（如 `mov eax, 4`），不必从内存加载。小 `const` 常被折叠成立即数；大 `const` 可能物化到 rodata；`static` 一定有固定地址。ARM/Thumb 立即数范围有限，编译器可能用 literal pool。

## 三、学习者信号

- **“编译期”标签会吞掉三轴**：求值时机、存储/地址、可变性必须分列讲；只说“编译期/运行期”会诱发“const/static 都有固定分配/都只有一份”的合并。
- **C/Java 类比是双刃剑**：C 的 `const int` 与 Java 的 `static` 都会把旧模型带进来；每次类比后要立刻给差异表，并用探针验证地址/份数。
- **资源生命周期问题意识强**：主动问 static 的 Drop、泄漏、`const _` 回收、立即数，说明在把语言规则往内存/运行时模型上挂；用探针（地址、Drop 打印）比口头解释有效。

## 四、CP2 验收（2026-10-22）

WoL 顶部新增：

```rust
const MAGIC_LEN: usize = 6;
const MAC_LEN: usize = 6;
const REPEAT: usize = 16;
const PACKET_LEN: usize = MAGIC_LEN + MAC_LEN * REPEAT;

const _: () = assert!(PACKET_LEN == 102);
```

`cargo check` 通过；`cargo run` 仍输出 102 字节（6 行 × 16 + 末行 6 = 102）；把断言里的 102 改成 101 后，`cargo run` 报 E0080，贴出了 `evaluation panicked: assertion failed: PACKET_LEN == 101`，再改回 102。编译期护栏验证成功。

一个 doc comment 精度：`/// 构造 Wake-on-LAN...` 现在在 `const _` 之前，Rust 的 `///` 会附着到下一个项，所以它实际文档化的是 `const _`，不是 `build_magic_packet`。开 CP3 前把 `const _` 挪到 `///` 之前，让文档注释紧贴函数。

## 五、CP3 验收（2026-10-22）

`build_magic_packet` 返回 `[u8; PACKET_LEN]` 的版本通过：

```rust
fn build_magic_packet(mac: &str) -> [u8; PACKET_LEN] {
    let mac_bytes = parse_mac(mac);
    let mut packet = [0u8; PACKET_LEN];

    for b in &mut packet[..MAGIC_LEN] {
        *b = 0xFF;
    }

    for i in 0..REPEAT {
        let start = MAGIC_LEN + i * MAC_LEN;
        for j in 0..MAC_LEN {
            packet[start + j] = mac_bytes[j];
        }
    }

    packet
}
```

- `cargo check` 无 warning；`cargo run` 输出与重构前一致，仍为 102 字节。
- 第一版只填了前 6 个 `0xFF`，MAC 部分全是 `0x00`，并留下 `unused variable: mac_bytes` warning；补上嵌套循环后通过。这是本轮最有价值的“先看输出、再看 warning”的验收。
- doc comment 已修：`const _` 上移到 `///` 之前，文档注释重新属于 `build_magic_packet`。
- 用户要求保留注释；旧的 Vec 注释仍在文件里，复习时以代码为准。
- 精度：`parse_mac` 仍返回 `Vec<u8>`，这一步只把包体改成定长；完全无分配留到固件课。

## 六、里程碑与下一步

- CP1、CP2、CP3 全部通过；课程预检已通过（静态 0 error / 0 warning；浏览器双分支正确 4/4、错误 0/4）。
- 产物：`my-notes/0005-const-and-compile-time.md`、本聚类记录、术语表晋升 const/static（语言核心共 19 词条）、LEARNER-PROFILE 同步、WoL README 第五课小节。
- 下一课：模块与可见性（对齐 rustlings 10_modules）。
