use std::time::Instant;

pub struct Clock {
    _ticks: u32,
    _last_tick: Instant,
    bpm: f32,
    pub bar_size: u32,
}

const TICKS_PER_BEAT: u32 = 24;

impl Clock {
    pub fn new() -> Self {
        return Clock {
            _ticks: 0,
            _last_tick: Instant::now(),
            bpm: 1.0,
            bar_size: 4,
        };
    }

    pub fn tick(&mut self) {
        self._ticks += 1;
        let now = Instant::now();
        let dt = now - self._last_tick;
        self._last_tick = now;
        let bpm = (60000000 / 24) as f32 / dt.as_micros() as f32;
        self.bpm = self.bpm * 0.5 + bpm * 0.5;
        println!("{}", self.bpm);
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
}
