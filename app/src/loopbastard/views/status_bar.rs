extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::pixels::Color;
use loop_bastard_ui::View;

use super::{Canvas, View, ViewBase, ViewInner, App};
use crate::loopbastard::fonts;
use crate::loopbastard::util::get_beat_color;

#[derive(View)]
pub struct StatusBarView {
    inner: ViewInner,
}

impl StatusBarView {
    pub fn new() -> Self {
        return Self {
            inner: ViewInner::new(),
        };
    }
}

impl ViewBase for StatusBarView {
    fn render(&mut self, app: &mut App, canvas: &mut Canvas, rect: &Rect) {
        let border_size = 3;
        let background: Color = Color::from((32, 32, 32));
        let border_color: Color = Color::from((128, 128, 128));
        let beat_color: Color = Color::from((255, 255, 255));

        canvas.set_draw_color(background);
        canvas.fill_rect(rect.clone()).unwrap();

        canvas.set_draw_color(border_color);
        canvas.fill_rect(Rect::new(
            rect.left(),
            rect.bottom() - border_size as i32,
            rect.width(),
            border_size
        )).unwrap();

        let beat_width = rect.width() / app.clock.bar_size;
        let beat = app.clock.beats() % app.clock.bar_size;
        canvas.set_draw_color(get_beat_color(&app.clock, &beat_color, &border_color));
        canvas.fill_rect(Rect::new(
            rect.left() + (beat_width * beat) as i32,
            rect.bottom() - border_size as i32,
            beat_width,
            border_size
        )).unwrap();



        let a = fonts::font.render(format!("{} BPM", app.clock.bpm as u32));
        //self.container.render(surface, rect);
    }
}
