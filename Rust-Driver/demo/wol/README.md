# WoL 开机练习器（骨架版）

语言预备期的周末练手项目第一步。最终形态（Wake-on-LAN 开机工具：PC 端 Rust CLI + 同一 WiFi 下的网页按钮）见 [MISSION.md](../../../MISSION.md) 的关键决策 6。本骨架只做一件事——**构造魔术包并打印**，不发送任何网络流量；发送功能、MAC 参数化、网页按钮都留到项目正式启动。

第二课《借用与引用》的课后任务 3 落在这个项目上：把一个"传 String"的函数改成"传 &str"。

## 怎么跑

```bash
cd Rust-Driver/demo/wol
cargo run
```

零第三方依赖（只用标准库），预期输出是 102 字节的魔术包，每行 16 个十六进制数：

```
FF FF FF FF FF FF AA BB CC DD EE FF AA BB
CC DD EE FF AA BB CC DD EE FF AA BB CC DD
EE FF AA BB CC DD EE FF AA BB CC DD EE FF
AA BB CC DD EE FF AA BB CC DD EE FF AA BB
CC DD EE FF AA BB CC DD EE FF AA BB CC DD
EE FF AA BB CC DD EE FF AA BB CC DD EE FF
AA BB CC DD EE FF AA BB CC DD EE FF AA BB
```

## 魔术包协议（30 秒版）

Wake-on-LAN 魔术包 = 6 字节 `0xFF` + 16 遍目标 MAC 地址，共 102 字节，正式版以 UDP 广播发往端口 9。本骨架只构造、不发送。

## 练习任务书（第二课课后任务 3）

现在的 `main` 里，`mac` 的所有权被送进了 `build_magic_packet`：

```rust
let packet = build_magic_packet(mac);   // 所有权一去不回
// println!("目标 MAC：{mac}");          // 想取消这行注释？编译器不让
```

按步骤来，每步都亲自跑一遍：

**Step 1**　取消 `main` 里 `println!("目标 MAC：{mac}");` 的注释，`cargo run`，把报错原文整段贴给老师（或对照下面"预期报错"自检）。

**Step 2**　把 `build_magic_packet` 的签名从 `mac: String` 改成 `mac: &str`。函数体里 `parse_mac(&mac)` 中的 `&` 要去掉——参数已经是引用了。

**Step 3**　调用处跟着改：`build_magic_packet(&mac)`。`&String` 会自动当成 `&str` 用（这叫 Deref 强制转换，The Book 4.3 有讲）。

**Step 4**　`cargo run`：打印成功，`mac` 毫发无损——这正是第二课第 5 节表格的第二行（只读借）。

**追问（选做）**　`parse_mac` 一开始就是 `&str`，`build_magic_packet` 却收 `String`——差在哪？什么样的函数才**应该**收 `String` 本体？（提示：看参考答案里的 `save_target`。）

## 预期报错（自检用，原文 + 中文）

Step 1，取消注释之后（已按实际编译输出整理，省略了部分行列号）：

```
error[E0382]: borrow of moved value: `mac`
（借用已移动的值：mac）
59 |     let mac = String::from("AA-BB-CC-DD-EE-FF");
62 |     let packet = build_magic_packet(mac);
   |                                     --- value moved here（所有权在这里被移走）
66 |     println!("目标 MAC：{mac}");
   |                          ^^^ value borrowed here after move（移动之后又借用）

note: consider changing this parameter type in function `build_magic_packet`
      to borrow instead if owning the value isn't necessary
（注意这条提示：如果不需要取得所有权，可以考虑把 build_magic_packet 的参数类型改成借用
 ——编译器直接把 Step 2 的答案告诉你了）
```

Step 2 改完签名、但还没改调用处：

```
error[E0308]: mismatched types
（类型不匹配）
62 |     let packet = build_magic_packet(mac);
   |                                    ^^^ expected `&str`, found `String`
help: consider borrowing here
   |
62 |     let packet = build_magic_packet(&mac);
   |                                     +
（建议在这里借用：&mac）
```

> 撞见和上面不一样、或看不懂的报错，整段贴出来，别自己硬啃。

## 参考答案

<details>
<summary>点开：改完之后的 build_magic_packet 和 main（先自己试，再看）</summary>

