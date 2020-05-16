extern crate simple_logger;
extern crate crossbeam_utils;

use super::{Clock, Display, MIDIInput};
use super::views::RootView;
use super::util::Timer;

pub trait AsyncTicking {
    fn get_tick_interval(&self) -> u32;
    fn tick(&mut self, app: &mut App);
}

pub struct App {
    pub clock: Clock,
    pub display: Display,
}

impl App {
    pub fn new() -> Self {
        simple_logger::init().unwrap();
        let root = Box::new(RootView::new());
        return Self {
            clock: Clock::new(),
            display: Display::new(root),
        };
    }

    pub fn tick_clock(&mut self) {
        self.clock.tick();
    }

    pub fn run(&mut self) {
        let mut midi = MIDIInput::new();
        //clock.register(midi);
        //clock.register(display);


        let mut screen_timer = Timer::new(std::time::Duration::from_millis(1000 / 60));

        loop {
            if screen_timer.tick() {
                display.tick(self);
            }

            midi.tick(self);
            ::std::thread::sleep(::std::time::Duration::new(0, 1_000_000_000u32 / 200));
        }
        //crossbeam_utils::thread::scope(|s| {
        //}).unwrap();
    }
}
