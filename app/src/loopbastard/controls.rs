use log::debug;
use super::App;
use super::events::{AppEvent, EventLoop, EventHandler};
use sdl2::keyboard::Keycode;

#[derive(Debug, Eq, PartialEq, Clone)]
pub enum Button {
    Play, Stop, Record, Number(usize), Shift,
}

pub struct ButtonControl {
    pub pressed: bool,
    button: Button,
    code: Keycode,
}

impl ButtonControl {
    pub fn new(button: Button, code: Keycode) -> Self {
        return Self {
            pressed: false,
            button: button,
            code: code,
        }
    }
}

impl EventHandler for ButtonControl {
    fn handle_event(&mut self, _app: &App, event: &AppEvent, event_loop: &mut EventLoop) {
        match event {
            AppEvent::SDLKeyUp(keycode) => {
                if *keycode == self.code {
                    self.pressed = false;
                }
            },
            AppEvent::SDLKeyDown(keycode) => {
                if *keycode == self.code {
                    self.pressed = true;
                    event_loop.post(AppEvent::ButtonPress(self.button.clone()));
                    debug!("Button pressed: {:?}", self.button);
                }
            },
            _ => (),
        }
    }
}

pub struct Controls {
    pub play_button: ButtonControl,
    pub stop_button: ButtonControl,
    pub record_button: ButtonControl,
    pub number1_button: ButtonControl,
    pub number2_button: ButtonControl,
    pub number3_button: ButtonControl,
    pub number4_button: ButtonControl,
    pub shift_button: ButtonControl,
}

impl Controls {
    pub fn new() -> Self {
        return Self {
            play_button: ButtonControl::new(Button::Play, Keycode::Space),
            stop_button: ButtonControl::new(Button::Stop, Keycode::Escape),
            record_button: ButtonControl::new(Button::Record, Keycode::R),
            number1_button: ButtonControl::new(Button::Number(1), Keycode::Num1),
            number2_button: ButtonControl::new(Button::Number(2), Keycode::Num2),
            number3_button: ButtonControl::new(Button::Number(3), Keycode::Num3),
            number4_button: ButtonControl::new(Button::Number(4), Keycode::Num4),
            shift_button: ButtonControl::new(Button::Shift, Keycode::LShift),
        }
    }

    pub fn foreach<F>(&mut self, mut f: F) where F: FnMut(&mut dyn EventHandler) {
        f(&mut self.play_button);
        f(&mut self.stop_button);
        f(&mut self.record_button);
        f(&mut self.number1_button);
        f(&mut self.number2_button);
        f(&mut self.number3_button);
        f(&mut self.number4_button);
        f(&mut self.shift_button);
    }
}

impl EventHandler for Controls {
    fn handle_event(&mut self, app: &App, event: &AppEvent, event_loop: &mut EventLoop) {
        self.foreach(|c| c.handle_event(app, event, event_loop));
    }
}