```rust
fn build_magic_packet(mac: &str) -> Vec<u8> {
    let mut packet = vec![0xFF; 6];
    for _ in 0..16 {
        for byte in parse_mac(mac) {   // 参数已是 &str，不用再 &
            packet.push(byte);
        }
    }
    packet
}

fn main() {
    let mac = String::from("AA-BB-CC-DD-EE-FF");

    let packet = build_magic_packet(&mac);   // 借出去看一眼，mac 还是我的
    println!("目标 MAC：{mac}");              // 照常打印

    print_hex(&packet);
}
```

**什么时候才该收 `String`**：函数要把数据**留存**（存进结构体、塞进 Vec、搬去别处）时，收本体是对的——借用只适合"借来看一眼"：

```rust
struct Target {
    mac: String,
}

fn save_target(mac: String) -> Target {
    Target { mac }   // 长期持有，必须收所有权
}
```

</details>

## 第三课练习：first_word（已完成）

在本项目里实现 `fn first_word(s: &str) -> &str`：返回第一个空格之前的切片，无空格返回整个字符串。用的是索引循环版，只用已学概念。

`main` 里用 NLL 顺序演示了“借用结束后才能 clear”：

```rust
let mut s = String::from("Hello World");
let word = first_word(&s);
println!("第一个单词：{word}");   // word 最后一次使用
s.clear();                        // 编译通过：不可变借用已结束
```

把 `println!` 挪到 `s.clear()` 之后就会得到 `error[E0502]`（不可变借用与 `&mut` 重叠）；反例以注释保留在 `main.rs` 末尾。完整任务见 [lessons/0003-slices-and-ranges.html](../../lessons/0003-slices-and-ranges.html)。

## 第四课练习：迭代器重构（已完成）

- `first_word` 改为 `bytes.iter().enumerate()` 版，`main` 打印四个边界输入（含空串和三个空格）。
- `parse_mac` 改为 `split('-').map(...).collect()` 流水线：`&str` → `u8` → `Vec<u8>`。
- `print_hex` 改为 `packet.iter().enumerate()`。
- `cargo run` 输出与重构前一致，102 字节魔术包不变；四个 first_word 结果为空串时输出空行。

## 第五课练习：const 与定长缓冲（已完成）

- 文件顶部新增 `MAGIC_LEN` / `MAC_LEN` / `REPEAT` / `PACKET_LEN`，其中 `PACKET_LEN = 6 + 16 * 6 = 102`；`const _: () = assert!(PACKET_LEN == 102);` 把长度错误变成编译错误 E0080。
- `build_magic_packet` 返回 `[u8; PACKET_LEN]`：前 6 字节用可变切片填 `0xFF`，再把 MAC 重复 16 遍写入固定数组。
- `print_hex(&packet)` 不用改：`&[u8; 102]` 可以当 `&[u8]` 用。
- `cargo check` 无 warning；`cargo run` 输出仍是 102 字节魔术包。
- 精度：`parse_mac` 仍返回 `Vec<u8>`，这一步只把包体改成定长；完全无分配留到固件课。
- 完整任务见 [lessons/0005-const-and-compile-time.html](../../lessons/0005-const-and-compile-time.html)。

## 第六课练习：模块拆分（已完成）

- `src/protocol.rs`：协议常量、`const _` 断言、`build_magic_packet`、`parse_mac`、`print_hex`。
- `src/main.rs`：`mod protocol;` + `use protocol::{build_magic_packet, print_hex};`，保留 `first_word` 与 `main`。
- 可见性：`build_magic_packet` / `print_hex` 为 `pub`；`parse_mac` 与常量保持私有（同模块内可见，main 不需要它们）。
- `cargo fmt`、`cargo check` 通过；`cargo run` 输出仍为 102 字节魔术包。
- 完整任务见 [lessons/0006-modules-and-visibility.html](../../lessons/0006-modules-and-visibility.html)。

## 下一步（项目路线）

1. MAC 地址从命令行参数读入（`std::env::args()`，顺带练 `Option`）；
2. 接上真实发送：`std::net::UdpSocket` 广播到 `255.255.255.255:9`（网络发送留到这步再加）；
3. 同一 WiFi 下的网页按钮（小型 HTTP 服务，第二阶段工具课）。
