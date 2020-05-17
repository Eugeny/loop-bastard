use crossbeam_utils::thread::Scope;
use sdl2::pixels::Color;
use super::Clock;
use std::time::{Instant, Duration};

pub trait WithThread where Self: std::marker::Send {
    fn run(&mut self);
    fn start<'a> (&'a mut self, scope: &Scope<'a>) {
        scope.spawn(move |_| {
            self.run()
        });
    }
}

pub fn get_beat_color (clock: &Clock, color1: &Color, color2: &Color) -> Color {
    let p = clock.beat_progress();
    let c = (color1.r as f32 + (color2.r as f32 - color1.r as f32 * p)) as u8;
    return Color::RGB(
        (color1.r as f32 + (color2.r as f32 - color1.r as f32) * p) as u8,
        (color1.g as f32 + (color2.g as f32 - color1.g as f32) * p) as u8,
        (color1.b as f32 + (color2.b as f32 - color1.b as f32) * p) as u8,
    );
}

pub struct Timer {
    last: Instant,
    interval: Duration,
}

impl Timer {
    pub fn new(interval: Duration) -> Self {
        return Self {
            last: Instant::now(),
            interval: interval,
        }
    }

    pub fn tick(&mut self) -> bool {
        let now = Instant::now();
        if now - self.last > self.interval {
            self.last = now;
            return true;
        }
        return false;
    }
}
