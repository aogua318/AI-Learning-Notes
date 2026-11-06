struct ButtonState {
    pin: u8,
    pressed: bool,
}

enum ButtonEvent {
    Pressed { pin: u8 },
    Released { pin: u8 },
    Held { pin: u8, ms: u32 },
}

impl ButtonState {
    fn new(pin: u8) -> Self {
        Self {
            pin,
            pressed: false,
        }
    }

    fn update(&mut self, pressed: bool, ms: u32) -> Option<ButtonEvent> {
        if pressed && !self.pressed {
            //按下
            self.pressed = true;
            Some(ButtonEvent::Pressed { pin: self.pin })
        } else if !pressed && self.pressed {
            //抬起
            self.pressed = false;
            Some(ButtonEvent::Released { pin: self.pin })
        } else if pressed && self.pressed {
            Some(ButtonEvent::Held { pin: self.pin, ms })
        } else {
            None
        }
    }
}

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
fn read_button<B: ButtonInput>(input: &B) -> bool {
    input.is_pressed()
}

fn main() {
    // println!("Hello, world!");
    let real = RealPin { pin: 15 }; // true
    let fake = FakePin { pressed: false }; // false

    // 静态分发：泛型函数接收具体类型
    assert!(read_button(&real));
    assert!(!read_button(&fake));

    // 动态分发：同一个 Vec 装不同具体类型
    let inputs: Vec<(&dyn ButtonInput, u32)> = vec![
        (&fake, 10), // false/false -> no event
        (&real, 15), // false -> true -> pressed
        (&real, 20), // true/true -> held
        (&fake, 15), // true -> false -> released
    ];

    let mut button = ButtonState::new(15);

    for (input, ms) in inputs {
        let pressed = input.is_pressed(); // 这里走 trait object 动态分发
        match button.update(pressed, ms) {
            Some(ButtonEvent::Pressed { pin }) => println!("pin {pin}: pressed"),
            Some(ButtonEvent::Released { pin }) => println!("pin {pin}: released"),
            Some(ButtonEvent::Held { pin, ms }) => println!("pin {pin}: held {ms} ms"),
            None => println!("no event"),
        }
    }
}
