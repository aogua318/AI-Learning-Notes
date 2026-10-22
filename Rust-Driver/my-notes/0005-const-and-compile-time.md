# 第五课学习笔记：const 与编译期常量

> 整理自第五课 CP1–CP3 的笔记、纠偏与代码验收（原笔记为即时问答，已按主题重组，误区处标注“曾误→正解”）。
> 配套材料：课程 [lessons/0005-const-and-compile-time.html](../lessons/0005-const-and-compile-time.html) · 术语表 [reference/glossary.html](../reference/glossary.html) · 实战：WoL 的 const 块与定长魔术包。

---

## 一、三种声明：求值时机 / 存储与地址 / 可变性

- `let`：**运行期绑定**。它的存储通常是栈帧或寄存器，也可能被优化掉；`let n = 4` 通常没有堆分配。“运行期”说的是绑定/赋值发生在运行期，不是“运行期才分配内存”。
- `const`：**编译期求值**，使用处内联/复制；通常不单独占一块存储。必须写类型、永远不可变，可以出现在数组长度等常量上下文里。
- `static`：初始值在编译期算好，但 `static` 本身是**运行期一直存在的固定分配**，恰好一份、地址固定。普通 `static` 是不可变绑定；只有 `static mut` 能直接改，且读写都要 `unsafe`。

| | `let` | `const` | `static` |
|---|---|---|---|
| 求值/存在 | 运行期绑定 | 编译期求值 | 初始化器编译期算，项本身运行期存在 |
| 份数 | 可以有多份 | **不保证一份** | **恰好一份** |
| 地址 | 栈/寄存器，可能被优化掉 | 不保证固定地址 | 固定地址 |
| 可变性 | `mut` 可改 | 永远不可变 | 默认不可变；`static mut` 要 `unsafe` |
| 数组长度 | 不能 | 能 | 能（不可变且初始化器为常量时） |

**曾误**：“`const` 和 `static` 在编译期都分配好数据，而且都只有一份；`static` 可以更改。”
**正解**：只有 `static` 保证一份和固定地址；`const` 是编译期值，使用处可能被复制。普通 `static` 不可变，`static mut` 才能直接改，且要 `unsafe`。

C 锚点：Rust 的 `const` 更像 C 的 `#define` / C++ 的 `constexpr`（有类型、有作用域，不是文本替换）；Rust 的 `static` 更像 C 里那个有地址的全局对象。C 的 `const int` 是只读对象，通常仍有存储，不要直接套到 Rust 的 `const` 上。

## 二、数组长度是类型的一部分

```rust
const N: usize = 4;
let buf = [0u8; N]; // buf: [u8; 4]

let n = 4;
let buf = [0u8; n]; // E0435: attempt to use a non-constant value in a constant
```

`[u8; 4]` 和 `[u8; 5]` 是两个不同的类型；类型必须在编译期完全确定，所以长度必须是常量表达式。`let n` 是运行期绑定，哪怕优化器知道它是 4，类型检查器也不接受。

- 数组占用字节数 = `N * size_of::<T>()`。
- `const` 和 `static` 都能当数组长度；分界不是“能否编译期用”，而是**地址与份数**。
- `let n = 4; let buf = [0u8; 4];` 可以——长度写的是字面量，不是 `n`。

## 三、const 的内联与地址

```rust
const MAX: usize = 4;

fn main() {
    let a = [0u8; MAX]; // 编译器看到的是 [0u8; 4]
    let b = [0u8; MAX]; // 又一次 [0u8; 4]
}
```

“内联”不是文本替换，而是**在使用处把常量值放进去**；运行时并没有一个叫 `MAX` 的变量。

“不保证固定地址”是指：写 `&MAX` 时编译器必须把值物化到某处，但可能在每个使用点各造一个匿名副本，也可能合并；语言不保证两个 `&MAX` 地址相同。需要固定地址，用 `static`。

大数组常量在多个使用点可能各复制一份，所以大查找表更适合 `static`。

## 四、static：固定地址的一份

```rust
static MAGIC: [u8; 6] = [0xFF; 6];

fn main() {
    let a = &MAGIC;
    let b = &MAGIC;
    println!("{}", std::ptr::eq(a, b)); // true：同一个分配
}
```

- 所有引用和裸指针都指向同一块分配；程序里只有一份。
- 生命周期是整个程序；程序结束时**不会调用 `Drop`**。
- 不可变 `static` 可能被放进只读内存，位置由链接器决定。
- 程序结束时 OS 回收进程地址空间，所以 static 本身不算堆泄漏；但 static 里拥有的资源（`Vec`、文件、锁）不会被 `Drop` 清理，长期运行/嵌入式里可能成为资源泄漏。`static &str` 不拥有字节，没有这个问题。

### static &str 与 let &str 的内存关系

`static GREETING: &str = "wol";` 有两层：

1. 字面量字节 `w o l` 在只读数据段（rodata）；
2. `GREETING` 是 static 项，静态地存一个胖指针（地址 + 长度）。

`let s = "wol";` 则是每次调用在栈/寄存器上新建一个胖指针，指向同一份字面量字节。

探针实测：`GREETING.as_ptr() == s.as_ptr()`（都指向字面量字节），但 `&GREETING` 与 `&s` 不同（一个是 static 项地址，一个是栈上局部槽地址）。`static` 不是字符串字节本身；想直接存字节，写 `static BYTES: [u8; 3] = *b"wol";`。

