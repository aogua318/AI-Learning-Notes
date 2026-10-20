//! WoL 开机练习器（骨架版）
//!
//! 项目定位：MISSION.md 里语言预备期的周末练手项目——最终形态是
//! "PC 端 Rust CLI + 同一 WiFi 下的网页按钮"。本骨架只走第一步：
//! 构造 Wake-on-LAN 魔术包（magic packet）并打印，不发送网络流量。
//!
//! 第二课《借用与引用》的课后任务落在这个文件里：
//! 把 build_magic_packet 的参数从 String 改成 &str。
//! 任务书、预期报错和参考答案见同目录 README.md。

/// 构造 Wake-on-LAN 魔术包：6 字节 0xFF 开头，后面跟 16 遍目标 MAC，共 102 字节。
///
/// 【练习目标】把这个参数从 `mac: String` 改成 `mac: &str`，
/// 并把 main 里那行注释掉的 println! 放出来——现在它会被编译器拦下。
fn build_magic_packet(mac: String) -> Vec<u8> {
    // vec![0xFF; 6] 是宏调用：造一个含 6 个 0xFF 的 Vec<u8>。
    // 原始写法：let mut packet = Vec::new(); for _ in 0..6 { packet.push(0xFF); }
    let mut packet = vec![0xFF; 6];

    // MAC 重复 16 遍，凑够网卡识别的魔术包格式
    for _ in 0..16 {
        for byte in parse_mac(&mac) {
            packet.push(byte);
        }
    }

    packet
}

/// 把 "AA-BB-CC-DD-EE-FF" 解析成 6 个字节。
/// 注意：这个函数的参数本来就是 &str——只读看一眼，不收所有权。
/// build_magic_packet 改成 &str 之后，和它就是同一个风格。
fn parse_mac(mac: &str) -> Vec<u8> {
    let mut bytes = Vec::new();

    for part in mac.split('-') {
        // u8::from_str_radix(字符串, 16)：按十六进制解析，"FF" 得到 255；
        // unwrap_or(0)：解析失败时给 0 而不是 panic（骨架图省事，正式版要报错）
        bytes.push(u8::from_str_radix(part, 16).unwrap_or(0));
    }

    bytes
}

/// 按十六进制打印字节数组，每行 16 个。
/// 参数 &[u8] 是"字节切片的引用"——切片是第三课的主角，现在认得即可。
fn print_hex(packet: &[u8]) {
    for i in 0..packet.len() {
        // {:02X} 是格式语法：至少两位、不足补 0、大写十六进制（类似 C 的 %02X）
        print!("{:02X} ", packet[i]);
        if i % 16 == 15 {
            println!();
        }
    }
    println!();
}

fn main() {
    let mac = String::from("AA-BB-CC-DD-EE-FF");

    // 【练习前的样子】mac 的所有权被送进了 build_magic_packet，一去不回
    let packet = build_magic_packet(mac);

    // 想在这里打印 mac？取消下一行的注释，看编译器怎么说——
    // 然后按 README.md 的任务书，把 build_magic_packet 改成收 &str。
    // println!("目标 MAC：{mac}");

    print_hex(&packet);
}
