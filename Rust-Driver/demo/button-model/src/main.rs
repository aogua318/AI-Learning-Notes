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
        }else{
            None
        }
    }
}

fn main() {
    // println!("Hello, world!");
    let mut button = ButtonState::new(15);

    for (pressed, ms) in [(false, 10),(true, 15), (true, 20), (false, 15)] {
        match button.update(pressed, ms) {
            Some(ButtonEvent::Pressed { pin }) => println!("pin {pin}: pressed "),
            Some(ButtonEvent::Released { pin }) => println!("pin {pin}: released"),
            Some(ButtonEvent::Held { pin, ms }) => println!("pin {pin}: held {ms} ms"),
            _ =>println!("no event")
        }
    }
}