### static mut 与 unsafe

```rust
static mut COUNT: u32 = 0;

fn main() {
    // COUNT += 1; // E0133: use of mutable static is unsafe
    unsafe {
        COUNT += 1;
        let value = COUNT; // 复制出 u32，避免对 static 取引用
        println!("{value}");
    }
}
```

**曾误**：“`static mut` 用 unsafe 是因为它只有一份，unsafe 能防止数据竞争。”
**正解**：只读的 static 也只有一份，但很安全；危险来自**全局可写 + 多线程/中断共享 + 编译器无法证明同步**。`unsafe` 不防止竞争，它把“证明安全”的责任交给你；真正防止竞争靠原子类型、临界区、锁或单一所有者。

固件里的优先级：原子类型 / 临界区 / 把状态收进一个所有者；不要一上来就用 `static mut`。

## 五、const fn 与编译期检查

```rust
const fn packet_len() -> usize {
    6 + 16 * 6
}

const PACKET_LEN: usize = packet_len(); // 编译期调用

fn main() {
    let buf = [0u8; packet_len()]; // 数组长度也能用 const fn
    let runtime_len = packet_len(); // 运行期调用同一个函数，也合法
    println!("{PACKET_LEN} {runtime_len} {}", buf.len()); // 102 102 102
}
```

`const fn` 是“可以在编译期跑”的函数，不是“只能编译期跑”。里面不能堆分配、不能调用非 `const` 函数、不能 `async`；`if`、`loop`、`while` 都可以。

const 上下文里的越界、溢出、断言失败是**编译错误 E0080**；同样的操作在运行期才是 panic。

```rust
const N: usize = 4;
const BUF: [u8; N] = [0; N];
const FIRST: u8 = BUF[5]; // E0080: index out of bounds

const PACKET_LEN: usize = 6 + 16 * 6;
const _: () = assert!(PACKET_LEN == 102); // 不成立就 E0080
```

`const _` 是**匿名常量项**，只为在编译期执行检查；它没有运行时对象，不存在“回收”，`()` 也没有 `Drop`。对比 `let _ = expr;` 才是运行期求值并立即丢弃。

| 错误编号 | 触发场景 | 一句话 |
|---|---|---|
| `E0435` | `let n = 4; [0u8; n]` | 数组长度用了运行期值 |
| `E0015` | `const N: usize = runtime_fn();` | 常量里调用了非 const 函数 |
| `E0080` | const 求值越界 / 溢出 / 断言失败 | 编译期就发现常量算不出来 |
| `E0133` | 直接读写 `static mut` | 可变静态项需要 unsafe |

## 六、WoL 实战：const 块与定长魔术包

CP2：在 `main.rs` 顶部建立唯一真相源：

```rust
const MAGIC_LEN: usize = 6;
const MAC_LEN: usize = 6;
const REPEAT: usize = 16;
const PACKET_LEN: usize = MAGIC_LEN + MAC_LEN * REPEAT;
const _: () = assert!(PACKET_LEN == 102);
```

`cargo check` 通过；`cargo run` 仍输出 102 字节。把断言改成 101，`cargo run` 直接报 E0080，证明编译期护栏有效。

CP3：`build_magic_packet` 返回定长数组：

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

- 前 6 字节用可变切片填 `0xFF`；
- 第 `i` 遍 MAC 的起始下标是 `MAGIC_LEN + i * MAC_LEN`，第 `j` 个字节写在 `start + j`；
- `print_hex(&packet)` 不用改：`&[u8; 102]` 可以当 `&[u8]` 用；
- `cargo check` 无 warning，`cargo run` 输出与重构前一致，仍为 102 字节。

精度：这一步只把**包体**改成定长数组；`parse_mac` 仍返回 `Vec<u8>`，所以还不是完全无分配。真正的固件版会把解析也做成定长/写入调用方缓冲区，留到固件课。

顺手学到的语法点：`///` 文档注释会附着到**下一个项**，空行不会断开。`const _` 不能夹在 `///` 和 `fn` 之间，否则文档注释会贴到 `const _` 上。

## 七、自查问题（复习时盖住答案自测）

1. `let` / `const` / `static` 分别在什么时机求值？各自有固定地址吗？各有几份？
2. 为什么 `let n = 4; [0u8; n]` 报 E0435？`const` 和 `static` 为什么可以？
3. “const 使用处内联”是什么意思？为什么 `&CONST` 不保证同址？
4. `static GREETING: &str` 和 `let s = "wol"` 分别把胖指针放在哪？字符串字节在哪？
5. `static mut` 为什么需要 unsafe？unsafe 能防止数据竞争吗？
6. `static` 不调用 `Drop` 会不会内存泄漏？分哪几种情况？
7. `const _: () = assert!(...)` 里的 `_` 有运行时生命周期吗？
8. 什么是立即数？为什么说“const 更像立即数”只是经验说法？
9. 为什么固件里更喜欢 `[u8; PACKET_LEN]` 而不是 `Vec<u8>`？这一步为什么还不是完全无分配？

---

> 本文件由第五课 CP1–CP3 的问答与代码验收整理而成。新的观察随时追加。
