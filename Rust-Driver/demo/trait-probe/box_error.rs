//! CP1 探针 B：最小 Box<dyn Error>。
//! 运行：rustc --edition 2021 box_error.rs -o box_error.exe && ./box_error.exe; echo "exit=$?"
//! 预期（stderr）：Error: ParseIntError { kind: InvalidDigit }
//! 预期退出码：1
//!
//! 这里打印的是 Debug（main 返回 Err 时由 Termination 打印），
//! 不是 Display；ParseIntError 的 Display 文本不是这个格式。

use std::error::Error;

fn main() -> Result<(), Box<dyn Error>> {
    let n: i64 = "abc".parse()?;
    println!("{n}");
    Ok(())
}
