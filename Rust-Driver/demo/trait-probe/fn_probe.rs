//! CP1 笔记 4 的修正版：闭包三张门牌。
//! 注意：`impl Trait` 不能写在 let 的类型标注里（E0562）；
//! 这里让闭包自己推断实现，约束写到泛型函数参数上。
//! 运行：rustc --edition 2021 fn_probe.rs -o fn_probe.exe && ./fn_probe.exe
//! 预期：
//! Fn: 5 5
//! FnMut: (1, 2)
//! FnOnce: hi

fn call_twice<F: FnMut() -> u32>(mut f: F) -> (u32, u32) {
    (f(), f())
}

fn consume<F: FnOnce() -> String>(f: F) -> String {
    f()
}

fn main() {
    // 只读捕获 -> Fn；可以多次调用
    let x = 5;
    let f = || x;
    println!("Fn: {} {}", f(), f());

    // 可变借用捕获 -> FnMut；可以多次调用
    let mut count = 0;
    let mut inc = || {
        count += 1;
        count
    };
    println!("FnMut: {:?}", call_twice(&mut inc));

    // 消耗捕获 -> FnOnce；只能调用一次
    let s = String::from("hi");
    let take = move || s;
    println!("FnOnce: {}", consume(take));
}
