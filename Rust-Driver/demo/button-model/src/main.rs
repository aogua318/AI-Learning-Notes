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

    fn update(&mut self, pressed: bool, ms: u32) -> ButtonEvent {
        if pressed && !self.pressed {
            //按下
            self.pressed = true;
            ButtonEvent::Pressed { pin: self.pin }
        } else if !pressed && self.pressed {
            //抬起
            self.pressed = false;
            ButtonEvent::Released { pin: self.pin }
        } else {
            ButtonEvent::Held { pin: self.pin, ms }
        }
    }
}

fn main() {
    // println!("Hello, world!");
    let mut button = ButtonState::new(15);

    for (pressed, ms) in [(true, 10), (true, 20), (false, 30)] {
        match button.update(pressed, ms) {
            ButtonEvent::Pressed { pin } => println!("pin {pin}: pressed"),
            ButtonEvent::Released { pin } => println!("pin {pin}: released"),
            ButtonEvent::Held { pin, ms } => println!("pin {pin}: held {ms} ms"),
        }
    }
}
