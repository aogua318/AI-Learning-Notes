//! WoL 开机练习器（骨架版）
//!
//! 项目定位：MISSION.md 里语言预备期的周末练手项目——最终形态是
//! "PC 端 Rust CLI + 同一 WiFi 下的网页按钮"。本骨架只走第一步：
//! 构造 Wake-on-LAN 魔术包（magic packet）并打印，不发送网络流量。
//!
//! 第二课《借用与引用》的课后任务在本文件完成（String → &str 重构），
//! 任务书与预期报错见同目录 README.md；第三课的 first_word 练习也在此实现。
//! 第四课的迭代器重构（parse_mac / print_hex）也在此完成。本文件是完成态。

mod protocol;
use protocol::{build_magic_packet, print_hex};

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
