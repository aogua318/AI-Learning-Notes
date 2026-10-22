//! WoL 开机练习器（骨架版）
//!
//! 项目定位：MISSION.md 里语言预备期的周末练手项目——最终形态是
//! "PC 端 Rust CLI + 同一 WiFi 下的网页按钮"。本骨架只走第一步：
//! 构造 Wake-on-LAN 魔术包（magic packet）并打印，不发送网络流量。
//!
//! 第二课《借用与引用》的课后任务在本文件完成（String → &str 重构），
//! 任务书与预期报错见同目录 README.md；第三课的 first_word 练习也在此实现。
//! 第四课的迭代器重构（parse_mac / print_hex）也在此完成。本文件是完成态。

const MAGIC_LEN: usize = 6;
const MAC_LEN: usize = 6;
const REPEAT: usize = 16;
const PACKET_LEN: usize = MAGIC_LEN + MAC_LEN * REPEAT;
const _: () = assert!(PACKET_LEN == 102);

/// 构造 Wake-on-LAN 魔术包：6 字节 0xFF 开头，后面跟 16 遍目标 MAC，共 102 字节。
/// 参数收 &str：只读借一眼，MAC 的所有权留在调用者手里。
fn build_magic_packet(mac: &str) -> [u8; PACKET_LEN] {
    // vec![0xFF; 6] 是宏调用：造一个含 6 个 0xFF 的 Vec<u8>。
    // 原始写法：let mut packet = Vec::new(); for _ in 0..6 { packet.push(0xFF); }
    let mac_bytes = parse_mac(mac);
    let mut packet = [0u8; PACKET_LEN];
    // for i in 0..MAGIC_LEN {
    //     packet[i]=0xFFu8;
    // }
    for b in &mut packet[..MAGIC_LEN]{
        *b = 0xFFu8;
    }
    for i in 0..REPEAT {
    let start = MAGIC_LEN + i * MAC_LEN;
    for j in 0..MAC_LEN {
        packet[start + j] = mac_bytes[j];
    }
}
    packet
}
/// 把 "AA-BB-CC-DD-EE-FF" 解析成 6 个字节。
/// 注意：这个函数的参数本来就是 &str——只读看一眼，不收所有权。
/// build_magic_packet 改成 &str 之后，和它就是同一个风格。
fn parse_mac(mac: &str) -> Vec<u8> {
    // let mut bytes = Vec::new();

    // for part in mac.split('-') {
    //     // u8::from_str_radix(字符串, 16)：按十六进制解析，"FF" 得到 255；
    //     // unwrap_or(0)：解析失败时给 0 而不是 panic（骨架图省事，正式版要报错）
    //     bytes.push(u8::from_str_radix(part, 16).unwrap_or(0));
    // }

    // bytes

    mac.split('-')
        .map(|part| u8::from_str_radix(part, 16).unwrap_or(0))
        .collect()
}

/// 按十六进制打印字节数组，每行 16 个。
/// 参数 &[u8] 是"字节切片的引用"——切片是第三课的主角，现在认得即可。
fn print_hex(packet: &[u8]) {
    for (i, &item) in packet.iter().enumerate() {
        // {:02X} 是格式语法：至少两位、不足补 0、大写十六进制（类似 C 的 %02X）
        print!("{:02X} ", item);
        if i % 16 == 15 {
            println!();
        }
    }
    println!();
}

/// 返回第一个空格之前的切片；没有空格就返回整个字符串。
/// 参数与返回值都是 &str：只借用、不复制。
fn first_word(s: &str) -> &str {
    let bytes = s.as_bytes();
    for (i, &item) in bytes.iter().enumerate() {
        if item == b' ' {
            // 如果检测到空格
            return &s[0..i];
        }
    }

    &s[..]
}

fn main() {
    let mac = String::from("AA-BB-CC-DD-EE-FF");

    // 借出去看一眼：mac 的所有权还在 main 手里，函数只读
    let packet = build_magic_packet(&mac);

    // 练习完成态：mac 毫发无损，照常打印
    println!("目标 MAC：{mac}");

    print_hex(&packet);

    let mut s = String::from("Hello World");
    let word = first_word(&s);
    println!("第一个单词：{word}"); // word 最后一次使用在这里
    s.clear(); // 编译通过：借用已结束，&mut s 不再冲突

    // 无空格分支
    println!("无空格：{}", first_word("Solo"));
    println!("3：{}", first_word(""));
    println!("4：{}", first_word("   "));

    // 反例（取消注释会报 E0502：不可变借用与 &mut 重叠）：
    // let t = String::from("Hello World");
    // let w = first_word(&t);
    // t.clear();
    // println!("{w}");
}
