use std::time::Duration;
use std::vec::Vec;
use std::sync::Mutex;

pub trait AsyncTicking {
    fn get_tick_interval(&self) -> u32;
    fn tick(&mut self, clock: &Clock);
}

pub struct Clock {
    pub ticks: u64,
    ticking_objects: Vec<Mutex<Box<AsyncTicking>>>,
    ticking_intervals: Vec<u32>,
}

impl Clock {
    pub fn new() -> Self {
        return Clock {
            ticks: 0,
            ticking_objects: Vec::new(),
            ticking_intervals: Vec::new(),
        };
    }

    pub fn tick(&mut self) {
        self.ticks += 1;
        for (index, obj) in self.ticking_objects.iter().enumerate() {
            if self.ticking_intervals[index] == 0 {
                let mut unwrapped = obj.lock().unwrap();
                unwrapped.tick(&self);
                self.ticking_intervals[index] = unwrapped.get_tick_interval();
            }
            self.ticking_intervals[index] -= 1;
        }
    }

    pub fn register(&mut self, obj: Box<AsyncTicking>) {
        self.ticking_objects.push(Mutex::new(obj));
        self.ticking_intervals.push(0);
    }

    pub fn run(&mut self) {
        loop {
            self.tick();
            ::std::thread::sleep(Duration::new(0, 1_000_000_000u32 / 60));
        }
    }
}
