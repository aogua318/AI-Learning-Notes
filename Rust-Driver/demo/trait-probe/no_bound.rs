//! CP1 探针 A 的负例：故意删掉 `: ButtonInput`。
//! 这个文件预期编译失败，报 E0599，不是可运行程序。
//! 运行：rustc --edition 2021 no_bound.rs -o no_bound.exe
//! 预期错误：no method named `is_pressed` found for reference `&B`
//!
//! 本目录没有 Cargo.toml；`cargo build` 不会编译这个文件。

trait ButtonInput {
    fn is_pressed(&self) -> bool;
}

struct FakePin {
    pressed: bool,
}

impl ButtonInput for FakePin {
    fn is_pressed(&self) -> bool {
        self.pressed
    }
}

fn describe<B>(button: &B) -> &'static str {
    if button.is_pressed() {
        "pressed"
    } else {
        "released"
    }
}

fn main() {
    let fake = FakePin { pressed: false };
    println!("{}", describe(&fake));
}
