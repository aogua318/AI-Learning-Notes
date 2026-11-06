//! 笔记 3.1 的修正版：`E: Debug` 是约束，不能写进返回类型。
//! 错误写法：fn main() -> Result<(), E: Debug>
//! 正确写法：fn main() -> Result<(), E>，并让 E 实现 Debug。
//! 运行：rustc --edition 2021 termination_fix.rs -o termination_fix.exe && ./termination_fix.exe; echo "exit=$?"
//! 预期：无输出，exit=0。

#[derive(Debug)]
struct E;

fn main() -> Result<(), E> {
    Ok(())
}
