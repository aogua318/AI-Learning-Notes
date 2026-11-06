//! CP1 探针 A：同一份 ButtonInput 契约的静态分发与动态分发。
//! 运行：rustc --edition 2021 trait_demo.rs -o trait_demo.exe && ./trait_demo.exe
//! 预期：
//! generic: real=pressed fake=released
//! dyn: pressed
//! dyn: released

trait ButtonInput {
    fn is_pressed(&self) -> bool;
}

struct RealPin {
    pin: u8,
}

struct FakePin {
    pressed: bool,
}

impl ButtonInput for RealPin {
    fn is_pressed(&self) -> bool {
        self.pin == 15
    }
}

impl ButtonInput for FakePin {
    fn is_pressed(&self) -> bool {
        self.pressed
    }
}

fn describe<B: ButtonInput>(button: &B) -> &'static str {
    if button.is_pressed() {
        "pressed"
    } else {
        "released"
    }
}

fn describe_dyn(button: &dyn ButtonInput) -> &'static str {
    if button.is_pressed() {
        "pressed"
    } else {
        "released"
    }
}

fn main() {
    let real = RealPin { pin: 15 };
    let fake = FakePin { pressed: false };

    // 静态分发：编译期为 RealPin / FakePin 各生成一份 describe
    println!(
        "generic: real={} fake={}",
        describe(&real),
        describe(&fake)
    );

    // 动态分发：同一份 describe_dyn 处理两个不同具体类型
    let inputs: Vec<&dyn ButtonInput> = vec![&real, &fake];
    for input in inputs {
        println!("dyn: {}", describe_dyn(input));
    }
}
