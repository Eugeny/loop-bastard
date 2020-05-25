extern crate log;
extern crate simple_logger;
extern crate crossbeam;
extern crate crossbeam_utils;
extern crate spin_sleep;

use std::sync::{Arc, Mutex};
use std::cell::RefCell;
use std::time::{Instant, Duration};
use super::{TICKS_PER_BEAT, Button, Controls, Clock, Display, MIDIInput, MIDIOutput, Sequencer, SequencerAction};
use super::views::RootView;
use super::util::Timer;
use super::events::{EventLoop, AppEvent, EventHandler};

pub trait AsyncTicking {
    fn get_tick_interval(&self) -> u32;
    fn tick(&mut self, app: &mut App);
}

pub struct AppState {
    pub global_q: u32,
    pub bar_size: u32,
    pub internal_bpm: u32,
    pub sequencers: Vec<Sequencer>,
    pub selected_sequencer: usize,
    pub selected_bank: usize,
}

pub struct App {
    pub state: RefCell<AppState>,
    pub _internal_clock_bpm: Arc<Mutex<u32>>,
    pub clock: RefCell<Clock>,
    pub event_loop: Arc<Mutex<RefCell<EventLoop>>>,
    pub controls: RefCell<Controls>,
    pub midi_input: RefCell<MIDIInput>,
    pub midi_output: RefCell<MIDIOutput>,
    display: RefCell<Display>,
}

impl App {
    pub fn new() -> Self {
        simple_logger::init().unwrap();
        let root = Box::new(RootView::new());
        let mut sequencers: Vec<Sequencer> = Vec::new();
        for _i in 0..16 {
            sequencers.push(Sequencer::new());
        }
        sequencers[0].output_channel = 5;
        for i in 0..16 {
            use super::{Message, MessageKind, SequencerEvent};
            let mut m = Message::new(MessageKind::NoteOn);
            m.note = 0 + i;
            m.velocity = 127;
            m.channel = 1;
            sequencers[0].events.push(SequencerEvent {
                position: i as u32 * 6,
                duration: 24,
                message: m,
            });
            // m.kind = MessageKind::NoteOff;
            // sequencers[0].events.push(SequencerEvent {
            //     position: i as u32 * 3 + 3,
            //     message: m,
            // });
        }
        return Self {
            state: RefCell::new(AppState {
                bar_size: 4,
                global_q: 4,
                internal_bpm: 120,
                sequencers: sequencers,
                selected_sequencer: 0,
                selected_bank: 0,
            }),
            clock: RefCell::new(Clock::new()),
            _internal_clock_bpm: Arc::new(Mutex::new(120)),
            event_loop: Arc::new(Mutex::new(RefCell::new(EventLoop::new()))),
            midi_input: RefCell::new(MIDIInput::new()),
            midi_output: RefCell::new(MIDIOutput::new()),
            controls: RefCell::new(Controls::new()),
            display: RefCell::new(Display::new(root)),
        };
    }

    pub fn run(&mut self) {
        crossbeam::scope(|s| {
            let arc_event_loop = self.event_loop.clone();
            let arc_bpm = self._internal_clock_bpm.clone();
            s.spawn(move |_| {
                App::run_internal_clock(arc_bpm, arc_event_loop);
            });
            self.run_main_thread();
        }).unwrap();
    }

    fn run_main_thread(&mut self) {
        let mut screen_timer = Timer::new(std::time::Duration::from_millis(1000 / 60));
        let mut midi_io_timer = Timer::new(std::time::Duration::from_millis(1000));
        loop {
            {
                let event_loop_cell = self.event_loop.lock().unwrap();
                let mut event_loop = event_loop_cell.borrow_mut();

                if screen_timer.tick() {
                    event_loop.post(AppEvent::UpdateDisplay);
                }

                if midi_io_timer.tick() {
                    event_loop.post(AppEvent::MIDIIOScan);
                    let mut internal_bpm = self._internal_clock_bpm.lock().unwrap();
                    if self.clock.borrow().has_external_clock() {
                        *internal_bpm = 0;
                    } else {
                        *internal_bpm = self.state.borrow().internal_bpm;
                    }
                }

                self.midi_input.borrow_mut().tick(&mut event_loop);

                // Pump events
                while let Some(event) = event_loop.get_event() {
                    self.handle_event(event, &mut event_loop);
                }
            }
            ::std::thread::sleep(Duration::new(0, 1_000_000_000u32 / 200));
        }
    }

    fn run_internal_clock(arc_bpm: Arc<Mutex<u32>>, arc_event_loop: Arc<Mutex<RefCell<EventLoop>>>) {
        loop {
            let now = Instant::now();
            let bpm = *arc_bpm.lock().unwrap();
            let next;
            if bpm > 0 {
                let event_loop_cell = arc_event_loop.lock().unwrap();
                let mut event_loop = event_loop_cell.borrow_mut();
                event_loop.post(AppEvent::InternalClockTick);
                next = now + Duration::from_secs_f32(60 as f32 / bpm as f32 / TICKS_PER_BEAT as f32)
            } else {
                next = now + Duration::from_millis(1000);
            }
            let new_now = Instant::now();
            if next > new_now {
                spin_sleep::sleep(next - new_now);
            }
        }
    }

    fn handle_event(&self, event: AppEvent, event_loop: &mut EventLoop) {
        {
            let mut state = self.state.borrow_mut();
            match event {
                AppEvent::ButtonPress(Button::Play) => {
                    let index = state.selected_sequencer;
                    if self.controls.borrow().shift_button.pressed || state.sequencers[index].recording {
                        state.sequencers[index].perform(SequencerAction::Start);
                    } else {
                        state.sequencers[index].schedule(SequencerAction::Start);
                    }
                },
                AppEvent::ButtonPress(Button::Stop) => {
                    let index = state.selected_sequencer;
                    if self.controls.borrow().shift_button.pressed {
                        state.sequencers[index].perform(SequencerAction::Stop);
                    } else {
                        state.sequencers[index].schedule(SequencerAction::Stop);
                    }
                },
                AppEvent::ButtonPress(Button::Record) => {
                    let index = state.selected_sequencer;
                    if self.controls.borrow().shift_button.pressed || state.sequencers[index].running {
                        state.sequencers[index].perform(SequencerAction::Record);
                    } else {
                        state.sequencers[index].schedule(SequencerAction::Record);
                    }
                },
                _ => (),
            }
        }

        self.clock.borrow_mut().handle_event(&self, &event, event_loop);
        self.display.borrow_mut().handle_event(&self, &event, event_loop);
        self.controls.borrow_mut().handle_event(&self, &event, event_loop);
        for s in self.state.borrow_mut().sequencers.iter_mut() {
            s.handle_event(&self, &event, event_loop);
        }

        self.midi_input.borrow_mut().handle_event(&self, &event, event_loop);
        self.midi_output.borrow_mut().handle_event(&self, &event, event_loop);
    }
}
