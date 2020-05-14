extern crate loop_bastard_ui;

use sdl2::rect::Rect;
use sdl2::pixels::Color;
use loop_bastard_ui::View;

use super::{Canvas, View, ViewBase, ViewInner};

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
    fn render(&mut self, canvas: &mut Canvas, rect: &Rect) {
        canvas.set_draw_color(Color::GREEN);
        canvas.fill_rect(rect.clone()).unwrap();
        //self.container.render(surface, rect);
    }
}
