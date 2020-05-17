extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::render::TextureQuery;
use sdl2::pixels::Color;
use loop_bastard_ui::View;
use std::path::Path;

use super::{View, ViewBase, ViewInner, RenderContext, TextureStore, TextView};
use crate::loopbastard::util::get_beat_color;

#[derive(View)]
pub struct StatusBarView {
    inner: ViewInner,
    bpm_text: TextView,
}

impl StatusBarView {
    pub fn new() -> Self {
        return Self {
            inner: ViewInner::new(),
            bpm_text: TextView::new("- BPM", Color::RGB(255, 255, 255)),
        };
    }
}

impl ViewBase for StatusBarView {
    fn render(&mut self, context: &mut RenderContext, rect: &Rect) {
        let border_size = 3;
        let background: Color = Color::RGB(32, 32, 32);
        let border_color: Color = Color::RGB(128, 128, 128);
        let beat_color: Color = Color::RGB(255, 255, 255);

        context.canvas.set_draw_color(background);
        context.canvas.fill_rect(rect.clone()).unwrap();

        context.canvas.set_draw_color(border_color);
        context.canvas.fill_rect(Rect::new(
            rect.left(),
            rect.bottom() - border_size as i32,
            rect.width(),
            border_size
        )).unwrap();

        let beat_width = rect.width() / context.app.clock.bar_size;
        let beat = context.app.clock.beats() % context.app.clock.bar_size;
        context.canvas.set_draw_color(get_beat_color(&context.app.clock, &beat_color, &border_color));
        context.canvas.fill_rect(Rect::new(
            rect.left() + (beat_width * beat) as i32,
            rect.bottom() - border_size as i32,
            beat_width,
            border_size
        )).unwrap();

        self.bpm_text.set_size(200, rect.height());
        self.bpm_text.set_position(5, 5);
        self.bpm_text.set_text(format!("{} BPM", context.app.clock.bpm as u32));
    }

    fn foreach_child<F>(&mut self, mut f: F) where F: FnMut(&mut dyn View) {
        f(&mut self.bpm_text);
    }
}
