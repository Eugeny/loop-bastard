extern crate simple_logger;
extern crate crossbeam_utils;

mod loopbastard;
use loopbastard::{Clock, Display, WithThread, MIDIInput, AsyncTicking};
use loopbastard::views::RootView;

pub fn main() {
    simple_logger::init().unwrap();

    let root = Box::new(RootView::new());

    let mut display = Display::new(root);
    let mut midi = MIDIInput::new();
    let mut clock = Clock::new();
    //clock.register(midi);
    //clock.register(display);


    loop {
        midi.tick(&mut clock);
        display.tick(&clock);
        ::std::thread::sleep(::std::time::Duration::new(0, 1_000_000_000u32 / 60));
    }
    //crossbeam_utils::thread::scope(|s| {
    //}).unwrap();
}
