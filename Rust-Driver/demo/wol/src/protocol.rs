const MAGIC_LEN: usize = 6;
const MAC_LEN: usize = 6;
const REPEAT: usize = 16;
const PACKET_LEN: usize = MAGIC_LEN + MAC_LEN * REPEAT;
const _: () = assert!(PACKET_LEN == 102);

/// 构造 Wake-on-LAN 魔术包：6 字节 0xFF 开头，后面跟 16 遍目标 MAC，共 102 字节。
/// 参数收 &str：只读借一眼，MAC 的所有权留在调用者手里。
pub fn build_magic_packet(mac: &str) -> [u8; PACKET_LEN] {
    // vec![0xFF; 6] 是宏调用：造一个含 6 个 0xFF 的 Vec<u8>。
    // 原始写法：let mut packet = Vec::new(); for _ in 0..6 { packet.push(0xFF); }
    let mac_bytes = parse_mac(mac);
    let mut packet = [0u8; PACKET_LEN];
    // for i in 0..MAGIC_LEN {
    //     packet[i]=0xFFu8;
    // }
    for b in &mut packet[..MAGIC_LEN] {
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
pub fn print_hex(packet: &[u8]) {
    for (i, &item) in packet.iter().enumerate() {
        // {:02X} 是格式语法：至少两位、不足补 0、大写十六进制（类似 C 的 %02X）
        print!("{:02X} ", item);
        if i % 16 == 15 {
            println!();
        }
    }
    println!();
}
