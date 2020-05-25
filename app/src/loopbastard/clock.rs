use std::time::{Instant, Duration};
use super::events::{AppEvent, EventHandler, EventLoop};
use super::{App, MessageKind};

pub struct Clock {
    _ticks: u32,
    _last_tick: Instant,
    _last_external_tick: Instant,
    pub bpm: f32,
}

pub const TICKS_PER_BEAT: u32 = 24;

impl Clock {
    pub fn new() -> Self {
        return Clock {
            _ticks: 0,
            _last_tick: Instant::now(),
            _last_external_tick: Instant::now() - Duration::from_secs(3600),
            bpm: 1.0,
        };
    }

    pub fn external_tick(&mut self) {
        self.tick();
        self._last_external_tick = Instant::now();
    }

    pub fn tick(&mut self) {
        self._ticks += 1;
        let now = Instant::now();
        let dt = now - self._last_tick;
        self._last_tick = now;
        if dt.as_micros() > 0 {
            let bpm = (60000000 / TICKS_PER_BEAT) as f32 / dt.as_micros() as f32;
            self.bpm = self.bpm * 0.9 + bpm * 0.1;
        }
    }

    #[inline]
    pub fn ticks(&self) -> u32 {
        self._ticks
    }

    #[inline]
    pub fn beats(&self) -> u32 {
        self._ticks / TICKS_PER_BEAT
    }

    pub fn beat_progress(&self) -> f32 {
        return (self._ticks % TICKS_PER_BEAT) as f32 / TICKS_PER_BEAT as f32;
    }

    pub fn has_external_clock(&self) -> bool {
        return Instant::now() - self._last_external_tick < Duration::from_millis(1000);
    }
}

impl EventHandler for Clock {
    fn handle_event(&mut self, app: &App, event: &AppEvent, event_loop: &mut EventLoop) {
        let state = app.state.borrow();
        match event {
            AppEvent::MIDIMessage(message) => {
                if message.kind == MessageKind::TimingClock {
                    self.external_tick();
                    event_loop.post(AppEvent::ClockTick);
                }
            },
            AppEvent::InternalClockTick => {
                self.tick();
                event_loop.post(AppEvent::ClockTick);
            },
            AppEvent::ClockTick => {
                if self._ticks % (TICKS_PER_BEAT * state.global_q) == 0 {
                    event_loop.post(AppEvent::GlobalQuantizerStep);
                }
            }
            _ => {}
        }
    }
}
