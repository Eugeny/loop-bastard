use crossbeam_utils::thread::Scope;
use sdl2::pixels::Color;
use sdl2::rect::Rect;
use super::views::{View, Canvas};
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

pub fn get_beat_color(clock: &Clock, color1: &Color, color2: &Color) -> Color {
    let p = clock.beat_progress();
    return Color::RGB(
        (color1.r as f32 + (color2.r as f32 - color1.r as f32) * p) as u8,
        (color1.g as f32 + (color2.g as f32 - color1.g as f32) * p) as u8,
        (color1.b as f32 + (color2.b as f32 - color1.b as f32) * p) as u8,
    );
}

pub fn get_blink_color(clock: &Clock, color1: &Color, color2: &Color) -> Color {
    return if clock.ticks() / 4 % 2 == 0 { *color1 } else { *color2 };
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

pub fn draw_rect(canvas: &mut Canvas, rect: Rect, width: u32) {
    for i in 0..width {
        canvas.draw_rect(Rect::new(rect.left() + i as i32, rect.top() + i as i32, rect.width() - i * 2, rect.height() - i * 2)).unwrap();
    }
}

pub fn arrange_spaced<T>(views: &mut [T], spacing: u32, rect: &Rect) where T: View {
    let w = (rect.width() + spacing) / views.len() as u32 - spacing;

    for (i, view) in views.iter_mut().enumerate() {
        view.set_position(i as i32 * (w + spacing) as i32, 0);
        view.set_size(w, rect.height());
    }
}
