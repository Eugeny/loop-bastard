use super::{App, Message, Button};
use std::collections::VecDeque;
use sdl2::keyboard::Keycode;

#[derive(Debug, Clone)]
pub enum AppEvent {
    MIDIMessage(Message),
    MIDIOutputMessage(Message),
    MIDIIOScan,
    SDLKeyUp(Keycode),
    SDLKeyDown(Keycode),
    ButtonPress(Button),
    ClockTick,
    InternalClockTick,
    GlobalQuantizerStep,
    UpdateDisplay,
}

pub trait EventHandler {
    fn handle_event(&mut self, _app: &App, _event: &AppEvent, _event_loop: &mut EventLoop) {}
}

pub struct EventLoop {
    events: VecDeque<AppEvent>,
}

impl EventLoop {
    pub fn new() -> Self {
        return Self {
            events: VecDeque::with_capacity(100),
        }
    }

    pub fn post(&mut self, event: AppEvent) {
        self.events.push_back(event);
    }

    pub fn get_event(&mut self) -> Option<AppEvent> {
        return self.events.pop_front();
    }
}
