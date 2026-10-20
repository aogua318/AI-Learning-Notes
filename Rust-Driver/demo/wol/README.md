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

## 下一步（项目路线）

1. MAC 地址从命令行参数读入（`std::env::args()`，顺带练 `Option`）；
2. 接上真实发送：`std::net::UdpSocket` 广播到 `255.255.255.255:9`（网络发送留到这步再加）；
3. 同一 WiFi 下的网页按钮（小型 HTTP 服务，第二阶段工具课）。
