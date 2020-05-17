extern crate log;
extern crate simple_logger;
extern crate crossbeam_utils;

use log::debug;
use std::sync::{Arc, Mutex};
use std::cell::RefCell;
use super::{Clock, Display, MIDIInput, Message};
use super::views::RootView;
use super::util::Timer;
use super::events::{EventLoop, AppEvent, EventHandler};

pub trait AsyncTicking {
    fn get_tick_interval(&self) -> u32;
    fn tick(&mut self, app: &mut App);
}

pub struct AppState {
}

pub struct App {
    pub state: AppState,
    pub clock: RefCell<Clock>,
    pub event_loop: Arc<Mutex<Box<EventLoop>>>,
    pub midi_input: MIDIInput,
}

impl App {
    pub fn new() -> Self {
        simple_logger::init().unwrap();
        return Self {
            state: AppState {},
            clock: RefCell::new(Clock::new()),
            event_loop: Arc::new(Mutex::new(Box::new(EventLoop::new()))),
            midi_input: MIDIInput::new(),
        };
    }

    pub fn run(&mut self) {
        let root = Box::new(RootView::new());
        let mut display = Display::new(root);

        let mut screen_timer = Timer::new(std::time::Duration::from_millis(1000 / 60));

        loop {
            if screen_timer.tick() {
                display.tick(self);
            }

            let event_loop_ptr = self.event_loop.clone();
            let event_loop = &mut event_loop_ptr.lock().unwrap();
            self.midi_input.tick(event_loop);
            while true {
                match event_loop.get_event() {
                    Some(event) => self.handle_event(event, event_loop),
                    None => { break; }
                }
            }
            ::std::thread::sleep(::std::time::Duration::new(0, 1_000_000_000u32 / 200));
        }
    }

    fn handle_event(&mut self, event: AppEvent, event_loop: &mut EventLoop) {
        self.clock.borrow_mut().handle_event(&self, event, event_loop);
    }
}
