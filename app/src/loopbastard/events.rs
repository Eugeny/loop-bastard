use super::Message;
use super::App;
use std::collections::VecDeque;

#[derive(Debug, Clone)]
pub enum AppEvent {
    MIDIMessage(Message),
    ClockTick,
}

pub trait EventHandler {
    fn handle_event(&mut self, app: &App, event: AppEvent, event_loop: &mut EventLoop);
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
